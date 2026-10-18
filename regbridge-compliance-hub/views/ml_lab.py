import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log, stats
from core import auth, ml
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, kpi, section, table

hero("Laboratoire ML & auto-amélioration", "Scoring client par apprentissage automatique, retours analystes, champion/challenger, détection de dérive et réentraînement.",
     kicker="Agent A14 · Auto-amélioration")
if not auth.guard("enterprise"):
    st.stop()
ch = ml.champion() or ml.train()
k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Modèle champion", ch["version"], ch["date"])
with k2: kpi("AUC", f"{ch['auc']:.3f}", "Validation", "teal")
with k3: kpi("F1", f"{ch['f1']:.3f}", f"Précision {ch['precision']:.2f} · Rappel {ch['rappel']:.2f}")
with k4: kpi("Retours analystes", ch["n_retours_analystes"], "intégrés au dernier entraînement", "amber")

t1, t2, t3 = st.tabs(["🎯 Scorer un client", "🔁 Réentraînement & versions", "📉 Dérive & agents"])
with t1:
    cs = load("countries.csv")
    c1, c2, c3 = st.columns(3)
    pays = c1.selectbox("Pays", cs["iso3"], format_func=dict(zip(cs.iso3, cs.pays)).get)
    row = {
        "type_client": c1.selectbox("Type", ["PP", "PM", "TRUST", "ASSO"]),
        "secteur": c1.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get),
        "risque_pays": float(100 - cs.set_index("iso3").loc[pays, "indice_securite_financiere"]),
        "ppe": int(c2.toggle("PPE")), "presse_negative": c2.number_input("Articles négatifs", 0, 20, 0),
        "part_especes": c2.slider("Part d'espèces", 0.0, 1.0, 0.1), "distance": int(c2.toggle("Relation à distance", True)),
        "niveaux_detention": c3.number_input("Niveaux de détention", 0, 6, 0), "nb_tx_mois": c3.number_input("Transactions / mois", 0, 2000, 20),
        "montant_moyen": c3.number_input("Montant moyen (€)", 0.0, 1e7, 800.0), "part_flux_pays_risque": c3.slider("Flux vers pays à risque", 0.0, 1.0, 0.05),
        "anciennete_mois": c1.number_input("Ancienneté (mois)", 0, 600, 24),
    }
    p = float(ml.score_clients(pd.DataFrame([row]))[0])
    lvl = "Très élevé" if p >= 0.75 else "Élevé" if p >= 0.5 else "Modéré" if p >= 0.25 else "Faible"
    a, b = st.columns([1, 1.6])
    with a:
        kpi("Probabilité de profil suspect", f"{p:.0%}", f"Niveau {lvl}", "red" if p >= 0.5 else "amber" if p >= 0.25 else "green")
        st.write("")
        st.markdown("**Votre décision d'analyste alimente le prochain modèle :**")
        x, y = st.columns(2)
        if x.button("Profil à risque confirmé", type="primary"):
            n = ml.add_client_feedback(row, 1)
            log("A14", "Retour analyste client", details=f"label=1, total={n}")
            st.toast(f"Retour enregistré ({n} au total)")
        if y.button("Profil sain"):
            n = ml.add_client_feedback(row, 0)
            log("A14", "Retour analyste client", details=f"label=0, total={n}")
            st.toast(f"Retour enregistré ({n} au total)")
    with b:
        ex = ml.explain(row)
        f = px.bar(ex, x="contribution", y="variable", orientation="h", color="contribution", color_continuous_scale=["#067647", "#F2F4F7", "#B42318"],
                   color_continuous_midpoint=0)
        f.update_layout(**PLOTLY_LAYOUT, height=380, coloraxis_showscale=False, title="Contribution de chaque variable (explicabilité locale)", yaxis_title="")
        chart(f, use_container_width=True)
with t2:
    fb = ml._feedback()
    st.write(f"**{len(fb)}** retour(s) analyste en attente d'intégration. Le challenger n'est promu que si son AUC n'est pas dégradée.")
    if st.button("🔁 Réentraîner (champion / challenger)", type="primary"):
        with st.spinner("Entraînement…"):
            e = ml.train("Réentraînement manuel sur retours analystes")
        log("A14", "Réentraînement", details=f"{e['version']} {e['statut']} AUC {e['auc']}")
        (st.success if e["statut"] == "champion" else st.warning)(f"{e['version']} : {e['statut']} (AUC {e['auc']})")
    reg = ml.registry()
    if len(reg):
        table(reg, hide_index=True, use_container_width=True)
        f = px.line(reg, x="version", y=["auc", "f1", "precision", "rappel"], markers=True)
        f.update_layout(**PLOTLY_LAYOUT, height=300, title="Performance par version", yaxis_title="", xaxis_title="")
        chart(f, use_container_width=True)
    st.caption("Auto-amélioration : (1) les retours analystes sont ajoutés aux données d'entraînement avec un poids x3 ; (2) les poids des règles de surveillance "
               "et des mots-clés de presse négative s'ajustent à chaque qualification ; (3) la dérive des populations déclenche une alerte de réentraînement.")
with t3:
    fb = ml._feedback()
    recent = fb if len(fb) >= 5 else load("training_clients.csv").sample(300, random_state=1).assign(part_especes=lambda d: d["part_especes"] * 1.6)
    st.markdown("**Indice de stabilité des populations (PSI)** — " + ("retours analystes" if len(fb) >= 5 else "simulation sur un échantillon décalé"))
    table(ml.drift_report(recent), hide_index=True, use_container_width=True)
    section("Performance opérationnelle des agents")
    s = stats()
    f = px.bar(s, x="code", y="exécutions", hover_data=["agent"], color_discrete_sequence=["#0E7490"])
    f.update_layout(**PLOTLY_LAYOUT, height=300, xaxis_title="", yaxis_title="Exécutions")
    chart(f, use_container_width=True)
footer()
