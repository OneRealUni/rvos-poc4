# RVOS POC4 backlog and issue tracker

- **Created:** 2026-10-06. Updated at the end of every increment, after the owner's review confirmation.
- **Rule:** every issue is fixed in POC4 (none is just logged). One increment = test first, one commit, owner approval before the commit, review confirmation after it.
- **Status values:** OPEN, IN PROGRESS, DONE (with commit), WATCH (no action planned, reason given).
- **Public-repo rule:** this file must not contain fixture file names, paper titles, author names or local paths.

## Decisions taken (owner, 2026-10-06)

- Baseline commit is rebuilt with neutral fixture names before the first push; nothing is pushed yet.
- F7: lower the verdict length in the `judge_novelty` prompt from 150-250 words to **60-100 words** (option A). The ceiling may be raised to **150** if the live before/after comparison shows evidence is lost.
- The details panel (Claim, Method, Stated result, numbered Related work) stays as it is, because the references and extra evidence are needed. A separate "reasoning" field in the response (option B) is not pursued.
- Tag `poc4-start-ui-update` is created after Increment 6 is complete.
- POC3 will become private; POC4 is the focus.
- HANDOVER.md and the two handoff files are rewritten for POC4 in Increment 6, before the first push and before any `/compact`.

## Increments

| Inc | Content | Touches | Status |
|---|---|---|---|
| 1 | Hide fixture names: rebuild the baseline with neutral names, read fixture paths from `.env` | `test_rvos_poc.py`, `README.md`, 3 history docs | DONE (commits `ca3424f`, `db47ff0`; owner review confirmed 2026-10-06) |
| 0 | Commit `CLAUDE.md`, `README.md` and this tracker | docs | DONE once committed (awaiting owner approval of the diff) |
| 2 | UI fixes: P4-05, P4-08, P4-09, P4-16 | `static/index.html`, `test_app.py` | DONE in the working tree; awaiting owner review and commit approval |
| 3 | F6 temperature + F7 verdict length + flaky-test study | `rvos_poc.py`, tests | OPEN |
| 4 | Truncation note (D1 UI part) + F15 shared numbering helper | `app.py`, `rvos_poc.py`, `index.html` | OPEN |
| 5 | F12 mocked test + D2 retrieval-relevance investigation | tests, investigation note | OPEN |
| 6 | Wrap-up: regenerate `pytest_output.txt`, close the register, rewrite HANDOVER + handoff files, tag, then push | docs | OPEN |

## Issues

| ID | Source | Issue | Planned fix | Inc | Status |
|---|---|---|---|---|---|
| P4-01 | owner request | Fixture file names and an author name appear in public files (`test_rvos_poc.py` 22 times, README 3, `pytest_output.txt` 2, findings register 2, HANDOVER 1) | Fixture paths read from `.env`; neutral test names; rebuild the baseline commit. Verified: zero hits in every commit, message and blob; live tests 4 passed; CI-like clone 48 passed, 5 skipped. | 1 | DONE (owner review confirmed) |
| P4-02 | F7 | Verdict is long because the prompt asks for 150-250 words (264 words in the run logged as F7; the two POC4 dry-run verdicts were not word-counted) | Prompt range to 60-100 words; ceiling 150 held in reserve; live before/after, 3 runs per fixture | 3 | OPEN |
| P4-03 | F6 | No `temperature` on either model call; verdicts vary between runs | `RVOS_TEMPERATURE`, default 0.2. First confirm the API accepts `temperature` for the model in use. | 3 | OPEN |
| P4-04 | live run, 2026-10-03 | One live reasoning test failed in a full run and passed on re-run | Repeat the live tests after P4-03 and record the failure rate | 3 | OPEN |
| P4-05 | UI dry run | The Verdict cites works as "[2]" but the list is hidden until "Show details" | A "Cited in the verdict" list inside the Verdict card, built from the `[n]` numbers in the Verdict text and looked up in the related-work list (deduplicated, numbers matching no work ignored, hidden when none). Browser-verified against a stub in dark/1000px and light/380px. The cited works also still appear in the full Related work list when details are open. | 2 | DONE (awaiting owner review) |
| P4-06 | D1 | The 12,000-character truncation is not disclosed in the UI | Flag in the response, note on the page | 4 | OPEN |
| P4-07 | F15 | Citation numbering is duplicated in `run()` and `app.py` | One shared helper | 4 | OPEN |
| P4-08 | UI dry run | Status line says "about a minute"; live runs took about 12 seconds | Status line now reads "this usually takes under a minute" | 2 | DONE (awaiting owner review) |
| P4-09 | UI dry run | `GET /favicon.ico` returns 404 in the server log | Inline SVG icon in the page; the browser no longer requests `/favicon.ico` (0 requests in the stub run) | 2 | DONE (awaiting owner review) |
| P4-10 | F12 | The "insufficient evidence" verdict path is untested | Mocked test | 5 | OPEN |
| P4-11 | D2 | Retrieval relevance: the judge called 3 of 8 results unrelated in one run | Investigate first, then decide | 5 | OPEN |
| P4-12 | F17 | The first OpenAlex key was exposed in a traceback in the POC3 chat session | Owner to rotate the key at OpenAlex; confirm here when done | - | DONE (owner confirmed rotation, 2026-10-06) |
| P4-13 | Hand-over 5 | `pytest_output.txt` is stale and the register is not closed | Regenerate from a full local run; close the register | 6 | OPEN |
| P4-14 | git | LF/CRLF warnings on every git command | Add a `.gitattributes` file | 6 | OPEN |
| P4-15 | handovers | HANDOVER.md and both handoff files describe POC3 | Rewrite for POC4 | 6 | OPEN |
| P4-16 | F14 | A related work with no abstract has not been seen in a live browser run | Confirmed in a real browser against a stub: the greyed item and its "no abstract, not assessed" note render, in both the cited list and the full list. A live run that produces a work without an abstract cannot be forced; re-check opportunistically. | 2 | DONE via stub (awaiting owner review) |
| W1 | register | The graph is compiled on every request | Fine for a demo | - | WATCH |
| W3 | register | The judge skips the number of a work with no abstract, so the list can start at [2] | Consistent with the report | - | WATCH |
| W5 | register | PyAlex client library not used | Revisit if a feature needs it | - | WATCH |
