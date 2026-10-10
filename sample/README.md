# Sample paper and recorded example

The hosted demo serves two files from this folder, so it never needs an upload
and has something to show if a live run fails.

| File | What it is |
|---|---|
| `paper.txt` | The sample paper as plain text, served at `/sample/paper` and used by the "Use the sample paper" button. |
| `recorded_report.json` | A stored Report for that paper, served at `/sample/recorded` and always shown with the label "Recorded result, not live". |

## The sample paper

- **Paper:** G. M. Foody (2023), "Challenges in the real world use of classification
  accuracy metrics: From recall and precision to the Matthews correlation
  coefficient", PLOS ONE 18(10): e0291908.
- **Identifier:** DOI 10.1371/journal.pone.0291908
- **Licence:** CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Checked in the
  publisher's own XML, which carries the licence statement, and in the PDF's copyright
  line, and listed as `cc-by` in OpenAlex on 2026-10-10.
- **Changes made (CC BY asks for this):** the text was extracted from the publisher's
  XML (`https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0291908&type=manuscript`).
  Kept: the title, the abstract and the body paragraphs. Left out: figures, tables,
  formulas (marked `[formula]`), references and layout. Nothing was reworded.
- Credit is shown on the page, under the sample button.

## Rules for any replacement

- Only an open-access paper whose licence allows redistribution and changes, for
  example CC BY. **Not** NC (non-commercial) or ND (no derivatives): a text copy is a
  change. This repository is public.
- Never an NDA paper, and nothing from `Docs/Test/`.
- Count the forbidden terms in its text first (`test_repo_hygiene.py` cannot look
  inside a PDF), and check the licence in the paper itself, not only in a database.
- Change this section and the credit line on the page together.

## Making `recorded_report.json`

It is the JSON the app returns for the sample paper. One live run costs API
credit, so do it deliberately, with the cost agreed first:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000          # in one terminal
curl -s -F "file=@sample/paper.txt" http://127.0.0.1:8000/analyse > sample/recorded_report.json
```

If `DEMO_ACCESS_CODE` is set in your `.env`, add
`-H "X-Access-Code: $DEMO_ACCESS_CODE"` to the `curl` line (set the variable in
your shell first; never type the code into the command). Open the file and check
it is a Report, not an error message, before committing it.
`test_app.py` fails if a committed file is missing a Report field.
