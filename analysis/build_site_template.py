"""Render the password page template for the hosted dashboard.

Fills analysis/site/password_template.html ({{ tokens }}) from analysis/out, so the headline,
the figures and the daily chart on the password page come from the same aggregates as the
dashboard, deck and report. StatiCrypt's own /*[|...|]*/ placeholders are left for it to fill.
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


def load(name):
    with open(os.path.join(OUT, name + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


K = {r["metric"]: r["value"] for r in load("kpis")}
k = lambda m: float(K[m])
day = lambda s: dt.date.fromisoformat(s)
short = lambda s: day(s).strftime("%b %-d")


def chart():
    rows = [r for r in load("daily") if r["country"] == "ALL"]
    rows.sort(key=lambda r: r["date"])
    dates = [r["date"] for r in rows]
    vals = [float(r["approval_rate"]) for r in rows]
    W, H, L, R, T, B = 600, 196, 40, 12, 14, 24
    lo, hi = 0.5, 0.95
    assert min(vals) >= lo and max(vals) <= hi, (min(vals), max(vals))
    x = lambda i: L + i * (W - L - R) / (len(vals) - 1)
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    split = dates.index(K["split_date"])
    pts = [(x(i), y(v)) for i, v in enumerate(vals)]
    line = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    area = line + f" L{x(len(vals) - 1):.1f},{H - B:.1f} L{x(0):.1f},{H - B:.1f} Z"
    inc_days = sorted({d for r in load("incidents") for d in re.findall(r"\d{4}-\d{2}-\d{2}", r["days"])})
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Daily approval rate, {short(dates[0])} to {short(dates[-1])} 2023: '
           f'{100 * k("approval_a"):.1f}% in the prior 30 days, {100 * k("approval_b"):.1f}% in the recent 30 days.">']
    out.append('<g class="grid" data-anim="fade" style="--d:1.4s">' + "".join(
        f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>' for t in (0.6, 0.7, 0.8, 0.9)) + "</g>")
    out.append('<g class="axis" data-anim="fade" style="--d:1.5s">' + "".join(
        f'<text x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{round(t * 100)}%</text>' for t in (0.6, 0.7, 0.8, 0.9))
        + f'<text x="{x(0):.1f}" y="{H - 6}">{short(dates[0])}</text>'
        + f'<text x="{x(len(vals) - 1):.1f}" y="{H - 6}" text-anchor="end">{short(dates[-1])}</text></g>')
    out.append(f'<path class="area" d="{area}" data-anim="fade" style="--d:2.9s; --t:.9s"/>')
    out.append(f'<line class="split" x1="{x(split):.1f}" x2="{x(split):.1f}" y1="{T}" y2="{H - B}" data-anim="grow-y" style="--d:1.6s; --t:.6s"/>')
    out.append(f'<text class="split-label" x="{x(split) + 6:.1f}" y="{T + 10}" data-anim="fade" style="--d:2s">Recent period from {short(K["split_date"])}</text>')
    out.append(f'<path class="line" d="{line}" style="--d:1.7s"/>')
    ya, yb = y(k("approval_a")), y(k("approval_b"))
    out.append(f'<line class="avg a" x1="{x(0):.1f}" x2="{x(split - 1):.1f}" y1="{ya:.1f}" y2="{ya:.1f}" data-anim="grow-x" style="--d:3.2s; --t:.7s"/>')
    out.append(f'<line class="avg b" x1="{x(split):.1f}" x2="{x(len(vals) - 1):.1f}" y1="{yb:.1f}" y2="{yb:.1f}" data-anim="grow-x" style="--d:3.5s; --t:.7s"/>')
    out.append(f'<text class="avg-label a" x="{x(split * 0.5):.1f}" y="{y(0.935):.1f}" text-anchor="middle" data-anim="zoom" style="--d:3.8s">{100 * k("approval_a"):.1f}%</text>')
    out.append(f'<text class="avg-label b" x="{x(len(vals) - 1):.1f}" y="{y(0.72):.1f}" text-anchor="end" data-anim="zoom" style="--d:4s">{100 * k("approval_b"):.1f}%</text>')
    for j, d in enumerate(inc_days):
        i = dates.index(d)
        out.append(f'<circle class="pin" cx="{x(i):.1f}" cy="{y(vals[i]):.1f}" r="4.5" data-anim="zoom" style="--d:{3.9 + 0.07 * j:.2f}s"><title>Incident window day: {short(d)}</title></circle>')
    out.append("</svg>")
    return "\n".join(out)


def stats():
    items = [
        dict(pre="−", to=abs(k("delta_pp")), dec=1, suf=" pts", label="approval, prior to recent 30 days"),
        dict(pre="−", to=abs(k("approved_change")), dec=0, suf="",
             label=f"approvals: {abs(k('volume_effect')):,.0f} from lower volume, {abs(k('rate_effect')):,.0f} from the lower rate"),
        dict(pre="≈", to=k("incident_excess_base"), dec=0, suf="", label="failures above baseline in four date windows; causes unconfirmed"),
    ]
    cards = []
    for j, s in enumerate(items):
        final = s["pre"] + f"{s['to']:,.{s['dec']}f}" + s["suf"]
        cards.append(f'<div class="stat" data-anim="fly-up" style="--d:{1.9 + 0.18 * j:.2f}s">'
                     f'<b data-to="{s["to"]}" data-dec="{s["dec"]}" data-pre="{s["pre"]}" data-suf="{s["suf"]}">{html.escape(final)}</b>'
                     f'<span>{html.escape(s["label"])}</span></div>')
    return "\n".join(cards)


def main(dest):
    first, last = short(K["first_date"]), short(K["last_date"])
    research = day(K["research_date"]).strftime("%b %-d, %Y")
    text = {
        "kicker": "Product Owner case study · KYC onboarding",
        "headline": f"KYC approval fell {abs(k('delta_pp')):.1f} points in a month. Most of the arithmetic is known; most of the causes are not yet.",
        "subtitle": "What the 2023 extracts show, what remains a hypothesis, and what to do first.",
        "chart_title": f"Approval among recorded decisions, by day · {first} – {last}, 2023",
        "fineprint": f"Aggregated counts and rates from {k('total_users'):,.0f} recorded decisions. No personal data.",
        "footer": f"KYC approval-rate diagnosis · 2023 extracts ({first} – {last}) · Case-study submission",
        "footer_right": f"Vendor research dated {research}",
    }
    markup = {"chart_svg": chart(), "stats": stats()}
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
