# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to work in this repo
- State assumptions explicitly; if uncertain, ask rather than guess.
- Minimum code that solves the problem — nothing speculative, no unrequested flexibility.
- Touch only what the task requires; match existing style; don't "improve" unrelated code.
- If you discover a defect or improvement beyond the current task's explicit
  scope while executing it -- even a clear one, even a security fix -- STOP,
  report what you found and how you'd fix it, and wait for instruction before
  implementing or committing it. Finish or roll back the in-scope work first;
  don't fold the new fix into the same commit either, even once approved --
  unless completing the in-scope work would itself re-trigger the newly-found
  issue (e.g. re-running a test that would leak a secret again), in which
  case report both and ask which to fix first.
- Turn every task into a verifiable goal (write a test, then make it pass) rather than "make it work."
- patches/ is gitignored: local patch files are scratch copies of changes already applied. There is no "commit review-evidence patches" routine in this repo -- CI now provides that evidence.

## Git and test hygiene
Standing rules from the owner (see handoff-rvos-poc3-post-review.md).
- Explain the exact git commands first, then wait for explicit approval
  before every commit and every push. Don't infer permission from adjacent
  context.
- Stage files by name. Never `git add .`.
- Never commit anything under `Docs/Test/` (NDA papers; the repo is public).
- Locally, never run bare `pytest`: `.env` and the `Docs/Test/` fixtures are
  present, so it runs the four live reasoning tests and spends API credit.
  Name the files: `pytest -v test_loading.py test_app.py test_pipeline_offline.py test_repo_hygiene.py`.
- Keep NDA fixture file names, paper titles and author names out of tracked
  files, commit messages and tracker/handover docs. The fixture paths
  (`RVOS_FIXTURE_OVERLAP`, `RVOS_FIXTURE_NOVEL`) and the terms to keep out
  (`RVOS_FORBIDDEN_TERMS`) live only in the gitignored `.env`;
  `test_repo_hygiene.py` checks tracked files for them (it skips in CI, where
  `.env` is absent).
- Never print a secret. The OpenAlex key is sent as a header, not a URL
  parameter, so a failing request can't put it in a traceback.

## Current state
POC4 is POC3 plus a new UI. POC3 (the reasoning pipeline, PDF/DOCX/TXT
loading, CI, the demo web UI, and three code-review hand-overs) is the
baseline commit `ca3424f`: rvos-poc3 `main` at `d51193d` (tag `poc3-complete`)
with the NDA fixture names redacted (`test_rvos_poc.py` reads its fixture paths
from `.env`; new `test_repo_hygiene.py`). POC4 changes `static/index.html`,
plus one test in `test_app.py`. Open issues are tracked in
Docs/review/POC4_backlog.md. See also README.md, CONTEXT.md, HANDOVER.md
(POC3 history), and Docs/review/ (findings register and fix plan).

## Completed increments
- POC1/POC2: the two-agent reasoning pipeline, orchestrated with
  LangGraph. Validated on both known directions (overlap, novel).
- POC3: PDF/DOCX/TXT input (load_paper_text, three format loaders) and
  GitHub Actions CI.
- POC3 UI and review hardening: the demo web UI (app.py, static/index.html);
  three code-review hand-overs (CI pinned to ubuntu-24.04 and Node 24
  actions, upper-bound dependency pins, corrupt-PDF and DOCX-table handling,
  extract_claim response validation, test_pipeline_offline.py); an OpenAlex
  API key sent as a header, with retry on 429/500/503/504. Findings F1-F17
  and their fixes are in Docs/review/.
- POC4 UI (this increment): see below.

## Current increment (POC4: new UI + details toggle)
Front-end only, a demo for a PhD-researcher persona, not a production
interface.
1. `static/index.html` only: plain HTML/CSS/vanilla JS, no framework, no
   build tooling, no external assets (system fonts, no CDN). No MCP.
2. Dark-first theme with a light variant (prefers-color-scheme); colours are
   custom properties on :root.
3. After a run the page shows the Verdict card only, with the related works
   the Verdict cites by number ("[2]") listed under it. A "Show details" button
   (aria-expanded, aria-controls) reveals Claim, Method, Stated result and the
   numbered Related work; the details collapse again at the start of each run.
4. The Verdict is shown as written. It is free text, so it is not parsed into
   a badge. A long Verdict is clamped to about six lines with a "Read more" /
   "Show less" button; the judge itself still writes the validated 150-250
   words (a 60-100 word prompt changed the judgment, see P4-02 and P4-17).
5. Not modified by the UI work: requirements.txt and the CI workflow.
   (test_rvos_poc.py differs from POC3 only by the fixture-name redaction in
   the baseline commit.) Inc 3-4 touched rvos_poc.py and app.py in small,
   tested ways: verdict-length constants at the validated 150-250,
   MAX_PAPER_CHARS, a shared numbered_related() helper, and one additive
   field `truncated` in the /analyse response (the other fields are unchanged).
6. Security properties kept: model- and paper-derived text is rendered with
   textContent, and only https:// URLs are linked, with
   rel="noopener noreferrer".
7. The added tests are in test_app.py: the served page has the details toggle
   and container, the cited-works block, an inline favicon, and no stale wait
   text. Behaviour is checked in a real browser against a stubbed pipeline
   (there is no JS test runner, by design).

## Explicit non-goals for this increment
- No production concerns: no auth, no multi-user handling, no
  deployment pipeline, no scalability work. This is a demo, not a
  release.
- No fix for the untested "insufficient evidence" verdict path (F12) --
  logged, deliberately deferred, decide later.
- No new agents, no batch/multi-paper processing.
- No change to extract_claim, search_openalex, judge_novelty, or
  load_paper_text's existing behaviour.
- Open, to be fixed in later POC4 increments rather than this UI one: F6
  (temperature), F7 (verdict length), F12 (insufficient-evidence test), F15
  (citation numbering duplicated in run() and app.py), D1 (12,000-character
  truncation), D2 (retrieval relevance). See Docs/review/. Each gets its own
  increment and commit, with the owner's approval first.

## Known constraint CI must respect
Docs/Test/* is gitignored (NDA fixtures in any format), not present in CI.
test_rvos_poc.py already skips cleanly (not crashes) when they're missing
(see its second skipif). CI will therefore show those four reasoning tests
SKIPPED, not PASSED — that's expected, not a bug. test_loading.py uses
synthetic files generated in tmp_path, test_pipeline_offline.py mocks the
model and OpenAlex, and test_app.py fakes the graph, so all three PASS in CI.
At POC4 CI should show 60 passed, 5 skipped (the fifth skip is the
test_repo_hygiene.py scan, which needs `.env`). CI verifies the code
imports, lints cleanly, loads PDF/DOCX/txt correctly, and that the web
routes behave; it does not verify reasoning correctness. No
ANTHROPIC_API_KEY secret is set: the workflow still passes
`secrets.ANTHROPIC_API_KEY`, which therefore arrives empty, and the
reasoning tests would skip without the NDA fixtures anyway. A public repo
has no use for an idle credential.
