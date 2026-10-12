import json
import re

_JSONLD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
IN_STOCK = ("instock", "limitedavailability", "onlineonly")


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def from_jsonld(html):
    """Price and availability from schema.org Product/Offer data, if the page has it."""
    for m in _JSONLD.finditer(html):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for n in _walk(data):
            if "price" in n and ("priceCurrency" in n or n.get("@type") == "Offer"):
                avail = str(n.get("availability", "")).rsplit("/", 1)[-1].lower()
                return {"price": str(n["price"]), "currency": n.get("priceCurrency", ""),
                        "available": (avail in IN_STOCK) if avail else None}
    return None


def from_regex(html, price_regex):
    """Fallback: the first capture group of a regex you wrote for this shop."""
    m = re.search(price_regex, html, re.S)
    return {"price": m.group(1).strip(), "currency": "", "available": None} if m else None


def extract(html, price_regex=None):
    return from_jsonld(html) or (from_regex(html, price_regex) if price_regex else None)
