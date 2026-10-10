"""
Tests for the demo web app (app.py): upload a paper, get a Report back.

Like test_loading.py these need no API key or NDA files. build_graph is
replaced with a fake, so the routes, upload handling and error mapping are
tested here and PASS in CI; the reasoning itself stays covered by the live
tests in test_rvos_poc.py.
"""

import json
import os
from pathlib import Path

import pytest
import requests
from docx import Document
from fastapi.testclient import TestClient

import app as app_module
import rvos_poc

FAKE_STATE = {
    "extracted": {
        "claim": "A claim.",
        "method": "A method.",
        "result": "A result.",
        "keywords": ["one", "two"],
    },
    "related": [
        {"title": "Paper A", "year": 2020, "id": "https://openalex.org/W1", "abstract": "Has one."},
        {"title": "Paper B", "year": 2021, "id": "https://openalex.org/W2", "abstract": ""},
    ],
    "verdict": "Overlaps with [1].",
}


class FakeGraph:
    def invoke(self, state):
        self.seen = state
        return FAKE_STATE


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "build_graph", lambda: FakeGraph())
    return TestClient(app_module.app)


def _upload(client, name, data):
    return client.post("/analyse", files={"file": (name, data)})


def test_txt_upload_returns_report(client):
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 200
    body = r.json()
    assert body["claim"] == "A claim."
    assert body["method"] == "A method."
    assert body["result"] == "A result."
    assert body["verdict"] == "Overlaps with [1]."
    assert body["truncated"] is False
    assert "keywords" not in body


def test_related_work_is_numbered_and_flags_missing_abstracts(client):
    body = _upload(client, "paper.txt", b"Some paper text.").json()
    assert body["related"] == [
        {"n": 1, "title": "Paper A", "year": 2020, "url": "https://openalex.org/W1", "has_abstract": True},
        {"n": 2, "title": "Paper B", "year": 2021, "url": "https://openalex.org/W2", "has_abstract": False},
    ]


def test_response_flags_a_paper_longer_than_the_assessed_limit(client, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_PAPER_CHARS", 5)
    assert _upload(client, "paper.txt", b"Some paper text.").json()["truncated"] is True


def test_insufficient_evidence_with_no_related_work_is_a_normal_report(client, monkeypatch):
    empty = {**FAKE_STATE, "related": [], "verdict": "Insufficient evidence to judge."}
    monkeypatch.setattr(app_module, "build_graph", lambda: type("G", (), {"invoke": lambda self, s: empty})())
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 200
    assert r.json()["related"] == []
    assert r.json()["verdict"] == "Insufficient evidence to judge."


def test_related_work_without_any_abstract_is_flagged_not_dropped(client, monkeypatch):
    bare = {**FAKE_STATE, "related": [
        {"title": "A", "year": 2020, "id": "https://openalex.org/W1", "abstract": ""},
        {"title": "B", "year": 2021, "id": "https://openalex.org/W2", "abstract": ""},
    ]}
    monkeypatch.setattr(app_module, "build_graph", lambda: type("G", (), {"invoke": lambda self, s: bare})())
    related = _upload(client, "paper.txt", b"Some paper text.").json()["related"]
    assert [(w["n"], w["has_abstract"]) for w in related] == [(1, False), (2, False)]


def test_docx_upload_is_loaded_and_fed_to_the_pipeline(client, tmp_path, monkeypatch):
    seen = {}

    class Recording(FakeGraph):
        def invoke(self, state):
            seen.update(state)
            return FAKE_STATE

    monkeypatch.setattr(app_module, "build_graph", lambda: Recording())
    path = tmp_path / "paper.docx"
    doc = Document()
    doc.add_paragraph("Docx paragraph text.")
    doc.save(str(path))
    r = _upload(client, "paper.docx", path.read_bytes())
    assert r.status_code == 200
    assert "Docx paragraph text." in seen["paper_text"]


def test_unsupported_type_is_400_with_user_readable_message(client):
    r = _upload(client, "paper.rtf", b"some text")
    assert r.status_code == 400
    detail = r.json()["detail"]
    for ext in (".txt", ".pdf", ".docx"):
        assert ext in detail
    assert "paper.rtf" in detail
    assert "tmp" not in detail.lower()


def test_empty_file_is_400_no_extractable_text(client):
    r = _upload(client, "paper.txt", b"")
    assert r.status_code == 400
    assert "no extractable text" in r.json()["detail"]


def test_loader_crash_is_400_not_500(client, monkeypatch):
    """A library failure inside load_paper_text (e.g. a corrupted or
    password-protected PDF -- see probes P5/P6 in the findings register,
    F2) must read as a bad file, not a server crash."""

    def boom(path):
        raise RuntimeError("pdfminer internals: no /Root object")

    monkeypatch.setattr(app_module, "load_paper_text", boom)
    r = _upload(client, "paper.pdf", b"whatever bytes")
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "corrupted" in detail or "password" in detail
    assert "pdfminer" not in r.text
    assert "/root" not in r.text.lower()


def test_oversized_upload_is_413(client, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_UPLOAD_BYTES", 10)
    r = _upload(client, "paper.txt", b"x" * 11)
    assert r.status_code == 413


def test_upstream_failure_is_502_with_generic_message(client, monkeypatch):
    class Failing:
        def invoke(self, state):
            raise requests.ConnectionError("secret-host:1234 refused")

    monkeypatch.setattr(app_module, "build_graph", lambda: Failing())
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 502
    assert "secret-host" not in r.text


def test_unexpected_failure_is_500_with_generic_message(client, monkeypatch):
    class Broken:
        def invoke(self, state):
            raise RuntimeError("internal detail Some paper text")

    monkeypatch.setattr(app_module, "build_graph", lambda: Broken())
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 500
    assert "internal detail" not in r.text
    assert "Traceback" not in r.text


def test_temp_file_is_deleted_after_success_and_after_failure(client, monkeypatch):
    paths = []
    real_load = rvos_poc.load_paper_text

    def spy(path):
        paths.append(path)
        return real_load(path)

    monkeypatch.setattr(app_module, "load_paper_text", spy)
    _upload(client, "paper.txt", b"Some paper text.")
    _upload(client, "paper.rtf", b"some text")
    assert len(paths) == 2
    assert not any(os.path.exists(p) for p in paths)


CODE = "test-code-123"


def _upload_with_code(client, code=None):
    headers = {} if code is None else {"X-Access-Code": code}
    return client.post("/analyse", files={"file": ("paper.txt", b"Some paper text.")}, headers=headers)


def test_without_the_access_code_analyse_is_401(client, monkeypatch):
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    assert _upload_with_code(client).status_code == 401


def test_with_a_wrong_access_code_analyse_is_401(client, monkeypatch):
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    assert _upload_with_code(client, "wrong-guess").status_code == 401


def test_with_the_right_access_code_analyse_runs(client, monkeypatch):
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    r = _upload_with_code(client, CODE)
    assert r.status_code == 200
    assert r.json()["verdict"] == "Overlaps with [1]."


def test_with_no_code_configured_analyse_needs_none(client, monkeypatch):
    monkeypatch.delenv("DEMO_ACCESS_CODE", raising=False)
    assert _upload_with_code(client).status_code == 200
    monkeypatch.setenv("DEMO_ACCESS_CODE", "")
    assert _upload_with_code(client).status_code == 200


def test_a_refused_request_never_reaches_the_pipeline(client, monkeypatch):
    def must_not_run():
        raise AssertionError("pipeline built for a request without the code")

    monkeypatch.setattr(app_module, "build_graph", must_not_run)
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    assert _upload_with_code(client, "wrong-guess").status_code == 401


def test_the_access_code_is_never_logged_or_echoed(client, monkeypatch, caplog):
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    with caplog.at_level("DEBUG"):
        refused = _upload_with_code(client, "wrong-guess")
        allowed = _upload_with_code(client, CODE)
    for text in (refused.text, allowed.text, caplog.text):
        assert CODE not in text
        assert "wrong-guess" not in text


def test_the_access_code_is_compared_in_constant_time(client, monkeypatch):
    calls = []
    real = app_module.hmac.compare_digest

    def spy(a, b):
        calls.append(1)
        return real(a, b)

    monkeypatch.setattr(app_module.hmac, "compare_digest", spy)
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    _upload_with_code(client, CODE)
    assert calls


def test_index_page_has_an_access_code_field_sent_as_a_header(client):
    html = client.get("/").text
    assert 'id="access-code"' in html
    assert 'type="password"' in html
    assert "X-Access-Code" in html


RECORDED = {**FAKE_STATE, "related": [], "verdict": "Recorded verdict.", "truncated": False}


@pytest.fixture
def sample_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "SAMPLE_DIR", tmp_path)
    return tmp_path


def test_recorded_report_is_served_and_labelled_recorded(client, sample_dir):
    (sample_dir / "recorded_report.json").write_text(json.dumps(RECORDED), encoding="utf-8")
    r = client.get("/sample/recorded")
    assert r.status_code == 200
    assert r.json()["verdict"] == "Recorded verdict."
    assert r.json()["recorded"] is True


def test_the_recorded_label_cannot_be_switched_off_by_the_file(client, sample_dir):
    (sample_dir / "recorded_report.json").write_text(json.dumps({**RECORDED, "recorded": False}), encoding="utf-8")
    assert client.get("/sample/recorded").json()["recorded"] is True


def test_missing_recorded_report_is_a_generic_404(client, sample_dir):
    r = client.get("/sample/recorded")
    assert r.status_code == 404
    assert str(sample_dir) not in r.text


def test_unreadable_recorded_report_is_a_generic_500(client, sample_dir):
    for bad in ("not json at all", "[1, 2]"):
        (sample_dir / "recorded_report.json").write_text(bad, encoding="utf-8")
        r = client.get("/sample/recorded")
        assert r.status_code == 500
        assert "not json" not in r.text
        assert str(sample_dir) not in r.text


def test_sample_paper_is_served_as_text_and_missing_is_404(client, sample_dir):
    assert client.get("/sample/paper").status_code == 404
    (sample_dir / "paper.txt").write_text("Open access text.", encoding="utf-8")
    r = client.get("/sample/paper")
    assert r.status_code == 200
    assert r.text == "Open access text."
    assert "text/plain" in r.headers["content-type"]


def test_sample_routes_need_no_access_code(client, sample_dir, monkeypatch):
    (sample_dir / "paper.txt").write_text("Open access text.", encoding="utf-8")
    (sample_dir / "recorded_report.json").write_text(json.dumps(RECORDED), encoding="utf-8")
    monkeypatch.setenv("DEMO_ACCESS_CODE", CODE)
    assert client.get("/sample/paper").status_code == 200
    assert client.get("/sample/recorded").status_code == 200


def test_a_committed_recorded_report_has_every_report_field():
    path = Path(app_module.SAMPLE_DIR) / "recorded_report.json"
    if not path.is_file():
        pytest.skip("no recorded report committed yet")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert set(report) >= {"claim", "method", "result", "related", "verdict", "truncated"}
    for work in report["related"]:
        assert set(work) >= {"n", "title", "year", "url", "has_abstract"}


def test_index_page_offers_the_sample_and_the_recorded_example(client):
    html = client.get("/").text
    assert 'id="use-sample"' in html
    assert 'id="show-recorded"' in html
    assert 'id="recorded-banner"' in html
    assert "Recorded result, not live" in html
    assert "/sample/paper" in html
    assert "/sample/recorded" in html


def test_index_page_credits_the_sample_paper_its_licence_and_the_changes(client):
    html = client.get("/").text
    assert "10.1371/journal.pone.0291908" in html
    assert "Foody" in html
    assert "CC BY 4.0" in html
    assert "creativecommons.org/licenses/by/4.0" in html
    assert "text extracted" in html.lower()


def test_a_committed_sample_paper_is_readable_text():
    path = Path(app_module.SAMPLE_DIR) / "paper.txt"
    if not path.is_file():
        pytest.skip("no sample paper committed yet")
    assert len(rvos_poc.load_paper_text(str(path))) > 5000


def test_index_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_index_page_has_details_toggle_and_container(client):
    html = client.get("/").text
    assert 'id="details-toggle"' in html
    assert 'aria-controls="details"' in html
    assert 'id="details"' in html


def test_index_page_shows_cited_works_under_the_verdict(client):
    html = client.get("/").text
    assert 'id="cited"' in html
    assert 'id="cited-list"' in html


def test_index_page_has_a_truncation_note(client):
    assert 'id="truncation-note"' in client.get("/").text


def test_index_page_clamps_a_long_verdict_with_a_read_more_toggle(client):
    html = client.get("/").text
    assert 'id="verdict-toggle"' in html
    assert 'aria-controls="verdict"' in html


def test_index_page_has_inline_favicon_and_accurate_wait_text(client):
    html = client.get("/").text
    assert 'rel="icon"' in html
    assert "about a minute" not in html
