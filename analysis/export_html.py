"""Export the KYC approval-rate dashboard as one self-contained, offline HTML file.

Wraps the dashboard page (analysis/dashboard/index.html + kx.js) with:
- the aggregated datasets from analysis/out/*.csv, inlined as JSON
- d3 7.9.0, inlined from analysis/tools/node_modules (no network needed)
- a small stand-in for the Claude Dashboard runtime (`dash` API)
- theme tokens (light and dark) using system fonts
- a sources list from analysis/out/manifest.json

Run from the project root, after analysis/build_datasets.py:
    python3 -I analysis/export_html.py
"""

import csv
import datetime as dt
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(ROOT, "analysis", "dashboard")
DATA = os.path.join(ROOT, "analysis", "out")
D3 = os.path.join(ROOT, "analysis", "tools", "node_modules", "d3", "dist", "d3.min.js")
OUT = os.path.join(ROOT, "analysis", "export", "kyc-dashboard.html")

LIGHT = {
    "color-bg": "#f6f7f8", "color-panel": "#ffffff", "color-fg": "#1c2126", "color-fg-muted": "#59636d",
    "color-border-line": "#dfe3e7", "color-ok": "#1d7a4c", "color-warn": "#8f5b00", "color-bad": "#b4361f",
    "cds-chart-muted": "#b6bdc4", "cds-chart-status-critical": "#c63f2b", "cds-chart-grid": "#eceff2",
    "cds-chart-axis": "#c8cdd2", "cds-chart-reference": "#8b949c", "cds-surface-popover": "#ffffff",
    "cds-border": "#d9dee3", "cds-text-secondary": "#59636d", "cds-shadow-popover": "0 6px 24px rgba(20, 28, 36, 0.12)",
    "kx-s1": "#2f6db3", "kx-s2": "#d4782a", "kx-s3": "#7a58b8", "kx-s4": "#2a9a76",
    "kx-s5": "#c44f7c", "kx-s6": "#8b8f2e", "kx-s7": "#3d9fc9", "kx-s8": "#a1694b",
}
DARK = {
    "color-bg": "#111417", "color-panel": "#181c20", "color-fg": "#e5e9ec", "color-fg-muted": "#a1abb4",
    "color-border-line": "#2a3036", "color-ok": "#5fcf95", "color-warn": "#e6b35a", "color-bad": "#f07a66",
    "cds-chart-muted": "#58616a", "cds-chart-status-critical": "#f07a66", "cds-chart-grid": "#22282d",
    "cds-chart-axis": "#3a424a", "cds-chart-reference": "#7f8992", "cds-surface-popover": "#1f2428",
    "cds-border": "#323a41", "cds-text-secondary": "#a1abb4", "cds-shadow-popover": "0 6px 24px rgba(0, 0, 0, 0.45)",
    "kx-s1": "#6fa6e6", "kx-s2": "#f0a062", "kx-s3": "#a98ee3", "kx-s4": "#5cc9a2",
    "kx-s5": "#e886ac", "kx-s6": "#bfc35f", "kx-s7": "#7cc5e8", "kx-s8": "#cc967a",
}
FIXED = {
    "font-anthropic-sans": 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    "font-anthropic-serif": 'Georgia, "Iowan Old Style", "Times New Roman", serif',
    "cds-font-size-caption": "12.5px", "cds-font-size-body": "14.5px", "cds-font-size-heading": "16px",
    "cds-font-size-title": "24px", "cds-font-weight-medium": "600",
    "cds-gap-xs": "4px", "cds-gap-sm": "8px", "cds-gap-md": "14px", "cds-gap-lg": "22px", "cds-gap-xl": "32px",
    "cds-pad-xs": "4px", "cds-pad-sm": "8px", "cds-pad-md": "12px", "cds-pad-lg": "18px", "cds-pad-xl": "28px",
    "cds-radius": "8px", "cds-dur-slow": "0.35s", "cds-ease-out": "cubic-bezier(0.2, 0.7, 0.2, 1)",
}

SHIM = r"""
(() => {
  // Stand-in for the Claude Dashboard runtime: static datasets, filters and links.
  const raw = JSON.parse(document.getElementById('kx-data').textContent);
  const listeners = [];
  const defaults = { country: 'ALL', scenario: 'Central' };
  let params = { ...defaults };
  function data(id) {
    if (raw[id]) return { status: 'ok', data: raw[id].rows, columns: raw[id].columns, refreshing: false, meta: [], message: '' };
    return { status: 'missing', data: [], meta: [] };
  }
  const run = () => listeners.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  window.dash = {
    data,
    colors: Array.from({ length: 8 }, (_, i) => `var(--kx-s${i + 1})`),
    calc() { throw new Error('dash.calc is not used in the export'); },
    loader() {},
    refresh() {},
    params: () => ({ ...params }),
    setParams(next) { params = { ...params, ...next }; run(); },
    resetParams() { params = { ...defaults }; run(); },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) { /* file:// or sandboxed */ } },
    onData(fn) { listeners.push(fn); fn(); },
  };
  let lastWidth = 0, timer = 0;
  new ResizeObserver(([entry]) => {
    const w = Math.round(entry.contentRect.width);
    if (w === lastWidth) return;
    lastWidth = w;
    clearTimeout(timer);
    timer = setTimeout(run, 120);
  }).observe(document.getElementById('dash-root'));
})();
"""


def tokens(values):
    return "\n".join(f"    --{k}: {v};" for k, v in values.items())


def load_datasets():
    out = {}
    for name in sorted(os.listdir(DATA)):
        if name.endswith(".csv"):
            with open(os.path.join(DATA, name), newline="") as f:
                reader = csv.DictReader(f)
                out[name[:-4]] = {"columns": reader.fieldnames, "rows": list(reader)}
    return out


def assert_no_record_level_data(blob, datasets):
    """Fail if a user_reference value or a record-level column is embedded."""
    ids = set()
    with open(os.path.join(ROOT, "KYC_summary.csv")) as f:
        next(f)
        for line in f:
            ids.add(line.split(",")[1])
    leaked = [m for m in re.findall(r"\b\d{9,13}\b", blob) if m in ids]
    assert not leaked, f"user_reference values found in export: {leaked[:3]}"
    for name, d in datasets.items():
        assert not {"user_reference", "year_birth", "date_"} & set(d["columns"]), name


def main():
    page = open(os.path.join(DASH, "index.html")).read()
    script = open(os.path.join(DASH, "kx.js")).read()
    d3 = open(D3).read()
    assert '<script src="kx.js"></script>' in page
    page = page.replace('<script src="kx.js"></script>', "")
    datasets = load_datasets()
    manifest = json.load(open(os.path.join(DATA, "manifest.json")))
    blob = json.dumps(datasets, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    assert_no_record_level_data(blob, datasets)
    today = dt.date.today().strftime("%b %-d, %Y")
    sources = "\n".join(
        f'      <li><span class="kx-code">{html.escape(k)}.csv</span> · {len(datasets[k]["rows"]):,} rows. {html.escape(manifest.get(k, ""))}</li>'
        for k in sorted(datasets))

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>KYC Approval-Rate Diagnosis</title>
<meta name="description" content="What the 2023 KYC extracts show about the fall in approval among recorded decisions, what remains a hypothesis, and the plan.">
<style>
  :root {{
{tokens(FIXED)}
{tokens(LIGHT)}
    color-scheme: light;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
{tokens(DARK)}
      color-scheme: dark;
    }}
  }}
  :root[data-theme="dark"] {{
{tokens(DARK)}
    color-scheme: dark;
  }}
  [hidden] {{ display: none !important; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{ margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); line-height: 1.5; }}
  #dash-root {{ padding-inline: clamp(16px, 4vw, 40px); padding-block: 28px 40px; }}
  #dash-root b, #dash-root strong {{ font-weight: 600; }}
  .dash-skeleton {{ color: transparent !important; background: var(--color-border-line); border-radius: 4px; }}
  .kx-export-foot {{ max-width: 80rem; margin: var(--cds-gap-xl) auto 0; border-top: 1px solid var(--color-border-line); padding-top: var(--cds-pad-lg); font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); line-height: 1.55; display: flex; flex-direction: column; gap: 6px; }}
  .kx-export-foot summary {{ cursor: pointer; color: var(--color-fg); font-weight: 600; }}
  .kx-export-foot ul {{ margin: var(--cds-gap-sm) 0 0; padding-left: 1.2rem; display: flex; flex-direction: column; gap: 4px; }}
  @media print {{
    :root {{ color-scheme: light; }}
    body {{ background: #ffffff; font-size: 11pt; }}
    #dash-root {{ padding: 0; }}
    .kx-export-foot details > ul {{ display: flex; }}
    @page {{ margin: 14mm; }}
  }}
</style>
</head>
<body>
<main id="dash-root">
{page}
<footer class="kx-export-foot">
  <p>Exported {today}. Case-study submission: aggregated 2023 extract, no personal data. Works offline: charts (d3 7.9.0, ISC licence) and all data are inside this file. Every figure comes from the aggregated tables below, built by analysis/build_datasets.py from the two raw extracts. No user ids, birth dates or record-level fields are included.</p>
  <details>
    <summary>Sources ({len(datasets)} aggregated tables)</summary>
    <ul>
{sources}
    </ul>
  </details>
</footer>
</main>
<script type="application/json" id="kx-data">{blob}</script>
<script>
/* d3 v7.9.0 | https://d3js.org | Copyright 2010-2023 Mike Bostock | ISC License */
{d3}
</script>
<script>{SHIM}</script>
<script>
{script}
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(doc)
    assert "https://cdnjs" not in doc and "fonts.googleapis" not in doc
    print(OUT, f"{os.path.getsize(OUT):,} bytes,", len(datasets), "datasets, offline")


if __name__ == "__main__":
    main()
