from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, kpi, section, table
from generators import excel
from generators import plan as P

hero("Dispositif de contrôle & plan de mise en conformité",
     "Plan étape par étape adapté au secteur, à la taille et à la maturité de l'entreprise, avec dispositif de contrôle sur trois lignes de maîtrise — exports PDF et JPEG.",
     kicker="Agent A15 · Contrôle & feuille de route")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
steps, ctrls = load("roadmap_steps.csv"), load("control_framework.csv")

c1, c2, c3 = st.columns(3)
company = c1.text_input("Entreprise", value=u.get("company") or "")
sec = c2.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get,
                   index=list(SECTOR_LABELS).index(u.get("sector")) if u.get("sector") in SECTOR_LABELS else 0)
size = c3.selectbox("Taille", list(P.SIZE_COEF), index=1)
c4, c5 = st.columns(2)
default_mat = int(st.session_state.get("maturity", {}).get(sec, 40))
maturity = c4.slider("Maturité actuelle du dispositif (%)", 0, 100, default_mat,
                     help="Repris automatiquement du diagnostic de l'agent Mise en conformité s'il a été réalisé pour ce secteur.")
start = c5.date_input("Date de démarrage", date.today())

plan = P.build_plan(steps, sec, size, maturity, start)
controls = P.controls_for(ctrls, sec)
k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Étapes", len(plan))
with k2: kpi("Durée totale", f"{int(plan['fin_sem'].max())} sem.", "", "teal")
with k3: kpi("Fin prévisionnelle", plan["date_fin"].max().strftime("%d/%m/%Y"), "", "amber")
with k4: kpi("Points de contrôle", len(controls), f"dont {int((controls['secteur'] == sec).sum())} spécifiques", "green")

t1, t2, t3 = st.tabs(["🗺️ Plan étape par étape", "🛡️ Dispositif de contrôle", "⬇️ Exports PDF / JPEG / Excel"])
with t1:
    g = plan.assign(Étape=plan["n"].astype(str) + ". " + plan["etape"], debut=pd.to_datetime(plan["date_debut"]), fin=pd.to_datetime(plan["date_fin"]))
    phases = sorted(g["phase"].unique(), key=lambda x: int(x.split(".")[0]))
    f = px.timeline(g, x_start="debut", x_end="fin", y="Étape", color="phase", hover_data=["responsable", "livrables", "duree"],
                    category_orders={"Étape": list(g["Étape"]), "phase": phases},
                    color_discrete_map={ph: P.PHASE_COLORS[int(ph.split(".")[0]) - 1] for ph in phases})
    f.update_yaxes(autorange="reversed")
    f.update_layout(**PLOTLY_LAYOUT, height=40 + 30 * len(plan), yaxis_title="", xaxis_title="", legend_title="Phase")
    chart(f, use_container_width=True)
    for r in plan.itertuples():
        with st.expander(f"Étape {r.n} · {r.etape}  —  {r.date_debut:%d/%m/%Y} → {r.date_fin:%d/%m/%Y} ({r.duree} sem.)"):
            st.markdown(f"**Phase :** {r.phase}  \n**Description :** {r.description}  \n**Livrables :** {r.livrables}  \n**Responsable :** {r.responsable}")
with t2:
    lv = st.multiselect("Lignes de maîtrise", list(P.LINES), default=list(P.LINES), format_func=lambda k: f"{k} — {P.LINES[k]}")
    view = controls[controls["niveau"].isin(lv)]
    table(view.drop(columns=["secteur"]), hide_index=True, use_container_width=True, height=460)
    b = px.histogram(view, x="domaine", color="niveau", color_discrete_sequence=["#0E7490", "#5925DC", "#0B1F3A"])
    b.update_layout(**PLOTLY_LAYOUT, height=300, xaxis_title="", yaxis_title="Contrôles", title="Répartition des contrôles par domaine")
    chart(b, use_container_width=True)
with t3:
    st.write("Le PDF contient la synthèse, le diagramme de Gantt, les fiches étape par étape et le dispositif de contrôle complet. "
             "Le JPEG est une infographie d'une page, prête à intégrer dans une proposition commerciale.")
    if st.button("Générer les documents", type="primary"):
        st.session_state["plan_files"] = (
            P.plan_pdf(company or "Entreprise", SECTOR_LABELS[sec], size, maturity, plan, controls),
            P.plan_jpeg(company or "Entreprise", SECTOR_LABELS[sec], size, plan),
            excel.template("plan_controle", company, pd.DataFrame({
                "Domaine": controls["domaine"], "Point de contrôle": controls["point_de_controle"], "Fréquence": controls["frequence"],
                "Échantillon": controls["methode_echantillon"], "Responsable": controls["niveau"], "Date": "", "Résultat": "",
                "Anomalies": "", "Plan d'action": "", "Statut": "À traiter"})),
            excel.dfs_to_xlsx({"Feuille de route": plan.drop(columns=["n_phase", "duree_semaines"]), "Dispositif de contrôle": controls},
                              f"Plan {SECTOR_LABELS[sec]}"),
            sec,
        )
        log("A15", "Plan de mise en conformité", details=f"{company} / {sec} / {size} / maturité {maturity}%")
    files = st.session_state.get("plan_files")
    if files and files[4] == sec:
        pdf_b, jpg_b, ctl_b, road_b, _ = files
        a, b_, c, d = st.columns(4)
        a.download_button("⬇️ Plan complet (PDF)", pdf_b, f"Plan_conformite_{sec}.pdf", "application/pdf", type="primary", use_container_width=True)
        b_.download_button("⬇️ Infographie (JPEG)", jpg_b, f"Plan_conformite_{sec}.jpg", "image/jpeg", use_container_width=True)
        c.download_button("⬇️ Plan de contrôle (Excel)", ctl_b, f"Plan_controle_{sec}.xlsx", use_container_width=True)
        d.download_button("⬇️ Feuille de route (Excel)", road_b, f"Feuille_de_route_{sec}.xlsx", use_container_width=True)
        st.image(jpg_b, caption="Aperçu de l'infographie", use_container_width=True)
footer()
