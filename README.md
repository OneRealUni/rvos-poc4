# RVOS POC4 -- status and how to run it

POC4 is POC3 with a new UI. The reasoning pipeline, the loaders, the web
route and the CI are unchanged (see CLAUDE.md).

## What's new in POC4
- A dark-first page (with a light variant that follows your system setting)
  and a clearer layout, in plain HTML/CSS/JS with no external assets.
- After a run the page shows the novelty Verdict first, with the related
  works it cites listed underneath. A "Show details" button reveals the
  Claim, Method, Stated result and numbered Related work, and hides them
  again. The details are collapsed at the start of each run.
- The live tests read their NDA fixture paths from `.env` instead of naming
  the papers in the repo (see Tests below).
- Nothing else changed in the app: `static/index.html` and one test in
  `test_app.py`. The `/analyse` response is the same as in POC3.

## Setup (about 5 minutes)

Python 3.11 is what CI uses.

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste in your real Anthropic API key. Also set
`OPENALEX_MAILTO`, and an `OPENALEX_API_KEY` (free from openalex.org):
anonymous OpenAlex access is the first traffic it drops under load, which
showed up as 503/504 errors in POC3. `.env` is gitignored.

## Run it

```bash
python rvos_poc.py "path/to/paper.txt"            # .txt
python rvos_poc.py "Docs/Test/some_paper.pdf"     # .pdf
python rvos_poc.py "Docs/Test/some_paper.docx"    # .docx
```

The report is written next to the input file as `<name>_report.md`.

Loading is plain text extraction, no cleanup: PDFs give each page's text
(two-column layouts may interleave), DOCX gives body paragraphs and table
cells (headers and footers are skipped). Only the first 12,000
characters reach the model. The run stops with an error
(exit status 1) for any other file type, and for a file with no
extractable text -- e.g. a scanned, image-only PDF, since OCR is not
supported.

## Run the UI

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

Run it from this folder: `app:app` loads `app.py` from the current
directory, and the page is read from `static/index.html` on disk, so what
runs is whatever is in the folder, committed or not. Changes to the page show
on a browser refresh; changes to the Python files need a restart.

Then open http://127.0.0.1:8000, choose a .pdf, .docx or .txt paper and
press "Assess novelty". A run takes roughly 10 to 60 seconds. The page
shows the Verdict, with the related works it cites by number (for example
"[2]") listed under it. Press "Show details" for the same Report as the
command line (claim, method, stated result, related work). The Verdict is
the model's text as written, so it can run to several paragraphs; the page
shows the first six lines and a "Read more" button when the text is longer.
Nothing is saved: the upload goes to a temp file that is
deleted straight away, and the report is not written anywhere. Related works
with no abstract are greyed out because the verdict never saw them. Uploads
over 10 MB are rejected. This is a demo: it has no login and should only be
bound to localhost.

## Tests

```bash
ruff check .
pytest -v test_loading.py test_app.py test_pipeline_offline.py
```

Name the files. A bare `pytest` on a machine with a real `.env` and the
`Docs/Test/` fixtures also runs the four live reasoning tests, which spend
Anthropic credit and OpenAlex quota. CI has neither, so there they skip.

`test_loading.py`, `test_app.py`, `test_pipeline_offline.py` and
`test_repo_hygiene.py` need no API key or NDA files (`test_loading.py`
generates tiny PDF/DOCX files on the fly; `test_app.py` replaces the
pipeline with a fake; `test_pipeline_offline.py` mocks the model and
OpenAlex). CI shows 54 passed and 5 skipped. `test_rvos_poc.py` calls the
live Anthropic and OpenAlex APIs and needs two local NDA fixture papers: set
their paths in `.env` as `RVOS_FIXTURE_OVERLAP` (a near-duplicate of a
published paper) and `RVOS_FIXTURE_NOVEL` (unpublished work), relative to
this folder or absolute. The defaults are `Docs/Test/fixture_overlap.txt` and
`Docs/Test/fixture_novel.txt`. Run it deliberately with
`pytest -v test_rvos_poc.py`. It skips if the files or the API key are
missing. `Docs/Test/*` is gitignored -- never commit NDA papers, and keep
their file names out of tracked files: list the terms to keep out in `.env` as
`RVOS_FORBIDDEN_TERMS` (comma-separated) and `test_repo_hygiene.py` checks the
tracked files for them (it skips when the variable is unset, as in CI).

## Everything else

Terminology (load vs. extract, paper text, verdict) is defined in
CONTEXT.md. The history of POC3, including three code-review hand-overs and
the OpenAlex incident, is in HANDOVER.md. The findings register and fix plan
(`Docs/review/`) list what is fixed and what is still open, for
example verdict length (F7), temperature (F6) and the 12,000-character
truncation (D1).
