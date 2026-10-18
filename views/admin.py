from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import auth
from core.data import load
from core.ui import footer, hero, kpi, section, table

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
with k2: kpi("Comptes payants actifs", int(((users["plan"] != "free") & (users["plan_expiry"].astype(str) >= date.today().isoformat())).sum()), "", "green")
with k3: kpi("Exécutions d'agents", len(load("agent_log.csv")), "", "teal")

t1, t2 = st.tabs(["👥 Utilisateurs", "🎟️ Codes d'activation"])
with t1:
    table(users, hide_index=True, use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    em = c1.selectbox("Utilisateur", users["email"])
    pl = c2.selectbox("Offre", list(auth.PLANS), format_func=lambda k: auth.PLANS[k]["label"])
    ex = c3.date_input("Expiration", date.today() + timedelta(days=30))
    if c4.button("Appliquer", type="primary"):
        auth.set_plan(em, pl, ex.isoformat())
        st.success("Offre mise à jour.")
        st.rerun()
    a1, a2 = st.columns(2)
    if a1.button("🔑 Réinitialiser le mot de passe du compte sélectionné"):
        tmp, key = auth.admin_reset_password(em)
        st.success(f"Mot de passe temporaire : **{tmp}** · nouvelle clé de récupération : **{key}** — à transmettre à l'utilisateur.")
    if a2.button("🗑️ Supprimer l'utilisateur sélectionné"):
        auth.delete_user(em)
        st.rerun()
    st.download_button("⬇️ Exporter le registre des comptes (CSV, sans mots de passe)",
                       users.to_csv(index=False).encode("utf-8"), "registre_comptes.csv")
    if auth.backup_enabled():
        st.success("Sauvegarde GitHub active : les registres (comptes, codes, certificats) sont sauvegardés à chaque modification.")
    else:
        st.warning("Sauvegarde GitHub non configurée : sur Streamlit Cloud, les comptes sont perdus à chaque redémarrage. "
                   "Ajoutez GITHUB_TOKEN et GITHUB_DATA_REPO (dépôt privé) dans les secrets.")
with t2:
    c1, c2, c3 = st.columns(3)
    pl = c1.selectbox("Offre du code", ["pro", "enterprise"], format_func=lambda k: auth.PLANS[k]["label"])
    days = c2.number_input("Durée (jours)", 7, 730, 30)
    n = c3.number_input("Nombre de codes", 1, 50, 1)
    if st.button("Générer", type="primary"):
        codes = [auth.create_code(pl, int(days)) for _ in range(int(n))]
        st.code("\n".join(codes))
    section("Codes émis")
    table(pd.DataFrame(auth.list_codes()), hide_index=True, use_container_width=True)
footer()
