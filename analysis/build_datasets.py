"""Authoritative calculations for the KYC approval-rate submission.

Reads the two raw extracts (KYC_summary.csv, KYC_details.csv; one row per
user_reference, joined 1:1) and writes aggregated CSVs to analysis/out/.
Every figure in the dashboard, the deck and the methodology note comes from
these files. No user ids, birth years or other record-level fields are written.

Run from the project root:  python3 -I analysis/build_datasets.py

Terminology used everywhere:
  approved      decision_type PASSED or APPROVED
  rejected      decision_type REJECTED
  warning       decision_type WARNING (unresolved: neither approved nor a confirmed rejection)
  unsuccessful  rejected + warning (= not approved)
  approval rate approved / recorded decisions. This is NOT the start-to-finish
                completion rate the assignment names: starts, abandonment and
                attempts are not in the extracts.
"""

import csv
import datetime as dt
import hashlib
import math
import os
import re
import statistics
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "analysis", "out")
RAW = {"summary": os.path.join(ROOT, "KYC_summary.csv"), "details": os.path.join(ROOT, "KYC_details.csv")}

SPLIT = "2023-08-24"  # prior period A: Jul 25 – Aug 23, 2023; recent period B: Aug 24 – Sep 22, 2023
PERIOD_LABEL = {"A": "Prior period (Jul 25 – Aug 23, 2023)", "B": "Recent period (Aug 24 – Sep 22, 2023)"}
RESEARCH_DATE = "2026-10-13"
STEPS = ["usability", "image_checks", "extraction", "data_checks", "liveness", "similarity"]
STEP_LABEL = {
    "usability": "Usability", "image_checks": "Image checks", "extraction": "Extraction",
    "data_checks": "Data checks", "liveness": "Liveness", "similarity": "Face match",
    "watchlist": "Watchlist", "execution": "Execution error", "none": "No failed check recorded",
}
APPROVED = ("PASSED", "APPROVED")

# Primary-reason groups ("drivers"). One per unsuccessful decision, so groups add up.
DRIVERS = [
    "Execution error",
    "Fraud signal",
    "No document type, no reason code",
    "Unsupported or incomplete document",
    "Image quality",
    "Screen or paper copy",
    "Selfie / liveness",
    "Face match",
    "Other",
]
# Who could act on each group. Descriptive, not an adjudicated cause.
DRIVER_CLASS = {
    "Fraud signal": "Fraud signal (not adjudicated)",
    "Execution error": "Execution error",
    "Unsupported or incomplete document": "Capture or document issue",
    "Image quality": "Capture or document issue",
    "Screen or paper copy": "Capture or document issue",
    "Selfie / liveness": "Capture or document issue",
    "No document type, no reason code": "Unexplained or identity mismatch",
    "Face match": "Unexplained or identity mismatch",
    "Other": "Unexplained or identity mismatch",
}
CLASSES = ["Fraud signal (not adjudicated)", "Execution error", "Capture or document issue", "Unexplained or identity mismatch"]

DOC_LABEL = {
    "ELECTORAL_ID": "Voter ID (INE)", "NATIONAL_ID": "National ID card", "UNCLASSIFIED": "No document type returned",
    "PASSPORT": "Passport", "RESIDENT_PERMIT_ID": "Residence permit", "REGULAR_DRIVING_LICENSE": "Driving licence",
    "OTHER": "Other",
}
AGE_BANDS = ["Under 18", "18–24", "25–34", "35–44", "45–54", "55+", "Not extracted"]


def norm(v):
    """Normalise a capability decision value."""
    if v == "PASSES":
        return "PASSED"
    return v or "NOT_RECORDED"


def primary_reason(r):
    """(step, reason) of the first check that explains an unsuccessful decision."""
    if any("TECHNICAL_ERROR" in r[s + "_decision_details"] for s in STEPS):
        return "execution", "TECHNICAL_ERROR"
    for s in STEPS:
        if r[s + "_decision"] in ("REJECTED", "WARNING"):
            return s, r[s + "_decision_details"]
    if r["watchlist_screening_decision"] == "WARNING":
        return "watchlist", "WATCHLIST_WARNING"
    if not r["data_type"]:
        return "none", "NO_DOCUMENT_TYPE"
    return "none", "NO_FAILING_CHECK"


def driver_for(step, reason):
    if reason == "TECHNICAL_ERROR":
        return "Execution error"
    if step == "image_checks" and (reason.startswith("MANIPULATED") or reason == "FAKE"):
        return "Fraud signal"
    if reason == "NO_DOCUMENT_TYPE":
        return "No document type, no reason code"
    if reason in ("UNSUPPORTED_DOCUMENT_TYPE", "MISSING_MANDATORY_DATAPOINTS", "MISSING_PAGE",
                  "PART_OF_DOCUMENT_MISSING", "PART_OF_DOCUMENT_HIDDEN", "NOT_A_DOCUMENT"):
        return "Unsupported or incomplete document"
    if reason in ("BLURRED", "GLARE", "DAMAGED_DOCUMENT"):
        return "Image quality"
    if reason in ("DIGITAL_COPY", "PHOTOCOPY"):
        return "Screen or paper copy"
    if step == "liveness" or reason == "LIVENESS_UNDETERMINED":
        return "Selfie / liveness"
    if step == "similarity":
        return "Face match"
    return "Other"


def failing_checks(r):
    n = sum(r[s + "_decision"] in ("REJECTED", "WARNING") for s in STEPS)
    return n + (r["watchlist_screening_decision"] == "WARNING")


def age_band(r):
    if not r["year_birth"]:
        return "Not extracted"
    a = 2023 - int(r["year_birth"])
    for limit, band in ((18, "Under 18"), (25, "18–24"), (35, "25–34"), (45, "35–44"), (55, "45–54")):
        if a < limit:
            return band
    return "55+"


def week_of(day):
    d = dt.date.fromisoformat(day)
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write(name, fieldnames, records):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(records)


def rate(num, den, nd=4):
    return round(num / den, nd) if den else ""


# ---------------------------------------------------------------------------
# Incidents: a date window, a scope and a failure signature. Attribution uses
# the excess over the prior-period rate of the same signature, because the
# extracts carry dates only (all timestamps are midnight) and ordinary failures
# also happen on incident days.
INCIDENTS = [
    {"id": "fraud_arg", "order": 1, "title": "Argentina fraud-signal burst", "when": "Aug 24",
     "dates": ["2023-08-24"], "country": "ARG", "type": "Suspected additional attack traffic",
     "signature": "fraud", "narrow": lambda r: r["driver"] == "Fraud signal",
     "broad": lambda r: r["step"] == "image_checks"},
    {"id": "exec_errors", "order": 2, "title": "Execution errors at usability", "when": "Sep 1–2",
     "dates": ["2023-09-01", "2023-09-02"], "country": "ALL", "type": "Technical failure that affected applicants",
     "signature": "exec_error", "narrow": lambda r: r["driver"] == "Execution error",
     "broad": lambda r: r["driver"] == "Execution error" or any(r[s + "_decision"] == "NOT_EXECUTED" and r[s + "_decision_details"] != "PRECONDITION_NOT_FULFILLED" for s in STEPS)},
    {"id": "liveness_spike", "order": 3, "title": "Liveness quality spike", "when": "Sep 1 and Sep 6",
     "dates": ["2023-09-01", "2023-09-06"], "country": "ALL", "type": "Technical failure that affected applicants",
     "signature": "liveness_quality",
     "narrow": lambda r: r["step"] == "liveness" and r["reason"] in ("BAD_QUALITY", "FACE_NOT_FULLY_VISIBLE"),
     "broad": lambda r: r["driver"] == "Selfie / liveness"},
    {"id": "fraud_mex", "order": 4, "title": "Mexico INE fraud-signal cluster", "when": "Sep 14–19",
     "dates": [f"2023-09-{d}" for d in range(14, 20)], "country": "MEX", "type": "Fraud-signal cluster without extra volume",
     "signature": "fraud", "narrow": lambda r: r["driver"] == "Fraud signal",
     "broad": lambda r: r["step"] == "image_checks"},
]
INCIDENT_DAYS = {d for i in INCIDENTS for d in i["dates"]}


def load():
    summary = {}
    for r in csv.DictReader(open(RAW["summary"])):
        summary[r["user_reference"]] = r
    rows = []
    for r in csv.DictReader(open(RAW["details"])):
        s = summary[r["user_reference"]]
        r["date"] = s["date_"][:10]
        r["ts"] = s["date_"]
        r["decision"] = s["decision_type"]
        r["approved"] = r["decision"] in APPROVED
        r["country"] = r["data_issuing_country"]
        r["period"] = "A" if r["date"] < SPLIT else "B"
        r["week"] = week_of(r["date"])
        r["doc"] = r["data_sub_type"] or r["data_type"] or "UNCLASSIFIED"
        if r["doc"] not in DOC_LABEL:
            r["doc"] = "OTHER"
        if r["approved"]:
            r["step"], r["reason"], r["driver"] = "", "", "Approved"
        else:
            r["step"], r["reason"] = primary_reason(r)
            r["driver"] = driver_for(r["step"], r["reason"])
        rows.append(r)
    return summary, rows


def main():
    os.makedirs(OUT, exist_ok=True)
    summary, rows = load()
    A = [r for r in rows if r["period"] == "A"]
    B = [r for r in rows if r["period"] == "B"]
    nA, nB = len(A), len(B)
    apA, apB = sum(r["approved"] for r in A), sum(r["approved"] for r in B)
    rA, rB = apA / nA, apB / nB
    unsB = [r for r in B if not r["approved"]]
    by = lambda sub, c: [r for r in sub if r["country"] == c]
    approval = lambda sub: sum(r["approved"] for r in sub) / len(sub)

    # ---------------- validation ----------------
    details_raw = list(csv.DictReader(open(RAW["details"])))
    s_ids, d_ids = set(summary), {r["user_reference"] for r in details_raw}
    dates = sorted({r["date"] for r in rows})
    span = (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days + 1
    blank = {c: sum(1 for r in details_raw if r[c] == "") for c in details_raw[0]}
    yb = [int(r["year_birth"]) for r in rows if r["year_birth"]]
    yb_blank_rejected = sum(1 for r in rows if not r["year_birth"] and r["decision"] == "REJECTED")
    label_mismatch = Counter((r["decision"], r["decision_label"]) for r in rows if r["decision_label"] != r["decision"])
    passes = sum(1 for r in details_raw for v in r.values() if v == "PASSES")
    validation = [
        ("rows", "Records in each extract", f"{len(summary):,} summary / {len(details_raw):,} details", "Pass", "Equal row counts."),
        ("unique", "Unique user_reference", f"{len(s_ids):,} / {len(d_ids):,}", "Pass", "No duplicate users in either file."),
        ("join", "Join coverage on user_reference", f"{len(s_ids & d_ids):,} matched, {len(s_ids - d_ids)} + {len(d_ids - s_ids)} unmatched", "Pass", "Complete one-to-one join."),
        ("dates", "Date coverage", f"{dates[0]} to {dates[-1]}: {len(dates)} of {span} calendar days", "Pass", "All days are present."),
        ("time", "Timestamp precision", f"{sum(1 for r in rows if r['ts'].endswith('T00:00:00Z')):,} of {len(rows):,} at midnight UTC", "Limitation",
         "Dates only. Intraday outage windows cannot be matched to records, and the extract does not say which event the date marks (submission, decision or export)."),
        ("decision", "Final outcome categories (summary.decision_type)", ", ".join(f"{k} {v:,}" for k, v in Counter(r["decision"] for r in rows).most_common()), "Pass",
         "PASSED and APPROVED = approved; REJECTED = rejected; WARNING = unresolved (not approved, not a confirmed rejection)."),
        ("label", "decision_type vs details.decision_label", "; ".join(f"{a} vs {b}: {n}" for (a, b), n in label_mismatch.items()), "Note",
         "summary.decision_type is treated as the outcome. The 8 'OK' labels are label-only; 1 record shows PASSED in the summary but REJECTED in details. We count it as approved until it is reconciled."),
        ("passes", "Non-standard capability value 'PASSES'", f"{passes} values", "Note", "Treated as PASSED."),
        ("watchlist_blank", "Blank watchlist_screening_decision", f"{blank['watchlist_screening_decision']:,} blank, 1 NOT_EXECUTED", "Note",
         "Shown as 'not recorded'. Mostly on rejected records; a blank field does not prove screening never ran elsewhere."),
        ("doc_blank", "Blank data_type (no document type returned)", f"{blank['data_type']:,} records", "Note",
         "A symptom with several possible causes (unsupported document, capture, configuration, classification coverage)."),
        ("yob", "Birth year extracted", f"{len(yb):,} present, {blank['year_birth']:,} blank; range {min(yb)}–{max(yb)}", "Limitation",
         f"{yb_blank_rejected:,} of the {blank['year_birth']:,} blanks are rejected records, so ages describe applicants whose document was read, not all applicants. Extreme years (e.g. {max(yb)}) suggest extraction errors."),
        ("country", "Country field", "MEX / ARG only (data_issuing_country)", "Note", "This is the country that issued the document. It is not always the residence or the account market."),
        ("attempts", "Attempts per user", "1 record per user_reference", "Limitation",
         "The extract does not say whether a record is the first, latest or final attempt; retries and later outcomes are not visible."),
        ("raw_hash", "Raw files unchanged", f"summary {sha256(RAW['summary'])[:12]}…, details {sha256(RAW['details'])[:12]}…", "Pass", "SHA-256 prefixes, recomputed on every build."),
    ]
    write("validation.csv", ["id", "check", "result", "status", "note"],
          [dict(zip(["id", "check", "result", "status", "note"], v)) for v in validation])

    # ---------------- metric registry (definitions, availability, ownership) ----------------
    metrics = [
        ("kyc_starts", "KYC starts", "Unavailable", "People who open the KYC flow.", "kyc_started events", "", "Daily, by country",
         "", "", "count", "data", "product, platform, mobile",
         "kyc_started with person id, session id, timestamp, country, app version, channel"),
        ("submissions", "Recorded decisions", "Available", "User records with a final decision in the extract (one per user_reference).",
         "Records", "", "Per period", nA, nB, "count", "data", "platform",
         "Whether a record is a first, latest or final attempt is not stated"),
        ("approval_rate", "Approval rate among recorded decisions", "Available",
         "Approved (PASSED or APPROVED) ÷ recorded decisions. The headline metric of this analysis.",
         "Approved decisions", "Recorded decisions", "Per period, by decision date", round(rA, 4), round(rB, 4), "pct", "product",
         "data, risk", "Not the start-to-finish completion rate: starts, abandonment and attempts are not in the data"),
        ("rejection_rate", "Rejection rate", "Available", "REJECTED ÷ recorded decisions.", "Rejected", "Recorded decisions",
         "Per period", rate(sum(r["decision"] == "REJECTED" for r in A), nA), rate(sum(r["decision"] == "REJECTED" for r in B), nB),
         "pct", "product", "risk", ""),
        ("warning_rate", "Unresolved warning rate", "Available", "WARNING ÷ recorded decisions. Later review outcome not in the extract.",
         "Warning", "Recorded decisions", "Per period", rate(sum(r["decision"] == "WARNING" for r in A), nA),
         rate(sum(r["decision"] == "WARNING" for r in B), nB), "pct", "ops", "compliance", "Review dispositions needed"),
        ("completion_rate", "Completion rate (start to terminal state)", "Unavailable",
         "Starts that reach a terminal state (approved, finally rejected, or abandoned for 7 days) within 7 days of start.",
         "Starts reaching a terminal state", "KYC starts", "7 days after start", "", "", "pct", "product", "data",
         "kyc_started, step events, terminal decision, abandonment rule"),
        ("eventual_approval", "Eventual approval within 7 days", "Unavailable",
         "Starts approved on any attempt within 7 days of the first start.", "People approved within window", "KYC starts",
         "7 days, cohort by start date", "", "", "pct", "product", "data, ops", "Person id across attempts, attempt number, timestamps, review dispositions"),
        ("abandonment", "Abandonment rate", "Unavailable", "Starts with no submission within 7 days.", "Starts without submission",
         "KYC starts", "7 days", "", "", "pct", "product", "mobile", "kyc_started and kyc_submitted events"),
        ("retry_outcomes", "Retry rate and retry approval", "Unavailable", "Share of unsuccessful first attempts that retry, and their approval.",
         "Retried / approved on retry", "Unsuccessful first attempts", "7 days", "", "", "pct", "product", "platform", "Attempt number per person"),
        ("review_outcomes", "Manual-review outcomes", "Unavailable", "Approval and turnaround of cases sent to review.", "Approved after review",
         "Cases sent to review", "Per week", "", "", "pct", "ops", "compliance", "Review queue events and dispositions"),
        ("time_to_decision", "Time to completion", "Unavailable", "Median minutes from start to terminal decision.", "", "",
         "Per week", "", "", "minutes", "product", "platform", "Timestamps with time of day on start and decision"),
        ("exec_error_rate", "Execution-error rate", "Available", "Unsuccessful decisions whose primary reason is TECHNICAL_ERROR ÷ recorded decisions.",
         "TECHNICAL_ERROR decisions", "Recorded decisions", "Per period", rate(sum(r["driver"] == "Execution error" for r in A), nA, 5),
         rate(sum(r["driver"] == "Execution error" for r in B), nB, 5), "pct", "platform", "vendors", ""),
        ("fraud_signal_rate", "Fraud-signal rate", "Available", "Unsuccessful decisions whose primary reason is a manipulation or fake label ÷ recorded decisions. Not adjudicated.",
         "Fraud-signal decisions", "Recorded decisions", "Per period", rate(sum(r["driver"] == "Fraud signal" for r in A), nA, 5),
         rate(sum(r["driver"] == "Fraud signal" for r in B), nB, 5), "pct", "risk", "ops", "Adjudication of a sample"),
    ]
    mcols = ["id", "name", "status", "definition", "numerator", "denominator", "window", "value_a", "value_b", "unit",
             "owner", "contributors", "gap"]
    write("metrics.csv", mcols + ["version", "approved_by", "freshness", "lineage"],
          [dict(zip(mcols, m), version="2.0" if m[0] == "approval_rate" else "1.0",
                approved_by="Proposed: Data & Analytics with the metric owner", freshness="Static extract, Jul 25 – Sep 22, 2023",
                lineage="KYC_summary.decision_type" if m[2] == "Available" else "Needs new events") for m in metrics])
    write("metric_versions.csv", ["id", "metric", "version", "change", "reason", "effective"], [
        {"id": "v1", "metric": "approval_rate", "version": "1.0", "change": "Called 'pass rate'; presented as the KYC funnel pass rate.",
         "reason": "First draft of this analysis.", "effective": "Superseded"},
        {"id": "v2", "metric": "approval_rate", "version": "2.0",
         "change": "Renamed 'approval rate among recorded decisions'; completion and eventual approval defined separately and marked unavailable.",
         "reason": "Review: the extract has no starts, attempts or abandonment, so it cannot measure start-to-finish completion.", "effective": "Current"},
    ])

    # events needed for the requested funnel (Phase 0 instrumentation)
    events = [
        ("kyc_started", "Person opens the KYC flow", "person_id, session_id, ts, country_selected, app_version, sdk_version, channel", "Starts, completion, abandonment"),
        ("document_selected", "Person chooses a document type", "session_id, ts, doc_type_selected, issuing_country", "Document mismatch diagnosis"),
        ("document_captured", "ID images captured (front, back)", "session_id, ts, capture_mode (camera/upload), retakes", "Capture-quality diagnosis"),
        ("selfie_captured", "Selfie captured", "session_id, ts, retakes", "Liveness diagnosis"),
        ("kyc_submitted", "Submission sent to the vendor", "session_id, attempt_no, ts, vendor_transaction_id", "Submissions, retries"),
        ("vendor_result", "Vendor result received", "vendor_transaction_id, ts, every capability decision and label, workflow version", "Reason analysis, incident windows"),
        ("kyc_decided", "ARQ decision applied", "session_id, ts, outcome, reason_code, decided_by (rule/reviewer), policy_version", "Approval, eventual approval, time to decision"),
        ("review_completed", "Manual review disposition", "session_id, ts, reviewer_role, outcome, reason", "Review outcomes"),
        ("account_enabled", "Account state after KYC", "person_id, ts, state", "Approval vs account enablement"),
    ]
    write("events.csv", ["event", "when", "fields", "enables"], [dict(zip(["event", "when", "fields", "enables"], e)) for e in events])

    # ---------------- daily / weekly ----------------
    def sig(r, name):
        return {"fraud": r["driver"] == "Fraud signal", "exec_error": r["driver"] == "Execution error",
                "liveness_quality": r["step"] == "liveness" and r["reason"] in ("BAD_QUALITY", "FACE_NOT_FULLY_VISIBLE")}[name]

    selected = set()
    for inc in INCIDENTS:
        for r in rows:
            if not r["approved"] and r["date"] in inc["dates"] and inc["country"] in ("ALL", r["country"]) and inc["narrow"](r):
                selected.add(id(r))
    daily = defaultdict(Counter)
    for r in rows:
        for sc in ("ALL", r["country"]):
            c = daily[(r["date"], sc)]
            c["n"] += 1
            c["approved"] += r["approved"]
            c["rejected"] += r["decision"] == "REJECTED"
            c["warning"] += r["decision"] == "WARNING"
            c["selected"] += id(r) in selected
            for s in ("fraud", "exec_error", "liveness_quality"):
                c[s] += (not r["approved"]) and sig(r, s)
    dcols = ("n", "approved", "rejected", "warning", "selected", "fraud", "exec_error", "liveness_quality")
    write("daily.csv", ["date", "country", "incident_day", *dcols, "approval_rate", "approval_excl_selected"],
          [{"date": d, "country": sc, "incident_day": int(d in INCIDENT_DAYS), **{k: c[k] for k in dcols}, "approval_rate": rate(c["approved"], c["n"]),
            "approval_excl_selected": rate(c["approved"], c["n"] - c["selected"])} for (d, sc), c in sorted(daily.items())])

    wk_total, wk = Counter(), Counter()
    for r in rows:
        for sc in ("ALL", r["country"]):
            wk_total[(r["week"], sc)] += 1
            if not r["approved"]:
                wk[(r["week"], sc, r["driver"])] += 1
    weekly = []
    for (w, sc), tot in sorted(wk_total.items()):
        ndays = len({r["date"] for r in rows if r["week"] == w})
        for drv in DRIVERS:
            weekly.append({"week": w, "country": sc, "driver": drv, "n": wk[(w, sc, drv)], "total": tot,
                           "share": rate(wk[(w, sc, drv)], tot, 5), "days": ndays})
    write("weekly_drivers.csv", ["week", "country", "driver", "n", "total", "share", "days"], weekly)

    # ---------------- reasons ----------------
    rc, tot = Counter(), Counter()
    for r in rows:
        for sc in ("ALL", r["country"]):
            tot[(sc, r["period"])] += 1
            if not r["approved"]:
                rc[(sc, r["step"], r["reason"], r["driver"], r["period"])] += 1
    reasons = []
    for sc, st, rs, dv in sorted({k[:4] for k in rc}):
        a, b = rc[(sc, st, rs, dv, "A")], rc[(sc, st, rs, dv, "B")]
        ra, rb = a / tot[(sc, "A")], b / tot[(sc, "B")]
        reasons.append({"id": f"{sc}-{st}-{rs}", "country": sc, "step": STEP_LABEL[st], "reason": rs, "driver": dv,
                        "n_a": a, "n_b": b, "rate_a": round(ra, 5), "rate_b": round(rb, 5), "change_pp": round(100 * (rb - ra), 2)})
    reasons.sort(key=lambda x: (x["country"], -x["n_b"]))
    write("reasons.csv", list(reasons[0].keys()), reasons)

    # ---------------- incidents (excess over baseline, with sensitivity) ----------------
    def scope(sc, sub=rows):
        return [r for r in sub if sc in ("ALL", r["country"])]

    def incident_numbers(inc, dates_, matcher, baseline="prior"):
        sr = scope(inc["country"])
        win = [r for r in sr if r["date"] in dates_]
        observed = sum(1 for r in win if not r["approved"] and matcher(r))
        if baseline == "prior":
            base_rows = [r for r in sr if r["period"] == "A"]
        else:  # recent-period days outside every incident window
            base_rows = [r for r in sr if r["period"] == "B" and r["date"] not in INCIDENT_DAYS]
        base_rate = sum(1 for r in base_rows if not r["approved"] and matcher(r)) / len(base_rows)
        expected = base_rate * len(win)
        return win, observed, expected, base_rate

    vol_by_day = lambda sc: Counter(r["date"] for r in scope(sc))
    incidents, sens = [], []
    unsuccessful_B = len(unsB)
    for inc in INCIDENTS:
        win, obs, exp, base_rate = incident_numbers(inc, inc["dates"], inc["narrow"])
        days = vol_by_day(inc["country"])
        normal = [d for d in days if d not in INCIDENT_DAYS]
        base_vol = statistics.median(days[d] for d in normal) * len(inc["dates"])
        excess_fail = max(0.0, obs - exp)
        ap_win = sum(r["approved"] for r in win)
        sig_rows = [r for r in win if not r["approved"] and inc["narrow"](r)]
        incidents.append({
            "id": inc["id"], "order": inc["order"], "title": inc["title"], "when": inc["when"], "type": inc["type"],
            "days": ",".join(inc["dates"]), "country": inc["country"], "signature": inc["signature"],
            "volume": len(win), "baseline_volume": round(base_vol), "excess_volume": max(0, round(len(win) - base_vol)),
            "observed": obs, "expected": round(exp, 1), "excess": round(excess_fail),
            "ordinary_unsuccessful": sum(1 for r in win if not r["approved"]) - obs,
            "share_of_decisions_b": rate(excess_fail, nB, 5), "share_of_unsuccessful_b": rate(excess_fail, unsuccessful_B, 4),
            "contribution_pp": round(-100 * excess_fail / nB, 2),
            "window_approval_rate": rate(ap_win, len(win)),
            "baseline_approval_rate": round(statistics.median(
                sum(r["approved"] for r in scope(inc["country"]) if r["date"] == d) / days[d] for d in normal), 4),
            "liveness_passed": sum(r["liveness_decision"] == "PASSED" for r in sig_rows),
            "face_passed": sum(r["similarity_decision"] == "PASSED" for r in sig_rows),
            "other_failing": sum(failing_checks(r) >= 2 for r in sig_rows),
            "screening_passed": sum(r["watchlist_screening_decision"] == "PASSED" for r in sig_rows),
            "doc_type_present": sum(bool(r["data_type"]) for r in sig_rows),
        })
        # sensitivity variants
        d0 = dt.date.fromisoformat(inc["dates"][0]) - dt.timedelta(days=1)
        d1 = dt.date.fromisoformat(inc["dates"][-1]) + dt.timedelta(days=1)
        wide = sorted(set(inc["dates"]) | {d0.isoformat(), d1.isoformat()})
        variants = [
            ("base", "Base: narrow signature, incident days, prior-period rate", inc["dates"], inc["narrow"], "prior"),
            ("wide_window", "Window widened by one day each side", wide, inc["narrow"], "prior"),
            ("broad_signature", "Broader signature (whole check or group)", inc["dates"], inc["broad"], "prior"),
            ("recent_baseline", "Baseline from recent non-incident days", inc["dates"], inc["narrow"], "recent"),
            ("all_matching", "Every failure of the same pattern in the window (no baseline; old method)", inc["dates"], inc["narrow"], None),
        ]
        for vid, label, dd, m, bl in variants:
            if bl is None:
                _, o, _, _ = incident_numbers(inc, dd, m)
                ex = o
            else:
                _, o, e, _ = incident_numbers(inc, dd, m, bl)
                ex = max(0.0, o - e)
            sens.append({"id": f"{inc['id']}-{vid}", "incident": inc["id"], "variant": vid, "label": label,
                         "observed": o, "attributed": round(ex), "share_of_unsuccessful_b": rate(ex, unsuccessful_B, 4)})
    write("incidents.csv", list(incidents[0].keys()), incidents)
    write("incident_sensitivity.csv", list(sens[0].keys()), sens)
    inc_total = {v: sum(s["attributed"] for s in sens if s["variant"] == v) for v in
                 ("base", "wide_window", "broad_signature", "recent_baseline", "all_matching")}

    # ---------------- decomposition of the approval-rate change ----------------
    excess_by_driver = defaultdict(float)
    for inc in incidents:
        drv = {"fraud": "Fraud signal", "exec_error": "Execution error", "liveness_quality": "Selfie / liveness"}[inc["signature"]]
        excess_by_driver[drv] += inc["excess"]
    ca, cb = Counter(r["driver"] for r in A), Counter(r["driver"] for r in B)
    bridge = []
    for drv in DRIVERS:
        sa, sb = ca[drv] / nA, cb[drv] / nB
        inc_part = excess_by_driver[drv] / nB
        bridge.append({"driver": drv, "class": DRIVER_CLASS[drv], "n_a": ca[drv], "n_b": cb[drv],
                       "share_a": round(sa, 5), "share_b": round(sb, 5),
                       "effect_pp": round(-100 * (sb - sa), 2) + 0.0, "incident_pp": round(-100 * inc_part, 2) + 0.0,
                       "rest_pp": round(-100 * (sb - sa - inc_part), 2) + 0.0})
    bridge.sort(key=lambda x: x["effect_pp"])
    write("bridge.csv", list(bridge[0].keys()), bridge)

    # declines by group and class, with both denominators
    fa, fb = nA - apA, nB - apB
    declines = []
    for g in DRIVERS:
        declines.append({"key": "group:" + g, "level": "group", "name": g, "class": DRIVER_CLASS[g], "n_a": ca[g], "n_b": cb[g],
                         "share_a": rate(ca[g], nA, 5), "share_b": rate(cb[g], nB, 5),
                         "of_unsuccessful_a": rate(ca[g], fa), "of_unsuccessful_b": rate(cb[g], fb)})
    for cl in CLASSES:
        na_ = sum(ca[g] for g in DRIVERS if DRIVER_CLASS[g] == cl)
        nb_ = sum(cb[g] for g in DRIVERS if DRIVER_CLASS[g] == cl)
        declines.append({"key": "class:" + cl, "level": "class", "name": cl, "class": cl, "n_a": na_, "n_b": nb_,
                         "share_a": rate(na_, nA, 5), "share_b": rate(nb_, nB, 5),
                         "of_unsuccessful_a": rate(na_, fa), "of_unsuccessful_b": rate(nb_, fb)})
    write("declines.csv", list(declines[0].keys()), declines)

    # ---------------- Mexico ----------------
    MEX_GROUP = {
        "NO_DOCUMENT_TYPE": "No reason code", "UNSUPPORTED_DOCUMENT_TYPE": "Unsupported document type",
        "MISSING_MANDATORY_DATAPOINTS": "Mandatory data not present", "MISSING_PAGE": "Page or part not present",
        "PART_OF_DOCUMENT_MISSING": "Page or part not present", "PART_OF_DOCUMENT_HIDDEN": "Page or part not present",
        "NOT_A_DOCUMENT": "Page or part not present", "BLURRED": "Image quality", "GLARE": "Image quality",
        "DAMAGED_DOCUMENT": "Image quality", "DIGITAL_COPY": "Screen or paper copy", "PHOTOCOPY": "Screen or paper copy",
        "TECHNICAL_ERROR": "Execution error",
    }
    mex = [r for r in rows if r["country"] == "MEX"]
    mexA, mexB = [r for r in mex if r["period"] == "A"], [r for r in mex if r["period"] == "B"]
    def mex_group(r):
        if r["approved"]:
            return "Approved"
        return MEX_GROUP.get(r["reason"], "Selfie, face or other")
    mex_rows = []
    order = ["No reason code", "Unsupported document type", "Mandatory data not present", "Page or part not present", "Image quality",
             "Screen or paper copy", "Execution error", "Selfie, face or other", "Approved"]
    ua = Counter(mex_group(r) for r in mexA if r["doc"] == "UNCLASSIFIED")
    ub = Counter(mex_group(r) for r in mexB if r["doc"] == "UNCLASSIFIED")
    for g in order:
        mex_rows.append({"group": g, "n_a": ua[g], "n_b": ub[g], "share_a": rate(ua[g], len(mexA), 5), "share_b": rate(ub[g], len(mexB), 5),
                         "change_pp": round(100 * (ub[g] / len(mexB) - ua[g] / len(mexA)), 2)})
    write("mex_no_doctype.csv", list(mex_rows[0].keys()), mex_rows)

    docs = []
    for sc in ("MEX", "ARG"):
        sr = [r for r in rows if r["country"] == sc]
        for doc in DOC_LABEL:
            def st(sub):
                d = [r for r in sub if r["doc"] == doc]
                return len(d), sum(r["approved"] for r in d), len(sub)
            n, p, t = st(sr)
            if not n:
                continue
            na, pa, ta = st([r for r in sr if r["period"] == "A"])
            nb, pb, tb = st([r for r in sr if r["period"] == "B"])
            docs.append({"id": f"{sc}-{doc}", "country": sc, "doc": doc, "label": DOC_LABEL[doc], "n": n, "share": rate(n, t),
                         "approval_rate": rate(p, n), "share_a": rate(na, ta), "share_b": rate(nb, tb),
                         "approval_rate_a": rate(pa, na), "approval_rate_b": rate(pb, nb)})
    docs.sort(key=lambda x: (x["country"], -x["n"]))
    write("docs.csv", list(docs[0].keys()), docs)

    wkt, wkd, wkp = Counter(), Counter(), Counter()
    for r in rows:
        wkt[(r["country"], r["week"])] += 1
        wkd[(r["country"], r["week"], r["doc"])] += 1
        wkp[(r["country"], r["week"], r["doc"])] += r["approved"]
    write("docs_weekly.csv", ["country", "week", "doc", "label", "n", "share", "approval_rate"],
          [{"country": sc, "week": w, "doc": doc, "label": DOC_LABEL[doc], "n": n, "share": rate(n, wkt[(sc, w)]),
            "approval_rate": rate(wkp[(sc, w, doc)], n)} for (sc, w, doc), n in sorted(wkd.items())])

    # ---------------- process (capability level) ----------------
    decided, decided_reason = Counter(), defaultdict(Counter)
    for r in rows:
        if r["approved"]:
            continue
        if r["step"] == "execution":
            st_ = next(s for s in STEPS if "TECHNICAL_ERROR" in r[s + "_decision_details"])
        elif r["step"] == "none":
            st_ = "classification" if r["reason"] == "NO_DOCUMENT_TYPE" else "decision"
        elif r["step"] == "watchlist":
            st_ = "watchlist_screening"
        else:
            st_ = r["step"]
        decided[st_] += 1
        decided_reason[st_][r["reason"]] += 1
    plan = [("usability", "Document", "Is the ID photo usable?"), ("classification", "Document", "Was a document type returned?"),
            ("image_checks", "Document", "Any sign of manipulation?"), ("extraction", "Document", "Were the fields read?"),
            ("data_checks", "Document", "Is the data consistent?"), ("liveness", "Selfie", "Is a live person present?"),
            ("similarity", "Selfie", "Does the face match the ID?"), ("watchlist_screening", "Screening", "Any watchlist hit?"),
            ("decision", "Decision", "Final recorded outcome")]
    process = []
    for order_, (st_, track, q) in enumerate(plan, 1):
        if st_ == "classification":
            reached = sum(norm(r["usability_decision"]) == "PASSED" for r in rows)
            okc = sum(norm(r["usability_decision"]) == "PASSED" and bool(r["data_type"]) for r in rows)
            counts, not_exec = Counter({"PASSED": okc, "REJECTED": reached - okc}), len(rows) - reached
        elif st_ == "decision":
            counts = Counter(r["decision"] for r in rows)
            counts["PASSED"] += counts.pop("APPROVED", 0)
            reached, not_exec = len(rows), 0
        else:
            counts = Counter(norm(r[st_ + "_decision"]) for r in rows)
            not_exec = counts.pop("NOT_EXECUTED", 0) + counts.pop("NOT_RECORDED", 0)
            reached = len(rows) - not_exec
        top = decided_reason[st_].most_common(1)
        process.append({"order": order_, "step": st_, "track": track, "question": q, "reached": reached,
                        "passed": counts["PASSED"], "warning": counts["WARNING"], "rejected": counts["REJECTED"],
                        "not_executed": not_exec, "decided_here": decided[st_], "top_reason": top[0][0] if top else "",
                        "top_reason_n": top[0][1] if top else 0})
    assert sum(p["decided_here"] for p in process) == len(rows) - apA - apB
    write("process_steps.csv", list(process[0].keys()), process)

    profile = []
    for sc in ("ALL", "MEX", "ARG"):
        sub = [r for r in rows if sc in ("ALL", r["country"])]
        bc, bp = Counter(age_band(r) for r in sub), Counter(age_band(r) for r in sub if r["approved"])
        for band in AGE_BANDS:
            profile.append({"id": f"{sc}-{band}", "country": sc, "age_band": band, "n": bc[band], "share": rate(bc[band], len(sub)),
                            "approval_rate": rate(bp[band], bc[band])})
    write("profile.csv", ["id", "country", "age_band", "n", "share", "approval_rate"], profile)

    # ---------------- compliance extract findings ----------------
    appr = [r for r in rows if r["approved"]]
    minors = [r for r in appr if r["year_birth"] and int(r["year_birth"]) >= 2006]
    compliance = [
        ("minors", "Approved records with birth year 2006 or later", len(minors),
         f"{sum(r['country'] == 'ARG' for r in minors):,} with an Argentine document. If the extracted birth year is right, the person was under 18 in 2023.",
         "Extraction error; a policy that allows minors in some product; an approval record that never became an enabled account.",
         "Compare with raw vendor responses and document images for a sample; check the age policy per country; check account state.",
         "compliance"),
        ("no_screening", "Approved records with no screening result in the extract", sum(1 for r in appr if r["watchlist_screening_decision"] in ("", "NOT_EXECUTED")),
         "Watchlist field blank (85) or NOT_EXECUTED (1).", "Screening ran in another system or a later step; field not exported.",
         "Look up screening records for these users in the screening system; confirm whether an account was enabled.", "compliance"),
        ("watchlist_warning", "Approved records with a watchlist WARNING", sum(1 for r in appr if r["watchlist_screening_decision"] == "WARNING"),
         "A potential match that should be resolved before approval.", "Warnings cleared in manual review that the extract does not show.",
         "Retrieve review dispositions; confirm who cleared each case and when.", "compliance"),
        ("label_mismatch", "Outcome disagrees between the two files", sum(1 for r in rows if r["decision_label"] != r["decision"]),
         "8 'OK' labels on approved records; 1 approved in the summary but REJECTED in details.", "A difference in the export field map.",
         "Reconcile against the system of record.", "data"),
        ("non_standard", "Non-standard capability values", passes, "'PASSES' instead of 'PASSED' in 3 fields.", "Manual edits or an export bug.",
         "Fix at source; add schema checks to the extract.", "data"),
    ]
    write("compliance.csv", ["id", "finding", "n", "detail", "alternatives", "validation", "owner"],
          [dict(zip(["id", "finding", "n", "detail", "alternatives", "validation", "owner"], c)) for c in compliance])

    # ---------------- hypotheses ----------------
    exec_inc = next(i for i in incidents if i["id"] == "exec_errors")
    live_inc = next(i for i in incidents if i["id"] == "liveness_spike")
    arg_inc = next(i for i in incidents if i["id"] == "fraud_arg")
    mex_inc = next(i for i in incidents if i["id"] == "fraud_mex")
    mex_unc_a = sum(1 for r in mexA if r["doc"] == "UNCLASSIFIED") / len(mexA)
    mex_unc_b = sum(1 for r in mexB if r["doc"] == "UNCLASSIFIED") / len(mexB)
    face_a, face_b = ca["Face match"] / nA, cb["Face match"] / nB
    hyps = [
        ("h_exec", "Execution errors on Sep 1–2 turned applicants into rejections", "exec_tech_errors",
         f"{exec_inc['observed']} TECHNICAL_ERROR rejections on two days in both countries. Usability NOT_EXECUTED; document checks and face match skipped; liveness passed in all {exec_inc['liveness_passed']}; screening passed in {exec_inc['screening_passed']}.",
         "A vendor incident; an ARQ integration or configuration fault (upload, file format, credentials); a network problem between ARQ and the vendor.",
         "ARQ request logs, raw vendor responses, vendor incident report, whether these people retried or were later approved.",
         "Pull logs and raw responses for both days; ask the vendor for an incident report; check later activity of the affected users.",
         "Whether the fault is ours or the vendor's (fix, SLA claim, or both). The hold-and-retry rule is useful in both cases."),
        ("h_liveness", "Liveness quality failures on Sep 1 and Sep 6 were caused by a vendor fault", "liveness_spike",
         f"{live_inc['observed']} BAD_QUALITY / FACE_NOT_FULLY_VISIBLE on two days, both countries, codes rare otherwise; a third-party copy of the vendor status page reports liveness incidents on these dates.",
         "An ARQ app release or capture change on those days; an SDK version change.",
         "App and SDK version per transaction; intraday timestamps; vendor confirmation that ARQ's region was affected.",
         "Compare with the release log; ask the vendor for the affected-transaction list.",
         "Whether to escalate commercially, and whether a retake policy for these codes is worth a test."),
        ("h_attack", "The Aug 24 Argentina burst was coordinated fraud", "fraud_arg",
         f"Argentine volume {arg_inc['volume']} vs a typical {arg_inc['baseline_volume']}; {arg_inc['observed']} manipulation signals; {arg_inc['liveness_passed']} passed liveness and {arg_inc['face_passed']} passed face match.",
         "A wave of false positives from the vendor model at the time of a marketing push; a campaign that attracted low-quality applicants; duplicate submissions.",
         "Adjudication of a sample, device and IP data, acquisition channel, cross-transaction links.",
         "Review a random sample of flagged cases; check acquisition channel for the day; ask the vendor about repeated faces or backgrounds.",
         "Whether to add pre-vendor velocity and device controls, and how to report attack traffic separately."),
        ("h_ine", "The Sep 14–19 Mexico INE flags reflect a vendor rule or model change", "fraud_mex",
         f"{mex_inc['observed']} manipulation signals on INE cards with no volume surge ({mex_inc['volume']} vs {mex_inc['baseline_volume']} typical); {mex_inc['liveness_passed']} passed liveness.",
         "A quieter fraud campaign; a new INE card version the model mis-scores.",
         "Vendor release notes for that week; adjudication of a sample; registry validation of the credentials.",
         "Sample review with the vendor; registry check on a sample if available.",
         "Whether INE flags should route to review instead of auto-decline."),
        ("h_mex_docs", "Mexico's higher 'no document type' share comes from document choice or capture, not one defect", "mex_docs",
         f"No document type returned for {mex_unc_a:.1%} of Mexican decisions in the prior period and {mex_unc_b:.1%} in the recent one. Argentina has almost none. {next(m['n_b'] for m in mex_rows if m['group']=='No reason code'):,} recent Mexican rejections have no reason code.",
         "Documents outside the accepted list; poor captures the vendor cannot classify; issuer-country mismatch; document configuration; vendor gaps for some INE versions.",
         "Image sample with the vendor, the document type the user selected, the accepted-document configuration, app version.",
         "Review 100 recent cases with the vendor; compare configuration history; split by app version once logged.",
         "Choose between a document picker, a configuration change or a vendor escalation."),
        ("h_face", "Face-match failures are a large problem from before the drop, partly from old ID photos", "face_review",
         f"Face match was {face_a:.2%} of prior-period decisions and {face_b:.2%} of recent ones: it improved, so it did not cause the drop. Mexican national ID cards fail face match more often than INE cards.",
         "Impostors; poor light on the selfie; card type.", "Adjudication of a sample; document issue date.",
         "Review a sample of NO_MATCH and NOT_POSSIBLE cases.",
         "Whether a review queue or registry face check is worth its cost; any threshold change needs risk validation."),
    ]
    write("hypotheses.csv", ["id", "hypothesis", "related", "evidence", "alternatives", "missing", "next", "decision"],
          [dict(zip(["id", "hypothesis", "related", "evidence", "alternatives", "missing", "next", "decision"], h)) for h in hyps])

    # ---------------- recovery scenarios ----------------
    # Populations are disjoint by primary reason in the recent period.
    def no_other_fail(sub):
        return sum(1 for r in sub if failing_checks(r) <= 1) / len(sub) if sub else 0
    win_exec = [r for r in B if not r["approved"] and r["date"] in INCIDENTS[1]["dates"] and r["driver"] == "Execution error"]
    win_live = [r for r in B if not r["approved"] and r["date"] in INCIDENTS[2]["dates"] and INCIDENTS[2]["narrow"](r)]
    steady_live = [r for r in B if r["driver"] == "Selfie / liveness" and r not in win_live]
    mex_doc = [r for r in B if r["country"] == "MEX" and r["driver"] in ("No document type, no reason code", "Unsupported or incomplete document")]
    capture = [r for r in B if r["driver"] in ("Image quality", "Screen or paper copy")]
    face_warn = [r for r in B if r["driver"] == "Face match" and r["similarity_decision"] == "WARNING"]
    face_nomatch = [r for r in B if r["driver"] == "Face match" and r["similarity_decision"] == "REJECTED"]
    proxy = lambda sub: sum(approval([r for r in A if r["country"] == c]) * sum(1 for x in sub if x["country"] == c) for c in ("MEX", "ARG")) / len(sub)
    POP = {
        "tech_error_hold": ("Execution errors (Sep 1–2)", win_exec, "Per comparable incident"),
        "liveness_retake_incident": ("Liveness quality failures on incident days", win_live, "Per comparable incident"),
        "liveness_retake": ("Other selfie / liveness failures", steady_live, "Every 30 days"),
        "mex_doc_guidance": ("Mexico: no document type or unsupported / incomplete document", mex_doc, "Every 30 days"),
        "capture_quality": ("Image quality and screen or paper copies", capture, "Every 30 days"),
        "review_queue": ("Face match: WARNING plus a share of NO_MATCH", face_warn + face_nomatch, "Every 30 days"),
    }
    # (eligibility, reach, return, remediation, subsequent approval multiplier) per scenario. All assumptions.
    F = {
        "tech_error_hold": {"Conservative": (1.0, 0.9, 0.5, 0.8, 0.9), "Central": (1.0, 1.0, 0.75, 0.9, 1.0), "Optimistic": (1.0, 1.0, 1.0, 0.98, 1.0)},
        "liveness_retake_incident": {"Conservative": (None, 0.9, 0.4, 0.6, 0.9), "Central": (None, 1.0, 0.6, 0.75, 1.0), "Optimistic": (None, 1.0, 0.8, 0.9, 1.0)},
        "liveness_retake": {"Conservative": (None, 0.9, 0.4, 0.3, 0.9), "Central": (None, 1.0, 0.6, 0.45, 1.0), "Optimistic": (None, 1.0, 0.8, 0.6, 1.0)},
        "mex_doc_guidance": {"Conservative": (0.5, 0.9, 1.0, 0.2, 0.9), "Central": (0.7, 1.0, 1.0, 0.35, 1.0), "Optimistic": (0.85, 1.0, 1.0, 0.5, 1.0)},
        "capture_quality": {"Conservative": (0.7, 0.9, 1.0, 0.3, 0.9), "Central": (0.85, 1.0, 1.0, 0.45, 1.0), "Optimistic": (0.95, 1.0, 1.0, 0.6, 1.0)},
        "review_queue": {"Conservative": (None, 1.0, 1.0, 0.3, 1.0), "Central": (None, 1.0, 1.0, 0.45, 1.0), "Optimistic": (None, 1.0, 1.0, 0.6, 1.0)},
    }
    nomatch_share = {"Conservative": 0.0, "Central": 0.25, "Optimistic": 0.5}
    scen = []
    for aid, (label, sub, cadence) in POP.items():
        base_ok = no_other_fail(sub)
        for sname, (elig, reach, ret, rem, mult) in F[aid].items():
            n = len(sub)
            if aid == "review_queue":
                n = len(face_warn) + round(nomatch_share[sname] * len(face_nomatch))
            e = base_ok if elig is None else elig
            # a reviewer's approval is final; elsewhere unexecuted checks may still fail (prior-period approval rate as proxy)
            sub_ap = mult if aid == "review_queue" else proxy(sub) * mult
            rec = n * e * reach * ret * rem * sub_ap
            scen.append({"id": f"{aid}-{sname}", "action": aid, "scenario": sname, "population": label, "cadence": cadence,
                         "observed_n": n, "no_other_failing_share": round(base_ok, 3), "eligibility": round(e, 3), "reach": reach,
                         "return_rate": ret, "remediation": rem, "subsequent_approval": round(sub_ap, 3),
                         "recovered": round(rec), "recovered_pp": round(100 * rec / nB, 2) if cadence == "Every 30 days" else ""})
    write("scenarios.csv", list(scen[0].keys()), scen)
    # control gaps: approvals that may need reversing if findings are confirmed. Kept apart from recovery.
    minorsB = sum(1 for r in B if r["approved"] and r["year_birth"] and int(r["year_birth"]) >= 2006)
    noscrB = sum(1 for r in B if r["approved"] and r["watchlist_screening_decision"] in ("", "NOT_EXECUTED"))
    gap = minorsB + noscrB
    totals = []
    for sname in ("Conservative", "Central", "Optimistic"):
        steady = sum(s_["recovered"] for s_ in scen if s_["scenario"] == sname and s_["cadence"] == "Every 30 days")
        incident = sum(s_["recovered"] for s_ in scen if s_["scenario"] == sname and s_["cadence"] == "Per comparable incident")
        totals.append({"scenario": sname, "steady_30d": steady, "steady_pp": round(100 * steady / nB, 2),
                       "approval_with_steady": round((apB + steady) / nB, 4), "per_incident": incident,
                       "control_gap_n": gap, "control_gap_10": -round(0.1 * gap), "control_gap_50": -round(0.5 * gap), "control_gap_all": -gap,
                       "control_gap_all_pp": round(-100 * gap / nB, 2)})
    write("scenario_totals.csv", list(totals[0].keys()), totals)

    # ---------------- experiment designs ----------------
    def n_per_arm(p1, p2, alpha_z=1.96, power_z=0.8416):
        pbar = (p1 + p2) / 2
        num = (alpha_z * math.sqrt(2 * pbar * (1 - pbar)) + power_z * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        return math.ceil(num / (p2 - p1) ** 2)
    mex_daily = len(mexB) / 30
    rMEX_B = approval(mexB)
    n_mex = n_per_arm(rMEX_B, rMEX_B + 0.02)
    live_daily = len(steady_live) / 30
    n_live = n_per_arm(0.05, 0.15)
    experiments = [
        ("exp_mex_docs", "mex_doc_guidance", "Optimisation experiment",
         "Pictures of the accepted documents, shown to Mexican applicants before capture, increase eventual approval.",
         "People who start KYC with a Mexican document. Exclude staff and test accounts, and people already approved.",
         "Person (person_id), assigned at first kyc_started, sticky across attempts.",
         "Eventual approval within 7 days of first start.", "7 days per person plus 7 days to mature the last cohort.",
         "+2.0 pp on eventual approval.",
         f"With the recent Mexican approval rate ({round(rMEX_B, 4):.1%}) as a stand-in baseline, the sample is about {n_mex:,} people per arm (95% confidence, 80% power). At about {mex_daily:,.0f} Mexican decisions a day that is roughly {math.ceil(2 * n_mex / mex_daily)} days at a 50/50 split. Recompute once start-based data exists.",
         "Start-to-submit rate, time to decision, fraud-signal rate, support contacts.",
         "Start at 10% for 3 days to check events, then 50/50. Expand if the primary outcome improves by at least the minimum and guardrails hold. Roll back if start-to-submit falls more than 2 pp or fraud signals rise more than 0.5 pp."),
        ("exp_liveness", "liveness_retake", "Optimisation experiment",
         "One guided retake after BAD_QUALITY or FACE_NOT_FULLY_VISIBLE from liveness increases eventual approval and does not increase fraud.",
         "People whose first liveness result is BAD_QUALITY or FACE_NOT_FULLY_VISIBLE and who have no fraud signal. Exclude ID_USED_AS_SELFIE and any manipulation label.",
         "Person, assigned at the first eligible liveness failure, sticky.",
         "Eventual approval within 7 days of the failure.", "7 days plus 7 days to mature.", "+10 pp on eventual approval in the eligible group.",
         f"If about 5% of the eligible group is approved later without a retake (not measurable yet), the sample is about {n_live:,} people per arm. At about {live_daily:,.0f} eligible people a day (recent non-incident rate) that is roughly {math.ceil(2 * n_live / live_daily)} days. Needs the real baseline from instrumentation.",
         "Fraud-signal rate and confirmed fraud among retake approvals, liveness spoof labels, vendor cost per approval, time to decision.",
         "Needs Risk sign-off before launch. Start 50/50. Roll back on any confirmed spoof or a fraud-signal rate among retake approvals above control."),
        ("exp_exec_errors", "tech_error_hold", "Remediation of a confirmed failure (not an A/B test)",
         "If we hold and retry decisions with TECHNICAL_ERROR, execution faults do not cause final rejections.",
         "All decisions with NOT_EXECUTED / TECHNICAL_ERROR in any capability.", "Not randomised: a fix for a known failure must go to all users.",
         "Share of TECHNICAL_ERROR cases resolved after retry, and their eventual approval within 7 days.", "Every incident; reviewed weekly.",
         "Zero final rejections with TECHNICAL_ERROR.", "Not applicable. Compare with the same incident type before the change.",
         "Retry volume and vendor cost, time to decision, approvals among retried cases that later show fraud.",
         "Ship behind a flag. Cap retries at three with backoff. Then hold the case for a manual decision. Roll back if retries amplify an outage or cost exceeds the agreed cap."),
        ("exp_review", "review_queue", "Capacity-limited pilot",
         "A manual review of face-match WARNINGs approves a large share of genuine applicants, with acceptable quality.",
         "Face-match WARNING (NOT_POSSIBLE) cases with no fraud signal; later a sample of NO_MATCH.", "Case, by staggered weekly rollout.",
         "Reviewer approval rate and 7-day eventual approval.", "4 weeks.", "Agree with Ops and Risk; for example 30% of reviewed cases approved.",
         "Capacity first: recent volumes are small enough for a pilot (see Plan), but cost per review and service level need Ops input.",
         "Second-reviewer agreement on 10% of cases, review turnaround, later fraud among approvals.",
         "Stop if agreement falls below an agreed threshold or turnaround breaches the service level."),
    ]
    write("experiments.csv", ["id", "action", "kind", "hypothesis", "population", "unit", "primary", "window", "mde", "sample", "guardrails", "rules"],
          [dict(zip(["id", "action", "kind", "hypothesis", "population", "unit", "primary", "window", "mde", "sample", "guardrails", "rules"], e)) for e in experiments])

    # ---------------- value model: observed quantities and the inputs it needs ----------------
    value_inputs = [
        ("value_per_activated", "Value per activated customer", "USD", "Contribution in the first 12 months after activation, not revenue recognised in the next 12 months."),
        ("activation_rate", "Activation rate after approval", "share", "Approved records that become active customers; approval is not account enablement."),
        ("paid_share", "Share of applicants from paid channels", "share", "Only paid applicants carry acquisition cost; organic declines are not wasted spend."),
        ("cac_paid", "Acquisition cost per paid applicant", "USD", "Spend per paid applicant who reached KYC."),
        ("billable_per_decision", "Billable vendor transactions per decision", "count", "One recorded decision may involve several or no billable transactions."),
        ("cost_per_transaction", "Vendor cost per billable transaction", "USD", "From the vendor contract."),
        ("review_cost", "Cost per manual review", "USD", "Loaded cost, with quality checks on a sample."),
        ("build_cost", "Implementation cost of the repeated-cause actions", "USD", "Engineering, design and vendor work for the actions behind the recoverable approvals."),
        ("run_cost_month", "Run cost per month", "USD", "Extra checks, retries, review and support."),
    ]
    # market-based presets (low / mid / high), derived in value_presets.py from fetched sources
    import value_presets as vp
    central = {s_["action"]: s_ for s_ in scen if s_["scenario"] == "Central"}
    lr = central["liveness_retake"]
    ctx = dict(review_n=central["review_queue"]["observed_n"],
               retake_attempts=lr["observed_n"] * lr["eligibility"] * lr["reach"] * lr["return_rate"],
               annual_decisions=len(rows) / len(dates) * 365)
    presets = vp.build(ctx)
    assert set(presets) == {v[0] for v in value_inputs}
    vrows = []
    for vid, label, unit, note in value_inputs:
        p = presets[vid]
        lo, mid, hi = p["vals"]
        assert lo <= mid <= hi, vid
        if unit == "share":
            assert 0 <= lo and hi <= 1, vid
        tidy = lambda v: int(v) if float(v).is_integer() and abs(v) >= 1 else round(v, 3)
        vrows.append(dict(id=vid, label=label, unit=unit, note=note, low=tidy(lo), mid=tidy(mid), high=tidy(hi),
                          cautious=vp.CAUTIOUS[vid], kind=p["kind"], sources=p["sources"], short=p["short"], basis=p["basis"]))
    write("value_inputs.csv", list(vrows[0].keys()), vrows)
    write("value_sources.csv", list(vp.SOURCES[0].keys()), vp.SOURCES)
    used = {s_ for r in vrows for s_ in r["sources"].split()}
    assert used == {s_["id"] for s_ in vp.SOURCES}, used ^ {s_["id"] for s_ in vp.SOURCES}

    # value results per preset and scenario: the same formulas the dashboard runs on live inputs
    attack_excess = next(i for i in incidents if i["id"] == "fraud_arg")["excess_volume"]
    unsucc_b = nB - apB
    vres = []
    for pi, pname in enumerate(vp.PRESETS):
        x = {r["id"]: r[r["cautious"]] if pname == "Cautious" else r[pname.lower()] for r in vrows}
        for t in totals:
            rec = t["steady_30d"]
            review_n = next(s_ for s_ in scen if s_["action"] == "review_queue" and s_["scenario"] == t["scenario"])["observed_n"]
            act = rec * x["activation_rate"]
            res = [
                ("activated", "Activated customers from recoverable approvals, per 30 days", "int", round(act)),
                ("cohort_value", "First-year value of one 30-day cohort", "usd", act * x["value_per_activated"]),
                ("annualised", "Same, if every 30 days repeats for a year", "usd", act * x["value_per_activated"] * 365 / 30),
                ("vendor_declined", "Historical vendor spend on recent not-approved decisions", "usd", unsucc_b * x["billable_per_decision"] * x["cost_per_transaction"]),
                ("vendor_attack", "Vendor spend avoidable on suspected extra attack traffic", "usd", attack_excess * x["billable_per_decision"] * x["cost_per_transaction"]),
                ("paid_declined", "Historical paid acquisition spend on recent not-approved applicants", "usd", unsucc_b * x["paid_share"] * x["cac_paid"]),
                ("review_30d", "Review cost per 30 days for the review-pilot population", "usd", review_n * x["review_cost"]),
                ("breakeven", "Break-even first-year value per activated customer", "usd", (x["build_cost"] / 12 + x["run_cost_month"]) / act if act else ""),
            ]
            for rid, rl, ru, rv in res:
                vres.append(dict(preset=pname, scenario=t["scenario"], id=rid, label=rl, unit=ru, value=round(rv, 2) if rv != "" else ""))
    write("value_results.csv", list(vres[0].keys()), vres)
    print("value presets", {r["id"]: (r["low"], r["mid"], r["high"]) for r in vrows})
    print("value results Mid/Central", {r["id"]: r["value"] for r in vres if r["preset"] == "Mid" and r["scenario"] == "Central"})

    # ---------------- headline figures ----------------
    exp_approvals_b = nB * rA
    kpis = [
        ("first_date", dates[0], "First day in the extract", "date"),
        ("split_date", SPLIT, "First day of the recent period", "date"),
        ("last_a_date", max(r["date"] for r in A), "Last day of the prior period", "date"),
        ("last_date", dates[-1], "Last day in the extract", "date"),
        ("days_total", len(dates), "Days in the extract", "int"),
        ("research_date", RESEARCH_DATE, "Vendor research date", "date"),
        ("total_users", len(rows), "Recorded decisions", "int"),
        ("n_a", nA, "Recorded decisions, prior period", "int"),
        ("n_b", nB, "Recorded decisions, recent period", "int"),
        ("approved_a", apA, "Approved, prior period", "int"),
        ("approved_b", apB, "Approved, recent period", "int"),
        ("approval_a", round(rA, 4), "Approval rate, prior period", "pct"),
        ("approval_b", round(rB, 4), "Approval rate, recent period", "pct"),
        ("delta_pp", round(100 * (rB - rA), 2), "Change in approval rate", "pp"),
        ("approved_change", apB - apA, "Change in approved count", "int"),
        ("volume_effect", round(exp_approvals_b - apA), "Approved-count change from lower volume (at the prior rate)", "int"),
        ("rate_effect", round(apB - exp_approvals_b), "Approved-count change from the lower rate", "int"),
        ("unsuccessful_a", nA - apA, "Not approved, prior period", "int"),
        ("unsuccessful_b", nB - apB, "Not approved, recent period", "int"),
        ("decline_a", round(1 - rA, 4), "Not-approved share, prior period", "pct"),
        ("decline_b", round(1 - rB, 4), "Not-approved share, recent period", "pct"),
        ("warning_a", sum(r["decision"] == "WARNING" for r in A), "Warnings, prior period", "int"),
        ("warning_b", sum(r["decision"] == "WARNING" for r in B), "Warnings, recent period", "int"),
        ("rejected_b", sum(r["decision"] == "REJECTED" for r in B), "Rejected, recent period", "int"),
        ("mex_approval_a", round(approval(by(A, "MEX")), 4), "Mexico approval rate, prior period", "pct"),
        ("mex_approval_b", round(approval(by(B, "MEX")), 4), "Mexico approval rate, recent period", "pct"),
        ("arg_approval_a", round(approval(by(A, "ARG")), 4), "Argentina approval rate, prior period", "pct"),
        ("arg_approval_b", round(approval(by(B, "ARG")), 4), "Argentina approval rate, recent period", "pct"),
        ("mex_share_a", round(len(by(A, "MEX")) / nA, 4), "Mexican-document share of decisions, prior period", "pct"),
        ("mex_share_b", round(len(by(B, "MEX")) / nB, 4), "Mexican-document share of decisions, recent period", "pct"),
        ("selected_incident", len([r for r in B if id(r) in selected]), "Unsuccessful decisions matching an incident signature in its window", "int"),
        ("approval_excl_selected", round(apB / (nB - len([r for r in B if id(r) in selected])), 4), "Recent approval rate after removing those records (descriptive only)", "pct"),
        ("approval_a_excl_days", round(approval([r for r in A if r["date"] not in INCIDENT_DAYS]), 4), "Prior-period approval rate without incident days", "pct"),
        ("approval_b_excl_days", round(approval([r for r in B if r["date"] not in INCIDENT_DAYS]), 4), "Recent-period approval rate without incident days", "pct"),
        ("delta_excl_days_pp", round(100 * (approval([r for r in B if r["date"] not in INCIDENT_DAYS]) - approval([r for r in A if r["date"] not in INCIDENT_DAYS])), 2), "Change in approval rate without incident days", "pp"),
        ("share_recent_on_incident_days", round(sum(1 for r in B if r["date"] in INCIDENT_DAYS) / nB, 4), "Share of recent decisions that fall on incident days", "pct"),
        ("incident_days_n", len({r["date"] for r in B if r["date"] in INCIDENT_DAYS}), "Incident days in the recent period", "int"),
        ("delta_rel", round(rB / rA - 1, 4), "Relative change in the approval rate", "pct"),
        ("approved_change_rel", round(apB / apA - 1, 4), "Relative change in the approved count", "pct"),
        ("volume_effect_share", round((exp_approvals_b - apA) / (apB - apA), 4), "Share of the approved-count change from lower volume", "pct"),
        ("rate_effect_share", round((apB - exp_approvals_b) / (apB - apA), 4), "Share of the approved-count change from the lower rate", "pct"),
        ("incident_excess_base", inc_total["base"], "Incident failures above baseline (base estimate)", "int"),
        ("incident_excess_low", min(inc_total[v] for v in ("base", "wide_window", "broad_signature", "recent_baseline")), "Incident failures above baseline, low end of sensitivity range", "int"),
        ("incident_excess_high", max(inc_total[v] for v in ("base", "wide_window", "broad_signature", "recent_baseline")), "Incident failures above baseline, high end of sensitivity range", "int"),
        ("incident_all_matching", inc_total["all_matching"], "Every failure of the same pattern in the windows (old method)", "int"),
        ("incident_share_unsuccessful", rate(inc_total["base"], nB - apB), "Base incident estimate as a share of recent unsuccessful decisions", "pct"),
        ("incident_contribution_pp", round(-100 * inc_total["base"] / nB, 2), "Base incident estimate as approval-rate points", "pp"),
        ("multi_fail_b", sum(1 for r in unsB if failing_checks(r) >= 2), "Recent unsuccessful decisions with two or more failed or warning checks", "int"),
        ("liveness_incident_face", sum(1 for r in win_live if r["similarity_decision"] in ("REJECTED", "WARNING")), "Liveness-spike cases that also had a face-match warning or rejection", "int"),
        ("liveness_incident_n", len(win_live), "Liveness-spike cases", "int"),
        ("exec_liveness_passed", exec_inc["liveness_passed"], "Execution-error cases with liveness passed", "int"),
        ("exec_screening_passed", exec_inc["screening_passed"], "Execution-error cases with screening passed", "int"),
        ("mex_nodoc_a", round(mex_unc_a, 4), "Mexican decisions with no document type, prior period", "pct"),
        ("mex_nodoc_b", round(mex_unc_b, 4), "Mexican decisions with no document type, recent period", "pct"),
        ("arg_usability_rejects", sum(1 for r in rows if r["country"] == "ARG" and r["usability_decision"] in ("REJECTED", "WARNING") and r["usability_decision_details"] != "LIVENESS_UNDETERMINED"), "Argentine usability rejections or warnings", "int"),
        ("mex_usability_rejects", sum(1 for r in mex if r["usability_decision"] in ("REJECTED", "WARNING") and r["usability_decision_details"] != "LIVENESS_UNDETERMINED"), "Mexican usability rejections or warnings", "int"),
        ("face_a", round(face_a, 4), "Face-match share of decisions, prior period", "pct"),
        ("face_b", round(face_b, 4), "Face-match share of decisions, recent period", "pct"),
        ("yob_blank_rejected", yb_blank_rejected, "Records with no birth year that were rejected", "int"),
        ("yob_blank", blank["year_birth"], "Records with no birth year", "int"),
        ("avg_daily", round(len(rows) / len(dates)), "Average decisions per day", "int"),
        ("peak_daily", max(Counter(r["date"] for r in rows).values()), "Most decisions in one day", "int"),
    ]
    write("kpis.csv", ["metric", "value", "label", "unit"], [{"metric": m, "value": v, "label": l, "unit": u} for m, v, l, u in kpis])

    # ---------------- open questions: what to confirm with ARQ before we act on the findings ----------------
    sc_c = {s_["action"]: s_ for s_ in scen if s_["scenario"] == "Central"}
    vol_effect = round(exp_approvals_b - apA)
    open_questions = [
        dict(id="q_row", order=1, topic="What a record is",
             question="Does each row hold a user's first, latest or final KYC attempt, and does the date mark the submission or the vendor's decision?",
             why="The headline is approval among recorded decisions. If rows are latest attempts, we cannot see earlier failures and retries, and the first-pass rate is lower than shown. If rows are final decisions, the warnings can be out of date.",
             changes="The metric definition (v2 to v3 in the registry), the retry hypotheses, and whether the bridge counts people or attempts.",
             who="Data platform or whoever produced the extract."),
        dict(id="q_starts", order=2, topic="Starts and abandonment",
             question="Is there any record, even weekly counts, of people who opened KYC and never submitted?",
             why=f"The brief defines the pass rate as people who start and finish. Without starts, completion and abandonment cannot be measured, and the {abs(vol_effect):,} fewer approvals from lower volume could be fewer starts, more abandonment, or both.",
             changes="Whether Phase 0 instrumentation is a prerequisite or a check on current data; how we read the volume effect; the completion metric status.",
             who="Mobile and platform engineering (app analytics, API logs)."),
        dict(id="q_flow", order=3, topic="Today's flow after a failure",
             question="What happens today after a TECHNICAL_ERROR or a liveness failure: does the user see the vendor's outcome, get a retake, or enter a review queue?",
             why=f"Hold-and-retry and the guided retake assume no retry exists. In the central scenario they recover {sc_c['tech_error_hold']['recovered']:,} approvals per comparable execution-error incident and {sc_c['liveness_retake']['recovered']:,} per 30 days on steady liveness failures.",
             changes="If a retry already exists, those recoverable counts shrink and the question becomes why retries fail; the Phase 0 hold-and-retry becomes a configuration check.",
             who="Product and the onboarding squad; the vendor integration owner."),
        dict(id="q_vendor", order=4, topic="Vendor setup",
             question="Which vendor product tier and data centre does ARQ use, and did ARQ receive incident notices for Sep 1, 2 and 6, 2023?",
             why=f"The vendor's status history shows liveness incidents on Sep 1 and 6 on its US data centre and nothing for Sep 2. The liveness spike is {live_inc['excess']:,} failures above baseline and the execution errors {exec_inc['excess']:,}.",
             changes="On another data centre the liveness attribution loses its vendor evidence; with notices, the execution errors have an owner and an SLA claim.",
             who="Vendor management; the vendor's account team."),
    ]
    write("open_questions.csv", list(open_questions[0].keys()), open_questions)


    # ---------------- risk register (ratings are judgement; evidence counts are from the extract) ----------------
    risks = [
        ("exec_final", "Execution errors or vendor faults recorded as final rejections", "Medium", "High", "platform",
         "Hold and retry on TECHNICAL_ERROR; vendor failover only after the orchestration work.", exec_inc["observed"], "recent TECHNICAL_ERROR rejections"),
        ("fraud_bursts", "Bursts of fraud signals, confirmed or not", "High", "Medium", "risk",
         "Adjudicate samples; pre-vendor velocity checks if fraud is confirmed.", cb["Fraud signal"], "recent fraud-signal decisions"),
        ("unexplained", "Mexican rejections that carry no reason code", "High", "High", "product",
         "Diagnose with the vendor before you choose a fix.", next(m["n_b"] for m in mex_rows if m["group"] == "No reason code"), "recent Mexican cases with no reason code"),
        ("control_findings", "Approvals that may conflict with policy (birth year, screening)", "Unknown", "High", "compliance",
         "Reconcile against policy, raw responses, reviews and account state.", compliance[0][2] + compliance[1][2] + compliance[2][2], "approved records to reconcile"),
        ("measurement_gap", "No measurement before submission or across attempts", "High", "Medium", "data",
         "Phase 0 instrumentation.", "", ""),
        ("vendor_change", "Vendor-side faults or changes that go unnoticed", "Medium", "Medium", "vendors",
         "Per-code alerts; status-page subscription; incident confirmation process.", live_inc["observed"], "liveness-spike decisions"),
        ("face_mismatch", "Genuine people who fail face match", "Medium", "Medium", "ops",
         "Review pilot; threshold changes only with risk validation.", cb["Face match"], "recent face-match decisions"),
        ("review_capacity", "New manual review without a capacity or quality plan", "Medium", "Medium", "ops",
         "Capacity plan, service level and a second review of a sample before launch.", "", ""),
    ]
    names = {d[0]: d[1] for d in DEPARTMENTS}
    write("risks.csv", ["id", "risk", "likelihood", "impact", "owner", "mitigation", "evidence_n", "evidence_label"],
          [dict(zip(["id", "risk", "likelihood", "impact", "owner", "mitigation", "evidence_n", "evidence_label"], (r[0], r[1], r[2], r[3], names[r[4]], *r[5:])))
           for r in risks])

    # ---------------- proposed alert rules, replayed on the extract ----------------
    def daily_share(pred, sc="ALL"):
        num, den = Counter(), Counter()
        for r in rows:
            if sc in ("ALL", r["country"]):
                den[r["date"]] += 1
                num[r["date"]] += bool(pred(r))
        return {d: num[d] / den[d] for d in den}
    rules = [
        ("approval", "Daily approval rate", "ALL", "product", lambda r: r["approved"], "below", "prior median − 5 pp", lambda b: b - 0.05),
        ("exec_error", "Execution errors", "ALL", "platform", lambda r: r["driver"] == "Execution error", "above", "0.5% of decisions", lambda b: 0.005),
        ("fraud", "Fraud signals", "ALL", "risk", lambda r: r["driver"] == "Fraud signal", "above", "3× prior median, at least 1.5%", lambda b: max(3 * b, 0.015)),
        ("liveness_quality", "Liveness quality failures", "ALL", "vendors", lambda r: r["step"] == "liveness" and r["reason"] in ("BAD_QUALITY", "FACE_NOT_FULLY_VISIBLE"), "above", "0.5% of decisions", lambda b: 0.005),
        ("no_doctype_mex", "No document type, Mexico", "MEX", "product", lambda r: r["driver"] == "No document type, no reason code", "above", "prior median + 3 pp", lambda b: b + 0.03),
        ("face_match", "Face-match failures", "ALL", "ops", lambda r: r["driver"] == "Face match", "above", "prior median + 2 pp", lambda b: b + 0.02),
    ]
    alerts = []
    for aid, label, sc, owner, pred, direction, rule, thr_fn in rules:
        ds = daily_share(pred, sc)
        base = statistics.median(v for d, v in ds.items() if d < SPLIT)
        thr = thr_fn(base)
        fired = sorted(d for d in ds if (ds[d] < thr if direction == "below" else ds[d] > thr))
        firedA = [d for d in fired if d < SPLIT]
        firedB = [d for d in fired if d >= SPLIT]
        alerts.append({"id": aid, "metric": label, "scope": sc, "owner": names[owner], "normal": round(base, 4), "rule": rule,
                       "threshold": round(thr, 4), "days_prior": len(firedA), "days_recent": len(firedB),
                       "first_recent": firedB[0] if firedB else "", "fired_dates": " ".join(firedB)})
    write("alerts.csv", list(alerts[0].keys()), alerts)
    inc_first_days = {i["dates"][0] for i in INCIDENTS}
    caught = {i["id"]: any(i["dates"][0] in a["fired_dates"].split() for a in alerts) for i in INCIDENTS}

    comp = {c[0]: c[2] for c in compliance}
    n_capture_class = sum(cb[g] for g in DRIVERS if DRIVER_CLASS[g] == "Capture or document issue")
    write_actions(nB, cb, len(mex_doc), len(capture), len(face_warn), len(face_nomatch), exec_inc, live_inc, comp, caught,
                  sum(a["days_prior"] for a in alerts), n_capture_class=n_capture_class)
    # ---------------- quick review: the whole story in plain language ----------------
    KP = {m: v for m, v, _l, _u in kpis}
    BR = {b_["driver"]: b_["effect_pp"] for b_ in bridge}
    TOT = {t["scenario"]: t for t in totals}
    VR = {(r["preset"], r["scenario"], r["id"]): r["value"] for r in vres}
    VI = {r["id"]: r for r in vrows}
    INC = {i["id"]: i for i in incidents}
    p1 = lambda v: f"{100 * v:.1f}%"
    pts = lambda v: ("+" if v > 0 else "−") + f"{abs(v):.2f} points"
    usd0 = lambda v: f"${int(v + 0.5):,}"
    with open(os.path.join(OUT, "actions.csv"), newline="") as f:
        acts = list(csv.DictReader(f))
    assert {a["id"] for a in acts if a["phase"] == "0"} >= {"instrument_min", "tech_error_hold", "alerting", "compliance_reconcile", "investigate_fraud", "vendor_confirm"}
    assert {a["id"] for a in acts if a["phase"] == "1"} == {"liveness_retake", "mex_doc_guidance", "fraud_precheck", "qual_research", "vendor_bakeoff"}
    mid_be, mid_v = VR[("Mid", "Central", "breakeven")], VI["value_per_activated"]["mid"]
    cau_be, cau_v = VR[("Cautious", "Central", "breakeven")], VI["value_per_activated"][VI["value_per_activated"]["cautious"]]
    assert mid_v >= mid_be and cau_v < cau_be, (mid_v, mid_be, cau_v, cau_be)
    # (section, heading, goto tab, kind, text). kinds: lead, p, li, step, caution, chart (text = chart id),
    # t_fix / t_test / t_learn / t_build (plan tracks, as in tracks.csv). Every number is computed above, none is typed.
    DC = {d_["name"]: d_ for d_ in declines if d_["level"] == "class"}
    cls_share = lambda name: f"{100 * float(DC[name]['of_unsuccessful_b']):.0f}%"
    face_share = f"{100 * cb['Face match'] / (nB - apB):.0f}%"
    n_sources = len(vp.SOURCES)
    assert abs(KP["volume_effect_share"] + KP["rate_effect_share"] - 1) < 0.001
    Q = [
        ("result", "The result", "summary", "chart", "funnel"),
        ("result", "", "", "lead", f"The KYC pass rate decreased by {abs(KP['delta_pp']):.1f} points in the last 30 days: from {p1(KP['approval_a'])} to {p1(KP['approval_b'])}."),
        ("result", "", "", "li", f"Relative decrease: {100 * abs(KP['delta_rel']):.1f}%."),
        ("result", "", "", "li", f"Approved people: {100 * abs(KP['approved_change_rel']):.1f}% fewer ({abs(KP['approved_change']):,} people)."),
        ("result", "", "", "li", f"Of the drop, {100 * KP['volume_effect_share']:.0f}% is because of fewer decisions and {100 * KP['rate_effect_share']:.0f}% is because of the lower rate."),
        ("result", "", "", "li", f"By country: Mexico from {p1(KP['mex_approval_a'])} to {p1(KP['mex_approval_b'])}, Argentina from {p1(KP['arg_approval_a'])} to {p1(KP['arg_approval_b'])}."),
        ("result", "", "", "term", "Pass rate here = approved decisions ÷ all recorded decisions. The data cannot show the people who started KYC and did not finish."),
        ("data", "What the data can show", "measurement", "p", "The data has one decision record for each person, with a date. It does not show when a person starts KYC."),
        ("data", "", "", "p", "Because of this, we cannot measure the completion rate. We measure the pass rate of recorded decisions."),
        ("data", "", "", "caution", "CAUTION: Do not report this pass rate as the completion rate."),
        ("causes", "Why it fell", "drivers", "chart", "causes"),
        ("causes", "", "", "p", f"Of the {nB - apB:,} not-approved decisions, {cls_share('Unexplained or identity mismatch')} are unexplained or identity mismatches and {cls_share('Capture or document issue')} are capture or document problems. Fraud signals are {cls_share('Fraud signal (not adjudicated)')} and execution errors are {cls_share('Execution error')}."),
        ("causes", "", "", "p", "Four reasons give most of the decrease. The second chart shows how much each reason moved the pass rate."),
        ("causes", "", "", "li", f"Fraud signals: {pts(BR['Fraud signal'])}. The vendor found more images that look altered or fake."),
        ("causes", "", "", "li", f"Execution errors: {pts(BR['Execution error'])}. On Sep 1–2, some checks did not run, and the system rejected these people."),
        ("causes", "", "", "li", f"Selfie and liveness failures: {pts(BR['Selfie / liveness'])}. The vendor status page shows liveness incidents on Sep 1 and Sep 6."),
        ("causes", "", "", "li", f"Mexican documents with no document type: {pts(BR['No document type, no reason code'])}. The vendor did not identify these documents."),
        ("causes", "", "", "p", f"Face match failures decreased ({pts(BR['Face match'])}). But face match is still {face_share} of the not-approved decisions."),
        ("causes", "", "", "caution", "CAUTION: A fraud signal is not confirmed fraud. Do not call it fraud before an analyst examines it."),
        ("incidents", "Short incidents", "incidents", "chart", "days"),
        ("incidents", "", "", "p", f"We found about {KP['incident_excess_base']:,} more failures than usual in four short date windows (range {KP['incident_excess_low']:,} to {KP['incident_excess_high']:,})."),
        ("incidents", "", "", "li", "Aug 24, Argentina: more fraud signals and more traffic than usual."),
        ("incidents", "", "", "li", "Sep 1–2: execution errors in both countries."),
        ("incidents", "", "", "li", "Sep 1 and Sep 6: liveness failures."),
        ("incidents", "", "", "li", "Sep 14–19, Mexico: more fraud signals, with usual traffic."),
        ("incidents", "", "", "p", f"Without the {KP['incident_days_n']} incident days, the pass rate still decreased by {abs(KP['delta_excl_days_pp']):.2f} points. These days hold {100 * KP['share_recent_on_incident_days']:.0f}% of the recent decisions. We keep them and show both views."),
        ("incidents", "", "", "p", "The causes of these incidents are not confirmed. The vendor status page does not show an incident on Sep 2."),
        ("plan", "What to do", "plan", "p", "The plan has four tracks, the same as on the What to do tab. The first three tracks start now and run at the same time. "
                                            "The obvious fixes go first because they are cheap to try. The fourth track is the platform work for later."),
        ("plan", "", "", "t_fix", "Record each KYC start, each step and each final decision."),
        ("plan", "", "", "t_fix", "Hold each decision that has a TECHNICAL_ERROR. Do the check again before you reject the person."),
        ("plan", "", "", "t_fix", "Set alerts for sudden increases in failures. Compare the control findings with the source systems."),
        ("plan", "", "", "t_fix", "If the fraud is confirmed, add device checks before the vendor call."),
        ("plan", "", "", "t_test", "Test one guided retake for unclear selfies."),
        ("plan", "", "", "t_test", "In Mexico, show pictures of the accepted documents before the capture."),
        ("plan", "", "", "t_learn", "Examine a sample of fraud signals. Find which signals are real fraud."),
        ("plan", "", "", "t_learn", "Ask the vendor for incident reports for Sep 1, Sep 2 and Sep 6."),
        ("plan", "", "", "t_learn", "Talk to people who failed the capture. Start with support tickets, then interviews, then session replays, then eye tracking if the budget permits."),
        ("plan", "", "", "t_learn", "Decide on the vendor: if the vendor cannot explain Sep 1, 2 and 6, test a second vendor."),
        ("plan", "", "", "t_build", "Build a KYC orchestration and decision layer."),
        ("plan", "", "", "t_build", "Add government registry checks (INE, RENAPER)."),
        ("plan", "", "", "t_build", "Add a second verification vendor for failover."),
        ("gain", "What we gain", "gain", "chart", "gain"),
        ("gain", "", "", "p", f"If the tests work, the pass rate increases by about {TOT['Central']['steady_pp']:.1f} points (range {TOT['Conservative']['steady_pp']:.1f} to {TOT['Optimistic']['steady_pp']:.1f})."),
        ("gain", "", "", "p", f"That is about {TOT['Central']['steady_30d']:,} more approved people each 30 days (range {TOT['Conservative']['steady_30d']:,} to {TOT['Optimistic']['steady_30d']:,})."),
        ("gain", "", "", "p", "These numbers come from scenarios. They are not forecasts."),
        ("money", "Money", "gain", "p", f"The value model has no ARQ numbers. It uses benchmark values from {n_sources} public sources: vendor price lists, Nu Holdings filings, Liftoff reports and Mexican salary data."),
        ("money", "", "", "li", f"Middle benchmarks: the actions pay back in the first year. Each active customer gives {usd0(mid_v)} of value for {usd0(mid_be)} of cost."),
        ("money", "", "", "li", f"Cautious benchmarks: the actions do not pay back in the first year. Each active customer gives {usd0(cau_v)} of value for {usd0(cau_be)} of cost."),
        ("money", "", "", "caution", "CAUTION: Replace the benchmark values with ARQ values before you make a decision."),
        ("questions", "Questions for ARQ", "reference", "li", "Does each row show the first attempt, the last attempt or the final decision?"),
        ("questions", "", "", "li", "Does ARQ have records of people who started KYC but did not send their documents?"),
        ("questions", "", "", "li", "What does the app do after a TECHNICAL_ERROR or a liveness failure?"),
        ("questions", "", "", "li", "Which vendor product and which data centre does ARQ use?"),
        ("questions", "", "", "p", "The answers can change the results of this review."),
    ]

    # plain-language checks that a script can do: sentence length (20 words for steps and cautions, 25 for descriptive text),
    # no contractions, no progressive or perfect tenses, no -ing verb forms, at most 6 sentences per item.
    ING_OK = {"during", "thing", "something", "nothing", "string", "tracking"}
    STEP_KINDS = {"step", "caution", "t_fix", "t_test", "t_learn", "t_build"}
    def plain_sentences(t):
        return [x for x in re.split(r"(?<=[.?!:])\s+(?=[A-Z])", t.strip()) if x]
    longest = 0
    # the Quick review's plan groups are the four tracks of the What to do tab, in the same order
    q_tracks = list(dict.fromkeys(k for _s, _h, _g, k, _t in Q if k.startswith("t_")))
    assert q_tracks == ["t_" + t.lower() for t, _n, _d in TRACK_INFO], (q_tracks, TRACK_INFO)
    for sec, _h, _g, kind, t in Q:
        if kind == "chart":
            continue
        sents = plain_sentences(t)
        assert len(sents) <= 6, t
        for s_ in sents:
            words = [w_ for w_ in re.split(r"\s+", s_) if re.search(r"[A-Za-z0-9]", w_)]
            limit = 20 if kind in STEP_KINDS else 25
            assert len(words) <= limit, (len(words), s_)
            longest = max(longest, len(words))
            assert not re.search(r"\b\w+'(t|re|ve|ll|d|s)\b|n't\b", s_), ("contraction", s_)
            assert not re.search(r"\b(is|are|was|were|be|been)\s+\w+ing\b", s_), ("progressive", s_)
            assert not re.search(r"\b(has|have|had)\s+(\w+ed|been|done|made|found|shown)\b", s_), ("perfect tense", s_)
            for w_ in re.findall(r"[A-Za-z]+ing\b", s_):
                assert w_.lower() in ING_OK, ("-ing form", w_, s_)
    quick = [dict(order=i_ + 1, section=sec, heading=h, goto=g, kind=kind, text=t) for i_, (sec, h, g, kind, t) in enumerate(Q)]
    write("quick_review.csv", list(quick[0].keys()), quick)
    n_words = sum(len(re.split(r"\s+", r["text"])) for r in quick if r["kind"] != "chart")
    print(f"quick review: {len(quick)} items, {n_words} words, longest sentence {longest} words")

    # ---------------- assumptions: what the analysis assumes, and what changes if each one is wrong ----------------
    # One list for the deck, the note, the dashboard and the chat. Every number is computed here, none is typed.
    w_a, w_b = 100 * KP["warning_a"] / KP["n_a"], 100 * KP["warning_b"] / KP["n_b"]
    assumptions = [
        ("metric", "The metric",
         "The pass rate is approval among recorded decisions: PASSED or APPROVED, divided by all recorded decisions.",
         "If the team means start-to-finish completion, the Phase 0 events must exist first. The true completion rate can be higher or lower."),
        ("records", "Records and dates",
         "Each record is one person's final decision, on the date in the extract. Country is the country that issued the document.",
         "If records are first attempts, retries can approve some people later, so eventual approval is higher. Recent cases can still change."),
        ("warnings", "Warnings",
         "WARNING counts as not approved. It is not a confirmed rejection, because the review outcome is not in the data.",
         f"If reviewers approve every warning, both rates increase ({w_a:.2f} and {w_b:.2f} points) and the fall is {w_b - w_a:.2f} points smaller."),
        ("reasons", "One primary reason",
         "Each unsuccessful decision has one primary reason, in check order. TECHNICAL_ERROR comes first.",
         f"A fix for the primary reason does not always give an approval: {KP['multi_fail_b']:,} recent decisions failed two or more checks."),
        ("baseline", "The baseline",
         "The prior period is the normal level. An incident window counts only the failures above the prior-period rate.",
         f"If the prior period was unusually good, the windows explain less. The sensitivity checks give {KP['incident_excess_low']:,}–{KP['incident_excess_high']:,} failures above baseline."),
        ("signals", "Fraud and vendor",
         "Fraud labels are signals, not confirmed fraud. The vendor incidents are documented, but their effect on ARQ is not confirmed.",
         "If the signals are real fraud, those rejections are correct and the gain is smaller. If the vendor had no effect, the failures need another cause."),
        ("scenarios", "Recovery scenarios",
         "The populations are observed. The recovery factors (reach, return and remediation) are assumptions.",
         f"The gain can be anywhere from +{TOT['Conservative']['steady_pp']:.1f} to +{TOT['Optimistic']['steady_pp']:.1f} points, or outside that range. The experiments measure it."),
        ("money", "Money",
         "Money values come from market benchmarks, not from ARQ's contracts or finance data.",
         "Replace them with ARQ's values before a decision. With the Cautious values, the actions do not pay back in the first year."),
        ("org", "Owners and effort",
         "Owners are roles, not people. Effort sizes are estimates.",
         "Confirm the owners and the sizes with the team in Phase 0."),
    ]
    write("assumptions.csv", ["id", "order", "area", "assumption", "if_wrong"],
          [dict(id=a_, order=i_ + 1, area=b_, assumption=c_, if_wrong=d_) for i_, (a_, b_, c_, d_) in enumerate(assumptions)])

    write_org()
    write_vendor()

    write_manifest()

    # ---------------- checks ----------------
    assert (apA, apB) == (23887, 20942), (apA, apB)
    assert round(100 * (rB - rA), 2) == -5.4
    assert round(exp_approvals_b - apA) == -1587 and round(apB - exp_approvals_b) == -1358
    assert round(sum(b["effect_pp"] for b in bridge), 1) in (-5.4, -5.41, -5.39)
    for p in ("A", "B"):
        tot_cls = sum(d["share_" + p.lower()] for d in declines if d["level"] == "class")
        assert abs(tot_cls - (1 - (rA if p == "A" else rB))) < 1e-3, (p, tot_cls)
    print(f"A {nA} approved {apA} ({rA:.2%})  B {nB} approved {apB} ({rB:.2%})  Δ {100*(rB-rA):.2f} pp  count Δ {apB-apA}")
    print("bridge", [(b["driver"], b["effect_pp"]) for b in bridge])
    print("incidents", [(i["id"], i["observed"], i["expected"], i["excess"], i["excess_volume"]) for i in incidents])
    print("incident totals", inc_total)
    print("scenario totals", totals)
    print("experiments n", n_mex, n_live)
    print("files", len([f for f in os.listdir(OUT) if f.endswith(".csv")]))


# ---------------------------------------------------------------------------
# Roadmap. Role-based owners; effort sizes: S ≤ 2 engineer-weeks, M = 2–6
# engineer-weeks plus design, L = several teams for a quarter or more.
PHASES = {
    0: "Phase 0 · Weeks 0–2 · Measure and stabilise",
    1: "Phase 1 · Weeks 2–6 · Test the main fixes",
    2: "Phase 2 · Weeks 6–13 · Scale what works",
    3: "Phase 3 · Next two quarters · Platform work (large)",
}


# Tracks group the roadmap by the kind of work; phases stay the time axis.
TRACKS = {"Remediate": "Fix", "Control": "Fix", "Measure": "Fix", "Experiment": "Test", "Investigate": "Learn", "Platform": "Build"}
TRACK_INFO = [
    ("Fix", "Fix and measure", "Obvious fixes and the instruments to see them work. Cheap, start now."),
    ("Test", "Test the fixes", "Hypotheses that are quick to try as experiments."),
    ("Learn", "Learn why", "Investigations and research that run beside the fixes."),
    ("Build", "Build later", "Platform work that needs a quarter or more."),
]


def write_actions(nB, cb, n_mexdoc, n_capture, n_facewarn, n_nomatch, exec_inc, live_inc, comp, caught, false_prior, n_capture_class=0):
    A = [
        dict(id="instrument_min", phase=0, kind="Measure", area="Measurement", title="Minimum funnel instrumentation",
             action="Emit the nine KYC events (start, document, selfie, submission, vendor result, decision, review, account state) with person, session and attempt ids and app/SDK version.",
             hypothesis="", evidence="The extract cannot measure starts, completion, abandonment, retries or time to decision.",
             eligible="Every KYC session", eligible_n="", outcome="Completion, eventual approval and abandonment become measurable for cohorts that start after the release.",
             confidence="High", accountable="data", participants="platform, mobile, product, legal", dependencies="Event schema sign-off; privacy review of fields.",
             effort="M (assumed 3–4 engineer-weeks across backend and mobile)", acceptance="Events for 99% of sessions in a daily reconciliation against vendor transactions; dashboards show first cohort.",
             window="First full 7-day cohort after release", rollout="Ship to 10% of sessions, reconcile, then 100%. Log only, so the rollback is to switch it off.",
             guardrails="No images or document numbers in analytics events; access by role.", conditional=""),
        dict(id="tech_error_hold", phase=0, kind="Remediate", area="Execution errors", title="Hold and retry on TECHNICAL_ERROR",
             action="Treat NOT_EXECUTED / TECHNICAL_ERROR as non-final. Retry with backoff, up to three times. Then hold the case for a manual decision; do not record a rejection.",
             hypothesis="h_exec", evidence=f"{exec_inc['observed']} recent rejections with usability TECHNICAL_ERROR; liveness passed in all of them.",
             eligible="Any decision with a TECHNICAL_ERROR capability", eligible_n=exec_inc["observed"],
             outcome="No final rejections caused by execution errors. Some held cases will still fail once the checks run.", confidence="High that rejections stop; unknown approval",
             accountable="platform", participants="product, vendors, cx", dependencies="Confirm how ARQ currently handles TECHNICAL_ERROR (discovery).",
             effort="S (assumed 1–2 engineer-weeks)", acceptance="Zero final rejections with TECHNICAL_ERROR over 4 weeks; 95% of held cases resolved within 24 hours.",
             window="4 weeks, then every incident", rollout="Feature flag; per-country enablement.", guardrails="Retry cap and rate limit so retries do not amplify an outage; cost cap.", conditional=""),
        dict(id="alerting", phase=0, kind="Measure", area="Monitoring", title="Daily, then hourly, alerts per reason code",
             action="Alert on the approval rate and on each reason code per country, against its usual level. Page the team that owns it.",
             hypothesis="", evidence=f"On a replay of the extract, the proposed daily rules fire on the first day of {sum(caught.values())} of the {len(caught)} incident windows. They also fire on {false_prior} day-rule combinations in the prior period.",
             eligible="All decisions", eligible_n="", outcome="Incidents detected within a day now, within an hour once events exist.", confidence="High",
             accountable="data", participants="platform, risk, product, ops", dependencies="Daily feed now; hourly needs the Phase 0 events.",
             effort="S (assumed 1 engineer-week)", acceptance="On replay, alerts fire on the first day of every incident window. False alerts in the prior period stay under one a week.",
             window="4 weeks", rollout="Start with notifications only. Then page the on-call person.", guardrails="Review thresholds monthly to limit alert fatigue.", conditional=""),
        dict(id="compliance_reconcile", phase=0, kind="Control", area="Compliance", title="Reconcile the control findings",
             action=f"Check three groups of approvals. {comp['minors']:,} have a birth year of 2006 or later, {comp['no_screening']} have no screening result and {comp['watchlist_warning']} have a screening warning. Compare each with the policy, the raw responses, the review dispositions and the account state.",
             hypothesis="", evidence="Extract findings, not confirmed control failures.",
             eligible=f"{comp['minors'] + comp['no_screening'] + comp['watchlist_warning']:,} approved records",
             eligible_n=comp['minors'] + comp['no_screening'] + comp['watchlist_warning'],
             outcome="Each control finding is confirmed or explained, and confirmed gaps are fixed. Approvals may fall if gaps are real.", confidence="High that the answer is knowable",
             accountable="compliance", participants="data, legal, risk, ops", dependencies="Access to screening records and account state.",
             effort="S (assumed 1–2 analyst-weeks)", acceptance="Every record classified (confirmed, explained, data error) with evidence.",
             window="2 weeks", rollout="Not applicable", guardrails="Escalate any confirmed under-age or unscreened active account the same day.", conditional=""),
        dict(id="investigate_fraud", phase=0, kind="Investigate", area="Fraud signals", title="Adjudicate a sample of fraud signals",
             action="Review a random sample of the Aug 24 Argentina and Sep 14–19 Mexico flags; pull channel, device and cross-transaction data.",
             hypothesis="h_attack, h_ine", evidence="Two clusters of manipulation signals with different volume patterns.", eligible="Recent fraud-signal decisions", eligible_n=cb["Fraud signal"],
             outcome="A confirmed-fraud rate per cluster, which decides the controls.", confidence="Medium",
             accountable="risk", participants="ops, vendors, growth", dependencies="Vendor support for case detail.", effort="S (assumed 1 analyst-week)",
             acceptance="At least 50 cases per cluster adjudicated with documented rationale.", window="2 weeks", rollout="Not applicable",
             guardrails="Reviewers blind to the hypothesis where practical.", conditional=""),
        dict(id="investigate_docs", phase=0, kind="Investigate", area="Mexico documents", title="Diagnose 'no document type' in Mexico",
             action="Review 100 recent Mexican cases with no document type with the vendor; compare the accepted-document configuration over time.",
             hypothesis="h_mex_docs", evidence="No document type for a larger share of Mexican decisions each week; almost none in Argentina.",
             eligible="Recent Mexican decisions with no document type", eligible_n="", outcome="The mix of causes, which decides the fix.", confidence="Medium",
             accountable="product", participants="vendors, data, country", dependencies="Vendor access to images; data-protection approval for the review.",
             effort="S (assumed 1–2 weeks)", acceptance="Each sampled case assigned a cause with vendor agreement.", window="2 weeks", rollout="Not applicable",
             guardrails="Images reviewed in the vendor portal only.", conditional=""),
        dict(id="vendor_confirm", phase=0, kind="Investigate", area="Vendor", title="Confirm vendor incident scope",
             action="Ask the vendor for incident reports for Sep 1, 2 and 6, 2023, and the affected ARQ transactions. Check ARQ's release log for those days.",
             hypothesis="h_exec, h_liveness", evidence="A third-party copy of the status page reports liveness incidents on Sep 1 and 6.", eligible="", eligible_n="",
             outcome="Confirmed or rejected vendor attribution.", confidence="Medium", accountable="vendors", participants="platform, finance",
             dependencies="Contract terms for incident reports.", effort="S", acceptance="Written vendor confirmation or denial per date.", window="2 weeks",
             rollout="Not applicable", guardrails="", conditional="Any SLA credit depends on the contract and on confirmed scope."),
        dict(id="kpi_split", phase=0, kind="Measure", area="Measurement", title="Report the headline with its breakdown",
             action="Keep the headline approval rate on all decisions, and show fraud-signal, execution-error and warning shares beside it.",
             hypothesis="", evidence="Fraud bursts and execution errors move the headline for different reasons.", eligible="", eligible_n="",
             outcome="Faster, correct triage that shows all outcomes.", confidence="High", accountable="data", participants="risk, finance, product",
             dependencies="", effort="S", acceptance="Weekly report adopted by the funnel review.", window="2 weeks", rollout="Not applicable",
             guardrails="Never report the headline with selected outcomes removed.", conditional=""),
        dict(id="liveness_retake", phase=1, kind="Experiment", area="Selfie / liveness", title="Test one guided retake on unclear selfies",
             action="When liveness returns BAD_QUALITY or FACE_NOT_FULLY_VISIBLE, offer one retake with tips about light and position.",
             hypothesis="h_liveness", evidence=f"{cb['Selfie / liveness']:,} recent selfie/liveness declines; on incident days {live_inc['observed']} more.",
             eligible="Liveness quality failures with no fraud signal", eligible_n=cb["Selfie / liveness"], outcome="See scenarios; measured by the experiment.",
             confidence="Low until tested", accountable="product", participants="mobile, vendors, risk, compliance", dependencies="Phase 0 events; vendor support for retakes; Risk sign-off.",
             effort="M (assumed 3 engineer-weeks)", acceptance="Experiment readout against its primary outcome and guardrails.", window="See experiment design",
             rollout="50/50 experiment, then staged rollout.", guardrails="Fraud-signal rate among retake approvals; spoof labels.", conditional="Only if vendor rules permit retakes for these labels."),
        dict(id="mex_doc_guidance", phase=1, kind="Experiment", area="Mexico documents", title="Test accepted-document guidance in Mexico",
             action="Show accepted Mexican documents with pictures before capture and block clearly unsupported choices.",
             hypothesis="h_mex_docs", evidence="More 'no document type' and unsupported-document outcomes in Mexico.", eligible="People who start KYC with a Mexican document",
             eligible_n=n_mexdoc, outcome="See scenarios; measured by the experiment.", confidence="Low until the diagnosis is done",
             accountable="product", participants="mobile, vendors, country, compliance", dependencies="Phase 0 diagnosis and events; confirmed accepted-document list.",
             effort="M (assumed 3–4 engineer-weeks plus design)", acceptance="Experiment readout.", window="See experiment design",
             rollout="10% then 50/50, then staged.", guardrails="Start-to-submit rate; fraud-signal rate.", conditional="Only if the diagnosis points to document choice rather than configuration or vendor coverage."),
        dict(id="fraud_precheck", phase=1, kind="Control", area="Fraud signals", title="Velocity and device checks before the vendor call",
             action="Rate-limit by device and network and block known-bad devices before a vendor transaction is created.",
             hypothesis="h_attack", evidence="Argentina volume roughly doubled on the day of the burst.", eligible="All submissions", eligible_n="",
             outcome="Fewer vendor transactions on attack traffic; no approval gain intended.", confidence="Medium",
             accountable="risk", participants="platform, compliance, legal, vendors, growth", dependencies="Fraud adjudication results; device data collection approved.",
             effort="M (assumed 3–5 engineer-weeks)", acceptance="False-block rate on a holdout below an agreed threshold.", window="4 weeks",
             rollout="Shadow mode first (log, do not block), then block.", guardrails="Monitor blocks of genuine applicants via appeals and support contacts.",
             conditional="Depends on adjudication that confirms coordinated fraud."),
        dict(id="qual_research", phase=1, kind="Investigate", area="Capture flow", title="Watch and ask people who failed the capture",
             action="Start with support tickets and vendor case images. Then do 8–10 remote interviews and unmoderated capture tests. Add session replay and eye tracking only if questions stay open.",
             hypothesis="h_liveness, h_mex_docs", evidence=f"Capture and document issues are {n_capture_class:,} of the recent not-approved decisions; the extract says what failed, not why.",
             eligible="Recently declined applicants who consent to contact", eligible_n=n_capture_class, outcome="A ranked list of observed failure causes, as input for the retake and guidance tests.",
             confidence="Medium", accountable="product", participants="cx, mobile, data, country, legal", dependencies="Consent to contact declined applicants; vendor case access.",
             effort="S–M (assumed 1 researcher-week per rung)", acceptance="Written causes ranked by frequency, each with a ticket, clip or image as evidence.", window="2–4 weeks",
             rollout="Not applicable", guardrails="No copies of ID documents kept; consent for every session.", conditional="Interviews and tests depend on consent; the costlier rungs on budget."),
        dict(id="vendor_bakeoff", phase=1, kind="Investigate", area="Vendor", title="Decide on the vendor: bake-off on a sample",
             action="If the vendor cannot explain Sep 1, 2 and 6, or cannot support retakes, test a second vendor. Run it in shadow mode on a sample and compare the decisions.",
             hypothesis="h_exec, h_liveness", evidence="Liveness incidents on the vendor's status page on Sep 1 and 6; execution errors on Sep 1–2 with no vendor entry.",
             eligible="A sample of recent submissions", eligible_n="", outcome="A decision: stay, renegotiate, or add a second vendor (Phase 3).", confidence="Medium",
             accountable="vendors", participants="platform, finance, compliance, risk, legal", dependencies="The vendor's incident reports (Phase 0); a second vendor's sandbox; a privacy review of the data we send.",
             effort="M (assumed 2–3 engineer-weeks plus commercial time)", acceptance="Side-by-side approval, false-reject and latency figures on the same sample.", window="4 weeks",
             rollout="Shadow only; no production decisions from the second vendor.", guardrails="No applicant data sent without a contract and a privacy review.",
             conditional="Only if the vendor does not answer in Phase 0, or the answers are not sufficient."),
        dict(id="capture_quality", phase=2, kind="Experiment", area="ID capture", title="On-device capture quality checks",
             action="Use auto-capture with blur and glare checks and a retake prompt; restrict uploads if the current flow allows them.",
             hypothesis="", evidence=f"{n_capture:,} recent image-quality or copy declines.", eligible="All ID captures", eligible_n=n_capture,
             outcome="See scenarios.", confidence="Low", accountable="mobile", participants="product, vendors, data", dependencies="Knowledge of the current capture flow (discovery).",
             effort="M (assumed 4 engineer-weeks)", acceptance="Experiment readout.", window="4 weeks", rollout="Staged by app version.",
             guardrails="Time to capture; start-to-submit rate.", conditional="Camera-only capture depends on the current flow, and on whether uploads are the cause."),
        dict(id="review_queue", phase=2, kind="Experiment", area="Face match", title="Pilot manual review of face-match warnings",
             action="Send face-match WARNINGs, and later a sample of NO_MATCH, to trained reviewers.",
             hypothesis="h_face", evidence=f"{n_facewarn} recent face-match warnings and {n_nomatch} NO_MATCH declines.", eligible="Face-match warnings without fraud signals",
             eligible_n=n_facewarn, outcome="See scenarios.", confidence="Low", accountable="ops", participants="compliance, risk, vendors, finance, legal",
             dependencies="Reviewer capacity, instruction and a quality plan; cost per review.", effort="M (process plus tools)",
             acceptance="Pilot readout with quality agreement.", window="4 weeks", rollout="Staggered weekly rollout.", guardrails="Second-reviewer agreement; later fraud among approvals.",
             conditional="Requires a capacity and quality plan. Any threshold change requires risk validation."),
        dict(id="reengagement", phase=2, kind="Remediate", area="Recovery", title="Invite recoverable applicants back",
             action="Message people declined for execution errors or capture issues with a retry link and tips for their reason.",
             hypothesis="", evidence="Execution errors and capture issues are the categories most likely to succeed on retry.", eligible="Past execution-error and capture declines",
             eligible_n="", outcome="One-off recovery of some past applicants.", confidence="Low", accountable="growth", participants="cx, product, legal, data",
             dependencies="Consent and permission to send messages; Phase 0 events to measure.", effort="S", acceptance="Return and approval rates measured per category.",
             window="4 weeks after send", rollout="Small batch first.", guardrails="Exclude fraud signals and compliance findings; frequency cap.",
             conditional="Only for appropriate recoverable categories and with consent."),
        dict(id="orchestration", phase=3, kind="Platform", area="Platform", title="KYC orchestration and decision layer",
             action="A service between the app and the vendors. It owns session state, retries, versioned rules per country, the route to review, and events.",
             hypothesis="", evidence="Every incident type above needs state, retries and rules that a thin integration lacks (if that is the current setup).",
             eligible="", eligible_n="", outcome="Faster, safer changes to KYC rules; prerequisite for failover.", confidence="Medium",
             accountable="platform", participants="product, data, vendors, risk, compliance", dependencies="Phase 0–2 learnings; architecture review.",
             effort="L (multi-team, a quarter or more)", acceptance="Parity with the current flow, then rule changes without app releases.", window="Quarterly",
             rollout="Shadow traffic, then country by country.", guardrails="Approval-rate and latency parity before cut-over.", conditional="Depends on what the current architecture already provides."),
        dict(id="registry_checks", phase=3, kind="Platform", area="Registry checks", title="Government registry checks (INE, RENAPER)",
             action="Validate credentials and faces against national registries where the vendor offers it.", hypothesis="h_ine, h_face", evidence="INE flags without volume; face mismatches on older cards.",
             eligible="", eligible_n="", outcome="Fewer false fraud flags and face mismatches, if prerequisites are met.", confidence="Low",
             accountable="vendors", participants="compliance, legal, platform, finance", dependencies="Commercial terms; registry contracts (e.g. INE requires a direct contract per the vendor).",
             effort="L (commercial plus integration)", acceptance="Pilot on a sample with measured agreement.", window="Quarterly", rollout="Pilot, then rule changes.",
             guardrails="A plan for registry downtime.", conditional="Requires integration and commercial work."),
        dict(id="second_vendor", phase=3, kind="Platform", area="Vendor resilience", title="Second verification vendor for failover",
             action="Add a second vendor behind the orchestration layer for outages and leverage.", hypothesis="h_exec", evidence="Execution-error incident.",
             eligible="", eligible_n="", outcome="Resilience to vendor outages.", confidence="Low", accountable="vendors", participants="platform, finance, legal, compliance",
             dependencies="Orchestration layer; commercial negotiation; parity tests.", effort="L", acceptance="Failover drill passes with parity on approval rate.",
             window="Quarterly", rollout="Shadow comparison, then failover only.", guardrails="Consistent decisions across vendors.", conditional="Requires integration and commercial work."),
    ]
    names = {d[0]: d[1] for d in DEPARTMENTS}
    for i, a in enumerate(A, 1):
        a["order"] = i
        a["phase_label"] = PHASES[a["phase"]]
        a["track"] = TRACKS[a["kind"]]
        a["owner"] = names[a["accountable"]]
        a["participant_names"] = ", ".join(names[p.strip()] for p in a["participants"].split(","))
    cols = ["id", "order", "phase", "phase_label", "track", "kind", "area", "title", "action", "hypothesis", "evidence", "eligible", "eligible_n",
            "outcome", "confidence", "accountable", "owner", "participants", "participant_names", "dependencies", "effort", "acceptance",
            "window", "rollout", "guardrails", "conditional"]
    write("actions.csv", cols, [{c: a.get(c, "") for c in cols} for a in A])
    write("phases.csv", ["phase", "label"], [{"phase": k, "label": v} for k, v in PHASES.items()])
    write("tracks.csv", ["id", "order", "name", "note"], [{"id": t, "order": i, "name": n, "note": d} for i, (t, n, d) in enumerate(TRACK_INFO, 1)])
    # the budget ladder for the qualitative research action: assumptions, not quotes
    research = [
        ("none", 1, "No budget", "Support tickets, app analytics, vendor case images", "Which failures people complain about; what the vendor saw on the image", "Week 1", "Existing data; no consent needed beyond current terms"),
        ("low", 2, "Low", "8–10 remote interviews; unmoderated capture tests on the real flow", "Why people choose the wrong document or fail the selfie", "Weeks 1–3", "Consent; a researcher-week; small incentives"),
        ("medium", 3, "Medium", "Session replay on the capture screens; a one-week diary study in Mexico", "Where people hesitate, retry or quit; what happens at home, not in a lab", "Weeks 2–4", "A replay tool with PII masking; privacy review"),
        ("high", 4, "High", "Lab usability sessions with eye tracking on the capture screens", "What people look at before a bad capture; whether the guidance is seen", "Weeks 3–6", "A lab or vendor; only if the cheaper rungs leave questions open"),
    ]
    write("research_options.csv", ["id", "order", "budget", "method", "answers", "when", "needs"],
          [dict(zip(["id", "order", "budget", "method", "answers", "when", "needs"], r)) for r in research])
    raci = []
    for a in A:
        raci.append({"id": f"{a['id']}-{a['accountable']}", "action_id": a["id"], "dept_id": a["accountable"], "role": "A"})
        for p in a["participants"].split(","):
            p = p.strip()
            role = "R" if p in RESPONSIBLE.get(a["id"], ()) else ("I" if p in INFORMED.get(a["id"], ()) else "C")
            raci.append({"id": f"{a['id']}-{p}", "action_id": a["id"], "dept_id": p, "role": role})
    write("raci.csv", ["id", "action_id", "dept_id", "role"], raci)
    for a in A:
        assert sum(1 for r in raci if r["action_id"] == a["id"] and r["role"] == "A") == 1


RESPONSIBLE = {"instrument_min": ("platform", "mobile"), "alerting": ("platform",), "compliance_reconcile": ("data",), "investigate_fraud": ("ops",),
               "investigate_docs": ("vendors", "data"), "liveness_retake": ("mobile",), "mex_doc_guidance": ("mobile",), "fraud_precheck": ("platform",),
               "review_queue": (), "reengagement": ("cx",), "orchestration": ("product",), "registry_checks": ("platform",), "second_vendor": ("platform",),
               "qual_research": ("cx",), "vendor_bakeoff": ("platform",)}
INFORMED = {"tech_error_hold": ("cx",), "vendor_confirm": ("finance",), "kpi_split": ("finance",), "fraud_precheck": ("growth",), "capture_quality": ("data",),
            "reengagement": ("data",), "mex_doc_guidance": ("cx",), "liveness_retake": (), "qual_research": ("legal",), "vendor_bakeoff": ("finance",)}

# Role-based example functions. Not ARQ's org chart: no people, headcount or reporting lines.
DEPARTMENTS = [
    ("leadership", "Leadership team", "Decide priorities and resources; review the KYC metrics monthly."),
    ("product", "Product · Onboarding", "Owns the approval-rate metric and the onboarding flow."),
    ("platform", "Engineering · Onboarding platform", "Owns integrations, retries and the response to execution errors."),
    ("mobile", "Engineering · Mobile", "Owns capture in the app."),
    ("data", "Data & Analytics", "Owns metric definitions, events, data quality and alerts."),
    ("ops", "Operations · KYC review", "Owns manual review, if one exists or is introduced."),
    ("cx", "Customer Support", "Owns what declined applicants are told."),
    ("vendors", "Vendor management", "Owns the verification vendor relationship and contract."),
    ("compliance", "Compliance", "Owns KYC policy and the control findings."),
    ("risk", "Risk & Fraud", "Owns fraud signals and controls."),
    ("finance", "Finance", "Owns unit economics and vendor cost."),
    ("growth", "Growth & Marketing", "Owns acquisition channels and re-engagement."),
    ("legal", "Legal & Privacy", "Owns data protection and consent."),
    ("country", "Country leads", "Give local knowledge of documents and regulations."),
]


def write_org():
    write("departments.csv", ["id", "order", "name", "focus"],
          [{"id": d, "order": i, "name": n, "focus": f} for i, (d, n, f) in enumerate(DEPARTMENTS, 1)])
    names = {d[0]: d[1] for d in DEPARTMENTS}
    rituals = [
        ("alerts", "Daily now; hourly once events exist", "Health alerts", "platform", ["platform", "risk", "data"], "Reason-code alerts", "Acknowledge and triage; follow the escalation path."),
        ("funnel_review", "Weekly", "KYC funnel review", "product", ["product", "data", "mobile", "ops", "risk", "cx", "country"], "Summary, Drivers, Plan", "Action status, experiment readouts, next priorities."),
        ("fraud_review", "Every two weeks", "Fraud review", "risk", ["risk", "compliance", "data", "growth"], "Incidents", "Controls to tighten or relax; cases to report."),
        ("vendor_review", "Monthly", "Vendor review", "vendors", ["vendors", "platform", "product", "risk", "finance"], "Vendor research, Incidents", "Incident reports, contract questions, features to evaluate."),
        ("metric_council", "Monthly", "Metric definitions review", "data", ["data", "product", "finance", "compliance"], "Measurement", "Approve definition changes and versions; check data freshness and quality."),
        ("leadership", "Monthly", "Leadership KPI review", "leadership", ["leadership", "product", "finance", "compliance"], "Summary, Plan", "Resources and priorities for the roadmap."),
    ]
    write("rituals.csv", ["id", "order", "cadence", "meeting", "chair", "attendees", "attendee_ids", "tabs", "decides"],
          [{"id": r, "order": i, "cadence": c, "meeting": m, "chair": names[ch], "attendees": ", ".join(names[a] for a in att),
            "attendee_ids": ";".join(att), "tabs": tb, "decides": dc} for i, (r, c, m, ch, att, tb, dc) in enumerate(rituals, 1)])
    esc = [
        (1, "Within 15 minutes of an alert", ["platform"], "Acknowledge, check the vendor status page, and decide whether the fault is the vendor's or ours."),
        (2, "Within 1 hour", ["vendors", "product", "cx"], "Open a vendor ticket; apply the hold-and-retry rule to affected codes; prepare a support message."),
        (3, "Within 4 hours, if unresolved", ["leadership", "growth"], "Decide on further measures. Pause paid acquisition only if the incident is severe and affects a material share of that traffic."),
        (4, "Same day, if controls are affected", ["compliance", "legal"], "Assess any screening, age or data-protection impact and what must be reported."),
        (5, "Within 5 business days", ["data", "finance"], "Blameless review with impact figures; check contract terms before any SLA claim."),
    ]
    write("escalation.csv", ["step", "within", "who", "who_ids", "does"],
          [{"step": s, "within": w, "who": ", ".join(names[i] for i in ids), "who_ids": ";".join(ids), "does": d} for s, w, ids, d in esc])
    access = [
        ("Leadership and investors", "Summary, Plan, aggregate metrics", "No record-level data; fraud-control detail summarised."),
        ("Department leads", "All tabs for their metrics and actions", "Aggregates only."),
        ("Risk and Compliance", "All tabs, with the control findings", "Record-level drill-down only in source systems, by role."),
        ("Analysts", "Definitions, lineage, validation", "Record-level data in the warehouse under access control."),
        ("Public", "Nothing from this dashboard", "Separate explainer, reviewed by Legal and Communications."),
    ]
    write("access.csv", ["audience", "sees", "restriction"], [dict(zip(["audience", "sees", "restriction"], a)) for a in access])
    adoption = [
        ("Users", "Product, Data, Risk, Compliance, Ops and Vendor leads who own KYC metrics or actions."),
        ("Core workflows", "Weekly funnel review; investigation of an alert; approval of a definition change; a check of an action's status."),
        ("Onboarding", "30-minute walkthrough per team; each owner confirms their metric definitions and actions in the first week."),
        ("Pilot", "Four weeks with the KYC funnel review only. Then a feedback round, before we add more metrics."),
        ("Feedback", "A comment thread per metric and a monthly five-question survey of owners."),
        ("Success measures", "Share of KYC actions with an owner and a current status. Share of metrics with an approved definition. Time from alert to acknowledgement. Decisions in the review that cite the platform. Page views are not a success measure."),
    ]
    write("adoption.csv", ["topic", "plan"], [dict(zip(["topic", "plan"], a)) for a in adoption])


MANIFEST = {
    "kpis": "Headline figures and reconciliation checkpoints.",
    "metrics": "Metric registry: definitions, availability, owners, versions.",
    "metric_versions": "Version history of the headline metric definition.",
    "validation": "Data validation checks on the two extracts.",
    "events": "Events needed to measure the requested funnel.",
    "daily": "Decisions and approvals per day and document country.",
    "weekly_drivers": "Not-approved decisions per week by primary reason.",
    "reasons": "Every primary reason, prior vs recent period.",
    "bridge": "Change in approval rate by primary reason.",
    "declines": "Not-approved decisions by group and class, with both denominators.",
    "incidents": "Four incident windows: observed, expected and above-baseline counts.",
    "incident_sensitivity": "Incident attribution under alternative windows, signatures and baselines.",
    "mex_no_doctype": "Mexican-document decisions with no document type, by outcome.",
    "docs": "Decisions by document type and country.",
    "docs_weekly": "Weekly document-type mix by country.",
    "process_steps": "Capability-level counts per check.",
    "profile": "Decisions by extracted birth-year band (biased by missingness).",
    "compliance": "Control findings in the extract, with validation steps.",
    "hypotheses": "Main hypotheses with evidence, alternatives and next steps.",
    "open_questions": "Questions to confirm with ARQ before any action, with what each answer changes.",
    "assumptions": "The assumptions behind the analysis, and what changes if each one is wrong.",
    "quick_review": "The whole story on one page, with charts.",
    "tracks": "The four roadmap tracks (Fix, Test, Learn, Build) and what each means.",
    "research_options": "Budget ladder for the qualitative research action (assumptions).",
    "scenarios": "Recovery scenarios per population: observed counts and assumed factors.",
    "scenario_totals": "Scenario totals and possible control-gap reversals.",
    "experiments": "Experiment and validation designs.",
    "value_inputs": "Financial inputs the value model needs, with market-based low / mid / high presets (not ARQ figures).",
    "value_sources": "Published sources behind the value-model presets, with fetch status.",
    "value_results": "Value-model results for each preset and scenario (same formulas as the dashboard).",
    "risks": "Risk register.",
    "alerts": "Proposed alert rules replayed on the extract.",
    "actions": "Roadmap actions with ownership, acceptance and guardrails.",
    "phases": "Roadmap phases.",
    "raci": "Responsibility assignments per action.",
    "departments": "Role-based example functions (not ARQ's organisation).",
    "rituals": "Operating rhythm.",
    "escalation": "Alert escalation path.",
    "access": "Access by audience.",
    "adoption": "Internal adoption plan.",
    "vendor_evidence": "Vendor status-page evidence for 2023 incident dates.",
    "vendor_capabilities": "Current vendor capabilities, prerequisites and verification.",
    "vendor_changes": "Vendor changes since 2023.",
}


def write_manifest():
    import json
    files = sorted(f[:-4] for f in os.listdir(OUT) if f.endswith(".csv"))
    missing = [f for f in files if f not in MANIFEST]
    assert not missing, missing
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump({k: MANIFEST[k] for k in files}, f, indent=1)


def write_vendor():
    """Filled from desk research; see vendor_research() for sources and verification status."""
    from vendor_research import EVIDENCE, CAPABILITIES, CHANGES
    write("vendor_evidence.csv", list(EVIDENCE[0].keys()), EVIDENCE)
    write("vendor_capabilities.csv", list(CAPABILITIES[0].keys()), CAPABILITIES)
    write("vendor_changes.csv", list(CHANGES[0].keys()), CHANGES)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    for stale in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if stale.endswith(".csv") or stale == "manifest.json":
            os.remove(os.path.join(OUT, stale))
    main()
