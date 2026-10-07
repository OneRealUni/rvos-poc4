# Handoff: RVOS POC4, next increments (RAG and PyAlex)

Written for a fresh agent, 2026-10-07. The owner named two key improvements for POC4:
**RAG** (P4-18) and **PyAlex** (P4-19). Neither is scoped yet. **Do not assume scope;
run a grilling session first** (`mattpocock-skills:grilling`) and agree acceptance
tests before writing code.

## Hard constraints (same gates as `handoff-rvos-poc4-maintenance.md`)
- Explain git commands first; approval before every commit and push; stage by name.
- Test first; one increment per commit; the owner reviews after each.
- Ask before any live run and state the cost; never bare `pytest` locally.
- Keep NDA fixture names out of tracked files. Never print a secret.
- Verified facts to respect: `claude-sonnet-5` rejects `temperature`; a 60-100 word
  verdict changed the judgment (deferred, P4-17); retrieval relevance depends more on
  the extracted keywords than on the query shape (P4-11 note in the tracker).

## What RAG has to fix (D1 + D2)
- Today the model sees only the first `MAX_PAPER_CHARS` (12,000) characters of a paper;
  the page and the report now say so, but the rest of the paper is ignored.
- Retrieval quality depends on 3-5 keyword phrases from one extraction call.
- Questions to settle with the owner: what "read the whole paper" means (chunked
  extraction per section? a summary-then-extract pass?); cost and latency budget per
  paper; how claims from several chunks are merged into one claim and one keyword set;
  whether the Verdict should cite the paper's own passages; what the acceptance tests
  are (the overlap and novel fixtures must keep their directions); and how truncation
  is reported once chunks exist.

## What PyAlex has to respect (P4-19)
- Current `search_openalex` is one GET with: header auth (`Authorization: Bearer`, never
  a query parameter, because `requests` prints URLs in errors), retry on
  429/500/503/504, `Retry-After` honoured and capped at 30 seconds, mocked offline tests.
  A switch to PyAlex must keep all of that or replace it with something at least as
  safe, and must not leak the key into a traceback.
- Add it as a pinned dependency with an upper bound (see the `requirements.txt` policy).
- It pays off only if a feature needs it: multi-page results, filters, citation-graph
  traversal. Decide that with the owner before adopting.

## Suggested order
1. Grilling session: scope RAG and PyAlex, the acceptance tests and the cost budget.
2. Write the failing tests and a measurement plan (scratch script, small samples) first.
3. Smallest increment that moves one acceptance test; verify offline, then ask for a
   live go; review with the owner; commit.

## Suggested skills
`mattpocock-skills:grilling`, `mattpocock-skills:tdd`, `mattpocock-skills:domain-modeling`
(only if `CONTEXT.md` needs new terms such as "chunk"), `mattpocock-skills:code-review`.

## First moves
1. `git status`, `git log --oneline -10`; read `CLAUDE.md`, `CONTEXT.md`, `HANDOVER.md`
   and `Docs/review/POC4_backlog.md` (rows P4-04, P4-11, P4-17, P4-18, P4-19).
2. Ask the owner whether the grilling session should start now.
