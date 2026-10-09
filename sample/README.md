# Sample paper and recorded example

Two files belong in this folder. The hosted demo serves them so it never needs
an upload and has something to show if a live run fails.

| File | What it is |
|---|---|
| `paper.txt` | The text of one public, open-access paper, served at `/sample/paper` and used by the "Use the sample paper" button. |
| `recorded_report.json` | A stored Report for that paper, served at `/sample/recorded` and always shown with the label "Recorded result, not live". |

## Rules

- **Only an open-access paper whose licence allows redistribution** (for
  example CC BY). This repository is public.
- **Never an NDA paper**, and nothing from `Docs/Test/`.
- Record the paper's public identifier (DOI, arXiv or OpenAlex ID) and its
  licence below when the files are added.

Paper identifier: _to be added_
Licence: _to be added_

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
