import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import auth
from core.data import RISK_COLORS, load
from core.feeds import fetch_news
from core.ui import PLOTLY_LAYOUT, chart, footer, geo_chart, hero, js_counters, js_ticker, section, table

u = auth.current_user()
hero("Tableau de bord sécurité financière", "Situation mondiale LCB-FT, sanctions et embargos — actualités, cartographie dynamique, jauge d'évolution.",
     badge=f"Bonjour {(u.get('name') or '').split(' ')[0] or u['email']}")

news, online = fetch_news()
js_ticker(news.head(25).to_dict("records"))

cs = load("countries.csv")
hist = load("index_history.csv")
sanc = load("sanctions_regimes.csv")
ppe = load("pep_watchlist.csv")
glob_now = round(cs["indice_securite_financiere"].mean(), 1)
snap = hist.groupby(["date", "evenement"], as_index=False)["indice"].mean().sort_values("date")
prev = snap["indice"].iloc[-1] if len(snap) else glob_now
if len(snap) and abs(prev - glob_now) < 1e-9 and len(snap) > 1:
    prev = snap["indice"].iloc[-2]

js_counters([
    ("Liste grise GAFI", int((cs["gafi_statut"] == "grise").sum()), 0, "Juridictions sous surveillance"),
    ("Liste noire GAFI", int((cs["gafi_statut"] == "noire").sum()), 0, "Appel à l'action"),
    ("Pays tiers haut risque UE", int(cs["ue_pays_tiers_haut_risque"].sum()), 0, "Règl. 2016/1675 modifié"),
    ("Régimes de sanctions", len(sanc), 0, "UE · ONU · OFAC · France"),
    ("PPE surveillées", len(ppe), 0, "Registre interne"),
    ("Indice mondial", glob_now, 1, "Sécurité financière /100"),
], deadline="2027-07-10")

# ------------------------------------------------------------------ carte + jauge
section("Cartographie mondiale de la sécurité financière")
c1, c2 = st.columns([2.1, 1], gap="medium")
with c1:
    f1, f2 = st.columns([1.4, 1])
    factor = f1.selectbox("Facteur affiché", ["Indice de sécurité financière", "Statut GAFI", "Liste UE pays à haut risque",
                                               "Intensité des sanctions", "Corruption (IPC indicatif)", "Risque PPE"], label_visibility="collapsed")
    periods = ["Situation actuelle"] + [f"{r.date} — {r.evenement}" for r in snap.itertuples()][::-1]
    period = f2.selectbox("Période", periods, label_visibility="collapsed")
    df = cs.copy()
    if period != "Situation actuelle":
        d, ev = period.split(" — ", 1)
        h = hist[(hist["date"] == d) & (hist["evenement"] == ev)].set_index("iso3")
        df["indice_securite_financiere"] = df["iso3"].map(h["indice"]).fillna(df["indice_securite_financiere"])
        df["gafi_statut"] = df["iso3"].map(h["gafi_statut"]).fillna(df["gafi_statut"])
        df["ue_pays_tiers_haut_risque"] = df["iso3"].map(h["ue_pays_tiers_haut_risque"]).fillna(df["ue_pays_tiers_haut_risque"])
    hover = {"iso3": False, "gafi_statut": True, "regimes_sanctions": True, "indice_securite_financiere": ":.1f"}
    if factor == "Indice de sécurité financière":
        fig = px.choropleth(df, locations="iso3", color="indice_securite_financiere", hover_name="pays", hover_data=hover,
                            color_continuous_scale=["#B42318", "#EA580C", "#FACC15", "#86EFAC", "#067647"], range_color=(0, 100),
                            labels={"indice_securite_financiere": "Indice"})
    elif factor == "Statut GAFI":
        df["GAFI"] = df["gafi_statut"].map({"-": "Non listé", "grise": "Liste grise", "noire": "Liste noire"})
        fig = px.choropleth(df, locations="iso3", color="GAFI", hover_name="pays",
                            color_discrete_map={"Non listé": "#D1FADF", "Liste grise": "#F79009", "Liste noire": "#101828"})
    elif factor == "Liste UE pays à haut risque":
        df["UE"] = df["ue_pays_tiers_haut_risque"].map({1: "Pays tiers à haut risque", 0: "Non listé"})
        fig = px.choropleth(df, locations="iso3", color="UE", hover_name="pays",
                            color_discrete_map={"Non listé": "#E0F2FE", "Pays tiers à haut risque": "#B42318"})
    elif factor == "Intensité des sanctions":
        fig = px.choropleth(df, locations="iso3", color="niveau_sanctions", hover_name="pays", hover_data={"regimes_sanctions": True},
                            color_continuous_scale=["#F2F4F7", "#FEC84B", "#F04438", "#7A271A"], range_color=(0, 3),
                            labels={"niveau_sanctions": "Sanctions (0-3)"})
    elif factor == "Corruption (IPC indicatif)":
        df["IPC"] = df["ipc_indicatif"].where(df["ipc_indicatif"] > 0)
        fig = px.choropleth(df, locations="iso3", color="IPC", hover_name="pays", color_continuous_scale="RdYlGn", range_color=(0, 100))
    else:
        fig = px.choropleth(df, locations="iso3", color="risque_ppe", hover_name="pays",
                            color_discrete_map={"Standard": "#D1FADF", "Modéré": "#FEC84B", "Élevé": "#F04438"})
    fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth", bgcolor="rgba(0,0,0,0)",
                    showcountries=True, countrycolor="#FFFFFF", landcolor="#EEF2F6", showland=True)
    fig.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=0, r=0, t=0, b=0)}, height=440,
                      legend=dict(orientation="h", y=-0.02), coloraxis_colorbar=dict(thickness=10, len=0.6))
    geo_chart(fig)

with c2:
    g = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=glob_now, number={"font": {"size": 30, "color": "#0B1F3A"}, "valueformat": ".1f"},
        domain={"x": [0.06, 0.94], "y": [0, 0.9]},
        delta={"reference": prev, "valueformat": ".2f", "increasing": {"color": "#067647"}, "decreasing": {"color": "#B42318"}},
        title={"text": "Indice mondial de sécurité financière (/100)", "font": {"size": 13, "color": "#0B1F3A"}},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#0B1F3A", "thickness": 0.22},
               "steps": [{"range": [0, 42], "color": "#FECDCA"}, {"range": [42, 62], "color": "#FDDCAB"},
                         {"range": [62, 80], "color": "#FEF0C7"}, {"range": [80, 100], "color": "#D1FADF"}],
               "threshold": {"line": {"color": "#0E7490", "width": 3}, "value": prev}}))
    g.update_layout(**{**PLOTLY_LAYOUT, "margin": dict(l=30, r=30, t=46, b=10)}, height=250)
    chart(g, use_container_width=True)
    ev = pd.concat([snap[["date", "indice"]], pd.DataFrame([{"date": pd.Timestamp.today().strftime("%Y-%m-%d"), "indice": glob_now}])])
    line = px.line(ev, x="date", y="indice", markers=True)
    line.update_traces(line_color="#0E7490")
    line.update_layout(**PLOTLY_LAYOUT, height=190, yaxis_title="", xaxis_title="", title=dict(text="Évolution de l'indice", font=dict(size=13)))
    chart(line, use_container_width=True)
    st.caption("Indice composite : statut GAFI, liste UE, sanctions, IPC, conflits, opacité. Nouveau point à chaque mise à jour (onglet Sanctions).")

# ------------------------------------------------------------------ régions & pays
r1, r2 = st.columns([1, 1.2], gap="medium")
with r1:
    section("Risque moyen par région")
    reg = cs.groupby("region", as_index=False)["indice_securite_financiere"].mean().sort_values("indice_securite_financiere")
    b = px.bar(reg, x="indice_securite_financiere", y="region", orientation="h", text_auto=".1f",
               color="indice_securite_financiere", color_continuous_scale=["#B42318", "#FACC15", "#067647"], range_color=(30, 95))
    b.update_layout(**PLOTLY_LAYOUT, height=300, coloraxis_showscale=False, xaxis_title="Indice /100", yaxis_title="")
    chart(b, use_container_width=True)
with r2:
    section("Juridictions les plus exposées")
    top = cs.nsmallest(10, "indice_securite_financiere")[["pays", "gafi_statut", "regimes_sanctions", "indice_securite_financiere", "niveau_risque_pays"]]
    table(top, hide_index=True, use_container_width=True, height=300,
                 column_config={"indice_securite_financiere": st.column_config.ProgressColumn("Indice", min_value=0, max_value=100, format="%.1f"),
                                "gafi_statut": "GAFI", "regimes_sanctions": "Sanctions", "niveau_risque_pays": "Niveau", "pays": "Pays"})

# ------------------------------------------------------------------ actualités + échéances
n1, n2 = st.columns([1.5, 1], gap="medium")
with n1:
    section("Dernières actualités conformité")
    st.caption("Flux en direct" if online else "Mode hors-ligne : sélection éditoriale (connectez la plateforme à Internet pour le flux en direct).")
    themes = ["Tous"] + sorted(news["theme"].dropna().unique().tolist())
    th = st.radio("Thème", themes, horizontal=True, label_visibility="collapsed")
    nn = news if th == "Tous" else news[news["theme"] == th]
    for r in nn.head(9).itertuples():
        st.markdown(f'<div class="rb-news"><a href="{html.escape(str(r.link))}" target="_blank">{html.escape(str(r.title))}</a>'
                    f'<div class="meta">{html.escape(str(r.source))} · {html.escape(str(r.published))} · {html.escape(str(r.theme))}</div></div>',
                    unsafe_allow_html=True)
with n2:
    section("Échéances réglementaires")
    regs = load("regulations.csv")
    up = regs[regs["Statut"] == "À venir"].sort_values("Date d'entrée en vigueur")
    for r in up.itertuples():
        days = (pd.Timestamp(r._5) - pd.Timestamp.today()).days
        st.markdown(f'<div class="rb-news" style="border-left-color:#B8891B"><b>{html.escape(r._2)}</b>'
                    f'<div class="meta">{r._5} · J-{days}</div></div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ articles
section("Ressources et articles de sécurité financière")
arts = load("articles.csv")
cats = ["Toutes"] + sorted(arts["categorie"].unique())
cat = st.pills("Catégorie", cats, default="Toutes", label_visibility="collapsed") or "Toutes"
arts = arts if cat == "Toutes" else arts[arts["categorie"] == cat]
cols = st.columns(3)
for i, r in enumerate(arts.itertuples()):
    with cols[i % 3]:
        st.markdown(f'<div class="rb-article"><div class="cat">{html.escape(r.categorie)}</div>'
                    f'<a href="{r.url}" target="_blank">{html.escape(r.titre)} ↗</a><p>{html.escape(r.description)}</p></div>',
                    unsafe_allow_html=True)
        st.write("")
footer()
