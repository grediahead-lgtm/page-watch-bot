"""Polite fetching: robots.txt is obeyed, size and time are limited, private addresses are refused."""
import ipaddress
import socket
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "page-watch-bot/0.1 (+personal price monitoring)"
MAX_BYTES = 2 * 1024 * 1024


class Refused(Exception):
    pass


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
    if not allowed_by_robots(url, opener, timeout):
        raise Refused("robots.txt does not allow this page: %s" % url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "uk,ru;q=0.8,en;q=0.5"})
    with (opener or urllib.request.build_opener()).open(req, timeout=timeout) as r:
        data = r.read(MAX_BYTES + 1)
        charset = r.headers.get_content_charset() or "utf-8"
    if len(data) > MAX_BYTES:
        raise Refused("page is larger than %d MB" % (MAX_BYTES // 1024 // 1024))
    return data.decode(charset, "replace")
