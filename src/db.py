"""Neon (Postgres + pgvector) connection helper.

Read-only from this repo's perspective: the document_chunks table is populated
by a separate, private ingestion pipeline (chunking, embedding, document
extraction). This module only ever SELECTs from it.
"""
import os

import psycopg
from pgvector.psycopg import register_vector


def get_conn() -> psycopg.Connection:
    """Opens a fresh connection on every call.

    Neon's "scale to zero" can drop a long-held idle connection (SSL error), so
    this repo never keeps one open across calls - each retrieval opens,
    queries, and closes its own connection.
    """
    conn = psycopg.connect(
        os.environ["NEON_DATABASE_URL"],
        autocommit=True,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )
    register_vector(conn)
    return conn
