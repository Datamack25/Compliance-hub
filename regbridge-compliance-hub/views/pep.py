from datetime import date

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from agents.registry import log
from core import auth
from core.data import load, save
from core.ui import PLOTLY_LAYOUT, geo_chart, footer, hero, kpi, section
from generators import excel, word

hero("Surveillance des PPE", "Personnes politiquement exposées par pays : fonctions publiques importantes (JOUE C/2023/724), registre, échéances de revue et contrôle de noms.",
     kicker="Agent A07 · PPE")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
cs, funcs, reg = load("countries.csv"), load("pep_functions.csv"), load("pep_watchlist.csv")
today = pd.Timestamp(date.today())
reg["prochaine_revue"] = pd.to_datetime(reg["prochaine_revue"], errors="coerce")
overdue = reg[reg["prochaine_revue"] < today]
soon = reg[(reg["prochaine_revue"] >= today) & (reg["prochaine_revue"] <= today + pd.Timedelta(days=30))]

k1, k2, k3, k4 = st.columns(4)
with k1: kpi("PPE suivies", len(reg))
with k2: kpi("Revues en retard", len(overdue), "À traiter", "red")
with k3: kpi("Revues < 30 jours", len(soon), "", "amber")
with k4: kpi("PPE pays à risque élevé", int((reg["risque_pays_ppe"] == "Élevé").sum()), "IPC < 35 ou sanctions", "red")

t1, t2, t3 = st.tabs(["🗺️ Risque PPE par pays", "📋 Registre & échéances", "🔎 Contrôle d'un nom"])
with t1:
    c1, c2 = st.columns([1.6, 1])
    with c1:
        m = px.choropleth(cs, locations="iso3", color="risque_ppe", hover_name="pays", hover_data={"ipc_indicatif": True, "iso3": False},
                          color_discrete_map={"Standard": "#D1FADF", "Modéré": "#FEC84B", "Élevé": "#F04438"})
        m.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth", landcolor="#EEF2F6", showland=True)
        m.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=0, r=0, t=0, b=0)}, height=400, legend=dict(orientation="h"))
        geo_chart(m)
    with c2:
        by = reg.groupby("pays").size().reset_index(name="PPE").sort_values("PPE", ascending=False)
        st.markdown("**PPE suivies par pays**")
        st.dataframe(by, hide_index=True, use_container_width=True, height=360)
    section("Fonctions publiques importantes")
    src = st.radio("Source", ["France — JOUE C/2023/724", "Catégories GAFI / AMLR (tous pays)"], horizontal=True)
    f = funcs[funcs["iso3"] == "FRA"] if src.startswith("France") else funcs[funcs["iso3"] == "*"]
    st.dataframe(f[["fonction", "niveau_risque", "source"]], hide_index=True, use_container_width=True)

with t2:
    if len(overdue):
        st.error(f"{len(overdue)} revue(s) annuelle(s) en retard : " + ", ".join(overdue["nom"].head(8)))
    ed = st.data_editor(reg.assign(prochaine_revue=reg["prochaine_revue"].dt.date), hide_index=True, num_rows="dynamic",
                        use_container_width=True, height=420,
                        column_config={"statut": st.column_config.SelectboxColumn(options=["En fonction", "Ancienne PPE (< 12 mois)", "Ancienne PPE (> 12 mois)"]),
                                       "relation": st.column_config.SelectboxColumn(options=["Client actif", "Prospect", "Bénéficiaire effectif", "Mandataire"]),
                                       "prochaine_revue": st.column_config.DateColumn()})
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Enregistrer le registre", type="primary"):
        save("pep_watchlist.csv", ed)
        log("A07", "MAJ registre PPE", details=f"{len(ed)} PPE")
        st.success("Registre enregistré.")
    pre = pd.DataFrame({"ID": ed["id"], "Nom": ed["nom"], "Fonction": ed["fonction"], "Pays": ed["pays"], "PPE / famille / proche": "PPE",
                        "Date d'identification": ed["date_identification"], "Accord direction (nom/date)": "", "Origine du patrimoine": "",
                        "Origine des fonds": "", "Fréquence de revue": "Annuelle", "Prochaine revue": ed["prochaine_revue"].astype(str), "Statut": ed["statut"]})
    c2.download_button("⬇️ Registre PPE (Excel)", excel.template("registre_ppe", u.get("company") or "", pre), "Registre_PPE.xlsx")
    c3.download_button("Fiche d'approbation PPE (Word)", word.pep_form(u.get("company") or ""), "Fiche_approbation_PPE.docx")
    declass = ed[ed["statut"] == "Ancienne PPE (> 12 mois)"]
    if len(declass):
        st.info(f"{len(declass)} ancienne(s) PPE depuis plus de 12 mois : déclassement possible après analyse du risque résiduel (AMLR art. 45).")

with t3:
    c1, c2 = st.columns(2)
    with c1:
        section("Évaluation du risque PPE")
        pays = st.selectbox("Pays de la fonction", cs["iso3"], format_func=dict(zip(cs.iso3, cs.pays)).get)
        fonction = st.selectbox("Fonction", funcs["fonction"].unique())
        lien = st.selectbox("Lien", ["Titulaire", "Membre de la famille", "Proche associé"])
        row = cs[cs["iso3"] == pays].iloc[0]
        base = {"Très élevé": 4, "Élevé": 3, "Modéré": 2, "Selon PPE": 3}.get(funcs[funcs["fonction"] == fonction]["niveau_risque"].iloc[0], 2)
        score = base + {"Élevé": 2, "Modéré": 1}.get(row["risque_ppe"], 0) + (1 if row["gafi_statut"] != "-" else 0) - (1 if lien != "Titulaire" else 0)
        lvl = "Très élevé" if score >= 6 else "Élevé" if score >= 4 else "Modéré"
        kpi("Niveau de risque PPE", lvl, f"Score {score} · IPC {row['ipc_indicatif'] or 'n.d.'} · GAFI {row['gafi_statut']}",
            "red" if score >= 4 else "amber")
    with c2:
        section("Recherche en sources ouvertes")
        name = st.text_input("Nom de la personne")
        if st.button("Rechercher (Wikidata)") and name:
            try:
                r = requests.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities", "search": name, "language": "fr",
                                                                               "uselang": "fr", "format": "json", "limit": 8},
                                 headers={"User-Agent": "RegBridge/1.0"}, timeout=8).json()
                kw = ["politi", "ministre", "député", "sénateur", "président", "ambassad", "maire", "gouverneur", "juge", "minister", "senator", "general"]
                hits = [{"libellé": e.get("label"), "description": e.get("description", ""),
                         "indice PPE": "⚠️ probable" if any(k in e.get("description", "").lower() for k in kw) else "—",
                         "lien": "https://www.wikidata.org/wiki/" + e["id"]} for e in r.get("search", [])]
                st.dataframe(pd.DataFrame(hits), hide_index=True, use_container_width=True) if hits else st.info("Aucun résultat.")
                log("A07", "Recherche PPE", details=name)
            except Exception:
                st.warning("Recherche en ligne indisponible (pas d'accès Internet).")
        if name:
            st.markdown(f"[Rechercher « {name} » sur OpenSanctions (PEP)](https://www.opensanctions.org/search/?q={name.replace(' ', '+')}&topics=role.pep)")
            m = reg[reg["nom"].str.lower().str.contains(name.lower().split(" ")[0])]
            if len(m):
                st.warning("Présent(e) dans le registre interne :")
                st.dataframe(m, hide_index=True)
footer()
