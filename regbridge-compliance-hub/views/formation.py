import random

import pandas as pd
import streamlit as st

from agents.registry import log
from core import auth
from core.data import load
from core.ui import footer, hero, kpi, section
from generators import pdf, word

u = auth.current_user()
hero("Formation & certification", "Modules LCB-FT, sanctions, PPE, crypto, fraude, AMLR/AMLA — quiz notés et certificats PDF vérifiables.",
     kicker="Agent A01 · Formation")

qb = load("quiz_bank.csv")
modules = ["Parcours complet"] + sorted(qb["module"].unique())
SUPPORTS = {
    "Fondamentaux LCB-FT": "Blanchiment = placement, empilement, intégration. Obligations : classification des risques, vigilance, DS à Tracfin, gel des avoirs, conservation 5 ans, formation. Risques sectoriels ACPR 2023 : transmission de fonds, monnaie électronique et actifs numériques « très élevés ».",
    "KYC / CDD": "Identifier et vérifier le client et le BE (> 25 % ou contrôle), recueillir l'objet de la relation, revenus/patrimoine ou CA. AMLR (10/07/2027) : règles uniformes, remédiation du stock fondée sur les risques (art. 26).",
    "PPE": "Fonctions listées au JOUE C/2023/724. Accord de la direction, origine du patrimoine, surveillance renforcée, statut maintenu ≥ 12 mois après la fin des fonctions.",
    "Sanctions & gel": "Listes UE, ONU, DG Trésor (et OFAC si exposition USD). GAFI juin 2026 : liste noire Corée du Nord, Iran, Myanmar ; ajouts liste grise Bosnie-Herzégovine et Irak. Paiements instantanés : filtrage quotidien (Règl. 2024/886).",
    "Surveillance & DS": "Scénarios calibrés sur le profil financier ; pilotage des stocks d'alertes ; surveillance des flux pays effectifs (décision ACPR Delubac 2025 : blâme + 600 000 €). DS préalable à l'exécution.",
    "Crypto-actifs": "MiCA : fin du régime transitoire PSAN au 1er juillet 2026. TFR : Travel Rule, vérification des wallets non hébergés au-delà de 1 000 €. Typologies Tracfin : rug pull, NFT, micro-paiements vers wallets connus.",
    "Fraude": "Mules financières, fraude au faux conseiller, FOVI/faux fournisseur : double validation, contre-appel, VoP.",
    "Jeux & hasard": "Mises en espèces sans ressources licites, rachat de tickets gagnants, chip dumping : identification au-delà des seuils et origine des fonds.",
    "Immobilier": "Prix décotés, absence de prêt, SCI étrangères, non-résidents : identification des BE et origine des fonds.",
    "Assurance": "Rachats anticipés malgré pénalités, tiers payeurs, bénéficiaires sans lien : contrôle au dénouement.",
    "AMLR / AMLA": "AMLA (Francfort) : supervision directe d'environ 40 entités à partir de 2028, RTS/ITS CDD. AMLR applicable au 10/07/2027 ; plafond espèces 10 000 €.",
}

t1, t2, t3 = st.tabs(["📘 Suivre un module", "🏅 Mes certificats", "🔍 Vérifier un certificat"])
with t1:
    c1, c2 = st.columns([1, 1.4])
    module = c1.selectbox("Module", modules)
    nq = c1.slider("Nombre de questions", 5, 20, 10)
    with c2:
        if module in SUPPORTS:
            st.info(SUPPORTS[module])
        else:
            st.info("Parcours complet : questions tirées de tous les modules. Seuil de réussite : 70 %.")
    if c1.button("Démarrer le quiz", type="primary") or "quiz" not in st.session_state:
        pool = qb if module == "Parcours complet" else qb[qb["module"] == module]
        rng = random.Random()
        sample = pool.sample(min(nq, len(pool)), random_state=rng.randint(0, 9999))
        qs = []
        for r in sample.itertuples():
            opts = [r.bonne_reponse] + r.distracteurs.split("|")
            rng.shuffle(opts)
            qs.append({"id": r.id, "q": r.question, "opts": opts, "a": r.bonne_reponse, "m": r.module})
        st.session_state["quiz"] = {"module": module, "qs": qs, "done": False}
    quiz = st.session_state["quiz"]
    with st.form("quiz_form"):
        st.markdown(f"#### {quiz['module']} — {len(quiz['qs'])} questions")
        answers = {}
        for i, q in enumerate(quiz["qs"], 1):
            answers[q["id"]] = st.radio(f"**{i}. {q['q']}**", q["opts"], index=None, key=f"q_{q['id']}")
        sub = st.form_submit_button("Valider mes réponses", type="primary")
    if sub:
        good = sum(answers[q["id"]] == q["a"] for q in quiz["qs"])
        score = 100 * good / len(quiz["qs"])
        st.session_state["quiz_result"] = (quiz["module"], score)
        log("A01", "Quiz", details=f"{quiz['module']} {score:.0f}%")
        for q in quiz["qs"]:
            if answers[q["id"]] != q["a"]:
                st.markdown(f"❌ {q['q']}  \n→ Bonne réponse : **{q['a']}**")
    res = st.session_state.get("quiz_result")
    if res:
        mod, score = res
        a, b = st.columns(2)
        with a:
            kpi("Score", f"{score:.0f} %", "Seuil de réussite 70 %", "green" if score >= 70 else "red")
        with b:
            if score >= 70:
                if auth.has_access(u, "pro"):
                    name = st.text_input("Nom sur le certificat", value=u.get("name") or "")
                    if st.button("Générer mon certificat PDF", type="primary"):
                        data, cid = pdf.certificate(name, mod, score, u.get("company") or "")
                        auth.save_certificate(cid, u["email"], name, mod, score)
                        log("A01", "Certificat", details=cid)
                        st.download_button("⬇️ Télécharger le certificat", data, file_name=f"Certificat_{cid}.pdf", mime="application/pdf")
                else:
                    auth.guard("pro")
            else:
                st.warning("Score insuffisant pour la certification : révisez le support et recommencez.")
    section("Supports de session")
    st.download_button("Feuille d'émargement (Word)", word.training_attendance(u.get("company") or "", module),
                       file_name="Emargement_formation.docx")
with t2:
    with auth.conn() as c:
        rows = [dict(r) for r in c.execute("SELECT cert_id,name,module,score,issued FROM certificates WHERE email=? ORDER BY issued DESC", (u["email"],))]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True) if rows else st.info("Aucun certificat pour le moment.")
with t3:
    cid = st.text_input("N° de certificat")
    if st.button("Vérifier", key="verif") and cid:
        c = auth.verify_certificate(cid)
        st.success(f"Authentique — {c['name']} · {c['module']} · {c['score']:.0f} % · {c['issued'][:10]}") if c else st.error("Introuvable.")
footer()
