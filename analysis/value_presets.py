"""Market-based presets for the value model.

Every preset comes from a published figure in SOURCES, combined with the stated
assumptions in ASSUME. None is an ARQ figure; Finance should replace each with
ARQ's own number. The sources were fetched on the research date in build_datasets.py.
"""

FX = 18.3528  # MXN per USD, Banco de México FIX for 13 Oct 2026 (S14)

SOURCES = [
    dict(id="S1", publisher="Veriff", title="Pricing page, self-serve plans",
         figure="Essential $0.80, Plus $1.39, Premium $1.89 per verification; PEP and sanctions add-on +$0.64",
         period="List prices, 13 Oct 2026", url="https://www.veriff.com/pricing", status="Fetched"),
    dict(id="S2", publisher="Sumsub", title="Pricing and plans",
         figure="Basic $1.35 (ID, liveness, face match); Compliance $1.85 (adds AML screening) per verification; only successful verifications are charged",
         period="List prices, 13 Oct 2026", url="https://sumsub.com/pricing/", status="Fetched"),
    dict(id="S3", publisher="Vendr", title="Jumio buyer guide",
         figure="Estimated $1.50–$3.00 per verification at 100,000–500,000 a year; median contract $55,850 a year",
         period="Updated Feb 2026", url="https://www.vendr.com/buyer-guides/jumio", status="Fetched (third-party estimate)"),
    dict(id="S4", publisher="Nu Holdings", title="Nu México press release",
         figure="Nu México ARPAC US$12.5 a month; cost to serve US$1 a month",
         period="Q3 2025, published 11 Feb 2026",
         url="https://nu.com/es/sala-de-prensa/compania/nu-mexico-espera-que-su-inversion-total-alcanzara-los-us-4-2-mil-millones-para-2030-a-medida-que-se-acerca-su-inicio-de-operaciones-como-banco",
         status="Fetched"),
    dict(id="S5", publisher="Nu Holdings", title="Form 6-K, Q1 2026 results",
         figure="Gross profit US$1,877.7m on revenue US$5,315.5m (managerial P&L), a 35.3% margin (derived)",
         period="Q1 2026", url="https://www.sec.gov/Archives/edgar/data/0001691493/000129281426003055/nu20260514_6k.htm", status="Fetched"),
    dict(id="S6", publisher="Nu Holdings", title="Form 20-F, FY2025",
         figure="Monthly activity rate 83%; 71% of new Brazilian customers in 2025 sourced organically; more than 50% of Mexican customers acquired through word-of-mouth referrals",
         period="31 Dec 2025", url="https://www.sec.gov/Archives/edgar/data/1691493/000129281426002166/nuform20f_2025.htm", status="Fetched"),
    dict(id="S7", publisher="Liftoff, via MarTech Series", title="Mobile Finance Apps report",
         figure="Fintech cost per registration $17.96 and activation rate 56.3%; LATAM cost per install $1.60, registration rate 18.3%, activation rate 38.2%",
         period="Data Jun 2021 – Jun 2022",
         url="https://martechseries.com/mobile/new-liftoff-data-reveals-customers-flock-to-fintech-as-economy-tightens-offers-finance-app-marketers-guidance-on-user-acquisition/",
         status="Fetched (secondary, dated)"),
    dict(id="S8", publisher="Bloomberg Línea", title="DolarApp raises US$70m and becomes ARQ",
         figure="More than 2 million users; more than US$10bn annualised transaction volume",
         period="3 Mar 2026",
         url="https://www.bloomberglinea.com/negocios/fintech-dolarapp-levanta-us70-millones-y-cambia-de-identidad-para-expansion-en-latinoamerica/",
         status="Fetched (press)"),
    dict(id="S9", publisher="Passageiro de Primeira", title="ARQ keeps a 0.5% fee on any conversion",
         figure="0.5% of the converted amount, no minimum", period="28 Jul 2026",
         url="https://passageirodeprimeira.com/sem-valor-minimo-arq-mantem-taxa-de-05-em-qualquer-conversao/", status="Fetched (consumer site)"),
    dict(id="S10", publisher="TalentUp", title="KYC analyst salary, Mexico City",
         figure="Median gross MXN 475,300 a year", period="Not stated (2026 page)",
         url="https://talentup.io/salary/KYC%20Analyst/mexico%20city", status="Fetched"),
    dict(id="S11", publisher="Paylab", title="Financial analyst salary, banking, Mexico",
         figure="Monthly gross: the lowest 10% earn under MXN 11,236 and the highest 10% over MXN 38,290; fewer than 20 verified respondents",
         period="Not stated", url="https://www.paylab.com/mx/salaryinfo/banking/financial-analyst?lang=en", status="Fetched"),
    dict(id="S12", publisher="Levels.fyi", title="Senior software engineer, Mexico",
         figure="Median total compensation MX$1,146,490 a year (224 submissions)", period="Updated 13 Oct 2026",
         url="https://www.levels.fyi/t/software-engineer/levels/senior/locations/mexico", status="Fetched (self-reported)"),
    dict(id="S13", publisher="Revelo", title="Hiring software developers in Mexico",
         figure="Senior $66,000–$90,000 a year; fully loaded cost 1.3–1.4× salary (IMSS, Infonavit, aguinaldo, PTU), up to $126,000",
         period="3 Jul 2026", url="https://www.revelo.com/blog/hire-software-developers-in-mexico", status="Fetched (recruiter)"),
    dict(id="S14", publisher="Banco de México", title="FIX exchange rate",
         figure=f"MXN {FX} per USD", period="13 Oct 2026",
         url="https://www.banxico.org.mx/tipcamb/tipCamMIAction.do?idioma=sp", status="Fetched"),
]

# Stated assumptions: judgement, not market data. Each is named in the basis text that uses it.
ASSUME = dict(
    first_year_ramp=0.40,        # first-year revenue of a new customer relative to the average Nu México customer
    reviewer_hours=140,          # productive hours per reviewer per month
    handle_min=(8, 15, 25),      # minutes per manual review
    qa_uplift=(1.1, 1.1, 1.2),   # quality sampling and second review
    loaded=(1.3, 1.35, 1.4),     # employer on-costs, within S13's 1.3–1.4×
    registrant_to_kyc=0.6,       # share of registrants who reach KYC (high CAC only)
    billable=(1.0, 1.2, 1.5),    # billable vendor transactions per decision (retries)
    paid_mid=0.40,
    eng_weeks=(12, 13, 19.5),    # roadmap effort for the four 30-day actions, plus 2 weeks review tooling; high adds 50% overrun
    team_overhead=(1.3, 1.5, 1.8),  # product, design, QA and vendor work on top of engineering
)

PRESETS = ("Low", "Mid", "High", "Cautious")
# Cautious takes the end of each range that weakens the case: low value and activation,
# high costs to build and run, and the smaller estimate of past waste.
CAUTIOUS = dict(value_per_activated="low", activation_rate="low", paid_share="low", cac_paid="low",
                billable_per_decision="low", cost_per_transaction="low", review_cost="high",
                build_cost="high", run_cost_month="high")


def money(v):
    return f"${v:,.2f}" if v < 100 and v != int(v) else f"${v:,.0f}"


def build(ctx):
    """Return {input_id: dict(low, mid, high, kind, sources, short, basis)}.

    ctx: review_n and retake_attempts (Central scenario, per 30 days) and annual_decisions.
    """
    A = ASSUME
    P = {}

    rev_arq = 10e9 / 2e6 * 0.005
    margin = 1877.7 / 5315.5
    arpac_year = 12.5 * 12
    v = (rev_arq - 12 * 1.0, arpac_year * A["first_year_ramp"] * margin, arpac_year * margin)
    P["value_per_activated"] = dict(
        vals=tuple(round(x) for x in v), kind="Derived", sources="S4 S5 S8 S9",
        short="ARQ press figures; Nu México revenue and margin",
        basis=(f"Low: ARQ's reported US$10bn volume ÷ 2m users × 0.5% fee = {money(rev_arq)} revenue a year, less $12 cost to serve (Nu México, $1 a month). "
               f"Mid: Nu México ARPAC $12.50 × 12 × {A['first_year_ramp']:.0%} first-year ramp (assumption) × {margin:.1%} gross margin. "
               "High: the same without the ramp, an average Nu México customer. Not all reported volume carries the fee, and users are not all active."))

    P["activation_rate"] = dict(
        vals=(0.382, 0.563, 0.83), kind="Proxy", sources="S6 S7",
        short="Liftoff LATAM and fintech activation; Nu activity rate",
        basis=("Low: Liftoff LATAM activation rate 38.2%. Mid: Liftoff fintech activation rate 56.3% (2021–22 data; the source doesn't define activation). "
               "High: Nu's monthly activity rate of 83%, a ceiling set by a mature primary bank. None measures approved-to-active directly."))

    P["paid_share"] = dict(
        vals=(0.29, A["paid_mid"], 0.50), kind="Proxy + assumption", sources="S6",
        short="Nu organic and word-of-mouth shares",
        basis=("Low: 29% of Nu's new Brazilian customers in 2025 were not sourced organically. High: Nu acquired more than 50% of Mexican customers through referrals, "
               f"so other channels are under 50%. Mid: {A['paid_mid']:.0%} (assumption). Not every non-organic channel is paid."))

    cpr_latam = 1.60 / 0.183
    P["cac_paid"] = dict(
        vals=(round(cpr_latam, 2), 17.96, round(17.96 / A["registrant_to_kyc"], 2)), kind="Derived", sources="S7",
        short="Liftoff cost per install and per registration",
        basis=(f"Low: Liftoff LATAM cost per install $1.60 ÷ 18.3% registration rate = {money(cpr_latam)} per registration. "
               f"Mid: Liftoff fintech cost per registration $17.96. High: $17.96 ÷ {A['registrant_to_kyc']:.0%} of registrants reaching KYC (assumption). 2021–22 data."))

    P["billable_per_decision"] = dict(
        vals=A["billable"], kind="Assumption", sources="S2",
        short="Assumption; replace with invoiced transactions ÷ decisions",
        basis=("Low: one billable transaction per decision. Mid and high: 1.2 and 1.5 with retries (assumption). "
               "Some vendors (Sumsub) charge only for successful verifications, which would make not-approved decisions free."))

    P["cost_per_transaction"] = dict(
        vals=(round(0.80 + 0.64, 2), 1.85, 3.00), kind="List price / estimate", sources="S1 S2 S3",
        short="Veriff and Sumsub list prices; Vendr estimate for Jumio",
        basis=(f"Low: Veriff Essential $0.80 + PEP and sanctions $0.64. Mid: Sumsub Compliance $1.85, which includes AML screening. "
               f"High: top of Vendr's $1.50–$3.00 estimate for Jumio at 100,000–500,000 verifications a year; the extract annualises to about {ctx['annual_decisions']:,.0f} decisions. "
               "Self-serve list prices; negotiated enterprise rates are usually lower."))

    kyc_month = 475300 / 12
    def review(mxn, i):
        hourly = mxn * A["loaded"][i] / FX / A["reviewer_hours"]
        return hourly * A["handle_min"][i] / 60 * A["qa_uplift"][i]
    rv = (review(11236, 0), review(kyc_month, 1), review(kyc_month, 2))
    P["review_cost"] = dict(
        vals=tuple(round(x, 2) for x in rv), kind="Derived", sources="S10 S11 S13 S14",
        short="Mexico analyst salaries × handling time",
        basis=(f"Monthly gross salary × loaded factor ÷ MXN {FX} ÷ {A['reviewer_hours']} productive hours × minutes per case × quality uplift. "
               f"Low: MXN 11,236 (Paylab, lowest 10% of financial analysts) × {A['loaded'][0]}, {A['handle_min'][0]} min, ×{A['qa_uplift'][0]}. "
               f"Mid: MXN {kyc_month:,.0f} (TalentUp KYC analyst median) × {A['loaded'][1]}, {A['handle_min'][1]} min, ×{A['qa_uplift'][1]}. "
               f"High: the same salary × {A['loaded'][2]}, {A['handle_min'][2]} min, ×{A['qa_uplift'][2]}. Hours, minutes and uplift are assumptions."))

    eng_year = 1146490 / FX
    weekly = (eng_year * A["loaded"][0] / 52, eng_year * A["loaded"][1] / 52, 126000 / 52)
    bc = tuple(round(A["eng_weeks"][i] * weekly[i] * A["team_overhead"][i], -2) for i in range(3))
    P["build_cost"] = dict(
        vals=bc, kind="Derived", sources="S12 S13 S14",
        short="Roadmap effort × Mexico engineering cost",
        basis=(f"Engineer-weeks × loaded weekly cost × team overhead. Weeks: {A['eng_weeks'][0]:g} / {A['eng_weeks'][1]:g} / {A['eng_weeks'][2]:g}, from the roadmap's effort for the four 30-day actions "
               "plus 2 weeks of review tooling; high adds a 50% overrun. "
               f"Weekly cost: Levels.fyi median MX$1,146,490 ÷ {FX} × {A['loaded'][0]} or × {A['loaded'][1]} ÷ 52 ({money(weekly[0])}, {money(weekly[1])}); high uses Revelo's top fully loaded $126,000 ({money(weekly[2])}). "
               f"Overhead for product, design, QA and vendor work: ×{A['team_overhead'][0]} / ×{A['team_overhead'][1]} / ×{A['team_overhead'][2]} (assumption)."))

    vals = {k: P[k]["vals"] for k in P}
    rc = tuple(round(ctx["review_n"] * vals["review_cost"][i] + ctx["retake_attempts"] * vals["billable_per_decision"][i] * vals["cost_per_transaction"][i], -1) for i in range(3))
    P["run_cost_month"] = dict(
        vals=rc, kind="Derived", sources="S1 S2 S3 S10 S11",
        short="Review cases and retake vendor calls, central scenario",
        basis=(f"Central scenario, per 30 days: {ctx['review_n']:,} review-pilot cases × cost per review, plus about {ctx['retake_attempts']:,.0f} guided selfie retakes × billable transactions × cost per transaction, "
               "using the same preset's values. Excludes support contacts and monitoring tools."))
    return P
