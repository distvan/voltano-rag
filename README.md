# Voltano RAG

Backend / query & answer-generation layer for "Voltano" (working title) — an AI assistant for Hungarian electricians.

This repo holds the **data-independent** backend code: given a user question, it identifies the relevant provider (if any), retrieves context from an already-populated vector store, and generates an answer via the Claude API. It does **not** contain document ingestion, chunking, or embedding of source content — that pipeline (and the actual curated content: legal texts, distributor business rules) lives in a separate, private repo. The code here by itself isn't the defensible asset; the content and the ingestion/decision logic are.

## Status

Early development. The retrieval and provider-disambiguation approach were prototyped against a Neon/pgvector database populated by a private ingestion pipeline; this repo is the next step: the answer-generation layer (a Claude API call over retrieved context, with a strict "no source → no answer" discipline).

## Tech stack

- **Python** + the native `anthropic` SDK (no LangChain)
- **Voyage AI** — query embedding only (document embedding happens in the private ingestion pipeline)
- **Neon (Postgres + pgvector)** — vector store (read-only from this repo's perspective)
- **FastAPI** — API layer

## Environment variables

See [`.env.example`](.env.example). API keys and connection strings are never committed — always loaded from environment variables.

```bash
cp .env.example .env
# fill in .env, then:
pip install -r requirements.txt
```
