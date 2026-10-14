"""Write the methodology/validation note and the change summary from analysis/out.

Numbers are read from the same aggregates as the dashboard and the deck.
Run from the project root after build_datasets.py:  python3 -I analysis/build_notes.py
"""

import csv
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
EXP = os.path.join(ROOT, "analysis", "export")


def load(name):
    with open(os.path.join(OUT, name + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


K = {r["metric"]: r["value"] for r in load("kpis")}
k = lambda m: float(K[m])
i = lambda v: f"{abs(round(float(v))):,}"
si = lambda v: ("−" if float(v) < 0 else "+") + i(v)
pct = lambda v, d=1: f"{100 * float(v):.{d}f}%"
pp = lambda v, d=2: ("−" if float(v) < 0 else "+") + f"{abs(float(v)):.{d}f} pp"
bridge = {r["driver"]: r for r in load("bridge")}
inc = sorted(load("incidents"), key=lambda r: int(r["order"]))
sens = load("incident_sensitivity")
tot = {r["scenario"]: r for r in load("scenario_totals")}
scen = load("scenarios")
vin = load("value_inputs")
vin_by = {r["id"]: r for r in vin}
vsrc = load("value_sources")
vres = {(r["preset"], r["id"]): r for r in load("value_results") if r["scenario"] == "Central"}
PRESETS = ("Low", "Mid", "High", "Cautious")
RES_IDS = ("activated", "cohort_value", "annualised", "breakeven", "review_30d", "vendor_declined", "vendor_attack", "paid_declined")
def vfmt(r, v):
    v = float(v)
    if r["unit"] == "share":
        return f"{100 * v:.1f}%"
    if r["unit"] == "USD":
        return f"${v:,.2f}" if v < 100 and v != int(v) else f"${v:,.0f}"
    return f"{v:g}"
def rfmt(r):
    half_up = lambda x: int(math.floor(float(x) + 0.5))
    return "—" if r["value"] == "" else (f"{half_up(r['value']):,}" if r["unit"] == "int" else f"${half_up(r['value']):,}")
exp = {r["id"]: r for r in load("experiments")}
evidence = load("vendor_evidence")
alerts = load("alerts")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def methodology():
    v = load("validation")
    m = load("metrics")
    s = []
    s.append("# KYC approval-rate diagnosis: methodology and validation\n")
    s.append(f"Data: `KYC_summary.csv` and `KYC_details.csv`, {i(k('total_users'))} records each, Jul 25 – Sep 22, 2023. "
             f"Vendor research dated {K['research_date']}. Every figure below is read from `analysis/out/`, the same tables the dashboard and deck use.\n")
    s.append("## 1. What is measured\n")
    s.append("The brief defines the KYC pass rate as people who start and finish the process. The extracts hold one recorded decision per user, with a date and no time of day, and no record of starts, attempts or abandonment. The headline metric is therefore **approval among recorded decisions**: decisions whose final outcome (`KYC_summary.decision_type`) is PASSED or APPROVED, divided by all recorded decisions in the period. It is not the start-to-finish completion rate, and the extracts cannot say whether that rate is higher or lower.\n")
    s.append(table(["Metric", "Status", "Definition", "Prior", "Recent", "Gap"],
                   [[r["name"], r["status"], r["definition"], (pct(r["value_a"], 2) if r["unit"] == "pct" else i(r["value_a"])) if r["value_a"] else "—",
                     (pct(r["value_b"], 2) if r["unit"] == "pct" else i(r["value_b"])) if r["value_b"] else "—", r["gap"] or "—"] for r in m]))
    s.append("\n**Outcome treatment.** PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection); unsuccessful = rejected + warning. The 8 `OK` labels in the details file are label-only; the 1 record that is PASSED in the summary but REJECTED in details is counted as approved pending reconciliation. `PASSES` (3 values) is read as PASSED. Blank screening is \"not recorded\". NOT_EXECUTED with PRECONDITION_NOT_FULFILLED means an earlier check failed; with TECHNICAL_ERROR it is an execution error. Capability results are kept separate from the final outcome.\n")
    s.append("**Periods.** Prior period Jul 25 – Aug 23, 2023 and recent period Aug 24 – Sep 22, 2023: the two 30-day halves of the extract. Dates are those in `KYC_summary.date_`; which event they mark (submission, decision or export) is not stated.\n")
    s.append("## 2. Data validation\n")
    s.append(table(["Check", "Result", "Status", "Treatment"], [[r["check"], r["result"], r["status"], r["note"]] for r in v]))
    s.append("\nReconciliation checkpoints, all reproduced by assertions in `build_datasets.py`: "
             f"prior {i(k('n_a'))} decisions, {i(k('approved_a'))} approved ({pct(k('approval_a'), 2)}); recent {i(k('n_b'))} decisions, {i(k('approved_b'))} approved ({pct(k('approval_b'), 2)}); "
             f"change {pp(k('delta_pp'))}; approved count {si(k('approved_change'))}, of which {si(k('volume_effect'))} from lower volume at the prior rate and {si(k('rate_effect'))} from the lower rate. "
             f"Mexican documents {pct(k('mex_approval_a'), 2)} → {pct(k('mex_approval_b'), 2)}; Argentine {pct(k('arg_approval_a'), 2)} → {pct(k('arg_approval_b'), 2)}.\n")
    s.append("## 3. Attribution of unsuccessful decisions\n")
    s.append("Each unsuccessful decision gets one primary reason: TECHNICAL_ERROR in any capability first, otherwise the first capability in vendor order (usability, image checks, extraction, data checks, liveness, face match) with REJECTED or WARNING, then a watchlist WARNING, then \"no document type, no reason code\" or \"no failing check\". Reasons are grouped into nine groups and four classes (fraud signal, execution error, capture or document issue, unexplained or identity mismatch). Classes describe who could act on the vendor's reason; they are not adjudicated causes. "
             f"Because each decision has one primary reason, group effects sum to the total change. {i(k('multi_fail_b'))} recent unsuccessful decisions had two or more failing or warning checks, so fixing a primary reason does not by itself imply approval.\n")
    s.append(table(["Primary reason", "Share prior", "Share recent", "Effect on approval", "Above baseline in windows"],
                   [[d, pct(r["share_a"], 2), pct(r["share_b"], 2), pp(r["effect_pp"]), pp(r["incident_pp"])] for d, r in bridge.items()]))
    s.append("\nFace match improved between the periods; it is a large existing loss, not a cause of the decrease.\n")
    s.append("## 4. Incident windows\n")
    s.append("A window is a date range, a country scope and a failure signature. Attributed failures = observed signature failures in the window − the count expected at the prior-period rate of that signature for the window's volume. Other failures on those days are not attributed. Records cannot be matched to intraday outages because all timestamps are midnight UTC.\n")
    s.append(table(["Window (2023)", "Type", "Observed", "Expected", "Above baseline", "Of recent decisions", "Of recent unsuccessful", "Approval points"],
                   [[f"{r['title']}, {r['when']}", r["type"], i(r["observed"]), r["expected"], i(r["excess"]), pct(r["share_of_decisions_b"], 2), pct(r["share_of_unsuccessful_b"]), pp(r["contribution_pp"])] for r in inc]))
    s.append(f"\nTotal above baseline {i(k('incident_excess_base'))} ({pct(k('incident_share_unsuccessful'))} of recent unsuccessful decisions, {pp(k('incident_contribution_pp'))} of approval). "
             f"Sensitivity across a ±1-day window, a broader signature and a recent-period baseline: {i(k('incident_excess_low'))}–{i(k('incident_excess_high'))}. "
             f"The earlier method (every matching failure, no baseline) gives {i(k('incident_all_matching'))}. Removing the {i(k('selected_incident'))} selected failures from the recent period gives {pct(k('approval_excl_selected'), 2)}; that is a descriptive rate after excluding selected records, not a counterfactual.\n")
    s.append(f"Without the {i(k('incident_days_n'))} incident days, the recent rate is {pct(k('approval_b_excl_days'))} against {pct(k('approval_a_excl_days'))} before: {pp(k('delta_excl_days_pp'))}. Those days hold {pct(k('share_recent_on_incident_days'))} of recent decisions, so they are kept in the headline; the dashboard shows both views.\n")
    s.append("**Vendor evidence.** The vendor's public status history (monitor.jumio.com) was read on the research date. Source quality: primary vendor status page; some entries were read by a research sub-task and are marked as such.\n")
    s.append(table(["Date", "UTC", "Entry", "Read", "ARQ impact"], [[e["date"], e["window_utc"] or "—", e["description"], e["verification"], e["arq_impact"]] for e in evidence]))
    s.append("\nA documented vendor incident is not confirmation of impact on ARQ: ARQ's data centre, product tier and transaction times are unknown. No vendor entry matches the Sep 1–2 TECHNICAL_ERROR pattern, so those errors could be the vendor's or ARQ's integration.\n")
    s.append("## 5. Recovery scenarios\n")
    s.append("Recovered approvals = observed population × eligibility × reach × return × remediation × subsequent approval. Observed populations are recent-period counts by primary reason and do not overlap. All other factors are assumptions, shown per scenario. For the selfie populations, eligibility is the observed share with no other failing check. Subsequent approval uses the prior-period approval rate for the same countries (checks that did not run could still fail), except the review queue, where a reviewer approval is final. Incident-type benefits are reported per comparable incident, not per month. Possible approval reversals from confirmed control findings are reported separately.\n")
    s.append(table(["Scenario", "Recoverable per 30 days", "Approval points", "Recent rate with them", "Per comparable incident"],
                   [[n, i(t["steady_30d"]), pp(t["steady_pp"], 1), pct(t["approval_with_steady"]), i(t["per_incident"])] for n, t in tot.items()]))
    s.append(f"\nIf all control findings were confirmed, up to {i(tot['Central']['control_gap_n'])} recent approvals ({pp(tot['Central']['control_gap_all_pp'], 1)}) might need reversing. These are scenarios built on stated assumptions, not forecasts; a target set from them is a goal, not a prediction.\n")
    s.append("## 6. Experiment sizing\n")
    s.append("Per-arm sample sizes use the normal approximation for two proportions (two-sided α = 0.05, power 0.80). Assignment is per person, so repeat attempts are not counted as independent users. "
             f"Mexico document guidance: {exp['exp_mex_docs']['sample']} Liveness retake: {exp['exp_liveness']['sample']} Hold-and-retry for TECHNICAL_ERROR is remediation of a confirmed failure and is validated by acceptance criteria, not randomised.\n")
    s.append("## 7. Value model\n")
    s.append("Observed quantities (approved-count change, rate counterfactual, recoverable approvals per scenario, suspected extra attack traffic) are kept separate from the financial inputs: value per activated customer, activation rate, paid-channel share and cost, billable vendor transactions per decision and their cost, review cost, build and run cost. "
             "The inputs start from market-based presets derived in `analysis/value_presets.py` from published sources fetched on the research date. None is an ARQ figure; each should be replaced with ARQ's own number. "
             "Low, Mid and High are the low, middle and high values of each input's range, so a High preset raises costs as well as value. Cautious takes the end of each range that weakens the case. Results appear only when every required input is valid. Annualisation multiplies 30-day figures by 365/30; first-year cohort value is not revenue recognised in the next 12 months.\n")
    s.append(table(["Input", "Low", "Mid", "High", "Kind", "Basis", "Sources"],
                   [[f"{r['label']} ({'%' if r['unit'] == 'share' else r['unit']})"] + [vfmt(r, r[c]) for c in ("low", "mid", "high")] + [r["kind"], r["basis"], r["sources"]] for r in vin]))
    s.append("\nSources (fetched on the research date; status shows how each was obtained):\n")
    s.append(table(["ID", "Source", "Figure used", "Period", "Status"],
                   [[r["id"], f"[{r['publisher']}: {r['title']}]({r['url']})", r["figure"], r["period"], r["status"]] for r in vsrc]))
    s.append("\nResults in the central scenario (" + i(tot["Central"]["steady_30d"]) + " recoverable approvals per 30 days):\n")
    s.append(table(["Result"] + list(PRESETS), [[vres[("Mid", rid)]["label"]] + [rfmt(vres[(p, rid)]) for p in PRESETS] for rid in RES_IDS]))
    s.append("\nUnder the Cautious preset the actions do not pay back within the first year: break-even is " + rfmt(vres[("Cautious", "breakeven")])
             + " per activated customer against " + vfmt(vin_by["value_per_activated"], vin_by["value_per_activated"]["low"]) + " of value. That is the case Finance should test first with ARQ's own figures.\n")
    s.append("## 8. Checks performed for this submission\n")
    s.append("- `build_datasets.py` asserts the reconciliation checkpoints, that class shares sum to the not-approved share, that process-step counts reconcile to all unsuccessful decisions, that every action has exactly one accountable role, and records SHA-256 hashes of both raw files on every run.\n"
             "- Every number marked in the dashboard page resolves to a row in `analysis/out/` (checked by script); every table column exists in its dataset.\n"
             "- The export embeds no `user_reference` values and no record-level columns (asserted in `export_html.py`), loads no network resources, and bundles d3 7.9.0.\n"
             "- The regenerated export was tested in a browser: one tab and one audience panel visible at a time; tooltips hidden at rest and on pointer leave; country filter synchronised across its three views; sorting and search; scenario picker updating tiles, table and value model together; presets switching all inputs and results, with results matching `value_results.csv`; invalid and blank inputs showing \"Needs …\" instead of stale values; keyboard tab navigation; no horizontal overflow at 375 px; no console errors; print to PDF with all tabs, details and charts rendered.\n"
             f"- Alert rules replayed on the extract fire on the first day of all four windows ({sum(int(a['days_prior']) for a in alerts)} rule-days fire in the prior period and need tuning).\n"
             "- The PowerPoint passes the pptx skill's structural validator; its text was checked with markitdown; every slide was rendered from the shared slide specification and inspected.\n")
    s.append("## 9. Open questions for ARQ\n")
    s.append("These are not asked in the submission. They are the answers that would change the findings, in the order they matter; each says what changes with the answer.\n")
    s.append(table(["#", "Question", "Why it matters", "What the answer changes", "Who would know"],
                   [[r["order"], r["question"], r["why"], r["changes"], r["who"]] for r in sorted(load("open_questions"), key=lambda r: int(r["order"]))]))
    s.append("\n## 10. Limitations and unresolved dependencies\n")
    s.append("- Starts, abandonment, attempts, review outcomes, account state and times of day are not in the extracts; completion and eventual approval are unavailable until the Phase 0 events exist.\n"
             "- Whether a record is a first, latest or final attempt, and what event its date marks, is unknown; recent cohorts may be immature.\n"
             "- Fraud signals are not adjudicated; execution errors are not attributed; vendor incident impact on ARQ is unconfirmed.\n"
             "- Birth year is extracted data with outcome-related missingness; ages describe people whose document was read.\n"
             "- Country is the document issuing country.\n"
             "- ARQ's current flow (retries, review, upload policy, architecture, vendor product tier) is unknown; the target design and roadmap mark these as discovery questions or conditions.\n"
             "- Effort sizes, scenario factors and the role-based organisation are assumptions. The value-model presets come from public prices, salaries and benchmarks for other companies (several dated or third-party estimates), not from ARQ's contracts or finance data.\n"
             "- The deck's PDF companion and the visual QA images were rendered from the HTML version of the shared slide specification with Chrome, because no PowerPoint or LibreOffice renderer was available. The .pptx itself was validated structurally but not opened in PowerPoint; table row heights may differ slightly there.\n")
    s.append("## 11. Reproduce\n")
    s.append("```bash\nbash analysis/build_all.sh\n```\n")
    s.append("This runs `build_datasets.py`, `export_html.py`, `build_notes.py` and `tools/build_deck.mjs`, then prints the deck PDF with headless Chrome. The tools in `analysis/tools/package.json` are pinned (d3 7.9.0, pptxgenjs 3.12.0).\n")
    return "\n".join(s)


def changes():
    ex = next(r for r in inc if r["id"] == "exec_errors")
    lv = next(r for r in inc if r["id"] == "liveness_spike")
    rows = [
        ("Central metric (§4)", "Headline renamed \"approval rate among recorded decisions\" in every title, chart, tile and slide. Starts, completion, eventual approval, abandonment, retries, review outcomes and time to completion defined separately and marked unavailable, with the events needed. Instrumentation moved into Phase 0. The claim that true completion \"must be lower\" was removed."),
        ("Independent verification (§5)", f"All checkpoints reproduced and asserted in code ({i(k('approved_a'))} / {i(k('approved_b'))} approved, {pp(k('delta_pp'))}, {si(k('volume_effect'))} volume and {si(k('rate_effect'))} rate effects, country rates). Validation table covers joins, uniqueness, dates, missing values, outcome categories and inconsistencies. Outcome treatment documented; warnings kept separate from rejections."),
        ("Technical errors (§6)", f"Corrected: usability returned TECHNICAL_ERROR and document checks and face match did not run, but liveness ran and passed in all {i(ex['liveness_passed'])} and screening passed in {i(ex['screening_passed'])}. Attribution to vendor or integration left open; no claim that the applicants were eligible."),
        ("Fraud (§6)", "\"Correct decline\" replaced by \"Fraud signal (not adjudicated)\". Passing liveness and face match no longer presented as proof of a genuine person with an altered ID. The headline population is unchanged; the excluded-records rate is labelled descriptive."),
        ("Current ARQ workflow (§6)", "Statements about ARQ showing vendor decisions to users, lacking retries or review, allowing uploads, or its architecture are now discovery questions or conditions. The Jumio Go inference is limited to those transactions."),
        ("Documents and demographics (§6)", "Missing document type described as a symptom with several causes and broken down by outcome. Country labelled document issuing country. Birth-year missingness shown beside the age chart."),
        ("Incident analysis (§7)", f"Attribution now uses excess over the prior-period rate ({i(k('incident_excess_base'))}, range {i(k('incident_excess_low'))}–{i(k('incident_excess_high'))}) instead of every matching failure ({i(k('incident_all_matching'))}). Types separate suspected attack traffic, technical failures and a cluster without extra volume; other failures in the window are shown but not attributed. Denominators shown separately. Vendor incidents verified on the vendor's own status history (liveness incidents on Sep 1 and 6 on the US data centre; nothing for Sep 2 or the fraud dates), with ARQ impact marked unconfirmed."),
        ("Deterioration vs existing opportunity (§8)", f"Decomposition recalculated under the final definitions (fraud signals {pp(bridge['Fraud signal']['effect_pp'])}, execution errors {pp(bridge['Execution error']['effect_pp'])}, selfie/liveness {pp(bridge['Selfie / liveness']['effect_pp'])}, no document type {pp(bridge['No document type, no reason code']['effect_pp'])}, face match {pp(bridge['Face match']['effect_pp'])}). Face match presented as an existing loss that improved. Six hypotheses each list evidence, alternatives, missing evidence, next step and the decision enabled."),
        ("Recovery forecasts (§9)", f"The +6.73 pp / 90.02% forecast was replaced by three transparent scenarios ({pp(tot['Conservative']['steady_pp'], 1)}, {pp(tot['Central']['steady_pp'], 1)}, {pp(tot['Optimistic']['steady_pp'], 1)} on recurring causes) using the six-factor formula, disjoint populations and observed multi-failure shares. Of the {i(k('liveness_incident_n'))} liveness-spike cases, {i(k('liveness_incident_face'))} also had face-match problems; that lowers their eligibility. Incident benefits are shown per comparable incident. Possible reversals from control findings are shown separately. The scenario picker drives every dependent view."),
        ("Roadmap (§10)", "Phase 0 now holds instrumentation, hold-and-retry, alerting, control reconciliation and three investigations. Each action lists evidence, population, outcome and confidence, accountable role and participants, dependencies, effort assumption, acceptance criteria, window, rollout and rollback, guardrails and conditions. The orchestration layer, registry checks and second vendor are Phase 3, size L. Timelines aligned across roadmap, target design, FAQ and deck."),
        ("Experiments (§11)", "Two optimisation experiments with hypothesis, population, person-level assignment, primary outcome, window, minimum effect, sample-size rationale, guardrails and launch/expansion/rollback rules; hold-and-retry treated as remediation of a confirmed failure; review as a capacity-limited pilot."),
        ("Compliance (§12)", "All four findings verified and described as extract findings to reconcile, with alternatives and validation steps. Approval records not equated with enabled accounts; blank screening not equated with no screening; no legal obligations asserted."),
        ("Commercial model (§13)", "Unsourced placeholder prices removed. Observed quantities kept separate from the financial inputs; outputs appear only with valid inputs; break-even and annualisation explained; declines no longer treated as wasted acquisition, nor decisions as billable transactions. No monetary headline."),
        ("Value-model presets (follow-up request)", f"Added Low, Mid, High and Cautious presets for all nine inputs, each derived from published sources ({len(vsrc)} sources: vendor list prices, Nu Holdings filings, Liftoff benchmarks, Mexican salary data, the Banxico FIX, ARQ press figures) with stated assumptions. The dashboard loads Mid by default, labels it as not ARQ data, shows each input's range and sources, and lists every source with its fetch status. Results per preset and scenario are written to `value_results.csv`, and the deck's appendix (A7–A8) reads them. Under Cautious, the central scenario doesn't pay back within a year."),
        ("Role fit (§14)", "Operating-model tab adds a KPI registry with owners, versions, approval, freshness and lineage; a real version history (this metric's v1 → v2); ownership and attribution rules; commitments with check-ins; access by audience; an adoption plan with non-vanity measures. Functions are role-based examples with no reporting lines or people."),
        ("Communication (§15)", "Summary opens with seven answers in the requested order; caveats sit beside the claims they qualify; consistent terms (approval, unsuccessful, warning, rejection); every period labelled with dates; 2023 diagnosis separated from dated vendor research; \"today\" removed."),
        ("Dashboard defects (§16)", "Confirmed in a browser: in the old export every tab, audience panel and tooltip showed at once, because `display: flex` overrode `[hidden]`. Fixed at source and in the export. Also fixed: same-page hash navigation and print output (all tabs, details and charts). Added data tables beside charts, keyboard tab navigation, explicit filter scope, input validation and an offline bundle (d3 inlined, system fonts)."),
        ("Public explainer and vendor research (§17)", "The explainer stays an unpublished draft; every claim carries a status badge (to confirm, proposed, general), and unsupported promises about one-time KYC, prevention, retries, review, documents, age, timing, encryption and retention were removed. Vendor research separates historical evidence, documented capabilities with prerequisites, inferred benefits and unverified applicability, with primary-source links and verification status."),
    ]
    s = ["# Change summary: review findings and their resolution\n",
         "Each row maps a section of the review brief to what changed. All numbers come from `analysis/out/`.\n",
         table(["Finding", "Resolution"], rows), "\n## Not changed\n",
         "- The original CSV extracts (SHA-256 hashes recorded in the validation table).\n"
         "- The private Claude Dashboard artifact was not republished; the authoritative deliverable is the offline export in `analysis/export/`.\n"
         "- Previous analysis elements that held up (the primary-reason method, the Mexico vs Argentina comparison, the four incident windows, the bridge) were kept and re-derived.\n",
         "\n## Remaining dependencies\n",
         "- Phase 0 events before completion, eventual approval or experiments can be measured.\n"
         "- Vendor confirmation of incident scope; adjudicated fraud samples; reconciliation of the control findings against source systems.\n"
         "- ARQ's current KYC flow and architecture, accepted-document policy, age policy and data-handling commitments (needed before any public copy).\n"
         "- ARQ's own unit economics to replace the market-based presets (vendor contract and invoices, activation, revenue per customer, acquisition cost, review cost).\n"]
    return "\n".join(s)


if __name__ == "__main__":
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "methodology-and-validation.md"), "w") as f:
        f.write(methodology())
    with open(os.path.join(EXP, "change-summary.md"), "w") as f:
        f.write(changes())
    print("wrote methodology-and-validation.md and change-summary.md")
