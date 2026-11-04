"""
Offline unit tests for scorecard.py (RT-49, Research scorecard Increment 1).

Seam 1 (primary): build_scorecard() maps a stubbed Haiku classifier response to
the additive `scorecard` object. The model call is mocked exactly as
test_pipeline_offline.py mocks the reasoning model, so nothing here needs an API
key, a network, or the NDA fixtures -- these PASS in CI and cost nothing.

What these pin is external behaviour: the object shape, the scores, the band
maths, the first-class "insufficient evidence" / "not assessed" states, the
truncation caveat, and graceful degradation. They never assert the prompt text
or private helpers, so a reworded prompt leaves them green.
"""

import types

import scorecard as sc

# A rich, normal pipeline result: method text present, abstracts retrievable.
EXTRACTED = {"claim": "A claim.", "method": "A described method.", "result": "A result.", "keywords": ["k"]}
RELATED_RICH = [
    {"title": "Paper A", "year": 2020, "id": "https://openalex.org/W1", "abstract": "A has an abstract."},
    {"title": "Paper B", "year": 2021, "id": "https://openalex.org/W2", "abstract": ""},
]
RELATED_NO_ABSTRACTS = [
    {"title": "Paper A", "year": 2020, "id": "https://openalex.org/W1", "abstract": ""},
    {"title": "Paper B", "year": 2021, "id": "https://openalex.org/W2", "abstract": ""},
]


def _fake_resp(text):
    """A fake Anthropic response shaped the way rvos_poc._response_text expects."""
    return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=text)])


def _stub_model(monkeypatch, text):
    """Make the single Haiku classifier call return `text` (or raise, if callable)."""
    def fake_create(**kwargs):
        if callable(text):
            return text()
        return _fake_resp(text)

    monkeypatch.setattr(sc.client.messages, "create", fake_create)


def _by_key(card):
    return {c["key"]: c for c in card["criteria"]}


def _build(monkeypatch, model_json, related=RELATED_RICH, extracted=EXTRACTED, truncated=False):
    _stub_model(monkeypatch, model_json)
    return sc.build_scorecard(extracted, related, "some paper text", truncated)


# ---------------------------------------------------------------------------
# the normal mapping
# ---------------------------------------------------------------------------


def test_scores_map_to_criteria_and_the_card_is_labelled_provisional(monkeypatch):
    card = _build(monkeypatch, '{"originality": 4, "methodology": 3, "ethics": 2}')
    assert card["provisional"] is True
    assert card["scale"] == 5
    assert card["available"] is True
    crit = _by_key(card)
    assert (crit["originality"]["score"], crit["originality"]["state"]) == (4, "scored")
    assert (crit["methodology"]["score"], crit["methodology"]["state"]) == (3, "scored")


def test_band_is_the_mean_of_originality_and_methodology(monkeypatch):
    card = _build(monkeypatch, '{"originality": 4, "methodology": 3, "ethics": 2}')
    assert card["band"] == 3.5
    assert card["band_state"] == "scored"


def test_ethics_is_computed_but_excluded_from_the_band(monkeypatch):
    # Ethics = 5 must not drag the band up; band stays mean(4, 2) = 3.0.
    card = _build(monkeypatch, '{"originality": 4, "methodology": 2, "ethics": 5}')
    crit = _by_key(card)
    assert crit["ethics"]["score"] == 5
    assert crit["ethics"]["state"] == "excluded"
    assert card["band"] == 3.0


def test_literature_and_statistics_are_not_assessed_awaiting_rag(monkeypatch):
    card = _build(monkeypatch, '{"originality": 3, "methodology": 3, "ethics": 3}')
    crit = _by_key(card)
    for key in ("literature", "statistics"):
        assert crit[key]["state"] == "not-assessed"
        assert crit[key]["score"] is None
        assert "awaiting RAG" in crit[key]["note"]


def test_the_five_criteria_appear_in_report_order(monkeypatch):
    card = _build(monkeypatch, '{"originality": 3, "methodology": 3, "ethics": 3}')
    assert [c["key"] for c in card["criteria"]] == [
        "originality", "methodology", "ethics", "literature", "statistics"
    ]


def test_model_json_may_be_wrapped_in_a_code_fence(monkeypatch):
    card = _build(monkeypatch, '```json\n{"originality": 2, "methodology": 4, "ethics": 1}\n```')
    assert card["available"] is True
    assert card["band"] == 3.0


# ---------------------------------------------------------------------------
# insufficient evidence is first-class (deterministic, not the model's whim)
# ---------------------------------------------------------------------------


def test_thin_retrieval_makes_originality_insufficient_evidence_not_a_low_score(monkeypatch):
    # The model still returns a number, but with no retrievable abstract there is
    # no prior work to measure originality against -- absence of evidence must not
    # be scored as poor quality.
    card = _build(monkeypatch, '{"originality": 4, "methodology": 3, "ethics": 2}', related=RELATED_NO_ABSTRACTS)
    crit = _by_key(card)
    assert crit["originality"]["state"] == "insufficient-evidence"
    assert crit["originality"]["score"] is None
    # Methodology is paper-derived, so it is still scored; the band is just it.
    assert crit["methodology"]["state"] == "scored"
    assert card["band"] == 3.0
    assert card["band_state"] == "scored"


def test_zero_related_works_leaves_originality_insufficient(monkeypatch):
    card = _build(monkeypatch, '{"originality": 5, "methodology": 2, "ethics": 2}', related=[])
    crit = _by_key(card)
    assert crit["originality"]["state"] == "insufficient-evidence"
    assert card["band"] == 2.0


def test_empty_method_text_makes_methodology_insufficient_evidence(monkeypatch):
    thin = {**EXTRACTED, "method": "   "}
    card = _build(monkeypatch, '{"originality": 4, "methodology": 3, "ethics": 2}', extracted=thin)
    crit = _by_key(card)
    assert crit["methodology"]["state"] == "insufficient-evidence"
    assert crit["methodology"]["score"] is None


def test_band_itself_reads_insufficient_when_nothing_is_scored(monkeypatch):
    thin = {**EXTRACTED, "method": ""}
    card = _build(monkeypatch, '{"originality": 4, "methodology": 3, "ethics": 2}', related=[], extracted=thin)
    assert card["band"] is None
    assert card["band_state"] == "insufficient-evidence"


# ---------------------------------------------------------------------------
# truncation caveat
# ---------------------------------------------------------------------------


def test_truncation_is_surfaced_as_a_caveat(monkeypatch):
    card = _build(monkeypatch, '{"originality": 3, "methodology": 3, "ethics": 3}', truncated=True)
    assert card["truncated"] is True
    assert "truncat" in card["caveat"].lower()


def test_a_short_paper_carries_no_truncation_caveat(monkeypatch):
    card = _build(monkeypatch, '{"originality": 3, "methodology": 3, "ethics": 3}', truncated=False)
    assert card["truncated"] is False
    assert "truncat" not in card["caveat"].lower()


# ---------------------------------------------------------------------------
# graceful degradation -- a scorer failure must never raise
# ---------------------------------------------------------------------------


def test_a_model_error_degrades_to_an_unavailable_card_without_raising(monkeypatch):
    def boom():
        raise RuntimeError("haiku call failed: secret-host refused")

    card = _build(monkeypatch, boom)
    assert card["available"] is False
    assert card["band"] is None
    assert card["band_state"] == "insufficient-evidence"
    assert card["provisional"] is True  # the shape is still whole


def test_malformed_model_json_degrades_to_unavailable(monkeypatch):
    card = _build(monkeypatch, "not json at all")
    assert card["available"] is False


def test_an_out_of_range_score_degrades_to_unavailable(monkeypatch):
    card = _build(monkeypatch, '{"originality": 9, "methodology": 3, "ethics": 2}')
    assert card["available"] is False


def test_a_missing_score_key_degrades_to_unavailable(monkeypatch):
    card = _build(monkeypatch, '{"originality": 3, "ethics": 2}')
    assert card["available"] is False


def test_the_scorer_makes_exactly_one_model_call(monkeypatch):
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        return _fake_resp('{"originality": 3, "methodology": 3, "ethics": 3}')

    monkeypatch.setattr(sc.client.messages, "create", fake_create)
    sc.build_scorecard(EXTRACTED, RELATED_RICH, "some paper text", False)
    assert calls["n"] == 1


def test_the_scorer_calls_the_haiku_model(monkeypatch):
    seen = {}

    def fake_create(**kwargs):
        seen.update(kwargs)
        return _fake_resp('{"originality": 3, "methodology": 3, "ethics": 3}')

    monkeypatch.setattr(sc.client.messages, "create", fake_create)
    sc.build_scorecard(EXTRACTED, RELATED_RICH, "some paper text", False)
    assert seen["model"] == "claude-haiku-5-5"
