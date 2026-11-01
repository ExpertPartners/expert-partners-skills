"""Public page sweep through the Firecrawl API.

Targets are names or URLs. A name is searched, then each result is scraped. A
URL is scraped directly. Only pages that need no login are saved, each with its
address and the date it was fetched. The API key is read from the
FIRECRAWL_API_KEY environment variable when the sweep runs and is never saved.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from evidence import Hunt, now_iso, slug

FIRECRAWL_BASE = "https://api.firecrawl.dev/v2"
KEY_VARIABLE = "FIRECRAWL_API_KEY"

LOGIN_PATH = re.compile(
    r"(^|/)(log-?in|sign-?in|signin|sign_in|auth|sso|oauth2?|session/new|account/login|users/sign_in)(/|$)",
    re.IGNORECASE,
)


class SweepError(RuntimeError):
    """The sweep or one of its requests failed."""


class FirecrawlClient:
    """Minimal Firecrawl client for search and scrape."""

    def __init__(self, api_key: str | None = None, base_url: str = FIRECRAWL_BASE,
                 timeout: float = 90, opener=None):
        key = api_key or os.environ.get(KEY_VARIABLE, "")
        if not key.strip():
            raise SweepError(f"{KEY_VARIABLE} is not set. Load it from 1Password into the environment for this run.")
        self._key = key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._open = opener or urllib.request.urlopen

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._open(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raise SweepError(f"Firecrawl {path} returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SweepError(f"Firecrawl {path} failed: {exc.__class__.__name__}") from None
        if body.get("success") is False:
            raise SweepError(f"Firecrawl {path} reported failure: {str(body.get('error') or '')[:200]}")
        return body

    def search(self, query: str, limit: int = 5) -> list[dict]:
        data = self._post("search", {"query": query, "limit": limit}).get("data") or []
        if isinstance(data, dict):
            data = data.get("web") or []
        return [item for item in data if isinstance(item, dict) and item.get("url")]

    def scrape(self, url: str) -> dict:
        body = self._post("scrape", {"url": url, "formats": ["markdown"], "onlyMainContent": True})
        return body.get("data") or {}


def is_url(target: str) -> bool:
    parsed = urlparse(target.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def host_blocked(url: str, blocked: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == b or host.endswith("." + b) for b in (d.lower().strip(".") for d in blocked if d))


def login_wall(status: int | None, final_url: str, markdown: str) -> str | None:
    """Return why a page looks like it needs a login, or None."""
    if status in (401, 403, 407):
        return f"HTTP {status}, the page needs access we do not have"
    if LOGIN_PATH.search(urlparse(final_url).path or ""):
        return "the page sent us to a login page"
    text = markdown.lower()
    if len(text) < 4000 and "password" in text and re.search(r"\b(log ?in|sign ?in)\b", text):
        return "the page is a login form"
    return None


def _page_markdown(title: str, url: str, requested: str, fetched_at: str, body: str) -> str:
    header = [f"# {title or url}", "",
              f"Address: {url}"]
    if requested != url:
        header.append(f"Requested address: {requested}")
    header += [f"Fetched: {fetched_at}", "Fetched through: Firecrawl, public access, no login", "", "---", ""]
    return "\n".join(header) + body.strip() + "\n"


def sweep(hunt: Hunt, targets: list[str], client=None, results_per_name: int = 5,
          max_pages: int = 25, blocked_domains: list[str] | None = None) -> list[dict]:
    """Sweep each target and record one route per target."""
    blocked = list(blocked_domains or [])
    if client is None:
        try:
            client = FirecrawlClient()
        except SweepError as exc:
            return [hunt.record_route({"route": "public page sweep", "target": t, "status": "failed",
                                       "problems": [str(exc)], "missing": ["Public pages for this target"]})
                    for t in targets]
    out_dir = hunt.fresh_dir("sweep/run")
    pages_dir = out_dir / "pages"
    pages_dir.mkdir()
    seen: set[str] = set()
    saved_total = 0
    index: list[dict] = []
    records = []
    for target in targets:
        target = target.strip()
        method = "scrape" if is_url(target) else "search then scrape"
        route = {"route": "public page sweep", "target": target, "method": method}
        found, missing, problems, evidence, text_files = [], [], [], [], []
        try:
            if is_url(target):
                candidates = [{"url": target}]
            else:
                candidates = client.search(target, limit=results_per_name)
                found.append(f"search returned {len(candidates)} results")
        except SweepError as exc:
            candidates = []
            problems.append(str(exc))
        saved = 0
        for candidate in candidates:
            url = candidate["url"]
            if url in seen:
                continue
            seen.add(url)
            if host_blocked(url, blocked):
                missing.append(f"{url} was skipped, its domain is on the blocked list")
                continue
            if saved_total >= max_pages:
                missing.append(f"{url} was not fetched, the {max_pages} page cap was reached")
                continue
            try:
                data = client.scrape(url)
            except SweepError as exc:
                problems.append(f"{url}: {exc}")
                continue
            meta = data.get("metadata") or {}
            status = meta.get("statusCode")
            final_url = meta.get("url") or meta.get("sourceURL") or url
            markdown = data.get("markdown") or ""
            wall = login_wall(status, final_url, markdown)
            if wall:
                missing.append(f"{url} was not saved, {wall}")
                continue
            if isinstance(status, int) and status >= 400:
                missing.append(f"{url} returned HTTP {status}")
                continue
            if not markdown.strip():
                missing.append(f"{url} returned no readable text")
                continue
            fetched_at = now_iso()
            saved_total += 1
            saved += 1
            title = meta.get("title") or candidate.get("title") or ""
            name = f"{saved_total:03d}-{slug(urlparse(final_url).netloc + urlparse(final_url).path)}.md"
            page = hunt.write_text(pages_dir / name, _page_markdown(title, final_url, url, fetched_at, markdown))
            evidence.append(hunt.rel(page))
            text_files.append(hunt.rel(page))
            index.append({"target": target, "requested": url, "address": final_url, "title": title,
                          "fetched_at": fetched_at, "status": status, "file": hunt.rel(page)})
        found.append(f"{saved} public pages saved")
        if is_url(target) and not saved and not problems and not missing:
            missing.append(f"{target} gave nothing to save")
        if not candidates and not problems:
            missing.append("no public results for this name")
        status = "found" if saved else ("failed" if problems else "nothing found")
        route.update(status=status, found=found, missing=missing, problems=problems,
                     evidence=evidence, text_files=text_files, output_dir=hunt.rel(out_dir))
        records.append(hunt.record_route(route))
    hunt.write_json(out_dir / "pages.json", index)
    return records
