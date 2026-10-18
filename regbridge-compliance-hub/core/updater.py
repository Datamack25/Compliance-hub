"""Mise à jour des listes officielles (sanctions, gel des avoirs, GAFI) et historisation de l'indice pays.

Chaque fonction renvoie (ok: bool, message: str). En cas d'absence de réseau, la plateforme continue de
fonctionner sur les référentiels CSV embarqués.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd
import requests

from core.data import load, recompute_countries, save
from core.paths import CACHE, DATA

UA = {"User-Agent": "Mozilla/5.0 (RegBridge Compliance Hub)"}
TIMEOUT = 60

URLS = {
    "un": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    "ofac": ["https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
             "https://www.treasury.gov/ofac/downloads/sdn.csv"],
    "eu": "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
    "fr": "https://gels-avoirs.dgtresor.gouv.fr/ApiPublic/api/v1/publication/derniere-publication-fichier-json",
    "fatf": "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html",
}


def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def update_un() -> tuple[bool, str]:
    try:
        root = ET.fromstring(_get(URLS["un"]).content)
        rows = []
        for ind in root.iter("INDIVIDUAL"):
            name = " ".join(filter(None, [(ind.findtext(t) or "").strip() for t in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")]))
            nat = ind.find("NATIONALITY")
            rows.append({"nom": name, "type": "Personne", "pays": (nat.findtext("VALUE") if nat is not None else "") or "",
                         "programme": ind.findtext("UN_LIST_TYPE") or ""})
            for al in ind.iter("INDIVIDUAL_ALIAS"):
                a = (al.findtext("ALIAS_NAME") or "").strip()
                if a:
                    rows.append({"nom": a, "type": "Personne (alias)", "pays": rows[-1]["pays"], "programme": rows[-1]["programme"]})
        for ent in root.iter("ENTITY"):
            rows.append({"nom": (ent.findtext("FIRST_NAME") or "").strip(), "type": "Entité", "pays": "",
                         "programme": ent.findtext("UN_LIST_TYPE") or ""})
        df = pd.DataFrame(rows)
        df = df[df["nom"].str.len() > 2]
        df.to_csv(CACHE / "un_list.csv", index=False)
        return True, f"Liste consolidée ONU : {len(df)} noms importés."
    except Exception as e:
        return False, f"ONU indisponible ({type(e).__name__})."


def update_ofac() -> tuple[bool, str]:
    for url in URLS["ofac"]:
        try:
            raw = _get(url).text
            df = pd.read_csv(io.StringIO(raw), header=None, dtype=str, on_bad_lines="skip")
            df = df.iloc[:, [1, 2, 3]]
            df.columns = ["nom", "type", "programme"]
            df["type"] = df["type"].replace({"-0- ": "Entité", "individual": "Personne"}).fillna("Entité")
            df["pays"] = ""
            df = df[df["nom"].notna()]
            df[["nom", "type", "pays", "programme"]].to_csv(CACHE / "ofac_sdn.csv", index=False)
            return True, f"Liste OFAC SDN : {len(df)} noms importés."
        except Exception:
            continue
    return False, "OFAC indisponible."


def update_eu() -> tuple[bool, str]:
    try:
        raw = _get(URLS["eu"]).content.decode("utf-8", "ignore")
        df = pd.read_csv(io.StringIO(raw), sep=";", dtype=str, on_bad_lines="skip")
        col = lambda *keys: next((c for c in df.columns if any(k.lower() in c.lower() for k in keys)), None)
        n, t, p, c = col("WholeName"), col("SubjectType"), col("Programme"), col("Citizenship_CountryDescription", "Citi_country")
        out = pd.DataFrame({"nom": df[n], "type": df[t] if t else "", "programme": df[p] if p else "", "pays": df[c] if c else ""})
        out = out[out["nom"].notna()].drop_duplicates("nom")
        out.to_csv(CACHE / "eu_list.csv", index=False)
        return True, f"Liste consolidée UE (FSF) : {len(out)} noms importés."
    except Exception as e:
        return False, f"UE indisponible ({type(e).__name__})."


def update_fr() -> tuple[bool, str]:
    try:
        js = _get(URLS["fr"]).json()
        pubs = js.get("Publications", js).get("PublicationDetail", [])
        rows = []
        for p in pubs:
            prenom, fondement = "", ""
            for d in p.get("RegistreDetail", []):
                if d.get("TypeChamp") == "PRENOM":
                    prenom = " ".join(v.get("Prenom", "") for v in d.get("Valeur", []))
                if d.get("TypeChamp") == "FONDEMENT_JURIDIQUE":
                    fondement = "; ".join(v.get("FondementJuridiqueLabel", "") for v in d.get("Valeur", []))[:120]
            rows.append({"nom": f"{prenom} {p.get('Nom', '')}".strip(), "type": p.get("Nature", ""), "pays": "",
                         "programme": fondement})
        df = pd.DataFrame(rows)
        df.to_csv(CACHE / "fr_gel.csv", index=False)
        return True, f"Registre national des gels (DG Trésor) : {len(df)} noms importés."
    except Exception as e:
        return False, f"DG Trésor indisponible ({type(e).__name__})."


# ------------------------------------------------------------------ GAFI
ALIASES = {
    "COD": ["Democratic Republic of the Congo", "Democratic Republic of Congo"], "CIV": ["Côte d'Ivoire", "Cote d'Ivoire"],
    "VGB": ["Virgin Islands (UK)", "British Virgin Islands"], "LAO": ["Lao People's Democratic Republic", "Laos", "Lao PDR"],
    "VNM": ["Viet Nam", "Vietnam"], "PRK": ["Democratic People's Republic of Korea", "DPRK", "North Korea"],
    "IRN": ["Iran"], "BOL": ["Bolivia"], "VEN": ["Venezuela"], "SYR": ["Syria", "Syrian Arab Republic"],
    "TUR": ["Türkiye", "Turkey"], "RUS": ["Russia", "Russian Federation"], "TZA": ["Tanzania"], "MDA": ["Moldova"],
    "KOR": ["Republic of Korea"], "MMR": ["Myanmar"], "PSE": ["Palestine"],
}


def _english_names(iso3: str) -> list[str]:
    names = list(ALIASES.get(iso3, []))
    try:
        import pycountry
        c = pycountry.countries.get(alpha_3=iso3)
        if c:
            names += [c.name] + ([c.common_name] if hasattr(c, "common_name") else [])
    except Exception:
        pass
    return list(dict.fromkeys(names))


def fetch_fatf() -> tuple[bool, str, dict]:
    """Analyse la page GAFI : renvoie {'grise': set, 'noire': set} détectés dans les dernières publications."""
    try:
        page = _get(URLS["fatf"]).text
        links = re.findall(r'href="([^"]*(?:increased-monitoring|call-for-action)[^"]*\.html)"', page)
        links = list(dict.fromkeys(("https://www.fatf-gafi.org" + l) if l.startswith("/") else l for l in links))
        found = {"grise": set(), "noire": set()}
        cs = load("countries.csv")
        for kind, key in (("grise", "increased-monitoring"), ("noire", "call-for-action")):
            lk = next((l for l in links if key in l), None)
            if not lk:
                continue
            txt = re.sub("<[^>]+>", " ", _get(lk).text)
            for iso in cs["iso3"]:
                if any(re.search(r"\b" + re.escape(n) + r"\b", txt) for n in _english_names(iso)):
                    found[kind].add(iso)
        if not found["grise"]:
            return False, "Publication GAFI détectée mais aucune juridiction reconnue — vérifier manuellement.", found
        return True, f"GAFI : {len(found['grise'])} juridictions sous surveillance, {len(found['noire'])} en appel à l'action.", found
    except Exception as e:
        return False, f"Site du GAFI indisponible ({type(e).__name__}).", {"grise": set(), "noire": set()}


def apply_fatf(found: dict, event: str) -> pd.DataFrame:
    cs = load("countries.csv").copy()
    cs["gafi_statut"] = "-"
    cs.loc[cs["iso3"].isin(found.get("grise", set())), "gafi_statut"] = "grise"
    cs.loc[cs["iso3"].isin(found.get("noire", set())), "gafi_statut"] = "noire"
    cs = recompute_countries(cs)
    save("countries.csv", cs)
    snapshot(event)
    return cs


def snapshot(event: str):
    cs = load("countries.csv")
    hist = load("index_history.csv")
    d = datetime.now().strftime("%Y-%m-%d")
    new = pd.DataFrame({"date": d, "evenement": event, "iso3": cs["iso3"], "gafi_statut": cs["gafi_statut"],
                        "ue_pays_tiers_haut_risque": cs["ue_pays_tiers_haut_risque"], "indice": cs["indice_securite_financiere"]})
    hist = pd.concat([hist[~((hist["date"] == d) & (hist["evenement"] == event))], new], ignore_index=True)
    save("index_history.csv", hist)


def update_all() -> list[tuple[bool, str]]:
    return [update_un(), update_ofac(), update_eu(), update_fr()]
