// Proxy for the dashboard's "Ask about this case" chat.
// Holds the Anthropic key, checks origin, access token and limits, and streams Claude's answer as plain text.
import RULES from '../rules.md';
import CASE_MATERIAL from '../case-material.md';

const enc = new TextEncoder();
const MAX_TURNS = 12;        // user and assistant turns together
const MAX_QUESTION = 1500;   // characters in one question
const MAX_ANSWER = 6000;     // characters in one earlier answer sent back as context
const MAX_TOTAL = 24000;     // characters in the whole conversation
const MAX_BODY = 40000;      // bytes in the request body

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

// Anthropic sends server-sent events; pass on only the answer text
function textStream(upstream) {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  (async () => {
    const reader = upstream.getReader();
    const dec = new TextDecoder();
    let buf = '';
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let cut;
        while ((cut = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, cut);
          buf = buf.slice(cut + 2);
          const data = block.split('\n').filter((l) => l.startsWith('data:')).map((l) => l.slice(5).trim()).join('');
          if (!data) continue;
          let ev;
          try { ev = JSON.parse(data); } catch { continue; }
          if (ev.type === 'content_block_delta' && ev.delta && ev.delta.type === 'text_delta') await writer.write(enc.encode(ev.delta.text));
          else if (ev.type === 'message_delta' && ev.delta && ev.delta.stop_reason === 'max_tokens') await writer.write(enc.encode(' …'));
          else if (ev.type === 'error') await writer.write(enc.encode('\n\nThe answer stopped because of an error. Try again.'));
        }
      }
    } catch {
      await writer.write(enc.encode('\n\nThe answer stopped. Try again.')).catch(() => {});
    } finally {
      await writer.close().catch(() => {});
    }
  })();
  return readable;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { ok, headers } = corsHeaders(request.headers.get('Origin') || '', env);
    if (request.method === 'OPTIONS') return new Response(null, { status: ok ? 204 : 403, headers });
    if (url.pathname !== '/chat' || request.method !== 'POST') return reply(404, 'Not found.', headers);
    if (!ok) return reply(403, MSG.origin, headers);
    if (!sameToken(request.headers.get('X-Chat-Token') || '', env.CHAT_TOKEN || '')) return reply(401, MSG.token, headers);

    const raw = await request.text();
    if (raw.length > MAX_BODY) return reply(413, MSG.long, headers);
    let body;
    try { body = JSON.parse(raw); } catch { return reply(400, MSG.bad, headers); }
    const p = problem(body);
    if (p) return reply(p[1], MSG[p[0]], headers);
    if (!env.ANTHROPIC_API_KEY) return reply(503, MSG.setup, headers);

    // limits: per visitor per minute, then the daily cap (approximate: KV is eventually consistent)
    if (env.PER_VISITOR) {
      const key = await hashed(request.headers.get('CF-Connecting-IP') || 'unknown');
      const { success } = await env.PER_VISITOR.limit({ key });
      if (!success) return reply(429, MSG.minute, headers);
    }
    if (env.BUDGET) {
      const day = 'day:' + new Date().toISOString().slice(0, 10);
      const used = Number(await env.BUDGET.get(day)) || 0;
      if (used >= (Number(env.DAILY_LIMIT) || 100)) return reply(429, MSG.day, headers);
      await env.BUDGET.put(day, String(used + 1), { expirationTtl: 3 * 86400 });
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
      console.log('upstream status', upstream.status); // status only: no question text is logged
      return reply(502, MSG.upstream, headers);
    }
    return new Response(textStream(upstream.body), {
      headers: { ...headers, 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
    });
  },
};
