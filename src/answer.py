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

`context_provider` (2026-08-20 product decision, see the private repo's
tech-stack-tanulo-projekt.md "Termékdöntés" entry): in the real product the
DSO should be known from context (set once per job/address), not re-parsed
from every query. Query-time name recognition (`identify_providers`) stays
in place as an override only - if the query itself names a company, that
wins over the context, since the user may be asking about a different site.
"""
from dataclasses import dataclass
from typing import Literal

from . import providers
from .generation import generate_answer
from .mszt_hints import StandardHint, suggest_standard
from .retrieval import search_filtered


@dataclass
class AnswerResult:
    status: Literal["ok", "needs_clarification"]
    message: str | None = None
    provider: str | None = None
    confidence: str | None = None
    answer: str | None = None
    sources: list[str] | None = None
    mszt_hint: StandardHint | None = None


def _build_ok_result(query: str, provider: str | None, grounded) -> AnswerResult:
    # Only offer a paid-standard pointer when we couldn't ground an answer at all -
    # a green/yellow answer already has a real source, it doesn't need a redirect.
    hint = suggest_standard(query) if grounded.confidence == "red" else None
    return AnswerResult(
        status="ok",
        provider=provider,
        confidence=grounded.confidence,
        answer=grounded.answer,
        sources=grounded.sources,
        mszt_hint=hint,
    )


def _answer_for_company(query: str, company: str, k: int) -> AnswerResult:
    allowed_docs = [providers.COMPANY_TO_DOC[company]] + list(providers.COMPANY_INDEPENDENT_DOCS)
    chunks = search_filtered(query, allowed_docs, k)
    grounded = generate_answer(query, chunks, company)
    return _build_ok_result(query, company, grounded)


def answer_question(query: str, k: int = 5, context_provider: str | None = None) -> AnswerResult:
    resolved, ambiguous_candidates = providers.identify_providers(query)

    if ambiguous_candidates:
        # A bare brand mention ("MVM", "E.ON") can't resolve on its own, but if the
        # active context happens to be one of the candidate entities, that's a real
        # signal (not a guess) - the user already told us which one they mean.
        if context_provider in ambiguous_candidates:
            return _answer_for_company(query, context_provider, k)
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
        # An explicit company name in the query always overrides the active context -
        # the user may be asking about a different job/site than the current one.
        return _answer_for_company(query, next(iter(resolved)), k)

    # No provider named in the query. If a context is set, use it directly - no need
    # to guess from retrieval at all.
    if context_provider:
        return _answer_for_company(query, context_provider, k)

    # No context either. Decide company-dependence with a search scoped ONLY to the
    # 6 company docs (not mixed with company-independent sources) - a mixed pool is
    # unreliable here because the more concentrated company-independent content can
    # crowd companies out of the top-k even when the question is genuinely
    # company-specific.
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
    return _build_ok_result(query, None, grounded)
