"""Provider (DSO) name recognition and the doc-scope maps for retrieval filtering.

This logic is a direct port of the validated version from the private ingestion
repo's notebook (docs/notebooks/voyage_neon_ingest.ipynb). It is data-independent
(no chunking/embedding here), which is why it can live in this public repo, but
it must stay in sync with the `source_doc` values actually written by that
private ingestion pipeline into the `document_chunks` table.

Known trap (do not "simplify" this away): a naive substring match on the bare
alias "emasz" (MVM Émász) also matches inside "demasz" (MVM Démász, accents
stripped), so every query naming MVM Démász would also resolve to MVM Émász.
Every alias pattern below is guarded with a negative lookbehind so it can only
match at a word boundary.
"""
import re
import unicodedata

UZLETSZABALYZAT_DOCS = {
    "mvm_demasz_elosztoi_uzletszabalyzat_torzs.md": "MVM Démász",
    "eon_ede_elosztoi_uzletszabalyzat_torzs.md": "E.ON Dél-dunántúli",
    "mvm_emasz_elosztoi_uzletszabalyzat_torzs.md": "MVM Émász",
    "opus_titasz_elosztoi_uzletszabalyzat_torzs.md": "OPUS TITÁSZ",
    "elmu_halozati_elosztoi_uzletszabalyzat_torzs.md": "ELMŰ Hálózati",
    "eon_eed_elosztoi_uzletszabalyzat_torzs.md": "E.ON Észak-dunántúli",
}
COMPANY_TO_DOC = {name: doc for doc, name in UZLETSZABALYZAT_DOCS.items()}

# Company-independent sources: apply to every provider equally (laws, the
# MEKH-approved Elosztói Szabályzat technical rulebook, and near-verbatim
# boilerplate the DSOs copy from the same source into their own business
# rules - e.g. the HMKE 50 kVA definition - deduplicated at ingestion time
# into this single shared doc so a query naming no provider doesn't get
# stuck seeing ">1 company" for content that isn't actually company-specific),
# so they're always in scope regardless of which DSO (if any) a question names.
LAW_FILES = {"2007_LXXXVI_torveny.md", "273_2007_X_19_korm_rendelet.md"}
ES_FILE = "mekh_elosztoi_szabalyzat_29_torzs.md"
SHARED_FILE = "kozos_boilerplate_uzletszabalyzat.md"
COMPANY_INDEPENDENT_DOCS = LAW_FILES | {ES_FILE, SHARED_FILE}


def _normalize(s: str) -> str:
    s = s.lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s


def _alias_pattern(alias: str) -> "re.Pattern":
    return re.compile(r"(?<![a-z])" + re.escape(alias))


PROVIDER_ALIASES = {
    "MVM Démász": ["mvm demasz", "demasz"],
    "MVM Émász": ["mvm emasz", "emasz"],
    "ELMŰ Hálózati": ["elmu halozati", "elmu"],
    "OPUS TITÁSZ": ["opus titasz", "titasz"],
    "E.ON Dél-dunántúli": ["e.on del-dunantuli", "eon del-dunantuli", "del-dunantuli e.on", "del-dunantuli eon"],
    "E.ON Észak-dunántúli": ["e.on eszak-dunantuli", "eon eszak-dunantuli", "eszak-dunantuli e.on", "eszak-dunantuli eon"],
}
PROVIDER_PATTERNS = {
    canonical: [_alias_pattern(a) for a in aliases]
    for canonical, aliases in PROVIDER_ALIASES.items()
}

BRAND_ONLY_CANDIDATES = {
    "MVM": {"MVM Démász", "MVM Émász"},
    "E.ON": {"E.ON Dél-dunántúli", "E.ON Észak-dunántúli"},
}
BRAND_PATTERNS = {brand: _alias_pattern(_normalize(brand)) for brand in BRAND_ONLY_CANDIDATES}


def identify_providers(query: str):
    """Returns (resolved, ambiguous_candidates).

    resolved: set of unambiguously named provider(s) (usually 0 or 1; >1 means
    the query names multiple providers at once).
    ambiguous_candidates: set of possible providers when only a shared brand
    name (e.g. "MVM", "E.ON") is used without disambiguating which entity is
    meant - in that case `resolved` is empty.
    """
    nq = _normalize(query)
    resolved = {c for c, pats in PROVIDER_PATTERNS.items() if any(p.search(nq) for p in pats)}
    if resolved:
        return resolved, None
    for brand, pattern in BRAND_PATTERNS.items():
        if pattern.search(nq):
            return set(), BRAND_ONLY_CANDIDATES[brand]
    return set(), None
