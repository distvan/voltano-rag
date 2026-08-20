"""Best-effort pointer to the (paid) MSZ standard likely covering a topic the
free-tier corpus can't answer - shown only alongside a "red" (no grounded
source) answer, and never presented as a citation from our own corpus.

Deliberately a small, manually curated table instead of an LLM guess: an
LLM-generated standard designation risks citing a wrong or nonexistent
number, which would violate the "no source -> no answer" discipline this
project is built around. Every entry here is a designation we're actually
confident about. Extend by adding rows, not by asking a model to invent one.
"""
import re
import unicodedata
from dataclasses import dataclass

MSZT_SALES_URL = "https://ugyintezes.mszt.hu/szabvanyertekesites"


@dataclass
class StandardHint:
    designation: str
    title: str
    url: str = MSZT_SALES_URL


def _normalize(s: str) -> str:
    s = s.lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_HINTS: list[tuple["re.Pattern[str]", StandardHint]] = [
    (
        re.compile(r"napelem|hmke|haztartasi meretu kisero|photovolt|\bpv\b"),
        StandardHint(
            designation="MSZ HD 60364-7-712",
            title="Napelemes (PV) energiaellátó rendszerek",
        ),
    ),
    (
        re.compile(r"elektromos jarmu|ev.?tolt|toltoallomas|toltopont|elektromobil"),
        StandardHint(
            designation="MSZ HD 60364-7-722",
            title="Elektromos járművek töltőberendezései",
        ),
    ),
]


def suggest_standard(query: str) -> StandardHint | None:
    """Returns a hint only for the current product wedge (HMKE/napelem, EV-töltés) -
    no entry for other topics means "we're not confident enough to guess", not
    "there's no relevant standard"."""
    nq = _normalize(query)
    for pattern, hint in _HINTS:
        if pattern.search(nq):
            return hint
    return None
