"""Moteur de Machine Learning et d'auto-amélioration.

1. Scoring client (GradientBoosting) — entraîné sur data/training_clients.csv + retours analystes
   (data/feedback_clients.csv, pondérés x3). Stratégie champion/challenger : un nouveau modèle n'est
   promu que si son AUC sur l'échantillon de validation commun n'est pas dégradée (> -0,005).
2. Surveillance transactionnelle — règles expertes (structuration, comptes de passage, pays à risque,
   embargo, vélocité…) + IsolationForest. Les poids des règles s'auto-ajustent selon la précision
   observée sur les retours analystes (modèle Bêta-Binomial).
3. Dérive (PSI) entre la population d'entraînement et les populations récemment scorées.
"""
from __future__ import annotations

import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from core.paths import DATA, MODELS

CAT = ["type_client", "secteur"]
NUM = ["risque_pays", "ppe", "presse_negative", "part_especes", "distance", "niveaux_detention",
       "nb_tx_mois", "montant_moyen", "part_flux_pays_risque", "anciennete_mois"]
FEATURES = CAT + NUM
LABELS_FR = {
    "type_client": "Type de client", "secteur": "Secteur", "risque_pays": "Risque pays", "ppe": "Statut PPE",
    "presse_negative": "Presse négative", "part_especes": "Part d'espèces", "distance": "Relation à distance",
    "niveaux_detention": "Niveaux de détention", "nb_tx_mois": "Transactions / mois", "montant_moyen": "Montant moyen",
    "part_flux_pays_risque": "Flux vers pays à risque", "anciennete_mois": "Ancienneté (mois)",
}
REGISTRY = MODELS / "registry.json"
FEEDBACK_CLIENTS = DATA / "feedback_clients.csv"
RULE_WEIGHTS = DATA / "rule_weights.json"


# ---------------------------------------------------------------- registre
def _registry() -> list[dict]:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return []


def _save_registry(reg):
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False))


def registry() -> pd.DataFrame:
    return pd.DataFrame(_registry())


def champion() -> dict | None:
    for r in reversed(_registry()):
        if r["statut"] == "champion":
            return r
    return None


# ---------------------------------------------------------------- données
def _base() -> pd.DataFrame:
    return pd.read_csv(DATA / "training_clients.csv")


def _feedback() -> pd.DataFrame:
    if FEEDBACK_CLIENTS.exists():
        return pd.read_csv(FEEDBACK_CLIENTS)
    return pd.DataFrame(columns=FEATURES + ["suspect", "date"])


def _pipeline():
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)], remainder="passthrough")
    clf = GradientBoostingClassifier(n_estimators=220, max_depth=3, learning_rate=0.06, subsample=0.9, random_state=11)
    return Pipeline([("pre", pre), ("clf", clf)])


def train(reason: str = "Entraînement initial") -> dict:
    base = _base()
    tr, te = train_test_split(base, test_size=0.25, random_state=3, stratify=base["suspect"])
    fb = _feedback()
    if len(fb):
        fb_tr, fb_te = (train_test_split(fb, test_size=0.3, random_state=3) if len(fb) >= 10 else (fb, fb.iloc[0:0]))
        tr = pd.concat([tr, fb_tr], ignore_index=True)
        te = pd.concat([te, fb_te], ignore_index=True)
    w = np.where(tr.index >= len(base) * 0.75, 3.0, 1.0) if len(fb) else np.ones(len(tr))
    pipe = _pipeline()
    pipe.fit(tr[FEATURES], tr["suspect"].astype(int), clf__sample_weight=w)
    proba = pipe.predict_proba(te[FEATURES])[:, 1]
    pred = (proba >= 0.5).astype(int)
    y = te["suspect"].astype(int)
    metrics = {
        "auc": round(float(roc_auc_score(y, proba)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "rappel": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
    }
    reg = _registry()
    version = f"v{len(reg) + 1}"
    champ = champion()
    promote = champ is None
    if champ is not None:
        # réévaluer le champion sur le même échantillon
        try:
            old = joblib.load(MODELS / f"client_model_{champ['version']}.joblib")
            old_auc = float(roc_auc_score(y, old.predict_proba(te[FEATURES])[:, 1]))
        except Exception:
            old_auc = 0.0
        metrics["auc_champion_meme_jeu"] = round(old_auc, 4)
        promote = metrics["auc"] >= old_auc - 0.005
    joblib.dump(pipe, MODELS / f"client_model_{version}.joblib")
    if promote:
        for r in reg:
            if r["statut"] == "champion":
                r["statut"] = "archivé"
    entry = {"version": version, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "motif": reason,
             "n_entrainement": int(len(tr)), "n_retours_analystes": int(len(fb)), **metrics,
             "statut": "champion" if promote else "rejeté (challenger moins performant)"}
    reg.append(entry)
    _save_registry(reg)
    return entry


_MODEL_CACHE: dict = {}


def model():
    ch = champion()
    if ch is None:
        ch = train()
    key = ch["version"]
    if key not in _MODEL_CACHE:
        _MODEL_CACHE.clear()
        _MODEL_CACHE[key] = joblib.load(MODELS / f"client_model_{key}.joblib")
    return _MODEL_CACHE[key]


def score_clients(df: pd.DataFrame) -> np.ndarray:
    return model().predict_proba(df[FEATURES])[:, 1]


def explain(row: dict) -> pd.DataFrame:
    """Explication locale par perturbation : effet de chaque variable vs une valeur de référence."""
    m = model()
    base = _base()
    ref = {c: base[c].mode()[0] for c in CAT}
    ref.update({c: float(base[c].median()) for c in NUM})
    x = pd.DataFrame([row])[FEATURES]
    p0 = float(m.predict_proba(x)[:, 1][0])
    out = []
    for f in FEATURES:
        x2 = x.copy()
        x2[f] = ref[f]
        out.append({"variable": LABELS_FR[f], "valeur": row[f], "contribution": round(p0 - float(m.predict_proba(x2)[:, 1][0]), 4)})
    return pd.DataFrame(out).sort_values("contribution", ascending=False)


def add_client_feedback(row: dict, label: int):
    r = {k: row[k] for k in FEATURES}
    r["suspect"] = int(label)
    r["date"] = datetime.now().isoformat(timespec="seconds")
    df = pd.concat([_feedback(), pd.DataFrame([r])], ignore_index=True)
    df.to_csv(FEEDBACK_CLIENTS, index=False)
    return len(df)


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    expected, actual = expected.astype(float), actual.astype(float)
    qs = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(qs) < 3:
        return 0.0
    e = np.histogram(expected, qs)[0] / len(expected) + 1e-6
    a = np.histogram(np.clip(actual, qs[0], qs[-1]), qs)[0] / max(len(actual), 1) + 1e-6
    return float(np.sum((a - e) * np.log(a / e)))


def drift_report(recent: pd.DataFrame) -> pd.DataFrame:
    base = _base()
    rows = []
    for f in NUM:
        if f in recent and len(recent) >= 5:
            v = psi(base[f], recent[f])
            rows.append({"variable": LABELS_FR[f], "PSI": round(v, 3),
                         "diagnostic": "Stable" if v < 0.1 else ("Dérive modérée" if v < 0.25 else "Dérive forte → réentraîner")})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- surveillance transactionnelle
RULES = {
    "R1": "Structuration : ≥ 3 dépôts d'espèces entre 8 000 et 9 999 € sur la période",
    "R2": "Compte de passage : débits ≈ crédits (ratio 0,8–1,2) et volume > 15 000 €",
    "R3": "Flux avec pays à risque élevé / très élevé (GAFI, UE, IPC)",
    "R4": "Espèces cumulées > 10 000 € sur la période",
    "R5": "Vélocité anormale (nombre d'opérations > 95e percentile)",
    "R6": "Opération avec un pays sous embargo global (Iran, Corée du Nord, Cuba, Russie)",
    "R7": "Montant unitaire > 30 000 € vers l'international",
}


def rule_weights() -> dict:
    if RULE_WEIGHTS.exists():
        return json.loads(RULE_WEIGHTS.read_text())
    w = {r: {"alpha": 2.0, "beta": 2.0} for r in RULES}
    w["R6"] = {"alpha": 8.0, "beta": 1.0}
    w["R1"] = {"alpha": 5.0, "beta": 2.0}
    return w


def rule_weight_value(w: dict, r: str) -> float:
    a, b = w[r]["alpha"], w[r]["beta"]
    return round(a / (a + b), 3)


def update_rule_weights(rules_hit: list[str], true_positive: bool):
    w = rule_weights()
    for r in rules_hit:
        if r in w:
            w[r]["alpha" if true_positive else "beta"] += 1.0
    RULE_WEIGHTS.write_text(json.dumps(w, indent=2))
    return w


def monitor(tx: pd.DataFrame, countries: pd.DataFrame) -> pd.DataFrame:
    tx = tx.copy()
    tx["montant"] = pd.to_numeric(tx["montant"], errors="coerce").fillna(0)
    risk = countries.set_index("iso3")
    hi = set(risk.index[risk["niveau_risque_pays"].isin(["Élevé", "Très élevé"])])
    embargo = set(risk.index[risk["niveau_sanctions"] >= 3])
    g = tx.groupby("client_id")
    feats = pd.DataFrame({
        "nb_operations": g.size(),
        "volume_total": g["montant"].sum(),
        "credits": g.apply(lambda d: d.loc[d["sens"] == "Crédit", "montant"].sum(), include_groups=False),
        "debits": g.apply(lambda d: d.loc[d["sens"] == "Débit", "montant"].sum(), include_groups=False),
        "especes": g.apply(lambda d: d.loc[d["type"].str.contains("espèces", case=False), "montant"].sum(), include_groups=False),
        "nb_structuration": g.apply(lambda d: int(((d["type"] == "Dépôt espèces") & d["montant"].between(8000, 9999)).sum()), include_groups=False),
        "flux_pays_risque": g.apply(lambda d: d.loc[d["pays_contrepartie"].isin(hi), "montant"].sum(), include_groups=False),
        "nb_embargo": g.apply(lambda d: int(d["pays_contrepartie"].isin(embargo).sum()), include_groups=False),
        "max_international": g.apply(lambda d: d.loc[d["type"].str.contains("international", case=False), "montant"].max() if (d["type"].str.contains("international", case=False)).any() else 0, include_groups=False),
    }).fillna(0)
    feats["ratio_debit_credit"] = np.where(feats["credits"] > 0, feats["debits"] / feats["credits"], 0)
    p95 = feats["nb_operations"].quantile(0.95)
    hits = {
        "R1": feats["nb_structuration"] >= 3,
        "R2": feats["ratio_debit_credit"].between(0.8, 1.2) & (feats["volume_total"] > 15000) & (feats["credits"] > 7500),
        "R3": feats["flux_pays_risque"] > 5000,
        "R4": feats["especes"] > 10000,
        "R5": feats["nb_operations"] > p95,
        "R6": feats["nb_embargo"] > 0,
        "R7": feats["max_international"] > 30000,
    }
    w = rule_weights()
    iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=5)
    X = np.log1p(feats[["nb_operations", "volume_total", "especes", "flux_pays_risque", "max_international"]].clip(lower=0))
    iso.fit(X)
    anomaly = -iso.score_samples(X)
    anomaly = (anomaly - anomaly.min()) / (anomaly.max() - anomaly.min() + 1e-9)
    feats["score_anomalie"] = anomaly.round(3)
    feats["regles"] = [", ".join(r for r in RULES if hits[r].loc[c]) for c in feats.index]
    feats["score_regles"] = [sum(rule_weight_value(w, r) for r in RULES if hits[r].loc[c]) for c in feats.index]
    feats["score_alerte"] = (100 * (1 - np.exp(-(feats["score_regles"] * 1.1 + feats["score_anomalie"] * 0.9)))).round(1)
    feats["priorite"] = pd.cut(feats["score_alerte"], [-1, 40, 65, 85, 101], labels=["Faible", "Moyenne", "Haute", "Critique"])
    feats.loc[feats["nb_embargo"] > 0, "priorite"] = "Critique"
    return feats.reset_index().sort_values("score_alerte", ascending=False)


# ---------------------------------------------------------------- presse négative : poids auto-ajustés
def update_keyword_weights(keywords: list[str], relevant: bool):
    p = DATA / "adverse_keywords.csv"
    kw = pd.read_csv(p)
    for k in keywords:
        m = kw["mot_cle"].str.lower() == k.lower()
        kw.loc[m, "poids"] = (kw.loc[m, "poids"] * (1.1 if relevant else 0.9)).clip(0.5, 5).round(2)
    kw.to_csv(p, index=False)
    return kw
