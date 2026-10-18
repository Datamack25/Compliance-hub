"""Test de fumée UI : connexion admin puis visite de chaque page, capture d'écran et détection d'exceptions.

Usage : python tests/smoke_ui.py http://localhost:8501 <dossier_captures>
"""
import sys
import time

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
PAGES = ["", "agents_hub", "formation", "kyc_remediation", "cartographie", "edd", "kyc_collect", "sanctions", "pep", "adverse",
         "monitoring", "fraud", "regwatch", "conformite", "controle", "kit", "ml_lab", "account", "admin"]


def wait_idle(page, t=40):
    t0 = time.time()
    time.sleep(1.5)
    while time.time() - t0 < t:
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        time.sleep(0.5)
    time.sleep(1.5)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    pg.goto(URL)
    wait_idle(pg)
    pg.screenshot(path=f"{OUT}/00_landing.png", full_page=True)
    pg.get_by_label("E-mail").first.fill("admin@regbridge.fr")
    pg.get_by_label("Mot de passe").first.fill("Admin!2026")
    pg.get_by_role("button", name="Connexion").click()
    wait_idle(pg)
    from urllib.parse import parse_qs, urlparse
    sid = parse_qs(urlparse(pg.url).query).get("s", [""])[0]
    print("session:", bool(sid))
    errors = {}
    for name in PAGES:
        pg.goto(f"{URL}/{name}?s={sid}")
        wait_idle(pg)
        exc = pg.locator('[data-testid="stException"]')
        if exc.count():
            errors[name or "dashboard"] = exc.first.inner_text()[:800]
        pg.screenshot(path=f"{OUT}/{name or 'dashboard'}.png", full_page=True)
        print("ok" if not exc.count() else "EXCEPTION", name or "dashboard")
    b.close()
for k, v in errors.items():
    print("=" * 20, k, "\n", v)
