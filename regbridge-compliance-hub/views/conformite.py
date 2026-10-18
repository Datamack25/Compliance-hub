import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, kpi, section, table
from generators import word

hero("Mise en conformité sectorielle", "Diagnostic de maturité LCB-FT et préparation AMLR pour fintech de paiement, banque, assurance, jeux, immobilier, transfert d'argent, crypto, corporate.",
     kicker="Agent A12 · Mise en conformité")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
chk = load("compliance_checklist.csv")
c1, c2 = st.columns(2)
company = c1.text_input("Entité", value=u.get("company") or "")
sec = c2.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get)
items = chk[chk["secteur"].isin(["COMMUN", sec])].reset_index(drop=True)
SC = {"Conforme": 1.0, "Partiel": 0.5, "Non conforme": 0.0, "Non applicable": None}

st.caption("Évaluez chaque exigence ; le score, le radar par domaine et le rapport Word sont calculés automatiquement.")
answers = []
for dom, grp in items.groupby("domaine", sort=False):
    with st.expander(f"{dom} — {len(grp)} exigence(s)", expanded=False):
        for r in grp.itertuples():
            a = st.radio(f"{r.exigence}  \n*{r.reference}*", list(SC), index=2, horizontal=True, key=f"c_{r.id}")
            answers.append({"domaine": dom, "exigence": r.exigence, "reference": r.reference, "statut": a})
res = pd.DataFrame(answers)
val = res["statut"].map(SC).dropna()
score = 100 * val.mean() if len(val) else 0
st.session_state.setdefault("maturity", {})[sec] = round(score)
k1, k2, k3 = st.columns(3)
with k1: kpi("Score de maturité", f"{score:.0f} %", "", "green" if score >= 75 else "amber" if score >= 50 else "red")
with k2: kpi("Écarts", int((res["statut"].isin(["Partiel", "Non conforme"])).sum()), "", "red")
with k3: kpi("Exigences évaluées", len(res))
by = res.assign(v=res["statut"].map(SC)).dropna(subset=["v"]).groupby("domaine")["v"].mean().mul(100).reset_index()
if len(by) >= 3:
    f = go.Figure(go.Scatterpolar(r=list(by["v"]) + [by["v"].iloc[0]], theta=list(by["domaine"]) + [by["domaine"].iloc[0]], fill="toself",
                                  line_color="#0E7490", fillcolor="rgba(14,116,144,.25)"))
    f.update_layout(**PLOTLY_LAYOUT, height=420, polar=dict(radialaxis=dict(range=[0, 100])), title="Maturité par domaine (%)")
    chart(f, use_container_width=True)
section("Feuille de route")
gaps = res[res["statut"].isin(["Partiel", "Non conforme"])].copy()
gaps["priorité"] = gaps["domaine"].map(lambda d: "P1" if d in ("Gel des avoirs", "Déclaration", "Vigilance renforcée", "Surveillance") else "P2")
table(gaps.sort_values("priorité"), hide_index=True, use_container_width=True)
if st.button("Générer le rapport de mise en conformité (Word)", type="primary"):
    log("A12", "Diagnostic", details=f"{company} / {sec} / {score:.0f}%")
    st.download_button("⬇️ Télécharger le rapport", word.gap_report(company, SECTOR_LABELS[sec], res, score), f"Rapport_conformite_{sec}.docx", type="primary")
st.page_link("views/controle.py", label="→ Construire le plan de mise en conformité et le dispositif de contrôle (PDF / JPEG)", icon="🧭")
footer()
