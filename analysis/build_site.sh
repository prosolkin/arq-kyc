#!/usr/bin/env bash
# Build docs/index.html: the offline dashboard, encrypted for GitHub Pages with StatiCrypt.
# The password comes only from the STATICRYPT_PASSWORD environment variable. It is never
# written to a file: the page holds a salt and the encrypted payload, nothing else.
# Run from the project root after analysis/export_html.py:
#     STATICRYPT_PASSWORD='...' bash analysis/build_site.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${STATICRYPT_PASSWORD:?set STATICRYPT_PASSWORD in the environment}"

SCRATCH="analysis/tools/.site-build"
rm -rf "$SCRATCH" && mkdir -p "$SCRATCH" docs
cp analysis/export/kyc-dashboard.html "$SCRATCH/index.html"

# A fixed salt (analysis/tools/staticrypt.json, public, not secret) keeps "remember me" valid across rebuilds.
( cd "$SCRATCH" && ../../tools/node_modules/.bin/staticrypt index.html \
    --config ../staticrypt.json \
    --directory ../../../docs \
    --remember 30 --short \
    --template-title "KYC approval-rate diagnosis" \
    --template-instructions "Case-study dashboard, aggregated 2023 data. Enter the password from the submission email." \
    --template-placeholder "Password" \
    --template-button "Open" \
    --template-remember "Remember on this device for 30 days" \
    --template-error "That password did not match." \
    --template-color-primary "#0F4C4D" \
    --template-color-secondary "#DCEAE9" )

touch docs/.nojekyll
rm -rf "$SCRATCH"
! grep -q "$STATICRYPT_PASSWORD" docs/index.html analysis/tools/staticrypt.json || { echo "password leaked into an output file" >&2; exit 1; }
ls -la docs
