"""Registre des agents de conformité et journal d'activité (data/agent_log.csv).

Chaque agent est une unité spécialisée (mission, page, offre requise). Les agents journalisent leurs
exécutions ; l'orchestrateur et l'agent d'auto-amélioration exploitent ce journal (taux de succès,
volumes, retours analystes) pour prioriser les réentraînements et ajuster les règles.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import streamlit as st

from core.data import append_row, load


@dataclass(frozen=True)
class Agent:
    code: str
    name: str
    icon: str
    mission: str
    page: str
    plan: str


AGENTS: list[Agent] = [
    Agent("A01", "Agent Formation & Certification", "🎓", "Modules LCB-FT, quiz adaptatifs, certificats PDF vérifiables et registre de formation.", "views/formation.py", "free"),
    Agent("A02", "Agent Remédiation KYC", "🧩", "Diagnostic du stock clients, priorisation AMLR art. 26, plan de remédiation et courriers.", "views/kyc_remediation.py", "pro"),
    Agent("A03", "Agent Cartographie des risques", "🗺️", "Cartographies Excel par secteur et typologie d'entreprise, formules vivantes, plan d'action.", "views/cartographie.py", "pro"),
    Agent("A04", "Agent Examen renforcé", "🔎", "Trames d'examen renforcé (L.561-10-2) par type de client, typologies Tracfin intégrées.", "views/edd.py", "pro"),
    Agent("A05", "Agent Recueil KYC", "🪪", "Fiches de recueil KYC et listes de pièces par typologie (PP, PM, trust, association, PPE…).", "views/kyc_collect.py", "pro"),
    Agent("A06", "Agent Sanctions & Embargos", "🛑", "Pays sous sanctions, listes GAFI/UE, mise à jour des listes officielles et filtrage de noms.", "views/sanctions.py", "free"),
    Agent("A07", "Agent PPE", "🏛️", "Surveillance des PPE par pays, fonctions publiques importantes, revues et alertes d'échéance.", "views/pep.py", "pro"),
    Agent("A08", "Agent Presse négative", "📰", "Recherche d'informations négatives (corruption, fraude, sanctions) avec scoring auto-apprenant.", "views/adverse.py", "pro"),
    Agent("A09", "Agent Surveillance transactionnelle", "📈", "Scénarios experts + Isolation Forest, priorisation des alertes, apprentissage par retour analyste.", "views/monitoring.py", "pro"),
    Agent("A10", "Agent Fraude sectorielle", "🛡️", "Scénarios de fraude par secteur, simulateur de scoring et contrôles recommandés.", "views/fraud.py", "pro"),
    Agent("A11", "Agent Veille & Jurisprudence", "⚖️", "AMLR, AMLA, AMLD6, MiCA, TFR, décisions ACPR et sanctions internationales — calendrier et impacts.", "views/regwatch.py", "free"),
    Agent("A12", "Agent Mise en conformité", "✅", "Diagnostic de maturité par secteur (banque, fintech, assurance, jeux, immobilier, MTO, crypto).", "views/conformite.py", "pro"),
    Agent("A15", "Agent Contrôle & plan de conformité", "🧭", "Dispositif de contrôle (3 lignes de maîtrise) et plan de mise en conformité étape par étape par secteur — PDF et JPEG.", "views/controle.py", "pro"),
    Agent("A13", "Agent Kit documentaire", "🗂️", "Dossier ZIP complet par secteur : procédures, registres, trames Word et Excel prêtes à l'emploi.", "views/kit.py", "enterprise"),
    Agent("A14", "Agent Auto-amélioration (ML)", "🧠", "Scoring client ML, champion/challenger, dérive (PSI), réentraînement sur retours analystes.", "views/ml_lab.py", "enterprise"),
]
BY_CODE = {a.code: a for a in AGENTS}


def log(agent_code: str, action: str, statut: str = "Succès", details: str = ""):
    u = st.session_state.get("user") or {}
    append_row("agent_log.csv", {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "agent": agent_code, "action": action,
                                 "statut": statut, "utilisateur": u.get("email", "anonyme"), "details": details[:300]})


def stats() -> pd.DataFrame:
    lg = load("agent_log.csv")
    rows = []
    for a in AGENTS:
        sub = lg[lg["agent"] == a.code] if len(lg) else lg
        n = len(sub)
        ok = int((sub["statut"] == "Succès").sum()) if n else 0
        rows.append({"code": a.code, "agent": a.name, "exécutions": n, "taux de succès": (ok / n if n else None),
                     "dernière exécution": sub["date"].max() if n else "—"})
    return pd.DataFrame(rows)
