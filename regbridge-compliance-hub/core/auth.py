"""Comptes utilisateurs, offres payantes et codes d'activation (SQLite + bcrypt).

Offres :
- free        « Découverte »  : tableau de bord, pays & sanctions (consultation), formation (sans certificat)
- pro         « Professionnel » : tous les agents et générateurs
- enterprise  « Entreprise »  : Pro + kit ZIP multi-secteurs, laboratoire ML (auto-amélioration), multi-utilisateurs

Paiement : lien de paiement Stripe configurable dans .streamlit/secrets.toml (STRIPE_LINK_PRO /
STRIPE_LINK_ENTERPRISE). Après paiement, l'administrateur délivre un code d'activation (onglet Admin)
que l'utilisateur saisit dans « Mon compte ». Chaque nouveau compte bénéficie d'un essai Pro de 7 jours.
"""
from __future__ import annotations

import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from core.paths import DATA

DB = DATA / "app.db"
PLANS = {
    "free": {"label": "Découverte", "rank": 0, "price": "0 €"},
    "pro": {"label": "Professionnel", "rank": 1, "price": "49 € / mois"},
    "enterprise": {"label": "Entreprise", "rank": 2, "price": "199 € / mois"},
}
TRIAL_DAYS = 7


@contextmanager
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _secret(key: str, default=None):
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, name TEXT, company TEXT, sector TEXT,
            pwd_hash TEXT NOT NULL, plan TEXT DEFAULT 'free', plan_expiry TEXT, role TEXT DEFAULT 'user',
            created TEXT, last_login TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS licence_codes(
            code TEXT PRIMARY KEY, plan TEXT, days INTEGER, created TEXT, used_by TEXT, used_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, email TEXT, expires TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS certificates(
            cert_id TEXT PRIMARY KEY, email TEXT, name TEXT, module TEXT, score REAL, issued TEXT)""")
        admin_email = _secret("ADMIN_EMAIL", "admin@regbridge.fr")
        admin_pwd = _secret("ADMIN_PASSWORD", "Admin!2026")
        if not c.execute("SELECT 1 FROM users WHERE email=?", (admin_email,)).fetchone():
            c.execute("INSERT INTO users(email,name,company,sector,pwd_hash,plan,plan_expiry,role,created) VALUES(?,?,?,?,?,?,?,?,?)",
                      (admin_email, "Administrateur", "RegBridge Conseil", "BANQUE", _hash(admin_pwd), "enterprise",
                       "2099-12-31", "admin", datetime.now().isoformat()))


def _hash(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


def _check(pwd: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pwd.encode(), h.encode())
    except Exception:
        return False


def valid_password(pwd: str) -> str | None:
    if len(pwd) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if not re.search(r"[A-Z]", pwd) or not re.search(r"[0-9]", pwd):
        return "Le mot de passe doit contenir au moins une majuscule et un chiffre."
    return None


def register(email, name, company, sector, pwd) -> tuple[bool, str]:
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Adresse e-mail invalide."
    err = valid_password(pwd)
    if err:
        return False, err
    try:
        with conn() as c:
            expiry = (datetime.now() + timedelta(days=TRIAL_DAYS)).date().isoformat()
            c.execute("INSERT INTO users(email,name,company,sector,pwd_hash,plan,plan_expiry,role,created) VALUES(?,?,?,?,?,?,?,?,?)",
                      (email, name.strip(), company.strip(), sector, _hash(pwd), "pro", expiry, "user", datetime.now().isoformat()))
        return True, f"Compte créé — essai Professionnel offert jusqu'au {expiry}."
    except sqlite3.IntegrityError:
        return False, "Un compte existe déjà avec cette adresse."


def login(email, pwd) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if r and _check(pwd, r["pwd_hash"]):
            c.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now().isoformat(), r["id"]))
            return dict(r)
    return None


def refresh(email) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(r) if r else None


def effective_plan(user: dict | None) -> str:
    if not user:
        return "free"
    exp = user.get("plan_expiry")
    if user.get("plan") != "free" and exp and exp < datetime.now().date().isoformat():
        return "free"
    return user.get("plan", "free")


def has_access(user: dict | None, needed: str) -> bool:
    return PLANS[effective_plan(user)]["rank"] >= PLANS[needed]["rank"]


def change_password(email, old, new) -> tuple[bool, str]:
    u = refresh(email)
    if not u or not _check(old, u["pwd_hash"]):
        return False, "Mot de passe actuel incorrect."
    err = valid_password(new)
    if err:
        return False, err
    with conn() as c:
        c.execute("UPDATE users SET pwd_hash=? WHERE email=?", (_hash(new), email))
    return True, "Mot de passe modifié."


def create_code(plan: str, days: int) -> str:
    code = f"RB-{plan[:3].upper()}-" + secrets.token_hex(4).upper()
    with conn() as c:
        c.execute("INSERT INTO licence_codes(code,plan,days,created) VALUES(?,?,?,?)", (code, plan, days, datetime.now().isoformat()))
    return code


def redeem(email: str, code: str) -> tuple[bool, str]:
    code = code.strip().upper()
    with conn() as c:
        r = c.execute("SELECT * FROM licence_codes WHERE code=?", (code,)).fetchone()
        if not r:
            return False, "Code inconnu."
        if r["used_by"]:
            return False, "Code déjà utilisé."
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        base = datetime.now().date()
        if u["plan"] == r["plan"] and u["plan_expiry"] and u["plan_expiry"] > base.isoformat():
            base = datetime.fromisoformat(u["plan_expiry"]).date()
        exp = (base + timedelta(days=int(r["days"]))).isoformat()
        c.execute("UPDATE users SET plan=?, plan_expiry=? WHERE email=?", (r["plan"], exp, email))
        c.execute("UPDATE licence_codes SET used_by=?, used_at=? WHERE code=?", (email, datetime.now().isoformat(), code))
    return True, f"Offre {PLANS[r['plan']]['label']} activée jusqu'au {exp}."


def list_users():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT id,email,name,company,sector,plan,plan_expiry,role,created,last_login FROM users ORDER BY id")]


def list_codes():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM licence_codes ORDER BY created DESC")]


def set_plan(email, plan, expiry):
    with conn() as c:
        c.execute("UPDATE users SET plan=?, plan_expiry=? WHERE email=?", (plan, expiry, email))


def delete_user(email):
    with conn() as c:
        c.execute("DELETE FROM users WHERE email=? AND role!='admin'", (email,))


def save_certificate(cert_id, email, name, module, score):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO certificates VALUES(?,?,?,?,?,?)", (cert_id, email, name, module, score, datetime.now().isoformat()))


def verify_certificate(cert_id) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM certificates WHERE cert_id=?", (cert_id.strip().upper(),)).fetchone()
        return dict(r) if r else None


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
