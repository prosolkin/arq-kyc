"""Gate before publishing the repository: nothing from the raw extracts, and no password, in tracked files.

Run from the project root after `git add`:
    STATICRYPT_PASSWORD='...' python3 -I analysis/check_repo.py
Checks every file `git ls-files` reports (staged or committed): no raw extract, no user_reference
value from KYC_summary.csv, no record-level column header set, no .env, and no password string
(when STATICRYPT_PASSWORD is set). Office and PDF files are scanned as text after extraction.
"""

import csv
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "KYC_summary.csv")
RECORD_COLUMNS = {"user_reference", "year_birth", "document_number", "first_name", "last_name"}
TEXT_EXT = {".py", ".js", ".mjs", ".html", ".md", ".csv", ".json", ".sh", ".txt", ".yml", ".yaml", ".gitignore"}


def tracked():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def text_of(path):
    full = os.path.join(ROOT, path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pptx" or ext == ".docx":
        with zipfile.ZipFile(full) as z:
            return "\n".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    if ext == ".pdf":
        r = subprocess.run(["pdftotext", full, "-"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""
    if ext in TEXT_EXT or os.path.basename(path) in {".gitignore", ".nojekyll"}:
        with open(full, encoding="utf-8", errors="ignore") as f:
            return f.read()
    return None  # binary we don't scan (none expected)


def main():
    files = tracked()
    problems = []
    for p in files:
        base = os.path.basename(p)
        if re.match(r"KYC_.*\.csv$", base, re.I) or base == ".env":
            problems.append(f"raw or secret file tracked: {p}")
    ids = set()
    if os.path.exists(RAW):
        with open(RAW, newline="") as f:
            ids = {r["user_reference"] for r in csv.DictReader(f) if r.get("user_reference")}
    else:
        print("note: KYC_summary.csv not present, user_reference check skipped")
    pw = os.environ.get("STATICRYPT_PASSWORD")
    if not pw:
        print("note: STATICRYPT_PASSWORD not set, password check skipped")
    unscanned = []
    for p in files:
        t = text_of(p)
        if t is None:
            unscanned.append(p)
            continue
        if pw and pw in t:
            problems.append(f"password string in {p}")
        if ids:
            tokens = set(re.findall(r"[A-Za-z0-9_-]{6,}", t))
            hit = tokens & ids
            if hit:
                problems.append(f"{len(hit)} user_reference values in {p}")
        if p.endswith(".csv"):
            with open(os.path.join(ROOT, p), newline="") as f:
                header = set(next(csv.reader(f), []))
            if header & RECORD_COLUMNS:
                problems.append(f"record-level columns {sorted(header & RECORD_COLUMNS)} in {p}")
    if unscanned:
        problems.append("unscanned binary files: " + ", ".join(unscanned))
    print(f"{len(files)} tracked files checked")
    if problems:
        print("\n".join("FAIL " + x for x in problems))
        sys.exit(1)
    print("repo gate passed")


if __name__ == "__main__":
    main()
