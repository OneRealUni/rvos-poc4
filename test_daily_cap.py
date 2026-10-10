"""
Tests for the daily cap on /analyse (DEMO_DAILY_CAP).

The cap counts analyses started per UTC day inside one server process. On a
serverless host each instance counts separately and forgets on restart, so it
is best-effort: the spend limit set with Anthropic is the real ceiling. Like
test_app.py these need no API key or NDA files; build_graph is a fake.
"""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

import app as app_module

STATE = {
    "extracted": {"claim": "A claim.", "method": "A method.", "result": "A result.", "keywords": ["one"]},
    "related": [{"title": "Paper A", "year": 2020, "id": "https://openalex.org/W1", "abstract": "Has one."}],
    "verdict": "Overlaps with [1].",
}


class FakeGraph:
    def invoke(self, state):
        return STATE


@pytest.fixture(autouse=True)
def fresh_counter(monkeypatch):
    monkeypatch.setitem(app_module._usage, "day", None)
    monkeypatch.setitem(app_module._usage, "count", 0)
    monkeypatch.delenv("DEMO_DAILY_CAP", raising=False)
    monkeypatch.delenv("DEMO_ACCESS_CODE", raising=False)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "build_graph", lambda: FakeGraph())
    return TestClient(app_module.app)


def run(client, name="paper.txt", data=b"Some paper text.", headers=None):
    return client.post("/analyse", files={"file": (name, data)}, headers=headers or {})


def test_without_a_cap_there_is_no_limit(client):
    assert all(run(client).status_code == 200 for _ in range(10))


def test_an_empty_cap_means_no_limit(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "")
    assert all(run(client).status_code == 200 for _ in range(3))


def test_the_run_after_the_cap_is_429_with_a_plain_message(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "2")
    assert [run(client).status_code for _ in range(2)] == [200, 200]
    r = run(client)
    assert r.status_code == 429
    assert "daily limit" in r.json()["detail"].lower()


def test_a_refused_request_is_not_counted(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "1")
    monkeypatch.setenv("DEMO_ACCESS_CODE", "test-code-123")
    for _ in range(3):
        assert run(client, headers={"X-Access-Code": "wrong-guess"}).status_code == 401
    assert run(client, headers={"X-Access-Code": "test-code-123"}).status_code == 200
    assert run(client, headers={"X-Access-Code": "test-code-123"}).status_code == 429


def test_a_bad_file_is_not_counted(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "1")
    assert run(client, name="paper.rtf", data=b"some text").status_code == 400
    assert run(client).status_code == 200
    assert run(client).status_code == 429


def test_a_request_over_the_cap_never_loads_the_paper(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "0")

    def must_not_run(path):
        raise AssertionError("paper loaded for a request over the cap")

    monkeypatch.setattr(app_module, "load_paper_text", must_not_run)
    assert run(client).status_code == 429


def test_the_count_starts_again_on_the_next_utc_day(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "1")
    monkeypatch.setattr(app_module, "_today", lambda: dt.date(2026, 10, 10))
    assert run(client).status_code == 200
    assert run(client).status_code == 429
    monkeypatch.setattr(app_module, "_today", lambda: dt.date(2026, 10, 11))
    assert run(client).status_code == 200


def test_a_cap_that_is_not_a_number_blocks_instead_of_switching_the_cap_off(client, monkeypatch):
    for bad in ("abc", "-1", "2.5"):
        monkeypatch.setenv("DEMO_DAILY_CAP", bad)
        assert run(client).status_code == 429


def test_the_page_and_the_sample_routes_ignore_the_cap(client, monkeypatch):
    monkeypatch.setenv("DEMO_DAILY_CAP", "0")
    assert client.get("/").status_code == 200
    assert client.get("/sample/recorded").status_code in (200, 404)
    assert client.get("/sample/paper").status_code in (200, 404)
