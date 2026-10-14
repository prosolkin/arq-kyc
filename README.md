# KYC approval-rate diagnosis (ARQ case study)

Why ARQ's KYC approval rate fell in August–September 2023, what is and isn't measurable in the two extracts provided, and what to do about it. Prepared as a case study for a Product Owner (ARQ Operating System) application, October 2026.

## Deliverables

| What | Where |
|---|---|
| Report (PDF): executive deck, evidence appendix, methodology and validation note | [`analysis/export/kyc-approval-report.pdf`](analysis/export/kyc-approval-report.pdf) |
| Quick review: the whole story on one page, in ASD-STE100 Simplified Technical English | first tab of the dashboard (`analysis/out/quick_review.csv`) |
| Interactive dashboard, offline, one file | [`analysis/export/kyc-dashboard.html`](analysis/export/kyc-dashboard.html); also served password-protected on GitHub Pages (password in the submission email) |
| Deck as PowerPoint and PDF | [`kyc-approval-deck.pptx`](analysis/export/kyc-approval-deck.pptx), [`kyc-approval-deck.pdf`](analysis/export/kyc-approval-deck.pdf) |
| Methodology and validation note | [`analysis/export/methodology-and-validation.md`](analysis/export/methodology-and-validation.md) |
| Aggregated datasets behind every number (38 CSVs) | [`analysis/out/`](analysis/out/), described in [`manifest.json`](analysis/out/manifest.json) |

## What the analysis says, in one paragraph

Approval among recorded decisions fell from 88.7% to 83.3% between the two 30-day halves of the extract (−5.4 points, 2,945 fewer approvals: about 1,587 from lower volume, 1,358 from the lower rate). Starts, completion and abandonment are not in the data, so the brief's "start and finish" rate can't be measured yet. Four reasons explain most of the change: more fraud signals (not adjudicated), execution errors on Sep 1–2, selfie and liveness failures that match vendor incidents on Sep 1 and 6, and Mexican documents returned without a type. The plan starts with two weeks of measurement and stabilisation, then experiments; recovery is given as scenarios, not forecasts, and the value model runs on market-based presets that ARQ's own figures should replace.

## How it was built

One script computes every number; the dashboard, the deck and the note read its output, so nothing is copied by hand.

```
analysis/build_datasets.py   raw extracts -> analysis/out/*.csv (aggregates only) + manifest.json
analysis/vendor_research.py  vendor status-page evidence and capability research, with fetch status
analysis/value_presets.py    market-based presets for the value model, with sources
analysis/export_html.py      dashboard page + d3 + datasets -> one offline HTML file
analysis/tools/build_deck.mjs  slide spec -> .pptx (pptxgenjs) and an HTML render for the PDF
analysis/build_notes.py      methodology note (markdown)
analysis/build_report.py     deck PDF + note -> report PDF
analysis/build_site.sh       encrypted copy of the dashboard for GitHub Pages (docs/)
analysis/site/password_template.html  the password page: the deck's title slide, animated
analysis/build_site_template.py       fills that page's headline, chart and figures from analysis/out
analysis/build_all.sh        runs all of the above
```

### Reproduce

Needs Python 3, Node, Google Chrome (for the PDFs) and [uv](https://docs.astral.sh/uv/) (for two pinned Python packages).

```bash
# 1. place the two extracts at the repository root (they are not in this repo)
#    KYC_summary.csv  KYC_details.csv
# 2. install the pinned build tools once
(cd analysis/tools && npm ci)
# 3. build everything
bash analysis/build_all.sh
```

The build asserts the reconciliation checkpoints (approved counts, the −5.4 points, the volume and rate effects), records the SHA-256 hashes of both extracts, and refuses to export the dashboard if any record-level field or user reference is present.

## What is deliberately not here

- The raw extracts `KYC_summary.csv` and `KYC_details.csv`: ARQ's data. Only aggregates are published.
- Personal data of any kind: the dashboard and the CSVs hold counts, rates and labels only.
- The password for the hosted dashboard.
- A draft public explainer written in ARQ's voice: unpublished, since every claim in it needs ARQ's confirmation.

## Notes on the files

- The deck PDF and the visual checks were rendered from the slide specification with Chrome; the `.pptx` passes a structural validator but was not opened in PowerPoint, so table row heights may differ slightly there.
- Vendor research is dated 13 October 2026 and kept separate from the 2023 diagnosis; each row carries how it was verified.
- The organisation in the operating-model tab is role-based and assumed; no people, headcount or reporting lines are implied.
