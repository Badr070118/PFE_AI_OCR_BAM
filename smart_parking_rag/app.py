from __future__ import annotations

import streamlit as st

from rag_engine import ask_question


st.set_page_config(page_title="Assistant IA du Parking Intelligent", page_icon="P", layout="wide")

st.title("Assistant IA du Parking Intelligent")
st.write("Posez une question en langage naturel sur le parking.")


def run_question(q: str) -> None:
    with st.spinner("Analyse en cours..."):
        response = ask_question(q)
    st.session_state.last_question = q
    st.session_state.last_answer = response.get("answer", "Aucune réponse.")


if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""


quick_questions = [
    "Qui est entré dans le parking aujourd’hui ?",
    "Quels véhicules ont accédé au parking aujourd’hui ?",
    "Combien d’employés sont actuellement présents ?",
    "Quels employés sont actuellement dans le parking ?",
    "Afficher les 10 derniers accès au parking",
    "Quelles plaques sont autorisées ?",
    "Quels véhicules ont été refusés ?",
    "Qui arrive souvent en retard ?",
]

st.subheader("Questions rapides")
cols = st.columns(4)
for idx, question in enumerate(quick_questions):
    with cols[idx % 4]:
        if st.button(question, use_container_width=True):
            run_question(question)


st.subheader("Question libre")
query = st.text_input("Votre question", value=st.session_state.last_question)
if st.button("Demander"):
    if query.strip():
        run_question(query.strip())

if st.session_state.last_answer:
    st.subheader("Réponse")
    st.write(st.session_state.last_answer)
