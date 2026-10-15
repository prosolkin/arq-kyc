"""Check every reader-facing text against the plain-language rules that a script can test.

Covers the rendered dashboard (all tabs, print mode), the deck (slide texts and speaker
notes), the methodology note and the README. Run after build_all.sh has built them:
    python3 -I analysis/check_writing.py
Exits with an error and lists each problem if any sentence breaks a rule.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import plain_language as pl  # noqa: E402

CHROME = os.environ.get("CHROME") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCRATCH = os.environ.get("DECK_SCRATCH") or os.path.join(ROOT, "analysis", "tools", ".deck-build")


def dashboard_blocks():
    page = "file://" + os.path.join(ROOT, "analysis", "export", "kyc-dashboard.html") + "#print"
    prof = os.path.join(SCRATCH, "writing-profile")
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--virtual-time-budget=6000", "--dump-dom", page],
                         capture_output=True, text=True, check=True).stdout
    assert "kx-page" in dom, "dashboard did not render"
    return pl.blocks_from_html(dom)


def main():
    sources = {
        "dashboard": dashboard_blocks(),
        "deck": json.load(open(os.path.join(SCRATCH, "deck-text.json"), encoding="utf-8")),
        "methodology note": pl.blocks_from_md(open(os.path.join(ROOT, "analysis", "export", "methodology-and-validation.md"), encoding="utf-8").read()),
        "README": pl.blocks_from_md(open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()),
    }
    site = os.path.join(ROOT, "docs", "index.html")
    if os.path.exists(site):
        sources["password page"] = [b for b in pl.blocks_from_html(open(site, encoding="utf-8").read()) if "/*[|" not in b]
    total = 0
    for name, blocks in sources.items():
        seen, bad = set(), []
        for s, p in pl.check_blocks(blocks):
            if s not in seen:
                seen.add(s); bad.append((s, p))
        total += len(bad)
        n_sent = sum(len(pl.sentences(b)) for b in blocks)
        print(f"writing {name}: {len(blocks)} blocks, {n_sent} sentences, {len(bad)} problems")
        for s, p in bad:
            print(f"   {'; '.join(p)} :: {s[:170]}")
    if total:
        sys.exit(f"writing check failed: {total} problems")
    print("writing check passed")


if __name__ == "__main__":
    main()
