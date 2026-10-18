"""Parcours fonctionnels UI (Playwright) : inscription, cartographie, filtrage, quiz/certificat, kit ZIP, réentraînement ML."""
import sys
import time
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."


def idle(pg, t=120):
    time.sleep(1.2)
    t0 = time.time()
    while time.time() - t0 < t and pg.locator('[data-testid="stStatusWidget"]').count():
        time.sleep(0.4)
    time.sleep(0.8)


def check(pg, name):
    exc = pg.locator('[data-testid="stException"]')
    print(("EXCEPTION " + exc.first.inner_text()[:600]) if exc.count() else "ok", name)
    pg.screenshot(path=f"{OUT}/flow_{name}.png", full_page=True)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    pg = ctx.new_page()
    # inscription d'un nouvel utilisateur
    pg.goto(URL)
    idle(pg)
    pg.get_by_role("tab", name="Créer un compte").click()
    pg.get_by_label("Nom complet").fill("Testeur Démo")
    pg.get_by_label("Société").fill("Fintech Démo SAS")
    pg.get_by_label("E-mail professionnel").fill(f"test{int(time.time())}@demo.fr")
    pg.get_by_label("Mot de passe (8+").fill("Secret123")
    pg.get_by_text("J'accepte les conditions").click()
    pg.get_by_role("button", name="Créer mon compte").click()
    idle(pg)
    check(pg, "signup")
    sid = parse_qs(urlparse(pg.url).query).get("s", [""])[0]
    go = lambda path: (pg.goto(f"{URL}/{path}?s={sid}"), idle(pg))  # noqa: E731

    go("cartographie")
    pg.get_by_role("button", name="Générer la cartographie Excel").click()
    idle(pg)
    with pg.expect_download() as d:
        pg.get_by_role("button", name="Télécharger la cartographie").click()
    print("download:", d.value.suggested_filename)
    check(pg, "cartographie")

    go("sanctions")
    pg.get_by_role("tab", name="Filtrage & listes officielles").click()
    pg.get_by_label("Nom / raison sociale").fill("Golden Crescent Trading")
    pg.keyboard.press("Enter")
    idle(pg)
    print("screening hit:", pg.get_by_text("correspondance(s) potentielle(s)").count() > 0)
    check(pg, "sanctions_screening")

    go("formation")
    for r in pg.locator('[data-testid="stRadio"]').all():
        r.locator("label").first.click()
    pg.get_by_role("button", name="Valider mes réponses").click()
    idle(pg)
    check(pg, "quiz")

    go("monitoring")
    pg.get_by_role("button", name="Vrai positif").click()
    idle(pg)
    check(pg, "monitoring_feedback")

    go("agents_hub")
    pg.get_by_role("button", name="Lancer la mission").click()
    idle(pg, 180)
    print("mission zip:", pg.get_by_text("Télécharger le pack").count() > 0)
    check(pg, "mission")
    b.close()
