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
! grep -q "{{ \|/\*\[|" docs/index.html || { echo "unfilled template placeholder in docs/index.html" >&2; exit 1; }
ls -la docs
