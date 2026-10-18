import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth
from core.data import load, save
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, section
from generators import excel

hero("Veille réglementaire & jurisprudence", "AMLR, AMLA, AMLD6, TFR, MiCA, paiements instantanés, DORA, AI Act… et décisions de sanction (ACPR, DOJ, FCA, CJUE).",
     kicker="Agent A11 · Veille")
u = auth.current_user()
regs, juris = load("regulations.csv"), load("jurisprudence.csv")

t1, t2, t3 = st.tabs(["📅 Calendrier réglementaire", "⚖️ Jurisprudence & sanctions", "✏️ Suivi (modifiable)"])
with t1:
    r = regs.copy()
    r["date"] = pd.to_datetime(r["Date d'entrée en vigueur"])
    r = r.sort_values("date")
    r["échéance"] = r["date"].dt.strftime("%d/%m/%Y")
    f = px.scatter(r, x="date", y="Nom/titre de la réglementation", color="Statut", text="échéance",
                   color_discrete_map={"En vigueur": "#0E7490", "À venir": "#B8891B"}, hover_data={"Résumé des points clés": True, "date": False})
    f.update_traces(marker=dict(size=15, symbol="diamond", line=dict(width=1.5, color="#FFFFFF")), textposition="middle right",
                    textfont=dict(size=10, color="#344054"))
    f.add_vline(x=pd.Timestamp.today(), line_dash="dot", line_color="#B42318")
    f.add_annotation(x=pd.Timestamp.today(), y=1.03, yref="paper", text="Aujourd'hui", showarrow=False, font=dict(color="#B42318", size=11))
    f.update_layout(**PLOTLY_LAYOUT, height=600, yaxis_title="", xaxis_title="", legend=dict(orientation="h", y=-0.08),
                    xaxis_range=[pd.Timestamp("2015-06-01"), pd.Timestamp("2032-01-01")])
    chart(f, use_container_width=True)
    section("Focus AMLR / AMLA")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**AMLR — Règl. (UE) 2024/1624**\n- Application : 10 juillet 2027\n- Règles CDD uniformes, BE ≥ 25 % (calcul revu, art. 52)\n- PPE : EDD automatique (art. 34, 42-46)\n- Plafond espèces 10 000 €\n- Remédiation du stock (art. 26)")
    c2.markdown("**AMLA — Règl. (UE) 2024/1620**\n- Siège : Francfort\n- Normes RTS/ITS (CDD, scoring des risques) 2026\n- Sélection d'~40 entités fin 2027\n- Supervision directe : janvier 2028")
    c3.markdown("**Listes à jour**\n- GAFI juin 2026 : + Bosnie-Herzégovine, Irak ; − Algérie, Namibie\n- UE 29/01/2026 : + Bolivie, BVI, Russie ; − Burkina Faso, Mali, Mozambique, Nigeria, Afrique du Sud, Tanzanie\n- MiCA : fin du régime PSAN au 1er juillet 2026")
with t2:
    sec = st.multiselect("Secteur", sorted(juris["secteur"].unique()), default=sorted(juris["secteur"].unique()))
    j = juris[juris["secteur"].isin(sec)].sort_values("date", ascending=False)
    for x in j.itertuples():
        with st.expander(f"{x.date} · {x.autorite} — {x.entite} · {x.sanction}"):
            st.markdown(f"**Manquements :** {x.manquements}\n\n**Enseignements :** {x.enseignements}")
    st.caption("Les montants des affaires étrangères sont arrondis ; se référer aux décisions officielles.")
with t3:
    if not auth.has_access(u, "pro"):
        auth.guard("pro")
    else:
        ed = st.data_editor(regs, num_rows="dynamic", hide_index=True, use_container_width=True, height=420,
                            column_config={"Statut": st.column_config.SelectboxColumn(options=["En vigueur", "À venir", "Abrogé"]),
                                           "Impact sur l'entreprise": st.column_config.SelectboxColumn(options=["Fort", "Moyen", "Faible"])})
        c1, c2 = st.columns(2)
        if c1.button("💾 Enregistrer", type="primary"):
            save("regulations.csv", ed)
            log("A11", "MAJ veille réglementaire", details=f"{len(ed)} textes")
            st.success("Suivi enregistré.")
        c2.download_button("⬇️ Exporter au format « Regulations Tracking » (Excel)",
                           excel.template("veille_reglementaire", u.get("company") or "", ed), "Suivi_reglementations.xlsx")
footer()
