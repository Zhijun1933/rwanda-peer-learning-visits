"""Polite HTTP fetching: robots.txt, per-domain delays, a do-not-crawl list."""

import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests

from . import config


def blocked_by_policy(url: str, do_not_crawl: list[str]) -> bool:
    host = urlsplit(url).netloc.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in do_not_crawl)


class PoliteFetcher:
    def __init__(self, cfg: dict | None = None, session: requests.Session | None = None):
        cfg = cfg or config.sources()
        self.user_agent = cfg["user_agent"]
        self.min_delay = float(cfg.get("min_delay_seconds", 5))
        self.timeout = float(cfg.get("timeout_seconds", 30))
        self.do_not_crawl = cfg.get("do_not_crawl", [])
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = self.user_agent
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}

    # robots.txt -----------------------------------------------------------
    def _robots_for(self, url: str):
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = self.session.get(base + "/robots.txt", timeout=self.timeout)
                if resp.status_code >= 400:
                    rp = None  # no robots.txt: crawling allowed by convention
                else:
                    rp.parse(resp.text.splitlines())
            except requests.RequestException:
                rp = None
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        if blocked_by_policy(url, self.do_not_crawl):
            return False
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def sitemaps(self, base_url: str) -> list[str]:
        rp = self._robots_for(base_url)
        return list(rp.site_maps() or []) if rp else []

    # rate limiting --------------------------------------------------------
    def _wait(self, url: str):
        host = urlsplit(url).netloc
        rp = self._robots_for(url)
        delay = self.min_delay
        if rp is not None:
            crawl_delay = rp.crawl_delay(self.user_agent)
            if crawl_delay:
                delay = max(delay, float(crawl_delay))
        elapsed = time.monotonic() - self._last_hit.get(host, 0.0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, check_robots: bool = True) -> requests.Response | None:
        """Fetch a URL, or return None if policy or robots.txt forbids it."""
        if check_robots and not self.allowed(url):
            return None
        self._wait(url)
        return self.session.get(url, timeout=self.timeout)
