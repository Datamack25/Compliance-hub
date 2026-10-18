import streamlit as st

from core import auth
from core.ui import footer, hero, section

u = auth.current_user()
plan = auth.effective_plan(u)
hero("Mon compte & abonnement", f"{u['email']} — offre {auth.PLANS[plan]['label']}", kicker="Compte")

c1, c2 = st.columns(2)
with c1:
    section("Profil")
    st.markdown(f"**Identifiant unique :** `{u.get('user_id')}`  \n**E-mail :** {u.get('email')}  \n**Nom :** {u.get('name')}  \n**Société :** {u.get('company')}  \n**Secteur :** {u.get('sector')}  \n"
                f"**Offre :** {auth.PLANS[plan]['label']}" + (f" (jusqu'au {u.get('plan_expiry')})" if plan != "free" else ""))
    with st.form("pwd"):
        old = st.text_input("Mot de passe actuel", type="password")
        new = st.text_input("Nouveau mot de passe", type="password")
        if st.form_submit_button("Changer le mot de passe"):
            ok, msg = auth.change_password(u["email"], old, new)
            (st.success if ok else st.error)(msg)
    section("Clé de récupération")
    st.caption("La clé permet de réinitialiser le mot de passe (onglet « Mot de passe oublié »). Générer une nouvelle clé invalide l'ancienne.")
    if st.button("Générer une nouvelle clé de récupération"):
        key = auth.regenerate_recovery_key(u["email"])
        st.success(f"Nouvelle clé : **{key}** — à conserver, elle ne sera plus affichée.")
        st.download_button("⬇️ Télécharger", f"Identifiant : {u.get('user_id')}\nClé de récupération : {key}\n".encode("utf-8"),
                           f"RegBridge_{u.get('user_id')}.txt")
with c2:
    section("Activer un code")
    code = st.text_input("Code d'activation (reçu après paiement)")
    if st.button("Activer", type="primary") and code:
        ok, msg = auth.redeem(u["email"], code)
        (st.success if ok else st.error)(msg)
        if ok:
            st.session_state["user"] = auth.refresh(u["email"])
            st.rerun()

section("Souscrire")
links = auth.payment_links()
p1, p2 = st.columns(2)
for col, key in ((p1, "pro"), (p2, "enterprise")):
    with col:
        pl = auth.PLANS[key]
        st.markdown(f'<div class="rb-plan {"featured" if key == "pro" else ""}"><h4>{pl["label"]}</h4><div class="price">{pl["price"]}</div></div>',
                    unsafe_allow_html=True)
        if links[key]:
            st.link_button(f"Payer l'offre {pl['label']} (Stripe)", links[key], type="primary", use_container_width=True)
        else:
            st.caption("Paiement en ligne non configuré : contactez l'administrateur pour obtenir un code d'activation.")
st.caption("Après paiement, un code d'activation vous est transmis par e-mail ; saisissez-le ci-dessus. Les offres se cumulent (la durée s'ajoute).")
footer()
