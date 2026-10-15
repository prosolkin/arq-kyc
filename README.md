# KYC approval-rate diagnosis (ARQ case study)

Why ARQ's KYC approval rate fell in August–September 2023, what the two extracts can and cannot measure, and what to do about it. Prepared as a case study for a Product Owner (ARQ Operating System) application, October 2026.

**Start here**

- **Interactive version:** [prosolkin.github.io/arq-kyc](https://prosolkin.github.io/arq-kyc/). The password is in the submission email.
- **Report (PDF, 36 pages):** [`kyc-approval-report.pdf`](analysis/export/kyc-approval-report.pdf). It has the executive deck, the evidence appendix and the methodology and validation note.

## Deliverables

| What | Where |
|---|---|
| Report (PDF): executive deck, evidence appendix, methodology and validation note | [`analysis/export/kyc-approval-report.pdf`](analysis/export/kyc-approval-report.pdf) |
| Interactive dashboard, hosted | [prosolkin.github.io/arq-kyc](https://prosolkin.github.io/arq-kyc/), with the password from the submission email. The first of the four main tabs is a Quick review: the whole story on one page, with charts. |
| Interactive dashboard, offline, one file | [`analysis/export/kyc-dashboard.html`](analysis/export/kyc-dashboard.html). Download it and open it in a browser; it works without a network. GitHub shows its source code, not the page. |
| Deck as PowerPoint and PDF | [`kyc-approval-deck.pptx`](analysis/export/kyc-approval-deck.pptx), [`kyc-approval-deck.pdf`](analysis/export/kyc-approval-deck.pdf) |
| Methodology and validation note | [`analysis/export/methodology-and-validation.md`](analysis/export/methodology-and-validation.md) |
| Aggregated datasets behind every number (42 CSV tables) | [`analysis/out/`](analysis/out/), described in [`manifest.json`](analysis/out/manifest.json) |

## What the analysis says

- Approval among recorded decisions fell from 88.7% to 83.3% between the two 30-day halves of the extract (−5.4 points).
- That is 2,945 fewer approvals: about 1,587 from fewer decisions and 1,358 from the lower rate.
- The brief describes a start-to-finish rate. The extracts have no starts, attempts or abandonment, so that rate needs new events first.
- Four reasons explain most of the change:
  - fraud signals: −2.05 points (signals, not confirmed fraud);
  - execution errors on Sep 1–2: −1.62 points;
  - selfie and liveness failures: −0.95 points, at the same time as vendor incidents on Sep 1 and 6;
  - Mexican documents with no document type: −0.60 points.
- Face match failures decreased (+0.36 points), so they did not cause the drop.
- About 1,057 failures sit above baseline in four short date windows (range 1,055–1,130). Their causes are not confirmed. Without the 10 incident days, the rate still fell by 1.45 points.
- The plan has four tracks: fix and measure, test the fixes, learn why, and build later. It starts with two weeks of measurement and stabilisation.
- If the tests work, the rate recovers about 2.5 points (range 0.9 to 4.3). These are scenarios, not forecasts. The value model uses market benchmarks until ARQ's own figures replace them.

## Where the analysis is

Read it in this order.

1. The [methodology and validation note](analysis/export/methodology-and-validation.md). It gives the definitions, the data checks, the attribution method, the incident windows, the scenarios, the experiment sizes, the value model and the limits.
2. The tables in [`analysis/out/`](analysis/out/). GitHub shows each CSV file as a table. Start with these:

| Table | What it holds |
|---|---|
| [`kpis.csv`](analysis/out/kpis.csv) | Headline figures and reconciliation checkpoints |
| [`bridge.csv`](analysis/out/bridge.csv) | Change in the approval rate by primary reason |
| [`declines.csv`](analysis/out/declines.csv) | Not-approved decisions by group and class |
| [`incidents.csv`](analysis/out/incidents.csv) | Four incident windows: observed, expected and above-baseline counts |
| [`daily.csv`](analysis/out/daily.csv) | Decisions and approvals per day and document country |
| [`hypotheses.csv`](analysis/out/hypotheses.csv) | Hypotheses with evidence, alternatives and next steps |
| [`actions.csv`](analysis/out/actions.csv) | The plan: each action with its track, phase, owner role and acceptance criteria |
| [`scenario_totals.csv`](analysis/out/scenario_totals.csv) | Recovery scenarios |
| [`value_results.csv`](analysis/out/value_results.csv) | Value-model results for each preset and scenario |
| [`open_questions.csv`](analysis/out/open_questions.csv) | Questions to confirm with ARQ, and what each answer changes |

3. The code. [`analysis/build_datasets.py`](analysis/build_datasets.py) computes every number. Its `main()` has one section for each topic. The sections go from data validation and the daily series to incidents, the decomposition, scenarios, the value model and the Quick review. The script asserts the key figures, so a wrong number stops the build.

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
analysis/chat/                        the chat about the case (a Cloudflare Worker), its rules and the case material
analysis/check_writing.py   plain-language checks on every text a reader sees
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

### Product analytics

The hosted page records anonymous product analytics: page views, tab changes, clicks, and the chat questions with their answers. The footer of the page says so. A reader is a random id in the browser. The log keeps no names and no IP addresses, and it deletes rows older than 90 days.

## What is deliberately not here

- The raw extracts `KYC_summary.csv` and `KYC_details.csv`: ARQ's data. Only aggregates are published.
- Personal data of any kind: the dashboard and the CSVs hold counts, rates and labels only.
- The password for the hosted dashboard.
- A draft public explainer written in ARQ's voice: unpublished, since every claim in it needs ARQ's confirmation.

## Notes on the files

- Chrome renders the deck PDF from the same slide specification as the `.pptx`. The `.pptx` passes a structural validator. Table row heights in PowerPoint can differ slightly from the PDF.
- Vendor research is dated 13 October 2026 and kept separate from the 2023 diagnosis; each row carries how it was verified.
- The organisation in the operating-model tab is role-based and assumed. It does not show people, headcount or who reports to whom.
