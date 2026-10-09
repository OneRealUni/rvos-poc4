"""
Deploy-config tests: the host installs runtime packages only, and a command-line
deploy uploads only the app files.

Vercel reads requirements.txt, so that file is the deploy list; the dev tools live
in requirements-dev.txt. A CLI deploy uploads everything its default exclusions do
not cover, and those do not cover .env or Docs/ (which holds NDA papers), so
.vercelignore is an allowlist.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent
# httpx is only there for the FastAPI TestClient.
DEV_ONLY = {"pytest", "ruff", "reportlab", "httpx", "uvicorn"}
UPLOADABLE = {"app.py", "rvos_poc.py", "requirements.txt", ".python-version", "static"}


def package_names(path):
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        names.add(re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower().replace("_", "-"))
    return names


def test_deploy_requirements_have_no_dev_tools():
    assert not package_names(ROOT / "requirements.txt") & DEV_ONLY


def test_dev_requirements_extend_the_deploy_list():
    path = ROOT / "requirements-dev.txt"
    assert "-r requirements.txt" in path.read_text(encoding="utf-8")
    assert DEV_ONLY <= package_names(path)


def test_vercelignore_allows_only_the_app_files():
    lines = (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
    rules = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    assert rules[0] == "/*"
    assert all(rule.startswith("!") for rule in rules[1:])
    assert {rule[1:] for rule in rules[1:]} <= UPLOADABLE
