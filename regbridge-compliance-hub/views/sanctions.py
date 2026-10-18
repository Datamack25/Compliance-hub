import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth, screening, updater
from core.data import load, recompute_countries, save
from core.ui import PLOTLY_LAYOUT, chart, footer, geo_chart, hero, kpi, section, table
from generators import excel, word

hero("Sanctions, embargos & listes GAFI", "Pays sous sanctions (UE, ONU, OFAC, France), listes grise/noire du GAFI, pays tiers à haut risque UE, filtrage de noms et mises à jour.",
     kicker="Agent A06 · Sanctions & Embargos")
u = auth.current_user()
pro = auth.has_access(u, "pro")
cs, reg = load("countries.csv"), load("sanctions_regimes.csv")

k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Embargos globaux", int((cs["niveau_sanctions"] >= 3).sum()), "Niveau 3", "red")
with k2: kpi("Pays sous sanctions", int((cs["niveau_sanctions"] >= 1).sum()), "Tous niveaux", "amber")
with k3: kpi("Liste grise GAFI", int((cs["gafi_statut"] == "grise").sum()), "Plénière juin 2026", "amber")
with k4: kpi("Liste UE haut risque", int(cs["ue_pays_tiers_haut_risque"].sum()), "En vigueur 29/01/2026", "red")

t1, t2, t3, t4 = st.tabs(["🌍 Pays sous sanctions", "🚩 Listes GAFI & UE", "🔎 Filtrage & listes officielles", "🕓 Historique"])

with t1:
    c1, c2, c3 = st.columns(3)
    auth_f = c1.multiselect("Autorité", sorted(reg["autorite"].unique()), default=sorted(reg["autorite"].unique()))
    int_f = c2.multiselect("Intensité", ["Très élevé", "Élevé", "Modéré", "Faible", "Variable"], default=["Très élevé", "Élevé", "Modéré", "Faible", "Variable"])
    q = c3.text_input("Recherche (pays, nature, base légale)")
    v = reg[reg["autorite"].isin(auth_f) & reg["intensite"].isin(int_f)]
    if q:
        v = v[v.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    table(v, hide_index=True, use_container_width=True, height=380)
    m = px.choropleth(cs, locations="iso3", color="niveau_sanctions", hover_name="pays", hover_data={"regimes_sanctions": True, "iso3": False},
                      color_continuous_scale=["#F2F4F7", "#FEC84B", "#F04438", "#7A271A"], range_color=(0, 3))
    m.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth", landcolor="#EEF2F6", showland=True)
    m.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=0, r=0, t=0, b=0)}, height=380)
    geo_chart(m)
    st.download_button("⬇️ Exporter régimes + pays (Excel)", excel.dfs_to_xlsx({"Régimes": reg, "Pays": cs}, "Sanctions & embargos"),
                       "Sanctions_embargos.xlsx")

with t2:
    a, b, c = st.columns(3)
    with a:
        section("Liste noire GAFI")
        table(cs[cs["gafi_statut"] == "noire"][["pays", "region"]], hide_index=True, use_container_width=True)
    with b:
        section("Liste grise GAFI")
        table(cs[cs["gafi_statut"] == "grise"][["pays", "region"]], hide_index=True, use_container_width=True, height=420)
    with c:
        section("Pays tiers à haut risque UE")
        table(cs[cs["ue_pays_tiers_haut_risque"] == 1][["pays", "region"]], hide_index=True, use_container_width=True, height=420)
    st.info("Prochaine plénière du GAFI : fin octobre 2026 (première sous présidence britannique). Sorties pressenties par la presse : "
            "Monaco, Bulgarie, Côte d'Ivoire — à confirmer après publication officielle.")
    section("Mettre à jour")
    if not pro:
        auth.guard("pro")
    else:
        c1, c2 = st.columns(2)
        if c1.button("🔄 Interroger le site du GAFI", type="primary"):
            ok, msg, found = updater.fetch_fatf()
            st.session_state["fatf_found"] = found if ok else None
            (st.success if ok else st.warning)(msg)
            log("A06", "MAJ GAFI", "Succès" if ok else "Échec", msg)
        found = st.session_state.get("fatf_found")
        if found:
            cur_g, cur_n = set(cs[cs.gafi_statut == "grise"].iso3), set(cs[cs.gafi_statut == "noire"].iso3)
            names = dict(zip(cs.iso3, cs.pays))
            st.write("**Ajouts liste grise :**", ", ".join(names[i] for i in found["grise"] - cur_g) or "aucun")
            st.write("**Retraits liste grise :**", ", ".join(names[i] for i in cur_g - found["grise"]) or "aucun")
            st.write("**Liste noire détectée :**", ", ".join(names[i] for i in found["noire"]) or "—")
            if st.button("Appliquer ces changements"):
                updater.apply_fatf(found, f"MAJ GAFI {pd.Timestamp.today():%d/%m/%Y}")
                st.success("Référentiel mis à jour et instantané d'indice enregistré.")
                st.rerun()
        with c2:
            st.caption("Mise à jour manuelle (après publication officielle) : modifiez les cellules puis enregistrez. "
                       "L'indice de sécurité financière est recalculé et un instantané daté alimente la jauge du tableau de bord.")
        ed = st.data_editor(cs[["iso3", "pays", "region", "gafi_statut", "ue_pays_tiers_haut_risque", "niveau_sanctions", "regimes_sanctions",
                                "ipc_indicatif", "zone_conflit", "opacite_financiere"]],
                            hide_index=True, use_container_width=True, height=360, num_rows="dynamic",
                            column_config={"gafi_statut": st.column_config.SelectboxColumn("GAFI", options=["-", "grise", "noire"]),
                                           "ue_pays_tiers_haut_risque": st.column_config.NumberColumn("UE", min_value=0, max_value=1),
                                           "niveau_sanctions": st.column_config.NumberColumn("Sanctions", min_value=0, max_value=3),
                                           "ipc_indicatif": st.column_config.NumberColumn("IPC", min_value=0, max_value=100),
                                           "zone_conflit": st.column_config.NumberColumn("Conflit", min_value=0, max_value=1),
                                           "opacite_financiere": st.column_config.NumberColumn("Opacité", min_value=0, max_value=1)})
        e1, e2 = st.columns([2, 1])
        ev = e1.text_input("Libellé de l'événement", value=f"Mise à jour manuelle {pd.Timestamp.today():%d/%m/%Y}")
        if e2.button("💾 Enregistrer et historiser", type="primary"):
            full = cs.set_index("iso3")
            ed2 = ed.set_index("iso3")
            for col in ed2.columns:
                full.loc[ed2.index.intersection(full.index), col] = ed2[col]
            new = ed2.loc[ed2.index.difference(full.index)]
            full = pd.concat([full, new]).reset_index().fillna({"membre_ue": 0, "risque_ppe": "Modéré"})
            full = recompute_countries(full)
            save("countries.csv", full)
            updater.snapshot(ev)
            log("A06", "MAJ manuelle référentiel pays", details=ev)
            st.success("Référentiel enregistré.")
            st.rerun()

with t3:
    if not pro:
        auth.guard("pro")
    else:
        c1, c2 = st.columns([1, 1.3])
        with c1:
            section("Listes officielles")
            table(screening.list_status(), hide_index=True, use_container_width=True)
            if st.button("🔄 Mettre à jour ONU · OFAC · UE · DG Trésor", type="primary"):
                with st.spinner("Téléchargement des listes officielles…"):
                    for ok, msg in updater.update_all():
                        (st.success if ok else st.warning)(msg)
                        log("A06", "MAJ listes", "Succès" if ok else "Échec", msg)
            st.caption("Sans accès Internet, le filtrage fonctionne sur la liste de démonstration (entrées « TEST »).")
        with c2:
            section("Filtrage d'un nom")
            name = st.text_input("Nom / raison sociale", placeholder="ex. Golden Crescent Trading")
            thr = st.slider("Seuil de correspondance", 60, 100, 85)
            lists = screening.all_lists()
            if name:
                res = screening.screen(name, lists, thr)
                if len(res):
                    st.error(f"{len(res)} correspondance(s) potentielle(s) — analyse discriminante requise.")
                    table(res, hide_index=True, use_container_width=True)
                else:
                    st.success("Aucune correspondance au-dessus du seuil.")
                log("A06", "Filtrage", details=f"{name} → {len(res)}")
        section("Filtrage par lot")
        up = st.file_uploader("Fichier CSV/Excel avec une colonne « nom »", type=["csv", "xlsx"])
        if up:
            df = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
            col = next((c for c in df.columns if c.lower() in ("nom", "name", "raison_sociale")), df.columns[0])
            lists = screening.all_lists()
            out = []
            for n in df[col].astype(str):
                r = screening.screen(n, lists, thr, limit=1)
                out.append({"nom": n, "alerte": "OUI" if len(r) else "non", "meilleure_correspondance": r.iloc[0]["nom_liste"] if len(r) else "",
                            "source": r.iloc[0]["source"] if len(r) else "", "score": r.iloc[0]["score"] if len(r) else 0})
            out = pd.DataFrame(out)
            table(out, hide_index=True, use_container_width=True)
            st.download_button("⬇️ Résultats (Excel)", excel.dfs_to_xlsx({"Filtrage": out}, "Filtrage sanctions"), "Filtrage_sanctions.xlsx")
            log("A06", "Filtrage par lot", details=f"{len(out)} noms, {int((out.alerte == 'OUI').sum())} alertes")
        st.download_button("Fiche de traitement d'alerte (Word)", word.sanctions_alert_form(u.get("company") or ""), "Fiche_alerte_filtrage.docx")

with t4:
    hist = load("index_history.csv")
    pays = st.multiselect("Pays", cs["iso3"], format_func=dict(zip(cs.iso3, cs.pays)).get, default=["RUS", "DZA", "NAM", "BIH", "IRQ", "NGA"])
    h = hist[hist["iso3"].isin(pays)].merge(cs[["iso3", "pays"]], on="iso3")
    f = px.line(h, x="date", y="indice", color="pays", markers=True, hover_data=["evenement", "gafi_statut", "ue_pays_tiers_haut_risque"])
    f.update_layout(**PLOTLY_LAYOUT, height=380, yaxis_title="Indice de sécurité financière", xaxis_title="")
    chart(f, use_container_width=True)
    table(hist.groupby(["date", "evenement"], as_index=False).agg(indice_moyen=("indice", "mean"), liste_grise=("gafi_statut", lambda s: (s == "grise").sum()),
                                                                          liste_ue=("ue_pays_tiers_haut_risque", "sum")).round(2),
                 hide_index=True, use_container_width=True)
footer()
