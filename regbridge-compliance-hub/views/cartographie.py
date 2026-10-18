import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, footer, hero, kpi, section
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

with st.expander("➕ Ajouter des risques spécifiques"):
    custom = st.data_editor(pd.DataFrame(columns=["categorie", "facteur", "probabilite", "impact", "dispositif_attenuation", "reference"]),
                            num_rows="dynamic", use_container_width=True,
                            column_config={"probabilite": st.column_config.NumberColumn(min_value=1, max_value=4, step=1),
                                           "impact": st.column_config.NumberColumn(min_value=1, max_value=4, step=1)})
custom = custom.dropna(subset=["facteur"]) if len(custom) else custom
if len(custom):
    custom = custom.assign(id=[f"{sec}-S{i + 1:02d}" for i in range(len(custom))], secteur=sec,
                           probabilite=custom["probabilite"].fillna(2).astype(int), impact=custom["impact"].fillna(2).astype(int),
                           risque_brut=0).fillna("")

prev = factors[factors["secteur"] == sec].copy()
if len(custom):
    prev = pd.concat([prev, custom], ignore_index=True)
prev["risque_brut_ajuste"] = (prev["probabilite"] * prev["impact"] * coef).round(1)
k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Facteurs de risque", len(prev))
with k2: kpi("Risque brut moyen", f"{prev['risque_brut_ajuste'].mean():.1f}/16", f"coef. {coef}")
with k3: kpi("Facteurs ≥ 12", int((prev["risque_brut_ajuste"] >= 12).sum()), "Très élevés", "red")
with k4: kpi("Niveau ACPR (ASR 2023)", opts["asr_level"], SECTOR_LABELS[sec], "amber")

g1, g2 = st.columns([1.2, 1])
with g1:
    f = px.scatter(prev, x="impact", y="probabilite", size="risque_brut_ajuste", color="categorie", hover_name="facteur",
                   size_max=34, range_x=[0.5, 4.5], range_y=[0.5, 4.5])
    f.update_layout(**PLOTLY_LAYOUT, height=380, title="Matrice probabilité × impact", xaxis_title="Impact", yaxis_title="Probabilité")
    for x0, y0, col in [(2.5, 2.5, "rgba(180,35,24,.06)")]:
        f.add_shape(type="rect", x0=x0, y0=y0, x1=4.5, y1=4.5, fillcolor=col, line_width=0)
    st.plotly_chart(f, use_container_width=True)
with g2:
    a = asr[asr["secteur"] == sec]
    st.markdown("**Cotations ACPR — ASR 2023**")
    st.dataframe(a[["produit", "menace", "vulnerabilite", "risque_global"]], hide_index=True, use_container_width=True, height=330)

section("Aperçu des facteurs")
st.dataframe(prev[["id", "categorie", "facteur", "probabilite", "impact", "risque_brut_ajuste", "dispositif_attenuation", "reference"]],
             hide_index=True, use_container_width=True, height=330)

if st.button("Générer la cartographie Excel", type="primary"):
    data = excel.risk_map(company or "Entité", sec, SECTOR_LABELS[sec], typ, coef, factors, load("typologies.csv"), cs, opts,
                          load("regulations.csv"), custom if len(custom) else None)
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
