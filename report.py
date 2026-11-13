"""
The Report module: the one place that maps a finished pipeline run to the
Report shape returned by /analyse (and mirrored by the recorded sample).

Giving the shape one home -- not assembled inline in the route and re-declared
by hand in the recorded fixture -- means the route, the recorded endpoint, the
tests and the UI all read the keys this module produces, so they cannot drift
apart. The reasoning core stays frozen (ADR-002): this module imports from
rvos_poc read-only and calls scorecard; it never folds either into itself.
"""

import logging

import scorecard
from rvos_poc import MAX_PAPER_CHARS, numbered_related

log = logging.getLogger("uvicorn.error")


def build_report(result: dict, paper_text: str) -> dict:
    """Map a finished pipeline run to the Report dict returned by /analyse.

    `result` is the final LangGraph state from build_graph().invoke(...):
    `extracted` (claim/method/result), `related`, `verdict`. The Report always
    carries a `scorecard`: the scorer gets the pipeline's internal related works
    (abstract text intact), and an unexpected scorer failure degrades to the
    "unavailable" card rather than failing the Report. No secret or paper text
    reaches the log.
    """
    extracted = result["extracted"]
    truncated = len(paper_text) > MAX_PAPER_CHARS

    try:
        card = scorecard.build_scorecard(extracted, result["related"], paper_text, truncated)
    except Exception as e:  # noqa: BLE001 -- an optional signal must never fail the Report
        log.error("Scorecard step failed: %s", type(e).__name__)
        card = scorecard.unavailable_scorecard(truncated)

    return {
        "claim": extracted["claim"],
        "method": extracted["method"],
        "result": extracted["result"],
        "related": [
            {
                "n": n,
                "title": w["title"],
                "year": w["year"],
                "url": w["id"],
                "has_abstract": bool(w["abstract"]),
            }
            for n, w in numbered_related(result["related"])
        ],
        "verdict": result["verdict"],
        "truncated": truncated,
        "scorecard": card,
    }
