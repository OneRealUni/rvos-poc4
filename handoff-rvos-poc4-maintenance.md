# Handoff: RVOS POC4 maintenance

Written for a fresh agent, 2026-10-07. Focus of the next session: **resume POC4
maintenance** (no task chosen yet; ask the user). For the planned larger work see
`handoff-rvos-poc4-next-increments.md`.

## Hard constraints from the user (do not break these)
- **Explain the exact git command sequence first, then wait for explicit approval
  before every commit and every push.** Stage files by name; never `git add .`.
- **Never commit anything under `Docs/Test/`** (NDA fixtures). Keep fixture file
  names, paper titles and author names out of tracked files, commit messages and
  docs; `test_repo_hygiene.py` checks this when `RVOS_FORBIDDEN_TERMS` is set in `.env`.
- **Do not change the reasoning core** (`extract_claim`, `search_openalex`,
  `judge_novelty`, their prompts, the LangGraph wiring) without an agreed increment,
  a test first, and the owner's go for any live run. A shorter verdict prompt was
  tried and changed the judgment; see `HANDOVER.md`.
- **Ask before any live run** (it spends Anthropic credit and OpenAlex quota) and
  state the estimated cost. Never run bare `pytest` locally.
- **Never print a secret.** Read keys from `.env`; the OpenAlex key is sent as a
  header, never a URL parameter.
- No `ANTHROPIC_API_KEY` repo secret in CI (reasoning tests skip there by design).
- The owner reviews and confirms after every increment.

## Where things stand
- Published at https://github.com/OneRealUni/rvos-poc4 (public), tag
  `poc4-start-ui-update` on the first-push commit. Check `git log --oneline` and plain
  `git status`; every later commit and push needs the owner's explicit approval.
- Offline suite: 67 passed, 1 skipped; CI should show 67 passed, 5 skipped.
- Issues are tracked in `Docs/review/POC4_backlog.md`; update it at the end of every
  increment.

## Read these instead of asking the user to re-explain
| Need | Where |
|---|---|
| Rules for working in this repo | `CLAUDE.md` |
| Glossary (load vs extract, paper text, verdict, ...) | `CONTEXT.md` |
| State, decisions, findings, gotchas, how to run | `HANDOVER.md` |
| Open issues and increment history | `Docs/review/POC4_backlog.md` |
| POC3 history and review audit trail | `Docs/review/POC3_handover.md`, `POC3_findings_register.md`, `POC3_fix_plan.md` |
| Latest offline test evidence | `pytest_output.txt` (offline files only) |
| CI workflow | `.github/workflows/tests.yml` |

Do not restate these; follow them.

## How this user wants to work
- Bullet-point answers, a small diagram where it helps, no "TL;DR" style summaries.
  Keep replies short when asked to speed up.
- Honest assessments, including pushback and your own mistakes; do not claim
  something works unless it was checked. Say what was not verified.
- Fix every reported issue in POC4 (do not just log it), one increment each, test
  first, one commit per increment, with approval before the commit.
- They correct plainly and expect the correction to be recorded.

## Things learned the hard way
- Fixture paths and the forbidden terms live only in `.env`; load it by explicit
  path in scratch scripts. `load_dotenv()` runs when `rvos_poc` is imported.
- `claude-sonnet-5` rejects `temperature` (HTTP 400); do not plan on it.
- Windows console is cp1252: use `PYTHONIOENCODING=utf-8`. Python 3.11 f-strings
  cannot contain backslashes. A literal backslash-n in Python source passed through
  a shell tool may become a real newline; use `chr(92)`.
- Importing the old-history backup bundle into this repository re-imports the old
  objects; inspect it in a separate clone.
- Headless Chrome driven over the DevTools protocol (scratch scripts, not in the
  repo) is how the UI is checked; there is no JS test runner by design.

## Unverified, so do not treat as fact
- That the live tests are stable: the old prompt failed about 1 in 3 assertions in a
  small sample, unexplained (P4-04).
- Retrieval-relevance conclusions rest on three extractions and an LLM judge.

## Suggested skills
- `mattpocock-skills:tdd` for any code change; `mattpocock-skills:diagnosing-bugs`
  if a test or the pipeline misbehaves (rerun once first: live tests vary);
  `mattpocock-skills:code-review` before handing work to a reviewer.
- Not invocable by the agent (user must type them): `mattpocock-skills:grill-with-docs`,
  `mattpocock-skills:handoff`. Do not run `init` (it would rewrite `CLAUDE.md`).

## First moves
1. `git status` (plain), `git log --oneline -10`.
2. Read `CLAUDE.md`, `CONTEXT.md`, `HANDOVER.md`, then the tracker.
3. Ask which task the user wants. Do not assume one.
