"""
Repo hygiene tests: keep local-only names out of the public repo.

The fixture papers are NDA and their file names identify them, so the live
tests read their paths from .env (RVOS_FIXTURE_OVERLAP, RVOS_FIXTURE_NOVEL)
instead of naming them in code. The terms to keep out of tracked files are
listed in .env too (RVOS_FORBIDDEN_TERMS, comma-separated), never here, so
this file cannot leak them itself. Without that variable (e.g. in CI) the
scan test skips.
"""

import os
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
TERMS = [t.strip().lower() for t in os.environ.get("RVOS_FORBIDDEN_TERMS", "").split(",") if t.strip()]


def test_fixture_paths_come_from_the_environment(monkeypatch):
    import test_rvos_poc

    monkeypatch.setenv("RVOS_FIXTURE_OVERLAP", "somewhere/a.txt")
    assert test_rvos_poc.fixture_path("RVOS_FIXTURE_OVERLAP", "x.txt") == ROOT / "somewhere" / "a.txt"

    monkeypatch.delenv("RVOS_FIXTURE_OVERLAP")
    assert test_rvos_poc.fixture_path("RVOS_FIXTURE_OVERLAP", "x.txt") == ROOT / "Docs" / "Test" / "x.txt"

    monkeypatch.setenv("RVOS_FIXTURE_OVERLAP", "")
    assert test_rvos_poc.fixture_path("RVOS_FIXTURE_OVERLAP", "x.txt") == ROOT / "Docs" / "Test" / "x.txt"


@pytest.mark.skipif(not TERMS, reason="RVOS_FORBIDDEN_TERMS not set (it lives in .env, never in the repo)")
def test_no_forbidden_terms_in_tracked_files():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    hits = []
    for name in tracked:
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        count = sum(text.count(term) for term in TERMS)
        if count:
            hits.append(f"{name} ({count})")
    assert not hits, "Tracked files contain terms listed in RVOS_FORBIDDEN_TERMS: " + "; ".join(hits)
