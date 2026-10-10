"""
RVOS demo web app: upload a paper, get the Report back on screen.

A thin wrapper around rvos_poc.py, which is not modified here. Calls
build_graph().invoke() directly rather than run(), because run() writes a
file and returns nothing. Demo only: one optional shared access code
(DEMO_ACCESS_CODE), no accounts, no storage.

Run:
    uvicorn app:app --host 127.0.0.1 --port 8000
"""

import hashlib
import hmac
import json
import logging
import os
import tempfile
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import anthropic
import requests
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from rvos_poc import (
    MAX_PAPER_CHARS,
    PaperLoadError,
    build_graph,
    load_paper_text,
    numbered_related,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
INDEX_PAGE = Path(__file__).parent / "static" / "index.html"
SAMPLE_DIR = Path(__file__).parent / "sample"

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="RVOS demo")


@app.get("/")
def index():
    return FileResponse(INDEX_PAGE)


@app.get("/sample/paper")
def sample_paper():
    """The public sample paper (open access), so the hosted demo needs no upload."""
    path = SAMPLE_DIR / "paper.txt"
    if not path.is_file():
        raise HTTPException(404, "No sample paper is available.")
    return FileResponse(path, media_type="text/plain; charset=utf-8")


@app.get("/sample/recorded")
def sample_recorded():
    """A stored Report for the sample paper, always labelled recorded.

    The flag is set here, not read from the file, so a stored file cannot pass
    itself off as a live run. No API call is made, so no access code is needed."""
    path = SAMPLE_DIR / "recorded_report.json"
    if not path.is_file():
        raise HTTPException(404, "No recorded example is available.")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise TypeError("not an object")
    except (ValueError, TypeError) as e:
        log.error("Recorded report could not be read: %s", type(e).__name__)
        raise HTTPException(500, "The recorded example could not be read.") from e
    return {**report, "recorded": True}


def require_access_code(x_access_code: str | None = Header(default=None)):
    """When DEMO_ACCESS_CODE is set, /analyse needs it in the X-Access-Code header.

    Unset or empty means no check (local runs). Both values are hashed first so
    the constant-time compare also hides their lengths. The code is never
    logged or put in a response; a refused request costs no API credit."""
    expected = os.environ.get("DEMO_ACCESS_CODE", "")
    if not expected:
        return
    given = hashlib.sha256((x_access_code or "").encode()).digest()
    if not hmac.compare_digest(given, hashlib.sha256(expected.encode()).digest()):
        raise HTTPException(401, "Access code missing or wrong.")


# Analyses started today (UTC) in this process. On a serverless host each
# instance has its own count and loses it on restart, so DEMO_DAILY_CAP is
# best-effort; the spend limit set with Anthropic is the real ceiling.
_usage: dict = {"day": None, "count": 0}
_usage_lock = threading.Lock()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _daily_cap():
    """None when DEMO_DAILY_CAP is unset or empty (no cap). A value that is not
    a whole number counts as 0, so a typo blocks runs instead of quietly
    switching the protection off."""
    raw = os.environ.get("DEMO_DAILY_CAP", "").strip()
    if not raw:
        return None
    return int(raw) if raw.isdigit() else 0


def _count_today() -> int:
    """Runs so far today; call with _usage_lock held."""
    today = _today()
    if _usage["day"] != today:
        _usage["day"], _usage["count"] = today, 0
    return _usage["count"]


def require_daily_headroom():
    cap = _daily_cap()
    if cap is None:
        return
    with _usage_lock:
        if _count_today() >= cap:
            raise HTTPException(429, "The daily limit for this demo has been reached. Please try again tomorrow.")


def count_run():
    """Called just before the pipeline, so only real runs are counted."""
    with _usage_lock:
        _count_today()
        _usage["count"] += 1


@app.post("/analyse", dependencies=[Depends(require_access_code), Depends(require_daily_headroom)])
def analyse(file: UploadFile):
    """Load the uploaded paper, run the pipeline, return the Report as JSON.

    The paper is written to a temp file only because load_paper_text() takes
    a path; the file is deleted before the response is built. Paper text and
    filenames are never logged, and errors sent to the browser are generic
    except for the loader's own message."""
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    display_name = os.path.basename(file.filename or "upload")
    ext = os.path.splitext(display_name)[1]
    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            paper_text = load_paper_text(tmp_path)
        except PaperLoadError as e:
            raise HTTPException(400, str(e).replace(tmp_path, display_name)) from e
        except Exception as e:
            # A library failure inside the loader (corrupt or password-
            # protected PDF, a malformed DOCX) is a bad file, not a server
            # crash -- see the fix plan, F2. This is deliberately broad: we
            # don't enumerate every PDF/DOCX library's exception types here,
            # since that knowledge belongs in load_paper_text, not this app.
            log.error("Loader failed unexpectedly: %s", type(e).__name__)
            raise HTTPException(
                400,
                "Could not read this file. It may be corrupted, "
                "password-protected, or in an unsupported format.",
            ) from e
    finally:
        os.unlink(tmp_path)

    count_run()
    try:
        result = build_graph().invoke({"paper_text": paper_text})
    except (anthropic.APIError, requests.RequestException, ValueError) as e:
        # ValueError covers extract_claim giving up on malformed model JSON
        # (json.JSONDecodeError is a ValueError) or missing keys.
        log.error("Analysis service failed: %s", type(e).__name__)
        raise HTTPException(502, "The analysis service failed. Please try again.") from e
    except Exception as e:
        log.error("Unexpected failure: %s", type(e).__name__)
        raise HTTPException(500, "Something went wrong. Please try again.") from e

    extracted = result["extracted"]
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
        "truncated": len(paper_text) > MAX_PAPER_CHARS,
    }
