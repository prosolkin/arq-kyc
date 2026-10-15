#!/usr/bin/env bash
# Build docs/index.html: the offline dashboard, encrypted for GitHub Pages with StatiCrypt.
# The password comes only from the STATICRYPT_PASSWORD environment variable. It is never
# written to a file: the page holds a salt and the encrypted payload, nothing else.
# The password page is analysis/site/password_template.html, filled by analysis/build_site_template.py
# with the dashboard theme tokens and the figures from analysis/out.
# Run from the project root after analysis/export_html.py:
#     STATICRYPT_PASSWORD='...' bash analysis/build_site.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${STATICRYPT_PASSWORD:?set STATICRYPT_PASSWORD in the environment}"

SCRATCH="analysis/tools/.site-build"
rm -rf "$SCRATCH" && mkdir -p "$SCRATCH" docs
cp analysis/export/kyc-dashboard.html "$SCRATCH/index.html"

# The chat panel needs the proxy address and its access token. Both go only into this copy,
# which is encrypted next: the public export in the repo never holds the token.
CHAT_ENDPOINT="${CHAT_ENDPOINT:-$(cat analysis/chat/chat-endpoint.txt 2>/dev/null || true)}"
CHAT_TOKEN="${CHAT_TOKEN:-$(cat analysis/chat/.chat-token 2>/dev/null || true)}"
if [ -n "$CHAT_ENDPOINT" ] && [ -n "$CHAT_TOKEN" ]; then
  CHAT_ENDPOINT="$CHAT_ENDPOINT" CHAT_TOKEN="$CHAT_TOKEN" python3 -I - "$SCRATCH/index.html" <<'PY'
import json, os, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
cfg = json.dumps({"endpoint": os.environ["CHAT_ENDPOINT"].strip(), "token": os.environ["CHAT_TOKEN"].strip()})
assert s.count("</head>") == 1
s = s.replace("</head>", f"<script>window.KX_CHAT = {cfg};</script>\n</head>")
open(p, "w", encoding="utf-8").write(s)
PY
  echo "chat: on (${CHAT_ENDPOINT})"
else
  echo "chat: off (no CHAT_ENDPOINT or CHAT_TOKEN)"
fi
python3 -I analysis/build_site_template.py "$PWD/$SCRATCH/password_template.html"

# A fixed salt (analysis/tools/staticrypt.json, public, not secret) keeps "remember me" valid across rebuilds.
( cd "$SCRATCH" && ../../tools/node_modules/.bin/staticrypt index.html \
    --config ../staticrypt.json \
    --directory ../../../docs \
    --template password_template.html \
    --remember 30 --short \
    --template-title "KYC approval-rate diagnosis" \
    --template-instructions "Enter the password from the submission email." \
    --template-placeholder "Password" \
    --template-button "Open dashboard" \
    --template-remember "Remember on this device for 30 days" \
    --template-error "That password is not correct. Look at the submission email and try again." \
    --template-toggle-show "Show password" \
    --template-toggle-hide "Hide password" )

touch docs/.nojekyll
rm -rf "$SCRATCH"
! grep -q "$STATICRYPT_PASSWORD" docs/index.html analysis/tools/staticrypt.json || { echo "password leaked into an output file" >&2; exit 1; }
if [ -n "${CHAT_TOKEN:-}" ]; then
  ! grep -rq "$CHAT_TOKEN" docs analysis/export analysis/dashboard || { echo "chat token leaked into an unencrypted file" >&2; exit 1; }
fi
! grep -q "{{ \|/\*\[|" docs/index.html || { echo "unfilled template placeholder in docs/index.html" >&2; exit 1; }
ls -la docs
