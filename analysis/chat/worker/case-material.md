# Case material: KYC approval-rate diagnosis (ARQ case study)

This is the full material behind the dashboard, the deck and the report. Sections follow the dashboard tabs. Numbers are exact as built from the two 2023 extracts (Jul 25 – Sep 22, 2023). Vendor research is dated Oct 13, 2026.

Where things are on the dashboard:

- Quick review: the short story with its charts.
- Why it fell: the reasons for not-approved decisions by class, the Mexico "no document type" breakdown, face match, the checks block by block, and the failure mix by week.
- What to do: the plan in phases and in four tracks, and every action with its owner, evidence and acceptance criteria. The research and vendor bake-off actions are here.
- What we gain: the recovery scenarios and the value model, with its inputs, results, presets and sources.
- Full summary (under Details): the answer, what to confirm with the team, the daily approval rate, what moved the rate, and what it means for each audience.
- Measurement (under Details): what can and cannot be measured, the metric definitions, the data validation, and the events needed to measure the funnel.
- Incidents (under Details): the four date windows with unusual failures, their counts, the sensitivity of the attribution, and the vendor's status-page evidence.
- Hypotheses & tests (under Details): the main hypotheses, how to test them, and the experiment designs.
- Operating model (under Details): the KPI registry, ownership, who does what, the operating rhythm, alerts, access and adoption.
- Target design (under Details): the requirements, scale, components, session states, and build or buy.
- Vendor research (under Details): the vendor's capabilities today against the 2023 problems, and the changes since 2023.
- Reference (under Details): the open questions for ARQ, the control findings, the risk register, common questions, a glossary and the method in short.

## Tab: Quick review


### The result

The KYC pass rate decreased by 5.4 points in the last 30 days: from 88.7% to 83.3%.
- Relative decrease: 6.1%.
- Approved people: 12.3% fewer (2,945 people).
- Of the drop, 54% is because of fewer decisions and 46% is because of the lower rate.
- By country: Mexico from 84.1% to 78.8%, Argentina from 94.9% to 89.1%.
Pass rate here = approved decisions ÷ all recorded decisions. The data cannot show the people who started KYC and did not finish.

### What the data can show
The data has one decision record for each person, with a date. It does not show when a person starts KYC.
Because of this, we cannot measure the completion rate. We measure the pass rate of recorded decisions.
CAUTION: Do not report this pass rate as the completion rate.

### Why it fell

Of the 4,201 not-approved decisions, 40% are unexplained or identity mismatches and 36% are capture or document problems. Fraud signals are 14% and execution errors are 10%.
Four reasons give most of the decrease. The second chart shows how much each reason moved the pass rate.
- Fraud signals: −2.05 points. The vendor found more images that look altered or fake.
- Execution errors: −1.62 points. On Sep 1–2, some checks did not run, and the system rejected these people.
- Selfie and liveness failures: −0.95 points. The vendor status page shows liveness incidents on Sep 1 and Sep 6.
- Mexican documents with no document type: −0.60 points. The vendor did not identify these documents.
Face match failures decreased (+0.36 points). But face match is still 14% of the not-approved decisions.
CAUTION: A fraud signal is not confirmed fraud. Do not call it fraud before an analyst examines it.

### Short incidents

We found about 1,057 more failures than usual in four short date windows (range 1,055 to 1,130).
- Aug 24, Argentina: more fraud signals and more traffic than usual.
- Sep 1–2: execution errors in both countries.
- Sep 1 and Sep 6: liveness failures.
- Sep 14–19, Mexico: more fraud signals, with usual traffic.
Without the 10 incident days, the pass rate still decreased by 1.45 points. These days hold 38% of the recent decisions. We keep them and show both views.
The causes of these incidents are not confirmed. The vendor status page does not show an incident on Sep 2.

### What to do
The plan has four tracks, the same as on the What to do tab. The first three tracks start now and run at the same time. The obvious fixes go first because they are cheap to try. The fourth track is the platform work for later.
- [Fix and measure] Record each KYC start, each step and each final decision.
- [Fix and measure] Hold each decision that has a TECHNICAL_ERROR. Do the check again before you reject the person.
- [Fix and measure] Set alerts for sudden increases in failures. Compare the control findings with the source systems.
- [Fix and measure] If the fraud is confirmed, add device checks before the vendor call.
- [Test the fixes] Test one guided retake for unclear selfies.
- [Test the fixes] In Mexico, show pictures of the accepted documents before the capture.
- [Learn why] Examine a sample of fraud signals. Find which signals are real fraud.
- [Learn why] Ask the vendor for incident reports for Sep 1, Sep 2 and Sep 6.
- [Learn why] Talk to people who failed the capture. Start with support tickets, then interviews, then session replays, then eye tracking if the budget permits.
- [Learn why] Decide on the vendor: if the vendor cannot explain Sep 1, 2 and 6, test a second vendor.
- [Build later] Build a KYC orchestration and decision layer.
- [Build later] Add government registry checks (INE, RENAPER).
- [Build later] Add a second verification vendor for failover.

### What we gain

If the tests work, the pass rate increases by about 2.5 points (range 0.9 to 4.3).
That is about 634 more approved people each 30 days (range 233 to 1,093).
These numbers come from scenarios. They are not forecasts.

### Money
The value model has no ARQ numbers. It uses benchmark values from 14 public sources: vendor price lists, Nu Holdings filings, Liftoff reports and Mexican salary data.
- Middle benchmarks: the actions pay back in the first year. Each active customer gives $21 of value for $13 of cost.
- Cautious benchmarks: the actions do not pay back in the first year. Each active customer gives $13 of value for $45 of cost.
CAUTION: Replace the benchmark values with ARQ values before you make a decision.

### Questions for ARQ
- Does each row show the first attempt, the last attempt or the final decision?
- Does ARQ have records of people who started KYC but did not send their documents?
- What does the app do after a TECHNICAL_ERROR or a liveness failure?
- Which vendor product and which data centre does ARQ use?
The answers can change the results of this review.

## Tab: Why it fell

Key figures:

| Figure | Value |
|---|---|
| First day in the extract | 2023-07-25 |
| First day of the recent period | 2023-08-24 |
| Last day of the prior period | 2023-08-23 |
| Last day in the extract | 2023-09-22 |
| Days in the extract | 60 |
| Vendor research date | 2026-10-13 |
| Recorded decisions | 52075 |
| Recorded decisions, prior period | 26932 |
| Recorded decisions, recent period | 25143 |
| Approved, prior period | 23887 |
| Approved, recent period | 20942 |
| Approval rate, prior period | 0.8869 |
| Approval rate, recent period | 0.8329 |
| Change in approval rate | -5.4 |
| Change in approved count | -2945 |
| Approved-count change from lower volume (at the prior rate) | -1587 |
| Approved-count change from the lower rate | -1358 |
| Not approved, prior period | 3045 |
| Not approved, recent period | 4201 |
| Not-approved share, prior period | 0.1131 |
| Not-approved share, recent period | 0.1671 |
| Warnings, prior period | 193 |
| Warnings, recent period | 281 |
| Rejected, recent period | 3920 |
| Mexico approval rate, prior period | 0.8409 |
| Mexico approval rate, recent period | 0.7885 |
| Argentina approval rate, prior period | 0.9487 |
| Argentina approval rate, recent period | 0.8913 |
| Mexican-document share of decisions, prior period | 0.5726 |
| Mexican-document share of decisions, recent period | 0.5681 |
| Unsuccessful decisions matching an incident signature in its window | 1068 |
| Recent approval rate after removing those records (descriptive only) | 0.8699 |
| Prior-period approval rate without incident days | 0.8869 |
| Recent-period approval rate without incident days | 0.8724 |
| Change in approval rate without incident days | -1.45 |
| Share of recent decisions that fall on incident days | 0.3782 |
| Incident days in the recent period | 10 |
| Relative change in the approval rate | -0.0609 |
| Relative change in the approved count | -0.1233 |
| Share of the approved-count change from lower volume | 0.5388 |
| Share of the approved-count change from the lower rate | 0.4612 |
| Incident failures above baseline (base estimate) | 1057 |
| Incident failures above baseline, low end of sensitivity range | 1055 |
| Incident failures above baseline, high end of sensitivity range | 1130 |
| Every failure of the same pattern in the windows (old method) | 1068 |
| Base incident estimate as a share of recent unsuccessful decisions | 0.2516 |
| Base incident estimate as approval-rate points | -4.2 |
| Recent unsuccessful decisions with two or more failed or warning checks | 298 |
| Liveness-spike cases that also had a face-match warning or rejection | 44 |
| Liveness-spike cases | 174 |
| Execution-error cases with liveness passed | 407 |
| Execution-error cases with screening passed | 251 |
| Mexican decisions with no document type, prior period | 0.1133 |
| Mexican decisions with no document type, recent period | 0.1424 |
| Argentine usability rejections or warnings | 0 |
| Mexican usability rejections or warnings | 1442 |
| Face-match share of decisions, prior period | 0.0277 |
| Face-match share of decisions, recent period | 0.0241 |
| Records with no birth year that were rejected | 3769 |
| Records with no birth year | 3789 |
| Average decisions per day | 868 |
| Most decisions in one day | 1331 |

Change in the approval rate by primary reason (points; they add up to the total change):

| Reason | Class | Effect (pp) | In incident windows (pp) | Rest (pp) |
|---|---|---|---|---|
| Fraud signal | Fraud signal (not adjudicated) | -2.05 | -1.9 | -0.15 |
| Execution error | Execution error | -1.62 | -1.62 | 0.0 |
| Selfie / liveness | Capture or document issue | -0.95 | -0.69 | -0.26 |
| No document type, no reason code | Unexplained or identity mismatch | -0.6 | 0.0 | -0.6 |
| Screen or paper copy | Capture or document issue | -0.34 | 0.0 | -0.34 |
| Unsupported or incomplete document | Capture or document issue | -0.17 | 0.0 | -0.17 |
| Other | Unexplained or identity mismatch | -0.03 | 0.0 | -0.03 |
| Image quality | Capture or document issue | -0.01 | 0.0 | -0.01 |
| Face match | Unexplained or identity mismatch | 0.36 | 0.0 | 0.36 |

Not-approved decisions by class:

| Class | Prior count | Recent count | Share of not approved, prior | Share of not approved, recent |
|---|---|---|---|---|
| Fraud signal (not adjudicated) | 88 | 598 | 0.0289 | 0.1423 |
| Execution error | 1 | 407 | 0.0003 | 0.0969 |
| Capture or document issue | 1243 | 1529 | 0.4082 | 0.364 |
| Unexplained or identity mismatch | 1713 | 1667 | 0.5626 | 0.3968 |

## Tab: Incidents (under Details)

| Window | When | Type | Observed | Expected | Above baseline | Approval points |
|---|---|---|---|---|---|---|
| Argentina fraud-signal burst | Aug 24 | Suspected additional attack traffic | 376 | 2.9 | 373 | -1.48 |
| Execution errors at usability | Sep 1–2 | Technical failure that affected applicants | 407 | 0.1 | 407 | -1.62 |
| Liveness quality spike | Sep 1 and Sep 6 | Technical failure that affected applicants | 174 | 0.5 | 173 | -0.69 |
| Mexico INE fraud-signal cluster | Sep 14–19 | Fraud-signal cluster without extra volume | 111 | 7.0 | 104 | -0.41 |

Vendor status-page evidence:

| Date | UTC | Entry | Read | ARQ impact |
|---|---|---|---|---|
| 2023-09-01 | 15:38–16:42 | Liveness returned 'Unable to see your face properly' for all ID verification transactions. | Fetched (agent) | Not confirmed |
| 2023-09-01 | 18:07–22:44 | Same liveness message. Liveness restored 20:59; Authentication restored for new users only; resolved 22:44. | Fetched | Not confirmed |
| 2023-09-06 | 10:00–17:22 | Instability; workaround 11:25; liveness restored 16:21; resolved 17:22. | Fetched | Not confirmed |
| 2023-09-13 | 13:23–13:44 | Retry surge after a fix: V2 scans unavailable; Jumio Go customers possibly saw extra 'unsupported document' rejections; Hybrid delays. | Fetched (agent) | Not confirmed |
| 2023-09-01 / 09-02 |  | No status entry mentions usability, TECHNICAL_ERROR or skipped document checks, and none is listed for Sep 2. | Fetched (agent) | Unknown: vendor or integration |
| 2023-08-24, 09-14 to 09-19 |  | No incidents listed for August 2023; only scheduled maintenance in Singapore during Sep 14–19. | Fetched (agent) | Not applicable |

## Tab: Hypotheses & tests (under Details)

| ID | Hypothesis | Evidence | Alternatives | Still needed | Next step | Decision it enables |
|---|---|---|---|---|---|---|
| h_exec | Execution errors on Sep 1–2 turned applicants into rejections | 407 TECHNICAL_ERROR rejections on two days in both countries. Usability NOT_EXECUTED; document checks and face match skipped; liveness passed in all 407; screening passed in 251. | A vendor incident; an ARQ integration or configuration fault (upload, file format, credentials); a network problem between ARQ and the vendor. | ARQ request logs, raw vendor responses, vendor incident report, whether these people retried or were later approved. | Pull logs and raw responses for both days; ask the vendor for an incident report; check later activity of the affected users. | Whether the fault is ours or the vendor's (fix, SLA claim, or both). The hold-and-retry rule is useful in both cases. |
| h_liveness | Liveness quality failures on Sep 1 and Sep 6 were caused by a vendor fault | 174 BAD_QUALITY / FACE_NOT_FULLY_VISIBLE on two days, both countries, codes rare otherwise; a third-party copy of the vendor status page reports liveness incidents on these dates. | An ARQ app release or capture change on those days; an SDK version change. | App and SDK version per transaction; intraday timestamps; vendor confirmation that ARQ's region was affected. | Compare with the release log; ask the vendor for the affected-transaction list. | Whether to escalate commercially, and whether a retake policy for these codes is worth a test. |
| h_attack | The Aug 24 Argentina burst was coordinated fraud | Argentine volume 660 vs a typical 318; 376 manipulation signals; 373 passed liveness and 373 passed face match. | A wave of false positives from the vendor model at the time of a marketing push; a campaign that attracted low-quality applicants; duplicate submissions. | Adjudication of a sample, device and IP data, acquisition channel, cross-transaction links. | Review a random sample of flagged cases; check acquisition channel for the day; ask the vendor about repeated faces or backgrounds. | Whether to add pre-vendor velocity and device controls, and how to report attack traffic separately. |
| h_ine | The Sep 14–19 Mexico INE flags reflect a vendor rule or model change | 111 manipulation signals on INE cards with no volume surge (2826 vs 2994 typical); 111 passed liveness. | A quieter fraud campaign; a new INE card version the model mis-scores. | Vendor release notes for that week; adjudication of a sample; registry validation of the credentials. | Sample review with the vendor; registry check on a sample if available. | Whether INE flags should route to review instead of auto-decline. |
| h_mex_docs | Mexico's higher 'no document type' share comes from document choice or capture, not one defect | No document type returned for 11.3% of Mexican decisions in the prior period and 14.2% in the recent one. Argentina has almost none. 1,034 recent Mexican rejections have no reason code. | Documents outside the accepted list; poor captures the vendor cannot classify; issuer-country mismatch; document configuration; vendor gaps for some INE versions. | Image sample with the vendor, the document type the user selected, the accepted-document configuration, app version. | Review 100 recent cases with the vendor; compare configuration history; split by app version once logged. | Choose between a document picker, a configuration change or a vendor escalation. |
| h_face | Face-match failures are a large problem from before the drop, partly from old ID photos | Face match was 2.77% of prior-period decisions and 2.41% of recent ones: it improved, so it did not cause the drop. Mexican national ID cards fail face match more often than INE cards. | Impostors; poor light on the selfie; card type. | Adjudication of a sample; document issue date. | Review a sample of NO_MATCH and NOT_POSSIBLE cases. | Whether a review queue or registry face check is worth its cost; any threshold change needs risk validation. |

Experiment designs:

| ID | Kind | Hypothesis | Population | Primary outcome | Window | Sample | Guardrails |
|---|---|---|---|---|---|---|---|
| exp_mex_docs | Optimisation experiment | Pictures of the accepted documents, shown to Mexican applicants before capture, increase eventual approval. | People who start KYC with a Mexican document. Exclude staff and test accounts, and people already approved. | Eventual approval within 7 days of first start. | 7 days per person plus 7 days to mature the last cohort. | With the recent Mexican approval rate (78.8%) as a stand-in baseline, the sample is about 6,314 people per arm (95% confidence, 80% power). At about 476 Mexican decisions a day that is roughly 27 days at a 50/50 split. Recompute once start-based data exists. | Start-to-submit rate, time to decision, fraud-signal rate, support contacts. |
| exp_liveness | Optimisation experiment | One guided retake after BAD_QUALITY or FACE_NOT_FULLY_VISIBLE from liveness increases eventual approval and does not increase fraud. | People whose first liveness result is BAD_QUALITY or FACE_NOT_FULLY_VISIBLE and who have no fraud signal. Exclude ID_USED_AS_SELFIE and any manipulation label. | Eventual approval within 7 days of the failure. | 7 days plus 7 days to mature. | If about 5% of the eligible group is approved later without a retake (not measurable yet), the sample is about 141 people per arm. At about 16 eligible people a day (recent non-incident rate) that is roughly 18 days. Needs the real baseline from instrumentation. | Fraud-signal rate and confirmed fraud among retake approvals, liveness spoof labels, vendor cost per approval, time to decision. |
| exp_exec_errors | Remediation of a confirmed failure (not an A/B test) | If we hold and retry decisions with TECHNICAL_ERROR, execution faults do not cause final rejections. | All decisions with NOT_EXECUTED / TECHNICAL_ERROR in any capability. | Share of TECHNICAL_ERROR cases resolved after retry, and their eventual approval within 7 days. | Every incident; reviewed weekly. | Not applicable. Compare with the same incident type before the change. | Retry volume and vendor cost, time to decision, approvals among retried cases that later show fraud. |
| exp_review | Capacity-limited pilot | A manual review of face-match WARNINGs approves a large share of genuine applicants, with acceptable quality. | Face-match WARNING (NOT_POSSIBLE) cases with no fraud signal; later a sample of NO_MATCH. | Reviewer approval rate and 7-day eventual approval. | 4 weeks. | Capacity first: recent volumes are small enough for a pilot (see Plan), but cost per review and service level need Ops input. | Second-reviewer agreement on 10% of cases, review turnaround, later fraud among approvals. |

## Tab: What to do

| Phase | Label |
|---|---|
| 0 | Phase 0 · Weeks 0–2 · Measure and stabilise |
| 1 | Phase 1 · Weeks 2–6 · Test the main fixes |
| 2 | Phase 2 · Weeks 6–13 · Scale what works |
| 3 | Phase 3 · Next two quarters · Platform work (large) |

| Track | Meaning |
|---|---|
| Fix and measure | Obvious fixes and the instruments to see them work. Cheap, start now. |
| Test the fixes | Hypotheses that are quick to try as experiments. |
| Learn why | Investigations and research that run beside the fixes. |
| Build later | Platform work that needs a quarter or more. |

| Phase | Track | Action | What | Accountable (role) | Effort (assumed) | Done when | Condition |
|---|---|---|---|---|---|---|---|
| 0 | Fix | Minimum funnel instrumentation | Emit the nine KYC events (start, document, selfie, submission, vendor result, decision, review, account state) with person, session and attempt ids and app/SDK version. | Data & Analytics | M (assumed 3–4 engineer-weeks across backend and mobile) | Events for 99% of sessions in a daily reconciliation against vendor transactions; dashboards show first cohort. |  |
| 0 | Fix | Hold and retry on TECHNICAL_ERROR | Treat NOT_EXECUTED / TECHNICAL_ERROR as non-final. Retry with backoff, up to three times. Then hold the case for a manual decision; do not record a rejection. | Engineering · Onboarding platform | S (assumed 1–2 engineer-weeks) | Zero final rejections with TECHNICAL_ERROR over 4 weeks; 95% of held cases resolved within 24 hours. |  |
| 0 | Fix | Daily, then hourly, alerts per reason code | Alert on the approval rate and on each reason code per country, against its usual level. Page the team that owns it. | Data & Analytics | S (assumed 1 engineer-week) | On replay, alerts fire on the first day of every incident window. False alerts in the prior period stay under one a week. |  |
| 0 | Fix | Reconcile the control findings | Check three groups of approvals. 1,223 have a birth year of 2006 or later, 86 have no screening result and 69 have a screening warning. Compare each with the policy, the raw responses, the review dispositions and the account state. | Compliance | S (assumed 1–2 analyst-weeks) | Every record classified (confirmed, explained, data error) with evidence. |  |
| 0 | Learn | Adjudicate a sample of fraud signals | Review a random sample of the Aug 24 Argentina and Sep 14–19 Mexico flags; pull channel, device and cross-transaction data. | Risk & Fraud | S (assumed 1 analyst-week) | At least 50 cases per cluster adjudicated with documented rationale. |  |
| 0 | Learn | Diagnose 'no document type' in Mexico | Review 100 recent Mexican cases with no document type with the vendor; compare the accepted-document configuration over time. | Product · Onboarding | S (assumed 1–2 weeks) | Each sampled case assigned a cause with vendor agreement. |  |
| 0 | Learn | Confirm vendor incident scope | Ask the vendor for incident reports for Sep 1, 2 and 6, 2023, and the affected ARQ transactions. Check ARQ's release log for those days. | Vendor management | S | Written vendor confirmation or denial per date. | Any SLA credit depends on the contract and on confirmed scope. |
| 0 | Fix | Report the headline with its breakdown | Keep the headline approval rate on all decisions, and show fraud-signal, execution-error and warning shares beside it. | Data & Analytics | S | Weekly report adopted by the funnel review. |  |
| 1 | Test | Test one guided retake on unclear selfies | When liveness returns BAD_QUALITY or FACE_NOT_FULLY_VISIBLE, offer one retake with tips about light and position. | Product · Onboarding | M (assumed 3 engineer-weeks) | Experiment readout against its primary outcome and guardrails. | Only if vendor rules permit retakes for these labels. |
| 1 | Test | Test accepted-document guidance in Mexico | Show accepted Mexican documents with pictures before capture and block clearly unsupported choices. | Product · Onboarding | M (assumed 3–4 engineer-weeks plus design) | Experiment readout. | Only if the diagnosis points to document choice rather than configuration or vendor coverage. |
| 1 | Fix | Velocity and device checks before the vendor call | Rate-limit by device and network and block known-bad devices before a vendor transaction is created. | Risk & Fraud | M (assumed 3–5 engineer-weeks) | False-block rate on a holdout below an agreed threshold. | Depends on adjudication that confirms coordinated fraud. |
| 1 | Learn | Watch and ask people who failed the capture | Start with support tickets and vendor case images. Then do 8–10 remote interviews and unmoderated capture tests. Add session replay and eye tracking only if questions stay open. | Product · Onboarding | S–M (assumed 1 researcher-week per rung) | Written causes ranked by frequency, each with a ticket, clip or image as evidence. | Interviews and tests depend on consent; the costlier rungs on budget. |
| 1 | Learn | Decide on the vendor: bake-off on a sample | If the vendor cannot explain Sep 1, 2 and 6, or cannot support retakes, test a second vendor. Run it in shadow mode on a sample and compare the decisions. | Vendor management | M (assumed 2–3 engineer-weeks plus commercial time) | Side-by-side approval, false-reject and latency figures on the same sample. | Only if the vendor does not answer in Phase 0, or the answers are not sufficient. |
| 2 | Test | On-device capture quality checks | Use auto-capture with blur and glare checks and a retake prompt; restrict uploads if the current flow allows them. | Engineering · Mobile | M (assumed 4 engineer-weeks) | Experiment readout. | Camera-only capture depends on the current flow, and on whether uploads are the cause. |
| 2 | Test | Pilot manual review of face-match warnings | Send face-match WARNINGs, and later a sample of NO_MATCH, to trained reviewers. | Operations · KYC review | M (process plus tools) | Pilot readout with quality agreement. | Requires a capacity and quality plan. Any threshold change requires risk validation. |
| 2 | Fix | Invite recoverable applicants back | Message people declined for execution errors or capture issues with a retry link and tips for their reason. | Growth & Marketing | S | Return and approval rates measured per category. | Only for appropriate recoverable categories and with consent. |
| 3 | Build | KYC orchestration and decision layer | A service between the app and the vendors. It owns session state, retries, versioned rules per country, the route to review, and events. | Engineering · Onboarding platform | L (multi-team, a quarter or more) | Parity with the current flow, then rule changes without app releases. | Depends on what the current architecture already provides. |
| 3 | Build | Government registry checks (INE, RENAPER) | Validate credentials and faces against national registries where the vendor offers it. | Vendor management | L (commercial plus integration) | Pilot on a sample with measured agreement. | Requires integration and commercial work. |
| 3 | Build | Second verification vendor for failover | Add a second vendor behind the orchestration layer for outages and leverage. | Vendor management | L | Failover drill passes with parity on approval rate. | Requires integration and commercial work. |

Qualitative research budget ladder (assumptions). This is the detail behind the action "Watch and ask people who failed the capture". The dashboard shows it in short form in that action:

| Budget | Method | What it answers | When |
|---|---|---|---|
| No budget | Support tickets, app analytics, vendor case images | Which failures people complain about; what the vendor saw on the image | Week 1 |
| Low | 8–10 remote interviews; unmoderated capture tests on the real flow | Why people choose the wrong document or fail the selfie | Weeks 1–3 |
| Medium | Session replay on the capture screens; a one-week diary study in Mexico | Where people hesitate, retry or quit; what happens at home, not in a lab | Weeks 2–4 |
| High | Lab usability sessions with eye tracking on the capture screens | What people look at before a bad capture; whether the guidance is seen | Weeks 3–6 |

## Tab: What we gain

| Scenario | Approvals per 30 days | Points | Recent rate with them | Per comparable incident | Possible reversals |
|---|---|---|---|---|---|
| Conservative | 233 | 0.93 | 0.8422 | 139 | -580 |
| Central | 634 | 2.52 | 0.8581 | 295 | -580 |
| Optimistic | 1093 | 4.35 | 0.8764 | 435 | -580 |

Value model inputs (market benchmarks, not ARQ figures):

| Input | Unit | Low | Mid | High | Basis |
|---|---|---|---|---|---|
| Value per activated customer | USD | 13 | 21 | 53 | ARQ press figures; Nu México revenue and margin |
| Activation rate after approval | share | 0.382 | 0.563 | 0.83 | Liftoff LATAM and fintech activation; Nu activity rate |
| Share of applicants from paid channels | share | 0.29 | 0.4 | 0.5 | Nu organic and word-of-mouth shares |
| Acquisition cost per paid applicant | USD | 8.74 | 17.96 | 29.93 | Liftoff cost per install and per registration |
| Billable vendor transactions per decision | count | 1 | 1.2 | 1.5 | Assumption; replace with invoiced transactions ÷ decisions |
| Vendor cost per billable transaction | USD | 1.44 | 1.85 | 3 | Veriff and Sumsub list prices; Vendr estimate for Jumio |
| Cost per manual review | USD | 0.83 | 5.72 | 10.79 | Mexico analyst salaries × time per case |
| Implementation cost of the repeated-cause actions | USD | 24400 | 31600 | 85000 | Roadmap effort × Mexico engineering cost |
| Run cost per month | USD | 510 | 2010 | 3860 | Review cases and retake vendor calls, central scenario |

Value model results, central scenario:

| Preset | Result | Value |
|---|---|---|
| Low | Activated customers from recoverable approvals, per 30 days | 242 |
| Low | First-year value of one 30-day cohort | 3148.44 |
| Low | Same, if every 30 days repeats for a year | 38306.07 |
| Low | Historical vendor spend on recent not-approved decisions | 6049.44 |
| Low | Vendor spend avoidable on suspected extra attack traffic | 492.48 |
| Low | Historical paid acquisition spend on recent not-approved applicants | 10647.85 |
| Low | Review cost per 30 days for the review-pilot population | 230.74 |
| Low | Break-even first-year value per activated customer | 10.5 |
| Mid | Activated customers from recoverable approvals, per 30 days | 357 |
| Mid | First-year value of one 30-day cohort | 7495.78 |
| Mid | Same, if every 30 days repeats for a year | 91198.68 |
| Mid | Historical vendor spend on recent not-approved decisions | 9326.22 |
| Mid | Vendor spend avoidable on suspected extra attack traffic | 759.24 |
| Mid | Historical paid acquisition spend on recent not-approved applicants | 30179.98 |
| Mid | Review cost per 30 days for the review-pilot population | 1590.16 |
| Mid | Break-even first-year value per activated customer | 13.01 |
| High | Activated customers from recoverable approvals, per 30 days | 526 |
| High | First-year value of one 30-day cohort | 27889.66 |
| High | Same, if every 30 days repeats for a year | 339324.2 |
| High | Historical vendor spend on recent not-approved decisions | 18904.5 |
| High | Vendor spend avoidable on suspected extra attack traffic | 1539.0 |
| High | Historical paid acquisition spend on recent not-approved applicants | 62867.96 |
| High | Review cost per 30 days for the review-pilot population | 2999.62 |
| High | Break-even first-year value per activated customer | 20.8 |
| Cautious | Activated customers from recoverable approvals, per 30 days | 242 |
| Cautious | First-year value of one 30-day cohort | 3148.44 |
| Cautious | Same, if every 30 days repeats for a year | 38306.07 |
| Cautious | Historical vendor spend on recent not-approved decisions | 6049.44 |
| Cautious | Vendor spend avoidable on suspected extra attack traffic | 492.48 |
| Cautious | Historical paid acquisition spend on recent not-approved applicants | 10647.85 |
| Cautious | Review cost per 30 days for the review-pilot population | 2999.62 |
| Cautious | Break-even first-year value per activated customer | 45.19 |

Sources of the value model inputs (shown under Sources on this tab):

| ID | Publisher | Title | Figure | Period | Status |
|---|---|---|---|---|---|
| S1 | Veriff | Pricing page, self-serve plans | Essential $0.80, Plus $1.39, Premium $1.89 per verification; PEP and sanctions add-on +$0.64 | List prices, 13 Oct 2026 | Fetched |
| S2 | Sumsub | Pricing and plans | Basic $1.35 (ID, liveness, face match); Compliance $1.85 (adds AML screening) per verification; only successful verifications are charged | List prices, 13 Oct 2026 | Fetched |
| S3 | Vendr | Jumio buyer guide | Estimated $1.50–$3.00 per verification at 100,000–500,000 a year; median contract $55,850 a year | Updated Feb 2026 | Fetched (third-party estimate) |
| S4 | Nu Holdings | Nu México press release | Nu México ARPAC US$12.5 a month; cost to serve US$1 a month | Q3 2025, published 11 Feb 2026 | Fetched |
| S5 | Nu Holdings | Form 6-K, Q1 2026 results | Gross profit US$1,877.7m on revenue US$5,315.5m (managerial P&L), a 35.3% margin (derived) | Q1 2026 | Fetched |
| S6 | Nu Holdings | Form 20-F, FY2025 | Monthly activity rate 83%; 71% of new Brazilian customers in 2025 sourced organically; more than 50% of Mexican customers acquired through word-of-mouth referrals | 31 Dec 2025 | Fetched |
| S7 | Liftoff, via MarTech Series | Mobile Finance Apps report | Fintech cost per registration $17.96 and activation rate 56.3%; LATAM cost per install $1.60, registration rate 18.3%, activation rate 38.2% | Data Jun 2021 – Jun 2022 | Fetched (secondary, dated) |
| S8 | Bloomberg Línea | DolarApp raises US$70m and becomes ARQ | More than 2 million users; more than US$10bn annualised transaction volume | 3 Mar 2026 | Fetched (press) |
| S9 | Passageiro de Primeira | ARQ keeps a 0.5% fee on any conversion | 0.5% of the converted amount, no minimum | 28 Jul 2026 | Fetched (consumer site) |
| S10 | TalentUp | KYC analyst salary, Mexico City | Median gross MXN 475,300 a year | Not stated (2026 page) | Fetched |
| S11 | Paylab | Financial analyst salary, banking, Mexico | Monthly gross: the lowest 10% earn under MXN 11,236 and the highest 10% over MXN 38,290; fewer than 20 verified respondents | Not stated | Fetched |
| S12 | Levels.fyi | Senior software engineer, Mexico | Median total compensation MX$1,146,490 a year (224 submissions) | Updated 13 Oct 2026 | Fetched (self-reported) |
| S13 | Revelo | Hiring software developers in Mexico | Senior $66,000–$90,000 a year; fully loaded cost 1.3–1.4× salary (IMSS, Infonavit, aguinaldo, PTU), up to $126,000 | 3 Jul 2026 | Fetched (recruiter) |
| S14 | Banco de México | FIX exchange rate | MXN 18.3528 per USD | 13 Oct 2026 | Fetched |

## Tab: Reference (under Details)

Open questions for ARQ:

| Question | Why it matters | What the answer changes | Who would know |
|---|---|---|---|
| Does each row hold a user's first, latest or final KYC attempt, and does the date mark the submission or the vendor's decision? | The headline is approval among recorded decisions. If rows are latest attempts, we cannot see earlier failures and retries, and the first-pass rate is lower than shown. If rows are final decisions, the warnings can be out of date. | The metric definition (v2 to v3 in the registry), the retry hypotheses, and whether the bridge counts people or attempts. | Data platform or whoever produced the extract. |
| Is there any record, even weekly counts, of people who opened KYC and never submitted? | The brief defines the pass rate as people who start and finish. Without starts, completion and abandonment cannot be measured, and the 1,587 fewer approvals from lower volume could be fewer starts, more abandonment, or both. | Whether Phase 0 instrumentation is a prerequisite or a check on current data; how we read the volume effect; the completion metric status. | Mobile and platform engineering (app analytics, API logs). |
| What happens today after a TECHNICAL_ERROR or a liveness failure: does the user see the vendor's outcome, get a retake, or enter a review queue? | Hold-and-retry and the guided retake assume no retry exists. In the central scenario they recover 242 approvals per comparable execution-error incident and 78 per 30 days on steady liveness failures. | If a retry already exists, those recoverable counts shrink and the question becomes why retries fail; the Phase 0 hold-and-retry becomes a configuration check. | Product and the onboarding squad; the vendor integration owner. |
| Which vendor product tier and data centre does ARQ use, and did ARQ receive incident notices for Sep 1, 2 and 6, 2023? | The vendor's status history shows liveness incidents on Sep 1 and 6 on its US data centre and nothing for Sep 2. The liveness spike is 173 failures above baseline and the execution errors 407. | On another data centre the liveness attribution loses its vendor evidence; with notices, the execution errors have an owner and an SLA claim. | Vendor management; the vendor's account team. |

Control findings in the extract (to reconcile, not confirmed failures):

| Finding | Records | Detail |
|---|---|---|
| Approved records with birth year 2006 or later | 1223 | 1,152 with an Argentine document. If the extracted birth year is right, the person was under 18 in 2023. |
| Approved records with no screening result in the extract | 86 | Watchlist field blank (85) or NOT_EXECUTED (1). |
| Approved records with a watchlist WARNING | 69 | A potential match that should be resolved before approval. |
| Outcome disagrees between the two files | 9 | 8 'OK' labels on approved records; 1 approved in the summary but REJECTED in details. |
| Non-standard capability values | 3 | 'PASSES' instead of 'PASSED' in 3 fields. |

## Method and validation (the methodology note in the report)

# KYC approval-rate diagnosis: methodology and validation

Data: `KYC_summary.csv` and `KYC_details.csv`, 52,075 records each, Jul 25 – Sep 22, 2023. Vendor research dated 2026-10-13. Every figure below is read from `analysis/out/`, the same tables the dashboard and deck use.

### 1. What is measured

The brief defines the KYC pass rate as people who start and finish the process. The extracts hold one recorded decision per user, with a date and no time of day, and no record of starts, attempts or abandonment. The headline metric is therefore **approval among recorded decisions**. It is the number of decisions with a final outcome (`KYC_summary.decision_type`) of PASSED or APPROVED, divided by all recorded decisions in the period. It is not the start-to-finish completion rate, and the extracts cannot say whether that rate is higher or lower.

| Metric | Status | Definition | Prior | Recent | Gap |
|---|---|---|---|---|---|
| KYC starts | Unavailable | People who open the KYC flow. | — | — | kyc_started with person id, session id, timestamp, country, app version, channel |
| Recorded decisions | Available | User records with a final decision in the extract (one per user_reference). | 26,932 | 25,143 | Whether a record is a first, latest or final attempt is not stated |
| Approval rate among recorded decisions | Available | Approved (PASSED or APPROVED) ÷ recorded decisions. The headline metric of this analysis. | 88.69% | 83.29% | Not the start-to-finish completion rate: starts, abandonment and attempts are not in the data |
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

**Outcome treatment.** PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection); unsuccessful = rejected + warning. The 8 `OK` labels in the details file are label-only. The 1 record that is PASSED in the summary but REJECTED in details counts as approved until it is reconciled.

`PASSES` (3 values) is read as PASSED. Blank screening is "not recorded". NOT_EXECUTED with PRECONDITION_NOT_FULFILLED means an earlier check failed; with TECHNICAL_ERROR it is an execution error. Capability results are kept separate from the final outcome.

**Periods.** Prior period Jul 25 – Aug 23, 2023 and recent period Aug 24 – Sep 22, 2023: the two 30-day halves of the extract. Dates are those in `KYC_summary.date_`; which event they mark (submission, decision or export) is not stated.

### 2. Data validation

| Check | Result | Status | Treatment |
|---|---|---|---|
| Records in each extract | 52,075 summary / 52,075 details | Pass | Equal row counts. |
| Unique user_reference | 52,075 / 52,075 | Pass | No duplicate users in either file. |
| Join coverage on user_reference | 52,075 matched, 0 + 0 unmatched | Pass | Complete one-to-one join. |
| Date coverage | 2023-07-25 to 2023-09-22: 60 of 60 calendar days | Pass | All days are present. |
| Timestamp precision | 52,075 of 52,075 at midnight UTC | Limitation | Dates only. Intraday outage windows cannot be matched to records, and the extract does not say which event the date marks (submission, decision or export). |
| Final outcome categories (summary.decision_type) | PASSED 44,825, REJECTED 6,772, WARNING 474, APPROVED 4 | Pass | PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection). |
| decision_type vs details.decision_label | PASSED vs REJECTED: 1; PASSED vs OK: 8 | Note | summary.decision_type is treated as the outcome. The 8 'OK' labels are label-only; 1 record shows PASSED in the summary but REJECTED in details. We count it as approved until it is reconciled. |
| Non-standard capability value 'PASSES' | 3 values | Note | Treated as PASSED. |
| Blank watchlist_screening_decision | 6,606 blank, 1 NOT_EXECUTED | Note | Shown as 'not recorded'. Mostly on rejected records; a blank field does not prove screening never ran elsewhere. |
| Blank data_type (no document type returned) | 3,781 records | Note | A symptom with several possible causes (unsupported document, capture, configuration, classification coverage). |
| Birth year extracted | 48,286 present, 3,789 blank; range 1909–2022 | Limitation | 3,769 of the 3,789 blanks are rejected records, so ages describe applicants whose document was read, not all applicants. Extreme years (e.g. 2022) suggest extraction errors. |
| Country field | MEX / ARG only (data_issuing_country) | Note | This is the country that issued the document. It is not always the residence or the account market. |
| Attempts per user | 1 record per user_reference | Limitation | The extract does not say whether a record is the first, latest or final attempt; retries and later outcomes are not visible. |
| Raw files unchanged | summary 67e4190909b7…, details e0762f377a41… | Pass | SHA-256 prefixes, recomputed on every build. |

Reconciliation checkpoints. Assertions in `build_datasets.py` reproduce each one:

- Prior period: 26,932 decisions, 23,887 approved (88.69%).
- Recent period: 25,143 decisions, 20,942 approved (83.29%).
- Change: −5.40 pp. Approved count −2,945: −1,587 from lower volume at the prior rate, −1,358 from the lower rate.
- Mexican documents 84.09% → 78.85%; Argentine 94.87% → 89.13%.

### 3. Attribution of unsuccessful decisions

Each unsuccessful decision gets one primary reason. TECHNICAL_ERROR in any capability comes first. Otherwise it is the first capability with REJECTED or WARNING, in vendor order: usability, image checks, extraction, data checks, liveness, face match. Then come a watchlist WARNING, "no document type, no reason code" and "no failed check". Reasons are grouped into nine groups and four classes (fraud signal, execution error, capture or document issue, unexplained or identity mismatch). Classes describe who could act on the vendor's reason; they are not adjudicated causes.

Because each decision has one primary reason, group effects sum to the total change. 298 recent unsuccessful decisions had two or more failed or warning checks, so a fix for the primary reason does not by itself mean approval.

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

Face match improved between the periods. It is a large loss from before the drop, not a cause of the decrease.

### 4. Incident windows

A window is a date range, a country scope and a failure signature. Attributed failures = observed signature failures in the window − the count expected at the prior-period rate of that signature for the window's volume. Other failures on those days are not attributed. Records cannot be matched to intraday outages because all timestamps are midnight UTC.

| Window (2023) | Type | Observed | Expected | Above baseline | Of recent decisions | Of recent unsuccessful | Approval points |
|---|---|---|---|---|---|---|---|
| Argentina fraud-signal burst, Aug 24 | Suspected additional attack traffic | 376 | 2.9 | 373 | 1.48% | 8.9% | −1.48 pp |
| Execution errors at usability, Sep 1–2 | Technical failure that affected applicants | 407 | 0.1 | 407 | 1.62% | 9.7% | −1.62 pp |
| Liveness quality spike, Sep 1 and Sep 6 | Technical failure that affected applicants | 174 | 0.5 | 173 | 0.69% | 4.1% | −0.69 pp |
| Mexico INE fraud-signal cluster, Sep 14–19 | Fraud-signal cluster without extra volume | 111 | 7.0 | 104 | 0.41% | 2.5% | −0.41 pp |

Total above baseline 1,057 (25.2% of recent unsuccessful decisions, −4.20 pp of approval). Sensitivity across a ±1-day window, a broader signature and a recent-period baseline: 1,055–1,130. The earlier method (every failure of the pattern, no baseline) gives 1,068. Without the 1,068 selected failures, the recent rate is 86.99%. That is a descriptive rate, not a counterfactual.

Without the 10 incident days, the recent rate is 87.2% against 88.7% before: −1.45 pp. Those days hold 37.8% of recent decisions, so they are kept in the headline; the dashboard shows both views.

**Vendor evidence.** The vendor's public status history (monitor.jumio.com) was read on the research date. Source quality: primary vendor status page; some entries were read by a research sub-task and are marked as such.

| Date | UTC | Entry | Read | ARQ impact |
|---|---|---|---|---|
| 2023-09-01 | 15:38–16:42 | Liveness returned 'Unable to see your face properly' for all ID verification transactions. | Fetched (agent) | Not confirmed |
| 2023-09-01 | 18:07–22:44 | Same liveness message. Liveness restored 20:59; Authentication restored for new users only; resolved 22:44. | Fetched | Not confirmed |
| 2023-09-06 | 10:00–17:22 | Instability; workaround 11:25; liveness restored 16:21; resolved 17:22. | Fetched | Not confirmed |
| 2023-09-13 | 13:23–13:44 | Retry surge after a fix: V2 scans unavailable; Jumio Go customers possibly saw extra 'unsupported document' rejections; Hybrid delays. | Fetched (agent) | Not confirmed |
| 2023-09-01 / 09-02 | — | No status entry mentions usability, TECHNICAL_ERROR or skipped document checks, and none is listed for Sep 2. | Fetched (agent) | Unknown: vendor or integration |
| 2023-08-24, 09-14 to 09-19 | — | No incidents listed for August 2023; only scheduled maintenance in Singapore during Sep 14–19. | Fetched (agent) | Not applicable |

A documented vendor incident is not confirmation of impact on ARQ: ARQ's data centre, product tier and transaction times are unknown. No vendor entry matches the Sep 1–2 TECHNICAL_ERROR pattern, so those errors could be the vendor's or ARQ's integration.

### 5. Recovery scenarios

Recovered approvals = observed population × eligibility × reach × return × remediation × subsequent approval. Observed populations are recent-period counts by primary reason and do not overlap. All other factors are assumptions, shown per scenario. For the selfie populations, eligibility is the observed share with no other failed check.

Subsequent approval uses the prior-period approval rate for the same countries, because checks that did not run could still fail. The review queue is the exception: a reviewer approval is final. Incident-type benefits are reported per comparable incident, not per month. Possible approval reversals from confirmed control findings are reported separately.

| Scenario | Recoverable per 30 days | Approval points | Recent rate with them | Per comparable incident |
|---|---|---|---|---|
| Conservative | 233 | +0.9 pp | 84.2% | 139 |
| Central | 634 | +2.5 pp | 85.8% | 295 |
| Optimistic | 1,093 | +4.3 pp | 87.6% | 435 |

If all control findings were confirmed, up to 580 recent approvals (−2.3 pp) we might need to reverse. These are scenarios built on stated assumptions, not forecasts; a target set from them is a goal, not a prediction.

### 6. Experiment sample sizes

Per-arm sample sizes use the normal approximation for two proportions (two-sided α = 0.05, power 0.80). Assignment is per person, so repeat attempts do not count as independent users.

Mexico document guidance. With the recent Mexican approval rate (78.8%) as a stand-in baseline, the sample is about 6,314 people per arm (95% confidence, 80% power). At about 476 Mexican decisions a day that is roughly 27 days at a 50/50 split. Recompute once start-based data exists.

Liveness retake. If about 5% of the eligible group is approved later without a retake (not measurable yet), the sample is about 141 people per arm. At about 16 eligible people a day (recent non-incident rate) that is roughly 18 days. Needs the real baseline from instrumentation.

Hold-and-retry for TECHNICAL_ERROR is remediation of a confirmed failure and is validated by acceptance criteria, not randomised.

### 7. Value model

The model keeps two kinds of numbers apart. Observed quantities come from the data: the approved-count change, the rate counterfactual, recoverable approvals per scenario and suspected extra attack traffic. Financial inputs come from outside the data: value and activation per customer, paid-channel share and cost, vendor cost, review cost, and build and run cost.

The inputs start from market-based presets derived in `analysis/value_presets.py` from published sources fetched on the research date. None is an ARQ figure; each should be replaced with ARQ's own number. 

Low, Mid and High are the low, middle and high values of each range, so a High preset raises costs as well as value. Cautious takes the weaker end of each range. Results appear only when every required input is valid. The annual figure multiplies 30-day figures by 365/30. First-year cohort value is not revenue recognised in the next 12 months.

| Input | Low | Mid | High | Kind | Basis | Sources |
|---|---|---|---|---|---|---|
| Value per activated customer (USD) | $13 | $21 | $53 | Derived | Low: ARQ's reported US$10bn volume ÷ 2m users × 0.5% fee = $25 revenue a year, less $12 cost to serve (Nu México, $1 a month). Mid: Nu México ARPAC $12.50 × 12 × 40% first-year ramp (assumption) × 35.3% gross margin. High: the same without the ramp, an average Nu México customer. Not all reported volume carries the fee, and users are not all active. | S4 S5 S8 S9 |
| Activation rate after approval (%) | 38.2% | 56.3% | 83.0% | Proxy | Low: Liftoff LATAM activation rate 38.2%. Mid: Liftoff fintech activation rate 56.3% (2021–22 data; the source does not define activation). High: Nu's monthly activity rate of 83%, a ceiling set by a mature primary bank. None measures approved-to-active directly. | S6 S7 |
| Share of applicants from paid channels (%) | 29.0% | 40.0% | 50.0% | Proxy + assumption | Low: 29% of Nu's new Brazilian customers in 2025 were not sourced organically. High: Nu acquired more than 50% of Mexican customers through referrals, so other channels are under 50%. Mid: 40% (assumption). Not every non-organic channel is paid. | S6 |
| Acquisition cost per paid applicant (USD) | $8.74 | $17.96 | $29.93 | Derived | Low: Liftoff LATAM cost per install $1.60 ÷ 18.3% registration rate = $8.74 per registration. Mid: Liftoff fintech cost per registration $17.96. High: $17.96 ÷ 60% of registrants who reach KYC (assumption). 2021–22 data. | S7 |
| Billable vendor transactions per decision (count) | 1 | 1.2 | 1.5 | Assumption | Low: one billable transaction per decision. Mid and high: 1.2 and 1.5 with retries (assumption). Some vendors (Sumsub) charge only for successful verifications, which would make not-approved decisions free. | S2 |
| Vendor cost per billable transaction (USD) | $1.44 | $1.85 | $3 | List price / estimate | Low: Veriff Essential $0.80 + PEP and sanctions $0.64. Mid: Sumsub Compliance $1.85, which includes AML screening. High: top of Vendr's $1.50–$3.00 estimate for Jumio at 100,000–500,000 verifications a year; the extract annualises to about 316,790 decisions. Self-serve list prices; negotiated enterprise rates are usually lower. | S1 S2 S3 |
| Cost per manual review (USD) | $0.83 | $5.72 | $10.79 | Derived | Monthly gross salary × loaded factor ÷ MXN 18.3528 ÷ 140 productive hours × minutes per case × quality uplift. Low: MXN 11,236 (Paylab, lowest 10% of financial analysts) × 1.3, 8 min, ×1.1. Mid: MXN 39,608 (TalentUp KYC analyst median) × 1.35, 15 min, ×1.1. High: the same salary × 1.4, 25 min, ×1.2. Hours, minutes and uplift are assumptions. | S10 S11 S13 S14 |
| Implementation cost of the repeated-cause actions (USD) | $24,400 | $31,600 | $85,000 | Derived | Engineer-weeks × loaded weekly cost × team overhead. Weeks: 12 / 13 / 19.5, from the roadmap's effort for the four 30-day actions plus 2 weeks for review tools; high adds a 50% overrun. Weekly cost: Levels.fyi median MX$1,146,490 ÷ 18.3528 × 1.3 or × 1.35 ÷ 52 ($1,562, $1,622); high uses Revelo's top fully loaded $126,000 ($2,423). Overhead for product, design, QA and vendor work: ×1.3 / ×1.5 / ×1.8 (assumption). | S12 S13 S14 |
| Run cost per month (USD) | $510 | $2,010 | $3,860 | Derived | Central scenario, per 30 days: 278 review-pilot cases × cost per review. Add about 191 guided selfie retakes × billable transactions × cost per transaction, with the same preset's values. Excludes support contacts and alert tools. | S1 S2 S3 S10 S11 |

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

### 8. Checks performed for this submission

- `build_datasets.py` asserts the reconciliation checkpoints. It also asserts that class shares sum to the not-approved share and that process-step counts reconcile to all unsuccessful decisions.
- Each action has exactly one accountable role (asserted). Each run records the SHA-256 hashes of both raw files.
- Every number marked in the dashboard page resolves to a row in `analysis/out/` (checked by script); every table column exists in its dataset.
- The export embeds no `user_reference` values and no record-level columns (asserted in `export_html.py`), loads no network resources, and bundles d3 7.9.0.
- Browser tests of the export: one tab and one audience panel show at a time. Tooltips hide when the pointer leaves. The country filter updates its three views.
- More browser tests: sort and search work; the scenario picker updates tiles, table and value model; each preset gives the results in `value_results.csv`.
- Invalid and blank inputs show "Needs …" and no old values. Keyboard tab navigation works. Nothing overflows at 375 px; the console has no errors.
- Print to PDF shows all tabs, details and charts.
- On a replay of the extract, the alert rules fire on the first day of all four windows. 5 rule-days fire in the prior period, so the thresholds need adjustment.
- The PowerPoint passes the pptx skill's structural validator; its text was checked with markitdown; every slide was rendered from the shared slide specification and inspected.

### 9. Open questions for ARQ

These are not asked in the submission. They are the answers that would change the findings, in the order they matter; each says what changes with the answer.

| # | Question | Why it matters | What the answer changes | Who would know |
|---|---|---|---|---|
| 1 | Does each row hold a user's first, latest or final KYC attempt, and does the date mark the submission or the vendor's decision? | The headline is approval among recorded decisions. If rows are latest attempts, we cannot see earlier failures and retries, and the first-pass rate is lower than shown. If rows are final decisions, the warnings can be out of date. | The metric definition (v2 to v3 in the registry), the retry hypotheses, and whether the bridge counts people or attempts. | Data platform or whoever produced the extract. |
| 2 | Is there any record, even weekly counts, of people who opened KYC and never submitted? | The brief defines the pass rate as people who start and finish. Without starts, completion and abandonment cannot be measured, and the 1,587 fewer approvals from lower volume could be fewer starts, more abandonment, or both. | Whether Phase 0 instrumentation is a prerequisite or a check on current data; how we read the volume effect; the completion metric status. | Mobile and platform engineering (app analytics, API logs). |
| 3 | What happens today after a TECHNICAL_ERROR or a liveness failure: does the user see the vendor's outcome, get a retake, or enter a review queue? | Hold-and-retry and the guided retake assume no retry exists. In the central scenario they recover 242 approvals per comparable execution-error incident and 78 per 30 days on steady liveness failures. | If a retry already exists, those recoverable counts shrink and the question becomes why retries fail; the Phase 0 hold-and-retry becomes a configuration check. | Product and the onboarding squad; the vendor integration owner. |
| 4 | Which vendor product tier and data centre does ARQ use, and did ARQ receive incident notices for Sep 1, 2 and 6, 2023? | The vendor's status history shows liveness incidents on Sep 1 and 6 on its US data centre and nothing for Sep 2. The liveness spike is 173 failures above baseline and the execution errors 407. | On another data centre the liveness attribution loses its vendor evidence; with notices, the execution errors have an owner and an SLA claim. | Vendor management; the vendor's account team. |

### 10. Limitations and unresolved dependencies

- Starts, abandonment, attempts, review outcomes, account state and times of day are not in the extracts. Completion and eventual approval stay unavailable until the Phase 0 events exist.
- Whether a record is a first, latest or final attempt, and what event its date marks, is unknown; recent cohorts may be immature.
- Fraud signals are not adjudicated; execution errors are not attributed; vendor incident impact on ARQ is unconfirmed.
- Birth year is extracted data with outcome-related missingness; ages describe people whose document was read.
- Country is the country that issued the document.
- ARQ's current flow (retries, review, upload policy, architecture, vendor product tier) is unknown; the target design and roadmap mark these as discovery questions or conditions.
- Effort sizes, scenario factors and the role-based organisation are assumptions. The value-model presets come from public prices, salaries and benchmarks for other companies (several dated or third-party estimates), not from ARQ's contracts or finance data.
- Chrome rendered the deck PDF and the visual QA images from the HTML version of the slide specification. No PowerPoint or LibreOffice renderer was available.
- The .pptx passes a structural validator. Table row heights in PowerPoint can differ slightly from the PDF.

### 11. Reproduce

The code, the aggregated tables, the deck and this report are in the public repository [github.com/prosolkin/arq-kyc](https://github.com/prosolkin/arq-kyc), without the raw extracts. The interactive version is at [prosolkin.github.io/arq-kyc](https://prosolkin.github.io/arq-kyc/); its password is in the email. To rebuild every output, put the two extracts at the root of the repository and run:

```bash
bash analysis/build_all.sh   # every step and the PDFs; pinned tools: d3 7.9.0, pptxgenjs 3.12.0
```
