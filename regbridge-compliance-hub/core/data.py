"""Accès centralisé aux référentiels CSV (mis en cache par Streamlit)."""
from __future__ import annotations

import csv
from datetime import datetime

import pandas as pd
import streamlit as st

from core.paths import DATA

SECTOR_LABELS = {
    "BANQUE": "Banque", "FINTECH": "Fintech de paiement", "ASSURANCE": "Assurance",
    "JEUX": "Jeux & hasard", "IMMOBILIER": "Immobilier", "TRANSFERT": "Transfert d'argent",
    "CRYPTO": "Crypto-actifs", "CHANGE": "Change manuel", "ENTREPRISE": "Entreprise / Corporate",
}
RISK_ORDER = ["Faible", "Modéré", "Élevé", "Très élevé"]
RISK_COLORS = {"Faible": "#067647", "Modéré": "#CA8A04", "Élevé": "#EA580C", "Très élevé": "#B42318"}


@st.cache_data(ttl=600, show_spinner=False)
def load(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def save(name: str, df: pd.DataFrame):
    df.to_csv(DATA / name, index=False)
    load.clear()


def append_row(name: str, row: dict):
    path = DATA / name
    exists = path.exists() and path.stat().st_size > 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)
    load.clear()


def countries() -> pd.DataFrame:
    return load("countries.csv")


def country_options() -> dict:
    c = countries()
    return dict(zip(c["iso3"], c["pays"]))


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def risk_pill(level: str) -> str:
    cls = {"Faible": "green", "Standard": "teal", "Modéré": "amber", "Élevé": "red", "Très élevé": "red"}.get(str(level), "grey")
    return f'<span class="rb-pill {cls}">{level}</span>'


def security_index(fatf, ue, sanc, cpi, conflict, secrecy) -> float:
    """Indice de sécurité financière 0-100 (100 = juridiction la plus sûre)."""
    s = 100.0
    s -= {"noire": 35, "grise": 16}.get(str(fatf), 0)
    s -= 10 * int(ue)
    s -= 9 * int(sanc)
    cpi = int(cpi) if str(cpi).strip() not in ("", "nan") else 0
    s -= (100 - (cpi if cpi > 0 else 55)) * 0.40
    s -= 10 * int(conflict)
    s -= 6 * int(secrecy)
    return round(max(0.0, min(100.0, s)), 1)


def risk_level(idx: float) -> str:
    if idx >= 80:
        return "Faible"
    if idx >= 62:
        return "Modéré"
    if idx >= 42:
        return "Élevé"
    return "Très élevé"


def recompute_countries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["indice_securite_financiere"] = [
        security_index(r.gafi_statut, r.ue_pays_tiers_haut_risque, r.niveau_sanctions, r.ipc_indicatif, r.zone_conflit, r.opacite_financiere)
        for r in df.itertuples()
    ]
    df["niveau_risque_pays"] = df["indice_securite_financiere"].apply(risk_level)
    return df
