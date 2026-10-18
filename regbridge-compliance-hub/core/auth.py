"""Comptes utilisateurs, offres payantes, codes d'activation et certificats.

Stockage (v1.2) — registres CSV dans data/ :
- users.csv          : comptes (identifiant unique RB-XXXX-XXXX, e-mail, mot de passe et clé de récupération hachés bcrypt…)
- licence_codes.csv  : codes d'activation émis / utilisés
- certificates.csv   : certificats de formation délivrés
Les sessions (jetons de reconnexion) restent en SQLite (data/app.db), car elles sont temporaires.

Persistance sur Streamlit Community Cloud : le disque de l'application est effacé à chaque redémarrage.
Pour conserver les comptes, renseigner dans les secrets un dépôt GitHub PRIVÉ de sauvegarde :
    GITHUB_TOKEN = "github_pat_..."         (droits « Contents : read & write » sur ce dépôt uniquement)
    GITHUB_DATA_REPO = "votre-compte/regbridge-data"
Les registres CSV y sont alors restaurés au démarrage et sauvegardés après chaque modification.

Offres :
- free        « Découverte »   : tableau de bord, pays & sanctions (consultation), formation (sans certificat)
- pro         « Professionnel » : tous les agents et générateurs
- enterprise  « Entreprise »   : Pro + kit ZIP multi-secteurs, laboratoire ML, multi-utilisateurs
"""
from __future__ import annotations

import base64
import os
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

import bcrypt
import pandas as pd
import requests
import streamlit as st

from core.paths import DATA

DB = DATA / "app.db"
USERS_CSV = DATA / "users.csv"
CODES_CSV = DATA / "licence_codes.csv"
CERTS_CSV = DATA / "certificates.csv"
USER_COLS = ["user_id", "email", "name", "company", "sector", "pwd_hash", "recovery_hash", "plan", "plan_expiry", "role",
             "created", "last_login"]
CODE_COLS = ["code", "plan", "days", "created", "used_by", "used_at"]
CERT_COLS = ["cert_id", "email", "name", "module", "score", "issued"]
PLANS = {
    "free": {"label": "Découverte", "rank": 0, "price": "0 €"},
    "pro": {"label": "Professionnel", "rank": 1, "price": "49 € / mois"},
    "enterprise": {"label": "Entreprise", "rank": 2, "price": "199 € / mois"},
}
TRIAL_DAYS = 7
_LOCK = threading.Lock()
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O/1/I pour éviter les confusions


# =============================================================================== utilitaires
def _secret(key: str, default=None):
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


def _hash(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def _check(pwd: str, h: str) -> bool:
    try:
        return bool(h) and bcrypt.checkpw(pwd.encode(), str(h).encode())
    except Exception:
        return False


def _rand(n: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def new_user_id() -> str:
    return f"RB-{_rand(4)}-{_rand(4)}"


def new_recovery_key() -> str:
    return f"{_rand(4)}-{_rand(4)}-{_rand(4)}-{_rand(4)}"


def _norm_key(k: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(k).upper())


def valid_password(pwd: str) -> str | None:
    if len(pwd) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if not re.search(r"[A-Z]", pwd) or not re.search(r"[0-9]", pwd):
        return "Le mot de passe doit contenir au moins une majuscule et un chiffre."
    return None


# =============================================================================== sauvegarde GitHub (optionnelle)
def _gh():
    tok, repo = _secret("GITHUB_TOKEN", ""), _secret("GITHUB_DATA_REPO", "")
    return (tok, repo) if tok and repo else (None, None)


def backup_enabled() -> bool:
    return _gh()[0] is not None


def _gh_url(repo, name):
    return f"https://api.github.com/repos/{repo}/contents/regbridge/{name}"


def _gh_pull(name: str, path) -> bool:
    tok, repo = _gh()
    if not tok:
        return False
    try:
        r = requests.get(_gh_url(repo, name), headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}, timeout=10)
        if r.ok:
            path.write_bytes(base64.b64decode(r.json()["content"]))
            return True
    except Exception:
        pass
    return False


def _gh_push(name: str, path):
    tok, repo = _gh()
    if not tok:
        return
    def run():
        try:
            h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
            cur = requests.get(_gh_url(repo, name), headers=h, timeout=10)
            body = {"message": f"Sauvegarde {name} — {datetime.now():%Y-%m-%d %H:%M}",
                    "content": base64.b64encode(path.read_bytes()).decode()}
            if cur.ok:
                body["sha"] = cur.json()["sha"]
            requests.put(_gh_url(repo, name), headers=h, json=body, timeout=15)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


# =============================================================================== registres CSV
def _read(path, cols) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


def _write(path, df: pd.DataFrame):
    tmp = path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)
    _gh_push(path.name, path)


def users_df() -> pd.DataFrame:
    return _read(USERS_CSV, USER_COLS)


def _save_users(df):
    _write(USERS_CSV, df)


@contextmanager
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    """Crée les registres, restaure la sauvegarde GitHub et migre l'ancienne base SQLite si besoin."""
    if st.session_state.get("_auth_init"):
        return
    with _LOCK:
        for name, path in (("users.csv", USERS_CSV), ("licence_codes.csv", CODES_CSV), ("certificates.csv", CERTS_CSV)):
            if not path.exists():
                _gh_pull(name, path)
        with conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, email TEXT, expires TEXT)")
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            df = users_df()
            # migration v1.0/1.1 (SQLite) -> CSV
            if "users" in tables:
                for r in c.execute("SELECT * FROM users"):
                    if r["email"] not in set(df["email"]):
                        df.loc[len(df)] = [new_user_id(), r["email"], r["name"] or "", r["company"] or "", r["sector"] or "", r["pwd_hash"], "",
                                           r["plan"] or "free", r["plan_expiry"] or "", r["role"] or "user", r["created"] or "", r["last_login"] or ""]
            if "licence_codes" in tables and not CODES_CSV.exists():
                _write(CODES_CSV, pd.DataFrame([dict(r) for r in c.execute("SELECT * FROM licence_codes")], columns=CODE_COLS).fillna(""))
            if "certificates" in tables and not CERTS_CSV.exists():
                _write(CERTS_CSV, pd.DataFrame([dict(r) for r in c.execute("SELECT * FROM certificates")], columns=CERT_COLS).fillna(""))
        admin_email = str(_secret("ADMIN_EMAIL", "admin@regbridge.fr")).strip().lower()
        admin_pwd = _secret("ADMIN_PASSWORD", "Admin!2026")
        if admin_email not in set(df["email"]):
            df.loc[len(df)] = ["RB-ADMN-0001", admin_email, "Administrateur", "RegBridge Conseil", "BANQUE", _hash(admin_pwd), "",
                               "enterprise", "2099-12-31", "admin", datetime.now().isoformat(timespec="seconds"), ""]
        if not USERS_CSV.exists() or len(df) != len(users_df()):
            _save_users(df)
        for path, cols in ((CODES_CSV, CODE_COLS), (CERTS_CSV, CERT_COLS)):
            if not path.exists():
                _write(path, pd.DataFrame(columns=cols))
    st.session_state["_auth_init"] = True


# =============================================================================== comptes
def _find(df: pd.DataFrame, ident: str) -> int | None:
    ident = str(ident).strip()
    m = df.index[(df["email"] == ident.lower()) | (df["user_id"].str.upper() == ident.upper())]
    return int(m[0]) if len(m) else None


def register(email, name, company, sector, pwd) -> tuple[bool, str, dict | None]:
    """Crée le compte. Retourne (ok, message, {user_id, recovery_key}) — la clé n'est affichée qu'une fois."""
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Adresse e-mail invalide.", None
    err = valid_password(pwd)
    if err:
        return False, err, None
    with _LOCK:
        df = users_df()
        if email in set(df["email"]):
            return False, "Un compte existe déjà avec cette adresse. Utilisez « Mot de passe oublié » si besoin.", None
        uid = new_user_id()
        while uid in set(df["user_id"]):
            uid = new_user_id()
        key = new_recovery_key()
        expiry = (datetime.now() + timedelta(days=TRIAL_DAYS)).date().isoformat()
        df.loc[len(df)] = [uid, email, name.strip(), company.strip(), sector, _hash(pwd), _hash(_norm_key(key)), "pro", expiry, "user",
                           datetime.now().isoformat(timespec="seconds"), ""]
        _save_users(df)
    return True, f"Compte créé — essai Professionnel offert jusqu'au {expiry}.", {"user_id": uid, "recovery_key": key}


def login(ident, pwd) -> dict | None:
    """Connexion par e-mail OU identifiant unique (RB-XXXX-XXXX)."""
    with _LOCK:
        df = users_df()
        i = _find(df, ident)
        if i is None or not _check(pwd, df.at[i, "pwd_hash"]):
            return None
        df.at[i, "last_login"] = datetime.now().isoformat(timespec="seconds")
        _save_users(df)
        return df.loc[i].to_dict()


def refresh(email) -> dict | None:
    df = users_df()
    i = _find(df, email)
    return df.loc[i].to_dict() if i is not None else None


def reset_password(email: str, user_id: str, recovery_key: str, new_pwd: str) -> tuple[bool, str, str | None]:
    """Réinitialisation par e-mail + identifiant unique + clé de récupération. Une nouvelle clé est générée."""
    err = valid_password(new_pwd)
    if err:
        return False, err, None
    with _LOCK:
        df = users_df()
        i = _find(df, email)
        if i is None or df.at[i, "user_id"].upper() != user_id.strip().upper() or not _check(_norm_key(recovery_key), df.at[i, "recovery_hash"]):
            return False, "Informations de récupération incorrectes (e-mail, identifiant ou clé).", None
        key = new_recovery_key()
        df.at[i, "pwd_hash"], df.at[i, "recovery_hash"] = _hash(new_pwd), _hash(_norm_key(key))
        _save_users(df)
    return True, "Mot de passe réinitialisé. Une nouvelle clé de récupération a été générée.", key


def regenerate_recovery_key(email: str) -> str:
    with _LOCK:
        df = users_df()
        i = _find(df, email)
        key = new_recovery_key()
        df.at[i, "recovery_hash"] = _hash(_norm_key(key))
        _save_users(df)
    return key


def admin_reset_password(email: str) -> tuple[str, str]:
    """Réinitialisation par l'administrateur : mot de passe temporaire + nouvelle clé de récupération."""
    tmp = f"Rb{_rand(6)}9"
    with _LOCK:
        df = users_df()
        i = _find(df, email)
        key = new_recovery_key()
        df.at[i, "pwd_hash"], df.at[i, "recovery_hash"] = _hash(tmp), _hash(_norm_key(key))
        _save_users(df)
    return tmp, key


def change_password(email, old, new) -> tuple[bool, str]:
    err = valid_password(new)
    if err:
        return False, err
    with _LOCK:
        df = users_df()
        i = _find(df, email)
        if i is None or not _check(old, df.at[i, "pwd_hash"]):
            return False, "Mot de passe actuel incorrect."
        df.at[i, "pwd_hash"] = _hash(new)
        _save_users(df)
    return True, "Mot de passe modifié."


def effective_plan(user: dict | None) -> str:
    if not user:
        return "free"
    exp = user.get("plan_expiry")
    if user.get("plan") != "free" and exp and exp < datetime.now().date().isoformat():
        return "free"
    return user.get("plan") or "free"


def has_access(user: dict | None, needed: str) -> bool:
    return PLANS[effective_plan(user)]["rank"] >= PLANS[needed]["rank"]


def list_users():
    df = users_df().drop(columns=["pwd_hash", "recovery_hash"])
    return df.to_dict("records")


def set_plan(email, plan, expiry):
    with _LOCK:
        df = users_df()
        i = _find(df, email)
        df.at[i, "plan"], df.at[i, "plan_expiry"] = plan, expiry
        _save_users(df)


def delete_user(email):
    with _LOCK:
        df = users_df()
        df = df[~((df["email"] == email) & (df["role"] != "admin"))]
        _save_users(df)


# =============================================================================== codes d'activation
def create_code(plan: str, days: int) -> str:
    code = f"RB-{plan[:3].upper()}-" + secrets.token_hex(4).upper()
    with _LOCK:
        df = _read(CODES_CSV, CODE_COLS)
        df.loc[len(df)] = [code, plan, str(days), datetime.now().isoformat(timespec="seconds"), "", ""]
        _write(CODES_CSV, df)
    return code


def redeem(email: str, code: str) -> tuple[bool, str]:
    code = code.strip().upper()
    with _LOCK:
        cd = _read(CODES_CSV, CODE_COLS)
        m = cd.index[cd["code"] == code]
        if not len(m):
            return False, "Code inconnu."
        j = m[0]
        if cd.at[j, "used_by"]:
            return False, "Code déjà utilisé."
        df = users_df()
        i = _find(df, email)
        plan, days = cd.at[j, "plan"], int(float(cd.at[j, "days"]))
        base = datetime.now().date()
        if df.at[i, "plan"] == plan and df.at[i, "plan_expiry"] and df.at[i, "plan_expiry"] > base.isoformat():
            base = datetime.fromisoformat(df.at[i, "plan_expiry"]).date()
        exp = (base + timedelta(days=days)).isoformat()
        df.at[i, "plan"], df.at[i, "plan_expiry"] = plan, exp
        cd.at[j, "used_by"], cd.at[j, "used_at"] = email, datetime.now().isoformat(timespec="seconds")
        _save_users(df)
        _write(CODES_CSV, cd)
    return True, f"Offre {PLANS[plan]['label']} activée jusqu'au {exp}."


def list_codes():
    return _read(CODES_CSV, CODE_COLS).iloc[::-1].to_dict("records")


# =============================================================================== certificats
def save_certificate(cert_id, email, name, module, score):
    with _LOCK:
        df = _read(CERTS_CSV, CERT_COLS)
        df = df[df["cert_id"] != cert_id]
        df.loc[len(df)] = [cert_id, email, name, module, str(score), datetime.now().isoformat(timespec="seconds")]
        _write(CERTS_CSV, df)


def verify_certificate(cert_id) -> dict | None:
    df = _read(CERTS_CSV, CERT_COLS)
    m = df[df["cert_id"] == cert_id.strip().upper()]
    if not len(m):
        return None
    r = m.iloc[0].to_dict()
    r["score"] = float(r["score"] or 0)
    return r


def certificates_of(email) -> list[dict]:
    df = _read(CERTS_CSV, CERT_COLS)
    return df[df["email"] == email].drop(columns=["email"]).iloc[::-1].to_dict("records")


# =============================================================================== sessions
def payment_links() -> dict:
    return {"pro": _secret("STRIPE_LINK_PRO", ""), "enterprise": _secret("STRIPE_LINK_ENTERPRISE", "")}


def create_session(email: str, days: int = 7) -> str:
    tok = secrets.token_urlsafe(24)
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE expires < ?", (datetime.now().isoformat(),))
        c.execute("INSERT INTO sessions VALUES(?,?,?)", (tok, email, (datetime.now() + timedelta(days=days)).isoformat()))
    return tok


def user_from_session(tok: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT email FROM sessions WHERE token=? AND expires > ?", (tok, datetime.now().isoformat())).fetchone()
    return refresh(r["email"]) if r else None


def end_session(tok: str | None):
    if tok:
        with conn() as c:
            c.execute("DELETE FROM sessions WHERE token=?", (tok,))


def start(user: dict):
    st.session_state["user"] = user
    st.session_state["sid"] = create_session(user["email"])


def current_user() -> dict | None:
    return st.session_state.get("user")


def guard(needed: str = "free") -> bool:
    """À appeler en tête de page. Retourne True si l'accès est autorisé, sinon affiche le verrou."""
    from core.ui import locked
    u = current_user()
    if u and has_access(u, needed):
        return True
    locked(PLANS[needed]["label"])
    return False
