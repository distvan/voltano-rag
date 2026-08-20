"""Streamlit demo for the Voltano RAG answer-generation layer.

Thin UI over `answer_question()` - no data, no ingestion, just a browser
front-end for the already-validated backend logic in src/.

Run with: streamlit run app.py
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.answer import answer_question
from src.config import check_env

CONFIDENCE_LABEL = {
    "green": ("🟢", "Megbízható"),
    "yellow": ("🟡", "Részleges / értelmezést igénylő"),
    "red": ("🔴", "Nem található megbízható válasz a forrásokban"),
}

EXAMPLE_QUESTIONS = [
    "Mennyi időn belül kell visszakapcsolni a fogyasztót a tartozás rendezése után az MVM Démásznál?",
    "Mi a szabály az MVM-nél a visszakapcsolásról?",
    "Mekkora teljesítményig számít HMKE-nek egy napelemes rendszer?",
    "Hogyan történik a társasházi energiaközösség HMKE-elszámolása?",
]

st.set_page_config(page_title="Voltano RAG demo", page_icon="⚡")

st.title("⚡ Voltano RAG demo")
st.caption(
    "HMKE (napelem) témában, 2 jogszabály + a MEKH Elosztói Szabályzat + mind a 6 "
    "elosztói engedélyes üzletszabályzata alapján. Válaszol, ha a forrásokban van "
    "megalapozott válasz - egyébként inkább visszakérdez vagy jelzi, hogy nem tudja."
)

try:
    check_env()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

if "query" not in st.session_state:
    st.session_state.query = ""

with st.sidebar:
    st.subheader("Példakérdések")
    for q in EXAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state.query = q

query = st.text_area("Kérdés", key="query", height=80)
ask = st.button("Kérdezek", type="primary")

if ask and query.strip():
    with st.spinner("Keresés és válaszgenerálás..."):
        result = answer_question(query.strip())

    if result.status == "needs_clarification":
        st.info(f"**Visszakérdezés:** {result.message}")
    else:
        icon, label = CONFIDENCE_LABEL.get(result.confidence, ("", result.confidence))
        provider_label = result.provider or "nem szolgáltatófüggő"
        st.markdown(f"{icon} **{label}** · {provider_label}")
        st.markdown(result.answer)
        if result.sources:
            with st.expander("Források"):
                for s in result.sources:
                    st.markdown(f"- {s}")
elif ask:
    st.warning("Írj be egy kérdést.")
