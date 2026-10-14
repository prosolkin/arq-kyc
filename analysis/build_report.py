"""Build the submission report PDF: the deck PDF followed by the methodology note.

The note is rendered from analysis/export/methodology-and-validation.md with Python-Markdown
and printed with headless Chrome, then merged after the deck with pypdf.
Run from the project root after build_all.sh has written the deck PDF:
    uv run --quiet --with markdown==3.11.1 --with pypdf==6.20.1 python -I analysis/build_report.py
"""

import html
import os
import shutil
import subprocess
import sys

import markdown
from pypdf import PdfReader, PdfWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "analysis", "export")
NOTE_MD = os.path.join(EXP, "methodology-and-validation.md")
DECK_PDF = os.path.join(EXP, "kyc-approval-deck.pdf")
OUT_PDF = os.path.join(EXP, "kyc-approval-report.pdf")
SCRATCH = os.environ.get("REPORT_SCRATCH") or os.path.join(ROOT, "analysis", "tools", ".report-build")
CHROME = os.environ.get("CHROME") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: Letter; margin: 0.7in 0.65in; }
html { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; color: #1F2A2E; line-height: 1.45; }
body { margin: 0; }
h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; font-weight: normal; color: #0F4C4D; }
h1 { font-size: 24pt; margin: 0 0 4pt; }
h1 + p { color: #5C686C; margin-top: 0; }
h2 { font-size: 15pt; margin: 20pt 0 6pt; page-break-after: avoid; border-bottom: 1px solid #D5DCDD; padding-bottom: 3pt; }
h3 { font-size: 12pt; margin: 14pt 0 4pt; page-break-after: avoid; }
p, ul, ol { margin: 0 0 7pt; }
li { margin-bottom: 2pt; }
code { font-family: Menlo, Consolas, monospace; font-size: 9pt; background: #F3F6F6; padding: 0 2pt; }
pre { background: #F3F6F6; padding: 6pt 8pt; font-size: 9pt; border-radius: 3pt; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 4pt 0 10pt; page-break-inside: auto; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th { background: #0F4C4D; color: #fff; text-align: left; font-weight: bold; padding: 3pt 4pt; vertical-align: top; }
td { border-bottom: 1px solid #D5DCDD; padding: 3pt 4pt; vertical-align: top; overflow-wrap: break-word; }
tr:nth-child(even) td { background: #F7F9F9; }
a { color: #0F4C4D; text-decoration: none; }
.part { font-family: Georgia, serif; color: #5C686C; font-size: 11pt; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 14pt; }
"""


def note_html():
    with open(NOTE_MD, encoding="utf-8") as f:
        body = markdown.markdown(f.read(), extensions=["tables", "fenced_code"])
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Methodology and validation</title>"
            f"<style>{CSS}</style></head><body><div class='part'>Part 2 · Methodology and validation</div>{body}</body></html>")


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    note_html_path = os.path.join(SCRATCH, "note.html")
    note_pdf = os.path.join(SCRATCH, "note.pdf")
    with open(note_html_path, "w", encoding="utf-8") as f:
        f.write(note_html())
    if not os.path.exists(CHROME):
        sys.exit("Chrome not found: set CHROME to the browser binary")
    if os.path.exists(note_pdf):
        os.remove(note_pdf)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={os.path.join(SCRATCH, 'profile')}", f"--print-to-pdf={note_pdf}",
                    "file://" + note_html_path], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    if not os.path.getsize(note_pdf):
        sys.exit("note PDF is empty")
    writer = PdfWriter()
    deck_pages = len(PdfReader(DECK_PDF).pages)
    for part in (DECK_PDF, note_pdf):
        writer.append(part)
    writer.add_metadata({"/Title": "KYC approval-rate diagnosis: report", "/Subject": "ARQ case study: deck and methodology note"})
    if os.path.exists(OUT_PDF):
        os.remove(OUT_PDF)
    with open(OUT_PDF, "wb") as f:
        writer.write(f)
    total = len(PdfReader(OUT_PDF).pages)
    note_pages = len(PdfReader(note_pdf).pages)
    assert total == deck_pages + note_pages, (total, deck_pages, note_pages)
    print(f"report PDF: {total} pages ({deck_pages} deck + {note_pages} note) -> {os.path.relpath(OUT_PDF, ROOT)}")


if __name__ == "__main__":
    main()
