import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from page_watch.extract import extract, from_jsonld  # noqa: E402
from page_watch.fetch import Refused, check_url, fetch  # noqa: E402
from page_watch.watch import describe, load_state, run_once, save_state  # noqa: E402


def page(price, avail="InStock"):
    data = {"@context": "https://schema.org", "@type": "Product", "name": "Bed",
            "offers": {"@type": "Offer", "price": price, "priceCurrency": "UAH",
                       "availability": "https://schema.org/" + avail}}
    return '<html><script type="application/ld+json">%s</script></html>' % json.dumps(data)


class ExtractTests(unittest.TestCase):
    def test_jsonld(self):
        self.assertEqual(from_jsonld(page("1250")), {"price": "1250", "currency": "UAH", "available": True})
        self.assertFalse(from_jsonld(page("1250", "OutOfStock"))["available"])

    def test_broken_jsonld_is_skipped(self):
        self.assertIsNone(from_jsonld('<script type="application/ld+json">{oops</script>'))

    def test_regex_fallback(self):
        html = '<span class="price"> 1 250,00 </span>'
        self.assertEqual(extract(html, r'class="price">\s*([0-9 ,.]+)')["price"], "1 250,00")
        self.assertIsNone(extract(html))

    def test_graph_and_list_nesting(self):
        data = {"@graph": [{"@type": "WebSite"}, {"@type": "Product", "offers": [{"@type": "Offer", "price": 5, "priceCurrency": "EUR"}]}]}
        html = '<script type="application/ld+json">%s</script>' % json.dumps(data)
        self.assertEqual(from_jsonld(html)["price"], "5")


class DescribeTests(unittest.TestCase):
    def test_changes(self):
        old = {"price": "100", "available": True}
        self.assertEqual(describe(old, {"price": "100", "available": True}), "")
        self.assertIn("100 -> 90", describe(old, {"price": "90", "currency": "UAH", "available": True}))
        self.assertIn("out of stock", describe(old, {"price": "100", "available": False}))


class RunTests(unittest.TestCase):
    def test_first_seen_is_silent_then_change_is_reported(self):
        html = {"v": page("100")}
        fetcher = lambda url, allow_private=False: html["v"]
        state = {}
        items = [{"name": "Bed", "url": "https://shop.example/bed"}]
        self.assertEqual(run_once(items, state, fetcher), ([], []))
        html["v"] = page("90")
        msgs, errs = run_once(items, state, fetcher)
        self.assertEqual(errs, [])
        self.assertIn("100 -> 90", msgs[0])
        self.assertEqual(run_once(items, state, fetcher), ([], []))  # no repeat

    def test_errors_are_reported_not_raised(self):
        def bad(url, allow_private=False):
            if "robots" in url:
                raise Refused("robots.txt does not allow this page")
            if "boom" in url:
                raise OSError("down")
            return "<html>no price</html>"
        items = [{"name": "a", "url": "https://x/robots"}, {"name": "b", "url": "https://x/boom"}, {"name": "c", "url": "https://x/c"}]
        msgs, errs = run_once(items, {}, bad)
        self.assertEqual(msgs, [])
        self.assertEqual(len(errs), 3)

    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            self.assertEqual(load_state(p), {})
            save_state(p, {"u": {"price": "1"}})
            self.assertEqual(load_state(p)["u"]["price"], "1")


class FetchTests(unittest.TestCase):
    def test_private_and_bad_schemes_refused(self):
        for url in ("file:///etc/passwd", "ftp://x.example/a", "http://127.0.0.1/x", "http://localhost/x", "http://[::1]/x"):
            with self.assertRaises(Refused, msg=url):
                check_url(url)

    def test_local_server_with_robots(self):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/robots.txt":
                    body = b"User-agent: *\nDisallow: /private\n"
                elif self.path == "/private":
                    body = b"secret"
                else:
                    body = page("100").encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % srv.server_port
        try:
            self.assertIn("ld+json", fetch(base + "/p", allow_private=True))
            with self.assertRaises(Refused):
                fetch(base + "/private", allow_private=True)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
