import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import footer, hero, section
from generators.zipkit import CLIENT_TYPES, SUBFOLDERS, build_kit

hero("Kit documentaire ZIP", "Un dossier par secteur, dix sous-dossiers thématiques, des trames Word et des outils Excel prêts à l'emploi (banque, assurance, fintech, jeux, immobilier, MTO, crypto…).",
     kicker="Agent A13 · Kit documentaire")
if not auth.guard("enterprise"):
    st.stop()
u = auth.current_user()
c1, c2 = st.columns([1, 2])
company = c1.text_input("Entité", value=u.get("company") or "")
secs = c2.multiselect("Secteurs à inclure", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get, default=list(SECTOR_LABELS))
l, r = st.columns(2)
with l:
    section("Arborescence de chaque secteur")
    st.code("\n".join(f"📁 {s}" for s in SUBFOLDERS), language=None)
with r:
    section("Contenu type (par secteur)")
    st.markdown("- Procédure LCB-FT & gel, politique d'acceptation clients\n- Cartographie des risques Excel (formules)\n"
                "- Fiches KYC par typologie de client + plan de remédiation + courrier type\n- Trames d'examen renforcé, fiche & registre PPE\n"
                "- Registre des alertes, typologies Tracfin\n- Fiche d'alerte de filtrage, registre de gel, référentiel pays\n"
                "- Trame de DS, registre des DS\n- Émargement et registre de formation\n- Plan de contrôle permanent, plan de mise en conformité (PDF + infographie JPEG)\n- Suivi des réglementations")
    st.caption(f"Environ {sum(len(CLIENT_TYPES.get(s, [])) for s in secs) + 23 * len(secs)} documents pour la sélection.")
if st.button("Construire le kit", type="primary") and secs:
    ref = dict(factors=load("risk_factors.csv"), typologies=load("typologies.csv"), countries=load("countries.csv"), regs=load("regulations.csv"),
               kyc=load("kyc_requirements.csv"), sectors=load("sectors.csv"), checklist=load("compliance_checklist.csv"), sanctions=load("sanctions_regimes.csv"),
                   roadmap=load("roadmap_steps.csv"), controls=load("control_framework.csv"))
    bar = st.progress(0.0, "Préparation…")
    data, manifest = build_kit(company or "Entite", [(s, SECTOR_LABELS[s]) for s in secs], ref, progress=lambda p, t: bar.progress(p, t))
    log("A13", "Kit ZIP", details=f"{len(secs)} secteurs, {len(manifest)} fichiers")
    st.success(f"Kit prêt : {len(manifest)} documents.")
    st.download_button("⬇️ Télécharger le kit (ZIP)", data, "Kit_conformite_RegBridge.zip", "application/zip", type="primary")
footer()
