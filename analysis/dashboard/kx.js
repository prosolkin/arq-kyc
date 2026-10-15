/* KYC approval-rate diagnosis: page script. Every figure comes from the datasets built by
   analysis/build_datasets.py; this script formats, filters and draws. The only arithmetic on
   the page is the value model, which multiplies observed counts by preset or reader-entered values. */

const root = document.getElementById('dash-root');
const kxRoot = root.querySelector('.kx');
const MINUS = '−';
const sign = (v) => (v > 0 ? '+' : v < 0 ? MINUS : '');
const FMT = {
  pct: d3.format('.1%'),
  pct2: d3.format('.2%'),
  pct0: d3.format('.0%'),
  int: d3.format(','),
  abs: (v) => d3.format(',')(Math.abs(v)),
  signed: (v) => sign(v) + d3.format(',')(Math.abs(v)),
  usd: (v) => (v < 0 ? MINUS : '') + d3.format('$,.0f')(Math.abs(v)),
  share: (v) => d3.format('.0%')(v),
  num1: d3.format('.1f'),
  text: (v) => String(v),
  pp: (v) => sign(v) + Math.abs(v).toFixed(1) + ' pp',
  pp2: (v) => sign(v) + Math.abs(v).toFixed(2) + ' pp',
  pp_abs: (v) => Math.abs(v).toFixed(1) + ' pp',
  date: (v) => d3.utcFormat('%b %-d')(new Date(v)),
  dateyear: (v) => d3.utcFormat('%b %-d, %Y')(new Date(v)),
};
const NUMERIC = new Set(['pct', 'pct2', 'pct0', 'int', 'abs', 'signed', 'usd', 'share', 'num1', 'pp', 'pp2', 'pp_abs']);
const COUNTRY = { ALL: 'All documents', MEX: 'Mexican documents', ARG: 'Argentine documents' };
const DRIVERS = ['Execution error', 'Fraud signal', 'No document type, no reason code', 'Unsupported or incomplete document', 'Image quality', 'Screen or paper copy', 'Selfie / liveness', 'Face match', 'Other'];
const CLASSES = ['Fraud signal (not adjudicated)', 'Execution error', 'Capture or document issue', 'Unexplained or identity mismatch'];
const CLASS_INFO = {
  'Fraud signal (not adjudicated)': ['The vendor flagged manipulation or a fake document. Some may be fraud, some false positives; none is adjudicated here.', 'Risk & Fraud, via sample adjudication'],
  'Execution error': ['A check did not run (TECHNICAL_ERROR) and the decision was recorded as a rejection.', 'Onboarding platform and Vendor management'],
  'Capture or document issue': ['Unsupported or incomplete document, image quality, a copy instead of the card, or an unclear selfie. Possibly recoverable on retry; not proven.', 'Product, Mobile and Vendor management'],
  'Unexplained or identity mismatch': ['No document type and no reason code, face mismatch, or other. Some are impostors, some may be genuine people.', 'Operations, Product and Vendor management'],
};
const TABS = ['quick', 'drivers', 'plan', 'gain', 'summary', 'measurement', 'incidents', 'hypotheses', 'operating', 'design', 'vendor', 'reference'];
const DETAIL_TABS = new Set(['summary', 'measurement', 'incidents', 'hypotheses', 'operating', 'design', 'vendor', 'reference']);
const PLACE_TAB = { tldr: 'quick', review: 'quick', scenarios: 'gain', value: 'gain', roadmap: 'plan', tracks: 'plan', overview: 'summary', trend: 'summary', declines: 'drivers', customers: 'drivers', causes: 'incidents', mexico: 'drivers', mix: 'drivers', teams: 'operating', impact: 'gain', actions: 'plan', spotted: 'reference', method: 'reference' };
const HYP_LABEL = { h_exec: 'H1', h_liveness: 'H2', h_attack: 'H3', h_ine: 'H4', h_mex_docs: 'H5', h_face: 'H6' };
const STEP_NAME = { usability: 'Usability', classification: 'Document type', image_checks: 'Image checks', extraction: 'Extraction', data_checks: 'Data checks', liveness: 'Liveness', similarity: 'Face match', watchlist_screening: 'Watchlist', decision: 'Final outcome' };
const SIG_LABEL = { fraud: 'Fraud signals', exec_error: 'Execution errors', liveness_quality: 'Liveness quality failures' };
const EVIDENCE_FOR = { fraud_arg: ['fraud_none'], exec_errors: ['sep2_none'], liveness_spike: ['sep1a', 'sep1b', 'sep6'], fraud_mex: ['fraud_none'] };

const colors = () => dash.colors || [];
kxRoot.style.setProperty('--kx-c0', colors()[0] || 'var(--color-fg)');
kxRoot.style.setProperty('--kx-c1', colors()[1] || 'var(--color-fg-muted)');
const driverColor = (d) => { const i = DRIVERS.indexOf(d); return i >= 0 && i < 8 && colors()[i] ? colors()[i] : 'var(--cds-chart-muted)'; };
const classColor = (c) => ({ 'Fraud signal (not adjudicated)': colors()[5], 'Execution error': 'var(--cds-chart-status-critical)', 'Capture or document issue': colors()[0], 'Unexplained or identity mismatch': colors()[2] }[c] || 'var(--cds-chart-muted)');

const rowsOf = (id) => { const d = dash.data(id); return d.status === 'ok' && Array.isArray(d.data) ? d.data : null; };
const parseWhere = (w) => (w || '').split('&').filter(Boolean).map((p) => p.split('=').map(decodeURIComponent));
const pick = (rows, where) => { const c = parseWhere(where); return rows.find((r) => c.every(([k, v]) => String(r[k]) === v)); };
const blank = (v) => v === '' || v === null || v === undefined;
const visible = (n) => n.getClientRects().length > 0;
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
const safeUrl = (u) => (/^https:\/\//.test(u || '') ? u : null);
const chipClass = (v) => 'kx-h kx-h-' + String(v).replace(/\W/g, '');
const kv = (m) => { const k = rowsOf('kpis'); const r = k && pick(k, 'metric=' + m); return r ? Number(r.value) : NaN; };

function settle(box, ids) {
  const st = ids.map((id) => dash.data(id).status);
  box.querySelector(':scope > .kx-failed')?.remove();
  if (st.every((s) => s === 'ok')) { box.classList.remove('dash-skeleton'); return true; }
  if (st.some((s) => ['error', 'connect', 'declined', 'missing'].includes(s))) { box.classList.remove('dash-skeleton'); box.append(el('div', 'kx-failed', 'Failed to load')); }
  else box.classList.add('dash-skeleton');
  return false;
}

function fillMarks() {
  root.querySelectorAll('[data-fill]').forEach((node) => {
    const d = dash.data(node.dataset.source);
    if (d.status !== 'ok') { node.textContent = '—'; return; }
    const row = Array.isArray(d.data) ? pick(d.data, node.dataset.where) : null;
    const raw = row ? row[node.dataset.field] : undefined;
    if (blank(raw)) { node.textContent = '—'; return; }
    const kind = node.dataset.fmt || 'text';
    const v = NUMERIC.has(kind) ? Number(raw) : raw;
    node.textContent = (FMT[kind] || FMT.text)(v);
    if (node.dataset.good) {
      const good = node.dataset.good === 'up' ? v > 0 : v < 0;
      node.classList.toggle('kx-good', v !== 0 && good);
      node.classList.toggle('kx-bad', v !== 0 && !good);
    }
  });
}

/* ---------- helpers for tables, tooltips and charts ---------- */
function cellsFor(tr, row, cols) {
  cols.forEach((c) => {
    const td = el('td', c.cls || null);
    const raw = row[c.field];
    if (c.chip) td.append(el('span', chipClass(raw), raw));
    else if (c.link) {
      const url = safeUrl(row[c.link]);
      if (url) { const a = el('a', null, raw); a.href = url; a.target = '_blank'; a.rel = 'noopener'; td.append(a); } else td.textContent = raw;
    } else if (c.fmt && !blank(raw)) td.textContent = (FMT[c.fmt] || FMT.text)(NUMERIC.has(c.fmt) ? Number(raw) : raw);
    else td.textContent = blank(raw) ? '—' : raw;
    tr.append(td);
  });
}
function fillTable(id, rows, key, cols) {
  const table = document.getElementById(id);
  if (!table) return;
  const body = table.querySelector('tbody');
  body.replaceChildren();
  if (!rows) return;
  rows.forEach((r) => { const tr = el('tr'); tr.dataset.key = r[key]; cellsFor(tr, r, cols); body.append(tr); });
}
function plainTable(box, headers, rows) {
  if (!box) return null;
  box.replaceChildren();
  const t = el('table', 'kx-table');
  const hr = el('tr');
  headers.forEach((h) => hr.append(el('th', h.num ? 'kx-num' : null, h.label)));
  const thead = el('thead'); thead.append(hr);
  const tb = el('tbody');
  rows.forEach((cells) => { const tr = el('tr'); cells.forEach((c, i) => tr.append(el('td', headers[i].num ? 'kx-num' : null, c))); tb.append(tr); });
  t.append(thead, tb);
  box.append(t);
  return t;
}
function measure(svg, texts) {
  const t = svg.append('text').attr('visibility', 'hidden');
  let w = 0;
  texts.forEach((s) => { t.text(s); w = Math.max(w, t.node().getComputedTextLength()); });
  t.remove();
  return w;
}
function tipFor(box) { let tip = box.querySelector(':scope > .kx-tip'); if (!tip) { tip = el('div', 'kx-tip'); tip.hidden = true; tip.setAttribute('role', 'tooltip'); box.append(tip); } return tip; }
function showTip(tip, box, x, y, title, lines) {
  tip.replaceChildren(el('div', 'kx-tip-h', title));
  lines.forEach(([color, label, value]) => {
    const row = el('div', 'kx-tip-row');
    if (color) { const sw = el('i', 'kx-sw'); sw.style.background = color; row.append(sw); }
    row.append(el('span', null, label), el('b', null, value));
    tip.append(row);
  });
  tip.hidden = false;
  const bw = box.clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
  let left = x + 14; if (left + tw > bw) left = x - tw - 14; if (left < 0) left = Math.max(0, Math.min(bw - tw, x - tw / 2));
  let top = y - th - 10; if (top < 0) top = y + 14;
  tip.style.left = left + 'px'; tip.style.top = top + 'px';
}
const hideTip = (tip) => { tip.hidden = true; };
function styleAxis(g) { g.attr('font-size', null).attr('font-family', null); g.select('.domain').style('stroke', 'var(--cds-chart-axis)'); g.selectAll('.tick line').style('stroke', 'var(--cds-chart-grid)'); }
function freshSvg(box, height) {
  d3.select(box).select('svg').remove();
  const w = Math.max(240, box.clientWidth);
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${w} ${height}`).attr('height', height).attr('aria-hidden', 'true');
  return { svg, w };
}
function chartReady(box, ids) { if (!box) return false; if (!settle(box, ids)) { d3.select(box).select('svg').remove(); return false; } return visible(box); }
const country = () => dash.params().country || 'ALL';
const scenario = () => dash.params().scenario || 'Central';

/* ---------- Summary ---------- */
function drawTrend() {
  const box = document.getElementById('trend-chart');
  const tbl = document.getElementById('trend-table');
  if (!settle(box, ['daily', 'incidents', 'kpis'])) return;
  const c = country();
  const rows = rowsOf('daily').filter((r) => r.country === c).map((r) => ({ day: r.date, date: new Date(r.date), n: +r.n, rate: +r.approval_rate, excl: +r.approval_excl_selected, sel: +r.selected }));
  plainTable(tbl, [{ label: 'Date' }, { label: 'Decisions', num: true }, { label: 'Approval rate', num: true }, { label: 'Selected incident failures', num: true }],
    rows.map((r) => [FMT.dateyear(r.day), FMT.int(r.n), FMT.pct(r.rate), r.sel ? FMT.int(r.sel) : '—']));
  if (!visible(box)) return;
  const exclDays = !!document.getElementById('trend-excl-days')?.checked;
  const splitDate = new Date(pick(rowsOf('kpis'), 'metric=split_date').value);
  const incDay = new Set(rowsOf('daily').filter((r) => r.incident_day === '1').map((r) => r.date));
  const kept = exclDays ? rows.filter((r) => !incDay.has(r.day)) : rows;
  const avg = (rs) => d3.sum(rs, (r) => r.n * r.rate) / d3.sum(rs, (r) => r.n);
  const priorAvg = avg(kept.filter((r) => r.date < splitDate)), recentAvg = avg(kept.filter((r) => r.date >= splitDate));
  const incidents = rowsOf('incidents').filter((i) => i.country === 'ALL' || c === 'ALL' || i.country === c);
  const H = 300;
  const { svg, w } = freshSvg(box, H);
  const lo = Math.max(0, Math.floor((d3.min(rows, (r) => Math.min(r.rate, r.excl)) - 0.03) * 20) / 20);
  const yTicks = d3.scaleLinear([lo, 1], [0, 1]).ticks(5);
  const m = { t: 44, r: 12, b: 26, l: measure(svg, yTicks.map(FMT.pct0)) + 10 };
  const x = d3.scaleUtc(d3.extent(rows, (r) => r.date), [m.l, w - m.r]);
  const y = d3.scaleLinear([lo, 1], [H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues(yTicks).tickFormat(FMT.pct0).tickSize(-(w - m.l - m.r))).call(styleAxis).call((g) => g.select('.domain').remove());
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((w - m.l - m.r) / 80))).tickFormat(d3.utcFormat('%b %-d')).tickSizeOuter(0)).call(styleAxis).call((g) => g.selectAll('.tick line').remove());
  if (exclDays) rows.filter((r) => incDay.has(r.day)).forEach((r) => svg.append('rect').attr('x', x(r.date) - (w - m.l - m.r) / rows.length / 2).attr('y', m.t - 4).attr('width', (w - m.l - m.r) / rows.length).attr('height', H - m.t - m.b + 4).style('fill', 'var(--cds-chart-muted)').attr('fill-opacity', 0.25));
  svg.append('line').attr('x1', x(rows[0].date)).attr('x2', x(splitDate)).attr('y1', y(priorAvg)).attr('y2', y(priorAvg)).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');
  svg.append('text').attr('x', x(rows[0].date) + 2).attr('y', y(priorAvg) + 14).text('Prior-period rate ' + FMT.pct(priorAvg));
  svg.append('line').attr('x1', x(splitDate)).attr('x2', x(rows[rows.length - 1].date)).attr('y1', y(recentAvg)).attr('y2', y(recentAvg)).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');
  svg.append('text').attr('x', x(rows[rows.length - 1].date) - 2).attr('y', y(recentAvg) + 14).attr('text-anchor', 'end').text((exclDays ? 'Recent rate without incident days ' : 'Recent-period rate ') + FMT.pct(recentAvg));
  svg.append('line').attr('x1', x(splitDate)).attr('x2', x(splitDate)).attr('y1', m.t - 6).attr('y2', H - m.b).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '2 3');
  svg.append('text').attr('x', x(splitDate) + 4).attr('y', H - m.b - 6).text('Recent period');
  const placed = [];
  incidents.slice().sort((a, b) => +a.order - +b.order).forEach((inc) => {
    const xs = inc.days.split(',').map((d) => x(new Date(d)));
    xs.forEach((cx) => svg.append('line').attr('x1', cx).attr('x2', cx).attr('y1', m.t - 4).attr('y2', H - m.b).style('stroke', 'var(--cds-chart-status-critical)').attr('stroke-opacity', 0.3));
    const bx = xs[0];
    let row = 0;
    while (placed.some((p) => p.row === row && Math.abs(p.x - bx) < 18)) row += 1;
    placed.push({ x: bx, row });
    const cy = 10 + row * 18;
    svg.append('circle').attr('cx', bx).attr('cy', cy).attr('r', 7.5).style('fill', 'var(--color-panel)').style('stroke', 'var(--cds-chart-status-critical)').attr('stroke-width', 1.5);
    svg.append('text').attr('x', bx).attr('y', cy).attr('dy', '0.35em').attr('text-anchor', 'middle').style('fill', 'var(--cds-chart-status-critical)').style('font-weight', 600).text(inc.order);
  });
  const line = (k) => d3.line().x((r) => x(r.date)).y((r) => y(r[k]));
  svg.append('path').datum(rows).style('fill', 'none').style('stroke', 'var(--cds-chart-muted)').attr('stroke-width', 2).attr('stroke-dasharray', '5 4').attr('d', line('excl'));
  svg.append('path').datum(kept).style('fill', 'none').style('stroke', colors()[0]).attr('stroke-width', 2).attr('stroke-linejoin', 'round').attr('stroke-linecap', 'round').attr('d', exclDays ? line('rate').defined((r) => !incDay.has(r.day)) : line('rate'));
  const dot = svg.append('circle').attr('r', 4).style('fill', colors()[0]).attr('visibility', 'hidden');
  const rule = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).style('stroke', 'var(--cds-chart-axis)').attr('visibility', 'hidden');
  const tip = tipFor(box);
  const bis = d3.bisector((r) => r.date).center;
  svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', w - m.l - m.r).attr('height', H - m.t - m.b).style('fill', 'transparent')
    .on('pointermove', (ev) => {
      const r = rows[bis(rows, x.invert(d3.pointer(ev)[0]))];
      const cx = x(r.date), scale = box.clientWidth / w;
      rule.attr('x1', cx).attr('x2', cx).attr('visibility', 'visible');
      dot.attr('cx', cx).attr('cy', y(r.rate)).attr('visibility', 'visible');
      const lines = [[colors()[0], 'Approval rate', FMT.pct(r.rate)], [null, 'Decisions', FMT.int(r.n)]];
      if (r.sel) lines.push([null, 'Selected incident failures', FMT.int(r.sel)], ['var(--cds-chart-muted)', 'Without them (descriptive)', FMT.pct(r.excl)]);
      showTip(tip, box, cx * scale, y(r.rate) * scale, d3.utcFormat('%a %b %-d, %Y')(r.date) + ' · ' + COUNTRY[c], lines);
    })
    .on('pointerleave', () => { hideTip(tip); dot.attr('visibility', 'hidden'); rule.attr('visibility', 'hidden'); });
}

function drawBridge() {
  const box = document.getElementById('bridge-chart');
  if (!settle(box, ['bridge'])) return;
  const rows = rowsOf('bridge').map((r) => ({ driver: r.driver, effect: +r.effect_pp, inc: +r.incident_pp, rest: +r.rest_pp, a: +r.share_a, b: +r.share_b }));
  plainTable(document.getElementById('bridge-table'), [{ label: 'Primary reason' }, { label: 'Share, prior', num: true }, { label: 'Share, recent', num: true }, { label: 'Effect on approval', num: true }, { label: 'Above baseline in windows', num: true }],
    rows.map((r) => [r.driver, FMT.pct2(r.a), FMT.pct2(r.b), FMT.pp2(r.effect), FMT.pp2(r.inc)]));
  if (!visible(box)) return;
  const rowH = 28, m = { t: 8, r: 12, b: 24 };
  const H = m.t + m.b + rows.length * rowH;
  const { svg, w } = freshSvg(box, H);
  m.l = measure(svg, rows.map((r) => r.driver)) + 12;
  const valW = measure(svg, rows.map((r) => FMT.pp(r.effect))) + 8;
  const lo = Math.min(0, d3.min(rows, (r) => Math.min(r.effect, r.inc))), hi = Math.max(0, d3.max(rows, (r) => r.effect));
  const x = d3.scaleLinear([lo, hi], [m.l + valW, w - m.r - valW]);
  const y = d3.scaleBand(rows.map((r) => r.driver), [m.t, H - m.b]).padding(0.3);
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(x.ticks(Math.max(2, Math.floor((w - m.l) / 90)))).tickFormat((v) => sign(v) + Math.abs(v) + ' pp').tickSize(-(H - m.t - m.b))).call(styleAxis).call((g) => g.select('.domain').remove());
  svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', m.t).attr('y2', H - m.b).style('stroke', 'var(--cds-chart-axis)');
  const tip = tipFor(box);
  rows.forEach((r) => {
    const g = svg.append('g'), yy = y(r.driver), bh = y.bandwidth();
    g.append('text').attr('x', m.l - 10).attr('y', yy + bh / 2).attr('dy', '0.35em').attr('text-anchor', 'end').style('fill', 'var(--color-fg)').text(r.driver);
    const seg = (from, to, fill) => { if (Math.abs(to - from) < 1e-9) return; g.append('rect').attr('x', x(Math.min(from, to))).attr('width', Math.max(1, Math.abs(x(to) - x(from)))).attr('y', yy).attr('height', bh).attr('rx', 3).style('fill', fill); };
    seg(0, r.inc, 'var(--cds-chart-status-critical)');
    const start = Math.sign(r.rest) === Math.sign(r.inc) ? r.inc : 0;
    seg(start, start + r.rest, colors()[0]);
    const end = r.effect < 0 ? Math.min(r.effect, r.inc) : Math.max(r.effect, 0);
    g.append('text').attr('x', r.effect < 0 ? x(end) - 4 : x(end) + 4).attr('y', yy + bh / 2).attr('dy', '0.35em').attr('text-anchor', r.effect < 0 ? 'end' : 'start').style('fill', 'var(--color-fg)').style('font-weight', 600).text(FMT.pp(r.effect));
    g.append('rect').attr('x', 0).attr('y', yy - (y.step() - bh) / 2).attr('width', w).attr('height', y.step()).style('fill', 'transparent')
      .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, svg.node()); const s = box.clientWidth / w; showTip(tip, box, px * s, py * s, r.driver, [[null, 'Share, prior period', FMT.pct2(r.a)], [null, 'Share, recent period', FMT.pct2(r.b)], [null, 'Effect on approval', FMT.pp2(r.effect)], ['var(--cds-chart-status-critical)', 'Above baseline in windows', FMT.pp2(r.inc)], [colors()[0], 'Everything else', FMT.pp2(r.rest)]]); })
      .on('pointerleave', () => hideTip(tip));
  });
}

/* ---------- Drivers ---------- */
function drawDeclineChart() {
  const box = document.getElementById('decline-chart');
  document.getElementById('decline-legend').replaceChildren(...CLASSES.map((c) => { const s = el('span'); const sw = el('i', 'kx-sw'); sw.style.background = classColor(c); s.append(sw, document.createTextNode(c)); return s; }));
  if (!settle(box, ['declines', 'kpis'])) return;
  const groups = rowsOf('declines').filter((r) => r.level === 'group').sort((a, b) => CLASSES.indexOf(a.class) - CLASSES.indexOf(b.class));
  plainTable(document.getElementById('decline-table'), [{ label: 'Group' }, { label: 'Class' }, { label: 'Prior', num: true }, { label: 'Recent', num: true }, { label: 'Of decisions, prior', num: true }, { label: 'Of decisions, recent', num: true }, { label: 'Of unsuccessful, recent', num: true }],
    groups.map((g) => [g.name, g.class, FMT.int(+g.n_a), FMT.int(+g.n_b), FMT.pct2(+g.share_a), FMT.pct2(+g.share_b), FMT.pct(+g.of_unsuccessful_b)]));
  if (!visible(box)) return;
  const bars = [{ key: 'a', label: 'Prior period', total: kv('decline_a') }, { key: 'b', label: 'Recent period', total: kv('decline_b') }];
  const H = 132;
  const { svg, w } = freshSvg(box, H);
  const m = { t: 6, r: 8, b: 24, l: measure(svg, bars.map((b) => b.label)) + 12 };
  const endW = measure(svg, bars.map((b) => FMT.pct(b.total))) + 10;
  const x = d3.scaleLinear([0, d3.max(bars, (b) => b.total)], [m.l, w - m.r - endW]);
  const y = d3.scaleBand(bars.map((b) => b.key), [m.t, H - m.b]).padding(0.35);
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((w - m.l) / 80))).tickFormat(FMT.pct0).tickSize(-(H - m.t - m.b))).call(styleAxis).call((g) => g.select('.domain').remove());
  const tip = tipFor(box);
  bars.forEach((b) => {
    const yy = y(b.key), bh = y.bandwidth();
    svg.append('text').attr('x', m.l - 10).attr('y', yy + bh / 2).attr('dy', '0.35em').attr('text-anchor', 'end').style('fill', 'var(--color-fg)').text(b.label);
    let acc = 0;
    groups.forEach((g) => {
      const v = Number(g['share_' + b.key]); if (!v) return;
      const x0 = x(acc), x1 = x(acc + v); acc += v;
      svg.append('rect').attr('x', x0).attr('width', Math.max(0.5, x1 - x0)).attr('y', yy).attr('height', bh).style('fill', classColor(g.class)).style('stroke', 'var(--color-panel)').attr('stroke-width', 1)
        .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, svg.node()); const s = box.clientWidth / w; showTip(tip, box, px * s, py * s, g.name + ' · ' + b.label, [[classColor(g.class), g.class, ''], [null, 'Share of all decisions', FMT.pct2(v)], [null, 'Share of unsuccessful', FMT.pct(Number(g['of_unsuccessful_' + b.key]))], [null, 'Decisions', FMT.int(Number(g['n_' + b.key]))]]); })
        .on('pointerleave', () => hideTip(tip));
    });
    svg.append('text').attr('x', x(b.total) + 6).attr('y', yy + bh / 2).attr('dy', '0.35em').style('fill', 'var(--color-fg)').style('font-weight', 600).text(FMT.pct(b.total));
  });
}

function drawDeclineCards() {
  const box = document.getElementById('decline-classes');
  box.replaceChildren();
  const rows = rowsOf('declines'); if (!rows) return;
  rows.filter((r) => r.level === 'class').sort((a, b) => CLASSES.indexOf(a.name) - CLASSES.indexOf(b.name)).forEach((r) => {
    const card = el('div', 'kx-card kx-tile');
    const head = el('span', 'kx-label'); const sw = el('i', 'kx-sw'); sw.style.background = classColor(r.name); head.append(sw, document.createTextNode(' ' + r.name));
    const [what, who] = CLASS_INFO[r.name] || ['', ''];
    const dl = el('dl', 'kx-kv');
    [['Of decisions, prior → recent', FMT.pct2(+r.share_a) + ' → ' + FMT.pct2(+r.share_b)], ['Of unsuccessful, prior → recent', FMT.pct(+r.of_unsuccessful_a) + ' → ' + FMT.pct(+r.of_unsuccessful_b)], ['Decisions, recent', FMT.int(+r.n_b)]]
      .forEach(([k, v]) => dl.append(el('dt', null, k), el('dd', null, v)));
    card.append(head, el('span', 'kx-mid', FMT.pct2(+r.share_b)), el('span', 'kx-sub', 'of recent decisions'), dl, el('p', 'kx-note', what), el('p', 'kx-note', 'Could act: ' + who));
    box.append(card);
  });
}

function drawMexBars() {
  const box = document.getElementById('mex-bars');
  box.querySelectorAll(':scope > .kx-bar-row').forEach((n) => n.remove());
  if (!settle(box, ['mex_no_doctype'])) return;
  const rows = rowsOf('mex_no_doctype').filter((r) => +r.n_a + +r.n_b > 0);
  const max = d3.max(rows, (r) => Math.max(+r.share_a, +r.share_b));
  rows.forEach((r) => {
    const row = el('div', 'kx-bar-row');
    const track = el('div', 'kx-bar-track'); track.style.flexDirection = 'column'; track.style.height = '1rem';
    [['share_a', 0.45], ['share_b', 1]].forEach(([f, op]) => { const b = el('div', 'kx-bar-fill'); b.style.width = (100 * +r[f] / max) + '%'; b.style.height = '50%'; b.style.background = r.group === 'No reason code' ? 'var(--cds-chart-status-critical)' : colors()[0]; b.style.opacity = op; track.append(b); });
    row.append(el('span', 'kx-bar-label', r.group), track, el('b', null, FMT.pct2(+r.share_a) + ' → ' + FMT.pct2(+r.share_b)));
    box.append(row);
  });
}

function drawUnclassified() {
  const box = document.getElementById('unc-chart');
  if (!chartReady(box, ['docs_weekly'])) return;
  const rows = rowsOf('docs_weekly').filter((r) => r.country === 'MEX' && r.doc === 'UNCLASSIFIED').map((r) => ({ week: r.week, share: +r.share, n: +r.n }));
  const H = 260;
  const { svg, w } = freshSvg(box, H);
  const y0 = d3.scaleLinear([0, d3.max(rows, (r) => r.share) * 1.2], [0, 1]).nice();
  const yTicks = y0.ticks(4);
  const m = { t: 18, r: 16, b: 26, l: measure(svg, yTicks.map(FMT.pct0)) + 10 };
  const x = d3.scalePoint(rows.map((r) => r.week), [m.l + 8, w - m.r - 8]);
  const y = d3.scaleLinear(y0.domain(), [H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues(yTicks).tickFormat(FMT.pct0).tickSize(-(w - m.l - m.r))).call(styleAxis).call((g) => g.select('.domain').remove());
  const every = x.step() < 48 ? 2 : 1;
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(rows.map((r) => r.week).filter((_, i) => i % every === 0)).tickFormat(FMT.date).tickSizeOuter(0)).call(styleAxis).call((g) => g.selectAll('.tick line').remove());
  svg.append('path').datum(rows).style('fill', 'none').style('stroke', colors()[0]).attr('stroke-width', 2).attr('d', d3.line().x((r) => x(r.week)).y((r) => y(r.share)));
  svg.selectAll('circle.p').data(rows).join('circle').attr('class', 'p').attr('cx', (r) => x(r.week)).attr('cy', (r) => y(r.share)).attr('r', 3).style('fill', colors()[0]);
  const last = rows[rows.length - 1];
  svg.append('text').attr('x', x(last.week)).attr('y', y(last.share) - 9).attr('text-anchor', 'end').style('fill', 'var(--color-fg)').style('font-weight', 600).text(FMT.pct(last.share));
  const tip = tipFor(box);
  svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', w - m.l - m.r).attr('height', H - m.t - m.b).style('fill', 'transparent')
    .on('pointermove', (ev) => { const px = d3.pointer(ev)[0]; const r = rows.reduce((b, q) => (Math.abs(x(q.week) - px) < Math.abs(x(b.week) - px) ? q : b), rows[0]); const s = box.clientWidth / w; showTip(tip, box, x(r.week) * s, y(r.share) * s, 'Week of ' + FMT.dateyear(r.week), [[null, 'No document type', FMT.pct(r.share)], [null, 'Decisions', FMT.int(r.n)]]); })
    .on('pointerleave', () => hideTip(tip));
}

function drawProcess() {
  const box = document.getElementById('process');
  box.querySelectorAll(':scope > .kx-lane').forEach((n) => n.remove());
  if (!settle(box, ['process_steps'])) return;
  const rows = rowsOf('process_steps').sort((a, b) => +a.order - +b.order);
  const hot = new Set(rows.filter((r) => r.step !== 'decision').sort((a, b) => +b.decided_here - +a.decided_here).slice(0, 3).map((r) => r.step));
  [['ID document', rows.filter((r) => r.track === 'Document')], ['Selfie, in parallel', rows.filter((r) => r.track === 'Selfie')], ['Then', rows.filter((r) => r.track === 'Screening' || r.track === 'Decision')]].forEach(([name, steps]) => {
    const lane = el('div', 'kx-lane'); lane.append(el('div', 'kx-lane-name', name));
    const row = el('div', 'kx-lane-row');
    steps.forEach((s, i) => {
      if (i > 0) row.append(el('span', 'kx-arrow', '→'));
      const card = el('div', 'kx-step' + (hot.has(s.step) ? ' kx-step-hot' : ''));
      card.append(el('b', null, STEP_NAME[s.step] || s.step), el('span', 'kx-step-q', s.question));
      const dl = el('dl', 'kx-kv');
      const add = (k, v) => dl.append(el('dt', null, k), el('dd', null, v));
      if (s.step === 'decision') { add('Approved', FMT.int(+s.passed)); add('Warning', FMT.int(+s.warning)); add('Rejected', FMT.int(+s.rejected)); }
      else { add('Checked', FMT.int(+s.reached)); add('Not run or not recorded', FMT.int(+s.not_executed)); add('Declined here', FMT.int(+s.decided_here)); }
      card.append(dl);
      if (+s.decided_here && s.step !== 'decision') { const t = el('span', 'kx-step-q'); t.append(document.createTextNode('Most often: '), el('span', 'kx-code', s.top_reason)); card.append(t); }
      row.append(card);
    });
    lane.append(row); box.append(lane);
  });
}

function drawMix() {
  const box = document.getElementById('mix-chart');
  document.getElementById('mix-legend').replaceChildren(...DRIVERS.map((k) => { const s = el('span'); const sw = el('i', 'kx-sw'); sw.style.background = driverColor(k); s.append(sw, document.createTextNode(k)); return s; }));
  if (!chartReady(box, ['weekly_drivers'])) return;
  const c = country();
  const raw = rowsOf('weekly_drivers').filter((r) => r.country === c);
  const weeks = [...new Set(raw.map((r) => r.week))].sort();
  const table = weeks.map((wk) => { const o = { week: wk }; raw.filter((r) => r.week === wk).forEach((r) => { o[r.driver] = +r.share; o.total = +r.total; o.days = +r.days; }); return o; });
  const stack = d3.stack().keys(DRIVERS).value((d, k) => d[k] || 0)(table);
  const H = 300;
  const { svg, w } = freshSvg(box, H);
  const top = d3.max(table, (d) => DRIVERS.reduce((s, k) => s + (d[k] || 0), 0));
  const y0 = d3.scaleLinear([0, top * 1.08], [0, 1]).nice();
  const yTicks = y0.ticks(5);
  const m = { t: 10, r: 8, b: 26, l: measure(svg, yTicks.map(FMT.pct0)) + 10 };
  const x = d3.scaleBand(weeks, [m.l, w - m.r]).padding(0.28);
  const y = d3.scaleLinear(y0.domain(), [H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues(yTicks).tickFormat(FMT.pct0).tickSize(-(w - m.l - m.r))).call(styleAxis).call((g) => g.select('.domain').remove());
  const every = x.step() < 46 ? 2 : 1;
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(weeks.filter((_, i) => i % every === 0)).tickFormat(FMT.date).tickSizeOuter(0)).call(styleAxis).call((g) => g.selectAll('.tick line').remove());
  const bw = Math.min(32, x.bandwidth()), off = (x.bandwidth() - bw) / 2;
  svg.append('g').selectAll('g').data(stack).join('g').style('fill', (s) => driverColor(s.key)).selectAll('rect').data((s) => s).join('rect')
    .attr('x', (d) => x(d.data.week) + off).attr('width', bw).attr('y', (d) => y(d[1])).attr('height', (d) => Math.max(0, y(d[0]) - y(d[1])));
  const tip = tipFor(box);
  svg.append('g').selectAll('rect').data(table).join('rect').attr('x', (d) => x(d.week)).attr('width', x.bandwidth()).attr('y', m.t).attr('height', H - m.t - m.b).style('fill', 'transparent')
    .on('pointermove', (ev, d) => { const [px, py] = d3.pointer(ev, svg.node()); const s = box.clientWidth / w; const lines = DRIVERS.filter((k) => d[k] > 0).slice().reverse().map((k) => [driverColor(k), k, FMT.pct2(d[k])]); lines.push([null, 'All not approved', FMT.pct(DRIVERS.reduce((t, k) => t + (d[k] || 0), 0))], [null, 'Decisions', FMT.int(d.total)]); showTip(tip, box, px * s, py * s, 'Week of ' + FMT.dateyear(d.week) + (d.days < 7 ? ' (partial)' : '') + ' · ' + COUNTRY[c], lines); })
    .on('pointerleave', () => hideTip(tip));
}

const reasonSort = { key: 'n_b', dir: -1 };
function drawReasons() {
  const table = document.getElementById('reasons-table');
  const rows = rowsOf('reasons'); if (!rows) return;
  const q = document.getElementById('reasons-search').value.trim().toLowerCase();
  const numeric = new Set(['n_a', 'n_b', 'change_pp']);
  const list = rows.filter((r) => r.country === country()).filter((r) => !q || [r.reason, r.step, r.driver].join(' ').toLowerCase().includes(q))
    .sort((a, b) => { const k = reasonSort.key; const av = numeric.has(k) ? +a[k] : a[k], bv = numeric.has(k) ? +b[k] : b[k]; return (av < bv ? -1 : av > bv ? 1 : 0) * reasonSort.dir; });
  table.querySelectorAll('th').forEach((th) => { const b = th.querySelector('button'); if (b) th.setAttribute('aria-sort', b.dataset.sort === reasonSort.key ? (reasonSort.dir > 0 ? 'ascending' : 'descending') : 'none'); });
  fillTable('reasons-table', list, 'id', [{ field: 'reason', cls: 'kx-code' }, { field: 'step', cls: 'kx-hide-narrow' }, { field: 'driver', cls: 'kx-hide-narrow' }, { field: 'n_a', fmt: 'int', cls: 'kx-num' }, { field: 'n_b', fmt: 'int', cls: 'kx-num' }, { field: 'change_pp', fmt: 'pp2', cls: 'kx-num' }]);
}

function drawAge() {
  const box = document.getElementById('age-chart');
  if (!chartReady(box, ['profile'])) return;
  const rows = rowsOf('profile').filter((r) => r.country !== 'ALL');
  const bands = [...new Set(rows.map((r) => r.age_band))];
  const H = 260;
  const { svg, w } = freshSvg(box, H);
  const y0 = d3.scaleLinear([0, d3.max(rows, (r) => +r.share) * 1.1], [0, 1]).nice();
  const yTicks = y0.ticks(4);
  const m = { t: 10, r: 8, b: 26, l: measure(svg, yTicks.map(FMT.pct0)) + 10 };
  const x = d3.scaleBand(bands, [m.l, w - m.r]).padding(0.22), xs = d3.scaleBand(['MEX', 'ARG'], [0, x.bandwidth()]).padding(0.12);
  const y = d3.scaleLinear(y0.domain(), [H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues(yTicks).tickFormat(FMT.pct0).tickSize(-(w - m.l - m.r))).call(styleAxis).call((g) => g.select('.domain').remove());
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickSizeOuter(0)).call(styleAxis).call((g) => g.selectAll('.tick line').remove());
  const fill = { MEX: colors()[0], ARG: colors()[1] };
  const tip = tipFor(box);
  rows.forEach((r) => {
    const bw = Math.min(32, xs.bandwidth()), bx = x(r.age_band) + xs(r.country) + (xs.bandwidth() - bw) / 2;
    svg.append('rect').attr('x', bx).attr('width', bw).attr('y', y(+r.share)).attr('height', Math.max(0, H - m.b - y(+r.share))).attr('rx', 3).style('fill', fill[r.country])
      .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, svg.node()); const s = box.clientWidth / w; showTip(tip, box, px * s, py * s, COUNTRY[r.country] + ' · ' + r.age_band, [[fill[r.country], 'Share of decisions', FMT.pct(+r.share)], [null, 'Approval rate', blank(r.approval_rate) ? '—' : FMT.pct(+r.approval_rate)], [null, 'Decisions', FMT.int(+r.n)]]); })
      .on('pointerleave', () => hideTip(tip));
  });
}

function drawDocMix() {
  const box = document.getElementById('docmix');
  box.querySelectorAll(':scope > .kx-bar-row, :scope > .kx-bar-group').forEach((n) => n.remove());
  if (!settle(box, ['docs'])) return;
  const rows = rowsOf('docs'); const max = d3.max(rows, (r) => +r.share);
  ['MEX', 'ARG'].forEach((c, ci) => {
    box.append(el('div', 'kx-bar-group', COUNTRY[c]));
    rows.filter((r) => r.country === c && +r.share >= 0.005).sort((a, b) => +b.share - +a.share).forEach((r) => {
      const row = el('div', 'kx-bar-row'); const track = el('div', 'kx-bar-track'); const f = el('div', 'kx-bar-fill');
      f.style.width = (100 * +r.share / max) + '%'; f.style.background = r.doc === 'UNCLASSIFIED' ? 'var(--cds-chart-status-critical)' : colors()[ci]; track.append(f);
      row.append(el('span', 'kx-bar-label', r.label), track, el('b', null, FMT.pct(+r.share) + ' · approved ' + FMT.pct(+r.approval_rate)));
      box.append(row);
    });
  });
}

/* ---------- Incidents ---------- */
function drawIncidentCards() {
  const box = document.getElementById('incident-cards');
  box.replaceChildren();
  const inc = rowsOf('incidents'), daily = rowsOf('daily'), ev = rowsOf('vendor_evidence');
  if (!inc || !daily || !ev) return;
  inc.slice().sort((a, b) => +a.order - +b.order).forEach((i) => {
    const card = el('article', 'kx-card kx-inc'); card.id = 'inc-' + i.id;
    const top = el('div', 'kx-inc-top'); top.append(el('span', 'kx-badge', i.order), el('h3', null, i.title));
    const chips = el('div', 'kx-chips'); [i.type, i.when + ', 2023', COUNTRY[i.country]].forEach((t) => chips.append(el('span', 'kx-chip', t)));
    const spark = el('div', 'kx-chart-sm'); spark.id = 'spark-' + i.id; spark.setAttribute('role', 'img'); spark.setAttribute('aria-label', SIG_LABEL[i.signature] + ' per day, ' + COUNTRY[i.country]);
    const dl = el('dl', 'kx-kv');
    const add = (k, v) => dl.append(el('dt', null, k), el('dd', null, v));
    add('Observed in window', FMT.int(+i.observed)); add('Expected at prior-period rate', FMT.num1(+i.expected)); add('Other unsuccessful in window (not attributed)', FMT.int(+i.ordinary_unsuccessful));
    if (i.id === 'fraud_arg' || i.id === 'fraud_mex') add('Decisions vs typical', FMT.int(+i.volume) + ' vs ' + FMT.int(+i.baseline_volume));
    if (i.signature === 'fraud') { add('Liveness passed', FMT.int(+i.liveness_passed)); add('Face match passed', FMT.int(+i.face_passed)); }
    if (i.id === 'exec_errors') { add('Liveness passed', FMT.int(+i.liveness_passed)); add('Screening passed', FMT.int(+i.screening_passed)); add('Document type returned', FMT.int(+i.doc_type_present)); }
    if (i.id === 'liveness_spike') add('Also had another failed check', FMT.int(+i.other_failing));
    const text = {
      fraud_arg: 'Argentine volume was about double a typical day. Manipulation signals on extra traffic suggest an attack. A pass on liveness and face match does not prove a genuine person with an altered ID. Adjudication is needed.',
      exec_errors: 'Usability returned TECHNICAL_ERROR, so document checks and face match never ran, but liveness ran and passed. The vendor status page lists no incident for these days, so the fault may be in ARQ’s integration.',
      liveness_spike: 'The vendor’s status page documents liveness incidents on both days, on its US data centre. That supports, but does not confirm, a vendor cause for ARQ.',
      fraud_mex: 'Signals on INE cards without extra volume. This could be quieter fraud, a vendor rule or model change, or a new card version. No vendor incident is listed.',
    }[i.id];
    const evidence = el('p', 'kx-note', 'Vendor status page: ' + EVIDENCE_FOR[i.id].map((k) => { const e = ev.find((x) => x.id === k); return e ? (e.window_utc ? e.date + ' ' + e.window_utc + ' UTC' : e.description) : ''; }).join('; '));
    card.append(top, chips, el('span', 'kx-big', FMT.int(+i.excess)), el('span', 'kx-label', 'above baseline · ' + FMT.pct(+i.share_of_unsuccessful_b) + ' of recent unsuccessful'), spark, dl, el('p', null, text), evidence);
    box.append(card);
  });
}
function drawSpark(i) {
  const box = document.getElementById('spark-' + i.id);
  if (!box || !visible(box)) return;
  const days = new Set(i.days.split(','));
  const rows = rowsOf('daily').filter((r) => r.country === i.country).map((r) => ({ day: r.date, v: +r[i.signature], n: +r.n }));
  const H = 72;
  const { svg, w } = freshSvg(box, H);
  const m = { t: 4, r: 2, b: 18, l: 2 };
  const x = d3.scaleBand(rows.map((r) => r.day), [m.l, w - m.r]).padding(0.15);
  const y = d3.scaleLinear([0, d3.max(rows, (r) => r.v) || 1], [H - m.b, m.t]);
  svg.append('line').attr('x1', m.l).attr('x2', w - m.r).attr('y1', H - m.b + 0.5).attr('y2', H - m.b + 0.5).style('stroke', 'var(--cds-chart-axis)');
  svg.selectAll('rect.b').data(rows).join('rect').attr('class', 'b').attr('x', (r) => x(r.day)).attr('width', x.bandwidth()).attr('y', (r) => y(r.v)).attr('height', (r) => Math.max(r.v ? 1 : 0, H - m.b - y(r.v))).style('fill', (r) => (days.has(r.day) ? 'var(--cds-chart-status-critical)' : 'var(--cds-chart-muted)'));
  svg.append('text').attr('x', m.l).attr('y', H - 4).text(FMT.date(rows[0].day));
  svg.append('text').attr('x', w - m.r).attr('y', H - 4).attr('text-anchor', 'end').text(FMT.date(rows[rows.length - 1].day));
  const tip = tipFor(box);
  svg.append('rect').attr('x', m.l).attr('y', 0).attr('width', w - m.l - m.r).attr('height', H - m.b).style('fill', 'transparent')
    .on('pointermove', (ev) => { const r = rows[Math.max(0, Math.min(rows.length - 1, Math.floor((d3.pointer(ev)[0] - m.l) / x.step())))]; const s = box.clientWidth / w; showTip(tip, box, (x(r.day) + x.bandwidth() / 2) * s, y(r.v) * s, FMT.dateyear(r.day), [[null, SIG_LABEL[i.signature], FMT.int(r.v)], [null, 'Decisions', FMT.int(r.n)]]); })
    .on('pointerleave', () => hideTip(tip));
}

/* ---------- Hypotheses & tests ---------- */
function drawHypotheses() {
  const box = document.getElementById('hyp-cards'); box.replaceChildren();
  const rows = rowsOf('hypotheses'); if (!rows) return;
  rows.forEach((h) => {
    const card = el('article', 'kx-card'); card.id = 'hyp-' + h.id;
    const head = el('div', 'kx-cardhead'); head.append(el('h3', null, HYP_LABEL[h.id] + ' · ' + h.hypothesis), el('span', 'kx-chip', 'Hypothesis'));
    const dl = el('dl', 'kx-gloss');
    [['Evidence', h.evidence], ['Alternatives', h.alternatives], ['Still needed', h.missing], ['Next step', h.next], ['Decision it enables', h.decision]].forEach(([k, v]) => dl.append(el('dt', null, k), el('dd', null, v)));
    card.append(head, dl); box.append(card);
  });
}
function drawExperiments() {
  const box = document.getElementById('exp-cards'); box.replaceChildren();
  const rows = rowsOf('experiments'); if (!rows) return;
  rows.forEach((e) => {
    const card = el('article', 'kx-card');
    const head = el('div', 'kx-cardhead'); head.append(el('h3', null, e.hypothesis), el('span', 'kx-chip', e.kind));
    const dl = el('dl', 'kx-gloss');
    [['Population', e.population], ['Assignment unit', e.unit], ['Primary outcome', e.primary], ['Observation window', e.window], ['Minimum meaningful effect', e.mde], ['Sample and duration', e.sample], ['Guardrails', e.guardrails], ['Launch, expansion, rollback', e.rules]].forEach(([k, v]) => dl.append(el('dt', null, k), el('dd', null, v)));
    card.append(head, dl); box.append(card);
  });
}

/* ---------- Plan & value ---------- */
function deptName(id) { const d = rowsOf('departments'); const r = d && d.find((x) => x.id === id); return r ? r.name : id; }
function drawRoadmap() {
  const box = document.getElementById('roadmap');
  const open = new Set([...box.querySelectorAll('details[open]')].map((d) => d.dataset.id));
  box.replaceChildren();
  const acts = rowsOf('actions'), phases = rowsOf('phases'); if (!acts || !phases) return;
  phases.forEach((p) => {
    const sec = el('div', 'kx-phase'); sec.append(el('h3', null, p.label));
    acts.filter((a) => a.phase === p.phase).sort((a, b) => +a.order - +b.order).forEach((a) => {
      const d = el('details', 'kx-action'); d.dataset.id = a.id; if (open.has(a.id)) d.open = true;
      const s = el('summary');
      const left = el('div'); left.append(el('b', null, a.title));
      const meta = el('div', 'kx-action-meta');
      [a.kind, a.owner, 'Effort ' + a.effort.split(' ')[0], 'Confidence: ' + a.confidence].forEach((t, i) => meta.append(el('span', i === 0 ? 'kx-chip' : null, t)));
      if (a.conditional) meta.append(el('span', 'kx-cond', 'Conditional'));
      left.append(meta);
      s.append(left, el('span', 'kx-expander', 'Details'));
      const body = el('div', 'kx-action-body');
      const dl = el('dl');
      const hyp = a.hypothesis ? a.hypothesis.split(',').map((h) => HYP_LABEL[h.trim()] || h).join(', ') : '—';
      [['What', a.action], ['Evidence', a.evidence], ['Hypotheses', hyp], ['Eligible population', a.eligible + (blank(a.eligible_n) ? '' : ' (' + FMT.int(+a.eligible_n) + ' in the recent period)')],
        ['Expected outcome', a.outcome], ['Confidence', a.confidence], ['Accountable', a.owner], ['Participants', a.participant_names], ['Dependencies', a.dependencies || '—'],
        ['Effort (assumed)', a.effort], ['Acceptance criteria', a.acceptance], ['Measurement window', a.window], ['Rollout and rollback', a.rollout], ['Guardrails', a.guardrails || '—'], ['Condition', a.conditional || 'None']]
        .forEach(([k, v]) => dl.append(el('dt', null, k), el('dd', null, v || '—')));
      body.append(dl); d.append(s, body); sec.append(d);
    });
    box.append(sec);
  });
}

function drawScenarios() {
  const sc = scenario();
  root.querySelectorAll('[data-scenario]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.scenario === sc)));
  const tot = rowsOf('scenario_totals'), rows = rowsOf('scenarios');
  const tiles = document.getElementById('scenario-tiles'); tiles.replaceChildren();
  if (!tot || !rows) return;
  const t = tot.find((r) => r.scenario === sc);
  [['Recoverable approvals per 30 days (' + sc.toLowerCase() + ')', FMT.int(+t.steady_30d), FMT.pp(+t.steady_pp) + ' on repeated causes; the recent rate would become ' + FMT.pct(+t.approval_with_steady)],
    ['Per comparable incident', FMT.int(+t.per_incident), 'Execution errors and liveness spikes; only when such an incident recurs'],
    ['If control findings are confirmed', FMT.signed(+t.control_gap_all), 'Approvals per 30 days that we might need to reverse if all are confirmed; ' + FMT.signed(+t.control_gap_50) + ' if half are']]
    .forEach(([label, big, sub]) => { const c = el('div', 'kx-card kx-tile'); c.append(el('span', 'kx-label', label), el('span', 'kx-big', big), el('span', 'kx-sub', sub)); tiles.append(c); });
  fillTable('scenario-table', rows.filter((r) => r.scenario === sc), 'id', [
    { field: 'population' }, { field: 'cadence', cls: 'kx-hide-narrow' }, { field: 'observed_n', fmt: 'int', cls: 'kx-num' }, { field: 'eligibility', fmt: 'share', cls: 'kx-num' },
    { field: 'reach', fmt: 'share', cls: 'kx-num' }, { field: 'return_rate', fmt: 'share', cls: 'kx-num' }, { field: 'remediation', fmt: 'share', cls: 'kx-num' },
    { field: 'subsequent_approval', fmt: 'share', cls: 'kx-num' }, { field: 'recovered', fmt: 'int', cls: 'kx-num' }]);
  document.getElementById('value-recoverable').textContent = FMT.int(+t.steady_30d) + ' (' + sc.toLowerCase() + ')';
  document.getElementById('value-incident').textContent = FMT.int(+t.per_incident) + ' (' + sc.toLowerCase() + ')';
}

const inputs = {};
let inputsBuilt = false;
let preset = 'Mid';
const PRESET_NAMES = ['Low', 'Mid', 'High', 'Cautious'];
const presetValue = (r, name) => Number(name === 'Cautious' ? r[r.cautious] : r[name.toLowerCase()]);
const fmtInput = (r, v) => (r.unit === 'share' ? FMT.pct(v) : r.unit === 'USD' ? (v < 100 && !Number.isInteger(v) ? d3.format('$,.2f')(v) : FMT.usd(v)) : d3.format(',.2~f')(v));
const toField = (r, v) => String(r.unit === 'share' ? +(v * 100).toFixed(2) : v);
function drawValueInputs() {
  const box = document.getElementById('value-inputs');
  const rows = rowsOf('value_inputs'); if (!rows || inputsBuilt) return;
  inputsBuilt = true;
  box.replaceChildren(...rows.map((r) => {
    const f = el('div', 'kx-field');
    const unit = r.unit === 'share' ? '%' : r.unit;
    const lab = el('label', null, r.label + ' (' + unit + ')'); lab.htmlFor = 'kx-in-' + r.id;
    const input = el('input'); input.type = 'number'; input.inputMode = 'decimal'; input.min = '0'; input.id = 'kx-in-' + r.id; input.dataset.id = r.id; input.dataset.unit = r.unit; input.step = 'any';
    if (r.unit === 'share') input.max = '100';
    const err = el('span', 'kx-err'); err.hidden = true; err.id = 'kx-err-' + r.id;
    const note = el('span', 'kx-note', r.note); note.id = 'kx-note-' + r.id;
    const range = el('span', 'kx-note kx-range', 'Market range ' + fmtInput(r, presetValue(r, 'Low')) + '–' + fmtInput(r, presetValue(r, 'High')) + ' · ' + r.kind + ' · ' + r.sources.split(' ').join(', '));
    range.id = 'kx-range-' + r.id;
    input.setAttribute('aria-describedby', err.id + ' ' + note.id + ' ' + range.id);
    input.addEventListener('input', () => { preset = null; readInput(input, err); drawPresetState(); drawValueResults(); });
    f.append(lab, input, err, note, range);
    return f;
  }));
  applyPreset(preset);
}
function applyPreset(name) {
  const rows = rowsOf('value_inputs'); if (!rows) return;
  preset = name;
  rows.forEach((r) => {
    const input = document.getElementById('kx-in-' + r.id); if (!input) return;
    input.value = name ? toField(r, presetValue(r, name)) : '';
    readInput(input, document.getElementById('kx-err-' + r.id));
  });
  drawPresetState(); drawValueResults();
}
function drawPresetState() {
  root.querySelectorAll('[data-preset]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.preset === preset)));
  const st = document.getElementById('value-preset-status');
  const filled = Object.keys(inputs).length;
  st.replaceChildren();
  if (preset) st.append(el('b', null, preset + ' preset. '), document.createTextNode('Market-based assumptions from published sources, not ARQ figures.'));
  else if (filled) st.append(el('b', null, 'Your values. '), document.createTextNode(filled + ' of ' + rowsOf('value_inputs').length + ' inputs set; choose a preset to reset them.'));
  else st.append(el('b', null, 'No inputs. '), document.createTextNode('Choose a preset or type values.'));
}
function readInput(input, err) {
  const id = input.dataset.id, raw = input.value.trim();
  delete inputs[id]; input.removeAttribute('aria-invalid'); err.hidden = true;
  if (raw === '' && !input.validity.badInput) return;
  const v = Number(raw);
  const max = input.dataset.unit === 'share' ? 100 : Infinity;
  if (raw === '' || !Number.isFinite(v) || v < 0 || v > max) { input.setAttribute('aria-invalid', 'true'); err.textContent = input.dataset.unit === 'share' ? 'Enter a percentage from 0 to 100.' : 'Enter a number of 0 or more.'; err.hidden = false; return; }
  inputs[id] = input.dataset.unit === 'share' ? v / 100 : v;
}
root.querySelectorAll('[data-preset]').forEach((b) => b.addEventListener('click', () => applyPreset(b.dataset.preset)));
document.getElementById('value-clear').addEventListener('click', () => applyPreset(null));
function valueResults(sc, x) {
  const tot = rowsOf('scenario_totals'), scen = rowsOf('scenarios'), inc = rowsOf('incidents');
  const t = tot.find((r) => r.scenario === sc);
  const rec = +t.steady_30d;
  const review = scen.find((r) => r.action === 'review_queue' && r.scenario === sc);
  const attack = inc.find((r) => r.id === 'fraud_arg');
  const act = () => rec * x.activation_rate;
  return [
    ['activated', 'Activated customers from recoverable approvals, per 30 days', ['activation_rate'], () => Math.round(act()), 'int'],
    ['cohort_value', 'First-year value of one 30-day cohort of those customers', ['activation_rate', 'value_per_activated'], () => act() * x.value_per_activated, 'usd'],
    ['annualised', 'Same, if every 30 days repeats for a year (annualised)', ['activation_rate', 'value_per_activated'], () => act() * x.value_per_activated * 365 / 30, 'usd'],
    ['vendor_declined', 'Historical vendor spend on recent not-approved decisions', ['billable_per_decision', 'cost_per_transaction'], () => kv('unsuccessful_b') * x.billable_per_decision * x.cost_per_transaction, 'usd'],
    ['vendor_attack', 'Vendor spend avoidable if suspected extra attack traffic were blocked before the vendor call', ['billable_per_decision', 'cost_per_transaction'], () => +attack.excess_volume * x.billable_per_decision * x.cost_per_transaction, 'usd'],
    ['paid_declined', 'Historical paid acquisition spend on recent not-approved applicants', ['paid_share', 'cac_paid'], () => kv('unsuccessful_b') * x.paid_share * x.cac_paid, 'usd'],
    ['review_30d', 'Review cost per 30 days for the review-pilot population', ['review_cost'], () => +review.observed_n * x.review_cost, 'usd'],
    ['breakeven', 'Break-even first-year value per activated customer', ['activation_rate', 'build_cost', 'run_cost_month'], () => (act() > 0 ? (x.build_cost / 12 + x.run_cost_month) / act() : NaN), 'usd'],
  ];
}
function drawValueResults() {
  const out = document.getElementById('value-results');
  const vin = rowsOf('value_inputs');
  out.replaceChildren();
  if (!rowsOf('scenario_totals') || !rowsOf('scenarios') || !rowsOf('incidents') || !vin) return;
  const sc = scenario();
  const label = (id) => vin.find((v) => v.id === id).label.toLowerCase();
  const need = (ids) => ids.filter((i) => !(i in inputs));
  const st = document.getElementById('value-results-status');
  st.textContent = (preset ? preset + ' preset' : 'Your values') + ', ' + sc.toLowerCase() + ' scenario. Change the scenario at the top of this tab.';
  const shown = {};
  valueResults(sc, inputs).forEach(([id, name, ids, fn, unit]) => {
    const miss = need(ids);
    let text = 'Needs ' + miss.map(label).join(', ');
    if (!miss.length) {
      const v = fn(); shown[id] = v;
      text = id === 'breakeven' ? (Number.isFinite(v) ? FMT.usd(v) + ' (build cost spread over 12 months)' : 'Not defined: no recoverable activations') : unit === 'int' ? FMT.int(v) : FMT.usd(v);
    }
    out.append(el('dt', null, name), el('dd', miss.length ? 'kx-note' : null, text));
  });
  if ('breakeven' in shown && Number.isFinite(shown.breakeven) && 'value_per_activated' in inputs) {
    const ok = inputs.value_per_activated >= shown.breakeven;
    out.append(el('dt', null, 'Pays back within the first year?'),
      el('dd', null, (ok ? 'Yes: ' : 'No: ') + FMT.usd(inputs.value_per_activated) + ' value per activated customer against ' + FMT.usd(shown.breakeven) + ' needed'));
  }
}
function drawPresetTables() {
  const vin = rowsOf('value_inputs'), src = rowsOf('value_sources');
  const pt = document.getElementById('preset-table');
  if (vin && pt) {
    const body = pt.querySelector('tbody');
    const open = new Set([...body.querySelectorAll('tr')].filter((tr) => tr.querySelector('details[open]')).map((tr) => tr.dataset.key));
    body.replaceChildren();
    vin.forEach((r) => {
      const tr = el('tr'); tr.dataset.key = r.id;
      tr.append(el('td', null, r.label + ' (' + (r.unit === 'share' ? '%' : r.unit) + ')'));
      ['Low', 'Mid', 'High'].forEach((n) => tr.append(el('td', 'kx-num', fmtInput(r, presetValue(r, n)))));
      const basis = el('td'); const d = el('details', 'kx-derive'); d.open = printing || open.has(r.id); d.append(el('summary', null, r.short + ' (' + r.sources.split(' ').join(', ') + ')'), el('p', 'kx-note', r.basis)); basis.append(d);
      tr.append(el('td', 'kx-hide-narrow', r.kind), basis);
      body.append(tr);
    });
  }
  fillTable('value-sources-table', src, 'id', [{ field: 'id' }, { field: 'publisher', link: 'url' }, { field: 'figure' }, { field: 'period', cls: 'kx-hide-narrow' }, { field: 'status' }]);
  const st = document.getElementById('value-sources-table');
  if (st && src) st.querySelectorAll('tbody tr').forEach((tr) => { const a = tr.children[1].querySelector('a'); const r = src.find((x) => x.id === tr.dataset.key); if (a && r) a.textContent = r.publisher + ': ' + r.title; });
}

/* ---------- Quick review ---------- */
const TRACK_KINDS = { t_fix: ['1', 'Fix and measure'], t_test: ['2', 'Test the fixes'], t_learn: ['3', 'Learn why'], t_vendor: ['4', 'Decide on the vendor'] };
function drawQuick() {
  const box = document.getElementById('quick-body');
  const rows = rowsOf('quick_review'); if (!box || !rows) return;
  const items = rows.slice().sort((a, b) => +a.order - +b.order);
  const sections = [];
  items.forEach((r) => { let sec = sections.find((x) => x.id === r.section); if (!sec) { sec = { id: r.section, heading: r.heading, goto: r.goto, items: [] }; sections.push(sec); } sec.items.push(r); });
  const WIDE = new Set(['result', 'causes', 'incidents', 'plan', 'questions']);
  const charts = [];
  // render one section's items into a container; returns the container
  const fill = (into, list) => {
    let ul = null, tracks = null;
    list.forEach((r) => {
      if (r.kind === 'chart') { const c = el('div', 'kx-qchart'); c.dataset.chart = r.text; into.append(c); charts.push(c); ul = null; return; }
      if (r.kind in TRACK_KINDS) {
        if (!tracks) { tracks = el('div', 'kx-tracks'); into.append(tracks); }
        let t = tracks.querySelector('[data-track="' + r.kind + '"]');
        if (!t) { t = el('div', 'kx-track'); t.dataset.track = r.kind; const h = el('h4'); h.append(el('span', null, TRACK_KINDS[r.kind][0]), document.createTextNode(TRACK_KINDS[r.kind][1])); t.append(h, el('ol')); tracks.append(t); }
        t.querySelector('ol').append(el('li', null, r.text)); ul = null; return;
      }
      if (r.kind === 'li') { if (!ul) { ul = el('ul'); into.append(ul); } ul.append(el('li', null, r.text)); return; }
      ul = null;
      if (r.kind === 'caution') { const c = el('p', 'kx-caveat'); const [head, ...rest] = r.text.split(': '); c.append(el('b', null, head + ': '), document.createTextNode(rest.join(': '))); into.append(c); }
      else into.append(el('p', r.kind === 'lead' ? 'kx-qlead' : r.kind === 'term' ? 'kx-qterm' : null, r.text));
    });
    return into;
  };
  const more = (goto) => {
    const tab = document.getElementById('tab-' + goto);
    const p = el('p', 'kx-more'); const b = el('button', 'kx-link', 'More detail: ' + (tab ? tab.textContent : goto)); b.type = 'button'; b.dataset.goto = goto; p.append(b); return p;
  };
  const data = sections.find((x) => x.id === 'data');
  const cards = sections.filter((x) => x.id !== 'data').map((sec, i) => {
    const card = el('article', 'kx-card' + (WIDE.has(sec.id) ? ' kx-qwide' : ''));
    card.append(el(i === 0 ? 'h2' : 'h3', null, sec.heading));
    const chartItems = sec.items.filter((r) => r.kind === 'chart'), textItems = sec.items.filter((r) => r.kind !== 'chart');
    if (sec.id === 'result' && data) {
      // the result, with what the data can show beside it
      const split = el('div', 'kx-qsplit');
      const left = fill(el('div'), sec.items);
      const aside = el('div', 'kx-qaside'); aside.append(el('h3', null, data.heading)); fill(aside, data.items); aside.append(more(data.goto));
      split.append(left, aside); card.append(split);
    } else if (WIDE.has(sec.id) && chartItems.length && sec.id !== 'plan') {
      const split = el('div', 'kx-qsplit');
      split.append(fill(el('div'), chartItems), fill(el('div'), textItems));
      card.append(split);
    } else {
      fill(card, sec.items);
      if (sec.id === 'questions') card.querySelectorAll('ul').forEach((u) => u.classList.add('kx-qcols'));
    }
    if (sec.goto) card.append(more(sec.goto));
    return card;
  });
  box.replaceChildren(...cards);
  const words = items.reduce((n, r) => n + (r.kind === 'chart' ? 0 : r.text.split(/\s+/).length), 0);
  const t = document.getElementById('quick-time'); if (t) t.textContent = String(Math.max(1, Math.round(words / 200)));
  if (visible(box)) charts.forEach((c) => QUICK_CHARTS[c.dataset.chart]?.(c));
}
document.getElementById('quick-body').addEventListener('click', (ev) => {
  const b = ev.target.closest('[data-goto]'); if (!b) return;
  showTab(b.dataset.goto); root.querySelector('.kx-tabbar').scrollIntoView({ block: 'start' }); document.getElementById('tab-' + b.dataset.goto).focus();
});
const qsvg = (box, w, h) => { const s = d3.create('svg').attr('viewBox', `0 0 ${w} ${h}`).attr('width', w).attr('height', h).attr('role', 'img'); box.append(s.node()); return s; };
const qlegend = (box, pairs) => { const l = el('div', 'kx-qlegend'); pairs.forEach(([color, label]) => { const sp = el('span'); const i = el('i'); i.style.background = color; sp.append(i, label); l.append(sp); }); box.append(l); };
const QUICK_CHARTS = {
  // two stacked bars: all decisions, split into approved and not approved, prior vs recent
  funnel(box) {
    const K = (m) => kv(m);
    const W = 640, rowH = 34, H = 2 * rowH + 8, L = 150, R = 176;
    const svg = qsvg(box, W, H).attr('aria-label', 'Decisions per period, approved and not approved');
    const maxN = Math.max(K('n_a'), K('n_b'));
    const x = d3.scaleLinear([0, maxN], [L, W - R]);
    [['Prior 30 days', K('n_a'), K('approved_a'), K('approval_a')], ['Recent 30 days', K('n_b'), K('approved_b'), K('approval_b')]].forEach(([label, n, ap, rate], i) => {
      const y = 8 + i * rowH;
      svg.append('text').attr('x', L - 10).attr('y', y + 18).attr('text-anchor', 'end').text(label);
      svg.append('rect').attr('x', x(0)).attr('y', y).attr('width', x(ap) - x(0)).attr('height', 24).attr('rx', 3).style('fill', colors()[0]);
      svg.append('rect').attr('x', x(ap)).attr('y', y).attr('width', x(n) - x(ap)).attr('height', 24).attr('rx', 3).style('fill', 'var(--cds-chart-status-critical)').attr('fill-opacity', 0.75);
      svg.append('text').attr('x', x(0) + 8).attr('y', y + 17).style('fill', 'var(--color-bg)').style('font-weight', 600).text(FMT.pct(rate) + ' approved (' + FMT.int(ap) + ')');
      svg.append('text').attr('x', x(n) + 6).attr('y', y + 17).attr('class', 'kx-qmuted').text(FMT.int(n - ap) + ' not approved');
    });
    // the caption is HTML, so it wraps on a narrow screen
    box.append(el('p', 'kx-note', 'Bar length = recorded decisions (' + FMT.int(K('n_a')) + ' then ' + FMT.int(K('n_b')) + '). Starts are not in the data.'));
  },
  // donut of not-approved decisions by class (recent) + bars of the change in rate by cause
  causes(box) {
    const dec = rowsOf('declines'), br = rowsOf('bridge'); if (!dec || !br) return;
    box.style.flexDirection = 'column'; box.style.alignItems = 'stretch';
    // 1. what the not-approved decisions are (composition, recent period)
    const classes = dec.filter((r) => r.level === 'class').map((r) => ({ name: r.name, v: +r.of_unsuccessful_b, n: +r.n_b }));
    const f1 = el('figure', 'kx-qfig'); box.append(f1);
    f1.append(el('figcaption', null, 'What the ' + FMT.int(kv('unsuccessful_b')) + ' not-approved decisions are, recent 30 days'));
    const row = el('div', 'kx-qfig-row'); f1.append(row);
    const d1 = el('div'); d1.style.flex = '0 0 170px'; row.append(d1);
    const svg = qsvg(d1, 170, 170).attr('aria-label', 'Not-approved decisions by class, recent period');
    const arc = d3.arc().innerRadius(48).outerRadius(82), pie = d3.pie().value((d) => d.v).sort(null);
    const g = svg.append('g').attr('transform', 'translate(85,85)');
    g.selectAll('path').data(pie(classes)).join('path').attr('d', arc).style('fill', (d) => classColor(d.data.name)).append('title').text((d) => d.data.name + ': ' + FMT.pct0(d.data.v) + ' (' + FMT.int(d.data.n) + ')');
    svg.append('text').attr('x', 85).attr('y', 82).attr('text-anchor', 'middle').style('font-weight', 600).text(FMT.int(kv('unsuccessful_b')));
    svg.append('text').attr('x', 85).attr('y', 98).attr('text-anchor', 'middle').attr('class', 'kx-qmuted').text('not approved');
    const leg = el('ul', 'kx-qkey'); row.append(leg);
    classes.forEach((c) => { const li = el('li'); const i = el('i'); i.style.background = classColor(c.name); li.append(i, el('b', null, FMT.pct0(c.v)), document.createTextNode(' ' + c.name)); leg.append(li); });
    // 2. how the rate moved from the prior to the recent period (a bridge, no colour)
    const f2 = el('figure', 'kx-qfig'); box.append(f2);
    const a = 100 * kv('approval_a'), z = 100 * kv('approval_b'), total = kv('delta_pp');
    f2.append(el('figcaption', null, 'How the pass rate went from ' + FMT.pct(kv('approval_a')) + ' to ' + FMT.pct(kv('approval_b'))));
    const eff = (d) => +br.find((r) => r.driver === d).effect_pp;
    const shown = [['Fraud signals', eff('Fraud signal')], ['Execution errors', eff('Execution error')], ['Selfie and liveness', eff('Selfie / liveness')],
      ['No document type (Mexico)', eff('No document type, no reason code')], ['Face match', eff('Face match')]];
    const other = +(total - d3.sum(shown, (x) => x[1])).toFixed(2);
    const steps = shown.slice(0, 4).concat([['Other reasons', other], shown[4]]);
    const W = 600, rowH = 30, L = 180, R = 76, T = 6, rows = steps.length + 2, H = T + rows * rowH + 30;
    const s2 = qsvg(f2, W, H).attr('aria-label', 'Bridge from the prior to the recent pass rate, by reason');
    const x = d3.scaleLinear([Math.floor(z - 0.6), Math.ceil(a + 0.6)], [L, W - R]);
    const yRow = (i) => T + i * rowH;
    x.ticks(5).forEach((t) => { s2.append('line').attr('x1', x(t)).attr('x2', x(t)).attr('y1', T).attr('y2', yRow(rows)).style('stroke', 'var(--cds-chart-grid)'); s2.append('text').attr('x', x(t)).attr('y', yRow(rows) + 14).attr('text-anchor', 'middle').attr('class', 'kx-qmuted').text(t + '%'); });
    const label = (i, txt, bold) => s2.append('text').attr('x', L - 10).attr('y', yRow(i) + rowH / 2 + 4).attr('text-anchor', 'end').style('font-weight', bold ? 600 : 400).text(txt);
    const value = (i, txt, bold) => s2.append('text').attr('x', W - R + 10).attr('y', yRow(i) + rowH / 2 + 4).style('font-weight', bold ? 600 : 400).style('font-variant-numeric', 'tabular-nums').text(txt);
    const dot = (i, v) => s2.append('circle').attr('cx', x(v)).attr('cy', yRow(i) + rowH / 2).attr('r', 5).style('fill', 'var(--color-fg)');
    label(0, 'Prior 30 days', true); value(0, FMT.pct(kv('approval_a')), true); dot(0, a);
    let run = a;
    steps.forEach(([name, v], k) => {
      const i = k + 1, next = run + v;
      s2.append('line').attr('x1', x(run)).attr('x2', x(run)).attr('y1', yRow(i) - rowH / 2 + 2).attr('y2', yRow(i) + 5).style('stroke', 'var(--color-fg-muted)').attr('stroke-dasharray', '2 2');
      s2.append('rect').attr('x', x(Math.min(run, next))).attr('y', yRow(i) + 5).attr('width', Math.max(1.5, Math.abs(x(next) - x(run)))).attr('height', rowH - 10).attr('rx', 2)
        .style('fill', 'var(--color-fg-muted)').attr('fill-opacity', v < 0 ? 0.55 : 0.25).style('stroke', 'var(--color-fg-muted)').attr('stroke-width', v < 0 ? 0 : 1);
      label(i, name); value(i, FMT.pp2(v));
      run = next;
    });
    s2.append('line').attr('x1', x(run)).attr('x2', x(run)).attr('y1', yRow(rows - 1) - rowH / 2 + 2).attr('y2', yRow(rows - 1) + rowH / 2).style('stroke', 'var(--color-fg-muted)').attr('stroke-dasharray', '2 2');
    label(rows - 1, 'Recent 30 days', true); value(rows - 1, FMT.pct(kv('approval_b')), true); dot(rows - 1, z);
    f2.append(el('p', 'kx-qmuted kx-qnote', 'Each bar is the change from one reason, in percentage points. Together they make the ' + FMT.pp(total) + ' drop. A bar to the left lowers the rate; a bar to the right raises it.'));
  },
  // the daily line with incident days shaded, and both period averages
  days(box) {
    const daily = rowsOf('daily'); if (!daily) return;
    const rows = daily.filter((r) => r.country === 'ALL').map((r) => ({ date: new Date(r.date), rate: +r.approval_rate, inc: r.incident_day === '1' }));
    const W = 400, H = 150, L = 40, R = 8, T = 10, B = 22;
    const d1 = el('div'); d1.style.flex = '1 1 100%'; box.append(d1);
    const svg = qsvg(d1, W, H).attr('aria-label', 'Daily pass rate with incident days shaded');
    const x = d3.scaleUtc(d3.extent(rows, (r) => r.date), [L, W - R]), y = d3.scaleLinear([0.5, 1], [H - B, T]);
    const bw = (W - L - R) / rows.length;
    rows.filter((r) => r.inc).forEach((r) => svg.append('rect').attr('x', x(r.date) - bw / 2).attr('y', T).attr('width', bw).attr('height', H - T - B).style('fill', 'var(--cds-chart-status-critical)').attr('fill-opacity', 0.18));
    [0.6, 0.8, 1].forEach((v) => { svg.append('line').attr('x1', L).attr('x2', W - R).attr('y1', y(v)).attr('y2', y(v)).style('stroke', 'var(--cds-chart-grid)'); svg.append('text').attr('x', L - 6).attr('y', y(v) + 4).attr('text-anchor', 'end').attr('class', 'kx-qmuted').text(FMT.pct0(v)); });
    const split = new Date(pick(rowsOf('kpis'), 'metric=split_date').value);
    [[rows[0].date, split, kv('approval_a')], [split, rows[rows.length - 1].date, kv('approval_b')]].forEach(([a, b, v]) => svg.append('line').attr('x1', x(a)).attr('x2', x(b)).attr('y1', y(v)).attr('y2', y(v)).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3'));
    svg.append('path').datum(rows).style('fill', 'none').style('stroke', colors()[0]).attr('stroke-width', 2).attr('stroke-linejoin', 'round').attr('d', d3.line().x((r) => x(r.date)).y((r) => y(r.rate)));
    svg.append('text').attr('x', L).attr('y', H - 6).attr('class', 'kx-qmuted').text(FMT.date(rows[0].date));
    svg.append('text').attr('x', W - R).attr('y', H - 6).attr('text-anchor', 'end').attr('class', 'kx-qmuted').text(FMT.date(rows[rows.length - 1].date));
    qlegend(d1, [[colors()[0], 'Daily pass rate'], ['var(--cds-chart-status-critical)', 'Incident window day'], ['var(--cds-chart-reference)', 'Period averages ' + FMT.pct(kv('approval_a')) + ' and ' + FMT.pct(kv('approval_b'))]]);
  },
  // the range of recoverable points, conservative to optimistic, with the central case marked
  gain(box) {
    const tot = rowsOf('scenario_totals'); if (!tot) return;
    const g = (n) => tot.find((r) => r.scenario === n);
    const lo = +g('Conservative').steady_pp, mid = +g('Central').steady_pp, hi = +g('Optimistic').steady_pp;
    const W = 400, H = 74, L = 24, R = 24;
    const d1 = el('div'); d1.style.flex = '1 1 100%'; box.append(d1);
    const svg = qsvg(d1, W, H).attr('aria-label', 'Range of recoverable pass-rate points');
    const x = d3.scaleLinear([0, Math.ceil(hi) + 1], [L, W - R]);
    svg.append('line').attr('x1', L).attr('x2', W - R).attr('y1', 40).attr('y2', 40).style('stroke', 'var(--cds-chart-axis)');
    x.ticks(6).forEach((t) => { svg.append('line').attr('x1', x(t)).attr('x2', x(t)).attr('y1', 40).attr('y2', 45).style('stroke', 'var(--cds-chart-axis)'); svg.append('text').attr('x', x(t)).attr('y', 60).attr('text-anchor', 'middle').attr('class', 'kx-qmuted').text('+' + t); });
    svg.append('rect').attr('x', x(lo)).attr('y', 26).attr('width', x(hi) - x(lo)).attr('height', 14).attr('rx', 7).style('fill', colors()[0]).attr('fill-opacity', 0.35);
    svg.append('circle').attr('cx', x(mid)).attr('cy', 33).attr('r', 8).style('fill', colors()[0]);
    svg.append('text').attr('x', x(lo)).attr('y', 18).attr('text-anchor', 'middle').attr('class', 'kx-qmuted').text(FMT.pp(lo));
    svg.append('text').attr('x', x(hi)).attr('y', 18).attr('text-anchor', 'middle').attr('class', 'kx-qmuted').text(FMT.pp(hi));
    svg.append('text').attr('x', x(mid)).attr('y', 18).attr('text-anchor', 'middle').style('font-weight', 600).text('Central ' + FMT.pp(mid));
    svg.append('text').attr('x', W - R).attr('y', 72).attr('text-anchor', 'end').attr('class', 'kx-qmuted').text('Pass-rate points recoverable per 30 days, on repeated causes');
  },
};

/* ---------- What to do: tracks × phases ---------- */
function drawTracks() {
  const box = document.getElementById('tracks');
  const acts = rowsOf('actions'), phases = rowsOf('phases'), tracks = rowsOf('tracks'); if (!box || !acts || !phases || !tracks) return;
  box.replaceChildren();
  const grid = el('div', 'kx-lanes');
  grid.append(el('div', 'kx-lane-h', ''));
  phases.forEach((p) => grid.append(el('div', 'kx-lane-h', p.label.replace(/^Phase (\d) · /, 'P$1 · '))));
  tracks.slice().sort((a, b) => +a.order - +b.order).forEach((t) => {
    const th = el('div', 'kx-lane-t'); th.append(document.createTextNode(t.name), el('small', null, t.note)); grid.append(th);
    phases.forEach((p) => {
      const cell = el('div', 'kx-lane-c');
      acts.filter((a) => a.track === t.id && a.phase === p.phase).sort((a, b) => +a.order - +b.order).forEach((a) => {
        const b = el('button', 'kx-lane-chip' + (a.conditional ? ' kx-lane-cond' : ''), a.title); b.type = 'button'; b.dataset.action = a.id;
        b.title = (a.conditional ? 'Conditional. ' : '') + a.owner + ' · effort ' + a.effort.split(' ')[0];
        cell.append(b);
      });
      grid.append(cell);
    });
  });
  box.append(grid);
}
document.getElementById('tracks').addEventListener('click', (ev) => {
  const b = ev.target.closest('[data-action]'); if (!b) return;
  const d = document.querySelector('#roadmap details[data-id="' + b.dataset.action + '"]'); if (!d) return;
  d.open = true; d.scrollIntoView({ block: 'center' }); d.querySelector('summary').focus({ preventScroll: true });
});

/* ---------- Ask about this case ----------
   Shown only when the hosted build adds window.KX_CHAT = { endpoint, token }. The proxy holds the API key.
   Answers are drawn with textContent only: the model's text never becomes HTML. */
(() => {
  const cfg = window.KX_CHAT, panel = document.getElementById('ask');
  if (!panel || !cfg || !cfg.endpoint || !cfg.token) return;
  panel.hidden = false;
  const thread = document.getElementById('ask-thread'), form = document.getElementById('ask-form'), input = document.getElementById('ask-input');
  const send = document.getElementById('ask-send'), clear = document.getElementById('ask-clear'), chips = document.getElementById('ask-chips'), count = document.getElementById('ask-count');
  const MAX = 1500, history = [];
  let busy = false;
  const inline = (parent, text) => {
    text.split(/(\*\*[^*]+\*\*)/g).forEach((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) parent.append(el('b', null, part.slice(2, -2)));
      else if (part) parent.append(document.createTextNode(part));
    });
  };
  // paragraphs, "- " bullets and **bold** only; bullet lines are grouped wherever they appear
  const render = (body, text) => {
    body.replaceChildren();
    const isBullet = (l) => /^\s*[-*•]\s+/.test(l);
    text.replace(/\r/g, '').split(/\n{2,}/).forEach((block) => {
      let p = null, ul = null;
      block.split('\n').filter((l) => l.trim()).forEach((l) => {
        if (isBullet(l)) {
          p = null;
          if (!ul) { ul = el('ul'); body.append(ul); }
          const li = el('li'); inline(li, l.replace(/^\s*[-*•]\s+/, '')); ul.append(li);
        } else {
          ul = null;
          if (p) p.append(el('br')); else { p = el('p'); body.append(p); }
          inline(p, l.replace(/^#+\s*/, ''));
        }
      });
    });
  };
  const add = (role, text) => {
    const msg = el('div', 'kx-ask-msg kx-ask-' + role), body = el('div', 'kx-ask-body');
    if (role === 'user') body.textContent = text; else render(body, text);
    msg.append(body); thread.append(msg); thread.scrollTop = thread.scrollHeight;
    return body;
  };
  const state = () => {
    send.disabled = busy || !input.value.trim() || input.value.length > MAX;
    clear.hidden = busy || !thread.children.length;
    chips.hidden = busy || thread.children.length > 0;
    count.textContent = input.value.length > MAX * 0.8 ? input.value.length + ' / ' + MAX : '';
  };
  // the input starts as one line and grows with the text, up to its max-height
  const fit = () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 200) + 'px'; input.style.overflowY = input.scrollHeight > 200 ? 'auto' : 'hidden'; };
  async function ask(question) {
    const q = question.trim();
    if (busy || !q || q.length > MAX) return;
    busy = true; input.value = ''; fit(); open(); state();
    history.push({ role: 'user', content: q });
    add('user', q);
    const body = add('assistant', '');
    body.classList.add('kx-ask-wait');
    body.append(el('span', 'kx-sr', 'Please wait.'), el('i'), el('i'), el('i'));
    let text = '';
    try {
      // the proxy accepts at most 12 turns, starting with a question: keep the newest odd number of turns
      const turns = history.length > 11 ? history.slice(history.length - 11) : history;
      const res = await fetch(cfg.endpoint.replace(/\/$/, '') + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Chat-Token': cfg.token }, body: JSON.stringify({ messages: turns }),
      });
      if (!res.ok || !res.body) {
        let msg = 'The chat is not available now. Try again later.';
        try { msg = (await res.json()).error || msg; } catch (e) { /* not JSON */ }
        throw new Error(msg);
      }
      const reader = res.body.getReader(), dec = new TextDecoder();
      body.classList.remove('kx-ask-wait');
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        text += dec.decode(value, { stream: true });
        render(body, text);
        thread.scrollTop = thread.scrollHeight;
      }
      if (!text.trim()) throw new Error('The chat sent an empty answer. Try again.');
      history.push({ role: 'assistant', content: text.slice(0, 6000) });
    } catch (e) {
      history.pop();
      body.classList.remove('kx-ask-wait');
      body.classList.add('kx-ask-err');
      body.textContent = e && e.message && !/fetch|network/i.test(e.message) ? e.message : 'The chat is not available now. Check the connection and try again.';
      // give the question back, so the reader can send it again
      if (!input.value) { input.value = q; fit(); }
    } finally {
      busy = false; state(); input.focus({ preventScroll: true });
    }
  }
  form.addEventListener('submit', (ev) => { ev.preventDefault(); ask(input.value); });
  input.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); ask(input.value); } });
  input.addEventListener('input', () => { fit(); state(); });
  chips.addEventListener('click', (ev) => { const b = ev.target.closest('button'); if (b) ask(b.textContent); });
  clear.addEventListener('click', () => { history.length = 0; thread.replaceChildren(); state(); input.focus(); });
  // closed: two suggestions, no hint. Clicking into the input opens the rest; leaving an empty chat closes it again.
  // A press inside the panel never closes it first, so a click on a suggestion always lands.
  let pressing = false;
  const open = () => panel.classList.add('kx-ask-open');
  const close = () => { if (!busy && !input.value.trim() && !thread.children.length) panel.classList.remove('kx-ask-open'); };
  ['focus', 'pointerdown', 'keydown'].forEach((t) => input.addEventListener(t, open));
  panel.addEventListener('pointerdown', () => { pressing = true; });
  document.addEventListener('pointerup', () => setTimeout(() => { pressing = false; }, 0), true);
  document.addEventListener('pointerdown', (ev) => { if (!panel.contains(ev.target)) close(); }, true);
  panel.addEventListener('focusout', () => setTimeout(() => { if (!pressing && !panel.contains(document.activeElement)) close(); }, 0));
  state();
})();

/* ---------- Open questions ---------- */
function drawOpenQuestions() {
  const q = rowsOf('open_questions'); if (!q) return;
  const rows = q.slice().sort((a, b) => +a.order - +b.order);
  const ol = document.getElementById('open-questions-summary');
  if (ol) ol.replaceChildren(...rows.map((r) => { const li = el('li'); li.append(el('b', 'kx-q', r.topic + '. '), document.createTextNode(r.question + ' '), el('span', 'kx-note', 'Changes: ' + r.changes)); return li; }));
  plainTable(document.getElementById('open-questions-table'), [{ label: '#' }, { label: 'Question' }, { label: 'Why it matters' }, { label: 'What the answer changes' }, { label: 'Who would know' }],
    rows.map((r) => [r.order, r.question, r.why, r.changes, r.who]));
}

/* ---------- Operating model ---------- */
function drawRegistry() {
  const box = document.getElementById('registry');
  const m = rowsOf('metrics'); if (!m || !rowsOf('departments')) return;
  const t = plainTable(box, [{ label: 'Metric' }, { label: 'Status' }, { label: 'Owner' }, { label: 'Contributors' }, { label: 'Version' }, { label: 'Approval' }, { label: 'Freshness' }, { label: 'Lineage' }],
    m.map((r) => [r.name, r.status, deptName(r.owner), r.contributors.split(',').map((c) => deptName(c.trim())).join(', '), r.version, r.approved_by, r.freshness, r.lineage]));
  t.querySelectorAll('tbody tr').forEach((tr) => { const td = tr.children[1]; const v = td.textContent; td.replaceChildren(el('span', chipClass(v), v)); });
}
function drawRaci() {
  const box = document.getElementById('raci');
  const raci = rowsOf('raci'), acts = rowsOf('actions'), depts = rowsOf('departments'); if (!raci || !acts || !depts) return;
  const used = depts.filter((d) => raci.some((r) => r.dept_id === d.id));
  const cells = new Map(raci.map((r) => [r.action_id + '|' + r.dept_id, r.role]));
  box.replaceChildren();
  const t = el('table', 'kx-table kx-raci'); const hr = el('tr'); hr.append(el('th', null, 'Action'));
  used.forEach((d) => hr.append(el('th', null, d.name)));
  const thead = el('thead'); thead.append(hr); const tb = el('tbody');
  acts.slice().sort((a, b) => +a.order - +b.order).forEach((a) => {
    const tr = el('tr'); tr.append(el('td', null, 'P' + a.phase + ' · ' + a.title));
    used.forEach((d) => { const td = el('td'); const role = cells.get(a.id + '|' + d.id); if (role) { const s = el('span', 'kx-r kx-r-' + role, role); s.title = d.name + ': ' + { A: 'accountable', R: 'responsible', C: 'consulted', I: 'informed' }[role]; s.setAttribute('aria-label', s.title); td.append(s); } tr.append(td); });
    tb.append(tr);
  });
  t.append(thead, tb); box.append(t);
}
function drawCommitments() {
  const acts = rowsOf('actions'); if (!acts || !rowsOf('departments')) return;
  plainTable(document.getElementById('commitments'), [{ label: 'Accountable' }, { label: 'Commitment' }, { label: 'Done when' }, { label: 'Due' }, { label: 'Check-in' }],
    acts.filter((a) => +a.phase <= 1).sort((a, b) => +a.order - +b.order).map((a) => [a.owner, a.title, a.acceptance, +a.phase === 0 ? 'End of week 2' : 'End of week 6', 'Weekly funnel review']));
}
function drawDeptCards() {
  const box = document.getElementById('dept-cards'); box.replaceChildren();
  const depts = rowsOf('departments'), raci = rowsOf('raci'), acts = rowsOf('actions'), rit = rowsOf('rituals'), met = rowsOf('metrics');
  if (!depts || !raci || !acts || !rit || !met) return;
  const byId = new Map(acts.map((a) => [a.id, a]));
  depts.forEach((d) => {
    const card = el('article', 'kx-card kx-dept');
    card.append(el('h4', null, d.name), el('p', 'kx-note', d.focus));
    const list = (title, items) => { if (!items.length) return; const w = el('div'); w.append(el('span', 'kx-label', title)); const ul = el('ul'); items.forEach((t) => ul.append(el('li', null, t))); w.append(ul); card.append(w); };
    list('Metrics owned', met.filter((m) => m.owner === d.id).map((m) => m.name + (m.status === 'Unavailable' ? ' (not yet measurable)' : '')));
    list('Accountable for', raci.filter((r) => r.dept_id === d.id && r.role === 'A').map((r) => byId.get(r.action_id)).filter(Boolean).map((a) => 'P' + a.phase + ' · ' + a.title));
    list('Works on', raci.filter((r) => r.dept_id === d.id && r.role === 'R').map((r) => byId.get(r.action_id)).filter(Boolean).map((a) => 'P' + a.phase + ' · ' + a.title));
    list('Meetings', rit.filter((r) => r.attendee_ids.split(';').includes(d.id)).map((r) => r.cadence + ': ' + r.meeting));
    box.append(card);
  });
}
function drawAdoption() {
  const box = document.getElementById('adoption'); const rows = rowsOf('adoption'); if (!rows) return;
  box.replaceChildren(); rows.forEach((r) => box.append(el('dt', null, r.topic), el('dd', null, r.plan)));
}

/* ---------- table views ---------- */
function drawTables() {
  const metrics = rowsOf('metrics');
  fillTable('metrics-table', metrics, 'id', [{ field: 'name' }, { field: 'status', chip: true }, { field: 'definition', cls: 'kx-wide' }, { field: 'window', cls: 'kx-hide-narrow' },
    { field: 'value_a', cls: 'kx-num' }, { field: 'value_b', cls: 'kx-num' }, { field: 'gap', cls: 'kx-hide-narrow' }]);
  document.querySelectorAll('#metrics-table tbody tr').forEach((tr) => {
    const row = metrics.find((m) => m.id === tr.dataset.key);
    [['value_a', 4], ['value_b', 5]].forEach(([f, i]) => { const v = row[f]; if (blank(v)) return; tr.children[i].textContent = row.unit === 'pct' ? (Number(v) < 0.01 ? FMT.pct2(+v) : FMT.pct(+v)) : FMT.int(+v); });
  });
  fillTable('validation-table', rowsOf('validation'), 'id', [{ field: 'check' }, { field: 'result' }, { field: 'status', chip: true }, { field: 'note', cls: 'kx-hide-narrow kx-wide' }]);
  fillTable('events-table', rowsOf('events'), 'event', [{ field: 'event', cls: 'kx-code' }, { field: 'when' }, { field: 'fields', cls: 'kx-code' }, { field: 'enables', cls: 'kx-hide-narrow' }]);
  const docs = rowsOf('docs');
  fillTable('docs-table', docs && docs.filter((r) => r.country === 'MEX'), 'id', [{ field: 'label' }, { field: 'share_a', fmt: 'pct', cls: 'kx-num' }, { field: 'share_b', fmt: 'pct', cls: 'kx-num' }, { field: 'approval_rate_a', fmt: 'pct', cls: 'kx-num' }, { field: 'approval_rate_b', fmt: 'pct', cls: 'kx-num' }, { field: 'n', fmt: 'int', cls: 'kx-num kx-hide-narrow' }]);
  const inc = rowsOf('incidents');
  fillTable('incident-table', inc && inc.slice().sort((a, b) => +a.order - +b.order), 'id', [{ field: 'title' }, { field: 'type', cls: 'kx-hide-narrow' }, { field: 'observed', fmt: 'int', cls: 'kx-num' }, { field: 'expected', fmt: 'num1', cls: 'kx-num' }, { field: 'excess', fmt: 'int', cls: 'kx-num' }, { field: 'share_of_decisions_b', fmt: 'pct2', cls: 'kx-num' }, { field: 'share_of_unsuccessful_b', fmt: 'pct', cls: 'kx-num' }, { field: 'contribution_pp', fmt: 'pp2', cls: 'kx-num' }, { field: 'ordinary_unsuccessful', fmt: 'int', cls: 'kx-num kx-hide-narrow' }]);
  const titles = new Map((inc || []).map((i) => [i.id, i.title]));
  const sens = rowsOf('incident_sensitivity');
  fillTable('sensitivity-table', sens && sens.map((s) => ({ ...s, incident: titles.get(s.incident) || s.incident })), 'id', [{ field: 'incident' }, { field: 'label' }, { field: 'observed', fmt: 'int', cls: 'kx-num' }, { field: 'attributed', fmt: 'int', cls: 'kx-num' }]);
  fillTable('evidence-table', rowsOf('vendor_evidence'), 'id', [{ field: 'date' }, { field: 'window_utc' }, { field: 'description', link: 'source', cls: 'kx-wide' }, { field: 'verification', chip: true, cls: 'kx-hide-narrow' }, { field: 'arq_impact' }]);
  fillTable('versions-table', rowsOf('metric_versions'), 'id', [{ field: 'version' }, { field: 'change' }, { field: 'reason', cls: 'kx-hide-narrow' }, { field: 'effective' }]);
  fillTable('rituals-table', rowsOf('rituals'), 'id', [{ field: 'cadence' }, { field: 'meeting' }, { field: 'chair', cls: 'kx-hide-narrow' }, { field: 'decides' }]);
  fillTable('escalation-table', rowsOf('escalation'), 'step', [{ field: 'within' }, { field: 'who' }, { field: 'does', cls: 'kx-wide' }]);
  fillTable('access-table', rowsOf('access'), 'audience', [{ field: 'audience' }, { field: 'sees' }, { field: 'restriction' }]);
  fillTable('alerts-table', rowsOf('alerts'), 'id', [{ field: 'metric' }, { field: 'owner', cls: 'kx-hide-narrow' }, { field: 'normal', fmt: 'pct', cls: 'kx-num' }, { field: 'rule' }, { field: 'days_prior', fmt: 'int', cls: 'kx-num' }, { field: 'days_recent', fmt: 'int', cls: 'kx-num' }, { field: 'first_recent', fmt: 'date', cls: 'kx-num' }]);
  fillTable('capability-table', rowsOf('vendor_capabilities'), 'id', [{ field: 'capability' }, { field: 'problem', cls: 'kx-hide-narrow' }, { field: 'documented', cls: 'kx-wide' }, { field: 'prerequisites' }, { field: 'inferred', cls: 'kx-hide-narrow' }, { field: 'unverified', cls: 'kx-hide-narrow' }, { field: 'verification', link: 'source' }]);
  fillTable('changes-table', rowsOf('vendor_changes'), 'id', [{ field: 'when' }, { field: 'area' }, { field: 'change', cls: 'kx-wide' }, { field: 'verification', link: 'source' }]);
  fillTable('compliance-table', rowsOf('compliance'), 'id', [{ field: 'finding' }, { field: 'n', fmt: 'int', cls: 'kx-num' }, { field: 'detail', cls: 'kx-hide-narrow' }, { field: 'alternatives', cls: 'kx-hide-narrow' }, { field: 'validation', cls: 'kx-wide' }]);
  fillTable('risk-table', rowsOf('risks'), 'id', [{ field: 'risk' }, { field: 'likelihood', chip: true }, { field: 'impact', chip: true }, { field: 'owner', cls: 'kx-hide-narrow' }, { field: 'mitigation', cls: 'kx-hide-narrow' }, { field: 'evidence_n', fmt: 'int', cls: 'kx-num' }]);
}

/* ---------- tabs, lenses, controls ---------- */
let activeTab = 'quick';
const detailsRow = document.getElementById('details-row'), detailsToggle = document.getElementById('details-toggle');
function setDetails(open) { detailsRow.hidden = !open; detailsToggle.setAttribute('aria-expanded', String(open)); detailsToggle.textContent = open ? 'Details ▴' : 'Details ▾'; }
detailsToggle.addEventListener('click', () => setDetails(detailsRow.hidden));
function showTab(id, opts = {}) {
  if (!TABS.includes(id)) return;
  activeTab = id;
  if (DETAIL_TABS.has(id) && detailsRow.hidden) setDetails(true);
  TABS.forEach((t) => { document.getElementById(t).hidden = t !== id; const b = document.getElementById('tab-' + t); b.setAttribute('aria-selected', String(t === id)); b.tabIndex = t === id ? 0 : -1; });
  if (opts.link !== false) dash.setLink(id);
  drawAll();
}
root.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));
root.querySelectorAll('.kx-tabs').forEach((nav) => nav.addEventListener('keydown', (ev) => {
  const keys = { ArrowRight: 1, ArrowLeft: -1, Home: 'first', End: 'last' };
  if (!(ev.key in keys)) return;
  ev.preventDefault();
  const i = TABS.indexOf(activeTab);
  const next = keys[ev.key] === 'first' ? TABS[0] : keys[ev.key] === 'last' ? TABS[TABS.length - 1] : TABS[(i + keys[ev.key] + TABS.length) % TABS.length];
  showTab(next); document.getElementById('tab-' + next).focus();
}));
root.querySelectorAll('[data-goto]').forEach((b) => b.addEventListener('click', () => { showTab(b.dataset.goto); root.querySelector('.kx-tabbar').scrollIntoView({ block: 'start' }); document.getElementById('tab-' + b.dataset.goto).focus(); }));
let lens = 'leadership';
root.querySelectorAll('[data-lens]').forEach((b) => b.addEventListener('click', () => { lens = b.dataset.lens; drawLens(); }));
function drawLens() {
  root.querySelectorAll('[data-lens]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lens === lens)));
  root.querySelectorAll('[data-lens-panel]').forEach((p) => { p.hidden = p.dataset.lensPanel !== lens; });
}
root.querySelectorAll('[data-country]').forEach((b) => b.addEventListener('click', () => dash.setParams({ country: b.dataset.country })));
root.querySelectorAll('[data-scenario]').forEach((b) => b.addEventListener('click', () => dash.setParams({ scenario: b.dataset.scenario })));
document.getElementById('reasons-search').addEventListener('input', () => drawReasons());
document.getElementById('trend-excl-days').addEventListener('change', () => drawTrend());
document.querySelectorAll('#reasons-table th button').forEach((b) => b.addEventListener('click', () => {
  const k = b.dataset.sort;
  if (reasonSort.key === k) reasonSort.dir *= -1; else { reasonSort.key = k; reasonSort.dir = ['reason', 'step', 'driver'].includes(k) ? 1 : -1; }
  drawReasons();
}));
document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') root.querySelectorAll('.kx-tip').forEach(hideTip); });

function drawAll() {
  root.querySelectorAll('[data-country]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.country === country())));
  drawLens();
  drawIncidentCards();
  fillMarks();
  drawTables();
  drawTrend(); drawBridge();
  drawDeclineChart(); drawDeclineCards(); drawMexBars(); drawUnclassified(); drawProcess(); drawMix(); drawReasons(); drawAge(); drawDocMix();
  (rowsOf('incidents') || []).forEach(drawSpark);
  drawQuick(); drawHypotheses(); drawExperiments(); drawOpenQuestions();
  drawTracks(); drawRoadmap(); drawScenarios(); drawValueInputs(); drawValueResults(); drawPresetTables();
  drawRegistry(); drawRaci(); drawCommitments(); drawDeptCards(); drawAdoption();
}

/* Print: show every tab, open every detail and draw every chart, then restore. */
let printing = false;
let savedOpen = [];
function printMode(on) {
  if (on === printing) return;
  printing = on;
  kxRoot.classList.toggle('kx-print-all', on);
  if (on) {
    savedOpen = [...root.querySelectorAll('details')].map((d) => [d, d.open]);
    savedOpen.forEach(([d]) => { d.open = true; });
  } else {
    savedOpen.forEach(([d, wasOpen]) => { d.open = wasOpen; });
  }
  drawAll();
  if (on) root.querySelectorAll('details').forEach((d) => { d.open = true; });
}
window.addEventListener('beforeprint', () => printMode(true));
window.addEventListener('afterprint', () => printMode(false));

function tabFromHash() {
  const hash = location.hash.slice(1);
  return TABS.includes(hash) ? hash : PLACE_TAB[hash];
}
window.addEventListener('hashchange', () => {
  if (location.hash === '#print') { printMode(true); return; }
  const tab = tabFromHash();
  if (tab && tab !== activeTab) showTab(tab, { link: false });
});

let opened = false;
dash.onData(() => {
  if (!opened) {
    opened = true;
    showTab(tabFromHash() || 'quick', { link: false });
    if (location.hash === '#print') printMode(true);
    return;
  }
  drawAll();
});
