import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Service Response – Validation KPI",
    layout="wide"
)

st.title("🔍 Validation KPI Service Response")
st.caption("Objectif : vérifier la logique métier et fiabiliser les KPI")

# ============================================================
# SIDEBAR – UPLOAD
# ============================================================
st.sidebar.header("📂 Chargement des données")

file_ie = st.sidebar.file_uploader(
    "Extraction IE",
    type=["xlsx"]
)

file_pointage = st.sidebar.file_uploader(
    "Pointage brut",
    type=["xlsx"]
)

file_base_bo = st.sidebar.file_uploader(
    "Base_BO",
    type=["xlsx"]
)

if not (file_ie and file_pointage and file_base_bo):
    st.info("👉 Charge les 3 fichiers pour démarrer")
    st.stop()

# ============================================================
# LECTURE DES FICHIERS
# ============================================================
df_ie = pd.read_excel(file_ie)
df_pt = pd.read_excel(file_pointage)
df_bo = pd.read_excel(file_base_bo)

# ============================================================
# NORMALISATION – EXTRACTION IE
# ============================================================
df_ie["OR"] = df_ie["OR"].astype(str).str.strip()

df_ie["Planifié ?"] = (
    df_ie["Planifié ?"]
    .astype(str)
    .str.replace("\u00A0", " ", regex=False)
    .str.strip()
    .str.upper()
)

df_ie["Est_Planifie"] = df_ie["Planifié ?"].str.contains("PLANIF")

df_ie["Localisation"] = (
    df_ie["Localisation"]
    .astype(str)
    .str.upper()
    .str.strip()
)

df_ie["Position"] = (
    df_ie["Position"]
    .astype(str)
    .str.upper()
    .str.strip()
)

# ============================================================


# ============================================================
# NORMALISATION – POINTAGE
# Règle : 1 OR = 1 technicien (premier trouvé)
# ============================================================
df_pt["OR"] = (
    df_pt["OR (Numéro)"]
    .astype(str)
    .str.strip()
)

df_pt_clean = (
    df_pt[
        ["OR", "Salarié - Nom", "Salarié - Équipe(Nom)"]
    ]
    .dropna(subset=["OR"])
    .drop_duplicates(subset=["OR"])
    .rename(columns={
        "Salarié - Nom": "Technicien",
        "Salarié - Équipe(Nom)": "Equipe"
    })
)

# ============================================================
# MERGE IE + POINTAGE
# ============================================================
df = df_ie.merge(
    df_pt_clean,
    on="OR",
    how="left"
)

# ============================================================
# NORMALISATION – BASE BO
# ============================================================
df_bo["OR"] = (
    df_bo["N° OR (Segment)"]
    .astype(str)
    .str.strip()
)

df_bo["Constructeur"] = (
    df_bo["Constructeur de l'équipement"]
    .astype(str)
    .str.upper()
    .str.strip()
)

df_bo_clean = df_bo[["OR", "Constructeur"]].dropna(subset=["OR"])

# ============================================================
# MERGE CONSTRUCTEUR
# ============================================================
df = df.merge(
    df_bo_clean,
    on="OR",
    how="left"
)

# ============================================================
# FILTRE CONSTRUCTEUR
# ============================================================
st.sidebar.header("🏗️ Équipement")

constructeurs_disponibles = sorted(
    df["Constructeur"]
    .dropna()
    .unique()
    .tolist()
)

constructeurs_selectionnes = st.sidebar.multiselect(
    "Constructeur de l’équipement",
    options=constructeurs_disponibles,
    default=constructeurs_disponibles
)

if constructeurs_selectionnes:
    df = df[df["Constructeur"].isin(constructeurs_selectionnes)]

# ============================================================
# KPI
# ============================================================
total_or = df["OR"].nunique()
or_planifies = df[df["Est_Planifie"]]["OR"].nunique()
or_non_planifies = total_or - or_planifies
taux_planif = round(
    (or_planifies / total_or) * 100, 2
) if total_or > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Total OR non planifiés", or_non_planifies)
c2.metric("Total OR planifiés", or_planifies)
c3.metric("Taux de planification", f"{taux_planif} %")

# ============================================================
# GRAPHIQUE – PAR ÉQUIPE
# ============================================================
df_graph = (
    df.groupby(["Equipe", "Planifié ?"])["OR"]
    .nunique()
    .reset_index()
)

fig = px.bar(
    df_graph,
    x="Equipe",
    y="OR",
    color="Planifié ?",
    barmode="stack",
    title="OR Field – Planifiés vs Non planifiés par équipe",
    text_auto=True
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TABLE DÉTAILLÉE
# ============================================================
st.subheader("📋 Détail des OR Field retenus dans les KPI")

st.dataframe(
    df[
        [
            "OR",
            "Nom client",
            "Type intervention",
            "Localisation",
            "Position",
            "Constructeur",
            "Technicien",
            "Equipe",
            "Planifié ?"
        ]
    ].sort_values("OR"),
    use_container_width=True
)

# ============================================================
# MESSAGE CONTEXTE MÉTIER
# ============================================================
if positions_selectionnees == ["EC"]:
    st.warning(
        "⚠️ Le filtre Position = EC (En cours) "
        "contient majoritairement des OR non planifiés. "
        "Le taux affiché n’est pas représentatif du KPI final."
    )
