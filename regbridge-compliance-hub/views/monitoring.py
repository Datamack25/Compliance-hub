import pandas as pd
import plotly.express as px
import streamlit as st

from agents.registry import log
from core import auth, ml
from core.data import append_row, load
from core.ui import PLOTLY_LAYOUT, chart, footer, hero, kpi, section, table
from generators import excel

hero("Surveillance transactionnelle", "Scénarios experts (structuration, comptes de passage, pays à risque, embargos) + Isolation Forest — les poids s'ajustent avec vos retours.",
     kicker="Agent A09 · Surveillance")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()

c1, c2 = st.columns([2, 1])
up = c1.file_uploader("Transactions (CSV/Excel : tx_id, client_id, date, type, montant, pays_contrepartie, sens)", type=["csv", "xlsx"])
demo = load("transactions_demo.csv")
c2.download_button("Modèle de fichier", demo.head(10).to_csv(index=False).encode("utf-8"), "modele_transactions.csv")
tx = (pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)) if up else demo
cs = load("countries.csv")


@st.cache_data(show_spinner="Analyse des transactions…")
def run(tx_df: pd.DataFrame, w_sig: str):
    return ml.monitor(tx_df, cs)


w = ml.rule_weights()
alerts = run(tx, str(w))
crit = alerts[alerts["priorite"].isin(["Critique", "Haute"])]
k1, k2, k3, k4 = st.columns(4)
with k1: kpi("Transactions", f"{len(tx):,}".replace(",", " "))
with k2: kpi("Clients surveillés", len(alerts))
with k3: kpi("Alertes critiques / hautes", len(crit), "", "red")
with k4: kpi("Volume analysé", f"{tx['montant'].sum() / 1e6:.2f} M€", "", "teal")

g1, g2 = st.columns([1.3, 1])
with g1:
    f = px.scatter(alerts, x="score_anomalie", y="score_regles", size="volume_total", color="priorite", hover_name="client_id",
                   hover_data=["regles"], color_discrete_map={"Critique": "#B42318", "Haute": "#F79009", "Moyenne": "#FEC84B", "Faible": "#0E7490"})
    f.update_layout(**PLOTLY_LAYOUT, height=360, title="Clients : anomalie statistique × règles expertes", xaxis_title="Score Isolation Forest",
                    yaxis_title="Score règles (pondéré)")
    chart(f, use_container_width=True)
with g2:
    rules = alerts["regles"].str.split(", ").explode().replace("", pd.NA).dropna().value_counts().reset_index()
    rules.columns = ["règle", "clients"]
    rules["libellé"] = rules["règle"].map(ml.RULES)
    f = px.bar(rules, x="clients", y="règle", orientation="h", hover_data=["libellé"], color_discrete_sequence=["#0B1F3A"])
    f.update_layout(**PLOTLY_LAYOUT, height=360, title="Déclenchements par règle", yaxis_title="")
    chart(f, use_container_width=True)

section("File d'alertes priorisée")
view = alerts[alerts["score_alerte"] >= 40][["client_id", "priorite", "score_alerte", "regles", "score_anomalie", "nb_operations", "volume_total",
                                              "especes", "flux_pays_risque", "nb_embargo"]]
table(view, hide_index=True, use_container_width=True, height=330,
             column_config={"score_alerte": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                            "volume_total": st.column_config.NumberColumn(format="%.0f €"), "especes": st.column_config.NumberColumn(format="%.0f €"),
                            "flux_pays_risque": st.column_config.NumberColumn(format="%.0f €")})

l, r = st.columns([1.2, 1])
with l:
    section("Analyse d'un client")
    cid = st.selectbox("Client", view["client_id"] if len(view) else alerts["client_id"])
    row = alerts[alerts["client_id"] == cid].iloc[0]
    st.markdown(f"**Règles déclenchées :** {row['regles'] or 'aucune'}")
    for rr in [x for x in row["regles"].split(", ") if x]:
        st.markdown(f"- `{rr}` {ml.RULES[rr]} — poids appris **{ml.rule_weight_value(w, rr):.2f}**")
    table(tx[tx["client_id"] == cid].sort_values("date"), hide_index=True, use_container_width=True, height=240)
    a, b = st.columns(2)
    hits = [x for x in row["regles"].split(", ") if x]
    if a.button("✅ Vrai positif (suspect)", type="primary"):
        ml.update_rule_weights(hits, True)
        append_row("feedback.csv", {"date": pd.Timestamp.now().isoformat(timespec="seconds"), "source": "surveillance", "objet_id": cid,
                                    "prediction": row["priorite"], "label_analyste": 1, "commentaire": row["regles"]})
        log("A09", "Retour analyste", details=f"{cid} vrai positif")
        st.cache_data.clear()
        st.rerun()
    if b.button("❎ Faux positif"):
        ml.update_rule_weights(hits, False)
        append_row("feedback.csv", {"date": pd.Timestamp.now().isoformat(timespec="seconds"), "source": "surveillance", "objet_id": cid,
                                    "prediction": row["priorite"], "label_analyste": 0, "commentaire": row["regles"]})
        log("A09", "Retour analyste", details=f"{cid} faux positif")
        st.cache_data.clear()
        st.rerun()
with r:
    section("Poids appris des règles (Bêta-Binomial)")
    wt = pd.DataFrame([{"règle": k, "libellé": v, "poids": ml.rule_weight_value(w, k), "VP": w[k]["alpha"] - 2, "FP": w[k]["beta"] - 2}
                       for k, v in ml.RULES.items()])
    table(wt, hide_index=True, use_container_width=True, height=300,
                 column_config={"poids": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    st.caption("Chaque retour « vrai positif » augmente la précision estimée de la règle, chaque « faux positif » la diminue : le score des futures alertes s'adapte.")
    pre = pd.DataFrame({"N° alerte": [f"AL-{i:04d}" for i in range(1, len(view) + 1)], "Date": pd.Timestamp.today().strftime("%d/%m/%Y"),
                        "Client": view["client_id"].values, "Scénario": view["regles"].values, "Montant": view["volume_total"].round(0).values,
                        "Analyste": "", "Date de prise en charge": "", "Délai (jours)": "", "Conclusion": "", "Examen renforcé": "", "DS (O/N)": "",
                        "Référence Ermes": "", "Date clôture": ""})
    st.download_button("⬇️ Registre des alertes (Excel)", excel.template("registre_alertes", u.get("company") or "", pre), "Registre_alertes.xlsx", type="primary")
footer()
