import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import footer, hero, section, table
from generators import word

hero("Examen renforcé", "Trames d'examen renforcé (CMF L.561-10-2 · AMLR art. 34) adaptées au type de client et au secteur, avec typologies Tracfin.",
     kicker="Agent A04 · Examen renforcé")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
kyc, typ, juris = load("kyc_requirements.csv"), load("typologies.csv"), load("jurisprudence.csv")

c1, c2, c3 = st.columns(3)
company = c1.text_input("Entité", value=u.get("company") or "")
sec = c2.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get)
ct = c3.selectbox("Type de client", sorted(kyc["type_client"].unique()))
trig = st.multiselect("Déclencheurs", ["Opération d'un montant inhabituellement élevé", "Opération complexe", "Absence de justification économique",
                                       "Lien avec un pays tiers à haut risque", "Client PPE", "Presse négative / réquisition judiciaire",
                                       "Alerte de surveillance automatisée"], default=["Opération d'un montant inhabituellement élevé"])
t = typ[typ["secteurs"].str.contains(sec)]
k = kyc[(kyc["type_client"].isin([ct, "PPE (tout type)"] if "PPE" in " ".join(trig) else [ct])) & (kyc["niveau_vigilance"] == "Renforcée")]

l, r = st.columns([1.3, 1])
with l:
    section("Typologies Tracfin intégrées à la trame")
    table(t[["intitule", "criteres_alerte", "source"]], hide_index=True, use_container_width=True, height=300)
with r:
    section("Pièces renforcées demandées")
    for p in k.itertuples():
        st.markdown(f"- {p.piece} · *{p.reference}*")
    section("Enseignement jurisprudentiel")
    j = juris[juris["id"] == "J001"].iloc[0]
    st.warning(f"**{j.entite} ({j.date}) — {j.sanction}.** {j.enseignements}")

if st.button("Générer la trame Word", type="primary"):
    data = word.edd_template(ct, SECTOR_LABELS[sec], company, t, k, {"extra_label": "Déclencheurs : " + ", ".join(trig)})
    log("A04", "Trame EDD", details=f"{ct} / {sec}")
    st.download_button("⬇️ Télécharger la trame d'examen renforcé", data, f"Examen_renforce_{sec}.docx", type="primary")
c1, c2 = st.columns(2)
c1.download_button("Trame de déclaration de soupçon (Word)", word.ds_template(company, SECTOR_LABELS[sec]), "Trame_DS.docx")
c2.download_button("Fiche d'approbation PPE (Word)", word.pep_form(company), "Fiche_PPE.docx")
footer()
