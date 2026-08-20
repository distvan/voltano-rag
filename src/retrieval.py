"""Query-time embedding and similarity search against the pre-populated vector store.

Only queries are embedded here. Document chunks were embedded once, offline, by
the private ingestion pipeline; this module only ever reads `document_chunks`.
"""
import os
from dataclasses import dataclass

import voyageai

from . import db

EMBED_MODEL = "voyage-4"

_voyage_client: voyageai.Client | None = None


def get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _voyage_client


@dataclass
class Chunk:
    source_doc: str
    section_ref: str | None
    text: str
    similarity: float


def embed_query(query: str) -> list[float]:
    return get_voyage_client().embed([query], model=EMBED_MODEL, input_type="query").embeddings[0]


def search_filtered(query: str, allowed_docs, k: int = 5) -> list[Chunk]:
    q_emb = embed_query(query)
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT source_doc, section_ref, chunk_text, embedding <=> %s::vector AS distance "
            "FROM document_chunks WHERE source_doc = ANY(%s) ORDER BY distance ASC LIMIT %s",
            (q_emb, list(allowed_docs), k),
        ).fetchall()
    finally:
        conn.close()
    return [
        Chunk(source_doc=doc, section_ref=ref, text=text, similarity=1 - distance)
        for doc, ref, text, distance in rows
    ]
