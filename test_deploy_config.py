"""
Deploy-config tests: the host installs runtime packages only, and a command-line
deploy uploads only the app files.

Vercel reads requirements.txt, so that file is the deploy list; the dev tools live
in requirements-dev.txt. A CLI deploy uploads everything its default exclusions do
not cover, and those do not cover .env or Docs/ (which holds NDA papers), so
.vercelignore is an allowlist.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parent
# httpx is only there for the FastAPI TestClient.
DEV_ONLY = {"pytest", "ruff", "reportlab", "httpx", "uvicorn"}
UPLOADABLE = {"app.py", "rvos_poc.py", "scorecard.py", "requirements.txt", ".python-version", "static", "sample"}


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


def test_vercelignore_ships_the_sample_folder():
    assert "!sample" in (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()


def vercelignore_allowlist():
    lines = (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
    rules = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return {rule[1:] for rule in rules[1:] if rule.startswith("!")}


def app_local_imports():
    """Top-level modules app.py imports that are local .py files in the repo root."""
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {name for name in names if (ROOT / f"{name}.py").exists()}


def test_vercelignore_ships_every_local_module_app_imports():
    # A local module app.py imports but the allowlist omits is silently dropped
    # from the deploy -> ModuleNotFoundError -> 500 on every route (the build
    # still passes, since it never imports the app). This ties the allowlist to
    # the actual imports so a new runtime module cannot slip through again.
    missing = {f"{name}.py" for name in app_local_imports()} - vercelignore_allowlist()
    assert not missing, (
        f"app.py imports these local modules but .vercelignore omits them: {sorted(missing)}"
    )
