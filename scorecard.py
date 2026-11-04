"""
Research scorecard (RT-49, Increment 1) -- the first research-quality scoring
signal added to the Report.

One classifier call (Haiku 5.5) scores three criteria 0-5 (Originality,
Methodology, Ethics); Ethics is computed but excluded from the overall band.
Literature and Statistics are deliberately "not assessed (awaiting RAG)". The
band is the neutral numeric mean of the *scored* criteria -- no colour, no
good/bad tiers (a research idea is never "bad").

Honesty is first-class and decided here, not by the model: a criterion with no
evidence behind it (no retrievable abstract to compare against; no method text)
reads "insufficient evidence" rather than a low score, and a scorer failure
degrades to an "unavailable" card instead of breaking the Report.

Imports the shared Anthropic client and response reader from rvos_poc WITHOUT
modifying it; the reasoning core stays frozen (see ADR-002).
"""

import json
import logging

from rvos_poc import MAX_PAPER_CHARS, _response_text, client

log = logging.getLogger("uvicorn.error")

MODEL = "claude-haiku-5-5"
SCALE = 5

# Fixed, non-model text. The scorer never echoes model prose into the card.
_AWAITING_RAG = "awaiting RAG"
_ETHICS_NOTE = "computed · excluded from band"
_INSUFFICIENT_NOTE = "insufficient evidence"
_UNAVAILABLE_CAVEAT = "The scorecard could not be generated for this run."

_LABELS = {
    "originality": "Originality",
    "methodology": "Methodology",
    "ethics": "Ethics",
    "literature": "Literature",
    "statistics": "Statistics",
}
_MODEL_KEYS = ("originality", "methodology", "ethics")


def _criterion(key, state, score=None, note=None):
    c = {"key": key, "label": _LABELS[key], "state": state, "score": score}
    if note:
        c["note"] = note
    return c


def _prompt(extracted, related, paper_text):
    evidence = "\n\n".join(
        f"- {w.get('title')} ({w.get('year')}): {w.get('abstract', '')[:400]}"
        for w in related
        if w.get("abstract")
    )
    return f"""You are scoring the research quality of a paper for a provisional, \
internal signal. Score each criterion as an integer from 0 (very weak) to 5 \
(very strong), judging only what the text below supports.

CLAIM: {extracted.get('claim', '')}
METHOD: {extracted.get('method', '')}
RESULT: {extracted.get('result', '')}

RELATED WORK RETRIEVED (abstracts):
{evidence if evidence else "(no abstracts were retrievable)"}

PAPER TEXT (excerpt):
{paper_text[:MAX_PAPER_CHARS]}

Score these three criteria:
- originality: how far the claim stands from the related work above.
- methodology: how sound the described method looks.
- ethics: how well ethical considerations appear to be handled.

Return ONLY valid JSON with integer keys originality, methodology, ethics, each \
0-5. No markdown fences, no commentary -- just the JSON object.
"""


def _model_scores(extracted, related, paper_text) -> dict:
    """Make the single Haiku call and return validated 0-5 integer scores.

    Raises on any malformed/out-of-range response; the caller degrades
    gracefully. One call only -- no retry (the scorer's budget is one call)."""
    # Thinking off: this is a short, deterministic classifier returning tiny JSON,
    # not a reasoning task. Haiku 5.5 runs adaptive thinking by default, which would
    # spend the whole token budget on a thinking block and return no text block
    # (stop_reason "max_tokens") -- confirmed live. Disabled is accepted at the
    # default "medium" effort. This also keeps the call cheap and deterministic.
    resp = client.messages.create(
        model=MODEL,
        max_tokens=200,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": _prompt(extracted, related, paper_text)}],
    )
    text = _response_text(resp).replace("```json", "").replace("```", "").strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError("scorer response was not a JSON object")
    scores = {}
    for key in _MODEL_KEYS:
        value = parsed.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= SCALE):
            raise ValueError(f"scorer returned an invalid {key} score")
        scores[key] = value
    return scores


def unavailable_scorecard(truncated: bool) -> dict:
    """A whole-shaped card for when the scorer could not run.

    Public so app.py can degrade defensively too: build_scorecard never raises,
    but the /analyse boundary guards against any unexpected failure as well."""
    return {
        "provisional": True,
        "scale": SCALE,
        "available": False,
        "band": None,
        "band_state": "insufficient-evidence",
        "criteria": [
            _criterion("originality", "insufficient-evidence", note=_INSUFFICIENT_NOTE),
            _criterion("methodology", "insufficient-evidence", note=_INSUFFICIENT_NOTE),
            _criterion("ethics", "excluded", note=_ETHICS_NOTE),
            _criterion("literature", "not-assessed", note=_AWAITING_RAG),
            _criterion("statistics", "not-assessed", note=_AWAITING_RAG),
        ],
        "caveat": _UNAVAILABLE_CAVEAT,
        "truncated": truncated,
    }


def build_scorecard(extracted: dict, related: list, paper_text: str, truncated: bool) -> dict:
    """Return the additive `scorecard` object for one analysed paper.

    Never raises: a model or parse failure returns an "unavailable" card so one
    optional signal cannot break /analyse. Logs the failure type only -- never a
    secret, the paper text, or the model's words."""
    try:
        scores = _model_scores(extracted, related, paper_text)
    except Exception as e:  # noqa: BLE001 -- any scorer failure degrades, never breaks the Report
        log.error("Scorecard unavailable: %s", type(e).__name__)
        return unavailable_scorecard(truncated)

    has_abstract = any(w.get("abstract") for w in related)
    has_method = bool((extracted.get("method") or "").strip())

    # Honesty gate (deterministic): absence of evidence is not a low score.
    if has_abstract:
        originality = _criterion("originality", "scored", score=scores["originality"])
    else:
        originality = _criterion("originality", "insufficient-evidence", note=_INSUFFICIENT_NOTE)
    if has_method:
        methodology = _criterion("methodology", "scored", score=scores["methodology"])
    else:
        methodology = _criterion("methodology", "insufficient-evidence", note=_INSUFFICIENT_NOTE)

    criteria = [
        originality,
        methodology,
        _criterion("ethics", "excluded", score=scores["ethics"], note=_ETHICS_NOTE),
        _criterion("literature", "not-assessed", note=_AWAITING_RAG),
        _criterion("statistics", "not-assessed", note=_AWAITING_RAG),
    ]

    # Band = mean of the scored, non-excluded criteria (Originality + Methodology).
    banded = [c["score"] for c in (originality, methodology) if c["state"] == "scored"]
    if banded:
        band, band_state = round(sum(banded) / len(banded), 1), "scored"
    else:
        band, band_state = None, "insufficient-evidence"

    caveat_parts = []
    if truncated:
        caveat_parts.append(
            f"This paper was truncated: only the first {MAX_PAPER_CHARS:,} characters were scored, "
            "so later sections may be missed."
        )
    if originality["state"] == "insufficient-evidence" or methodology["state"] == "insufficient-evidence":
        caveat_parts.append("Some criteria lacked enough evidence to score.")

    return {
        "provisional": True,
        "scale": SCALE,
        "available": True,
        "band": band,
        "band_state": band_state,
        "criteria": criteria,
        "caveat": " ".join(caveat_parts),
        "truncated": truncated,
    }
