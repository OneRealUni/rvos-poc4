"""
Tests for the Report module (report.build_report): the one place that maps a
finished pipeline run to the /analyse Report shape. Like test_app.py these need
no API key or NDA files -- the pipeline result is a plain dict and the scorer is
stubbed, so the Report shape is asserted directly at the module seam rather than
through HTTP and a fake graph.
"""

import pytest

import report
import scorecard

# A finished pipeline run: the LangGraph final state build_graph().invoke(...)
# returns -- extracted (claim/method/result), related, verdict.
FAKE_RESULT = {
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

# The scorer's top-level shape (keys only); the scorer's own mapping is covered
# in test_scorecard.py. Carries exactly the keys a real card has so a parity
# check against it would be meaningful.
FAKE_CARD = {
    "provisional": True,
    "scale": 5,
    "available": True,
    "band": 3.5,
    "band_state": "scored",
    "criteria": [],
    "caveat": "",
    "truncated": False,
}


@pytest.fixture
def stub_scorecard(monkeypatch):
    """Stub the scorer and capture the arguments build_report passes it."""
    seen = {}

    def fake_build(extracted, related, paper_text, truncated):
        seen["args"] = {
            "extracted": extracted,
            "related": related,
            "paper_text": paper_text,
            "truncated": truncated,
        }
        return FAKE_CARD

    monkeypatch.setattr(scorecard, "build_scorecard", fake_build)
    return seen


def test_report_has_exactly_the_analyse_shape(stub_scorecard):
    rep = report.build_report(FAKE_RESULT, "short text")
    assert set(rep) == {"claim", "method", "result", "related", "verdict", "truncated", "scorecard"}


def test_report_copies_the_extracted_fields_and_the_verdict(stub_scorecard):
    rep = report.build_report(FAKE_RESULT, "short text")
    assert rep["claim"] == "A claim."
    assert rep["method"] == "A method."
    assert rep["result"] == "A result."
    assert rep["verdict"] == "Overlaps with [1]."
    assert "keywords" not in rep  # internal extract field, never exposed


def test_related_work_is_numbered_and_flags_missing_abstracts(stub_scorecard):
    rep = report.build_report(FAKE_RESULT, "short text")
    assert rep["related"] == [
        {"n": 1, "title": "Paper A", "year": 2020, "url": "https://openalex.org/W1", "has_abstract": True},
        {"n": 2, "title": "Paper B", "year": 2021, "url": "https://openalex.org/W2", "has_abstract": False},
    ]


def test_truncated_is_false_below_the_limit_and_true_above(stub_scorecard, monkeypatch):
    monkeypatch.setattr(report, "MAX_PAPER_CHARS", 5)
    assert report.build_report(FAKE_RESULT, "12345")["truncated"] is False
    assert report.build_report(FAKE_RESULT, "123456")["truncated"] is True


def test_scorecard_from_the_scorer_is_attached(stub_scorecard):
    assert report.build_report(FAKE_RESULT, "short text")["scorecard"] is FAKE_CARD


def test_scorer_gets_the_internal_related_with_abstracts_and_the_truncation(stub_scorecard, monkeypatch):
    monkeypatch.setattr(report, "MAX_PAPER_CHARS", 5)
    report.build_report(FAKE_RESULT, "123456")
    args = stub_scorecard["args"]
    # the scorer must see the full related works (abstract text intact), not the
    # trimmed /analyse view, so it can judge originality against prior work
    assert args["related"] is FAKE_RESULT["related"]
    assert args["related"][0]["abstract"] == "Has one."
    assert args["truncated"] is True


def test_a_scorer_failure_degrades_to_the_unavailable_card_not_an_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("scorer blew up: secret-host:9000")

    monkeypatch.setattr(scorecard, "build_scorecard", boom)
    rep = report.build_report(FAKE_RESULT, "short text")  # must not raise
    assert rep["scorecard"] == scorecard.unavailable_scorecard(False)
    assert rep["scorecard"]["available"] is False
    assert rep["verdict"] == "Overlaps with [1]."  # the rest of the Report survives
