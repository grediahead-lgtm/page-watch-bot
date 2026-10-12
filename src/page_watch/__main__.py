import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

from .watch import load_state, run_once, save_state


def send_telegram(token, chat_id, text):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        if not json.loads(r.read()).get("ok"):
            raise RuntimeError("telegram refused the message")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="page_watch", description="Check watched pages once; run it from cron.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--state", default="state.json")
    ap.add_argument("--dry-run", action="store_true", help="print messages instead of sending them")
    args = ap.parse_args(argv)
    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    items = cfg["items"]
    if len(items) > 50:
        raise ValueError("at most 50 pages per config; be polite to the shops")
    state = load_state(args.state)
    messages, errors = run_once(items, state, allow_private=bool(cfg.get("allow_private")))
    save_state(args.state, state)
    text = "\n\n".join(messages + (["Problems:\n" + "\n".join(errors)] if errors else []))
    if text:
        token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), cfg.get("chat_id")
        if args.dry_run or not token or not chat:
            print(text)
        else:
            send_telegram(token, chat, text)
    print(json.dumps({"changes": len(messages), "problems": len(errors)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
