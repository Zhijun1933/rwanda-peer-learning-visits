from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, status_code=200, text="", content=None):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode()


class FakeSession:
    """Serves canned responses by URL and records every request."""

    def __init__(self, routes: dict[str, FakeResponse]):
        self.routes = routes
        self.headers = {}
        self.requested = []

    def get(self, url, timeout=None):
        self.requested.append(url)
        return self.routes.get(url, FakeResponse(404, "not found"))


@pytest.fixture
def fixtures():
    return FIXTURES


@pytest.fixture
def test_cfg():
    return {
        "user_agent": "test-agent",
        "min_delay_seconds": 0,
        "timeout_seconds": 5,
        "do_not_crawl": ["rci.gov.rw", "cooperation.rw", "facebook.com"],
        "slug_keywords": ["study-tour", "benchmark"],
    }
