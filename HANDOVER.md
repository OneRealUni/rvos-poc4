# POC4 handover

The one document the owner and Claude both read and improve. Updated 2026-10-08.
POC4 is POC3 plus a new UI and a set of tracked fixes. The POC3 history, including
the three code-review hand-overs and the OpenAlex incident, is archived in
`Docs/review/POC3_handover.md`.

## Where things live

| What | Where |
|---|---|
| Rules for working in this repo | `CLAUDE.md` |
| Glossary (paper, claim, verdict, load vs extract) | `CONTEXT.md` |
| Current state, rules, gotchas, how to run | this file (`HANDOVER.md`) |
| **All open and closed work, status, acceptance criteria** | **Jira project `RT`** (Scrum board). The only tracker: do not copy item lists into repo docs |
| Definition of Done | Confluence page "RT Definition of Done (standard)" in the Agile directory of the RTVOS space |
| Agent handoff | ONE file for agents, written at the end of every session by the handoff skill, local only (`Docs/handoff/`, gitignored) |
| POC3 audit trail (frozen) | `Docs/review/POC3_findings_register.md`, `POC3_fix_plan.md`, `POC3_handover.md` |
| Offline test evidence | `pytest_output.txt` (stamped with a commit) |

Handover (this file) is for the owner and Claude, across sessions and compacts.
Handoff is only for agents. There is nothing else.

## Where things stand

- Published: `OneRealUni/rvos-poc4` (public), branch `main`, tag
  `poc4-start-ui-update` (2026-10-07). GitHub Actions passed: 67 passed, 5 skipped.
  Every later commit and push needs the owner's explicit approval.
- Offline suite: 67 passed + 1 skipped locally. CI shows 67 passed, 5 skipped (the
  four live tests and the `.env`-dependent hygiene scan skip there by design).
- The four live tests (`test_rvos_poc.py`) passed 4 of 4 after the fixture rename
  (2026-10-06) and are run only deliberately.
- POC3 (`rvos-poc3`) is private. The POC4 history was rebuilt twice before the first
  push (so no fixture names appear in it, and no `Claude-Session:` trailers). Commit
  hashes are not quoted in docs because a rewrite changes them.
- Work tracking moved to Jira (project `RT`) on 2026-10-08. The repo docs below
  still contain old open-issue lists (`CLAUDE.md`, `Docs/review/POC4_backlog.md`);
  cleaning them is tracked in Jira and needs its own approved commit.

## Standing rules (the owner's gates)

- Explain the exact git commands first, then wait for explicit approval before every
  commit and every push. Stage files by name, never `git add .`. No `Claude-Session:`
  trailer (`Co-Authored-By:` is fine).
- Never commit anything under `Docs/Test/` or `Docs/handoff/`. Keep fixture names,
  paper titles, author names, local paths and keys out of tracked files, commit
  messages, Jira and Confluence. `test_repo_hygiene.py` checks tracked files when
  `RVOS_FORBIDDEN_TERMS` is set in `.env`.
- Never run bare `pytest` locally. Name the offline files:
  `pytest -v test_loading.py test_app.py test_pipeline_offline.py test_repo_hygiene.py`.
  Ask before any live run and state the cost first.
- Never print a secret. The OpenAlex key goes in an `Authorization` header.
- Do not change the reasoning core (`extract_claim`, `search_openalex`,
  `judge_novelty`, their prompts, the LangGraph wiring) without an agreed Jira story,
  a test first, and the owner's go for any live run.
- Test first, one commit per increment, the owner reviews after each. Found a
  defect outside the task? Stop, report it, raise a Jira story; do not fold it in.
- Jira and Confluence writes are confirmed by the owner too: show the exact text
  first, one OK per batch. Keep Jira labels few and generic. A story is Done only
  after the implementer ticks the DoD page rules in a comment and the owner confirms.

## How the owner wants to work

- Diagrams plus bullets, crisp answers, no "TL;DR". Honest assessments, including
  your own mistakes; say what was not verified. Ask rather than guess (the owner can
  grill you).
- Small steps, every action reviewed before it is done. Agree scope and rules before
  a new workstream starts.
- Write a handover and handoff when a thread nears about 140k tokens; update Jira
  fully first. Keep both local.
- For POC3 files, use the owner's local `..\POC3` repo. Any GitHub command (push,
  `gh`) needs the owner's approval first.

## What POC4 changed

- **UI:** dark-first page with a light variant, Verdict card first, "Show details"
  for Claim, Method, Stated result and Related work. Plain HTML/CSS/JS, `textContent`
  only, `https://` links only.
- **Fixture names:** fixture paths come from `RVOS_FIXTURE_OVERLAP` /
  `RVOS_FIXTURE_NOVEL` in the gitignored `.env`.
- **Increments:** cited-works list, honest wait text, inline favicon; verdict length
  constants kept at the validated 150-250 with a "Read more / Show less" clamp;
  `MAX_PAPER_CHARS`, a `truncated` flag with a note on the page and in the report, and
  a shared `numbered_related()` helper; seven tests for the "insufficient evidence" path;
  this handover and a regenerated `pytest_output.txt`; `.gitattributes`.

## Findings worth remembering

- `claude-sonnet-5` rejects `temperature` (HTTP 400 "temperature is deprecated for
  this model"; SDK 1.11 has no such parameter). Variance is measured, not controlled.
  `claude-sonnet-5-5` also gives no control; moving to it is a separate decision with a
  fresh live validation.
- A 60-100 word judge verdict changes the judgment: on the novel fixture, 9 of 9
  shorter verdicts said "overlaps significantly". The judge stays at 150-250 words.
  The old prompt also failed the live check about 1 in 3 times, unexplained. The core
  live test was deliberately left unchanged.
- Retrieval (D2): no query shape wins consistently; the keywords chosen by
  `extract_claim` matter more. A low related share on a novel paper is expected.
- Facts to respect in any retrieval or RAG work: `search_openalex` is one GET with
  header auth, retry on 429/500/503/504, `Retry-After` honoured and capped at 30 s,
  and mocked tests. The model sees only the first 12,000 characters of a paper today.
- Insufficient evidence: the model does say so on empty evidence (one live call).

## Gotchas

- `load_dotenv()` runs when `rvos_poc` is imported, so scripts must load `.env` by
  explicit path when run from elsewhere.
- Windows console is cp1252: set `PYTHONIOENCODING=utf-8` when printing titles.
  Python 3.11 f-strings cannot contain backslashes. A literal backslash-n in Python
  source passed through a shell tool may arrive as a real newline; use `chr(92)`.
- `.gitattributes` forces LF; `core.autocrlf=true` no longer prints warnings.
- Importing the old-history backup bundle re-imports the old objects and names; the
  bundle was deleted. Inspect any such bundle in a separate clone.
- Scratch scripts (live measurements, the retrieval study, the headless-Chrome driver
  for the UI, the NDA scrub for Jira drafts) live in the session scratchpad, hard-code
  local paths, and are not in the repo. Recreate them as needed; do not commit them.
- The UI is checked in a real browser against a stubbed pipeline (headless Chrome over
  the DevTools protocol); there is no JS test runner, by design.
- Approximate live spend for the whole POC4 effort: well under one US dollar.

## Unverified, so do not treat as fact

- That the live tests are stable (small sample, unexplained failures with the old
  prompt).
- Retrieval-relevance conclusions rest on three extractions and an LLM judge.
- Jira/Confluence: write access beyond create, edit and link was not tested; no
  delete operation was found, so a wrong create is removed by the owner in the UI.

## Suggested skills

- `mattpocock-skills:grilling` to scope work with the owner (for example RAG).
- `mattpocock-skills:tdd` for every code change (test first, one increment per commit).
- `mattpocock-skills:code-review` before handing a diff to the owner.
- `mattpocock-skills:diagnosing-bugs` if a test or the pipeline misbehaves (rerun once
  first: live tests vary).
- `mattpocock-skills:domain-modeling` only if `CONTEXT.md` needs new terms (for example
  "chunk" once RAG is designed).
- `claude-api` before touching any Anthropic call (model constraints).
- The owner types `/handoff` (and any grilling-with-docs skill) themselves; the agent
  cannot invoke them. Do not run `init`: it would rewrite `CLAUDE.md`.

## Session start checklist

1. `git status` (plain), `git log --oneline -10`.
2. Read `CLAUDE.md`, `CONTEXT.md`, this file, then the agent handoff in `Docs/handoff/`.
3. Open the Jira board (project `RT`); ask the owner which story to work on. Do not
   assume one.

## How to run

```bash
python -m venv venv
venv\Scripts\activate              # Windows
pip install -r requirements.txt
cp .env.example .env               # Anthropic key, OpenAlex mailto + key, fixture paths
uvicorn app:app --host 127.0.0.1 --port 8000      # run from this folder
ruff check .
pytest -v test_loading.py test_app.py test_pipeline_offline.py test_repo_hygiene.py
pytest -v test_rvos_poc.py         # live: costs credit; needs .env and the fixtures
```
