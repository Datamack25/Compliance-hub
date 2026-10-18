from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import auth
from core.data import load
from core.ui import footer, hero, kpi, section

u = auth.current_user()
if u.get("role") != "admin":
    st.error("Accès réservé à l'administrateur.")
    st.stop()
hero("Administration", "Utilisateurs, offres, codes d'activation et journal des agents.", kicker="Admin")
if u["email"] == "admin@regbridge.fr":
    st.warning("Compte administrateur par défaut : définissez ADMIN_EMAIL et ADMIN_PASSWORD dans les secrets avant toute mise en production.")
users = pd.DataFrame(auth.list_users())
k1, k2, k3 = st.columns(3)
with k1: kpi("Utilisateurs", len(users))
with k2: kpi("Comptes payants actifs", int(((users["plan"] != "free") & (users["plan_expiry"] >= date.today().isoformat())).sum()), "", "green")
with k3: kpi("Exécutions d'agents", len(load("agent_log.csv")), "", "teal")

t1, t2 = st.tabs(["👥 Utilisateurs", "🎟️ Codes d'activation"])
with t1:
    st.dataframe(users, hide_index=True, use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    em = c1.selectbox("Utilisateur", users["email"])
    pl = c2.selectbox("Offre", list(auth.PLANS), format_func=lambda k: auth.PLANS[k]["label"])
    ex = c3.date_input("Expiration", date.today() + timedelta(days=30))
    if c4.button("Appliquer", type="primary"):
        auth.set_plan(em, pl, ex.isoformat())
        st.success("Offre mise à jour.")
        st.rerun()
    if st.button("Supprimer l'utilisateur sélectionné"):
        auth.delete_user(em)
        st.rerun()
with t2:
    c1, c2, c3 = st.columns(3)
    pl = c1.selectbox("Offre du code", ["pro", "enterprise"], format_func=lambda k: auth.PLANS[k]["label"])
    days = c2.number_input("Durée (jours)", 7, 730, 30)
    n = c3.number_input("Nombre de codes", 1, 50, 1)
    if st.button("Générer", type="primary"):
        codes = [auth.create_code(pl, int(days)) for _ in range(int(n))]
        st.code("\n".join(codes))
    section("Codes émis")
    st.dataframe(pd.DataFrame(auth.list_codes()), hide_index=True, use_container_width=True)
footer()
