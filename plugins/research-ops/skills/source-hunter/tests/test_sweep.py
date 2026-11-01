import io
import json
import urllib.error

import pytest

from evidence import Hunt
from sweep import FirecrawlClient, SweepError, login_wall, sweep


class FakeClient:
    def __init__(self, pages, results=None, fail_search=False):
        self.pages = pages
        self.results = results or {}
        self.fail_search = fail_search
        self.scraped = []
        self.searched = []

    def search(self, query, limit=5):
        self.searched.append((query, limit))
        if self.fail_search:
            raise SweepError("Firecrawl search returned HTTP 402")
        return self.results.get(query, [])[:limit]

    def scrape(self, url):
        self.scraped.append(url)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return page


def _page(markdown, status=200, url=None, title="A page"):
    meta = {"statusCode": status, "title": title}
    if url:
        meta["url"] = url
    return {"markdown": markdown, "metadata": meta}


PAGES = {
    "https://example.org/course/outline": _page("Public outline of the advisor lesson.", title="Outline"),
    "https://example.org/blog/advisor": _page("A blog post that names the shadow board advisor."),
    "https://example.org/members": _page("Sign in\n\nEmail\n\nPassword\n\nLog in", status=200),
    "https://example.org/private": _page("", status=403),
    "https://example.org/redirects": _page("Welcome back", url="https://example.org/users/sign_in"),
    "https://example.org/gone": _page("Not found", status=404),
    "https://blocked.example.net/page": _page("should never be fetched"),
    "https://example.org/broken": SweepError("Firecrawl scrape returned HTTP 500"),
}


def test_sweep_saves_public_pages_with_address_and_date(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    client = FakeClient(PAGES, results={"shadow board advisor": [
        {"url": "https://example.org/blog/advisor", "title": "Blog"},
        {"url": "https://example.org/members"},
        {"url": "https://blocked.example.net/page"},
        {"url": "https://example.org/course/outline"},
    ]})
    routes = sweep(hunt, ["shadow board advisor", "https://example.org/course/outline", "https://example.org/private",
                          "https://example.org/redirects", "https://example.org/gone", "https://example.org/broken"],
                   client=client, blocked_domains=["example.net"])
    assert [r["status"] for r in routes] == ["found", "nothing found", "nothing found", "nothing found",
                                             "nothing found", "failed"]
    assert "https://blocked.example.net/page" not in client.scraped
    assert client.searched == [("shadow board advisor", 5)]
    first = routes[0]
    assert len(first["evidence"]) == 2
    for rel in first["evidence"]:
        text = (hunt.root / rel).read_text()
        assert "Address: https://example.org/" in text
        assert "Fetched: 20" in text
    joined = " ".join(first["missing"])
    assert "login form" in joined and "blocked list" in joined
    assert "needs access" in routes[2]["missing"][0]
    assert "login page" in routes[3]["missing"][0]
    assert "HTTP 404" in routes[4]["missing"][0]
    assert "HTTP 500" in routes[5]["problems"][0]
    # The outline URL was already saved through the search, so it is not fetched twice.
    assert client.scraped.count("https://example.org/course/outline") == 1
    index = json.loads((hunt.root / first["output_dir"] / "pages.json").read_text())
    assert {p["address"] for p in index} == {"https://example.org/blog/advisor", "https://example.org/course/outline"}


def test_sweep_respects_page_cap(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    client = FakeClient(PAGES)
    routes = sweep(hunt, ["https://example.org/course/outline", "https://example.org/blog/advisor"],
                   client=client, max_pages=1)
    assert routes[0]["status"] == "found"
    assert "page cap" in routes[1]["missing"][0]
    assert client.scraped == ["https://example.org/course/outline"]


def test_search_failure_is_recorded(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    routes = sweep(hunt, ["anything"], client=FakeClient({}, fail_search=True))
    assert routes[0]["status"] == "failed"
    assert "402" in routes[0]["problems"][0]


def test_missing_key_is_a_failed_route_without_network(tmp_path, monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    hunt = Hunt(tmp_path / "evidence")
    routes = sweep(hunt, ["https://example.org/course/outline"])
    assert routes[0]["status"] == "failed"
    assert "FIRECRAWL_API_KEY is not set" in routes[0]["problems"][0]


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_client_reads_key_at_run_time_and_posts_to_firecrawl(monkeypatch):
    calls = []

    def opener(request, timeout):
        calls.append(request)
        body = json.loads(request.data)
        if request.full_url.endswith("/search"):
            return FakeResponse(json.dumps({"success": True, "data": {"web": [{"url": "https://example.org/a"}]}}).encode())
        return FakeResponse(json.dumps({"success": True, "data": {"markdown": body["url"], "metadata": {}}}).encode())

    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key-from-env")
    client = FirecrawlClient(opener=opener)
    assert client.search("name", limit=3) == [{"url": "https://example.org/a"}]
    assert client.scrape("https://example.org/a")["markdown"] == "https://example.org/a"
    assert [c.full_url for c in calls] == ["https://api.firecrawl.dev/v2/search", "https://api.firecrawl.dev/v2/scrape"]
    assert calls[0].get_header("Authorization") == "Bearer test-key-from-env"
    assert json.loads(calls[0].data) == {"query": "name", "limit": 3}
    assert json.loads(calls[1].data)["formats"] == ["markdown"]


def test_client_errors_never_include_the_key(monkeypatch):
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setenv("FIRECRAWL_API_KEY", "secret-value-123")
    with pytest.raises(SweepError) as info:
        FirecrawlClient(opener=opener).scrape("https://example.org")
    assert "401" in str(info.value) and "secret-value-123" not in str(info.value)


def test_login_wall_rules():
    assert login_wall(401, "https://x.org/a", "")
    assert login_wall(200, "https://x.org/login", "hi")
    assert login_wall(200, "https://x.org/a", "Log in\nPassword")
    assert login_wall(200, "https://x.org/blog/how-to-login-faster", "An essay") is None
    assert login_wall(200, "https://x.org/a", "Public text") is None


def test_page_cap_counts_every_fetch(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    client = FakeClient(PAGES)
    routes = sweep(hunt, ["https://example.org/members", "https://example.org/gone", "https://example.org/blog/advisor"],
                   client=client, max_pages=2)
    assert client.scraped == ["https://example.org/members", "https://example.org/gone"]
    assert "page cap" in routes[2]["missing"][0]


def test_redirect_to_blocked_domain_is_not_saved(tmp_path):
    hunt = Hunt(tmp_path / "evidence")
    pages = {"https://example.org/hop": _page("Landed somewhere blocked", url="https://www.blocked.example.net/x")}
    routes = sweep(hunt, ["https://example.org/hop"], client=FakeClient(pages), blocked_domains=["blocked.example.net"])
    assert routes[0]["status"] == "nothing found"
    assert "redirected to a blocked domain" in routes[0]["missing"][0]
    assert not list((hunt.root / routes[0]["output_dir"] / "pages").iterdir())


def test_dropped_connection_and_odd_replies_become_sweep_errors(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "k")

    def reset(request, timeout):
        raise ConnectionResetError("reset")

    with pytest.raises(SweepError, match="ConnectionResetError"):
        FirecrawlClient(opener=reset).scrape("https://example.org")

    def odd(request, timeout):
        return FakeResponse(b'["not", "an", "object"]')

    with pytest.raises(SweepError, match="unexpected reply"):
        FirecrawlClient(opener=odd).scrape("https://example.org")
