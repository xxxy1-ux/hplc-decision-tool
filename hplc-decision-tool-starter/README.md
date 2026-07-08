# HPLC Decision Tool Starter

A minimal GitHub-ready Flask web app for an HPLC troubleshooting decision tool.

## What it does

- Takes HPLC peak data from a web form
- Calculates k, Rs, alpha, N and HETP in Python
- Builds a deterministic composite key
- Fires a rule from a Lookup_Master-style dictionary
- Displays calculated results and recommendation

## Run locally

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# Windows: venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Run tests

```bash
pytest
```

## Deploy from GitHub to Render

1. Push this folder to GitHub.
2. Go to Render.
3. New Web Service.
4. Connect your GitHub repo.
5. Build command:

```bash
pip install -r requirements.txt
```

6. Start command:

```bash
gunicorn app:app
```

## Important

This starter keeps the decision logic server-side in Python.
Do not move the HPLC decision logic into JavaScript.
