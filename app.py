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

st.title("🔍 Validation KPI Service Response (hors Power BI)")
st.caption("Objectif : vérifier la logique métier et les chiffres réels")

# ============================================================
# SIDEBAR – UPLOAD
# ============================================================
st.sidebar.header("📂 Chargement des données")

file_ie = st.sidebar.file_uploader(
    "Extraction IE (déjà traitée – avec Planifié ?)",
    type=["xlsx"]
)

file_pointage = st.sidebar.file_uploader(
    "Pointage brut",
    type=["xlsx"]
)

if not (file_ie and file_pointage):
    st.info("👉 Charge l’Extraction IE traitée et le Pointage pour commencer")
    st.stop()

# ============================================================
# LECTURE DES FICHIERS
# ============================================================
df_ie = pd.read_excel(file_ie)
df_pt = pd.read_excel(file_pointage)

# ============================================================
# NORMALISATION – EXTRACTION IE
# ============================================================
df_ie["OR"] = df_ie["OR"].astype(str).str.strip()
df_ie["Planifié ?"] = df_ie["Planifié ?"].astype(str).str.strip()
df_ie["Localisation"] = df_ie["Localisation"].astype(str).str.upper().str.strip()
df_ie["Position"] = df_ie["Position"].astype(str).str.upper().str.strip()

# ============================================================
# FILTRE OR FIELD (RÈGLE MÉTIER)
# OR Field = MO EXTERIEUR / MO CVA
# ============================================================
localisations_field = ["MO EXTERIEUR", "MO CVA"]

df_ie_field = df_ie[
    df_ie["Localisation"].isin(localisations_field)
].copy()

# ============================================================
# SIDEBAR – POINT DE CONTRÔLE POSITION
# ============================================================
st.sidebar.header("🎛️ Points de contrôle métier")

positions_disponibles = sorted(
    df_ie_field["Position"].dropna().unique().tolist()
)

positions_selectionnees = st.sidebar.multiselect(
    "Positions OR à inclure dans les KPI",
    options=positions_disponibles,
    default=positions_disponibles
)

df_ie_field = df_ie_field[
    df_ie_field["Position"].isin(positions_selectionnees)
].copy()

# ============================================================
# NORMALISATION – POINTAGE
# ============================================================
df_pt["OR"] = df_pt["OR (Numéro)"].astype(str).str.strip()
df_pt["Heures"] = pd.to_numeric(
    df_pt["Heures"],
    errors="coerce"
).fillna(0)

# ============================================================
# DÉTERMINER LE "VRAI" TECHNICIEN PAR OR
# Règle : technicien avec le PLUS d’heures
# ============================================================
df_pt_agg = (
    df_pt.groupby(
        ["OR", "Salarié - Nom", "Salarié - Équipe(Nom)"],
        as_index=False
    )["Heures"]
    .sum()
)

df_pt_best = (
    df_pt_agg
    .sort_values(["OR", "Heures"], ascending=[True, False])
    .drop_duplicates(subset=["OR"])
    .rename(columns={
        "Salarié - Nom": "Technicien",
        "Salarié - Équipe(Nom)": "Equipe"
    })
)

# ============================================================
# MERGE IE + POINTAGE
# ============================================================
df = df_ie_field.merge(
    df_pt_best[["OR", "Technicien", "Equipe"]],
    on="OR",
    how="left"
)

# ============================================================
# KPI
# ============================================================
total_or = df["OR"].nunique()
or_planifie = df[df["Planifié ?"] == "Planifié"]["OR"].nunique()
or_non_planifie = total_or - or_planifie
taux_planif = round(
    (or_planifie / total_or) * 100, 2
) if total_or > 0 else 0

# ============================================================
# AFFICHAGE KPI
# ============================================================
c1, c2, c3 = st.columns(3)

c1.metric("Total OR non planifiés", or_non_planifie)
c2.metric("Total OR planifiés", or_planifie)
c3.metric("Taux de planification", f"{taux_planif} %")

# ============================================================
# GRAPHIQUE – OR PAR ÉQUIPE & PLANIFICATION
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
            "Technicien",
            "Equipe",
            "Planifié ?"
        ]
    ]
    .sort_values("OR"),
    use_container_width=True
)

# ============================================================
# FOOTER – INTERPRÉTATION
# ============================================================
st.caption(
    "ℹ️ Cette application sert de référence métier pour valider "
    "les KPI avant implémentation Power BI."
)
