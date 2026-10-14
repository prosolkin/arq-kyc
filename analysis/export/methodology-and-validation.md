# KYC approval-rate diagnosis: methodology and validation

Data: `KYC_summary.csv` and `KYC_details.csv`, 52,075 records each, Jul 25 – Sep 22, 2023. Vendor research dated 2026-10-13. Every figure below is read from `analysis/out/`, the same tables the dashboard and deck use.

## 1. What is measured

The brief defines the KYC pass rate as people who start and finish the process. The extracts hold one recorded decision per user, with a date and no time of day, and no record of starts, attempts or abandonment. The headline metric is therefore **approval among recorded decisions**: decisions whose final outcome (`KYC_summary.decision_type`) is PASSED or APPROVED, divided by all recorded decisions in the period. It is not the start-to-finish completion rate, and the extracts cannot say whether that rate is higher or lower.

| Metric | Status | Definition | Prior | Recent | Gap |
|---|---|---|---|---|---|
| KYC starts | Unavailable | People who open the KYC flow. | — | — | kyc_started with person id, session id, timestamp, country, app version, channel |
| Recorded decisions | Available | User records with a final decision in the extract (one per user_reference). | 26,932 | 25,143 | Whether a record is a first, latest or final attempt is not stated |
| Approval rate among recorded decisions | Available | Approved (PASSED or APPROVED) ÷ recorded decisions. The headline metric of this analysis. | 88.69% | 83.29% | Not the start-to-finish completion rate: starts, abandonment and attempts are missing |
| Rejection rate | Available | REJECTED ÷ recorded decisions. | 10.59% | 15.59% | — |
| Unresolved warning rate | Available | WARNING ÷ recorded decisions. Later review outcome not in the extract. | 0.72% | 1.12% | Review dispositions needed |
| Completion rate (start to terminal state) | Unavailable | Starts that reach a terminal state (approved, finally rejected, or abandoned for 7 days) within 7 days of start. | — | — | kyc_started, step events, terminal decision, abandonment rule |
| Eventual approval within 7 days | Unavailable | Starts approved on any attempt within 7 days of the first start. | — | — | Person id across attempts, attempt number, timestamps, review dispositions |
| Abandonment rate | Unavailable | Starts with no submission within 7 days. | — | — | kyc_started and kyc_submitted events |
| Retry rate and retry approval | Unavailable | Share of unsuccessful first attempts that retry, and their approval. | — | — | Attempt number per person |
| Manual-review outcomes | Unavailable | Approval and turnaround of cases sent to review. | — | — | Review queue events and dispositions |
| Time to completion | Unavailable | Median minutes from start to terminal decision. | — | — | Timestamps with time of day on start and decision |
| Execution-error rate | Available | Unsuccessful decisions whose primary reason is TECHNICAL_ERROR ÷ recorded decisions. | 0.00% | 1.62% | — |
| Fraud-signal rate | Available | Unsuccessful decisions whose primary reason is a manipulation or fake label ÷ recorded decisions. Not adjudicated. | 0.33% | 2.38% | Adjudication of a sample |

**Outcome treatment.** PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection); unsuccessful = rejected + warning. The 8 `OK` labels in the details file are label-only; the 1 record that is PASSED in the summary but REJECTED in details is counted as approved pending reconciliation. `PASSES` (3 values) is read as PASSED. Blank screening is "not recorded". NOT_EXECUTED with PRECONDITION_NOT_FULFILLED means an earlier check failed; with TECHNICAL_ERROR it is an execution error. Capability results are kept separate from the final outcome.

**Periods.** Prior period Jul 25 – Aug 23, 2023 and recent period Aug 24 – Sep 22, 2023: the two 30-day halves of the extract. Dates are those in `KYC_summary.date_`; which event they mark (submission, decision or export) is not stated.

## 2. Data validation

| Check | Result | Status | Treatment |
|---|---|---|---|
| Records in each extract | 52,075 summary / 52,075 details | Pass | Equal row counts. |
| Unique user_reference | 52,075 / 52,075 | Pass | No duplicate users in either file. |
| Join coverage on user_reference | 52,075 matched, 0 + 0 unmatched | Pass | Complete one-to-one join. |
| Date coverage | 2023-07-25 to 2023-09-22: 60 of 60 calendar days | Pass | No missing days. |
| Timestamp precision | 52,075 of 52,075 at midnight UTC | Limitation | Dates only. Intraday outage windows cannot be matched to records, and the extract does not say which event the date marks (submission, decision or export). |
| Final outcome categories (summary.decision_type) | PASSED 44,825, REJECTED 6,772, WARNING 474, APPROVED 4 | Pass | PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection). |
| decision_type vs details.decision_label | PASSED vs REJECTED: 1; PASSED vs OK: 8 | Note | summary.decision_type is treated as the outcome. The 8 'OK' labels are label-only; 1 record shows PASSED in the summary but REJECTED in details and is counted as approved, pending reconciliation. |
| Non-standard capability value 'PASSES' | 3 values | Note | Treated as PASSED. |
| Blank watchlist_screening_decision | 6,606 blank, 1 NOT_EXECUTED | Note | Shown as 'not recorded'. Mostly on rejected records; a blank field does not prove screening never ran elsewhere. |
| Blank data_type (no document type returned) | 3,781 records | Note | A symptom with several possible causes (unsupported document, capture, configuration, classification coverage). |
| Birth year extracted | 48,286 present, 3,789 blank; range 1909–2022 | Limitation | 3,769 of the 3,789 blanks are rejected records, so ages describe applicants whose document was read, not all applicants. Extreme years (e.g. 2022) suggest extraction errors. |
| Country field | MEX / ARG only (data_issuing_country) | Note | This is the document's issuing country, not necessarily residence or account market. |
| Attempts per user | 1 record per user_reference | Limitation | The extract does not say whether a record is the first, latest or final attempt; retries and later outcomes are not visible. |
| Raw files unchanged | summary 67e4190909b7…, details e0762f377a41… | Pass | SHA-256 prefixes, recomputed on every build. |

Reconciliation checkpoints, all reproduced by assertions in `build_datasets.py`: prior 26,932 decisions, 23,887 approved (88.69%); recent 25,143 decisions, 20,942 approved (83.29%); change −5.40 pp; approved count −2,945, of which −1,587 from lower volume at the prior rate and −1,358 from the lower rate. Mexican documents 84.09% → 78.85%; Argentine 94.87% → 89.13%.

## 3. Attribution of unsuccessful decisions

Each unsuccessful decision gets one primary reason: TECHNICAL_ERROR in any capability first, otherwise the first capability in vendor order (usability, image checks, extraction, data checks, liveness, face match) with REJECTED or WARNING, then a watchlist WARNING, then "no document type, no reason code" or "no failing check". Reasons are grouped into nine groups and four classes (fraud signal, execution error, capture or document issue, unexplained or identity mismatch). Classes describe who could act on the vendor's reason; they are not adjudicated causes. Because each decision has one primary reason, group effects sum to the total change. 298 recent unsuccessful decisions had two or more failing or warning checks, so fixing a primary reason does not by itself imply approval.

| Primary reason | Share prior | Share recent | Effect on approval | Above baseline in windows |
|---|---|---|---|---|
| Fraud signal | 0.33% | 2.38% | −2.05 pp | −1.90 pp |
| Execution error | 0.00% | 1.62% | −1.62 pp | −1.62 pp |
| Selfie / liveness | 1.68% | 2.62% | −0.95 pp | −0.69 pp |
| No document type, no reason code | 3.51% | 4.11% | −0.60 pp | +0.00 pp |
| Screen or paper copy | 0.29% | 0.63% | −0.34 pp | +0.00 pp |
| Unsupported or incomplete document | 1.96% | 2.13% | −0.17 pp | +0.00 pp |
| Other | 0.08% | 0.11% | −0.03 pp | +0.00 pp |
| Image quality | 0.69% | 0.70% | −0.01 pp | +0.00 pp |
| Face match | 2.77% | 2.41% | +0.36 pp | +0.00 pp |

Face match improved between the periods; it is a large existing loss, not a cause of the decrease.

## 4. Incident windows

A window is a date range, a country scope and a failure signature. Attributed failures = observed signature failures in the window − the count expected at the prior-period rate of that signature for the window's volume. Other failures on those days are not attributed. Records cannot be matched to intraday outages because all timestamps are midnight UTC.

| Window (2023) | Type | Observed | Expected | Above baseline | Of recent decisions | Of recent unsuccessful | Approval points |
|---|---|---|---|---|---|---|---|
| Argentina fraud-signal burst, Aug 24 | Suspected additional attack traffic | 376 | 2.9 | 373 | 1.48% | 8.9% | −1.48 pp |
| Execution errors at usability, Sep 1–2 | Technical failure affecting applicants | 407 | 0.1 | 407 | 1.62% | 9.7% | −1.62 pp |
| Liveness quality spike, Sep 1 and Sep 6 | Technical failure affecting applicants | 174 | 0.5 | 173 | 0.69% | 4.1% | −0.69 pp |
| Mexico INE fraud-signal cluster, Sep 14–19 | Fraud-signal cluster without extra volume | 111 | 7.0 | 104 | 0.41% | 2.5% | −0.41 pp |

Total above baseline 1,057 (25.2% of recent unsuccessful decisions, −4.20 pp of approval). Sensitivity across a ±1-day window, a broader signature and a recent-period baseline: 1,055–1,130. The earlier method (every matching failure, no baseline) gives 1,068. Removing the 1,068 selected failures from the recent period gives 86.99%; that is a descriptive rate after excluding selected records, not a counterfactual.

**Vendor evidence.** The vendor's public status history (monitor.jumio.com) was read on the research date. Source quality: primary vendor status page; some entries were read by a research sub-task and are marked as such.

| Date | UTC | Entry | Read | ARQ impact |
|---|---|---|---|---|
| 2023-09-01 | 15:38–16:42 | Liveness returned 'Unable to see your face properly' for all ID verification transactions. | Fetched (agent) | Not confirmed |
| 2023-09-01 | 18:07–22:44 | Same liveness message. Liveness restored 20:59; Authentication restored for new users only; resolved 22:44. | Fetched | Not confirmed |
| 2023-09-06 | 10:00–17:22 | Instability; workaround 11:25; liveness restored 16:21; resolved 17:22. | Fetched | Not confirmed |
| 2023-09-13 | 13:23–13:44 | Retry surge after a fix: V2 scans unavailable; Jumio Go customers may have seen extra 'unsupported document' rejections; Hybrid delays. | Fetched (agent) | Not confirmed |
| 2023-09-01 / 09-02 | — | No status entry mentions usability, TECHNICAL_ERROR or skipped document checks, and none is listed for Sep 2. | Fetched (agent) | Unknown: vendor or integration |
| 2023-08-24, 09-14 to 09-19 | — | No incidents listed for August 2023; only scheduled maintenance in Singapore during Sep 14–19. | Fetched (agent) | Not applicable |

A documented vendor incident is not confirmation of impact on ARQ: ARQ's data centre, product tier and transaction times are unknown. No vendor entry matches the Sep 1–2 TECHNICAL_ERROR pattern, so those errors could be the vendor's or ARQ's integration.

## 5. Recovery scenarios

Recovered approvals = observed population × eligibility × reach × return × remediation × subsequent approval. Observed populations are recent-period counts by primary reason and do not overlap. All other factors are assumptions, shown per scenario. For the selfie populations, eligibility is the observed share with no other failing check. Subsequent approval uses the prior-period approval rate for the same countries (checks that did not run could still fail), except the review queue, where a reviewer approval is final. Incident-type benefits are reported per comparable incident, not per month. Possible approval reversals from confirmed control findings are reported separately.

| Scenario | Recoverable per 30 days | Approval points | Recent rate with them | Per comparable incident |
|---|---|---|---|---|
| Conservative | 233 | +0.9 pp | 84.2% | 139 |
| Central | 634 | +2.5 pp | 85.8% | 295 |
| Optimistic | 1,093 | +4.3 pp | 87.6% | 435 |

If all control findings were confirmed, up to 580 recent approvals (−2.3 pp) might need reversing. These are scenarios built on stated assumptions, not forecasts; a target set from them is a goal, not a prediction.

## 6. Experiment sizing

Per-arm sample sizes use the normal approximation for two proportions (two-sided α = 0.05, power 0.80). Assignment is per person, so repeat attempts are not counted as independent users. Mexico document guidance: Using the recent submission-based Mexican approval rate (78.8%) as a stand-in baseline, about 6,314 people per arm (95% confidence, 80% power). At about 476 Mexican decisions a day that is roughly 27 days at a 50/50 split. Recompute once start-based data exists. Liveness retake: Assuming about 5% of the eligible group is approved later without a retake (not measurable yet), about 141 people per arm. At about 16 eligible people a day (recent non-incident rate) that is roughly 18 days. Needs the real baseline from instrumentation. Hold-and-retry for TECHNICAL_ERROR is remediation of a confirmed failure and is validated by acceptance criteria, not randomised.

## 7. Value model

Observed quantities (approved-count change, rate counterfactual, recoverable approvals per scenario, suspected extra attack traffic) are kept separate from the financial inputs: value per activated customer, activation rate, paid-channel share and cost, billable vendor transactions per decision and their cost, review cost, build and run cost. The inputs start from market-based presets derived in `analysis/value_presets.py` from published sources fetched on the research date. None is an ARQ figure; each should be replaced with ARQ's own number. Low, Mid and High are the low, middle and high values of each input's range, so a High preset raises costs as well as value. Cautious takes the end of each range that weakens the case. Results appear only when every required input is valid. Annualisation multiplies 30-day figures by 365/30; first-year cohort value is not revenue recognised in the next 12 months.

| Input | Low | Mid | High | Kind | Basis | Sources |
|---|---|---|---|---|---|---|
| Value per activated customer (USD) | $13 | $21 | $53 | Derived | Low: ARQ's reported US$10bn volume ÷ 2m users × 0.5% fee = $25 revenue a year, less $12 cost to serve (Nu México, $1 a month). Mid: Nu México ARPAC $12.50 × 12 × 40% first-year ramp (assumption) × 35.3% gross margin. High: the same without the ramp, an average Nu México customer. Not all reported volume carries the fee, and users are not all active. | S4 S5 S8 S9 |
| Activation rate after approval (%) | 38.2% | 56.3% | 83.0% | Proxy | Low: Liftoff LATAM activation rate 38.2%. Mid: Liftoff fintech activation rate 56.3% (2021–22 data; the source doesn't define activation). High: Nu's monthly activity rate of 83%, a ceiling set by a mature primary bank. None measures approved-to-active directly. | S6 S7 |
| Share of applicants from paid channels (%) | 29.0% | 40.0% | 50.0% | Proxy + assumption | Low: 29% of Nu's new Brazilian customers in 2025 were not sourced organically. High: Nu acquired more than 50% of Mexican customers through referrals, so other channels are under 50%. Mid: 40% (assumption). Not every non-organic channel is paid. | S6 |
| Acquisition cost per paid applicant (USD) | $8.74 | $17.96 | $29.93 | Derived | Low: Liftoff LATAM cost per install $1.60 ÷ 18.3% registration rate = $8.74 per registration. Mid: Liftoff fintech cost per registration $17.96. High: $17.96 ÷ 60% of registrants reaching KYC (assumption). 2021–22 data. | S7 |
| Billable vendor transactions per decision (count) | 1 | 1.2 | 1.5 | Assumption | Low: one billable transaction per decision. Mid and high: 1.2 and 1.5 with retries (assumption). Some vendors (Sumsub) charge only for successful verifications, which would make not-approved decisions free. | S2 |
| Vendor cost per billable transaction (USD) | $1.44 | $1.85 | $3 | List price / estimate | Low: Veriff Essential $0.80 + PEP and sanctions $0.64. Mid: Sumsub Compliance $1.85, which includes AML screening. High: top of Vendr's $1.50–$3.00 estimate for Jumio at 100,000–500,000 verifications a year; the extract annualises to about 316,790 decisions. Self-serve list prices; negotiated enterprise rates are usually lower. | S1 S2 S3 |
| Cost per manual review (USD) | $0.83 | $5.72 | $10.79 | Derived | Monthly gross salary × loaded factor ÷ MXN 18.3528 ÷ 140 productive hours × minutes per case × quality uplift. Low: MXN 11,236 (Paylab, lowest 10% of financial analysts) × 1.3, 8 min, ×1.1. Mid: MXN 39,608 (TalentUp KYC analyst median) × 1.35, 15 min, ×1.1. High: the same salary × 1.4, 25 min, ×1.2. Hours, minutes and uplift are assumptions. | S10 S11 S13 S14 |
| Implementation cost of the recurring-cause actions (USD) | $24,400 | $31,600 | $85,000 | Derived | Engineer-weeks × loaded weekly cost × team overhead. Weeks: 12 / 13 / 19.5, from the roadmap's effort for the four 30-day actions plus 2 weeks of review tooling; high adds a 50% overrun. Weekly cost: Levels.fyi median MX$1,146,490 ÷ 18.3528 × 1.3 or × 1.35 ÷ 52 ($1,562, $1,622); high uses Revelo's top fully loaded $126,000 ($2,423). Overhead for product, design, QA and vendor work: ×1.3 / ×1.5 / ×1.8 (assumption). | S12 S13 S14 |
| Run cost per month (USD) | $510 | $2,010 | $3,860 | Derived | Central scenario, per 30 days: 278 review-pilot cases × cost per review, plus about 191 guided selfie retakes × billable transactions × cost per transaction, using the same preset's values. Excludes support contacts and monitoring tools. | S1 S2 S3 S10 S11 |

Sources (fetched on the research date; status shows how each was obtained):

| ID | Source | Figure used | Period | Status |
|---|---|---|---|---|
| S1 | [Veriff: Pricing page, self-serve plans](https://www.veriff.com/pricing) | Essential $0.80, Plus $1.39, Premium $1.89 per verification; PEP and sanctions add-on +$0.64 | List prices, 13 Oct 2026 | Fetched |
| S2 | [Sumsub: Pricing and plans](https://sumsub.com/pricing/) | Basic $1.35 (ID, liveness, face match); Compliance $1.85 (adds AML screening) per verification; only successful verifications are charged | List prices, 13 Oct 2026 | Fetched |
| S3 | [Vendr: Jumio buyer guide](https://www.vendr.com/buyer-guides/jumio) | Estimated $1.50–$3.00 per verification at 100,000–500,000 a year; median contract $55,850 a year | Updated Feb 2026 | Fetched (third-party estimate) |
| S4 | [Nu Holdings: Nu México press release](https://nu.com/es/sala-de-prensa/compania/nu-mexico-espera-que-su-inversion-total-alcanzara-los-us-4-2-mil-millones-para-2030-a-medida-que-se-acerca-su-inicio-de-operaciones-como-banco) | Nu México ARPAC US$12.5 a month; cost to serve US$1 a month | Q3 2025, published 11 Feb 2026 | Fetched |
| S5 | [Nu Holdings: Form 6-K, Q1 2026 results](https://www.sec.gov/Archives/edgar/data/0001691493/000129281426003055/nu20260514_6k.htm) | Gross profit US$1,877.7m on revenue US$5,315.5m (managerial P&L), a 35.3% margin (derived) | Q1 2026 | Fetched |
| S6 | [Nu Holdings: Form 20-F, FY2025](https://www.sec.gov/Archives/edgar/data/1691493/000129281426002166/nuform20f_2025.htm) | Monthly activity rate 83%; 71% of new Brazilian customers in 2025 sourced organically; more than 50% of Mexican customers acquired through word-of-mouth referrals | 31 Dec 2025 | Fetched |
| S7 | [Liftoff, via MarTech Series: Mobile Finance Apps report](https://martechseries.com/mobile/new-liftoff-data-reveals-customers-flock-to-fintech-as-economy-tightens-offers-finance-app-marketers-guidance-on-user-acquisition/) | Fintech cost per registration $17.96 and activation rate 56.3%; LATAM cost per install $1.60, registration rate 18.3%, activation rate 38.2% | Data Jun 2021 – Jun 2022 | Fetched (secondary, dated) |
| S8 | [Bloomberg Línea: DolarApp raises US$70m and becomes ARQ](https://www.bloomberglinea.com/negocios/fintech-dolarapp-levanta-us70-millones-y-cambia-de-identidad-para-expansion-en-latinoamerica/) | More than 2 million users; more than US$10bn annualised transaction volume | 3 Mar 2026 | Fetched (press) |
| S9 | [Passageiro de Primeira: ARQ keeps a 0.5% fee on any conversion](https://passageirodeprimeira.com/sem-valor-minimo-arq-mantem-taxa-de-05-em-qualquer-conversao/) | 0.5% of the converted amount, no minimum | 28 Jul 2026 | Fetched (consumer site) |
| S10 | [TalentUp: KYC analyst salary, Mexico City](https://talentup.io/salary/KYC%20Analyst/mexico%20city) | Median gross MXN 475,300 a year | Not stated (2026 page) | Fetched |
| S11 | [Paylab: Financial analyst salary, banking, Mexico](https://www.paylab.com/mx/salaryinfo/banking/financial-analyst?lang=en) | Monthly gross: the lowest 10% earn under MXN 11,236 and the highest 10% over MXN 38,290; fewer than 20 verified respondents | Not stated | Fetched |
| S12 | [Levels.fyi: Senior software engineer, Mexico](https://www.levels.fyi/t/software-engineer/levels/senior/locations/mexico) | Median total compensation MX$1,146,490 a year (224 submissions) | Updated 13 Oct 2026 | Fetched (self-reported) |
| S13 | [Revelo: Hiring software developers in Mexico](https://www.revelo.com/blog/hire-software-developers-in-mexico) | Senior $66,000–$90,000 a year; fully loaded cost 1.3–1.4× salary (IMSS, Infonavit, aguinaldo, PTU), up to $126,000 | 3 Jul 2026 | Fetched (recruiter) |
| S14 | [Banco de México: FIX exchange rate](https://www.banxico.org.mx/tipcamb/tipCamMIAction.do?idioma=sp) | MXN 18.3528 per USD | 13 Oct 2026 | Fetched |

Results in the central scenario (634 recoverable approvals per 30 days):

| Result | Low | Mid | High | Cautious |
|---|---|---|---|---|
| Activated customers from recoverable approvals, per 30 days | 242 | 357 | 526 | 242 |
| First-year value of one 30-day cohort | $3,148 | $7,496 | $27,890 | $3,148 |
| Same, if every 30 days repeats for a year | $38,306 | $91,199 | $339,324 | $38,306 |
| Break-even first-year value per activated customer | $11 | $13 | $21 | $45 |
| Review cost per 30 days for the review-pilot population | $231 | $1,590 | $3,000 | $3,000 |
| Historical vendor spend on recent not-approved decisions | $6,049 | $9,326 | $18,905 | $6,049 |
| Vendor spend avoidable on suspected extra attack traffic | $492 | $759 | $1,539 | $492 |
| Historical paid acquisition spend on recent not-approved applicants | $10,648 | $30,180 | $62,868 | $10,648 |

Under the Cautious preset the actions do not pay back within the first year: break-even is $45 per activated customer against $13 of value. That is the case Finance should test first with ARQ's own figures.

## 8. Checks performed for this submission

- `build_datasets.py` asserts the reconciliation checkpoints, that class shares sum to the not-approved share, that process-step counts reconcile to all unsuccessful decisions, that every action has exactly one accountable role, and records SHA-256 hashes of both raw files on every run.
- Every number marked in the dashboard page resolves to a row in `analysis/out/` (checked by script); every table column exists in its dataset.
- The export embeds no `user_reference` values and no record-level columns (asserted in `export_html.py`), loads no network resources, and bundles d3 7.9.0.
- The regenerated export was tested in a browser: one tab and one audience panel visible at a time; tooltips hidden at rest and on pointer leave; country filter synchronised across its three views; sorting and search; scenario picker updating tiles, table and value model together; presets switching all inputs and results, with results matching `value_results.csv`; invalid and blank inputs showing "Needs …" instead of stale values; keyboard tab navigation; no horizontal overflow at 375 px; no console errors; print to PDF with all tabs, details and charts rendered.
- Alert rules replayed on the extract fire on the first day of all four windows (5 rule-days fire in the prior period and need tuning).
- The PowerPoint passes the pptx skill's structural validator; its text was checked with markitdown; every slide was rendered from the shared slide specification and inspected.

## 9. Open questions for ARQ

These are not asked in the submission. They are the answers that would change the findings, in the order they matter; each says what changes with the answer.

| # | Question | Why it matters | What the answer changes | Who would know |
|---|---|---|---|---|
| 1 | Does each row hold a user's first, latest or final KYC attempt, and does the date mark the submission or the vendor's decision? | The headline is approval among recorded decisions. If rows are latest attempts, earlier failures and retries are invisible and the first-pass rate is lower than shown; if they are final decisions, the warnings may be stale. | The metric definition (v2 to v3 in the registry), the retry hypotheses, and whether the bridge counts people or attempts. | Data platform or whoever produced the extract. |
| 2 | Is there any record, even weekly counts, of people who opened KYC and never submitted? | The brief defines the pass rate as people who start and finish. Without starts, completion and abandonment can't be measured, and the 1,587 fewer approvals from lower volume could be fewer starts, more abandonment, or both. | Whether Phase 0 instrumentation is a prerequisite or a check on existing data; the reading of the volume effect; the completion metric's status. | Mobile and platform engineering (app analytics, API logs). |
| 3 | What happens today after a TECHNICAL_ERROR or a liveness failure: does the user see the vendor's outcome, get a retake, or enter a review queue? | Hold-and-retry and the guided retake assume no retry exists. In the central scenario they recover 242 approvals per comparable execution-error incident and 78 per 30 days on steady liveness failures. | If a retry already exists, those recoverable counts shrink and the question becomes why retries fail; the Phase 0 hold-and-retry becomes a configuration check. | Product and the onboarding squad; the vendor integration owner. |
| 4 | Which vendor product tier and data centre does ARQ use, and did ARQ receive incident notices for Sep 1, 2 and 6, 2023? | The vendor's status history shows liveness incidents on Sep 1 and 6 on its US data centre and nothing for Sep 2. The liveness spike is 173 failures above baseline and the execution errors 407. | On another data centre the liveness attribution loses its vendor evidence; with notices, the execution errors have an owner and an SLA claim. | Vendor management; the vendor's account team. |

## 10. Limitations and unresolved dependencies

- Starts, abandonment, attempts, review outcomes, account state and times of day are not in the extracts; completion and eventual approval are unavailable until the Phase 0 events exist.
- Whether a record is a first, latest or final attempt, and what event its date marks, is unknown; recent cohorts may be immature.
- Fraud signals are not adjudicated; execution errors are not attributed; vendor incident impact on ARQ is unconfirmed.
- Birth year is extracted data with outcome-related missingness; ages describe people whose document was read.
- Country is the document issuing country.
- ARQ's current flow (retries, review, upload policy, architecture, vendor product tier) is unknown; the target design and roadmap mark these as discovery questions or conditions.
- Effort sizes, scenario factors and the role-based organisation are assumptions. The value-model presets come from public prices, salaries and benchmarks for other companies (several dated or third-party estimates), not from ARQ's contracts or finance data.
- The deck's PDF companion and the visual QA images were rendered from the HTML version of the shared slide specification with Chrome, because no PowerPoint or LibreOffice renderer was available. The .pptx itself was validated structurally but not opened in PowerPoint; table row heights may differ slightly there.

## 11. Reproduce

```bash
bash analysis/build_all.sh
```

This runs `build_datasets.py`, `export_html.py`, `build_notes.py` and `tools/build_deck.mjs`, then prints the deck PDF with headless Chrome. The tools in `analysis/tools/package.json` are pinned (d3 7.9.0, pptxgenjs 3.12.0).
