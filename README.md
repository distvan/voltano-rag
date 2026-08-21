---
title: Voltano RAG Demo
emoji: ⚡
colorFrom: blue
colorTo: yellow
sdk: streamlit
app_file: app.py
pinned: false
---

# Voltano RAG

Backend / query & answer-generation layer for "Voltano" (working title) — an AI assistant for Hungarian electricians.

This repo holds the **data-independent** backend code: given a user question, it identifies the relevant provider (if any), retrieves context from an already-populated vector store, and generates an answer via the Claude API. It does **not** contain document ingestion, chunking, or embedding of source content — that pipeline (and the actual curated content: legal texts, distributor business rules) lives in a separate, private repo. The code here by itself isn't the defensible asset; the content and the ingestion/decision logic are.

## Status

The answer-generation layer (provider disambiguation + retrieval + a Claude call with a strict "no source → no answer" discipline and a green/yellow/red confidence label) is built and live-tested against a Neon/pgvector database populated by a private ingestion pipeline. A `cli.py` test harness and a `app.py` Streamlit demo both sit on top of the same `src/answer.answer_question()` entry point.

## Tech stack

- **Python** + the native `anthropic` SDK (no LangChain)
- **Voyage AI** — query embedding only (document embedding happens in the private ingestion pipeline)
- **Neon (Postgres + pgvector)** — vector store (read-only from this repo's perspective)
- **Streamlit** — browser demo UI over the same backend logic
- **FastAPI** — API layer (planned)

## Environment variables

See [`.env.example`](.env.example). API keys and connection strings are never committed — always loaded from environment variables.

```bash
cp .env.example .env
# fill in .env, then:
pip install -r requirements.txt
```

## Running

```bash
# CLI
python cli.py "Mennyi időn belül kell visszakapcsolni a fogyasztót az MVM Démásznál?"

# Browser demo
streamlit run app.py
```

## Deploying the demo (Hugging Face Spaces)

This repo is set up to run directly as a Streamlit-SDK Space (see the YAML block at the top of this file). Hugging Face Spaces injects secrets as regular environment variables, so no bridge code is needed - the app reads them via `os.environ` exactly like a local `.env` run.

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space), SDK = **Streamlit**.
2. Either connect this GitHub repo, or push this repo's contents to the Space's own git remote.
3. In the Space's **Settings → Variables and secrets**, add the same three keys as `.env.example`: `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `NEON_DATABASE_URL` (as secrets, not public variables).
4. The Space builds from `requirements.txt` and runs `app.py` automatically. Future pushes redeploy it.
