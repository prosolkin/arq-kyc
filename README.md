# KYC approval-rate diagnosis (ARQ case study)

Why ARQ's KYC approval rate fell in August–September 2023, what the two extracts can and cannot measure, and what to do about it. Prepared as a case study for a Product Owner (ARQ Operating System) application, October 2026.

## Deliverables

| What | Where |
|---|---|
| Report (PDF): executive deck, evidence appendix, methodology and validation note | [`analysis/export/kyc-approval-report.pdf`](analysis/export/kyc-approval-report.pdf) |
| Quick review: the whole story on one page, with charts | first tab of the dashboard (`analysis/out/quick_review.csv`). Four main tabs (Quick review, Why it fell, What to do, What we gain); the rest sit under Details |
| Interactive dashboard, offline, one file | [`analysis/export/kyc-dashboard.html`](analysis/export/kyc-dashboard.html); also served password-protected on GitHub Pages (password in the submission email) |
| Deck as PowerPoint and PDF | [`kyc-approval-deck.pptx`](analysis/export/kyc-approval-deck.pptx), [`kyc-approval-deck.pdf`](analysis/export/kyc-approval-deck.pdf) |
| Methodology and validation note | [`analysis/export/methodology-and-validation.md`](analysis/export/methodology-and-validation.md) |
| Aggregated datasets behind every number (38 CSVs) | [`analysis/out/`](analysis/out/), described in [`manifest.json`](analysis/out/manifest.json) |

## What the analysis says

- Approval among recorded decisions fell from 88.7% to 83.3% between the two 30-day halves of the extract (−5.4 points).
- That is 2,945 fewer approvals: about 1,587 from lower volume and 1,358 from the lower rate.
- Starts, completion and abandonment are not in the data, so the brief's "start and finish" rate cannot be measured yet.
- Four reasons explain most of the change. They are more fraud signals (not adjudicated), execution errors on Sep 1–2, and selfie and liveness failures.
- The selfie and liveness failures match vendor incidents on Sep 1 and 6. The fourth reason is Mexican documents returned without a type.
- The plan starts with two weeks of measurement and stabilisation, then experiments. Recovery is given as scenarios, not forecasts.
- The value model runs on market-based presets; ARQ's own figures should replace them.

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
analysis/chat/                        the chat proxy (Cloudflare Worker), its rules and the case material
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

The build asserts the reconciliation checkpoints: approved counts, the −5.4 points, and the volume and rate effects. It records the SHA-256 hashes of both extracts. It stops the export if any record-level field or user reference is present.

## Ask about this case (chat)

The hosted dashboard has a chat above the tabs. Claude Opus 5.5 answers questions about the case from the case material only.

- `analysis/chat/build_chat_context.py` builds `analysis/chat/worker/case-material.md` from the same outputs as the dashboard. The whole file goes into the prompt, so no search index is necessary.
- `analysis/chat/worker/rules.md` holds the rules: questions about this case only, figures as given, facts apart from hypotheses, and short answers.
- `analysis/chat/worker/src/index.js` is a Cloudflare Worker. It holds the Anthropic key as a secret, and the page never sees the key.
- The Worker accepts only the dashboard's origin and an access token. The build adds that token only to the encrypted page.
- Limits: 6 questions a minute for each visitor, 100 a day in total, and 1,500 characters for each question.
- The offline file and the copy in this repository have no chat and make no requests.

### Log and notifications

The hosted page keeps a small log, so the author can see how readers use it and that the chat works. The footer of the hosted page tells readers about the log.

- The Worker writes each question, its answer, the status, the time and the token use to a D1 database. The schema is in `analysis/chat/worker/migrations/`.
- The page sends page views, tab changes and clicks to the same database. It sends the label of the clicked control, never typed text.
- A reader is a random id in the browser, with the city, country, network and browser that Cloudflare reports. The log keeps no names and no IP addresses.
- A daily job deletes rows older than 90 days (`RETENTION_DAYS`).
- A Telegram bot sends a message for each question and when a visitor opens the dashboard. To connect a bot, run `python3 -I analysis/chat/setup_telegram.py`.
- To read the log, run `python3 -I analysis/chat/show_log.py`. Add `chats 20`, `events 50` or `visitor <id>` for detail.

## What is deliberately not here

- The raw extracts `KYC_summary.csv` and `KYC_details.csv`: ARQ's data. Only aggregates are published.
- Personal data of any kind: the dashboard and the CSVs hold counts, rates and labels only.
- The password for the hosted dashboard.
- A draft public explainer written in ARQ's voice: unpublished, since every claim in it needs ARQ's confirmation.

## Notes on the files

- Chrome rendered the deck PDF and the visual checks from the slide specification. The `.pptx` passes a structural validator, but nobody opened it in PowerPoint, so table row heights can be slightly different there.
- Vendor research is dated 13 October 2026 and kept separate from the 2023 diagnosis; each row carries how it was verified.
- The organisation in the operating-model tab is role-based and assumed. It does not show people, headcount or who reports to whom.
