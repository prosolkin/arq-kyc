"""Render the password page template for the hosted dashboard.

Fills analysis/site/password_template.html ({{ tokens }}) from analysis/out and from the
dashboard's own theme tokens in export_html.py, so the password page uses the same colours,
type and figures as the dashboard. StatiCrypt's /*[|...|]*/ placeholders are left for it.
    python3 -I analysis/build_site_template.py <output path>
"""

import csv
import datetime as dt
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
SRC = os.path.join(ROOT, "analysis", "site", "password_template.html")
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from export_html import DARK, FIXED, LIGHT  # noqa: E402


def load(name):
    with open(os.path.join(OUT, name + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


K = {r["metric"]: r["value"] for r in load("kpis")}
k = lambda m: float(K[m])
day = lambda s: dt.date.fromisoformat(s)
short = lambda s: day(s).strftime("%b %-d")
pct = lambda v: f"{100 * v:.1f}%"


def theme_css():
    block = lambda d: " ".join(f"--{n}: {v};" for n, v in d.items())
    return (f"  :root {{ {block(FIXED)} {block(LIGHT)} }}\n"
            f"  @media (prefers-color-scheme: dark) {{ :root {{ {block(DARK)} }} }}")


def chart():
    rows = sorted((r for r in load("daily") if r["country"] == "ALL"), key=lambda r: r["date"])
    dates = [r["date"] for r in rows]
    vals = [float(r["approval_rate"]) for r in rows]
    W, H, L, R, T, B = 640, 210, 40, 74, 10, 22
    lo, hi = 0.5, 1.0
    x = lambda i: L + i * (W - L - R) / (len(vals) - 1)
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    split = dates.index(K["split_date"])
    step = (W - L - R) / (len(vals) - 1)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Daily pass rate, {short(dates[0])} to {short(dates[-1])} 2023: '
           f'{pct(k("approval_a"))} in the prior 30 days, {pct(k("approval_b"))} in the recent 30 days.">']
    for i, r in enumerate(rows):
        if r["incident_day"] == "1":
            out.append(f'<rect class="inc" x="{x(i) - step / 2:.1f}" y="{T}" width="{step:.1f}" height="{H - T - B}"/>')
    for t in (0.6, 0.7, 0.8, 0.9, 1.0):
        out.append(f'<line class="grid-line" x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        out.append(f'<text class="axis" x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{round(t * 100)}%</text>')
    out.append(f'<text class="axis" x="{x(0):.1f}" y="{H - 4}">{short(dates[0])}</text>')
    out.append(f'<text class="axis" x="{x(split):.1f}" y="{H - 4}" text-anchor="middle">{short(K["split_date"])}</text>')
    out.append(f'<text class="axis" x="{x(len(vals) - 1):.1f}" y="{H - 4}" text-anchor="end">{short(dates[-1])}</text>')
    for a, b, v in ((0, split - 1, k("approval_a")), (split, len(vals) - 1, k("approval_b"))):
        out.append(f'<line class="avg" x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
    out.append(f'<text class="avg-label" x="{W - R + 6}" y="{y(k("approval_a")) + 4:.1f}">Prior {pct(k("approval_a"))}</text>')
    out.append(f'<text class="avg-label" x="{W - R + 6}" y="{y(k("approval_b")) + 4:.1f}">Recent {pct(k("approval_b"))}</text>')
    line = "M" + " L".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    out.append(f'<path class="line" d="{line}"/>')
    out.append("</svg>")
    return "\n".join(out)


def stats():
    tiles = [
        ("Pass rate change", f"−{abs(k('delta_pp')):.1f} pts", f"{pct(k('approval_a'))} → {pct(k('approval_b'))}, prior to recent 30 days"),
        ("Approvals", f"−{100 * abs(k('approved_change_rel')):.1f}%",
         f"{abs(k('approved_change')):,.0f} fewer: {100 * k('volume_effect_share'):.0f}% from fewer decisions, {100 * k('rate_effect_share'):.0f}% from the lower rate"),
        ("Short incidents", f"≈{k('incident_excess_base'):,.0f}", "failures above baseline in four date windows; causes not confirmed"),
    ]
    return "\n".join(f'<div class="tile"><span class="label">{html.escape(a)}</span><span class="big">{html.escape(b)}</span><span class="sub">{html.escape(c)}</span></div>'
                     for a, b, c in tiles)


def main(dest):
    first, last = short(K["first_date"]), short(K["last_date"])
    research = day(K["research_date"]).strftime("%b %-d, %Y")
    signed = lambda v, fmt: ("−" if v < 0 else "+") + format(abs(v), fmt)
    text = {
        "strip": "Case study for the ARQ Product Owner role (ARQ Operating System). This is independent work, not an ARQ page.",
        "headline": "KYC pass rate: why it fell and what to do",
        "lede": f"The KYC pass rate (approval among recorded decisions) fell from {pct(k('approval_a'))} to {pct(k('approval_b'))} between the two periods "
                f"({signed(k('delta_pp'), '.1f')} pp), or {signed(k('approved_change'), ',.0f')} approvals.",
        "scope": f"{k('total_users'):,.0f} recorded decisions, one per user. Prior period: {first} – {short(K['last_a_date'])}, 2023; "
                 f"recent period: {short(K['split_date'])} – {last}, 2023. Aggregated data, no personal data.",
        "chart_title": "Approval among recorded decisions, by day",
        "fineprint": "The dashboard opens in this browser. It holds counts and rates only.",
        "footer": f"KYC approval-rate diagnosis · 2023 extracts ({first} – {last}) · Case-study submission",
        "footer_right": f"Vendor research dated {research}",
    }
    markup = {"theme_css": theme_css(), "chart_svg": chart(), "stats": stats()}
    with open(SRC, encoding="utf-8") as f:
        s = f.read()
    for key, v in text.items():
        s = s.replace("{{ " + key + " }}", html.escape(v, quote=False))
    for key, v in markup.items():
        s = s.replace("{{ " + key + " }}", v)
    left = re.findall(r"\{\{ *\w+ *\}\}", s)
    assert not left, left
    with open(dest, "w", encoding="utf-8") as f:
        f.write(s)
    print("password page template ->", os.path.relpath(dest, ROOT) if dest.startswith(ROOT) else dest)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "analysis", "tools", ".site-build", "password_template.html"))
