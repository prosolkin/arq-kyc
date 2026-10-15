// Build the KYC submission deck from the authoritative aggregates in analysis/out.
// One slide specification feeds two renderers: PowerPoint (pptxgenjs) and HTML
// (printed to PDF by headless Chrome for the companion PDF and visual QA).
//
// Run from the project root:  node analysis/tools/build_deck.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { csvParse } from 'd3';
import pptxgen from 'pptxgenjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const DATA = path.join(ROOT, 'analysis', 'out');
const OUT = path.join(ROOT, 'analysis', 'export');
const SCRATCH = process.env.DECK_SCRATCH || path.join(ROOT, 'analysis', 'tools', '.deck-build');

const load = (n) => csvParse(fs.readFileSync(path.join(DATA, n + '.csv'), 'utf8'));
const D_FILES = fs.readdirSync(DATA).filter((f) => f.endsWith('.csv')).length; // the aggregated tables, as published
const D = Object.fromEntries(['kpis', 'bridge', 'incidents', 'incident_sensitivity', 'daily', 'declines', 'metrics', 'validation', 'events', 'hypotheses',
  'actions', 'phases', 'tracks', 'scenarios', 'scenario_totals', 'experiments', 'value_inputs', 'value_sources', 'value_results', 'open_questions', 'compliance', 'mex_no_doctype', 'docs', 'vendor_evidence',
  'vendor_capabilities', 'departments', 'adoption', 'alerts'].map((n) => [n, load(n)]));
const K = (m) => { const r = D.kpis.find((x) => x.metric === m); if (!r) throw new Error('kpi ' + m); return Number(r.value); };
const row = (t, k, v) => { const r = D[t].find((x) => x[k] === v); if (!r) throw new Error(`${t} ${k}=${v}`); return r; };
const MINUS = '−';
const sgn = (v) => (v > 0 ? '+' : v < 0 ? MINUS : '');
const int = (v) => Math.round(Math.abs(v)).toLocaleString('en-US');
const sint = (v) => sgn(v) + int(v);
const pct = (v, d = 1) => (100 * v).toFixed(d) + '%';
const pp = (v, d = 1) => sgn(v) + Math.abs(v).toFixed(d) + ' pp';
const usd = (v) => (v < 0 ? MINUS : '') + '$' + Math.round(Math.abs(v)).toLocaleString('en-US');
const usd2 = (v) => '$' + (Number.isInteger(+v) ? String(+v) : Number(v).toFixed(2));
const inputFmt = (r, v) => (r.unit === 'share' ? pct(+v) : r.unit === 'USD' ? (+v < 100 ? usd2(v) : usd(+v)) : String(+v));

// ---------------- design ----------------
// The dashboard's own theme tokens (analysis/export_html.py): light for content slides, dark for the cover and divider.
const C = { ink: '1C2126', muted: '59636D', faint: '8B949C', line: 'DFE3E7', panel: 'FFFFFF', bg: 'F6F7F8', head: 'F1F3F5',
  teal: '1C2126', tealSoft: 'EEF3FA', amber: '8F5B00', amberSoft: 'F8F1E6', red: 'B4361F', redSoft: 'F9E8E4', white: 'FFFFFF', blue: '2F6DB3', chartRed: 'C63F2B' };
const DK = { bg: '111417', panel: '181C20', line: '2A3036', fg: 'E5E9EC', muted: 'A1ABB4', blue: '6FA6E6', red: 'F07A66' };
const SOFT_LINE = { [C.panel]: C.line, [C.tealSoft]: 'D3E0F2', [C.amberSoft]: 'EAD9BE', [C.redSoft]: 'EDCAC2' };
const W = 13.333, H = 7.5, MX = 0.6;
const FONT = { head: 'Georgia', body: 'Arial' };
const FOOT = 'KYC approval-rate diagnosis · 2023 extracts (Jul 25 – Sep 22) · Case-study submission';
const SITE = 'https://prosolkin.github.io/arq-kyc/'; // the hosted dashboard; its password is only in the email
const REPO = 'https://github.com/prosolkin/arq-kyc'; // code, aggregated tables, deck and report

const slides = [];
function slide(section, title, opts = {}) {
  const s = { section, title, dark: !!opts.dark, els: [], notes: opts.notes || '' };
  if (title && !opts.noTitle) s.els.push({ t: 'text', x: MX, y: 0.42, w: W - 2 * MX, h: 0.95, font: 'head', size: opts.titleSize || 26, color: s.dark ? C.white : C.ink, paras: [{ text: title }] });
  slides.push(s);
  return s;
}
const text = (s, x, y, w, h, paras, o = {}) => s.els.push({ t: 'text', x, y, w, h, paras: paras.map((p) => (typeof p === 'string' ? { text: p } : p)), size: o.size || 14, color: o.color || C.ink, font: o.font || 'body', align: o.align, valign: o.valign });
const rect = (s, x, y, w, h, fill, o = {}) => s.els.push({ t: 'rect', x, y, w, h, fill, line: o.line || (o.radius ? SOFT_LINE[fill] : undefined), radius: o.radius });
const line = (s, x1, y1, x2, y2, color, o = {}) => s.els.push({ t: 'line', x1, y1, x2, y2, color, width: o.width || 1, dash: o.dash });
const table = (s, x, y, w, colW, rows, o = {}) => s.els.push({ t: 'table', x, y, w, colW, rows, size: o.size || 11, header: o.header !== false, rowH: o.rowH });
const stat = (s, x, y, w, big, label, o = {}) => {
  rect(s, x, y, w, o.h || 1.35, o.fill || C.panel, { radius: 0.08 });
  text(s, x + 0.2, y + 0.14, w - 0.4, 0.62, [{ text: big }], { font: 'head', size: o.bigSize || 30, color: o.color || C.ink });
  text(s, x + 0.2, y + 0.8, w - 0.4, (o.h || 1.35) - 0.85, [{ text: label }], { size: 11.5, color: C.muted });
};
const note = (s, paras, y = 6.62) => text(s, MX, y, W - 2 * MX, 0.42, paras, { size: 10.5, color: C.muted });

// ---------------- data used in several places ----------------
const scen = Object.fromEntries(D.scenario_totals.map((r) => [r.scenario, r]));
const incs = D.incidents.slice().sort((a, b) => +a.order - +b.order);
const actions = D.actions.slice().sort((a, b) => +a.order - +b.order);
const hyp = Object.fromEntries(D.hypotheses.map((h) => [h.id, h]));
const HL = { h_exec: 'H1', h_liveness: 'H2', h_attack: 'H3', h_ine: 'H4', h_mex_docs: 'H5', h_face: 'H6' };
const bridge = D.bridge.map((r) => ({ ...r, effect: +r.effect_pp, inc: +r.incident_pp, rest: +r.rest_pp }));
const b = (d) => bridge.find((r) => r.driver === d);
const expMex = row('experiments', 'id', 'exp_mex_docs');

// ======================= EXECUTIVE NARRATIVE =======================
{
  const s = slide('Executive narrative', null, { dark: true, noTitle: true,
    notes: 'Purpose: answer the brief in one pass. The headline metric is approval among recorded decisions. These extracts cannot measure the start-to-finish funnel that the brief describes, and the deck says so first. The interactive version of the same analysis is at prosolkin.github.io/arq-kyc. Its password is in the email.' });
  const sgn = (v, d) => (v < 0 ? MINUS : '+') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  text(s, MX, 0.5, W - 2 * MX, 0.7, [{ text: 'KYC pass rate: why it fell and what to do' }], { font: 'head', size: 32, color: DK.fg });
  text(s, MX, 1.28, 9.6, 0.6, [{ text: `The KYC pass rate (approval among recorded decisions) fell from ${pct(K('approval_a'))} to ${pct(K('approval_b'))} between the two periods (${sgn(K('delta_pp'), 1)} pp), or ${sgn(K('approved_change'), 0)} approvals.` }], { size: 15, color: DK.fg });
  text(s, MX, 1.98, W - 2 * MX, 0.42, [{ text: `${int(K('total_users'))} recorded decisions, one per user. Prior period: Jul 25 – Aug 23, 2023; recent period: Aug 24 – Sep 22, 2023. Aggregated data, no personal data.` },
    { text: 'Vendor research dated Oct 13, 2026.' }], { size: 10.5, color: DK.muted });
  // the daily chart, in a dark card
  const cx = MX, cy = 2.5, cw = 8.05, ch = 3.2;
  rect(s, cx, cy, cw, ch, DK.panel, { line: DK.line, radius: 0.08 });
  text(s, cx + 0.22, cy + 0.16, cw - 0.4, 0.3, [{ text: 'Approval among recorded decisions, by day', bold: true }], { size: 12, color: DK.fg });
  const days = D.daily.filter((r) => r.country === 'ALL');
  const L = cx + 0.62, R = cx + cw - 1.15, top = cy + 0.62, bot = cy + ch - 0.48, lo = 0.5, hi = 1.0;
  const yv = (v) => bot - (v - lo) / (hi - lo) * (bot - top);
  [0.6, 0.8, 1.0].forEach((v) => { line(s, L, yv(v), R, yv(v), DK.line, { width: 0.75 }); text(s, cx + 0.12, yv(v) - 0.09, 0.42, 0.2, [{ text: Math.round(v * 100) + '%' }], { size: 9, color: DK.muted, align: 'right' }); });
  const bw = (R - L) / days.length;
  days.forEach((d, i) => rect(s, L + i * bw + bw * 0.14, yv(+d.approval_rate), bw * 0.72, bot - yv(+d.approval_rate), d.incident_day === '1' ? DK.red : DK.blue));
  const split = days.findIndex((d) => d.date === '2023-08-24');
  [[0, split, K('approval_a'), 'Prior'], [split, days.length, K('approval_b'), 'Recent']].forEach(([a, z, v, name]) => {
    line(s, L + a * bw, yv(v), L + z * bw, yv(v), DK.muted, { width: 1, dash: 'dash' });
  });
  text(s, R + 0.08, yv(K('approval_a')) - 0.16, 1.0, 0.2, [{ text: 'Prior ' + pct(K('approval_a')) }], { size: 9, color: DK.muted });
  text(s, R + 0.08, yv(K('approval_b')) - 0.02, 1.0, 0.2, [{ text: 'Recent ' + pct(K('approval_b')) }], { size: 9, color: DK.muted });
  text(s, L, bot + 0.08, 1, 0.2, [{ text: 'Jul 25' }], { size: 9, color: DK.muted });
  text(s, L + split * bw - 0.5, bot + 0.08, 1, 0.2, [{ text: 'Aug 24' }], { size: 9, color: DK.muted, align: 'center' });
  text(s, R - 1, bot + 0.08, 1, 0.2, [{ text: 'Sep 22' }], { size: 9, color: DK.muted, align: 'right' });
  rect(s, L, cy + ch - 0.2, 0.12, 0.08, DK.blue); text(s, L + 0.18, cy + ch - 0.25, 1.4, 0.2, [{ text: 'Daily pass rate' }], { size: 9, color: DK.muted });
  rect(s, L + 1.55, cy + ch - 0.22, 0.12, 0.12, DK.red); text(s, L + 1.73, cy + ch - 0.25, 1.8, 0.2, [{ text: 'Incident window day' }], { size: 9, color: DK.muted });
  // what the deck covers, where the password card sits on the web page
  const tx = cx + cw + 0.18, tw = W - MX - tx;
  rect(s, tx, cy, tw, ch, DK.panel, { line: DK.line, radius: 0.08 });
  text(s, tx + 0.22, cy + 0.16, tw - 0.4, 0.3, [{ text: 'In this deck', bold: true }], { size: 12, color: DK.fg });
  text(s, tx + 0.22, cy + 0.52, tw - 0.4, 1.9, ['The answer in seven points', 'What we can and cannot measure', 'Why the rate fell', 'Short incidents', 'Hypotheses and tests', 'The plan in four tracks', 'What we gain', 'Evidence appendix (A1–A11)']
    .map((t, i) => ({ text: `${i + 1}.  ${t}`, after: 3 })), { size: 11, color: DK.fg });
  line(s, tx + 0.22, cy + 2.44, tx + tw - 0.22, cy + 2.44, DK.line, { width: 0.75 });
  text(s, tx + 0.22, cy + 2.52, tw - 0.4, 0.62, [
    { text: 'Website: ' + SITE.replace('https://', '').replace(/\/$/, ''), link: SITE, size: 10.5, color: DK.blue, after: 3 },
    { text: 'Code and data: ' + REPO.replace('https://', ''), link: REPO, size: 10.5, color: DK.blue, after: 3 },
    { text: 'The website has a chat. Its password is in the email.', size: 9, color: DK.muted },
  ], { size: 11, color: DK.fg });
  // three tiles, like the web page
  const tiles = [
    ['Pass rate change', `${MINUS}${Math.abs(K('delta_pp')).toFixed(1)} pts`, `${pct(K('approval_a'))} → ${pct(K('approval_b'))}, prior to recent 30 days`],
    ['Approvals', `${MINUS}${pct(Math.abs(K('approved_change_rel')))}`, `${int(K('approved_change'))} fewer: ${pct(K('volume_effect_share'), 0)} from fewer decisions, ${pct(K('rate_effect_share'), 0)} from the lower rate`],
    ['Short incidents', `≈${int(K('incident_excess_base'))}`, 'failures above baseline in four date windows; causes not confirmed'],
  ];
  const gap = 0.18, tw3 = (W - 2 * MX - 2 * gap) / 3, ty = cy + ch + 0.18, th = 1.32;
  tiles.forEach(([label, big, sub], i) => {
    const x = MX + i * (tw3 + gap);
    rect(s, x, ty, tw3, th, DK.panel, { line: DK.line, radius: 0.08 });
    text(s, x + 0.22, ty + 0.12, tw3 - 0.4, 0.24, [{ text: label }], { size: 10, color: DK.muted });
    text(s, x + 0.22, ty + 0.36, tw3 - 0.4, 0.5, [{ text: big }], { font: 'head', size: 24, color: DK.fg });
    text(s, x + 0.22, ty + 0.86, tw3 - 0.4, 0.42, [{ text: sub }], { size: 9.5, color: DK.muted });
  });
}
{
  const s = slide('Executive narrative', 'Where to find the work: the website, the code and this report', { notes: 'The website shows the same analysis and figures as this report, with a chat about the case. Its password is in the email. The repository holds the scripts and the aggregated tables, and one build makes every output from the two extracts.' });
  const cards = [
    ['Website', 'Interactive version', SITE.replace('https://', '').replace(/\/$/, ''), SITE, [
      'The same analysis and figures as this report, on one website.',
      'Four main tabs: Quick review, Why it fell, What to do and What we gain. Eight detail pages sit under Details.',
      'A chat answers questions about the case from the case material only.',
      'The password is in the email.']],
    ['GitHub', 'Code and data', REPO.replace('https://', ''), REPO, [
      `The scripts and the ${D_FILES} aggregated tables behind every number.`,
      'One build makes the website, this deck and the report from the two extracts.',
      'The raw extracts are not in the repository. It holds aggregates only, with no personal data.',
      'The README shows where to start.']],
    ['PDF', 'This report', 'kyc-approval-report.pdf', null, [
      'The executive narrative: what changed, why, what to do and what we gain.',
      'The evidence appendix, A1 to A11.',
      'The methodology and validation note: definitions, data checks, methods and limits.']],
  ];
  const gap = 0.25, cw = (W - 2 * MX - 2 * gap) / 3, y = 1.55, h = 4.75;
  cards.forEach(([tag, name, addr, url, points], i) => {
    const x = MX + i * (cw + gap);
    rect(s, x, y, cw, h, C.panel, { radius: 0.08 });
    text(s, x + 0.3, y + 0.28, cw - 0.6, 0.3, [{ text: tag.toUpperCase() }], { size: 10, color: C.muted });
    text(s, x + 0.3, y + 0.58, cw - 0.6, 0.45, [{ text: name }], { font: 'head', size: 22, color: C.ink });
    text(s, x + 0.3, y + 1.12, cw - 0.6, 0.35, [url ? { text: addr, link: url } : { text: addr }], { size: 13, color: url ? C.blue : C.ink });
    line(s, x + 0.3, y + 1.62, x + cw - 0.3, y + 1.62, C.line, { width: 0.75 });
    text(s, x + 0.3, y + 1.8, cw - 0.6, h - 2.0, points.map((t) => ({ text: t, bullet: true, after: 7 })), { size: 12.5, color: C.ink });
  });
  note(s, [{ text: 'Every figure in the website, the deck and the report comes from the same aggregated tables.' }]);
}
{
  const s = slide('Executive narrative', 'The answer in seven points', { notes: 'The seven points follow the order that an executive needs. They are: what we can measure, what changed, the arithmetic, the hypotheses, the first steps, the needs, and the checks.' });
  const items = [
    ['What is measurable', 'Approval among recorded decisions, by day, document country and failed check. Not measurable: starts, completion, abandonment, retries, review outcomes, time to completion.'],
    ['What changed', `Pass rate ${pct(K('approval_a'))} → ${pct(K('approval_b'))} (${pp(K('delta_pp'))}, ${pct(Math.abs(K('delta_rel')))} relative). Approvals ${pct(Math.abs(K('approved_change_rel')))} fewer (${sint(K('approved_change'))}): ${pct(K('volume_effect_share'), 0)} of that from fewer decisions, ${pct(K('rate_effect_share'), 0)} from the lower rate.`],
    ['Arithmetic drivers', `Fraud signals ${pp(b('Fraud signal').effect, 2)}, execution errors ${pp(b('Execution error').effect, 2)}, selfie / liveness ${pp(b('Selfie / liveness').effect, 2)}, no document type ${pp(b('No document type, no reason code').effect, 2)}. Face match improved (${pp(b('Face match').effect, 2)}).`],
    ['Still hypotheses', `${int(K('incident_excess_base'))} failures (range ${int(K('incident_excess_low'))}–${int(K('incident_excess_high'))}) sit above baseline in four date windows. Fraud signals are not adjudicated; the execution errors are unattributed; vendor incidents on Sep 1 and 6 are documented, but impact on ARQ is not.`],
    ['First (Phase 0, weeks 0–2)', 'Instrument the funnel and hold and retry execution errors. Alert per reason code. Reconcile control findings and adjudicate fraud samples. Diagnose Mexican "no document type" with the vendor.'],
    ['Needed', 'Event schema with privacy sign-off; vendor case access and incident reports; Risk and Compliance time; one medium and several small engineering items (sizes to confirm).'],
    ['Verification', `Acceptance criteria per action; experiments on eventual approval per person within 7 days. Scenarios for repeated causes: ${pp(+scen.Conservative.steady_pp)} to ${pp(+scen.Optimistic.steady_pp)}, not forecasts. Confirmed control gaps could cost up to ${pp(Math.abs(+scen.Central.control_gap_all_pp)).replace('+', '')}.`],
  ];
  items.forEach(([k, v], i) => {
    const y = 1.45 + i * 0.73;
    rect(s, MX, y + 0.04, 0.42, 0.42, C.teal, { radius: 0.21 });
    text(s, MX, y + 0.1, 0.42, 0.32, [{ text: String(i + 1) }], { size: 13, color: C.white, align: 'center' });
    text(s, MX + 0.6, y + 0.05, 2.6, 0.62, [{ text: k }], { size: 14, color: C.teal });
    text(s, MX + 3.25, y + 0.05, W - 2 * MX - 3.25, 0.66, [{ text: v }], { size: 12.5 });
  });
}
{
  const s = slide('Executive narrative', 'We can measure approval among recorded decisions, not the start-to-finish funnel', { notes: 'The brief defines pass rate as people who start and finish KYC. The extracts hold one recorded decision per user with a date only, so the headline is approval among recorded decisions. Completion, eventual approval and abandonment need new events.' });
  rect(s, MX, 1.5, 4.1, 4.85, C.tealSoft, { radius: 0.08 });
  text(s, MX + 0.25, 1.68, 3.6, 4.6, [
    { text: 'Headline metric', bold: true, color: C.teal, after: 6 },
    { text: 'Approval rate = approved (PASSED or APPROVED) ÷ recorded decisions.', after: 10 },
    { text: `Prior period ${pct(K('approval_a'))}, recent ${pct(K('approval_b'))}.`, after: 10 },
    { text: 'WARNING counts as not approved and not as a confirmed rejection. Its later review outcome is not in the data.', after: 10, size: 12, color: C.muted },
    { text: 'Each record is one user; the extract does not say whether it is a first, latest or final attempt, nor what event its date marks.', size: 12, color: C.muted },
  ], { size: 14 });
  const mrows = [['Metric', 'Status', 'Prior', 'Recent']].concat(D.metrics.filter((m) => ['approval_rate', 'warning_rate', 'completion_rate', 'eventual_approval', 'abandonment', 'retry_outcomes', 'review_outcomes', 'time_to_decision'].includes(m.id))
    .map((m) => [m.name, m.status, m.value_a === '' ? '—' : (m.unit === 'pct' ? pct(+m.value_a) : int(+m.value_a)), m.value_b === '' ? '—' : (m.unit === 'pct' ? pct(+m.value_b) : int(+m.value_b))]));
  table(s, 5.0, 1.5, 4.6, [2.1, 1.0, 0.75, 0.75], mrows.map((r, i) => i === 0 ? r : [r[0], { text: r[1], color: r[1] === 'Available' ? C.teal : C.red, bold: true }, r[2], r[3]]), { size: 11 });
  text(s, 9.9, 1.5, 2.85, 4.9, [
    { text: 'To measure the funnel, log', bold: true, color: C.teal, after: 6 },
    ...D.events.map((e) => ({ text: e.event, bullet: true, size: 11.5, after: 2 })),
    { text: 'with person, session and attempt ids, timestamps and app/SDK version.', size: 11.5, color: C.muted },
  ], { size: 13 });
  note(s, [{ text: 'Do not read the approval rate as completion. People who never submit, and approvals after retry or review, are not visible here. Whether true completion is lower or higher cannot be determined from these extracts.' }]);
}
{
  const s = slide('Executive narrative', `Approval fell from ${pct(K('approval_a'))} to ${pct(K('approval_b'))}: ${int(K('approved_change'))} fewer approvals`, { notes: 'The count fell for two reasons: fewer decisions in the recent period, and a lower approval rate. Only the rate effect is about KYC performance.' });
  stat(s, MX, 1.5, 3.9, `${pct(K('approval_a'))} → ${pct(K('approval_b'))}`, `Approval among recorded decisions, prior → recent period (${pp(K('delta_pp'))})`, { bigSize: 28 });
  stat(s, MX, 3.0, 3.9, sint(K('approved_change')), `Approvals: ${sint(K('volume_effect'))} from fewer decisions at the prior rate, ${sint(K('rate_effect'))} from the lower rate`, { bigSize: 28 });
  stat(s, MX, 4.5, 1.88, `${pct(K('mex_approval_b'))}`, `Mexican documents (was ${pct(K('mex_approval_a'))})`, { bigSize: 24 });
  stat(s, MX + 2.02, 4.5, 1.88, `${pct(K('arg_approval_b'))}`, `Argentine documents (was ${pct(K('arg_approval_a'))})`, { bigSize: 24 });
  // daily columns
  const days = D.daily.filter((r) => r.country === 'ALL');
  const cx = 4.9, cy = 1.55, cw = W - MX - cx, ch = 4.55, lo = 0.4, hi = 1.0;
  text(s, cx, cy - 0.05, cw, 0.3, [{ text: 'Daily approval rate, all documents (red = incident window days)' }], { size: 11.5, color: C.muted });
  const top = cy + 0.75, bot = cy + ch - 0.35, yv = (v) => bot - (v - lo) / (hi - lo) * (bot - top);
  [0.4, 0.6, 0.8, 1.0].forEach((v) => { line(s, cx + 0.45, yv(v), cx + cw, yv(v), C.line, { width: 0.75 }); text(s, cx, yv(v) - 0.1, 0.4, 0.2, [{ text: Math.round(v * 100) + '%' }], { size: 9.5, color: C.faint, align: 'right' }); });
  const incDays = new Set(incs.flatMap((i) => i.days.split(',')));
  const bw = (cw - 0.5) / days.length;
  days.forEach((d, i) => {
    const v = +d.approval_rate, x = cx + 0.5 + i * bw;
    rect(s, x, yv(v), bw * 0.72, bot - yv(v), incDays.has(d.date) ? C.chartRed : C.blue);
  });
  const splitIdx = days.findIndex((d) => d.date === '2023-08-24');
  line(s, cx + 0.5 + splitIdx * bw - bw * 0.14, top - 0.05, cx + 0.5 + splitIdx * bw - bw * 0.14, bot, C.ink, { width: 1, dash: 'dash' });
  text(s, cx + 0.5 + splitIdx * bw, top - 0.3, 2, 0.25, [{ text: 'Recent period →' }], { size: 10, color: C.ink });
  text(s, cx + 0.45, bot + 0.06, 1.2, 0.22, [{ text: 'Jul 25' }], { size: 9.5, color: C.faint });
  text(s, cx + cw - 1.2, bot + 0.06, 1.2, 0.22, [{ text: 'Sep 22' }], { size: 9.5, color: C.faint, align: 'right' });
  note(s, [{ text: `Without the ${int(K('incident_days_n'))} incident days (red), the recent rate is ${pct(K('approval_b_excl_days'))}: ${pp(K('delta_excl_days_pp'), 2)}. Those days hold ${pct(K('share_recent_on_incident_days'), 0)} of recent decisions, so they stay in. Mexican documents were ${pct(K('mex_share_a'))} of decisions, then ${pct(K('mex_share_b'))}. Columns start at 40%.` }]);
}
{
  const s = slide('Executive narrative', 'Four reasons explain most of the change; face match improved but remains a large loss', { notes: 'Each unsuccessful decision gets one primary reason in check order, so effects add up to the total change. Red is the part above baseline inside the four date windows (base estimate).' });
  const x0 = MX + 3.3, x1 = 8.3, lo = -2.75, hi = 0.6, xv = (v) => x0 + (v - lo) / (hi - lo) * (x1 - x0);
  bridge.forEach((r, i) => {
    const y = 1.65 + i * 0.5;
    text(s, MX, y + 0.04, 3.2, 0.3, [{ text: r.driver }], { size: 12, align: 'right' });
    if (r.inc) rect(s, Math.min(xv(0), xv(r.inc)), y, Math.abs(xv(r.inc) - xv(0)), 0.32, C.red);
    const st = Math.sign(r.rest) === Math.sign(r.inc) ? r.inc : 0;
    if (Math.abs(r.rest) > 1e-9) rect(s, Math.min(xv(st), xv(st + r.rest)), y, Math.abs(xv(st + r.rest) - xv(st)), 0.32, C.blue);
    const endX = r.effect < 0 ? xv(Math.min(r.effect, r.inc)) - 0.85 : xv(Math.max(r.effect, 0)) + 0.08;
    text(s, endX, y + 0.04, 0.8, 0.3, [{ text: pp(r.effect, 2), bold: true }], { size: 11.5, align: r.effect < 0 ? 'right' : 'left' });
  });
  line(s, xv(0), 1.55, xv(0), 1.65 + bridge.length * 0.5, C.ink, { width: 1 });
  rect(s, MX + 3.3, 6.25, 0.22, 0.18, C.red); text(s, MX + 3.6, 6.22, 3.0, 0.25, [{ text: 'Above baseline in incident windows' }], { size: 10.5, color: C.muted });
  rect(s, MX + 6.6, 6.25, 0.22, 0.18, C.blue); text(s, MX + 6.9, 6.22, 2.0, 0.25, [{ text: 'Everything else' }], { size: 10.5, color: C.muted });
  rect(s, 8.9, 1.55, W - MX - 8.9, 4.7, C.panel, { radius: 0.08 });
  text(s, 9.1, 1.72, W - MX - 9.3, 4.5, [
    { text: 'How to read the bars', bold: true, color: C.teal, after: 8 },
    { text: `Fraud signals: ${pp(b('Fraud signal').inc, 2)} of ${pp(b('Fraud signal').effect, 2)} sits in two windows.`, bullet: true, after: 6 },
    { text: `Execution errors: almost all of ${pp(b('Execution error').effect, 2)} is on Sep 1–2.`, bullet: true, after: 6 },
    { text: `Selfie / liveness: ${pp(b('Selfie / liveness').inc, 2)} on Sep 1 and 6, ${pp(b('Selfie / liveness').rest, 2)} elsewhere.`, bullet: true, after: 6 },
    { text: `No document type, no reason code: ${pp(b('No document type, no reason code').effect, 2)}, all outside the windows, so it is a slower, continuous shift (mostly Mexican documents).`, bullet: true, after: 6 },
    { text: `Face match: ${pct(K('face_a'), 2)} → ${pct(K('face_b'), 2)} of decisions. Not a cause of the drop, but a large loss from before the drop.`, bullet: true },
  ], { size: 12.5 });
  note(s, [{ text: `${int(K('multi_fail_b'))} recent unsuccessful decisions had two or more failed checks. A primary reason prevents double counts. A fix for that reason does not by itself get the person approved.` }]);
}
{
  const s = slide('Executive narrative', `About ${int(K('incident_excess_base'))} failures sit above baseline in four windows; causes are unconfirmed`, { notes: 'Attribution is observed minus expected at the prior-period rate of the same signature. Dates only: we cannot match records to times of day. Other failures on those days are not attributed.' });
  const rows = [['Window (2023)', 'Type', 'Observed', 'Expected', 'Above baseline', 'Of recent unsuccessful', 'Approval pts']]
    .concat(incs.map((i) => [`${i.order}. ${i.title}, ${i.when}`, i.type, int(+i.observed), (+i.expected).toFixed(1), int(+i.excess), pct(+i.share_of_unsuccessful_b), pp(+i.contribution_pp, 2)]))
    .concat([[{ text: 'Total', bold: true }, '', '', '', { text: int(K('incident_excess_base')), bold: true }, { text: pct(K('incident_share_unsuccessful')), bold: true }, { text: pp(K('incident_contribution_pp'), 2), bold: true }]]);
  table(s, MX, 1.5, W - 2 * MX, [3.6, 3.0, 0.95, 0.95, 1.2, 1.35, 1.08], rows, { size: 11.5 });
  const ex = row('incidents', 'id', 'exec_errors'), arg = row('incidents', 'id', 'fraud_arg');
  text(s, MX, 4.25, 5.9, 2.3, [
    { text: 'What we know and what we do not know', bold: true, color: C.teal, after: 6 },
    { text: `Argentina, Aug 24: ${int(+arg.volume)} decisions vs a typical ${int(+arg.baseline_volume)}; ${int(+arg.liveness_passed)} of the flagged passed liveness. Suggests attack traffic; not adjudicated.`, bullet: true, size: 12, after: 4 },
    { text: `Sep 1–2: usability TECHNICAL_ERROR, liveness passed in all ${int(+ex.liveness_passed)}, screening passed in ${int(+ex.screening_passed)}. Vendor or ARQ integration: unknown.`, bullet: true, size: 12, after: 4 },
    { text: 'Mexico, Sep 14–19: INE flags without extra volume: fraud, a rule change or a new card version.', bullet: true, size: 12 },
  ], { size: 13 });
  rect(s, 6.85, 4.25, W - MX - 6.85, 2.25, C.amberSoft, { radius: 0.08 });
  text(s, 7.05, 4.38, W - MX - 7.25, 2.1, [
    { text: 'Vendor status page (read Oct 13, 2026)', bold: true, color: C.amber, after: 6 },
    { text: 'Liveness incidents on the vendor’s US data centre: Sep 1 (15:38–16:42 and 18:07–22:44 UTC) and Sep 6 (10:00–17:22 UTC). No entry for Sep 2 or for the fraud-signal dates.', size: 12, after: 6 },
    { text: 'A documented vendor incident is not confirmation of impact on ARQ.', size: 12, color: C.muted },
  ], { size: 13 });
  note(s, [{ text: `Without the ${int(K('incident_days_n'))} incident days the rate still fell ${pp(K('delta_excl_days_pp'), 2)} (${pct(K('approval_a_excl_days'))} → ${pct(K('approval_b_excl_days'))}); they hold ${pct(K('share_recent_on_incident_days'), 0)} of recent decisions. Sensitivity range ${int(K('incident_excess_low'))}–${int(K('incident_excess_high'))} across window, signature and baseline variants. Without the ${int(K('selected_incident'))} failures that match the patterns, the rate is ${pct(K('approval_excl_selected'), 2)}. That is a descriptive rate, not performance without incidents.` }]);
}
{
  const s = slide('Executive narrative', 'Six hypotheses, each with the step that would settle it', { notes: 'None of these is established. Each row names the evidence, the strongest alternative, and the investigation and the decision it enables.' });
  const short = {
    h_exec: ['Execution errors on Sep 1–2 became rejections', 'Vendor fault vs ARQ integration or network', 'Pull ARQ logs and raw responses; vendor incident report', 'Fault owner; SLA question; hold-and-retry either way'],
    h_liveness: ['Liveness failures on Sep 1 and 6 were a vendor fault', 'ARQ app or SDK release', 'Release log; vendor list of affected transactions', 'Escalate; test a retake policy'],
    h_attack: ['Aug 24 Argentina burst was coordinated fraud', 'Vendor false positives during a campaign', 'Adjudicate a sample; channel and device data', 'Pre-vendor velocity controls'],
    h_ine: ['Sep 14–19 INE flags reflect a vendor rule change', 'Quieter fraud; new INE card version', 'Sample review with the vendor; registry check', 'Review vs auto-decline for INE flags'],
    h_mex_docs: ['Mexican "no document type" has several causes', 'Unsupported documents, capture, configuration, coverage', 'Review 100 cases with the vendor; config history', 'Picker vs configuration vs escalation'],
    h_face: ['Face mismatches partly reflect old ID photos', 'Impostors; poor light on the selfie', 'Adjudicate NO_MATCH and NOT_POSSIBLE samples', 'Review queue or registry face check'],
  };
  const rows = [['', 'Hypothesis', 'Strongest alternative', 'Next step', 'Decision it enables']].concat(Object.entries(short).map(([id, v]) => [HL[id], ...v]));
  table(s, MX, 1.5, W - 2 * MX, [0.55, 3.5, 2.85, 2.95, 2.28], rows, { size: 11.5 });
  note(s, [{ text: `Data behind each: H1 ${int(+row('incidents', 'id', 'exec_errors').observed)} TECHNICAL_ERROR rejections. H2 ${int(+row('incidents', 'id', 'liveness_spike').observed)} liveness quality failures on two days. H3 ${int(+row('incidents', 'id', 'fraud_arg').observed)} signals with doubled volume. H4 ${int(+row('incidents', 'id', 'fraud_mex').observed)} INE signals at normal volume. H5 no document type ${pct(K('mex_nodoc_a'))} → ${pct(K('mex_nodoc_b'))} of Mexican decisions. H6 face match ${pct(K('face_b'), 2)} of recent decisions.` }], 6.25);
}
{
  const s = slide('Executive narrative', 'The plan in four tracks: fix and measure, test, learn, build', { notes: 'Rows are the kind of work, columns are time. Fixes and instruments go first, because they are cheap and useful whatever the root cause. Experiments test the obvious hypotheses. Research runs beside them, from support tickets up to eye tracking. Platform work comes later. Items marked ◌ are conditional.' });
  const tracks = D.tracks.slice().sort((a, b) => +a.order - +b.order), phases = D.phases;
  const labelW = 2.3, gap = 0.08, colW = (W - 2 * MX - labelW - 3 * gap) / 4, lineH = 0.23;
  let y = 1.45;
  rect(s, MX, y, labelW, 0.38, C.teal, { radius: 0.05 });
  text(s, MX + 0.12, y + 0.07, labelW - 0.24, 0.26, [{ text: 'Track' }], { size: 10.5, color: C.white });
  phases.forEach((p, i) => { const x = MX + labelW + gap + i * (colW + gap); rect(s, x, y, colW, 0.38, i === 3 ? C.amberSoft : C.tealSoft, { radius: 0.05 }); text(s, x + 0.1, y + 0.07, colW - 0.2, 0.26, [{ text: p.label.replace('Phase ', 'P') }], { size: 10, color: i === 3 ? C.amber : C.teal }); });
  y += 0.46;
  tracks.forEach((t) => {
    const cells = phases.map((p) => actions.filter((a) => a.track === t.id && a.phase === p.phase));
    const rows = Math.max(1, ...cells.map((c) => c.length));
    const h = 0.16 + rows * lineH;
    rect(s, MX, y, labelW, h, C.panel, { radius: 0.05 });
    text(s, MX + 0.12, y + 0.06, labelW - 0.24, h - 0.1, [{ text: t.name, bold: true, after: 2 }, { text: t.note, size: 9, color: C.muted }], { size: 11, color: C.teal });
    cells.forEach((list, i) => {
      const x = MX + labelW + gap + i * (colW + gap);
      rect(s, x, y, colW, h, C.white, { line: C.line, radius: 0.05 });
      if (list.length) text(s, x + 0.1, y + 0.06, colW - 0.2, h - 0.1, list.map((a, k) => ({ text: (a.conditional ? '◌ ' : '• ') + a.title, size: 9.5, color: a.conditional ? C.amber : C.ink, after: k < list.length - 1 ? 1 : 0 })), { size: 9.5 });
    });
    y += h + gap;
  });
  note(s, [{ text: '◌ = conditional on a Phase 0 finding. Owners, evidence, acceptance criteria and guardrails per action are in the dashboard (What to do). Effort sizes are assumptions.' }], Math.max(y + 0.05, 6.55));
}
{
  const s = slide('Executive narrative', 'Phase 0, weeks 0–2: measure and stabilise before we optimise', { notes: 'Phase 0 is mostly measurement and investigation, plus one remediation (hold and retry) that is useful whatever the root cause.' });
  const p0 = actions.filter((a) => a.phase === '0');
  p0.forEach((a, i) => {
    const col = i % 4, r = Math.floor(i / 4);
    const x = MX + col * 3.07, y = 1.5 + r * 2.45, w = 2.92;
    rect(s, x, y, w, 2.3, i === 1 ? C.tealSoft : C.panel, { radius: 0.08 });
    text(s, x + 0.17, y + 0.14, w - 0.34, 0.6, [{ text: a.title, bold: true }], { size: 12.5, color: C.teal });
    text(s, x + 0.17, y + 0.78, w - 0.34, 0.3, [{ text: `${a.owner} · ${a.kind} · ${a.effort.split(' ')[0]}` }], { size: 10, color: C.muted });
    text(s, x + 0.17, y + 1.2, w - 0.34, 1.05, [{ text: 'Done when: ' + a.acceptance }], { size: 10.5 });
  });
  note(s, [{ text: 'Effort sizes are assumptions (S ≤ 2 engineer-weeks, M = 2–6). Owners are role-based examples, not named people. Later phases: P1 weeks 2–6, P2 weeks 6–13, P3 the next two quarters.' }]);
}
{
  const s = slide('Executive narrative', `Recovery scenarios: ${pp(+scen.Conservative.steady_pp)} to ${pp(+scen.Optimistic.steady_pp)} on repeated causes, not a forecast`, { notes: 'Each population is observed; every multiplier is an assumption. Populations do not overlap. Incident-type benefits occur only when a comparable incident recurs. Control-gap reversals are shown separately.' });
  ['Conservative', 'Central', 'Optimistic'].forEach((n, i) => {
    const t = scen[n];
    stat(s, MX + i * 2.55, 1.5, 2.4, pp(+t.steady_pp), `${n}: ${int(+t.steady_30d)} approvals per 30 days; recent rate would be ${pct(+t.approval_with_steady)}`, { h: 1.8, bigSize: 30, fill: i === 1 ? C.tealSoft : C.panel });
  });
  stat(s, MX + 7.75, 1.5, 2.25, int(+scen.Central.per_incident), 'Central: approvals protected per comparable incident (execution errors, liveness spikes)', { h: 1.8, bigSize: 28 });
  stat(s, MX + 10.15, 1.5, W - 2 * MX - 10.15, sint(+scen.Central.control_gap_all), `If all control findings are confirmed: approvals per 30 days that we may need to reverse (${pp(+scen.Central.control_gap_all_pp)})`, { h: 1.8, bigSize: 26, fill: C.redSoft, color: C.red });
  text(s, MX, 3.5, W - 2 * MX, 0.4, [{ text: 'Recovered = observed population × eligibility × reach × return × remediation × subsequent approval', bold: true }], { size: 13, color: C.teal });
  const rows = [['Population (recent period)', 'Observed', 'Central factors (E × R × Ret × Fix × Then)', 'Central', 'Range']].concat(
    ['tech_error_hold', 'liveness_retake_incident', 'liveness_retake', 'mex_doc_guidance', 'capture_quality', 'review_queue'].map((a) => {
      const g = (sc) => D.scenarios.find((r) => r.action === a && r.scenario === sc);
      const c = g('Central');
      const f = (v) => (+v).toFixed(2).replace(/0$/, '').replace(/\.$/, '');
      return [c.population + (c.cadence === 'Per comparable incident' ? ' (per incident)' : ''), int(+c.observed_n), [c.eligibility, c.reach, c.return_rate, c.remediation, c.subsequent_approval].map(f).join(' × '), int(+c.recovered), `${int(+g('Conservative').recovered)}–${int(+g('Optimistic').recovered)}`];
    }));
  table(s, MX, 3.95, W - 2 * MX, [4.55, 1.05, 4.0, 1.0, 1.53], rows, { size: 10.5 });
  note(s, [{ text: 'A target set from these scenarios is a goal, not a prediction. "Eligible" for selfie populations is the observed share with no other failed check. "Then" is the prior-period approval rate for the same countries, except review, where a reviewer approval is final.' }], 6.55);
}
{
  const s = slide('Executive narrative', 'What we need, and how we will know it worked', { notes: 'The ask is small in Phase 0. Verification is per action (acceptance criteria) and per experiment (eventual approval per person within 7 days).' });
  rect(s, MX, 1.5, 5.9, 4.9, C.panel, { radius: 0.08 });
  text(s, MX + 0.25, 1.68, 5.4, 4.7, [
    { text: 'Decisions and resources', bold: true, color: C.teal, after: 8 },
    { text: 'Approve Phase 0 and its owners.', bullet: true, after: 5 },
    { text: 'Privacy review of the event schema (Legal & Privacy).', bullet: true, after: 5 },
    { text: 'Vendor: case access, raw responses, incident reports for Sep 1, 2 and 6.', bullet: true, after: 5 },
    { text: 'Risk and Compliance time: fraud adjudication and control reconciliation.', bullet: true, after: 5 },
    { text: 'Engineering: instrumentation (M), hold-and-retry (S), alerts (S). Sizes to confirm.', bullet: true, after: 5 },
    { text: 'Finance: replace the value model’s market-based presets with ARQ unit economics.', bullet: true },
  ], { size: 13 });
  rect(s, 6.75, 1.5, W - MX - 6.75, 4.9, C.tealSoft, { radius: 0.08 });
  text(s, 7.0, 1.68, W - MX - 7.25, 4.7, [
    { text: 'How success is verified', bold: true, color: C.teal, after: 8 },
    { text: 'Zero final rejections with TECHNICAL_ERROR over 4 weeks.', bullet: true, after: 5 },
    { text: 'Alerts replayed on 2023 data fire on the first day of all four windows.', bullet: true, after: 5 },
    { text: 'Each control finding classified as confirmed, explained or data error.', bullet: true, after: 5 },
    { text: `Experiments by person, outcome = eventual approval within 7 days. Mexico guidance: about ${int(+expMex.sample.match(/about ([\d,]+)/)[1].replace(/,/g, ''))} people per arm for +2 pp (stand-in baseline).`, bullet: true, after: 5 },
    { text: 'Weekly: approval rate with fraud-signal, execution-error and warning shares beside it; completion once events exist.', bullet: true },
  ], { size: 13 });
}

{
  const q = D.open_questions.slice().sort((a, b) => +a.order - +b.order);
  const s = slide('Executive narrative', 'Four things to confirm with the team before we act', { notes:
    'These are not asked in the submission. They are the answers that would change the findings. Each row says what changes with the answer.\n\n'
    + q.map((r) => r.order + '. ' + r.question + ' Who would know: ' + r.who).join('\n\n') });
  const rows = [['', 'Question', 'Why it matters', 'What the answer changes']].concat(q.map((r) => [String(r.order), r.question, r.why, r.changes]));
  table(s, MX, 1.4, W - 2 * MX, [0.35, 3.9, 4.5, 3.38], rows, { size: 11 });
  note(s, [{ text: 'The analysis stands on the extract alone. These answers decide how far each conclusion carries, not whether the work was done.' }], 6.5);
}

// ======================= APPENDIX =======================
{
  const s = slide('Appendix', null, { dark: true, noTitle: true, notes: 'Evidence appendix: definitions, validation, composition, Mexico, incident sensitivity, experiments, value model, operating model, control findings, vendor research.' });
  text(s, MX, 2.7, 11, 1.0, [{ text: 'Appendix: evidence and method' }], { font: 'head', size: 34, color: DK.fg });
  text(s, MX, 3.8, 11, 1.6, [{ text: 'A1 Definitions · A2 Validation · A3 Composition · A4 Mexico · A5 Incident sensitivity · A6 Experiments · A7–A8 Value model · A9 Operating model · A10 Control findings · A11 Vendor research' }], { size: 15, color: DK.muted });
}
{
  const s = slide('Appendix', 'A1 · Metric definitions: what is available and what needs new events', { notes: 'Proposed KPI registry entries. Unavailable metrics list the gap.' });
  const rows = [['Metric', 'Status', 'Definition and window', 'Gap or caveat']].concat(D.metrics.map((m) => [m.name, m.status, `${m.definition} Window: ${m.window.toLowerCase()}.`, m.gap || '—']));
  table(s, MX, 1.3, W - 2 * MX, [2.5, 1.05, 5.6, 2.98], rows, { size: 10 });
}
{
  const s = slide('Appendix', 'A2 · Data validation and outcome treatment', { notes: 'All checks recomputed on every build. Raw files are hashed to show they were not modified.' });
  const rows = [['Check', 'Result', 'Status', 'Treatment']].concat(D.validation.map((v) => [v.check, v.result, v.status, v.note]));
  table(s, MX, 1.3, W - 2 * MX, [2.25, 3.75, 0.85, 5.28], rows, { size: 10 });
}
{
  const s = slide('Appendix', 'A3 · What the not-approved share is made of', { notes: 'Classes describe who could act on a group of vendor reasons. They are not adjudicated causes.' });
  const cls = D.declines.filter((d) => d.level === 'class');
  const grp = D.declines.filter((d) => d.level === 'group');
  const rows = [['Group', 'Class', 'Prior', 'Recent', 'Of decisions, prior', 'Of decisions, recent', 'Of unsuccessful, recent']].concat(
    grp.map((g) => [g.name, g.class, int(+g.n_a), int(+g.n_b), pct(+g.share_a, 2), pct(+g.share_b, 2), pct(+g.of_unsuccessful_b)]),
    cls.map((g) => [{ text: g.name, bold: true }, 'Class total', int(+g.n_a), int(+g.n_b), pct(+g.share_a, 2), pct(+g.share_b, 2), pct(+g.of_unsuccessful_b)]));
  table(s, MX, 1.45, W - 2 * MX, [3.3, 3.0, 0.9, 0.9, 1.3, 1.35, 1.38], rows, { size: 10 });
  note(s, [{ text: `Not-approved share: ${pct(K('decline_a'))} prior, ${pct(K('decline_b'))} recent. ${int(K('warning_b'))} recent decisions are unresolved warnings, not confirmed rejections.` }]);
}
{
  const s = slide('Appendix', 'A4 · Mexico: "no document type" is a symptom with several outcomes', { notes: 'Share of all Mexican-document decisions. No reason code is the largest and grew; the cause is not established.' });
  const rows = [['Outcome for Mexican decisions with no document type', 'Prior', 'Recent', 'Share, prior', 'Share, recent', 'Change']].concat(
    D.mex_no_doctype.map((m) => [m.group, int(+m.n_a), int(+m.n_b), pct(+m.share_a, 2), pct(+m.share_b, 2), pp(+m.change_pp, 2)]));
  table(s, MX, 1.45, 7.6, [3.4, 0.75, 0.75, 0.9, 0.9, 0.9], rows, { size: 10.5 });
  const drow = [['Document type returned (Mexico)', 'Approval prior', 'Approval recent']].concat(D.docs.filter((d) => d.country === 'MEX').map((d) => [d.label, pct(+d.approval_rate_a), pct(+d.approval_rate_b)]));
  table(s, 8.5, 1.45, W - MX - 8.5, [2.25, 0.95, 1.03], drow, { size: 10.5 });
  note(s, [{ text: `Argentine documents: ${int(K('arg_usability_rejects'))} usability rejections or warnings in the extract; Mexican: ${int(K('mex_usability_rejects'))}. Possible causes include documents outside the accepted list, capture quality, a mismatch with the issuer country, configuration and vendor coverage.` }]);
}
{
  const s = slide('Appendix', 'A5 · Incident attribution: sensitivity and vendor evidence', { notes: 'Four baseline-based variants plus the old method (every failure of the pattern, no baseline) for comparison.' });
  const v = (id, variant) => int(+D.incident_sensitivity.find((r) => r.incident === id && r.variant === variant).attributed);
  const rows = [['Window', 'Base', 'Window ±1 day', 'Broader signature', 'Recent baseline', 'Old method (no baseline)']]
    .concat(incs.map((i) => [`${i.order}. ${i.title}`, v(i.id, 'base'), v(i.id, 'wide_window'), v(i.id, 'broad_signature'), v(i.id, 'recent_baseline'), v(i.id, 'all_matching')]))
    .concat([[{ text: 'Total', bold: true }, int(K('incident_excess_base')), '', '', '', int(K('incident_all_matching'))]]);
  table(s, MX, 1.45, 7.3, [2.5, 0.8, 0.95, 1.0, 0.95, 1.1], rows, { size: 10.5 });
  text(s, MX, 3.75, 7.3, 2.6, [
    { text: 'How to read it', bold: true, color: C.teal, after: 5 },
    { text: 'Base: failures that match the window\u2019s pattern, minus the count expected at the prior-period rate for the window\u2019s volume.', bullet: true, size: 11.5, after: 3 },
    { text: `Range across the four baseline-based variants: ${int(K('incident_excess_low'))}–${int(K('incident_excess_high'))}.`, bullet: true, size: 11.5, after: 3 },
    { text: 'The old method counts every failure of the pattern on the day. That includes failures that also occur on normal days.', bullet: true, size: 11.5 },
  ], { size: 12.5 });
  const er = [['Date', 'UTC', 'Vendor status page entry']].concat(D.vendor_evidence.map((e) => [e.date, e.window_utc || '—', e.description]));
  table(s, 8.15, 1.45, W - MX - 8.15, [1.05, 0.95, 2.58], er, { size: 10 });
}
{
  const s = slide('Appendix', 'A6 · Experiment and validation designs', { notes: 'With assignment by person, repeat attempts do not count as independent users. Sample sizes use stand-in baselines and must be recomputed after Phase 0.' });
  const ex = D.experiments;
  const fields = [['Kind', 'kind'], ['Hypothesis', 'hypothesis'], ['Population', 'population'], ['Assignment unit', 'unit'], ['Primary outcome', 'primary'], ['Window', 'window'], ['Minimum effect', 'mde'], ['Sample', 'sample'], ['Guardrails', 'guardrails'], ['Rules', 'rules']];
  const pickE = ['exp_mex_docs', 'exp_liveness'].map((id) => ex.find((e) => e.id === id));
  const rows = [['', 'Mexico document guidance', 'Guided liveness retake']].concat(fields.map(([l, f]) => [l, pickE[0][f], pickE[1][f]]));
  table(s, MX, 1.45, W - 2 * MX, [1.6, 5.27, 5.26], rows, { size: 10 });
}
{
  const vi = D.value_inputs;
  const s = slide('Appendix', 'A7 · Value model inputs: market-based presets, not ARQ figures', { notes:
    'Each preset comes from a published price, salary or fintech benchmark, fetched on the research date. The dashboard lists every source with its figure and fetch status. '
    + 'Low, Mid and High are the ends and middle of each input’s range, not pessimistic and optimistic cases. Cautious takes the end that weakens the case. '
    + 'Finance should replace each preset with ARQ’s own number; the value model recomputes immediately.' });
  const rows = [['Input', 'Low', 'Mid', 'High', 'Kind', 'Basis', 'Sources']].concat(vi.map((r) => [
    r.label + ' (' + (r.unit === 'share' ? '%' : r.unit) + ')', inputFmt(r, r.low), inputFmt(r, r.mid), inputFmt(r, r.high), r.kind, r.short, r.sources.split(' ').join(', ')]));
  table(s, MX, 1.3, W - 2 * MX, [3.05, 0.85, 0.85, 0.85, 1.6, 3.6, 1.33], rows, { size: 11 });
  const src = D.value_sources.map((r) => r.id + ' ' + r.publisher).join(' · ');
  note(s, [{ text: `Sources S1–S${D.value_sources.length}: the dashboard (What we gain) gives each figure, period and link.` }], 6.45);
}
{
  const vr = D.value_results;
  const P = ['Low', 'Mid', 'High', 'Cautious'];
  const get = (p, id) => vr.find((r) => r.preset === p && r.scenario === 'Central' && r.id === id);
  const fmtR = (r) => (r.value === '' ? '—' : r.unit === 'int' ? int(+r.value) : usd(+r.value));
  const ids = ['activated', 'cohort_value', 'annualised', 'breakeven', 'review_30d', 'vendor_declined', 'vendor_attack', 'paid_declined'];
  const vpa = (p) => { const r = D.value_inputs.find((x) => x.id === 'value_per_activated'); return +(p === 'Cautious' ? r[r.cautious] : r[p.toLowerCase()]); };
  const s = slide('Appendix', 'A8 · Value model results by preset, central scenario', { notes:
    `Central scenario: ${int(+scen.Central.steady_30d)} recoverable approvals per 30 days (range ${int(+scen.Conservative.steady_30d)}–${int(+scen.Optimistic.steady_30d)}). `
    + 'Cohort value = recoverable × activation rate × first-year value per activated customer. Break-even = (build cost ÷ 12 + run cost per month) ÷ (recoverable × activation rate). '
    + 'Vendor spend = decisions × billable transactions per decision × cost per transaction. These are illustrations on market-based inputs, not forecasts and not ARQ figures.' });
  const rows = [['Result (per 30 days unless stated)'].concat(P)].concat(ids.map((id) => [get('Mid', id).label].concat(P.map((p) => fmtR(get(p, id))))));
  rows.push(['Pays back within the first year? (value per activated customer vs break-even)'].concat(P.map((p) => { const b = +get(p, 'breakeven').value; return (vpa(p) >= b ? 'Yes: ' : 'No: ') + usd(vpa(p)) + ' vs ' + usd(b); })));
  table(s, MX, 1.3, W - 2 * MX, [5.33, 1.8, 1.8, 1.8, 1.4], rows, { size: 11.5 });
  note(s, [{ text: 'The first-year value of a cohort comes in over the next year. It is not revenue recognised in the next 12 months. Past vendor and paid-acquisition spend on not-approved applicants is already spent. Only a fix of the cause stops future spend.' }], 6.35);
}
{
  const s = slide('Appendix', 'A9 · Operating model: owned metrics with versions, lineage and adoption', { notes: 'Role-based example functions, not ARQ’s organisation. Relevant to a company KPI platform: definitions, owners, versions, freshness, access and adoption.' });
  const rows = [['Metric', 'Status', 'Owner (role)', 'Version', 'Lineage']].concat(D.metrics.filter((m) => ['approval_rate', 'completion_rate', 'eventual_approval', 'exec_error_rate', 'fraud_signal_rate', 'review_outcomes'].includes(m.id))
    .map((m) => [m.name, m.status, D.departments.find((d) => d.id === m.owner).name, m.version, m.lineage]));
  table(s, MX, 1.45, 7.2, [2.6, 1.0, 1.8, 0.65, 1.15], rows, { size: 10 });
  text(s, 8.1, 1.45, W - MX - 8.1, 2.4, [
    { text: 'Ownership rules', bold: true, color: C.teal, after: 5 },
    { text: 'One accountable owner per metric, effective-dated.', bullet: true, size: 11.5, after: 2 },
    { text: 'Definition changes need owner and Data approval; old versions stay queryable.', bullet: true, size: 11.5, after: 2 },
    { text: 'Past results stay attributed to the owner at the time.', bullet: true, size: 11.5 },
  ], { size: 12.5 });
  const ad = D.adoption.find((a) => a.topic === 'Success measures');
  text(s, 8.1, 4.0, W - MX - 8.1, 2.4, [
    { text: 'Adoption success measures', bold: true, color: C.teal, after: 5 },
    { text: ad.plan, size: 11.5 },
  ], { size: 12.5 });
  note(s, [{ text: 'This analysis is version 2.0 of the headline metric: v1.0 called it "pass rate"; v2.0 renamed it and defined completion separately.' }]);
}
{
  const s = slide('Appendix', 'A10 · Control findings in the extract: to reconcile, not confirmed failures', { notes: 'An approval record is not an enabled account; a blank field is not proof a check never ran. Legal obligations are not asserted here.' });
  const rows = [['Finding', 'Records', 'Other explanations', 'How to validate']].concat(D.compliance.map((c) => [c.finding, int(+c.n), c.alternatives, c.validation]));
  table(s, MX, 1.45, W - 2 * MX, [3.3, 0.9, 3.9, 4.03], rows, { size: 10.5 });
  note(s, [{ text: 'If an extracted birth year of 2006 or later is accurate, the person was under 18 during 2023. The applicable eligibility policy and the data quality both still need confirmation.' }]);
}
{
  const s = slide('Appendix', 'A11 · Vendor research (Oct 13, 2026): availability is not effectiveness', { notes: 'Kept separate from the 2023 diagnosis. Each row lists prerequisites and what is not verified for ARQ.' });
  const rows = [['Capability', '2023 problem', 'Documented', 'Prerequisites', 'Not verified for ARQ']].concat(D.vendor_capabilities.filter((c) => ['classification', 'usability', 'liveness', 'ctr', 'retrieval', 'sdk', 'ine', 'renaper'].includes(c.id))
    .map((c) => [c.capability, c.problem, c.documented, c.prerequisites, c.unverified]));
  table(s, MX, 1.45, W - 2 * MX, [1.8, 1.7, 3.8, 2.85, 1.98], rows, { size: 10 });
}

// ---------------- renderers ----------------
const EMU = 914400;
function renderPptx(file) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';
  pres.title = 'KYC approval-rate diagnosis';
  pres.author = 'KYC case study';
  pres.company = 'Case study';
  pres.theme = { headFontFace: FONT.head, bodyFontFace: FONT.body };
  pres.defineSlideMaster({ title: 'CONTENT', background: { color: C.bg },
    objects: [{ text: { text: FOOT, options: { x: MX, y: H - 0.42, w: 9, h: 0.25, fontSize: 9, color: C.faint, fontFace: FONT.body, margin: 0 } } }],
    slideNumber: { x: W - MX - 0.6, y: H - 0.42, w: 0.6, h: 0.25, fontSize: 9, color: C.faint, fontFace: FONT.body, align: 'right' } });
  pres.defineSlideMaster({ title: 'DARK', background: { color: DK.bg }, objects: [] });
  let section = null;
  slides.forEach((s) => {
    if (s.section !== section) { pres.addSection({ title: s.section }); section = s.section; }
    const sl = pres.addSlide({ masterName: s.dark ? 'DARK' : 'CONTENT', sectionTitle: s.section });
    s.els.forEach((e, idx) => {
      const name = `${e.t}-${idx}`;
      if (e.t === 'rect') {
        sl.addShape(e.radius ? pres.ShapeType.roundRect : pres.ShapeType.rect, { x: e.x, y: e.y, w: e.w, h: e.h, fill: { color: e.fill }, line: e.line ? { color: e.line, width: 0.75 } : { type: 'none' }, rectRadius: e.radius || 0, objectName: name });
      } else if (e.t === 'line') {
        sl.addShape(pres.ShapeType.line, { x: Math.min(e.x1, e.x2), y: Math.min(e.y1, e.y2), w: Math.abs(e.x2 - e.x1), h: Math.abs(e.y2 - e.y1), line: { color: e.color, width: e.width, dashType: e.dash || 'solid' }, objectName: name });
      } else if (e.t === 'text') {
        const runs = [];
        e.paras.forEach((p, pi) => {
          runs.push({ text: p.text, options: { bold: !!p.bold, color: p.color || e.color, fontSize: p.size || e.size, bullet: p.bullet ? (p.bullet === 'number' ? { type: 'number' } : { indent: 12 }) : false,
            paraSpaceAfter: p.after || 0, breakLine: pi < e.paras.length - 1, align: e.align || 'left', ...(p.link ? { hyperlink: { url: p.link } } : {}) } });
        });
        sl.addText(runs, { x: e.x, y: e.y, w: e.w, h: e.h, fontFace: e.font === 'head' ? FONT.head : FONT.body, margin: 0, valign: e.valign || 'top', fit: 'none', isTextBox: true, objectName: name });
      } else if (e.t === 'table') {
        const rows = e.rows.map((r, ri) => r.map((c) => {
          const cell = typeof c === 'object' ? c : { text: String(c) };
          const head = e.header && ri === 0;
          return { text: cell.text, options: { bold: head || !!cell.bold, color: head ? C.muted : (cell.color || C.ink), fill: { color: head ? C.head : C.white }, fontSize: e.size, fontFace: FONT.body, valign: 'top' } };
        }));
        sl.addTable(rows, { x: e.x, y: e.y, w: e.w, colW: e.colW, border: { type: 'solid', pt: 0.5, color: C.line }, margin: [0.04, 0.06, 0.04, 0.06], autoPage: false, objectName: name });
      }
    });
    if (s.notes) sl.addNotes(s.notes);
  });
  return pres.writeFile({ fileName: file });
}

const esc = (t) => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function renderHtml(file) {
  const parts = slides.map((s, si) => {
    const els = s.els.map((e) => {
      if (e.t === 'rect') return `<div style="position:absolute;left:${e.x}in;top:${e.y}in;width:${e.w}in;height:${e.h}in;background:#${e.fill};${e.line ? `border:0.75pt solid #${e.line};box-sizing:border-box;` : ''}border-radius:${e.radius ? Math.min(e.radius, 0.1) : 0}in"></div>`;
      if (e.t === 'line') {
        const horiz = Math.abs(e.y2 - e.y1) < 1e-6;
        return `<div style="position:absolute;left:${Math.min(e.x1, e.x2)}in;top:${Math.min(e.y1, e.y2)}in;width:${horiz ? Math.abs(e.x2 - e.x1) + 'in' : '0'};height:${horiz ? '0' : Math.abs(e.y2 - e.y1) + 'in'};${horiz ? 'border-top' : 'border-left'}:${e.width}pt ${e.dash ? 'dashed' : 'solid'} #${e.color}"></div>`;
      }
      if (e.t === 'text') {
        const ps = e.paras.map((p) => {
          const st = `margin:0 0 ${p.after || 0}pt 0;font-size:${p.size || e.size}pt;color:#${p.color || e.color};font-weight:${p.bold ? 700 : 400};text-align:${e.align || 'left'}`;
          const body = p.link ? `<a href="${esc(p.link)}" style="color:inherit;text-decoration:underline">${esc(p.text)}</a>` : esc(p.text);
          return p.bullet ? `<p style="${st};padding-left:14pt;text-indent:-10pt">•&nbsp;&nbsp;${body}</p>` : `<p style="${st}">${body}</p>`;
        }).join('');
        return `<div class="tx" style="position:absolute;left:${e.x}in;top:${e.y}in;width:${e.w}in;height:${e.h}in;font-family:${e.font === 'head' ? 'Georgia, serif' : 'Arial, sans-serif'}">${ps}</div>`;
      }
      if (e.t === 'table') {
        const cols = e.colW.map((w) => `<col style="width:${w}in">`).join('');
        const body = e.rows.map((r, ri) => '<tr>' + r.map((c) => {
          const cell = typeof c === 'object' ? c : { text: String(c) };
          const head = e.header && ri === 0;
          return `<td style="background:#${head ? C.head : C.white};color:#${head ? C.muted : (cell.color || C.ink)};font-weight:${head || cell.bold ? 700 : 400}">${esc(cell.text)}</td>`;
        }).join('') + '</tr>').join('');
        return `<table class="tb" style="position:absolute;left:${e.x}in;top:${e.y}in;width:${e.w}in;font-size:${e.size}pt"><colgroup>${cols}</colgroup>${body}</table>`;
      }
      return '';
    }).join('\n');
    const foot = s.dark ? '' : `<div class="foot" style="left:${MX}in">${esc(FOOT)}</div><div class="foot" style="right:${MX}in;text-align:right">${si + 1}</div>`;
    return `<section class="slide" id="s${si + 1}" style="background:#${s.dark ? DK.bg : C.bg}">${els}${foot}</section>`;
  }).join('\n');
  const doc = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>KYC approval-rate diagnosis</title><style>
@page { size: ${W}in ${H}in; margin: 0; }
html, body { margin: 0; padding: 0; background: #888; }
.slide { position: relative; width: ${W}in; height: ${H}in; overflow: hidden; break-after: page; margin: 0 auto; }
.tx { line-height: 1.2; }
.tb { border-collapse: collapse; table-layout: fixed; font-family: Arial, sans-serif; line-height: 1.2; }
.tb td { border: 0.5pt solid #${C.line}; padding: 0.04in 0.06in; vertical-align: top; overflow-wrap: anywhere; }
.foot { position: absolute; bottom: 0.17in; font: 9pt Arial, sans-serif; color: #${C.faint}; width: 9in; }
@media screen { .slide { margin: 0.3in auto; box-shadow: 0 2px 12px rgba(0,0,0,.3); } }
</style></head><body>${parts}</body></html>`;
  fs.writeFileSync(file, doc);
}

// every reader-facing string (titles, text boxes, table cells, speaker notes), for the writing check
function deckTexts() {
  const out = [];
  const cellText = (c) => (typeof c === 'string' ? c : c && c.text ? c.text : '');
  slides.forEach((s) => {
    if (s.title) out.push(s.title);
    if (s.notes) out.push(s.notes);
    s.els.forEach((e) => {
      if (e.t === 'text') e.paras.forEach((p) => { const t = typeof p === 'string' ? p : p.text; if (t) out.push(t); });
      if (e.t === 'table') e.rows.forEach((r) => r.forEach((c) => { const t = cellText(c); if (t) out.push(t); }));
    });
  });
  return out;
}

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(SCRATCH, { recursive: true });
fs.writeFileSync(path.join(SCRATCH, 'deck-text.json'), JSON.stringify(deckTexts(), null, 0));
renderHtml(path.join(SCRATCH, 'deck.html'));
await renderPptx(path.join(OUT, 'kyc-approval-deck.pptx'));
console.log(`slides ${slides.length}; pptx -> analysis/export/kyc-approval-deck.pptx; html -> ${path.join(SCRATCH, 'deck.html')}`);
