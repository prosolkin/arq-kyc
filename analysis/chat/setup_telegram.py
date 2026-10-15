"""Connect the chat proxy to a Telegram bot: find your chat id, send a test message, and store both as Worker secrets.

Before you run it:
1. In Telegram, open @BotFather, send /newbot and follow the steps. Copy the token that it gives you.
2. Open your new bot and send it any message, for example "hi".

Then, from the project root:
    python3 -I analysis/chat/setup_telegram.py

The script reads the token without echo and gives it straight to `wrangler secret put`. It writes no file.
"""

import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker")


def api(token, method, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Telegram refused the request ({e.code}). Check the token and try again.")


def put_secret(name, value):
    r = subprocess.run(["npx", "--no-install", "wrangler", "secret", "put", name], cwd=WORKER,
                       input=value, text=True, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"wrangler could not set {name}:\n{r.stderr or r.stdout}")
    print(f"set {name}")


def main():
    token = getpass.getpass("Bot token from @BotFather (hidden): ").strip()
    if ":" not in token:
        sys.exit("That does not look like a bot token. It has the form 123456:ABC-...")
    me = api(token, "getMe")["result"]
    print(f"bot: @{me.get('username')}")
    chats = {}
    for u in api(token, "getUpdates").get("result", []):
        m = u.get("message") or u.get("edited_message") or {}
        c = m.get("chat") or {}
        if c.get("type") == "private":
            chats[c["id"]] = c
    if not chats:
        sys.exit(f"No message found. Open @{me.get('username')} in Telegram, send it any message, and run this again.")
    chat = list(chats.values())[-1]
    name = " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) or chat.get("username") or "?"
    if input(f"Send notifications to {name} (chat {chat['id']})? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        sys.exit("Stopped. Nothing was changed.")
    api(token, "sendMessage", {"chat_id": chat["id"],
                               "text": "KYC case chat: notifications are on. You get a message for each question, "
                                       "and when someone opens the dashboard."})
    print("test message sent")
    put_secret("TELEGRAM_BOT_TOKEN", token)
    put_secret("TELEGRAM_CHAT_ID", str(chat["id"]))
    print("Done. The Worker uses the new secrets at once; no deploy is necessary.")


if __name__ == "__main__":
    main()
