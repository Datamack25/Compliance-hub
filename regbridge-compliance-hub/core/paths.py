from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "cache"
MODELS = ROOT / "models"
ASSETS = ROOT / "assets"
for p in (DATA, CACHE, MODELS):
    p.mkdir(parents=True, exist_ok=True)

APP_NAME = "RegBridge Compliance Hub"
APP_TAGLINE = "Architecture complète de conformité LCB-FT, sanctions, embargos & fraude"

APP_VERSION = "1.1.0"
APP_AUTHOR = "Mackenson CINEUS"
APP_RELEASE = "Octobre 2026"
