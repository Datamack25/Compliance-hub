import pandas as pd
import streamlit as st

from agents.registry import log
from core import auth
from core.data import load
from core.ui import footer, hero, section
from generators import excel, word

hero("Recueil des éléments KYC", "Fiches de recueil et listes de pièces par typologie de client : personnes physiques, morales, trusts, associations, PPE, contreparties régulées.",
     kicker="Agent A05 · Recueil KYC")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
kyc = load("kyc_requirements.csv")

c1, c2 = st.columns([1, 2])
company = c1.text_input("Entité", value=u.get("company") or "")
types = sorted(kyc["type_client"].unique())
sel = c2.multiselect("Typologies de client", types, default=types[:3])
lvl = st.radio("Niveau de vigilance affiché", ["Tous", "Simplifiée", "Standard", "Renforcée"], horizontal=True)

for t in sel:
    sub = kyc[kyc["type_client"] == t]
    if lvl != "Tous":
        sub = sub[sub["niveau_vigilance"] == lvl]
    with st.expander(f"🪪 {t} — {len(sub)} éléments", expanded=len(sel) == 1):
        st.dataframe(sub[["piece", "niveau_vigilance", "reference"]], hide_index=True, use_container_width=True)
        st.download_button(f"Fiche de recueil Word — {t}", word.kyc_form(t, company, kyc[kyc["type_client"] == t]),
                           f"Fiche_KYC_{t[:30]}.docx", key=f"dl_{t}")

section("Exports groupés")
c1, c2 = st.columns(2)
if c1.button("Générer toutes les fiches (ZIP)", type="primary") and sel:
    import io
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        for t in sel:
            z.writestr(f"Fiche_KYC_{''.join(ch if ch.isalnum() else '_' for ch in t)}.docx", word.kyc_form(t, company, kyc[kyc["type_client"] == t]))
    log("A05", "Fiches KYC", details=", ".join(sel))
    c1.download_button("⬇️ Télécharger le ZIP", bio.getvalue(), "Fiches_KYC.zip")
c2.download_button("Matrice des pièces KYC (Excel)",
                   excel.dfs_to_xlsx({"Pièces KYC": kyc, "Synthèse": pd.crosstab(kyc["type_client"], kyc["niveau_vigilance"]).reset_index()}, "Matrice KYC"),
                   "Matrice_pieces_KYC.xlsx")
footer()
