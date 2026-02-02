import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================
# CONFIG APP
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
    "Extraction IE (déjà filtrée OR Field)",
    type=["xlsx"]
)

file_pointage = st.sidebar.file_uploader(
    "Pointage brut",
    type=["xlsx"]
)

file_base_bo = st.sidebar.file_uploader(
    "Base_BO (constructeur équipement)",
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
# (OR Field déjà filtrés en amont via Power Query)
# ============================================================
df_ie["OR"] = df_ie["OR"].astype(str).str.strip()

df_ie["Planifié ?"] = (
    df_ie["Planifié ?"]
    .astype(str)
    .str.replace("\u00A0", " ", regex=False)
    .str.strip()
    .str.upper()
)

df_ie["Est_Planifie"] = df_ie["Planifié ?"].eq("PLANIFIÉ")

df_ie["Position"] = (
    df_ie["Position"]
    .astype(str)
    .str.upper()
    .str.strip()
)

# ============================================================
# FILTRE POSITION (PÉRIMÈTRE MÉTIER)
# ============================================================
st.sidebar.header("🎛️ Périmètre métier")

positions_disponibles = sorted(
    df_ie["Position"].dropna().unique().tolist()
)

positions_selectionnees = st.sidebar.multiselect(
    "Position OR",
    options=positions_disponibles,
    default=positions_disponibles
)

df_ie = df_ie[
    df_ie["Position"].isin(positions_selectionnees)
].copy()

# ============================================================
# POINTAGE – RAMENER AU GRAIN OR (1 OR = 1 TECHNICIEN)
# Règle : premier technicien pointé (stable)
# ============================================================
df_pt_or = (
    df_pt
    .assign(
        OR=lambda x: x["OR (Numéro)"].astype(str).str.strip()
    )
    .groupby("OR", as_index=False)
    .agg({
        "Salarié - Nom": "first",
        "Salarié - Equipe(Nom)": "first"
    })
    .rename(columns={
        "Salarié - Nom": "Technicien",
        "Salarié - Equipe(Nom)": "Equipe"
    })
)

# ============================================================
# BASE_BO – RAMENER AU GRAIN OR (1 OR = 1 CONSTRUCTEUR)
# ============================================================
df_bo_or = (
    df_bo
    .assign(
        OR=lambda x: x["N° OR (Segment)"].astype(str).str.strip(),
        Constructeur=lambda x: x["Constructeur de l'équipement"]
            .astype(str)
            .str.upper()
            .str.strip()
    )
    .groupby("OR", as_index=False)
    .agg({
        "Constructeur": "first"
    })
)

# ============================================================
# MERGES FINAUX (SANS DUPLICATION)
# TABLE MAÎTRE = EXTRACTION IE
# ============================================================
df = (
    df_ie
    .merge(df_pt_or, on="OR", how="left")
    .merge(df_bo_or, on="OR", how="left")
)

# ============================================================
# VERROU DE SÉCURITÉ (CRITIQUE)
# ============================================================
assert df["OR"].nunique() == len(df), (
    "❌ ERREUR CRITIQUE : duplication d’OR après merge"
)

# ============================================================
# FILTRE CONSTRUCTEUR
# ============================================================
st.sidebar.header("🏗️ Équipement")

constructeurs_disponibles = sorted(
    df["Constructeur"].dropna().unique().tolist()
)

constructeurs_selectionnes = st.sidebar.multiselect(
    "Constructeur de l’équipement",
    options=constructeurs_disponibles,
    default=constructeurs_disponibles
)

if constructeurs_selectionnes:
    df = df[df["Constructeur"].isin(constructeurs_selectionnes)]

# ============================================================
# KPI (GRAIN = OR)
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
# GRAPHIQUE – OR PAR ÉQUIPE
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
    text_auto=True,
    title="OR Field – Planifiés vs Non planifiés par équipe"
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TABLEAU DÉTAIL – 1 OR = 1 LIGNE
# ============================================================
st.subheader("📋 Détail des OR Field retenus dans les KPI")

st.dataframe(
    df[
        [
            "OR",
            "Nom client",
            "Type intervention",
            "Position",
            "Constructeur",
            "Technicien",
            "Equipe",
            "Planifié ?"
        ]
    ]
    .sort_values("OR"),
    use_container_width=True
)

# ============================================================
# INFO MÉTIER
# ============================================================
st.caption(
    "ℹ️ Les KPI sont calculés sur les OR distincts. "
    "Chaque OR apparaît une seule fois (grain maîtrisé)."
)
