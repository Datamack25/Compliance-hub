from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth
from core.data import load
from core.ui import PLOTLY_LAYOUT, footer, hero, kpi, section
from generators import excel, word

hero("Remédiation KYC", "Diagnostic du stock clients, priorisation fondée sur les risques (AMLR art. 26), plan de remédiation et courriers.",
     kicker="Agent A02 · Remédiation KYC")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()

REVIEW = {"Élevé": 365, "Standard": 3 * 365, "Faible": 5 * 365}
st.caption("Importez votre portefeuille (CSV/Excel) avec les colonnes du modèle, ou utilisez le jeu de démonstration.")
c1, c2 = st.columns([2, 1])
up = c1.file_uploader("Portefeuille clients", type=["csv", "xlsx"])
demo = load("kyc_portfolio_demo.csv")
c2.download_button("Modèle de fichier (CSV)", demo.head(5).to_csv(index=False).encode("utf-8"), "modele_portefeuille_kyc.csv")
df = (pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)) if up else demo.copy()
with st.expander("Paramètres de revue périodique"):
    a, b, c = st.columns(3)
    REVIEW["Élevé"] = a.number_input("Risque élevé (jours)", 90, 1825, 365)
    REVIEW["Standard"] = b.number_input("Risque standard (jours)", 180, 2555, 1095)
    REVIEW["Faible"] = c.number_input("Risque faible (jours)", 365, 3650, 1825)

today = pd.Timestamp(date.today())


def diagnose(r):
    issues, missing = [], []
    try:
        if pd.Timestamp(r["expiration_piece_identite"]) < today:
            issues.append("Pièce d'identité expirée")
            missing.append("Pièce d'identité en cours de validité")
    except Exception:
        issues.append("Date de validité de la pièce inconnue")
    try:
        overdue = (today - pd.Timestamp(r["derniere_revue"])).days - REVIEW.get(r["niveau_risque"], 1095)
        if overdue > 0:
            issues.append(f"Revue périodique en retard de {overdue} j")
    except Exception:
        overdue = 0
    if r.get("justificatif_domicile") == "Non":
        issues.append("Justificatif de domicile manquant")
        missing.append("Justificatif de domicile de moins de 3 mois")
    if r.get("be_identifies") == "Non":
        issues.append("Bénéficiaires effectifs non identifiés")
        missing.append("Identification des bénéficiaires effectifs (organigramme, extrait RBE)")
    if r.get("origine_fonds") == "Non" and r["niveau_risque"] == "Élevé":
        issues.append("Origine des fonds non documentée (risque élevé)")
        missing.append("Justificatif de l'origine des fonds")
    if r.get("activite_documentee") == "Non":
        issues.append("Activité / profession non documentée")
        missing.append("Justificatif d'activité professionnelle ou de revenus")
    if r.get("ppe") == "Oui" and r["niveau_risque"] != "Élevé":
        issues.append("PPE non classée en risque élevé")
    pts = {"Élevé": 50, "Standard": 25, "Faible": 10}.get(r["niveau_risque"], 20) + 12 * len(issues) + (25 if r.get("ppe") == "Oui" else 0)
    return pd.Series({"anomalies": "; ".join(issues), "pieces_manquantes": "; ".join(missing), "nb_anomalies": len(issues), "score_priorite": pts})


res = pd.concat([df, df.apply(diagnose, axis=1)], axis=1)
res["priorite"] = pd.cut(res["score_priorite"], [-1, 30, 60, 1000], labels=["P3", "P2", "P1"])
to_fix = res[res["nb_anomalies"] > 0].sort_values("score_priorite", ascending=False)

k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Clients analysés", len(res))
with k2: kpi("Dossiers non conformes", len(to_fix), f"{len(to_fix) / max(len(res), 1):.0%} du portefeuille", "red")
with k3: kpi("Priorité P1", int((to_fix["priorite"] == "P1").sum()), "Risque élevé / PPE", "amber")
with k4: kpi("Taux de conformité", f"{1 - len(to_fix) / max(len(res), 1):.0%}", "", "green")

g1, g2 = st.columns(2)
with g1:
    ex = to_fix["anomalies"].str.split("; ").explode()
    ex = ex.str.replace(r" de \d+ j", "", regex=True).value_counts().reset_index()
    ex.columns = ["anomalie", "nb"]
    f = px.bar(ex, x="nb", y="anomalie", orientation="h", color_discrete_sequence=["#0E7490"])
    f.update_layout(**PLOTLY_LAYOUT, height=320, yaxis_title="", xaxis_title="Dossiers", title="Anomalies par type")
    st.plotly_chart(f, use_container_width=True)
with g2:
    p = res.groupby(["niveau_risque", "priorite"], observed=True).size().reset_index(name="n")
    f = px.bar(p, x="niveau_risque", y="n", color="priorite", color_discrete_map={"P1": "#B42318", "P2": "#F79009", "P3": "#0E7490"})
    f.update_layout(**PLOTLY_LAYOUT, height=320, title="Dossiers par risque et priorité", xaxis_title="", yaxis_title="")
    st.plotly_chart(f, use_container_width=True)

section("Plan de remédiation priorisé")
show = to_fix[["client_id", "nom", "type", "pays", "niveau_risque", "ppe", "priorite", "anomalies", "pieces_manquantes"]]
st.dataframe(show, hide_index=True, use_container_width=True, height=380)
pre = pd.DataFrame({"ID client": to_fix["client_id"], "Nom": to_fix["nom"], "Type": to_fix["type"], "Niveau de risque": to_fix["niveau_risque"],
                    "Anomalie(s)": to_fix["anomalies"], "Pièces manquantes": to_fix["pieces_manquantes"], "Priorité (AMLR art. 26)": to_fix["priorite"].astype(str),
                    "Date de relance 1": (today + pd.Timedelta(days=7)).strftime("%d/%m/%Y"), "Date de relance 2": (today + pd.Timedelta(days=30)).strftime("%d/%m/%Y"),
                    "Date limite": (today + pd.Timedelta(days=60)).strftime("%d/%m/%Y"), "Statut": "À traiter",
                    "Mesure si non-réponse": to_fix["priorite"].map({"P1": "Restriction des opérations + examen renforcé", "P2": "Restriction", "P3": "Relance"}).astype(str),
                    "Chargé KYC": ""})
c1, c2 = st.columns(2)
if c1.download_button("⬇️ Plan de remédiation (Excel)", excel.template("remediation_kyc", u.get("company") or "", pre),
                      "Plan_remediation_KYC.xlsx", type="primary"):
    log("A02", "Plan de remédiation", details=f"{len(to_fix)} dossiers")
cl = c2.selectbox("Courrier client", to_fix["client_id"] + " — " + to_fix["nom"]) if len(to_fix) else None
if cl:
    r = to_fix[to_fix["client_id"] == cl.split(" — ")[0]].iloc[0]
    miss = [m for m in r["pieces_manquantes"].split("; ") if m] or ["Mise à jour de vos informations personnelles et professionnelles"]
    c2.download_button("⬇️ Courrier de demande (Word)", word.remediation_letter(u.get("company") or "", r["nom"], miss), f"Courrier_{r['client_id']}.docx")
footer()
