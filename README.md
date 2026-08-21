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

## Deploying the demo (Google Cloud Run)

Chosen over Hugging Face Spaces (Streamlit SDK deprecated 2025-04; the remaining Gradio/Docker options require a paid plan to create) and Streamlit Community Cloud (real but likely slower wake-up after the free tier's idle sleep - Cloud Run's serverless cold start is on the order of seconds, built specifically for that pattern). Trade-off: needs a Google Cloud account with a credit card on file (the Always Free tier - 2M requests/month - won't auto-charge, but sign-up requires a card).

Cloud Run's Python buildpack auto-detects Streamlit from `requirements.txt` and builds a container without a Dockerfile - no need to write or maintain one. `Procfile` in this repo pins the exact start command explicitly (`streamlit run app.py`), since the repo also has `cli.py` as a second possible entry point and auto-detection shouldn't have to guess between them. Env vars (the three from `.env.example`) are regular OS environment variables here too - same `os.environ.get(...)` code path as local `.env` runs, no bridging needed (unlike Streamlit Community Cloud's `st.secrets`).

1. Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) and run `gcloud init` (creates/selects a GCP project; needs a billing account with a card on file for the Always Free tier to activate).
2. From the repo root:
   ```bash
   gcloud run deploy voltano-rag \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ANTHROPIC_API_KEY=...,VOYAGE_API_KEY=...,NEON_DATABASE_URL=...
   ```
   (`us-central1` is one of the Always Free tier regions.) For secrets you'd rather not pass on the command line, use [Secret Manager](https://docs.cloud.google.com/run/docs/configuring/services/secrets) and `--set-secrets` instead of `--set-env-vars`.
3. `gcloud` prints the service URL once the build and deploy finish. Re-run the same command to redeploy after code changes (no git integration by default, unlike Streamlit Cloud/HF Spaces).
