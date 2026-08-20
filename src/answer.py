"""Top-level entry point: question in, grounded answer (or a clarifying question) out.

This is a direct port of the validated `answer_with_disambiguation()` logic from
the private repo's notebook, extended to call the LLM for the actual answer
instead of returning raw retrieved chunks. See providers.py for why the
clarify-when-ambiguous behavior is intentionally conservative: an earlier,
more "helpful" version tried to skip clarification when a query named no
provider but scored similarly against law text and company text, on the
assumption a small score gap meant the topic was company-agnostic. Live
testing showed that gap does not reliably distinguish a genuinely
company-agnostic question from a genuinely company-specific one, so a
silent-wrong-answer risk was traded for one extra clarifying question in the
rare company-agnostic case.
"""
from dataclasses import dataclass
from typing import Literal

from . import providers
from .generation import generate_answer
from .retrieval import search_filtered


@dataclass
class AnswerResult:
    status: Literal["ok", "needs_clarification"]
    message: str | None = None
    provider: str | None = None
    confidence: str | None = None
    answer: str | None = None
    sources: list[str] | None = None


def answer_question(query: str, k: int = 5) -> AnswerResult:
    resolved, ambiguous_candidates = providers.identify_providers(query)

    if ambiguous_candidates:
        candidates_str = " vagy ".join(sorted(ambiguous_candidates))
        return AnswerResult(
            status="needs_clarification",
            message=f"A kérdésben szereplő márkanév önmagában nem egyértelmű - melyik entitásra gondoltál: {candidates_str}?",
        )

    if len(resolved) > 1:
        return AnswerResult(
            status="needs_clarification",
            message=f"Több szolgáltató is szerepel a kérdésben ({', '.join(sorted(resolved))}) - egyszerre csak egyre tudok válaszolni, melyikre gondoltál?",
        )

    if len(resolved) == 1:
        company = next(iter(resolved))
        allowed_docs = [providers.COMPANY_TO_DOC[company]] + list(providers.COMPANY_INDEPENDENT_DOCS)
        chunks = search_filtered(query, allowed_docs, k)
        grounded = generate_answer(query, chunks, company)
        return AnswerResult(
            status="ok",
            provider=company,
            confidence=grounded.confidence,
            answer=grounded.answer,
            sources=grounded.sources,
        )

    # No provider named. Decide company-dependence with a search scoped ONLY to
    # the 6 company docs (not mixed with company-independent sources) - a mixed
    # pool is unreliable here because the more concentrated company-independent
    # content can crowd companies out of the top-k even when the question is
    # genuinely company-specific.
    company_chunks = search_filtered(query, list(providers.UZLETSZABALYZAT_DOCS.keys()), k)
    companies_present = {providers.UZLETSZABALYZAT_DOCS[c.source_doc] for c in company_chunks}

    if len(companies_present) > 1:
        all_companies = ", ".join(sorted(providers.UZLETSZABALYZAT_DOCS.values()))
        return AnswerResult(
            status="needs_clarification",
            message=f"A kérdés szolgáltatófüggő szabályra vonatkozhat, de nem neveztél meg elosztót. Melyikre vonatkozik a kérdésed ({all_companies})?",
        )

    # Topic isn't (or barely is) company-specific - use the full pool.
    allowed_docs = list(providers.UZLETSZABALYZAT_DOCS.keys()) + list(providers.COMPANY_INDEPENDENT_DOCS)
    chunks = search_filtered(query, allowed_docs, k)
    grounded = generate_answer(query, chunks, None)
    return AnswerResult(
        status="ok",
        provider=None,
        confidence=grounded.confidence,
        answer=grounded.answer,
        sources=grounded.sources,
    )
