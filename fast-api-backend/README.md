# FastAPI backend for summaries and code reviews (Gemini)

## Setup

1. Create and activate a venv (optional):

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your Gemini API key (free tier works):

```bash
export GEMINI_API_KEY=your_key_here
```

## Run

```bash
uvicorn summary.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- GET /           → Health
- GET /summary    → Summarize latest commit or a given commit
  - Query: `commit` (optional)
- GET /code-review → Review latest commit or PR range
  - Query: `base_ref` (optional), e.g. `origin/main`

## Notes
- The service shells out to `git`, so run it inside a Git repo with history available.
- Diffs are truncated at ~250KB for token safety.


