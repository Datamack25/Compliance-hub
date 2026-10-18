import re

import pandas as pd
import streamlit as st

from agents.registry import log
from core import auth, ml
from core.data import load
from core.feeds import search_news
from core.ui import footer, hero, kpi, section
from generators import word

hero("Presse négative", "Détection d'informations négatives (corruption, fraude, blanchiment, sanctions, terrorisme) en sources ouvertes, avec pondération auto-apprenante.",
     kicker="Agent A08 · Presse négative")
if not auth.guard("pro"):
    st.stop()
u = auth.current_user()
kw = load("adverse_keywords.csv")

c1, c2, c3 = st.columns([2, 1, 1])
subject = c1.text_input("Personne ou société", placeholder="Nom complet entre guillemets recommandé")
lang = c2.selectbox("Langue", ["fr", "en", "fr + en"])
strict = c3.toggle("Correspondance exacte", value=True)

if st.button("Lancer la recherche", type="primary") and subject:
    q_terms = " OR ".join(kw[kw["poids"] >= 2]["mot_cle"].head(12))
    base = f'"{subject}"' if strict else subject
    items, online = [], False
    for lg in (["fr", "en"] if lang == "fr + en" else [lang]):
        terms = " OR ".join(kw[(kw["langue"] == lg) & (kw["poids"] >= 1.5)]["mot_cle"].head(10))
        res, ok = search_news(f"{base} ({terms})", lg)
        items += res
        online |= ok
    rows = []
    for it in items:
        t = it["title"].lower()
        found = [k for k in kw["mot_cle"] if re.search(r"\b" + re.escape(k.lower()), t)]
        s = sum(float(kw.loc[kw["mot_cle"] == k, "poids"].iloc[0]) for k in found)
        rows.append({**it, "mots_cles": ", ".join(found), "score": round(s, 1)})
    df = pd.DataFrame(rows).drop_duplicates("title") if rows else pd.DataFrame(columns=["title", "link", "source", "published", "mots_cles", "score"])
    st.session_state["adv"] = (subject, df, online)
    log("A08", "Recherche presse négative", details=f"{subject} → {len(df)} articles")

if "adv" in st.session_state:
    subject, df, online = st.session_state["adv"]
    if not online:
        st.warning("Recherche en ligne indisponible : la plateforme doit être connectée à Internet (Streamlit Cloud l'est par défaut).")
    total = min(100, df["score"].sum() * 4) if len(df) else 0
    a, b, c = st.columns(3)
    with a: kpi("Articles trouvés", len(df))
    with b: kpi("Articles avec mots-clés", int((df["score"] > 0).sum()) if len(df) else 0, "", "amber")
    with c: kpi("Score presse négative", f"{total:.0f}/100", "≥ 40 : vigilance renforcée", "red" if total >= 40 else "green")
    if len(df):
        df = df.sort_values("score", ascending=False)
        section("Qualification par l'analyste (améliore la pondération des mots-clés)")
        for i, r in enumerate(df.head(15).itertuples()):
            x1, x2, x3 = st.columns([6, 1, 1])
            x1.markdown(f"**[{r.title}]({r.link})**  \n<small>{r.source} · {r.published} · mots-clés : {r.mots_cles or '—'} · score {r.score}</small>",
                        unsafe_allow_html=True)
            if x2.button("Pertinent", key=f"p{i}") and r.mots_cles:
                ml.update_keyword_weights(r.mots_cles.split(", "), True)
                log("A08", "Retour analyste", details="pertinent")
                load.clear()
                st.toast("Pondération renforcée")
            if x3.button("Non pertinent", key=f"n{i}") and r.mots_cles:
                ml.update_keyword_weights(r.mots_cles.split(", "), False)
                log("A08", "Retour analyste", details="non pertinent")
                load.clear()
                st.toast("Pondération réduite")
        st.download_button("⬇️ Rapport presse négative (Word)", word.adverse_report(u.get("company") or "", subject, df, total), "Rapport_presse_negative.docx",
                           type="primary")

section("Dictionnaire de mots-clés (pondérations apprises)")
st.dataframe(load("adverse_keywords.csv").sort_values("poids", ascending=False), hide_index=True, use_container_width=True, height=300)
footer()
