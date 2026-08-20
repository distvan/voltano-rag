"""Claude-based answer generation over retrieved context.

Core discipline (ported from the private repo's design principles): "no source
-> no answer" and a three-tier confidence label rather than a single
confident-sounding answer, since a wrong-but-fluent answer is worse for a
practicing electrician than a visible "not sure."
"""
import os
from typing import Literal

import anthropic
from pydantic import BaseModel

from .retrieval import Chunk

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """\
Magyar villanyszerelőknek segítesz kérdéseket megválaszolni elosztói \
üzletszabályzatok, jogszabályok és a MEKH Elosztói Szabályzat kivonatai alapján.

Szigorú szabályok:
- KIZÁRÓLAG a megadott forrásszövegekre támaszkodj. Ha a forrásokban nincs \
válasz a kérdésre, ezt mondd ki egyértelműen - ne egészítsd ki általános \
tudásból, és ne találgass.
- Minden állításodhoz add meg, melyik forrásrészlet(ek) támasztják alá.
- Értékeld a válaszod megbízhatóságát:
  - "green": a forrásszövegek egyértelműen és közvetlenül megválaszolják a kérdést.
  - "yellow": a forrásszövegek részleges vagy közvetett választ adnak, esetleg \
értelmezést igényelnek.
  - "red": a forrásszövegek nem tartalmazzák a válasz megadásához szükséges \
információt - ilyenkor az `answer` mezőben csak azt írd le, mit NEM lehet \
megválaszolni a rendelkezésre álló forrásokból, ne találgass.
- A válasz nyelve mindig magyar, még akkor is, ha ez az utasítás angolul van."""


class GroundedAnswer(BaseModel):
    confidence: Literal["green", "yellow", "red"]
    answer: str
    sources: list[str]


_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _format_context(chunks: list[Chunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        ref = c.section_ref or "(nincs alfejezet-címke)"
        parts.append(f"[Forrás {i} - {c.source_doc} - {ref}]\n{c.text}")
    return "\n\n".join(parts)


def generate_answer(query: str, chunks: list[Chunk], provider: str | None) -> GroundedAnswer:
    provider_note = f"A kérdés szolgáltatója: {provider}." if provider else "A kérdés nem szolgáltatóspecifikus."
    context = _format_context(chunks)
    user_message = (
        f"{provider_note}\n\n"
        f"Kérdés: {query}\n\n"
        f"Forrásszövegek:\n\n{context}"
    )
    response = get_client().messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
        output_format=GroundedAnswer,
    )
    return response.parsed_output
