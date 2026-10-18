import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, kpi, section, table
from generators import excel

hero("Cartographie des risques", "Construction d'une cartographie LCB-FT par secteur, personnalisée selon la typologie d'entreprise, exportée en Excel (formules vivantes).",
     kicker="Agent A03 · Cartographie")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()

factors, typos, cs = load("risk_factors.csv"), load("company_typologies.csv"), load("countries.csv")
sectors, asr = load("sectors.csv"), load("asr_2023_products.csv")

c1, c2, c3 = st.columns(3)
company = c1.text_input("Entité", value=u.get("company") or "")
sec = c2.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get,
                   index=list(SECTOR_LABELS).index(u.get("sector")) if u.get("sector") in SECTOR_LABELS else 0)
tsub = typos[typos["secteur"] == sec]
typ = c3.selectbox("Typologie d'entreprise", tsub["typologie"])
coef = float(tsub.set_index("typologie").loc[typ, "coefficient"])

section("Personnalisation du profil")
o1, o2, o3 = st.columns(3)
opts = {
    "especes": o1.toggle("Forte intensité d'espèces"),
    "non_residents": o1.toggle("Clientèle non-résidente / flux internationaux"),
    "digital": o2.toggle("Entrée en relation 100 % à distance"),
    "ppe": o2.toggle("Clientèle PPE significative"),
    "crypto": o3.toggle("Exposition crypto-actifs"),
    "dispositif_jeune": o3.toggle("Dispositif LCB-FT récent / perfectible"),
}
opts["countries"] = st.multiselect("Pays d'activité / de flux (vide = tous)", cs["iso3"], format_func=dict(zip(cs.iso3, cs.pays)).get,
                                   default=["FRA"])
coef = st.slider("Coefficient de typologie (ajustable)", 0.7, 1.5, coef, 0.05)
opts["asr_level"] = sectors.set_index("code").loc[sec, "niveau_asr"]

LVL = {"Très élevée": 4, "Élevée": 3, "Modérée": 2, "Faible": 1}
CANAUX = {"Face-à-face en agence": (1, 2), "Entrée en relation à distance (digital)": (3, 3), "Intermédiaires / apporteurs d'affaires": (2, 3),
          "Agents / distributeurs": (3, 3), "Plateforme API / partenaires (BaaS)": (3, 4), "Paiement / remise d'espèces au guichet": (4, 3)}
CLIENTELE = {"Particuliers résidents": (2, 2), "Non-résidents": (3, 3), "Professionnels à forte intensité d'espèces": (4, 3),
             "Personnes morales complexes / holdings": (3, 4), "PPE et proches": (3, 4), "Associations / ONG": (2, 3),
             "Trusts / fiducies": (3, 4), "Mineurs / majeurs protégés": (1, 2), "Clients occasionnels": (3, 3)}
SECT_CLIENTS = {"BTP / rénovation": (3, 3), "Restauration / commerce de détail espèces": (4, 3), "Négoce de matières premières": (3, 4),
                "Immobilier / marchands de biens": (3, 4), "Crypto-actifs": (4, 4), "Jeux d'argent": (3, 3), "Art / biens de luxe": (3, 4),
                "Import-export / transport": (3, 3), "ONG / humanitaire en zones sensibles": (3, 4), "Sécurité privée / défense": (3, 4),
                "Professions du chiffre et du droit": (2, 3)}
MITIG = {"Produits": "Vigilance adaptée au produit, seuils et scénarios dédiés", "Canaux": "Contrôles d'identité renforcés selon le canal, contrôle des tiers",
         "Géographie": "Vigilance renforcée pays, filtrage des flux effectifs, autorisation préalable", "Clientèle": "Vigilance proportionnée au profil, revue périodique",
         "Secteur client": "Questionnaire d'activité, justificatifs, scénarios sectoriels"}

section("Dimensions de la cartographie")
st.caption("Sélectionnez les produits, canaux, pays, types de clientèle et secteurs d'activité des clients : chaque élément devient un facteur coté (probabilité × impact) dans la cartographie Excel.")
d1, d2 = st.columns(2)
prod_opts = asr.copy()
prod_opts["lib"] = prod_opts["produit"] + " (ASR : " + prod_opts["risque_global"] + ")"
sel_prod = d1.multiselect("🧾 Produits et services commercialisés", prod_opts["lib"], default=list(prod_opts[prod_opts["secteur"] == sec]["lib"])[:4])
sel_can = d2.multiselect("🔀 Canaux de distribution", list(CANAUX), default=["Face-à-face en agence", "Entrée en relation à distance (digital)"])
d3, d4 = st.columns(2)
sel_cli = d3.multiselect("👥 Types de clientèle", list(CLIENTELE), default=["Particuliers résidents", "Personnes morales complexes / holdings", "PPE et proches"])
sel_sc = d4.multiselect("🏭 Secteurs d'activité des clients", list(SECT_CLIENTS), default=["BTP / rénovation", "Restauration / commerce de détail espèces"])
st.caption("🌍 Les pays sélectionnés plus haut dont le niveau de risque est modéré, élevé ou très élevé sont intégrés automatiquement (dimension Géographie).")

rows = []
for lib in sel_prod:
    r = prod_opts[prod_opts["lib"] == lib].iloc[0]
    rows.append(("Produits", f"Produit : {r.produit}", LVL.get(r.menace, 2), LVL.get(r.vulnerabilite, 2), "ACPR ASR 2023"))
for c in sel_can:
    rows.append(("Canaux", f"Canal : {c}", *CANAUX[c], "CMF R.561-5-1; AMLR art. 22"))
for c in sel_cli:
    rows.append(("Clientèle", f"Clientèle : {c}", *CLIENTELE[c], "CMF L.561-10; AMLR art. 29-46"))
for c in sel_sc:
    rows.append(("Secteur client", f"Secteur client : {c}", *SECT_CLIENTS[c], "Tracfin 2023-2024; ANR 2023"))
geo = cs[cs["iso3"].isin(opts["countries"]) & cs["niveau_risque_pays"].isin(["Modéré", "Élevé", "Très élevé"])]
for r in geo.itertuples():
    p_, i_ = {"Très élevé": (4, 4), "Élevé": (3, 4), "Modéré": (2, 3)}[r.niveau_risque_pays]
    det = f"GAFI {r.gafi_statut}" if r.gafi_statut != "-" else "hors listes GAFI"
    rows.append(("Géographie", f"Pays : {r.pays} ({r.niveau_risque_pays}, {det})", p_, i_, "Liste UE 2016/1675; GAFI; sanctions"))
dims = pd.DataFrame(rows, columns=["categorie", "facteur", "probabilite", "impact", "reference"])
if len(dims):
    dims["dispositif_attenuation"] = dims["categorie"].map(MITIG)
    dims["id"] = [f"{sec}-D{i + 1:02d}" for i in range(len(dims))]
    dims["secteur"] = sec
    dims["risque_brut"] = dims["probabilite"] * dims["impact"]

with st.expander("➕ Ajouter des risques spécifiques (tableau à compléter)"):
    st.caption("Saisissez une ligne par risque : catégorie, facteur, probabilité (1-4), impact (1-4), dispositif et référence.")
    custom = st.data_editor(pd.DataFrame({"categorie": ["Clientèle"], "facteur": [""], "probabilite": [2], "impact": [2],
                                          "dispositif_attenuation": [""], "reference": [""]}),
                            num_rows="dynamic", use_container_width=True, hide_index=True,
                            column_config={"categorie": st.column_config.SelectboxColumn("Catégorie", options=["Clientèle", "Produits", "Canaux", "Géographie",
                                                                                                                 "Opérations", "Secteur client", "Dispositif"]),
                                           "facteur": st.column_config.TextColumn("Facteur de risque", width="large"),
                                           "probabilite": st.column_config.NumberColumn("Probabilité", min_value=1, max_value=4, step=1),
                                           "impact": st.column_config.NumberColumn("Impact", min_value=1, max_value=4, step=1),
                                           "dispositif_attenuation": st.column_config.TextColumn("Dispositif d'atténuation", width="large"),
                                           "reference": "Référence"})
custom = custom[custom["facteur"].astype(str).str.strip() != ""].dropna(subset=["facteur"]) if len(custom) else custom
if len(custom):
    custom = custom.assign(id=[f"{sec}-S{i + 1:02d}" for i in range(len(custom))], secteur=sec,
                           probabilite=custom["probabilite"].fillna(2).astype(int), impact=custom["impact"].fillna(2).astype(int),
                           risque_brut=0).fillna("")
extra = pd.concat([x for x in (dims, custom) if len(x)], ignore_index=True) if (len(dims) or len(custom)) else pd.DataFrame()

prev = factors[factors["secteur"] == sec].copy()
if len(extra):
    prev = pd.concat([prev, extra], ignore_index=True)
prev["risque_brut_ajuste"] = (prev["probabilite"] * prev["impact"] * coef).round(1)
prev["niveau"] = pd.cut(prev["risque_brut_ajuste"], [-1, 3, 6, 10, 100], labels=["Faible", "Modéré", "Élevé", "Très élevé"]).astype(str)
k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Facteurs de risque", len(prev), f"dont {len(extra)} issus des dimensions")
with k2: kpi("Risque brut moyen", f"{prev['risque_brut_ajuste'].mean():.1f}/16", f"coef. {coef}")
with k3: kpi("Facteurs ≥ 12", int((prev["risque_brut_ajuste"] >= 12).sum()), "Très élevés", "red")
with k4: kpi("Niveau ACPR (ASR 2023)", opts["asr_level"], SECTOR_LABELS[sec], "amber")

g1, g2 = st.columns([1, 1.1])
with g1:
    mat = prev.groupby(["probabilite", "impact"]).size().unstack(fill_value=0).reindex(index=[4, 3, 2, 1], columns=[1, 2, 3, 4], fill_value=0)
    import plotly.graph_objects as go
    zc = [[p * i for i in [1, 2, 3, 4]] for p in [4, 3, 2, 1]]
    hm = go.Figure(go.Heatmap(z=zc, x=["Impact 1", "Impact 2", "Impact 3", "Impact 4"], y=["Proba 4", "Proba 3", "Proba 2", "Proba 1"],
                              colorscale=[[0, "#D1FADF"], [0.35, "#FEF0C7"], [0.65, "#FDDCAB"], [1, "#F97066"]], showscale=False,
                              text=mat.values, texttemplate="<b>%{text}</b>", textfont=dict(size=20, color="#0B1F3A"),
                              hovertemplate="%{y} × %{x}<br>%{text} facteur(s)<extra></extra>", xgap=4, ygap=4))
    hm.update_layout(**PLOTLY_LAYOUT, height=360, title="Matrice de chaleur — nombre de facteurs")
    chart(hm)
with g2:
    by = prev.groupby("categorie", as_index=False).agg(risque=("risque_brut_ajuste", "mean"), n=("id", "count")).sort_values("risque")
    bf = px.bar(by, x="risque", y="categorie", orientation="h", text=by["risque"].round(1), color="risque",
                color_continuous_scale=["#067647", "#FACC15", "#B42318"], range_color=(2, 14), hover_data={"n": True})
    bf.update_traces(textposition="outside", textfont_color="#0B1F3A")
    bf.update_layout(**PLOTLY_LAYOUT, height=360, coloraxis_showscale=False, title="Risque brut moyen par dimension (/16)",
                     xaxis_title="", yaxis_title="", xaxis_range=[0, 17])
    chart(bf)
section("Cotations ACPR — ASR 2023 du secteur")
a = asr[asr["secteur"] == sec]
table(a[["produit", "menace", "vulnerabilite", "risque_global"]],
      column_config={"produit": "Produit / activité", "menace": "Menace", "vulnerabilite": "Vulnérabilité", "risque_global": "Risque global"})

section("Aperçu des facteurs")
table(prev.sort_values("risque_brut_ajuste", ascending=False)[["id", "categorie", "facteur", "probabilite", "impact", "risque_brut_ajuste", "niveau",
                                                                "dispositif_attenuation", "reference"]], height=420,
      column_config={"id": "ID", "categorie": "Dimension", "facteur": "Facteur de risque", "probabilite": "Proba.", "impact": "Impact",
                     "risque_brut_ajuste": "Risque brut", "niveau": "Niveau", "dispositif_attenuation": "Dispositif d'atténuation", "reference": "Référence"})

if st.button("Générer la cartographie Excel", type="primary"):
    data = excel.risk_map(company or "Entité", sec, SECTOR_LABELS[sec], typ, coef, factors, load("typologies.csv"), cs, opts,
                          load("regulations.csv"), extra if len(extra) else None)
    log("A03", "Cartographie", details=f"{company} / {sec} / {typ}")
    st.download_button("⬇️ Télécharger la cartographie", data, f"Cartographie_LCB-FT_{sec}.xlsx", type="primary")

section("Génération multi-secteurs")
multi = st.multiselect("Secteurs", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get, default=["BANQUE", "FINTECH", "ASSURANCE"])
if st.button("Générer un classeur par secteur (ZIP)") and multi:
    import io
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        for s in multi:
            t0 = typos[typos["secteur"] == s].iloc[0]
            z.writestr(f"Cartographie_{s}.xlsx", excel.risk_map(company or "Entité", s, SECTOR_LABELS[s], t0.typologie, float(t0.coefficient),
                                                              factors, load("typologies.csv"), cs, {"asr_level": sectors.set_index("code").loc[s, "niveau_asr"]},
                                                              load("regulations.csv")))
    log("A03", "Cartographies multi-secteurs", details=",".join(multi))
    st.download_button("⬇️ Télécharger les cartographies (ZIP)", bio.getvalue(), "Cartographies_sectorielles.zip")
footer()
