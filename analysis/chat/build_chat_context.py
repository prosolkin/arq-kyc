"""Build the case material for the chat proxy from the same outputs as the dashboard.

Writes analysis/chat/worker/case-material.md: one section per dashboard tab, so the chat
can name the tab with more detail. Run from the project root after build_notes.py:
    python3 -I analysis/chat/build_chat_context.py
"""

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "analysis", "out")
NOTE = os.path.join(ROOT, "analysis", "export", "methodology-and-validation.md")
DEST = os.path.join(ROOT, "analysis", "chat", "worker", "case-material.md")
MAX_BYTES = 120_000  # about 30K tokens; the whole file goes in the cached system prompt

# what each dashboard page holds, so the chat names the right page (keep in step with analysis/dashboard/index.html)
GUIDE = [
    "Quick review: the short story with its charts.",
    "Why it fell: the reasons for not-approved decisions by class, the Mexico \"no document type\" breakdown, face match, the checks block by block, and the failure mix by week.",
    "What to do: the plan in phases and in four tracks, and every action with its owner, evidence and acceptance criteria. The research and vendor bake-off actions are here.",
    "What we gain: the recovery scenarios and the value model, with its inputs, results, presets and sources.",
    "Full summary (under Details): the answer, what to confirm with the team, the daily approval rate, what moved the rate, and what it means for each audience.",
    "Measurement (under Details): what can and cannot be measured, the metric definitions, the data validation, and the events needed to measure the funnel.",
    "Incidents (under Details): the four date windows with unusual failures, their counts, the sensitivity of the attribution, and the vendor's status-page evidence.",
    "Hypotheses & tests (under Details): the main hypotheses, how to test them, and the experiment designs.",
    "Operating model (under Details): the KPI registry, ownership, who does what, the operating rhythm, alerts, access and adoption.",
    "Target design (under Details): the requirements, scale, components, session states, and build or buy.",
    "Vendor research (under Details): the vendor's capabilities today against the 2023 problems, and the changes since 2023.",
    "Reference (under Details): the assumptions, the open questions for ARQ, the control findings, the risk register, common questions, a glossary and the method in short.",
]


def load(name):
    with open(os.path.join(OUT, name + ".csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def table(rows, cols, labels=None):
    labels = labels or cols
    out = ["| " + " | ".join(labels) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def main():
    s = []
    s.append("# Case material: KYC approval-rate diagnosis (ARQ case study)\n")
    s.append("This is the full material behind the dashboard, the deck and the report. Sections follow the dashboard tabs. "
             "Numbers are exact as built from the two 2023 extracts (Jul 25 – Sep 22, 2023). Vendor research is dated Oct 13, 2026.\n")
    s.append("Where things are on the dashboard:\n")
    s.append("\n".join("- " + x for x in GUIDE) + "\n")

    # Quick review: the short story, in reading order
    s.append("## Tab: Quick review\n")
    for r in sorted(load("quick_review"), key=lambda r: int(r["order"])):
        head = f"\n### {r['heading']}\n" if r["heading"] else ""
        if r["kind"] == "chart":
            if head:
                s.append(head)
            continue
        bullet = "- " if r["kind"] in ("li", "t_fix", "t_test", "t_learn", "t_build") else ""
        track = {"t_fix": "[Fix and measure] ", "t_test": "[Test the fixes] ", "t_learn": "[Learn why] ", "t_build": "[Build later] "}.get(r["kind"], "")
        s.append(f"{head}{bullet}{track}{r['text']}")
    s.append("")

    # Why it fell
    s.append("## Tab: Why it fell\n")
    k = {r["metric"]: r for r in load("kpis")}
    s.append("Key figures:\n")
    s.append(table([{"metric": m, "value": r["value"], "label": r["label"]} for m, r in k.items()], ["label", "value"], ["Figure", "Value"]))
    s.append("\nChange in the approval rate by primary reason (points; they add up to the total change):\n")
    s.append(table(load("bridge"), ["driver", "class", "effect_pp", "incident_pp", "rest_pp"], ["Reason", "Class", "Effect (pp)", "In incident windows (pp)", "Rest (pp)"]))
    s.append("\nNot-approved decisions by class:\n")
    s.append(table([r for r in load("declines") if r["level"] == "class"], ["name", "n_a", "n_b", "of_unsuccessful_a", "of_unsuccessful_b"],
                   ["Class", "Prior count", "Recent count", "Share of not approved, prior", "Share of not approved, recent"]))
    s.append("")

    # Incidents
    s.append("## Tab: Incidents (under Details)\n")
    s.append(table(load("incidents"), ["title", "when", "type", "observed", "expected", "excess", "contribution_pp"],
                   ["Window", "When", "Type", "Observed", "Expected", "Above baseline", "Approval points"]))
    s.append("\nVendor status-page evidence:\n")
    s.append(table(load("vendor_evidence"), ["date", "window_utc", "description", "verification", "arq_impact"], ["Date", "UTC", "Entry", "Read", "ARQ impact"]))
    s.append("")

    # Hypotheses
    s.append("## Tab: Hypotheses & tests (under Details)\n")
    s.append(table(load("hypotheses"), ["id", "hypothesis", "evidence", "alternatives", "missing", "next", "decision"],
                   ["ID", "Hypothesis", "Evidence", "Alternatives", "Still needed", "Next step", "Decision it enables"]))
    s.append("\nExperiment designs:\n")
    s.append(table(load("experiments"), ["id", "kind", "hypothesis", "population", "primary", "window", "sample", "guardrails"],
                   ["ID", "Kind", "Hypothesis", "Population", "Primary outcome", "Window", "Sample", "Guardrails"]))
    s.append("")

    # What to do
    s.append("## Tab: What to do\n")
    s.append(table(load("phases"), ["phase", "label"], ["Phase", "Label"]))
    s.append("")
    s.append(table(load("tracks"), ["name", "note"], ["Track", "Meaning"]))
    s.append("")
    s.append(table(sorted(load("actions"), key=lambda r: int(r["order"])),
                   ["phase", "track", "title", "action", "owner", "effort", "acceptance", "conditional"],
                   ["Phase", "Track", "Action", "What", "Accountable (role)", "Effort (assumed)", "Done when", "Condition"]))
    s.append("\nQualitative research budget ladder (assumptions). This is the detail behind the action "
             "\"Watch and ask people who failed the capture\". The dashboard shows it in short form in that action:\n")
    s.append(table(load("research_options"), ["budget", "method", "answers", "when"], ["Budget", "Method", "What it answers", "When"]))
    s.append("")

    # What we gain
    s.append("## Tab: What we gain\n")
    s.append(table(load("scenario_totals"), ["scenario", "steady_30d", "steady_pp", "approval_with_steady", "per_incident", "control_gap_all"],
                   ["Scenario", "Approvals per 30 days", "Points", "Recent rate with them", "Per comparable incident", "Possible reversals"]))
    s.append("\nValue model inputs (market benchmarks, not ARQ figures):\n")
    s.append(table(load("value_inputs"), ["label", "unit", "low", "mid", "high", "short"], ["Input", "Unit", "Low", "Mid", "High", "Basis"]))
    s.append("\nValue model results, central scenario:\n")
    s.append(table([r for r in load("value_results") if r["scenario"] == "Central"], ["preset", "label", "value"], ["Preset", "Result", "Value"]))
    s.append("\nSources of the value model inputs (shown under Sources on this tab):\n")
    s.append(table(load("value_sources"), ["id", "publisher", "title", "figure", "period", "status"], ["ID", "Publisher", "Title", "Figure", "Period", "Status"]))
    s.append("")

    # Reference
    s.append("## Tab: Reference (under Details)\n")
    s.append("Assumptions, and what changes if each one is wrong (also a slide in the deck and section 10 of the note):\n")
    s.append(table(sorted(load("assumptions"), key=lambda r: int(r["order"])), ["area", "assumption", "if_wrong"], ["Area", "We assume", "If it is wrong"]))
    s.append("\nOpen questions for ARQ:\n")
    s.append(table(sorted(load("open_questions"), key=lambda r: int(r["order"])), ["question", "why", "changes", "who"],
                   ["Question", "Why it matters", "What the answer changes", "Who would know"]))
    s.append("\nControl findings in the extract (to reconcile, not confirmed failures):\n")
    s.append(table(load("compliance"), ["finding", "n", "detail"], ["Finding", "Records", "Detail"]))
    s.append("")

    # Method: the full note
    s.append("## Method and validation (the methodology note in the report)\n")
    with open(NOTE, encoding="utf-8") as f:
        note = f.read()
    s.append(note.replace("\n# ", "\n### ").replace("\n## ", "\n### "))

    text = "\n".join(s)
    size = len(text.encode("utf-8"))
    assert size < MAX_BYTES, f"case material too large: {size:,} bytes"
    with open(DEST, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"chat case material: {size:,} bytes -> {os.path.relpath(DEST, ROOT)}")


if __name__ == "__main__":
    main()
