# POC4 handover

Written 2026-10-07. POC4 is POC3 plus a new UI and a set of tracked fixes. Read
`CLAUDE.md` (rules), `CONTEXT.md` (glossary) and `Docs/review/POC4_backlog.md`
(the issue tracker) before touching anything. The POC3 history, including the
three code-review hand-overs and the OpenAlex incident, is archived in
`Docs/review/POC3_handover.md`.

## Where things stand

- A **local** git repository in this folder, branch `main`, **not pushed**: no
  remote is configured and no tag exists yet. The planned tag is
  `poc4-start-ui-update`; the owner asked for it to be created only after the
  final checks are confirmed.
- History: nine commits, see `git log --oneline`: the POC3 baseline with fixture
  names redacted, the new UI, a docs and tracker commit, then one commit per
  increment (Inc 2 to Inc 6). The history was rebuilt twice before any push: once
  so NDA fixture names never appear in it, once to strip the `Claude-Session:` line
  from every commit message. Commit hashes are deliberately not quoted in the docs
  because a rewrite changes them.
- Tests: offline suite 67 passed + 1 skipped (CI shows 67 passed, 5 skipped,
  the five being the four live tests and the `.env`-dependent hygiene scan).
  The four live tests (`test_rvos_poc.py`) passed 4 of 4 after the fixture
  rename (2026-10-06) and are run only deliberately.
- The working tree is clean once the final commit is made; check `git status`.

## Which document is for what

| Document | Purpose |
|---|---|
| `CLAUDE.md` | Rules for working in this repo (read first) |
| `CONTEXT.md` | Glossary: paper, claim, verdict, load vs extract |
| `HANDOVER.md` (this file) | Current state, decisions, findings, gotchas, checklist |
| `Docs/review/POC4_backlog.md` | The **live** POC4 tracker: increments, decisions, issues P4-01..P4-19, owner priorities |
| `Docs/review/POC3_findings_register.md`, `POC3_fix_plan.md` | The **frozen** POC3 audit trail from the external code review (F1-F17, D1/D2, W1-W5). Do not add new issues here; the register only has a short POC4 status section at its end |
| `Docs/review/POC3_handover.md` | Archived POC3 handover (history only) |
| `handoff-rvos-poc4-maintenance.md` | Entry point for a fresh agent doing ordinary maintenance |
| `handoff-rvos-poc4-next-increments.md` | Entry point for the planned RAG / PyAlex work |
| `Docs/handoffs/` | **Local only (gitignored, never pushed).** Dated snapshots written by the `/handoff` command at the end of a session: a work log, not the current state. Add a new dated file after each session |
| `pytest_output.txt` | Offline test evidence at a stamped commit |

## Before the first push (checklist; nothing has been pushed)

1. Done: all increments committed and approved.
2. Decided by the owner (2026-10-07): no LICENSE (all rights reserved by default);
   the repository is public and named `rvos-poc4`; the `Claude-Session:` line was
   stripped from every commit message; `Docs/handoffs/` stays local; the old-history
   backup bundle was deleted.
3. Re-run: `ruff check .`, the four offline test files, a clean-checkout CI
   simulation (copy tracked + untracked-not-ignored files to a temp folder with no
   `.env`; expect 67 passed, 5 skipped), and a scan of every commit's contents and
   messages for the forbidden terms, local path fragments and the real key values.
4. Create the tag `poc4-start-ui-update` last, on the final commit, only when the
   owner says so (a tag set before a history rewrite would point at a dead commit).
5. Only on the owner's explicit "push": push, then verify the GitHub Actions run
   (expect 67 passed, 5 skipped). GitHub commands need approval; pushing workflow
   files needs the `workflow` scope on the `gh` token.

## What POC4 changed, by increment

- **UI:** dark-first page with a light variant, Verdict card
  first, a "Show details" button for Claim, Method, Stated result and Related
  work. Plain HTML/CSS/JS, `textContent` only, `https://` links only.
- **Inc 1, fixture names:** `test_rvos_poc.py` reads the NDA fixture paths from
  `RVOS_FIXTURE_OVERLAP` / `RVOS_FIXTURE_NOVEL` in the gitignored `.env`;
  `test_repo_hygiene.py` scans tracked files for the terms in
  `RVOS_FORBIDDEN_TERMS` (also in `.env`; it skips in CI).
- **Inc 2:** a "Cited in the verdict" list built from the `[n]` numbers in the
  Verdict text, honest wait text, an inline favicon.
- **Inc 3:** verdict length constants kept at the validated 150-250; a long
  Verdict is clamped to six lines with "Read more" / "Show less".
- **Inc 4:** `MAX_PAPER_CHARS`, a `truncated` flag in `/analyse` with a note on
  the page and in the report, and a shared `numbered_related()` helper.
- **Inc 5:** seven tests for the "insufficient evidence" path; retrieval
  relevance investigated.
- **Inc 6:** this handover, the two handoff files, a regenerated
  `pytest_output.txt`, and `.gitattributes`.

## Findings worth remembering

- **F6 (temperature) is not possible** on `claude-sonnet-5`: the API returns
  400 "`temperature` is deprecated for this model" and SDK 1.11 has no such
  parameter. Variance is measured, not controlled.
- **A 60-100 word judge verdict changes the judgment.** On the novel fixture
  the short verdicts said "The claim overlaps significantly with existing
  work" (9 of 9 shorter verdicts failed the live "novel" check; the old prompt
  also failed 1 of 3, unexplained). It is deferred as P4-17. The core live test
  was deliberately left unchanged.
- **Retrieval (D2):** no query shape wins consistently; the keywords chosen by
  `extract_claim` matter more. A low related share on a novel paper is
  expected.
- Insufficient evidence: the model does say so on empty evidence (one live call).

## Standing rules (the owner's gates)

- Explain the exact git commands first, then wait for explicit approval before
  every commit and every push. Stage files by name, never `git add .`.
- Never commit anything under `Docs/Test/`. Keep fixture names, titles and
  author names out of tracked files, commit messages and docs.
- Never run bare `pytest` locally; name the offline files. Ask before any live
  run and state the cost first.
- Never print a secret. The OpenAlex key goes in an `Authorization` header.
- The owner reviews and confirms after every increment before the next one.

## Gotchas

- `load_dotenv()` runs when `rvos_poc` is imported, so scripts must load `.env`
  by explicit path if they are run from elsewhere.
- Windows console is cp1252: set `PYTHONIOENCODING=utf-8` when printing
  titles. Python 3.11 f-strings cannot contain backslashes.
- When a shell tool passes Python source containing a literal backslash-n it may
  arrive as a real newline; build it with `chr(92)` or avoid it.
- `git fetch` from the old-history backup bundle re-imports the old objects
  (and the names) into the repository; open the bundle in a separate clone.
- `.gitattributes` forces LF; the machine's `core.autocrlf=true` no longer
  prints LF/CRLF warnings.
- Do NOT add a `Claude-Session:` trailer to commit messages (it was stripped from
  all of them before the first push). The `Co-Authored-By:` line is fine.
- The scratch scripts used in this work (live measurement, retrieval study, the
  headless-Chrome driver for the UI, the pre-push checks) lived in the session
  scratchpad, are not in the repository, and hard-code local paths. Recreate them
  as needed; do not commit them as they are.
- The model in use is `claude-sonnet-5`. `claude-sonnet-5-5` (same price) exists;
  moving to it would be a separate decision with a fresh live validation, and it
  also gives no temperature control.
- Approximate live spend for the whole POC4 effort so far: well under one US dollar
  (largest items: the F7 measurement about $0.16, the retrieval study about $0.09).

## Open items

- **P4-18 RAG** and **P4-19 PyAlex** are the key next improvements (owner
  priority). See `handoff-rvos-poc4-next-increments.md`.
- **P4-17:** retry a shorter verdict with a prompt that protects the judgment.
- **P4-04:** the old prompt's occasional live-assertion failures are unexplained.
- Owner actions: say when to create the tag and push; make `rvos-poc3` private
  as planned.
- **P4-20:** there are several handoff files (two entry points plus the local
  snapshots); the owner will sort or merge them later.

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
