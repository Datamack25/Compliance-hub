import pandas as pd
import streamlit as st

from agents.registry import AGENTS, log, stats
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import agent_card, footer, hero, section
from generators import zipkit

u = auth.current_user()
hero("Orchestrateur des agents", "15 agents spécialisés coopèrent pour construire l'architecture de conformité, de surveillance et d'embargos de l'entité.")

st_df = stats().set_index("code")
cols = st.columns(3)
for i, a in enumerate(AGENTS):
    ok = auth.has_access(u, a.plan)
    n = int(st_df.loc[a.code, "exécutions"])
    pill = (f'<span class="rb-pill teal">{a.code}</span> <span class="rb-pill {"green" if ok else "amber"}">'
            f'{"Actif" if ok else "Offre " + auth.PLANS[a.plan]["label"]}</span> <span class="rb-pill grey">{n} exécution(s)</span>')
    with cols[i % 3]:
        agent_card(a.icon, a.name, a.mission, pill)
        st.page_link(a.page, label="Ouvrir l'agent →")
        st.write("")

section("Mission orchestrée : pack de démarrage conformité")
st.write("L'orchestrateur enchaîne les agents Cartographie → Recueil KYC → Examen renforcé → Sanctions → Formation → Veille → Plan & contrôle "
         "pour produire un dossier complet pour un secteur.")
if auth.guard("pro"):
    with st.form("mission"):
        c1, c2 = st.columns(2)
        company = c1.text_input("Entité", value=u.get("company") or "")
        sec = c2.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get,
                           index=list(SECTOR_LABELS).index(u.get("sector")) if u.get("sector") in SECTOR_LABELS else 0)
        go = st.form_submit_button("Lancer la mission", type="primary")
    if go:
        ref = dict(factors=load("risk_factors.csv"), typologies=load("typologies.csv"), countries=load("countries.csv"),
                   regs=load("regulations.csv"), kyc=load("kyc_requirements.csv"), sectors=load("sectors.csv"),
                   checklist=load("compliance_checklist.csv"), sanctions=load("sanctions_regimes.csv"),
                   roadmap=load("roadmap_steps.csv"), controls=load("control_framework.csv"))
        status = st.status("Mission en cours…", expanded=True)
        steps = [("A03", "Cartographie des risques"), ("A05", "Fiches de recueil KYC"), ("A04", "Trames d'examen renforcé"),
                 ("A06", "Référentiel pays & sanctions"), ("A01", "Supports de formation"), ("A11", "Suivi réglementaire"), ("A15", "Plan de mise en conformité & dispositif de contrôle")]
        for code, lbl in steps:
            status.write(f"🤖 {code} · {lbl}")
        data, manifest = zipkit.build_kit(company or "Entite", [(sec, SECTOR_LABELS[sec])], ref)
        for code, lbl in steps:
            log(code, f"Mission orchestrée — {lbl}", details=f"{company} / {sec}")
        status.update(label=f"Mission terminée — {len(manifest)} documents générés", state="complete")
        st.download_button("⬇️ Télécharger le pack (ZIP)", data, file_name=f"Pack_conformite_{sec}.zip", mime="application/zip", type="primary")

section("Journal d'activité des agents")
lg = load("agent_log.csv")
c1, c2 = st.columns([1, 1.6])
with c1:
    s = stats()
    s["taux de succès"] = s["taux de succès"].map(lambda x: "—" if pd.isna(x) else f"{x:.0%}")
    st.dataframe(s, hide_index=True, use_container_width=True, height=420)
with c2:
    st.dataframe(lg.sort_values("date", ascending=False).head(200) if len(lg) else lg, hide_index=True, use_container_width=True, height=420)
footer()
