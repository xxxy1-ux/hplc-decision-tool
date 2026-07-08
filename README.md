# HPLC Method Troubleshooting Decision Tool

A Flask + Jinja2 + Bootstrap 5 web app implementing the updated HPLC Decision Tool specification.

## What is included

- Server-side deterministic Python rule engine.
- Composite-key lookup against Lookup_Master.
- 6-rule Lookup_Resolution sub-matrix.
- Calculations for k, Rs, alpha, N, and HETP.
- Merged-vs-absent diagnostic test panel for fewer than 7 peaks.
- Lever tracker L1-L6.
- Validation log and chromatogram database using SQLite through Flask-SQLAlchemy.
- CSV export for the validation log.
- Bootstrap interface matching the 10-page structure in the specification.
- Pytest tests for key deterministic logic.

## Important implementation notes

1. The uploaded specification still contains duplicate composite keys for Rules 10/18 and 11/19. A normal Python dictionary cannot store two active values for the same key. This implementation keeps Rules 10 and 11 as the active lookup rules and preserves Rules 18 and 19 as duplicate guidance shown in the documentation/results when relevant.
2. The specification uses detailed Rs categories (`FAIL_SINGLE`, `FAIL_MULTI`, `FAIL_SEVERE`) but some matrix rows use generic `FAIL`. The engine calculates detailed Rs status for display, then falls back to generic `FAIL` for keys that require it.
3. The UI provides one width field named `USP Width / W½`. It is used for both Rs and N/HETP because the supplied page inventory lists one width field, while the formula section references USP base width for Rs and half-height width for N.
4. AI parsing and AI explanation are represented as optional/fallback areas only. No AI is used in the decision path.

## How to run

```bash
cd hplc_decision_tool_v2
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Run tests

```bash
pytest -q
```

## Project structure

```text
app.py                  Flask routes and database actions
hplc_engine.py          Deterministic calculation and diagnosis engine
rules.py                Lookup_Master and Lookup_Resolution data
templates/              Jinja2 templates
static/css/styles.css   Visual design
static/js/app.js        UX helpers only, no decision logic
models.py               SQLite models
requirements.txt        Dependencies
tests/                  Pytest suite
```
