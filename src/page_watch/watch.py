import json
import os

from .extract import extract
from .fetch import Refused, fetch


def load_state(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def describe(old, new):
    changes = []
    if old.get("price") != new.get("price"):
        changes.append("price %s -> %s %s" % (old.get("price"), new.get("price"), new.get("currency", "")))
    if old.get("available") is not None and new.get("available") is not None and old["available"] != new["available"]:
        changes.append("now %s" % ("in stock" if new["available"] else "out of stock"))
    return ", ".join(changes)


def run_once(items, state, fetcher=fetch, allow_private=False):
    """items: [{name, url, price_regex?}]. Returns (messages, errors); mutates state.
    The first time a page is seen it is only remembered, no message."""
    messages, errors = [], []
    for it in items:
        try:
            html = fetcher(it["url"], allow_private=allow_private)
        except Refused as e:
            errors.append("%s: refused (%s)" % (it["name"], e))
            continue
        except Exception as e:
            errors.append("%s: could not load (%s)" % (it["name"], type(e).__name__))
            continue
        new = extract(html, it.get("price_regex"))
        if not new:
            errors.append("%s: price not found on the page" % it["name"])
            continue
        old = state.get(it["url"])
        if old:
            diff = describe(old, new)
            if diff:
                messages.append("%s: %s\n%s" % (it["name"], diff, it["url"]))
        state[it["url"]] = new
    return messages, errors
