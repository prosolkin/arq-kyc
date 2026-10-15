"""Read the hosted dashboard's log (the D1 database kyc-case-log) in the terminal. Times are local.

From the project root:
    python3 -I analysis/chat/show_log.py                     # summary: visitors, views, questions, tabs, clicks
    python3 -I analysis/chat/show_log.py chats 20            # the last 20 questions with their full answers
    python3 -I analysis/chat/show_log.py events 50           # the last 50 page events
    python3 -I analysis/chat/show_log.py visitor v-1a2b3c4d5e  # one visitor's timeline
"""

import datetime as dt
import json
import os
import re
import subprocess
import sys

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker")
TABS = {"quick": "Quick review", "drivers": "Why it fell", "plan": "What to do", "gain": "What we gain",
        "summary": "Full summary", "measurement": "Measurement", "incidents": "Incidents", "hypotheses": "Hypotheses & tests",
        "operating": "Operating model", "design": "Target design", "vendor": "Vendor research", "reference": "Reference"}


def query(sql):
    """Run one or more statements; returns a list of result lists, one per statement."""
    r = subprocess.run(["npx", "--no-install", "wrangler", "d1", "execute", "kyc-case-log", "--remote", "--json", "--command", sql],
                       cwd=WORKER, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr or r.stdout)
    return [x.get("results", []) for x in json.loads(r.stdout)]


def local(ts):
    if not ts:
        return ""
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%b %d %H:%M")


def table(rows, cols, title=None):
    if title:
        print(f"\n{title}")
    if not rows:
        print("  (none yet)")
        return
    cells = [[str(r.get(c) if r.get(c) is not None else "") for c in cols] for r in rows]
    w = [max(len(c), *(len(x[i]) for x in cells)) for i, c in enumerate(cols)]
    print("  " + "  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    for x in cells:
        print("  " + "  ".join(v.ljust(w[i]) for i, v in enumerate(x)))


def summary():
    tot, visitors, days, tabs, clicks, health = query("""
SELECT (SELECT COUNT(DISTINCT visitor) FROM events) AS visitors, (SELECT COUNT(DISTINCT session) FROM events WHERE name = 'view') AS page_views,
       (SELECT COUNT(*) FROM chats WHERE status = 200) AS answers, (SELECT COUNT(*) FROM chats WHERE status <> 200) AS failed,
       (SELECT MIN(ts) FROM events) AS since;
WITH t AS (SELECT visitor, session, MAX(value) AS s FROM events WHERE name = 'leave' GROUP BY visitor, session)
SELECT e.visitor, MIN(e.ts) AS first, MAX(e.ts) AS last, MAX(e.city) AS city, MAX(e.country) AS country, MAX(e.network) AS network,
       MAX(e.browser) AS browser, COUNT(DISTINCT CASE WHEN e.name = 'view' THEN e.session END) AS views, SUM(e.name = 'tab') AS tabs,
       SUM(e.name IN ('click', 'chip', 'details', 'print')) AS clicks, (SELECT COUNT(*) FROM chats c WHERE c.visitor = e.visitor) AS questions,
       (SELECT SUM(s) FROM t WHERE t.visitor = e.visitor) AS seconds
FROM events e GROUP BY e.visitor ORDER BY last DESC LIMIT 30;
SELECT substr(ts, 1, 10) AS day, COUNT(DISTINCT visitor) AS visitors, COUNT(DISTINCT CASE WHEN name = 'view' THEN session END) AS views,
       SUM(name = 'tab') AS tabs, SUM(name IN ('click', 'chip', 'details', 'print')) AS clicks,
       (SELECT COUNT(*) FROM chats c WHERE substr(c.ts, 1, 10) = substr(events.ts, 1, 10)) AS questions
FROM events GROUP BY day ORDER BY day DESC LIMIT 14;
SELECT target AS tab, COUNT(*) AS opened, COUNT(DISTINCT visitor) AS visitors FROM events WHERE name = 'tab' GROUP BY target ORDER BY opened DESC;
SELECT name AS kind, target AS what, COUNT(*) AS n FROM events WHERE name IN ('click', 'chip', 'details', 'print', 'chat_open')
GROUP BY name, target ORDER BY n DESC LIMIT 25;
SELECT status, COALESCE(stop, '') AS stop, COUNT(*) AS n, ROUND(AVG(ms) / 1000.0, 1) AS avg_s, SUM(cache_read > 0) AS from_cache,
       SUM(input_tokens + COALESCE(cache_read, 0) + COALESCE(cache_write, 0)) AS input_tok, SUM(output_tokens) AS output_tok
FROM chats GROUP BY status, stop ORDER BY n DESC;
""")
    t = tot[0] if tot else {}
    print(f"since {local(t.get('since')) or '-'}: {t.get('visitors', 0)} visitors, {t.get('page_views', 0)} page views, "
          f"{t.get('answers', 0)} answered questions, {t.get('failed', 0)} failed")
    for v in visitors:
        v["first"], v["last"] = local(v["first"]), local(v["last"])
        v["place"] = ", ".join(x for x in (v.pop("city"), v.pop("country")) if x)
        v["time"] = f"{round((v.pop('seconds') or 0) / 60, 1)} min"
    table(visitors, ["visitor", "first", "last", "place", "network", "browser", "views", "tabs", "clicks", "questions", "time"], "Visitors")
    table(days, ["day", "visitors", "views", "tabs", "clicks", "questions"], "By day (UTC)")
    for r in tabs:
        r["tab"] = TABS.get(r["tab"], r["tab"])
    table(tabs, ["tab", "opened", "visitors"], "Tabs opened")
    table(clicks, ["kind", "what", "n"], "Clicks")
    table(health, ["status", "stop", "n", "avg_s", "from_cache", "input_tok", "output_tok"], "Chat health")


def chats(n):
    rows = query(f"SELECT * FROM chats ORDER BY id DESC LIMIT {int(n)}")[0]
    for r in reversed(rows):
        place = ", ".join(x for x in (r["city"], r["country"]) if x)
        print(f"\n— {local(r['ts'])} · {r['visitor']} · {place} · {r['network'] or ''} · {r['browser'] or ''}")
        print(f"  status {r['status']} {r['stop'] or ''} · {round((r['ms'] or 0) / 1000, 1)} s · question {r['turn']} · "
              f"tokens in {r['input_tokens']} (cache read {r['cache_read']}, write {r['cache_write']}), out {r['output_tokens']}")
        print(f"Q: {r['question']}")
        if r["answer"]:
            print("A: " + r["answer"].strip().replace("\n", "\n   "))


def events(n):
    rows = query(f"SELECT ts, visitor, name, target, value, city, country FROM events ORDER BY id DESC LIMIT {int(n)}")[0]
    for r in rows:
        r["ts"] = local(r["ts"])
        if r["name"] == "tab":
            r["target"] = TABS.get(r["target"], r["target"])
    table(list(reversed(rows)), ["ts", "visitor", "name", "target", "value", "city", "country"], f"Last {n} events")


def visitor(v):
    if not re.fullmatch(r"v-[a-z0-9]{6,20}", v):
        sys.exit("A visitor id looks like v-1a2b3c4d5e.")
    ev, ch = query(f"SELECT ts, session, name, target, value FROM events WHERE visitor = '{v}' ORDER BY ts;"
                   f"SELECT ts, session, status, question FROM chats WHERE visitor = '{v}' ORDER BY ts;")
    rows = [{"ts": r["ts"], "session": r["session"], "what": r["name"] + (": " + TABS.get(r["target"] or "", r["target"] or "") if r["target"] else "")
             + (f" ({r['value']:g})" if r["value"] is not None else "")} for r in ev]
    rows += [{"ts": r["ts"], "session": r["session"], "what": f"asked ({r['status']}): {r['question'][:90]}"} for r in ch]
    rows.sort(key=lambda r: r["ts"])
    for r in rows:
        r["ts"] = local(r["ts"])
    table(rows, ["ts", "session", "what"], f"Timeline of {v}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "summary":
        summary()
    elif cmd == "chats":
        chats(arg or 10)
    elif cmd == "events":
        events(arg or 40)
    elif cmd == "visitor" and arg:
        visitor(arg)
    else:
        sys.exit(__doc__)
