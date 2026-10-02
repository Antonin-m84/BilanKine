"""BilanKine — application Streamlit structurée pour bilan kinésithérapique.

Lancer l'application avec :
    streamlit run bilan_app.py
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import streamlit as st


# -------------------------------
# Utilitaires robustes
# -------------------------------
def to_float(value: Any) -> float | None:
    """Convertit en float si possible, sinon None."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp_eva(value: Any) -> float | None:
    """Borne une EVA entre 0 et 10."""
    raw = to_float(value)
    if raw is None:
        return None
    return max(0.0, min(10.0, raw))


def calcul_lsi(cote_atteint: float | None, cote_sain: float | None) -> float | None:
    """Calcule un LSI en % en évitant division par zéro."""
    if cote_atteint is None or cote_sain in (None, 0):
        return None
    return round((cote_atteint / cote_sain) * 100, 1)


def statut_objectif(score: float | None, seuil: float) -> str:
    """Retourne un statut simple d'atteinte d'objectif."""
    if score is None:
        return "À surveiller"
    if score >= seuil:
        return "Atteint"
    if score >= max(0.0, seuil - 10):
        return "À surveiller"
    return "Non atteint"


def as_iso(value: Any) -> Any:
    """Sérialisation minimale JSON."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def badge_statut(statut: str) -> str:
    color = {
        "Atteint": "🟢",
        "À surveiller": "🟠",
        "Non atteint": "🔴",
    }
    return f"{color.get(statut, '⚪')} {statut}"


# -------------------------------
# Constantes UI
# -------------------------------
REGIONS_CORPORELLES = [
    "Cervicale",
    "Épaule",
    "Coude/Poignet",
    "Dorsale",
    "Lombaire",
    "Bassin/SI",
    "Hanche",
    "Genou",
    "Cheville/Pied",
]

SYMPTOMES = ["Douleur", "Paresthésie", "Hypoesthésie", "Faiblesse"]

RED_FLAGS = [
    "Traumatisme important récent",
    "Fièvre, frissons ou suspicion d'infection",
    "Cancer connu ou suspicion clinique",
    "Perte de poids inexpliquée",
    "Douleur nocturne atypique/non mécanique",
    "Déficit neurologique progressif",
    "Anesthésie en selle",
    "Troubles sphinctériens récents",
    "Signes vasculaires (ischémie, douleur mollet suspecte, asymétrie marquée)",
    "Altération systémique (fatigue majeure, état général altéré)",
]

TESTS_CIBLES: dict[str, list[tuple[str, str]]] = {
    "Lombaire/Bassin": [
        ("SLR / Lasègue", "Élévation jambe tendue ; noter angle et reproduction symptomatique."),
        ("Slump test", "Flexion rachidienne + extension genou ; comparer D/G."),
        ("Prone instability", "Test de stabilité lombaire en procubitus."),
    ],
    "Cervicale": [
        ("Spurling", "Compression foraminale cervicale en extension/rotation."),
        ("Distraction cervicale", "Traction douce ; noter soulagement/provocation."),
        ("ULNT1 médian", "Neurodynamique du nerf médian."),
    ],
    "Épaule": [
        ("Jobe (Empty can)", "Abduction dans plan scapulaire, résistance."),
        ("Hawkins-Kennedy", "Conflit sous-acromial en flexion/rotation interne."),
        ("External Rotation Lag", "Recherche déficit coiffe postéro-supérieure."),
    ],
    "Genou": [
        ("Lachman", "Translation tibiale antérieure (LCA)."),
        ("McMurray", "Rotation/varus-valgus pour ménisque."),
        ("Valgus 30°", "Stabilité ligament collatéral médial."),
    ],
    "Hanche": [
        ("FADIR", "Flexion, adduction, rotation interne."),
        ("FABER", "Flexion-abduction-rotation externe."),
        ("Thomas modifié", "Raideur fléchisseurs de hanche."),
    ],
    "Cheville/Pied": [
        ("Tiroir antérieur cheville", "Stabilité talo-fibulaire antérieure."),
        ("Talar tilt", "Stabilité ligamentaire latérale."),
        ("Knee to wall", "Dorsiflexion fonctionnelle mesurée."),
    ],
    "Coude/Poignet": [
        ("Cozen", "Épicondylalgie latérale contre résistance."),
        ("Phalen", "Canal carpien en flexion maintenue."),
        ("Tinel poignet", "Percussion trajet médian."),
    ],
}

LASLETT_TESTS = [
    "Distraction",
    "Compression",
    "Thigh thrust",
    "Sacral thrust",
    "Gaenslen",
]


def render_test(prefix: str, nom: str, description: str) -> dict[str, Any] | None:
    active = st.checkbox(f"Activer : {nom}", key=f"{prefix}_{nom}_active")
    if not active:
        return None

    with st.expander(f"Détail — {nom}", expanded=False):
        st.caption(description)
        resultat = st.radio(
            "Résultat",
            ["Positif", "Négatif", "Non réalisé"],
            horizontal=True,
            key=f"{prefix}_{nom}_resultat",
        )
        douleur = st.slider(
            "EVA provoquée",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key=f"{prefix}_{nom}_eva",
        )
        cote = st.selectbox(
            "Côté", ["Bilatéral", "Droite", "Gauche", "NA"], key=f"{prefix}_{nom}_cote"
        )
        score = st.number_input(
            "Score éventuel",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=1.0,
            key=f"{prefix}_{nom}_score",
        )
        commentaire = st.text_area("Commentaire", key=f"{prefix}_{nom}_commentaire")

    return {
        "test": nom,
        "resultat": resultat,
        "eva_provoquee": douleur,
        "cote": cote,
        "score": score,
        "commentaire": commentaire,
    }


st.set_page_config(
    page_title="BilanKine",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "marquages_body_chart" not in st.session_state:
    st.session_state.marquages_body_chart = []

st.title("🩺 BilanKine — Outil structuré de bilan kinésithérapique")
st.warning(
    "⚠️ Outil d'aide à la documentation et au raisonnement clinique. "
    "Les tests doivent être sélectionnés et interprétés par un professionnel formé. "
    "Les seuils/normes varient selon la population, le protocole et le contexte. "
    "Tout drapeau rouge impose une évaluation médicale selon les procédures locales.",
    icon="🚨",
)

if st.button("🔄 Réinitialiser tout le bilan", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

onglets = st.tabs(
    [
        "Identité & contexte",
        "Douleur & body chart",
        "Red flags",
        "Examen général",
        "Modules conditionnels",
        "Tests ciblés",
        "Fonction/force/reprise",
        "Synthèse & export",
        "Références et limites",
    ]
)

# 1) Identité
with onglets[0]:
    st.subheader("Identité / consentement / contexte")
    c1, c2, c3 = st.columns(3)
    with c1:
        date_bilan = st.date_input("Date du bilan", value=date.today(), key="date_bilan")
        nom_patient = st.text_input("Nom/identifiant patient", key="nom_patient")
    with c2:
        prenom_patient = st.text_input("Prénom", key="prenom_patient")
        consentement = st.checkbox("Consentement informé vérifié", key="consentement")
    with c3:
        motif = st.text_area("Motif principal", key="motif", height=90)

    col_a, col_b = st.columns(2)
    with col_a:
        profession = st.text_input("Profession", key="profession")
        sport = st.text_input("Sport / activité physique", key="sport")
        antecedents = st.text_area("Antécédents pertinents", key="antecedents")
    with col_b:
        traitements = st.text_area("Traitements en cours", key="traitements")
        objectifs_patient = st.text_area("Objectifs du patient", key="objectifs_patient")
        limitations = st.text_area("Limitations fonctionnelles", key="limitations")

# 2) Douleur + body chart
with onglets[1]:
    st.subheader("Douleur")
    c1, c2 = st.columns(2)
    with c1:
        localisation = st.text_area("Localisation libre", key="douleur_localisation")
        regions_principales = st.multiselect(
            "Régions principales",
            REGIONS_CORPORELLES,
            key="regions_principales",
        )
        cote_douleur = st.selectbox("Côté dominant", ["Droite", "Gauche", "Bilatéral", "Central"], key="cote_douleur")
        description_douleur = st.text_area("Description / qualité", key="description_douleur")
    with c2:
        comportement = st.text_area("Comportement mécanique (24h, charges, repos)", key="comportement_douleur")
        irritabilite = st.select_slider(
            "Irritabilité", options=["Faible", "Modérée", "Élevée"], value="Modérée", key="irritabilite"
        )
        evolution = st.selectbox("Évolution", ["Aiguë", "Subaiguë", "Chronique", "Fluctuante"], key="evolution")

    eva1, eva2, eva3, eva4 = st.columns(4)
    with eva1:
        eva_repos = clamp_eva(st.number_input("EVA repos", min_value=0.0, max_value=10.0, value=0.0, step=0.5, key="eva_repos"))
    with eva2:
        eva_activite = clamp_eva(st.number_input("EVA activité", min_value=0.0, max_value=10.0, value=0.0, step=0.5, key="eva_activite"))
    with eva3:
        eva_meilleure = clamp_eva(st.number_input("EVA meilleure", min_value=0.0, max_value=10.0, value=0.0, step=0.5, key="eva_meilleure"))
    with eva4:
        eva_pire = clamp_eva(st.number_input("EVA pire", min_value=0.0, max_value=10.0, value=0.0, step=0.5, key="eva_pire"))

    st.divider()
    st.subheader("Body chart semi-interactive (grille régionale)")
    st.caption(
        "Choix technique : grille régionale structurée (plus stable que SVG cliquable pur dans Streamlit sans dépendance externe)."
    )

    region_col, side_col, sym_col = st.columns(3)
    with region_col:
        region_chart = st.selectbox("Région", REGIONS_CORPORELLES, key="region_chart")
    with side_col:
        cote_chart = st.selectbox("Côté", ["Droite", "Gauche", "Bilatéral", "Central"], key="cote_chart")
    with sym_col:
        type_symptome = st.selectbox("Type de symptôme", SYMPTOMES, key="type_symptome_chart")

    eva_symptome = st.slider("Intensité EVA du marquage", 0.0, 10.0, 0.0, 0.5, key="eva_symptome")
    commentaire_symptome = st.text_input("Commentaire du marquage", key="commentaire_symptome")

    if st.button("Ajouter le marquage", key="ajouter_marquage"):
        st.session_state.marquages_body_chart.append(
            {
                "region": region_chart,
                "cote": cote_chart,
                "symptome": type_symptome,
                "eva": eva_symptome,
                "commentaire": commentaire_symptome,
            }
        )
        st.success("Marquage ajouté")

    if st.session_state.marquages_body_chart:
        detail_region = st.selectbox(
            "Vue détaillée par région",
            sorted({m["region"] for m in st.session_state.marquages_body_chart}),
            key="detail_region_chart",
        )
        details = [m for m in st.session_state.marquages_body_chart if m["region"] == detail_region]
        with st.expander(f"Détail {detail_region}", expanded=False):
            st.dataframe(details, use_container_width=True)

        st.markdown("#### Tableau récapitulatif")
        st.dataframe(st.session_state.marquages_body_chart, use_container_width=True)
    else:
        st.info("Aucun marquage pour le moment.")

# 3) Red flags
with onglets[2]:
    st.subheader("Red flags / orientation")
    st.caption("Checklist d'aide au dépistage : nécessite jugement clinique et procédures locales.")

    reponses_red_flags: dict[str, bool] = {}
    for item in RED_FLAGS:
        reponses_red_flags[item] = st.checkbox(item, key=f"rf_{item}")

    red_flag_present = any(reponses_red_flags.values())
    if red_flag_present:
        st.error(
            "Alerte : au moins un signal inquiétant est coché. Recommander une évaluation médicale/orientation selon le contexte. "
            "Ce module ne pose pas de diagnostic.",
            icon="🚩",
        )
    else:
        st.success("Aucun red flag majeur coché dans cette checklist.")

    st.text_area("Commentaire d'orientation", key="commentaire_orientation")

# 4) Examen général
with onglets[3]:
    st.subheader("Examen général")

    with st.expander("Observation & posture", expanded=False):
        ras_obs = st.checkbox("RAS observation/posture", key="ras_obs")
        if not ras_obs:
            st.text_area("Détails observation/posture", key="details_obs")

    with st.expander("ROM (amplitude, qualité, symptômes)", expanded=False):
        ras_rom = st.checkbox("RAS ROM", key="ras_rom")
        if not ras_rom:
            st.text_area("Détails ROM (degrés/qualité/symptômes)", key="details_rom")

    with st.expander("Palpation", expanded=False):
        ras_palp = st.checkbox("RAS palpation", key="ras_palp")
        if not ras_palp:
            st.text_area("Détails palpation", key="details_palp")

    with st.expander("Examen neurologique", expanded=False):
        ras_neuro_exam = st.checkbox("RAS neurologique", key="ras_neuro_exam")
        if not ras_neuro_exam:
            st.text_area("Myotomes", key="exam_myotomes")
            st.text_area("Dermatomes", key="exam_dermatomes")
            st.text_area("Réflexes", key="exam_reflexes")
            st.text_area("Neurodynamique", key="exam_neurodynamique")

# 5) Modules conditionnels
with onglets[4]:
    st.subheader("Modules conditionnels")

    regions_detectees = set(st.session_state.get("regions_principales", []))
    regions_detectees.update({m["region"] for m in st.session_state.marquages_body_chart})

    if {"Lombaire", "Cervicale"}.intersection(regions_detectees):
        st.markdown("### Module McKenzie (conditionnel)")
        st.caption("Structure originale inspirée d'une logique clinique publique (sans reproduction de formulaire protégé).")
        st.text_area("Anamnèse orientée (aggravants/soulageants)", key="mck_anamnese")
        st.selectbox("Centralisation", ["Oui", "Non", "Incertain"], key="mck_centralisation")
        st.selectbox("Périphérisation", ["Oui", "Non", "Incertain"], key="mck_peripherisation")

        if "Lombaire" in regions_detectees:
            st.markdown("**Mouvements répétés lombaires**")
            st.text_input("Flexion répétée (effet pendant/après)", key="mck_lomb_flexion")
            st.text_input("Extension répétée (effet pendant/après)", key="mck_lomb_extension")
            st.text_input("Glissement latéral (effet pendant/après)", key="mck_lomb_glissement")

        if "Cervicale" in regions_detectees:
            st.markdown("**Mouvements répétés cervicaux**")
            st.text_input("Rétraction/extension (effet pendant/après)", key="mck_cerv_extension")
            st.text_input("Flexion répétée (effet pendant/après)", key="mck_cerv_flexion")
            st.text_input("Glissement latéral cervical (effet pendant/après)", key="mck_cerv_glissement")

        st.text_input("Classification provisoire", key="mck_classification")
        st.text_input("Préférence directionnelle", key="mck_preference")
        st.text_area("Objectifs McKenzie", key="mck_objectifs")
    else:
        st.info("Le module McKenzie apparaît si une région lombaire ou cervicale est sélectionnée.")

    st.divider()
    st.markdown("### Batterie neuro (conditionnelle)")
    signes_neuro = st.checkbox("Présence de signes neurologiques à explorer", key="signes_neuro")
    if signes_neuro:
        ras_neuro = st.checkbox("RAS neuro (masquer détails)", key="ras_neuro_detail")
        if not ras_neuro:
            st.text_area("Myotomes par niveau", key="neuro_myotomes")
            st.text_area("Dermatomes par niveau", key="neuro_dermatomes")
            st.text_area("Réflexes", key="neuro_reflexes")
            st.text_area("Neurodynamique", key="neuro_dyn")
            nd1, nd2 = st.columns(2)
            with nd1:
                st.number_input("Force droite (/5)", min_value=0, max_value=5, value=5, key="neuro_force_d")
                st.number_input("Sensibilité droite (/10)", min_value=0, max_value=10, value=10, key="neuro_sens_d")
            with nd2:
                st.number_input("Force gauche (/5)", min_value=0, max_value=5, value=5, key="neuro_force_g")
                st.number_input("Sensibilité gauche (/10)", min_value=0, max_value=10, value=10, key="neuro_sens_g")
            st.slider("EVA neuro", 0.0, 10.0, 0.0, 0.5, key="neuro_eva")
            st.multiselect(
                "Qualité des symptômes neuro",
                ["Brûlure", "Décharge", "Engourdissement", "Picotements", "Allodynie", "Autre"],
                key="neuro_qualite",
            )
            st.caption("Utiliser également le body chart pour localiser hypoesthésies/paresthésies.")
    else:
        st.info("Activer si signes neurologiques présents.")

# 6) Tests ciblés
with onglets[5]:
    st.subheader("Tests ciblés par région")
    resultats_tests: list[dict[str, Any]] = []

    for region, tests in TESTS_CIBLES.items():
        with st.expander(f"{region}", expanded=False):
            actif_region = st.checkbox(f"Activer tests {region}", key=f"activer_{region}")
            if actif_region:
                for nom_test, desc_test in tests:
                    resultat = render_test(region, nom_test, desc_test)
                    if resultat:
                        resultats_tests.append({"region": region, **resultat})

            if region == "Lombaire/Bassin":
                st.markdown("#### Cluster Laslett (SI)")
                st.caption("Les clusters orientent le raisonnement et ne constituent pas un diagnostic isolé.")
                actif_laslett = st.checkbox("Activer cluster Laslett", key="laslett_actif")
                if actif_laslett:
                    positifs = 0
                    realises = 0
                    for test_l in LASLETT_TESTS:
                        rep = st.radio(
                            test_l,
                            ["Positif", "Négatif", "Non réalisé"],
                            key=f"laslett_{test_l}",
                            horizontal=True,
                        )
                        if rep != "Non réalisé":
                            realises += 1
                        if rep == "Positif":
                            positifs += 1
                    st.metric("Tests positifs (Laslett)", f"{positifs} / {realises if realises else len(LASLETT_TESTS)}")

    st.session_state["resultats_tests"] = resultats_tests
    if resultats_tests:
        st.markdown("#### Récapitulatif tests activés")
        st.dataframe(resultats_tests, use_container_width=True)
    else:
        st.info("Aucun test ciblé renseigné.")

# 7) Fonction / force / reprise
with onglets[6]:
    st.subheader("Tests fonctionnels / force / reprise")
    seuil_lsi = st.number_input("Seuil cible LSI (%)", min_value=50.0, max_value=120.0, value=90.0, step=1.0, key="seuil_lsi")

    mesures = ["Saut unipodal", "Squat unipodal", "Presse/Jambe", "Hop test distance"]
    table_lsi: list[dict[str, Any]] = []
    for nom in mesures:
        with st.expander(nom, expanded=False):
            cote_atteint = st.selectbox("Côté atteint", ["Droite", "Gauche", "NA"], key=f"{nom}_cote_atteint")
            val_d = to_float(st.number_input("Valeur droite", min_value=0.0, value=0.0, step=0.1, key=f"{nom}_d"))
            val_g = to_float(st.number_input("Valeur gauche", min_value=0.0, value=0.0, step=0.1, key=f"{nom}_g"))
            reps_ou_temps = st.text_input("Répétitions/temps/protocole", key=f"{nom}_rep_temps")
            douleur_pendant = st.slider("Douleur pendant", 0.0, 10.0, 0.0, 0.5, key=f"{nom}_douleur_pendant")
            douleur_apres = st.slider("Douleur après", 0.0, 10.0, 0.0, 0.5, key=f"{nom}_douleur_apres")

            lsi = None
            if cote_atteint == "Droite":
                lsi = calcul_lsi(val_d, val_g)
            elif cote_atteint == "Gauche":
                lsi = calcul_lsi(val_g, val_d)

            statut = statut_objectif(lsi, seuil_lsi)
            st.markdown(f"**LSI** : {lsi if lsi is not None else 'NA'} | **Statut** : {badge_statut(statut)}")
            table_lsi.append(
                {
                    "test": nom,
                    "cote_atteint": cote_atteint,
                    "droite": val_d,
                    "gauche": val_g,
                    "lsi": lsi,
                    "statut": statut,
                    "douleur_pendant": douleur_pendant,
                    "douleur_apres": douleur_apres,
                    "protocole": reps_ou_temps,
                }
            )

    st.markdown("### Batterie McGill (seuils éditables)")
    protocoles_mcgill = {
        "Sorensen (sec)": 60.0,
        "Side bridge droit (sec)": 45.0,
        "Side bridge gauche (sec)": 45.0,
        "Trunk flexor (sec)": 60.0,
    }
    res_mcgill = []
    for test, default in protocoles_mcgill.items():
        colv, cols = st.columns(2)
        with colv:
            valeur = st.number_input(f"{test} - résultat", min_value=0.0, value=0.0, step=1.0, key=f"mcgill_{test}_val")
        with cols:
            seuil = st.number_input(f"{test} - seuil", min_value=0.0, value=default, step=1.0, key=f"mcgill_{test}_seuil")
        statut = statut_objectif(valeur, seuil)
        res_mcgill.append({"test": test, "valeur": valeur, "seuil": seuil, "statut": statut})

    st.dataframe(res_mcgill, use_container_width=True)

    st.markdown("### Critères de reprise personnalisables")
    criteres_reprise = {
        "Force suffisante selon objectifs": st.checkbox("Force suffisante", key="crit_force"),
        "LSI au-dessus du seuil": st.checkbox("LSI cible atteint", key="crit_lsi"),
        "Tolérance sauts/course/changements direction": st.checkbox("Tolérance gestuelle", key="crit_tolerance"),
        "Absence de reproduction symptomatique significative": st.checkbox("Symptômes contrôlés", key="crit_symptomes"),
        "Objectifs patient compatibles": st.checkbox("Objectifs patient validés", key="crit_objectifs"),
    }
    autre_critere = st.text_input("Autre critère personnalisé", key="autre_critere")
    st.session_state["table_lsi"] = table_lsi
    st.session_state["res_mcgill"] = res_mcgill
    st.session_state["criteres_reprise"] = criteres_reprise
    st.session_state["autre_critere"] = autre_critere

# 8) Synthèse & export
with onglets[7]:
    st.subheader("Synthèse automatique (non diagnostique)")

    tests = st.session_state.get("resultats_tests", [])
    tests_pos = [t for t in tests if t.get("resultat") == "Positif"]
    tests_neg = [t for t in tests if t.get("resultat") == "Négatif"]
    table_lsi = st.session_state.get("table_lsi", [])
    nb_atteints = len([t for t in table_lsi if t.get("statut") == "Atteint"])
    nb_total_lsi = len(table_lsi)

    completion_items = [
        bool(st.session_state.get("motif", "").strip()),
        bool(st.session_state.get("regions_principales", [])),
        bool(st.session_state.marquages_body_chart),
        True,
        bool(st.session_state.get("resultats_tests", [])),
        bool(table_lsi),
    ]
    completion = int((sum(completion_items) / len(completion_items)) * 100)
    st.progress(completion / 100)
    st.caption(f"Complétude estimée : {completion}%")

    red_flag_texte = "Présents" if any(st.session_state.get(f"rf_{item}", False) for item in RED_FLAGS) else "Aucun majeur coché"
    synthese = {
        "date_bilan": as_iso(st.session_state.get("date_bilan")),
        "patient": {
            "nom": st.session_state.get("nom_patient", ""),
            "prenom": st.session_state.get("prenom_patient", ""),
            "consentement": st.session_state.get("consentement", False),
        },
        "contexte": {
            "motif": st.session_state.get("motif", ""),
            "objectifs": st.session_state.get("objectifs_patient", ""),
            "limitations": st.session_state.get("limitations", ""),
        },
        "douleur": {
            "regions": st.session_state.get("regions_principales", []),
            "eva": {
                "repos": st.session_state.get("eva_repos", 0.0),
                "activite": st.session_state.get("eva_activite", 0.0),
                "meilleure": st.session_state.get("eva_meilleure", 0.0),
                "pire": st.session_state.get("eva_pire", 0.0),
            },
        },
        "red_flags": red_flag_texte,
        "body_chart": st.session_state.marquages_body_chart,
        "tests_positifs": [t["test"] for t in tests_pos],
        "tests_negatifs": [t["test"] for t in tests_neg],
        "lsi": table_lsi,
        "mcgill": st.session_state.get("res_mcgill", []),
        "criteres_reprise": st.session_state.get("criteres_reprise", {}),
        "plan": st.text_area("Plan / réévaluation / suivi", key="plan_suivi"),
        "mention_non_diagnostic": "Synthèse de documentation clinique, non diagnostique.",
    }

    st.markdown("#### Résumé clinique")
    st.markdown(
        f"""
- **Contexte** : {synthese['contexte']['motif'] or 'Non renseigné'}
- **Douleur EVA** : repos {synthese['douleur']['eva']['repos']} / activité {synthese['douleur']['eva']['activite']} / pire {synthese['douleur']['eva']['pire']}
- **Red flags** : {red_flag_texte}
- **Tests ciblés** : {len(tests_pos)} positifs, {len(tests_neg)} négatifs
- **Critères fonctionnels (LSI)** : {nb_atteints}/{nb_total_lsi} atteints
- **Message** : ce résumé aide le raisonnement clinique, sans diagnostic automatique.
"""
    )

    json_payload = json.dumps(synthese, ensure_ascii=False, indent=2, default=as_iso)
    st.download_button(
        "📥 Export JSON",
        data=json_payload,
        file_name="bilan_kine.json",
        mime="application/json",
        use_container_width=True,
    )

    md_payload = "\n".join(
        [
            "# Compte-rendu de bilan kinésithérapique (aide à la documentation)",
            f"- Date: {synthese['date_bilan']}",
            f"- Patient: {synthese['patient']['prenom']} {synthese['patient']['nom']}",
            f"- Consentement: {'Oui' if synthese['patient']['consentement'] else 'Non'}",
            f"- Motif: {synthese['contexte']['motif']}",
            f"- Red flags: {red_flag_texte}",
            f"- Tests positifs: {', '.join(synthese['tests_positifs']) if synthese['tests_positifs'] else 'Aucun'}",
            f"- Tests négatifs: {', '.join(synthese['tests_negatifs']) if synthese['tests_negatifs'] else 'Aucun'}",
            f"- Plan: {synthese['plan']}",
            "\n> Document non diagnostique. Interprétation réservée aux professionnels formés.",
        ]
    )
    st.download_button(
        "📥 Télécharger compte-rendu Markdown",
        data=md_payload,
        file_name="bilan_kine.md",
        mime="text/markdown",
        use_container_width=True,
    )

# 9) Références
with onglets[8]:
    st.subheader("Références et limites")
    st.markdown(
        """
### Références documentaires
- Laslett et al. (2005) — SIJ provocation cluster validity (PMID: 16038856) : https://pubmed.ncbi.nlm.nih.gov/16038856/
- Laslett et al. (2003) — McKenzie + SI tests (PMID: 12775204) : https://pubmed.ncbi.nlm.nih.gov/12775204/
- NICE NG59 — Low back pain and sciatica : https://www.nice.org.uk/guidance/ng59
- McKenzie Institute (2020) — formulaires lombaire/cervicale (inspiration structurelle, sans reproduction)
- Littérature McGill / Childs / Liebenson sur Sorensen, trunk flexor et side bridge (protocoles et seuils adaptables)

### Limites cliniques
- Cet outil ne pose pas de diagnostic et ne remplace pas le jugement clinique.
- Les seuils affichés sont paramétrables et ne doivent pas être pris comme normes universelles.
- Les données saisies restent locales à la session Streamlit ; éviter toute donnée personnelle inutile.
"""
    )

st.caption("BilanKine — version MVP structurée pour professionnel de santé")
