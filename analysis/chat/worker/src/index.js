// Proxy for the dashboard's "Ask about this case" chat, and a small log of how the hosted page is used.
// Holds the Anthropic key, checks origin, access token and limits, and streams Claude's answer as plain text.
// Each question is kept with its answer in D1, page events too, and a Telegram chat gets a notification.
// "Who" is a random id from the browser plus place, network and browser from Cloudflare: no names, no IP addresses.
import RULES from '../rules.md';
import CASE_MATERIAL from '../case-material.md';

const enc = new TextEncoder();
const MAX_TURNS = 12;        // user and assistant turns together
const MAX_QUESTION = 1500;   // characters in one question
const MAX_ANSWER = 6000;     // characters in one earlier answer sent back as context
const MAX_TOTAL = 24000;     // characters in the whole conversation
const MAX_BODY = 40000;      // bytes in the request body
const MAX_EVENTS = 50;       // page events in one batch
const MAX_EVENT_BODY = 16000;
const EVENT_NAMES = new Set(['view', 'tab', 'details', 'chip', 'chat_open', 'click', 'print', 'leave']);
const ID = /^[a-z0-9-]{4,40}$/;
const VIEW_GAP_MS = 30 * 60 * 1000; // a new "dashboard opened" notification at most every 30 minutes per visitor

const MSG = {
  origin: 'This page cannot use the chat.',
  token: 'The chat token is not correct. Open the dashboard again from its link.',
  long: 'The conversation is too long. Clear the chat and ask again.',
  question: `A question can have at most ${MAX_QUESTION} characters.`,
  bad: 'The chat could not read the question.',
  minute: 'Too many questions in one minute. Wait a moment and try again.',
  day: 'The chat reached its limit for today. Try again tomorrow, or use the tabs below.',
  setup: 'The chat is not ready yet.',
  upstream: 'The model is not available now. Try again in a few minutes.',
};

function corsHeaders(origin, env) {
  const allowed = (env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const ok = allowed.includes(origin);
  const headers = { Vary: 'Origin' };
  if (ok) Object.assign(headers, {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Chat-Token',
    'Access-Control-Max-Age': '600',
  });
  return { ok, headers };
}

const reply = (status, error, headers) => new Response(JSON.stringify({ error }), {
  status, headers: { ...headers, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});

// constant-time comparison, so the token cannot be guessed from response times
function sameToken(given, expected) {
  if (!expected) return false;
  const a = enc.encode(given), b = enc.encode(expected);
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a[i] || 0) ^ (b[i] || 0);
  return diff === 0;
}

// the rate-limit key only: the IP address is hashed in memory and never stored
async function hashed(text) {
  const d = await crypto.subtle.digest('SHA-256', enc.encode(text));
  return [...new Uint8Array(d)].slice(0, 12).map((x) => x.toString(16).padStart(2, '0')).join('');
}

// the conversation must alternate user / assistant, start and end with the user, and stay small
function problem(body) {
  const m = body && body.messages;
  if (!Array.isArray(m) || m.length === 0) return ['bad', 400];
  if (m.length > MAX_TURNS) return ['long', 413];
  let total = 0;
  for (let i = 0; i < m.length; i++) {
    const t = m[i], role = i % 2 === 0 ? 'user' : 'assistant';
    if (!t || t.role !== role || typeof t.content !== 'string' || !t.content.trim()) return ['bad', 400];
    if (role === 'user' && t.content.length > MAX_QUESTION) return ['question', 413];
    if (role === 'assistant' && t.content.length > MAX_ANSWER) return ['long', 413];
    total += t.content.length;
  }
  if (m[m.length - 1].role !== 'user') return ['bad', 400];
  if (total > MAX_TOTAL) return ['long', 413];
  return null;
}

/* ---------- who asked: an id from the page, and what Cloudflare knows about the request ---------- */
function browserOf(ua) {
  const b = /Edg\//.test(ua) ? 'Edge' : /OPR\//.test(ua) ? 'Opera' : /Firefox\//.test(ua) ? 'Firefox'
    : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : 'Other';
  const os = /iPhone|iPad/.test(ua) ? 'iOS' : /Android/.test(ua) ? 'Android' : /Mac OS X/.test(ua) ? 'macOS'
    : /Windows/.test(ua) ? 'Windows' : /Linux/.test(ua) ? 'Linux' : 'other';
  return b + ' on ' + os;
}
function who(request, body) {
  const cf = request.cf || {};
  const id = (v) => (typeof v === 'string' && ID.test(v) ? v : null);
  return {
    visitor: id(body && body.visitor), session: id(body && body.session),
    country: cf.country || null, city: cf.city || null, network: cf.asOrganization || null,
    browser: browserOf(request.headers.get('User-Agent') || ''),
  };
}
const whoLine = (w, note) => [(w.visitor || 'no id') + (note ? ` (${note})` : ''), [w.city, w.country].filter(Boolean).join(', ') || 'unknown place', w.network, w.browser].filter(Boolean).join(' · ');
const cut = (s, n) => (s && s.length > n ? s.slice(0, n - 1) + '…' : s || '');

/* ---------- Telegram: plain text, so the model's text needs no escaping ---------- */
async function notify(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) { console.log('telegram not set'); return; }
  try {
    const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text: cut(text, 4000), disable_web_page_preview: true }),
    });
    // status and Telegram's short error text only: never the message
    console.log('telegram', r.status, r.ok ? '' : ((await r.json().catch(() => ({}))).description || ''));
  } catch (e) { console.log('telegram failed', e && e.message); }
}

/* ---------- the log ---------- */
async function logChat(env, w, c) {
  if (!env.LOG) return { first: false };
  try {
    const prior = await env.LOG.prepare('SELECT COUNT(*) AS n FROM chats WHERE visitor = ?1').bind(w.visitor).first();
    await env.LOG.prepare(`INSERT INTO chats (ts, visitor, session, country, city, network, browser, turn, question, answer, status, ms,
        input_tokens, cache_read, cache_write, output_tokens, stop) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17)`)
      .bind(new Date().toISOString(), w.visitor, w.session, w.country, w.city, w.network, w.browser, c.turn, c.question, c.answer ?? null,
        c.status, c.ms ?? null, c.usage?.input_tokens ?? null, c.usage?.cache_read_input_tokens ?? null,
        c.usage?.cache_creation_input_tokens ?? null, c.usage?.output_tokens ?? null, c.stop ?? null)
      .run();
    return { first: !prior || !prior.n };
  } catch (e) { console.log('log failed', e && e.message); return { first: false }; }
}

async function recordChat(env, w, c, used) {
  const { first } = await logChat(env, w, c);
  const head = c.status === 200 ? `💬 KYC case chat · question ${c.turn} of this conversation`
    : `⚠️ KYC case chat · status ${c.status}${c.stop ? ' (' + c.stop + ')' : ''}`;
  const lines = [head, 'Who: ' + whoLine(w, first ? 'first question' : ''), '', 'Q: ' + cut(c.question, 600)];
  if (c.answer) lines.push('', 'A: ' + cut(c.answer, 2600));
  const facts = [c.ms != null ? (c.ms / 1000).toFixed(1) + ' s' : null, c.answer ? c.answer.split(/\s+/).filter(Boolean).length + ' words' : null,
    c.usage?.cache_read_input_tokens ? 'prompt from cache' : c.usage?.cache_creation_input_tokens ? 'prompt cache written' : (c.usage ? 'no prompt cache' : null),
    used ? `today ${used}` : null].filter(Boolean);
  if (facts.length) lines.push('', facts.join(' · '));
  await notify(env, lines.join('\n'));
}

async function saveEvents(env, w, rows) {
  try {
    let note = null;
    if (env.NOTIFY_VIEWS === '1' && rows.some((r) => r.name === 'view') && w.visitor) {
      const last = await env.LOG.prepare("SELECT MAX(ts) AS last, COUNT(*) AS n FROM events WHERE visitor = ?1 AND name = 'view'").bind(w.visitor).first();
      if (!last || !last.n) note = 'first visit';
      else if (Date.now() - Date.parse(last.last) > VIEW_GAP_MS) note = 'back again, ' + (last.n + 1) + ' visits';
    }
    const ins = env.LOG.prepare('INSERT INTO events (ts, visitor, session, country, city, network, browser, name, target, value) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)');
    await env.LOG.batch(rows.map((r) => ins.bind(r.ts, w.visitor, w.session, w.country, w.city, w.network, w.browser, r.name, r.target, r.value)));
    if (note) {
      const v = rows.find((r) => r.name === 'view');
      await notify(env, `👀 KYC dashboard opened\nWho: ${whoLine(w, note)}${v && v.value ? `\nScreen: ${v.value} px wide, ${v.target || ''} theme` : ''}`);
    }
  } catch (e) { console.log('events failed', e && e.message); }
}

async function events(request, env, ctx, ok, headers) {
  if (!ok) return reply(403, MSG.origin, headers);
  const raw = await request.text();
  if (raw.length > MAX_EVENT_BODY) return reply(413, 'Too many events in one batch.', headers);
  let body;
  try { body = JSON.parse(raw); } catch { return reply(400, MSG.bad, headers); }
  if (!sameToken(String((body && body.token) || ''), env.CHAT_TOKEN || '')) return reply(401, MSG.token, headers);
  if (env.EVENTS) {
    const { success } = await env.EVENTS.limit({ key: await hashed(request.headers.get('CF-Connecting-IP') || 'unknown') });
    if (!success) return reply(429, MSG.minute, headers);
  }
  const now = Date.now(), w = who(request, body);
  const rows = (Array.isArray(body.events) ? body.events.slice(0, MAX_EVENTS) : [])
    .filter((e) => e && EVENT_NAMES.has(e.n))
    .map((e) => ({
      ts: new Date(now - Math.min(Math.max(Number(e.ago) || 0, 0), 3600e3)).toISOString(),
      name: e.n, target: typeof e.g === 'string' ? e.g.slice(0, 120) : null,
      value: typeof e.v === 'number' && Number.isFinite(e.v) ? e.v : null,
    }));
  if (rows.length && env.LOG) ctx.waitUntil(saveEvents(env, w, rows));
  return new Response(null, { status: 204, headers });
}

/* ---------- Anthropic sends server-sent events: pass on only the answer text, and keep it for the log ---------- */
function textStream(upstream, onEnd) {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  (async () => {
    const reader = upstream.getReader();
    const dec = new TextDecoder();
    let buf = '', text = '', stop = null, usage = {};
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let at;
        while ((at = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, at);
          buf = buf.slice(at + 2);
          const data = block.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('');
          if (!data) continue;
          let ev;
          try { ev = JSON.parse(data); } catch { continue; }
          if (ev.type === 'message_start' && ev.message && ev.message.usage) usage = { ...ev.message.usage };
          else if (ev.type === 'content_block_delta' && ev.delta && ev.delta.type === 'text_delta') {
            text += ev.delta.text;
            await writer.write(enc.encode(ev.delta.text));
          } else if (ev.type === 'message_delta') {
            if (ev.usage && ev.usage.output_tokens != null) usage.output_tokens = ev.usage.output_tokens;
            if (ev.delta && ev.delta.stop_reason) stop = ev.delta.stop_reason;
            if (stop === 'max_tokens') await writer.write(enc.encode(' …'));
          } else if (ev.type === 'error') {
            stop = 'error: ' + ((ev.error && ev.error.type) || 'unknown');
            await writer.write(enc.encode('\n\nThe answer stopped because of an error. Try again.'));
          }
        }
      }
    } catch {
      stop = stop || 'interrupted';
      await writer.write(enc.encode('\n\nThe answer stopped. Try again.')).catch(() => {});
    } finally {
      await writer.close().catch(() => {});
      onEnd({ text, stop, usage });
    }
  })();
  return readable;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const { ok, headers } = corsHeaders(request.headers.get('Origin') || '', env);
    if (request.method === 'OPTIONS') return new Response(null, { status: ok ? 204 : 403, headers });
    if (url.pathname === '/events' && request.method === 'POST') return events(request, env, ctx, ok, headers);
    if (url.pathname !== '/chat' || request.method !== 'POST') return reply(404, 'Not found.', headers);
    if (!ok) return reply(403, MSG.origin, headers);
    if (!sameToken(request.headers.get('X-Chat-Token') || '', env.CHAT_TOKEN || '')) return reply(401, MSG.token, headers);

    const raw = await request.text();
    if (raw.length > MAX_BODY) return reply(413, MSG.long, headers);
    let body;
    try { body = JSON.parse(raw); } catch { return reply(400, MSG.bad, headers); }
    const p = problem(body);
    if (p) return reply(p[1], MSG[p[0]], headers);

    const t0 = Date.now(), w = who(request, body);
    const c = { question: body.messages[body.messages.length - 1].content, turn: Math.ceil(body.messages.length / 2) };
    const fail = (status, key, stop, used) => {
      ctx.waitUntil(key === 'minute' ? logChat(env, w, { ...c, status, stop }) : recordChat(env, w, { ...c, status, stop }, used));
      return reply(status, MSG[key], headers);
    };
    if (!env.ANTHROPIC_API_KEY) return fail(503, 'setup', 'no API key');

    // limits: per visitor per minute, then the daily cap (approximate: KV is eventually consistent)
    if (env.PER_VISITOR) {
      const { success } = await env.PER_VISITOR.limit({ key: await hashed(request.headers.get('CF-Connecting-IP') || 'unknown') });
      if (!success) return fail(429, 'minute', 'per-minute limit');
    }
    let used = null;
    if (env.BUDGET) {
      const day = 'day:' + new Date().toISOString().slice(0, 10);
      used = Number(await env.BUDGET.get(day)) || 0;
      if (used >= (Number(env.DAILY_LIMIT) || 100)) return fail(429, 'day', 'daily limit', used);
      used += 1;
      await env.BUDGET.put(day, String(used), { expirationTtl: 3 * 86400 });
    }

    const upstream = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({
        model: env.MODEL || 'claude-opus-5-5',
        max_tokens: Number(env.MAX_TOKENS) || 800,
        stream: true,
        system: [
          { type: 'text', text: RULES },
          { type: 'text', text: CASE_MATERIAL, cache_control: { type: 'ephemeral' } },
        ],
        messages: body.messages.map(({ role, content }) => ({ role, content })),
      }),
    });
    if (!upstream.ok || !upstream.body) {
      console.log('upstream status', upstream.status);
      return fail(502, 'upstream', 'Anthropic status ' + upstream.status, used);
    }
    let finish;
    const ended = new Promise((resolve) => { finish = resolve; });
    ctx.waitUntil(ended.then((r) => recordChat(env, w, { ...c, status: 200, answer: r.text, stop: r.stop, usage: r.usage, ms: Date.now() - t0 }, used)));
    return new Response(textStream(upstream.body, finish), {
      headers: { ...headers, 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
    });
  },

  // daily: delete log rows older than RETENTION_DAYS
  async scheduled(event, env, ctx) {
    if (!env.LOG) return;
    const cutoff = new Date(Date.now() - (Number(env.RETENTION_DAYS) || 90) * 86400e3).toISOString();
    ctx.waitUntil(env.LOG.batch([
      env.LOG.prepare('DELETE FROM chats WHERE ts < ?1').bind(cutoff),
      env.LOG.prepare('DELETE FROM events WHERE ts < ?1').bind(cutoff),
    ]));
  },
};
