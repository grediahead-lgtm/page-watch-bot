"""Polite fetching: robots.txt is obeyed, size and time are limited, private addresses are refused."""
import ipaddress
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "page-watch-bot/0.1 (+personal price monitoring)"
MAX_BYTES = 2 * 1024 * 1024


class Refused(Exception):
    pass


def ssl_context():
    for p in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    """Every redirect target goes through the same address check as the first URL."""

    def __init__(self, allow_private):
        self.allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            check_url(newurl, self.allow_private)
        except Refused as e:
            raise urllib.error.HTTPError(newurl, code, "redirect refused: %s" % e, headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def default_opener(allow_private=False):
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context()), _SafeRedirects(allow_private))


def check_url(url, allow_private=False):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise Refused("only http(s) urls are allowed: %s" % url)
    if not allow_private:
        for info in socket.getaddrinfo(p.hostname, p.port or 80, type=socket.SOCK_STREAM):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise Refused("refusing a private/local address: %s" % p.hostname)
    return p


def allowed_by_robots(url, opener=None, timeout=10):
    p = urllib.parse.urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    robots_url = "%s://%s/robots.txt" % (p.scheme, p.netloc)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": UA})
        with (opener or urllib.request.build_opener()).open(req, timeout=timeout) as r:
            rp.parse(r.read(MAX_BYTES).decode("utf-8", "replace").splitlines())
    except Exception:  # no readable robots.txt: robots rules do not forbid anything
        return True
    return rp.can_fetch(UA, url)


def fetch(url, allow_private=False, opener=None, timeout=15):
    check_url(url, allow_private)
    opener = opener or default_opener(allow_private)
    if not allowed_by_robots(url, opener, timeout):
        raise Refused("robots.txt does not allow this page: %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "uk,ru;q=0.8,en;q=0.5"})
    with opener.open(req, timeout=timeout) as r:
        data = r.read(MAX_BYTES + 1)
        charset = r.headers.get_content_charset() or "utf-8"
    if len(data) > MAX_BYTES:
        raise Refused("page is larger than %d MB" % (MAX_BYTES // 1024 // 1024))
    return data.decode(charset, "replace")
