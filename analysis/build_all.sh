#!/usr/bin/env bash
# Rebuild every deliverable in analysis/export/ from the two raw extracts.
# Requires: python3, node, the pinned tools in analysis/tools (npm install there once),
# and Google Chrome for the deck PDF.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -I analysis/build_datasets.py
python3 -I analysis/export_html.py
python3 -I analysis/build_notes.py
python3 -I analysis/chat/build_chat_context.py

SCRATCH="${DECK_SCRATCH:-analysis/tools/.deck-build}"
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
DECK_SCRATCH="$SCRATCH" node analysis/tools/build_deck.mjs

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ -x "$CHROME" ]; then
  rm -f analysis/export/kyc-approval-deck.pdf
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --user-data-dir="$SCRATCH/profile" \
    --print-to-pdf="$PWD/analysis/export/kyc-approval-deck.pdf" "file://$SCRATCH/deck.html" 2>/dev/null
  [ -s "analysis/export/kyc-approval-deck.pdf" ] && echo "deck PDF written" || { echo "deck PDF not updated" >&2; exit 1; }
  # the report PDF: deck, then the methodology note (needs uv for the two pinned Python packages)
  if command -v uv >/dev/null; then
    CHROME="$CHROME" uv run --quiet --with markdown==3.11.1 --with pypdf==6.20.1 python -I analysis/build_report.py
  else
    echo "uv not found: skipped the report PDF (see analysis/build_report.py)"
  fi
else
  echo "Chrome not found: skipped the deck and report PDFs"
fi

# the password-protected copy for GitHub Pages, only when a password is in the environment
if [ -n "${STATICRYPT_PASSWORD:-}" ]; then
  bash analysis/build_site.sh
else
  echo "STATICRYPT_PASSWORD not set: docs/index.html not rebuilt"
fi

# writing rules: every text a reader sees (dashboard, deck, note, README, password page) must pass the script-checkable rules
if [ -x "$CHROME" ]; then
  CHROME="$CHROME" DECK_SCRATCH="$SCRATCH" python3 -I analysis/check_writing.py
fi
ls -la analysis/export
