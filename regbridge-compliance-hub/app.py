"""RegBridge Compliance Hub — point d'entrée Streamlit.

Lancement : streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="RegBridge Compliance Hub", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

from agents.registry import AGENTS  # noqa: E402
from core import auth  # noqa: E402
from core.data import SECTOR_LABELS  # noqa: E402
from core.paths import APP_NAME, APP_TAGLINE  # noqa: E402
from core.ui import card, footer, hero, inject_css, section  # noqa: E402

inject_css()
auth.init_db()


def landing():
    hero(APP_NAME, APP_TAGLINE + " — 15 agents spécialisés, IA auto-apprenante, générateurs Word/Excel/PDF/ZIP.",
         kicker="RegBridge Conseil · Plateforme RegTech", badge="AMLR / AMLA ready · 10/07/2027")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        section("Ce que fait la plateforme")
        cols = st.columns(2)
        feats = [
            ("Cartographies des risques", "Excel personnalisable par secteur et typologie d'entreprise, formules vivantes, matrice de chaleur et plan d'action."),
            ("Sanctions, embargos & GAFI", "Pays sous sanctions, listes grise/noire GAFI, pays tiers à haut risque UE, filtrage de noms sur listes officielles."),
            ("PPE & presse négative", "Surveillance des PPE par pays (JOUE C/2023/724) et détection d'informations négatives (corruption, fraude)."),
            ("Surveillance & ML", "Scénarios experts, Isolation Forest et scoring client qui s'améliore avec les retours de vos analystes."),
            ("Kit documentaire ZIP", "Procédures, fiches KYC, trames d'examen renforcé, registres : banque, assurance, fintech, jeux, immobilier, MTO, crypto."),
            ("Formation certifiante", "Quiz par module et certificats PDF vérifiables (CMF L.561-34)."),
        ]
        for i, (t, b) in enumerate(feats):
            with cols[i % 2]:
                card(t, b)
                st.write("")
    with right:
        section("Accès")
        t1, t2, t3 = st.tabs(["Se connecter", "Créer un compte", "Vérifier un certificat"])
        with t1:
            with st.form("login"):
                email = st.text_input("E-mail")
                pwd = st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Connexion", type="primary", use_container_width=True):
                    u = auth.login(email, pwd)
                    if u:
                        auth.start(u)
                        st.rerun()
                    st.error("Identifiants incorrects.")
            st.caption("Compte de démonstration administrateur : admin@regbridge.fr / Admin!2026 (à changer via les secrets).")
        with t2:
            with st.form("signup"):
                name = st.text_input("Nom complet")
                company = st.text_input("Société")
                sector = st.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get)
                email = st.text_input("E-mail professionnel")
                pwd = st.text_input("Mot de passe (8+ caractères, 1 majuscule, 1 chiffre)", type="password")
                ok_cgu = st.checkbox("J'accepte les conditions d'utilisation et la politique de confidentialité")
                if st.form_submit_button("Créer mon compte — essai Pro 7 jours", type="primary", use_container_width=True):
                    if not ok_cgu:
                        st.warning("Merci d'accepter les conditions.")
                    else:
                        ok, msg = auth.register(email, name, company, sector, pwd)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            auth.start(auth.login(email, pwd))
                            st.rerun()
        with t3:
            cid = st.text_input("N° de certificat (ex. RB-XXXXXXXXXX)")
            if st.button("Vérifier") and cid:
                c = auth.verify_certificate(cid)
                if c:
                    st.success(f"Certificat authentique — {c['name']} · {c['module']} · score {c['score']:.0f} % · émis le {c['issued'][:10]}")
                else:
                    st.error("Certificat introuvable.")
    section("Offres")
    p1, p2, p3 = st.columns(3)
    for col, key, feats, featured in [
        (p1, "free", ["Tableau de bord et actualités", "Pays, sanctions & GAFI (consultation)", "Veille réglementaire & jurisprudence", "Formation (quiz)"], False),
        (p2, "pro", ["Tout Découverte +", "Cartographies Excel personnalisées", "Trames EDD, fiches KYC, remédiation", "PPE, presse négative, surveillance ML", "Certificats PDF"], True),
        (p3, "enterprise", ["Tout Professionnel +", "Kit ZIP multi-secteurs (200+ documents)", "Laboratoire ML & auto-amélioration", "Multi-utilisateurs, administration"], False),
    ]:
        with col:
            plan = auth.PLANS[key]
            li = "".join(f"<li>{f}</li>" for f in feats)
            st.markdown(f'<div class="rb-plan {"featured" if featured else ""}"><h4>{plan["label"]}</h4>'
                        f'<div class="price">{plan["price"]}</div><ul>{li}</ul></div>', unsafe_allow_html=True)
    footer()


user = auth.current_user()
if not user and st.query_params.get("s"):
    user = auth.user_from_session(st.query_params["s"])
    if user:
        st.session_state["user"], st.session_state["sid"] = user, st.query_params["s"]
if not user:
    landing()
    st.stop()

user = auth.refresh(user["email"]) or user
st.session_state["user"] = user
plan = auth.effective_plan(user)

with st.sidebar:
    st.markdown(f"### 🛡️ {APP_NAME}")
    st.markdown(f"**{user.get('name') or user['email']}**  \n{user.get('company') or ''}")
    exp = user.get("plan_expiry") or ""
    st.markdown(f"Offre : **{auth.PLANS[plan]['label']}**" + (f" · jusqu'au {exp}" if plan != "free" and exp < "2099" else ""))
    if st.button("Se déconnecter", use_container_width=True):
        auth.end_session(st.session_state.get("sid"))
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

lock = lambda a: "" if auth.has_access(user, a.plan) else " 🔒"  # noqa: E731
pages = {
    "Pilotage": [st.Page("views/dashboard.py", title="Tableau de bord", icon="📊", default=True),
                 st.Page("views/agents_hub.py", title="Orchestrateur des agents", icon="🤖")],
    "Agents conformité": [st.Page(a.page, title=f"{a.name.replace('Agent ', '')}{lock(a)}", icon=a.icon) for a in AGENTS if a.code not in ("A13", "A14")],
    "Production & IA": [st.Page(a.page, title=f"{a.name.replace('Agent ', '')}{lock(a)}", icon=a.icon) for a in AGENTS if a.code in ("A13", "A14")],
    "Compte": [st.Page("views/account.py", title="Mon compte & abonnement", icon="👤")]
    + ([st.Page("views/admin.py", title="Administration", icon="🛠️")] if user.get("role") == "admin" else []),
}
nav = st.navigation(pages, expanded=True)
if st.session_state.get("sid"):
    st.query_params["s"] = st.session_state["sid"]  # reprise de session après rechargement
nav.run()
