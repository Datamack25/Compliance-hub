"""Filtrage de noms contre les listes de sanctions (démo + listes officielles mises en cache)."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process

from core.paths import CACHE, DATA

CACHED_LISTS = {
    "ONU": CACHE / "un_list.csv",
    "OFAC": CACHE / "ofac_sdn.csv",
    "UE": CACHE / "eu_list.csv",
    "France (DG Trésor)": CACHE / "fr_gel.csv",
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9 ]", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def all_lists() -> pd.DataFrame:
    frames = []
    demo = pd.read_csv(DATA / "sanctions_entities_demo.csv")
    demo["source"] = "Démo (" + demo["liste"] + ")"
    frames.append(demo[["nom", "type", "pays", "programme", "source"]])
    for src, path in CACHED_LISTS.items():
        if path.exists():
            df = pd.read_csv(path, keep_default_na=False)
            df["source"] = src
            frames.append(df[["nom", "type", "pays", "programme", "source"]])
    out = pd.concat(frames, ignore_index=True)
    out["norm"] = out["nom"].map(normalize)
    return out


def list_status() -> pd.DataFrame:
    rows = []
    for src, path in CACHED_LISTS.items():
        if path.exists():
            n = sum(1 for _ in open(path, encoding="utf-8")) - 1
            rows.append({"liste": src, "entrées": n, "mise à jour": pd.Timestamp(path.stat().st_mtime, unit="s").strftime("%d/%m/%Y %H:%M")})
        else:
            rows.append({"liste": src, "entrées": 0, "mise à jour": "jamais (cliquer sur Mettre à jour)"})
    return pd.DataFrame(rows)


def screen(name: str, lists: pd.DataFrame, threshold: int = 85, limit: int = 15) -> pd.DataFrame:
    q = normalize(name)
    if not q:
        return pd.DataFrame()
    res = process.extract(q, lists["norm"], scorer=fuzz.token_set_ratio, limit=limit * 3, score_cutoff=threshold - 10)
    rows = []
    for _, score, idx in res:
        r = lists.iloc[idx]
        sort_score = fuzz.token_sort_ratio(q, r["norm"])
        final = round(0.6 * score + 0.4 * sort_score, 1)
        if final >= threshold:
            rows.append({"nom_liste": r["nom"], "type": r["type"], "pays": r["pays"], "programme": r["programme"],
                         "source": r["source"], "score": final})
    df = pd.DataFrame(rows)
    return df.sort_values("score", ascending=False).head(limit) if len(df) else df
