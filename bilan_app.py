"""BilanKine — point d'entrée de l'application Streamlit.

Lancer l'application avec :
    streamlit run bilan_app.py
"""

import streamlit as st


st.set_page_config(
    page_title="BilanKine",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)


st.title("🩺 BilanKine")
st.subheader("Bilan de kinésithérapie")
st.write(
    "Bienvenue dans BilanKine. Cette première version sert de point de départ "
    "pour construire votre application de bilan de kinésithérapie."
)

st.divider()

with st.form("patient_form"):
    st.header("Informations du patient")

    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nom")
    with col2:
        prenom = st.text_input("Prénom")

    motif = st.text_area("Motif de consultation", height=120)
    date_bilan = st.date_input("Date du bilan")
    submitted = st.form_submit_button("Enregistrer le bilan")

if submitted:
    if not nom.strip() or not prenom.strip():
        st.warning("Veuillez renseigner le nom et le prénom du patient.")
    else:
        st.success(
            f"Bilan initialisé pour {prenom} {nom} le {date_bilan.strftime('%d/%m/%Y')}."
        )
        if motif.strip():
            st.info(f"Motif renseigné : {motif}")

st.caption("BilanKine — prototype Streamlit")
