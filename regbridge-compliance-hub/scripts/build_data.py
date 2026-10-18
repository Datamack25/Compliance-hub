"""
Génère l'ensemble des référentiels CSV de la plateforme (data/*.csv).

Sources principales (voir README) :
- ACPR – Analyse sectorielle des risques LCB-FT (ASR) 2023
- Tracfin – Rapport « LCB-FT : état de la menace 2023-2024 » (tome 3)
- ACPR Commission des sanctions – décision Banque Delubac & Cie (proc. 2024-02, 19/06/2025)
- JOUE C/2023/724 – liste des fonctions publiques importantes (PPE)
- GAFI – liste grise/noire après la plénière de juin 2026
- UE – Règlements délégués (UE) 2026/46 et 2026/83 (pays tiers à haut risque, en vigueur 29/01/2026)
- Règlement (UE) 2024/1624 (AMLR), Directive (UE) 2024/1640 (AMLD6), Règlement (UE) 2024/1620 (AMLA)

Usage : python scripts/build_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def write(name: str, header: list[str], rows: list[list]):
    with open(DATA / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  ✔ {name:38s} {len(rows):>5} lignes")


# ---------------------------------------------------------------------------
# 1. PAYS — statut GAFI, liste UE, sanctions, IPC (indicatif), conflit, opacité
# ---------------------------------------------------------------------------
# iso3;nom;région;gafi(noire/grise/-);ue_hrtc(0/1);sanctions(0-3);régimes;ipc;conflit;opacité;ue
COUNTRIES = """
FRA;France;Europe;-;0;0;;67;0;0;1
DEU;Allemagne;Europe;-;0;0;;75;0;0;1
ITA;Italie;Europe;-;0;0;;54;0;0;1
ESP;Espagne;Europe;-;0;0;;56;0;0;1
PRT;Portugal;Europe;-;0;0;;57;0;0;1
BEL;Belgique;Europe;-;0;0;;69;0;0;1
NLD;Pays-Bas;Europe;-;0;0;;78;0;1;1
LUX;Luxembourg;Europe;-;0;0;;81;0;1;1
IRL;Irlande;Europe;-;0;0;;77;0;1;1
AUT;Autriche;Europe;-;0;0;;67;0;0;1
DNK;Danemark;Europe;-;0;0;;90;0;0;1
SWE;Suède;Europe;-;0;0;;80;0;0;1
FIN;Finlande;Europe;-;0;0;;88;0;0;1
POL;Pologne;Europe;-;0;0;;53;0;0;1
CZE;Tchéquie;Europe;-;0;0;;56;0;0;1
SVK;Slovaquie;Europe;-;0;0;;49;0;0;1
HUN;Hongrie;Europe;-;0;0;;41;0;0;1
ROU;Roumanie;Europe;-;0;0;;46;0;0;1
BGR;Bulgarie;Europe;grise;0;0;;43;0;0;1
GRC;Grèce;Europe;-;0;0;;49;0;0;1
HRV;Croatie;Europe;-;0;0;;47;0;0;1
SVN;Slovénie;Europe;-;0;0;;60;0;0;1
EST;Estonie;Europe;-;0;0;;76;0;0;1
LVA;Lettonie;Europe;-;0;0;;59;0;0;1
LTU;Lituanie;Europe;-;0;0;;63;0;0;1
CYP;Chypre;Europe;-;0;0;;56;0;1;1
MLT;Malte;Europe;-;0;0;;46;0;1;1
GBR;Royaume-Uni;Europe;-;0;0;;71;0;0;0
CHE;Suisse;Europe;-;0;0;;81;0;1;0
NOR;Norvège;Europe;-;0;0;;81;0;0;0
ISL;Islande;Europe;-;0;0;;77;0;0;0
MCO;Monaco;Europe;grise;1;0;;0;0;1;0
LIE;Liechtenstein;Europe;-;0;0;;0;0;1;0
AND;Andorre;Europe;-;0;0;;0;0;1;0
SRB;Serbie;Europe;-;0;0;;35;0;0;0
BIH;Bosnie-Herzégovine;Europe;grise;0;1;UE (atteinte à la stabilité);33;0;0;0
ALB;Albanie;Europe;-;0;0;;42;0;0;0
MKD;Macédoine du Nord;Europe;-;0;0;;40;0;0;0
MNE;Monténégro;Europe;-;0;0;;46;0;0;0
MDA;Moldavie;Europe;-;0;1;UE (déstabilisation);43;0;0;0
UKR;Ukraine;Europe;-;0;2;UE/OFAC (territoires occupés, Crimée);35;1;0;0
BLR;Biélorussie;Europe;-;0;2;UE/OFAC/UK (sectoriel, gel d'avoirs);33;0;0;0
RUS;Russie;Europe;-;1;3;UE (20+ paquets), OFAC, UK, ONU partiel;22;1;0;0
TUR;Turquie;Europe;-;0;1;UE (forages Méditerranée orientale);34;0;0;0
GEO;Géorgie;Europe;-;0;0;;53;0;0;0
ARM;Arménie;Asie;-;0;0;;47;0;0;0
AZE;Azerbaïdjan;Asie;-;0;0;;22;0;0;0
USA;États-Unis;Amériques;-;0;0;;65;0;0;0
CAN;Canada;Amériques;-;0;0;;75;0;0;0
MEX;Mexique;Amériques;-;0;1;OFAC (cartels désignés FTO);26;1;0;0
BRA;Brésil;Amériques;-;0;0;;34;0;0;0
ARG;Argentine;Amériques;-;0;0;;37;0;0;0
CHL;Chili;Amériques;-;0;0;;63;0;0;0
COL;Colombie;Amériques;-;0;0;;39;1;0;0
PER;Pérou;Amériques;-;0;0;;31;0;0;0
ECU;Équateur;Amériques;-;0;0;;32;1;0;0
BOL;Bolivie;Amériques;grise;1;0;;28;0;0;0
VEN;Venezuela;Amériques;grise;1;2;UE/OFAC (sectoriel, gel d'avoirs);10;0;0;0
PRY;Paraguay;Amériques;-;0;0;;24;0;0;0
URY;Uruguay;Amériques;-;0;0;;76;0;0;0
PAN;Panama;Amériques;-;0;0;;33;0;1;0
CRI;Costa Rica;Amériques;-;0;0;;58;0;0;0
GTM;Guatemala;Amériques;-;0;1;UE (atteinte à la démocratie);25;0;0;0
HND;Honduras;Amériques;-;0;0;;22;0;0;0
SLV;Salvador;Amériques;-;0;0;;30;0;0;0
NIC;Nicaragua;Amériques;-;0;1;UE/OFAC (gel d'avoirs);14;0;0;0
CUB;Cuba;Caraïbes;-;0;3;OFAC (embargo global), UE (aucun);26;0;0;0
HTI;Haïti;Caraïbes;grise;1;1;ONU (rés. 2653 - gangs), UE, OFAC;16;1;0;0
DOM;République dominicaine;Caraïbes;-;0;0;;36;0;0;0
JAM;Jamaïque;Caraïbes;-;0;0;;44;0;0;0
TTO;Trinité-et-Tobago;Caraïbes;-;1;0;;41;0;0;0
BHS;Bahamas;Caraïbes;-;0;0;;64;0;1;0
BRB;Barbade;Caraïbes;-;0;0;;68;0;1;0
VGB;Îles Vierges britanniques;Caraïbes;grise;1;0;;0;0;1;0
CYM;Îles Caïmans;Caraïbes;-;0;0;;0;0;1;0
PRI;Porto Rico;Caraïbes;-;0;0;;0;0;0;0
CHN;Chine;Asie;-;0;1;UE (droits de l'homme), OFAC (listes ciblées);43;0;0;0
HKG;Hong Kong;Asie;-;0;1;OFAC (ciblé);74;0;1;0
JPN;Japon;Asie;-;0;0;;71;0;0;0
KOR;Corée du Sud;Asie;-;0;0;;64;0;0;0
PRK;Corée du Nord;Asie;noire;1;3;ONU, UE, OFAC (embargo global);15;0;0;0
IND;Inde;Asie;-;0;0;;38;0;0;0
PAK;Pakistan;Asie;-;0;0;;27;1;0;0
AFG;Afghanistan;Asie;-;1;2;ONU (régime 1988 Taliban), UE, OFAC;17;1;0;0
BGD;Bangladesh;Asie;-;0;0;;23;0;0;0
LKA;Sri Lanka;Asie;-;0;0;;32;0;0;0
NPL;Népal;Asie;grise;1;0;;34;0;0;0
MMR;Myanmar;Asie;noire;1;2;UE/OFAC/UK (embargo armes, gel);16;1;0;0
THA;Thaïlande;Asie;-;0;0;;34;0;0;0
VNM;Vietnam;Asie;grise;1;0;;40;0;0;0
LAO;Laos;Asie;grise;1;0;;33;0;0;0
KHM;Cambodge;Asie;-;0;0;;21;0;0;0
MYS;Malaisie;Asie;-;0;0;;50;0;0;0
SGP;Singapour;Asie;-;0;0;;84;0;1;0
IDN;Indonésie;Asie;-;0;0;;37;0;0;0
PHL;Philippines;Asie;-;0;0;;33;0;0;0
KAZ;Kazakhstan;Asie;-;0;0;;40;0;0;0
UZB;Ouzbékistan;Asie;-;0;0;;32;0;0;0
KGZ;Kirghizistan;Asie;-;0;0;;25;0;0;0
TJK;Tadjikistan;Asie;-;0;0;;19;0;0;0
TKM;Turkménistan;Asie;-;0;0;;17;0;0;0
MNG;Mongolie;Asie;-;0;0;;33;0;0;0
ARE;Émirats arabes unis;Moyen-Orient;-;0;0;;68;0;1;0
SAU;Arabie saoudite;Moyen-Orient;-;0;0;;59;0;0;0
QAT;Qatar;Moyen-Orient;-;0;0;;59;0;0;0
KWT;Koweït;Moyen-Orient;grise;0;0;;46;0;0;0
BHR;Bahreïn;Moyen-Orient;-;0;0;;53;0;0;0
OMN;Oman;Moyen-Orient;-;0;0;;55;0;0;0
JOR;Jordanie;Moyen-Orient;-;0;0;;49;0;0;0
ISR;Israël;Moyen-Orient;-;0;0;;64;1;0;0
PSE;Palestine;Moyen-Orient;-;0;1;UE/OFAC (Hamas - gel ciblé);0;1;0;0
LBN;Liban;Moyen-Orient;grise;1;1;UE/OFAC (Hezbollah - ciblé);22;1;0;0
SYR;Syrie;Moyen-Orient;grise;1;2;ONU (HTS), UE/OFAC (allègements 2025, ciblé);12;1;0;0
IRQ;Irak;Moyen-Orient;grise;0;1;ONU (résiduel), OFAC (ciblé);26;1;0;0
IRN;Iran;Moyen-Orient;noire;1;3;ONU (snapback 2025), UE, OFAC (embargo global);23;1;0;0
YEM;Yémen;Moyen-Orient;grise;1;1;ONU (Houthis - rés. 2140);13;1;0;0
EGY;Égypte;Afrique;-;0;0;;30;0;0;0
LBY;Libye;Afrique;-;0;2;ONU (embargo armes, gel), UE;13;1;0;0
TUN;Tunisie;Afrique;-;0;1;UE (détournement de fonds publics);39;0;0;0
DZA;Algérie;Afrique;-;1;0;;34;0;0;0
MAR;Maroc;Afrique;-;0;0;;37;0;0;0
MRT;Mauritanie;Afrique;-;0;0;;30;0;0;0
SEN;Sénégal;Afrique;-;0;0;;45;0;0;0
MLI;Mali;Afrique;-;0;1;UE (gel ciblé);27;1;0;0
BFA;Burkina Faso;Afrique;-;0;0;;41;1;0;0
NER;Niger;Afrique;-;0;1;UE (gel ciblé);34;1;0;0
TCD;Tchad;Afrique;-;0;0;;21;1;0;0
NGA;Nigeria;Afrique;-;0;0;;26;1;0;0
GHA;Ghana;Afrique;-;0;0;;42;0;0;0
CIV;Côte d'Ivoire;Afrique;grise;1;0;;45;0;0;0
GIN;Guinée;Afrique;-;0;1;UE (gel ciblé);28;0;0;0
GNB;Guinée-Bissau;Afrique;-;0;1;ONU/UE (gel ciblé);21;0;0;0
SLE;Sierra Leone;Afrique;-;0;0;;33;0;0;0
LBR;Liberia;Afrique;-;0;0;;25;0;0;0
TGO;Togo;Afrique;-;0;0;;32;0;0;0
BEN;Bénin;Afrique;-;0;0;;45;0;0;0
CMR;Cameroun;Afrique;grise;1;0;;26;1;0;0
GAB;Gabon;Afrique;-;0;0;;27;0;0;0
COG;Congo;Afrique;-;0;0;;23;0;0;0
COD;RD Congo;Afrique;grise;1;1;ONU/UE (embargo armes, gel);20;1;0;0
CAF;Centrafrique;Afrique;-;0;1;ONU/UE (embargo armes);24;1;0;0
SDN;Soudan;Afrique;-;0;2;ONU/UE/OFAC (Darfour, RSF);15;1;0;0
SSD;Soudan du Sud;Afrique;grise;1;1;ONU (embargo armes);8;1;0;0
ETH;Éthiopie;Afrique;-;0;0;;37;1;0;0
ERI;Érythrée;Afrique;-;0;1;UE (gel ciblé);13;0;0;0
SOM;Somalie;Afrique;-;0;1;ONU (Al-Shabaab, embargo armes);9;1;0;0
KEN;Kenya;Afrique;grise;1;0;;32;0;0;0
UGA;Ouganda;Afrique;-;0;0;;26;0;0;0
TZA;Tanzanie;Afrique;-;0;0;;41;0;0;0
RWA;Rwanda;Afrique;-;0;0;;57;0;0;0
BDI;Burundi;Afrique;-;0;1;UE (gel ciblé);17;0;0;0
AGO;Angola;Afrique;grise;1;0;;32;0;0;0
ZMB;Zambie;Afrique;-;0;0;;39;0;0;0
ZWE;Zimbabwe;Afrique;-;0;1;UE (embargo armes);21;0;0;0
MOZ;Mozambique;Afrique;-;0;0;;25;1;0;0
MDG;Madagascar;Afrique;-;0;0;;26;0;0;0
MUS;Maurice;Afrique;-;0;0;;51;0;1;0
NAM;Namibie;Afrique;-;1;0;;49;0;0;0
BWA;Botswana;Afrique;-;0;0;;57;0;0;0
ZAF;Afrique du Sud;Afrique;-;0;0;;41;0;0;0
AUS;Australie;Océanie;-;0;0;;77;0;0;0
NZL;Nouvelle-Zélande;Océanie;-;0;0;;83;0;0;0
PNG;Papouasie-Nouvelle-Guinée;Océanie;grise;0;0;;31;0;0;0
VUT;Vanuatu;Océanie;-;1;0;;0;0;1;0
FJI;Fidji;Océanie;-;0;0;;0;0;0;0
"""


def security_index(fatf, ue, sanc, cpi, conflict, secrecy):
    s = 100.0
    s -= {"noire": 35, "grise": 16}.get(fatf, 0)
    s -= 10 * int(ue)
    s -= 9 * int(sanc)
    cpi_eff = cpi if cpi > 0 else 55  # IPC non publié -> valeur neutre
    s -= (100 - cpi_eff) * 0.40
    s -= 10 * int(conflict)
    s -= 6 * int(secrecy)
    return round(max(0.0, min(100.0, s)), 1)


def niveau(idx):
    if idx >= 80:
        return "Faible"
    if idx >= 62:
        return "Modéré"
    if idx >= 42:
        return "Élevé"
    return "Très élevé"


country_rows = []
for line in COUNTRIES.strip().splitlines():
    iso, nom, reg, fatf, ue, sanc, regimes, cpi, conf, sec, eu = line.split(";")
    idx = security_index(fatf, ue, sanc, int(cpi), conf, sec)
    pep_risk = "Élevé" if (int(cpi) and int(cpi) < 35) or sanc in ("2", "3") else ("Modéré" if int(cpi) < 55 else "Standard")
    country_rows.append([iso, nom, reg, fatf, int(ue), int(sanc), regimes, int(cpi), int(conf), int(sec), int(eu),
                         idx, niveau(idx), pep_risk])
write("countries.csv",
      ["iso3", "pays", "region", "gafi_statut", "ue_pays_tiers_haut_risque", "niveau_sanctions", "regimes_sanctions",
       "ipc_indicatif", "zone_conflit", "opacite_financiere", "membre_ue", "indice_securite_financiere",
       "niveau_risque_pays", "risque_ppe"],
      country_rows)

# Historique de l'indice (snapshots datés : listes UE 29/01/2026, plénière GAFI 19/06/2026, aujourd'hui)
def snapshot_rows(label, d, overrides):
    rows = []
    for r in country_rows:
        iso, fatf, ue = r[0], r[3], r[4]
        if iso in overrides:
            fatf, ue = overrides[iso].get("gafi", fatf), overrides[iso].get("ue", ue)
        idx = security_index(fatf, ue, r[5], r[7], r[8], r[9])
        rows.append([d, label, iso, fatf, ue, idx])
    return rows

hist = []
# Avant 29/01/2026 : Nigeria, Afrique du Sud, Mozambique, Tanzanie, Burkina, Mali sur la liste UE ;
# Bolivie, BVI, Russie pas encore sur la liste UE.
pre_ue = {"NGA": {"ue": 1}, "ZAF": {"ue": 1}, "MOZ": {"ue": 1}, "TZA": {"ue": 1}, "BFA": {"ue": 1}, "MLI": {"ue": 1},
          "BOL": {"ue": 0}, "VGB": {"ue": 0}, "RUS": {"ue": 0},
          "DZA": {"gafi": "grise"}, "NAM": {"gafi": "grise"}, "BIH": {"gafi": "-"}, "IRQ": {"gafi": "-"}}
hist += snapshot_rows("Avant MAJ liste UE (déc. 2025)", "2025-12-31", pre_ue)
pre_gafi = {"DZA": {"gafi": "grise"}, "NAM": {"gafi": "grise"}, "BIH": {"gafi": "-"}, "IRQ": {"gafi": "-"}}
hist += snapshot_rows("Liste UE 2026/46 & 2026/83", "2026-01-29", pre_gafi)
hist += snapshot_rows("Plénière GAFI juin 2026", "2026-06-19", {})
write("index_history.csv", ["date", "evenement", "iso3", "gafi_statut", "ue_pays_tiers_haut_risque", "indice"], hist)

# ---------------------------------------------------------------------------
# 2. RÉGIMES DE SANCTIONS / EMBARGOS
# ---------------------------------------------------------------------------
sanctions = [
    ["RUS", "Russie", "UE", "Sectoriel + gel d'avoirs + interdictions d'import/export", "Règl. (UE) 833/2014 et 269/2014", "2014-07-31", "Très élevé"],
    ["RUS", "Russie", "OFAC", "Gel SDN, sanctions secondaires, plafonnement pétrole", "EO 14024", "2021-04-15", "Très élevé"],
    ["BLR", "Biélorussie", "UE", "Sectoriel + gel d'avoirs", "Règl. (UE) 765/2006", "2006-05-18", "Élevé"],
    ["IRN", "Iran", "ONU", "Rétablissement des sanctions (snapback) prolifération", "Rés. 1737 et suivantes", "2025-09-28", "Très élevé"],
    ["IRN", "Iran", "UE", "Gel d'avoirs, restrictions financières, prolifération et droits de l'homme", "Règl. (UE) 267/2012 et 359/2011", "2012-03-23", "Très élevé"],
    ["IRN", "Iran", "OFAC", "Embargo global", "ITSR 31 CFR 560", "1995-03-15", "Très élevé"],
    ["PRK", "Corée du Nord", "ONU", "Embargo global prolifération", "Rés. 1718 (2006)", "2006-10-14", "Très élevé"],
    ["PRK", "Corée du Nord", "UE", "Embargo + gel d'avoirs", "Règl. (UE) 2017/1509", "2017-08-30", "Très élevé"],
    ["CUB", "Cuba", "OFAC", "Embargo global (CACR)", "31 CFR 515", "1963-07-08", "Très élevé"],
    ["SYR", "Syrie", "UE", "Levée de la plupart des mesures économiques (mai 2025), maintien gel ciblé et armes", "Règl. (UE) 36/2012 modifié", "2025-05-28", "Élevé"],
    ["SYR", "Syrie", "ONU", "Régime Al-Qaida / HTS (gel ciblé)", "Rés. 1267/1989/2253", "2014-05-14", "Élevé"],
    ["VEN", "Venezuela", "UE", "Embargo armes + gel d'avoirs", "Règl. (UE) 2017/2063", "2017-11-13", "Élevé"],
    ["VEN", "Venezuela", "OFAC", "Sanctions sectorielles (PDVSA, gouvernement)", "EO 13850, 13884", "2019-08-05", "Élevé"],
    ["MMR", "Myanmar", "UE", "Embargo armes + gel d'avoirs", "Règl. (UE) 401/2013", "2013-04-29", "Élevé"],
    ["AFG", "Afghanistan", "ONU", "Régime 1988 (Taliban) – gel, voyage, armes", "Rés. 1988 (2011)", "2011-06-17", "Élevé"],
    ["LBY", "Libye", "ONU", "Embargo armes + gel d'avoirs", "Rés. 1970 (2011)", "2011-02-26", "Élevé"],
    ["SDN", "Soudan", "ONU", "Darfour – embargo armes, gel", "Rés. 1591 (2005)", "2005-03-29", "Élevé"],
    ["SSD", "Soudan du Sud", "ONU", "Embargo armes", "Rés. 2428 (2018)", "2018-07-13", "Modéré"],
    ["COD", "RD Congo", "ONU", "Embargo armes + gel ciblé", "Rés. 1533 (2004)", "2004-03-12", "Modéré"],
    ["CAF", "Centrafrique", "ONU", "Embargo armes (allégé) + gel ciblé", "Rés. 2127 (2013)", "2013-12-05", "Modéré"],
    ["SOM", "Somalie", "ONU", "Al-Shabaab – gel ciblé, embargo armes", "Rés. 2713 (2023)", "2023-12-01", "Élevé"],
    ["YEM", "Yémen", "ONU", "Gel ciblé (Houthis), embargo armes ciblé", "Rés. 2140 (2014)", "2014-02-26", "Élevé"],
    ["HTI", "Haïti", "ONU", "Gel ciblé (gangs), embargo armes", "Rés. 2653 (2022)", "2022-10-21", "Modéré"],
    ["LBN", "Liban", "OFAC", "Hezbollah – SDGT", "EO 13224", "2001-09-23", "Modéré"],
    ["IRQ", "Irak", "ONU", "Régime résiduel (ex-régime)", "Rés. 1483 (2003)", "2003-05-22", "Faible"],
    ["NIC", "Nicaragua", "UE", "Gel d'avoirs ciblé", "Règl. (UE) 2019/1716", "2019-10-14", "Modéré"],
    ["MLI", "Mali", "UE", "Gel d'avoirs ciblé", "Règl. (UE) 2017/1770", "2017-09-28", "Modéré"],
    ["GIN", "Guinée", "UE", "Gel d'avoirs ciblé", "Règl. (UE) 1284/2009", "2009-12-22", "Faible"],
    ["GNB", "Guinée-Bissau", "ONU", "Interdiction de voyage ciblée", "Rés. 2048 (2012)", "2012-05-18", "Faible"],
    ["BDI", "Burundi", "UE", "Gel d'avoirs ciblé", "Règl. (UE) 2015/1755", "2015-10-01", "Faible"],
    ["ZWE", "Zimbabwe", "UE", "Embargo armes", "Décision 2011/101/PESC", "2002-02-18", "Faible"],
    ["TUN", "Tunisie", "UE", "Détournement de fonds publics", "Règl. (UE) 101/2011", "2011-02-04", "Faible"],
    ["MDA", "Moldavie", "UE", "Actions de déstabilisation", "Règl. (UE) 2023/888", "2023-04-28", "Faible"],
    ["GTM", "Guatemala", "UE", "Atteinte à la démocratie", "Règl. (UE) 2024/287", "2024-01-12", "Faible"],
    ["TUR", "Turquie", "UE", "Forages non autorisés en Méditerranée orientale", "Règl. (UE) 2019/1890", "2019-11-11", "Faible"],
    ["CHN", "Chine", "UE", "Droits de l'homme (régime mondial)", "Règl. (UE) 2020/1998", "2021-03-22", "Faible"],
    ["UKR", "Ukraine", "UE", "Crimée/Sébastopol et territoires occupés (Donetsk, Louhansk, Zaporijia, Kherson)", "Règl. (UE) 692/2014 et 2022/263", "2014-06-23", "Élevé"],
    ["PSE", "Palestine", "UE", "Hamas / Jihad islamique – gel ciblé", "Règl. (UE) 2024/386", "2024-01-19", "Modéré"],
    ["MEX", "Mexique", "OFAC", "Cartels désignés FTO/SDGT", "EO 14157", "2025-02-20", "Modéré"],
    ["*", "Thématique", "UE", "Régime mondial cyberattaques", "Règl. (UE) 2019/796", "2019-05-17", "Variable"],
    ["*", "Thématique", "UE", "Régime terrorisme (liste UE autonome)", "Règl. (CE) 2580/2001", "2001-12-27", "Variable"],
    ["*", "Thématique", "UE", "Armes chimiques", "Règl. (UE) 2018/1542", "2018-10-15", "Variable"],
    ["*", "Thématique", "France", "Gel des avoirs national (DG Trésor) – terrorisme", "CMF L.562-2 et s.", "2016-06-03", "Variable"],
]
write("sanctions_regimes.csv", ["iso3", "pays", "autorite", "nature", "base_legale", "depuis", "intensite"], sanctions)

# Entités de démonstration pour tests de filtrage (fictives — préfixe TEST)
demo_entities = [
    ["TEST-001", "TEST Ivan Petrovitch Volkov", "Personne", "RUS", "UE", "Gel d'avoirs (démo)", "1968-03-12"],
    ["TEST-002", "TEST Golden Crescent Trading LLC", "Entité", "ARE", "OFAC", "SDN (démo)", ""],
    ["TEST-003", "TEST Ali Reza Tehrani", "Personne", "IRN", "ONU", "Prolifération (démo)", "1975-09-01"],
    ["TEST-004", "TEST Northern Star Shipping Co", "Entité", "PRK", "ONU", "Navire / transport (démo)", ""],
    ["TEST-005", "TEST Mohamed Al-Sayed Haddad", "Personne", "SYR", "France", "Gel national terrorisme (démo)", "1981-01-20"],
    ["TEST-006", "TEST Caribbean Bridge Remit SA", "Entité", "HTI", "ONU", "Soutien aux gangs (démo)", ""],
    ["TEST-007", "TEST Olga Sergeyevna Morozova", "Personne", "BLR", "UE", "Gel d'avoirs (démo)", "1972-11-05"],
    ["TEST-008", "TEST Sahel Gold Export SARL", "Entité", "MLI", "UE", "Gel ciblé (démo)", ""],
]
write("sanctions_entities_demo.csv", ["id", "nom", "type", "pays", "liste", "programme", "date_naissance"], demo_entities)

# ---------------------------------------------------------------------------
# 3. SECTEURS & NIVEAUX DE RISQUE ASR 2023
# ---------------------------------------------------------------------------
sectors = [
    ["BANQUE", "Banque", "ACPR", "Modéré à élevé", "CMF L.561-2 1°; arrêté du 6 janv. 2021", "Banque de détail, gestion de fortune, correspondance bancaire, trade finance, crédit"],
    ["FINTECH", "Fintech de paiement (EP/EME)", "ACPR", "Élevé à très élevé", "CMF L.561-2 1° et 1° bis; DSP2", "Comptes de paiement, IBAN virtuels, monnaie électronique, cartes prépayées, agents"],
    ["ASSURANCE", "Assurance", "ACPR", "Faible à modéré", "CMF L.561-2 2°", "Assurance-vie, capitalisation, rachats anticipés, assurance rançon"],
    ["JEUX", "Jeux et paris (casinos, opérateurs en ligne)", "ANJ / SCCJ", "Élevé", "CMF L.561-2 9° et 9° bis", "Casinos, paris sportifs/hippiques, poker en ligne, cercles de jeux"],
    ["IMMOBILIER", "Immobilier", "DGCCRF", "Élevé", "CMF L.561-2 8°", "Agents immobiliers, marchands de biens, promoteurs, gestion locative haut de gamme"],
    ["TRANSFERT", "Transmission de fonds (MTO)", "ACPR", "Très élevé", "CMF L.561-2 1°; Règl. (UE) 2023/1113", "Transferts en espèces, corridors à risque, agents, hawala"],
    ["CRYPTO", "Crypto-actifs (PSAN/CASP)", "AMF / ACPR", "Très élevé", "MiCA 2023/1114; TFR 2023/1113; CMF L.54-10-1", "Conversion fiat-crypto, wallets non hébergés, mixeurs, DeFi, NFT"],
    ["CHANGE", "Change manuel", "ACPR", "Élevé", "CMF L.561-2 7°", "Change d'espèces, clientèle occasionnelle, frontières"],
    ["ENTREPRISE", "Entreprise non financière / Corporate", "Selon assujettissement", "Variable", "Loi Sapin II; CMF L.561-2 (si assujettie)", "Anticorruption, sanctions/export, fraude fournisseurs, tiers"],
]
write("sectors.csv", ["code", "secteur", "superviseur", "niveau_asr", "base_legale", "perimetre"], sectors)

asr = [
    # produit, secteur, menace, vulnérabilité, risque global (grille ACPR p.113)
    ["Actifs numériques", "CRYPTO", "Très élevée", "Très élevée", "Très élevé"],
    ["Transmission de fonds", "TRANSFERT", "Très élevée", "Très élevée", "Très élevé"],
    ["Monnaie électronique", "FINTECH", "Élevée", "Très élevée", "Très élevé"],
    ["Change manuel", "CHANGE", "Très élevée", "Modérée", "Élevé"],
    ["Établissement de paiement", "FINTECH", "Élevée", "Élevée", "Élevé"],
    ["Intermédiaire en financement participatif (IFP)", "FINTECH", "Élevée", "Élevée", "Élevé"],
    ["Gestion de fortune", "BANQUE", "Élevée", "Élevée", "Élevé"],
    ["Correspondance bancaire hors UE", "BANQUE", "Élevée", "Élevée", "Élevé"],
    ["Crédit à la consommation (FT)", "BANQUE", "Élevée", "Élevée", "Élevé"],
    ["Banque de détail", "BANQUE", "Élevée", "Modérée", "Modéré"],
    ["Correspondance bancaire intra-UE", "BANQUE", "Élevée", "Modérée", "Modéré"],
    ["Assurance rançon", "ASSURANCE", "Élevée", "Modérée", "Modéré"],
    ["Services d'investissement (BC)", "BANQUE", "Modérée", "Modérée", "Modéré"],
    ["BFI et crédits aux entreprises (BC)", "BANQUE", "Modérée", "Modérée", "Modéré"],
    ["Trade finance", "BANQUE", "Modérée", "Modérée", "Modéré"],
    ["Assurance-vie", "ASSURANCE", "Modérée", "Modérée", "Modéré"],
    ["Crédit immobilier de luxe", "IMMOBILIER", "Modérée", "Modérée", "Modéré"],
    ["Courtiers en assurance-vie", "ASSURANCE", "Modérée", "Modérée", "Modéré"],
    ["Crédit à la consommation (BC)", "BANQUE", "Modérée", "Élevée", "Modéré"],
    ["Leasing", "BANQUE", "Modérée", "Faible", "Faible"],
    ["Affacturage", "BANQUE", "Modérée", "Faible", "Faible"],
    ["Cautionnement et nantissement", "BANQUE", "Faible", "Faible", "Faible"],
    ["Crédit immobilier (hors luxe)", "IMMOBILIER", "Faible", "Faible", "Faible"],
    ["Courtiers OBSP et d'assurance (hors vie)", "ASSURANCE", "Faible", "Faible", "Faible"],
    ["Activités de crédit hors conso", "BANQUE", "Faible", "Modérée", "Faible"],
    ["Assurance non-vie (hors rançon)", "ASSURANCE", "Faible", "Modérée", "Faible"],
]
write("asr_2023_products.csv", ["produit", "secteur", "menace", "vulnerabilite", "risque_global"], asr)

# ---------------------------------------------------------------------------
# 4. FACTEURS DE RISQUE PAR SECTEUR (base des cartographies)
# ---------------------------------------------------------------------------
# secteur | catégorie | facteur | probabilité 1-4 | impact 1-4 | dispositif d'atténuation | réf.
RF = {
    "BANQUE": [
        ("Clientèle", "Personnes politiquement exposées (PPE) et proches", 3, 4, "Filtrage PPE à l'entrée en relation et en continu, accord de la direction, origine du patrimoine", "CMF L.561-10 2°; AMLR art. 42-46"),
        ("Clientèle", "Clients non-résidents / pays tiers à haut risque", 3, 4, "Vigilance renforcée art. L.561-10 4°, contrôle des flux par pays", "CMF L.561-10; AMLR art. 29-31"),
        ("Clientèle", "Structures opaques, trusts, sociétés-écrans", 3, 4, "Identification des bénéficiaires effectifs (RBE), seuil 25 %, organigramme", "CMF R.561-1; AMLR art. 51-58"),
        ("Clientèle", "Professionnels à forte intensité d'espèces", 4, 3, "Profil de fonctionnement attendu, seuils espèces, justificatifs", "ASR 2023 §2.2.1"),
        ("Clientèle", "Clients faisant l'objet de presse négative / réquisitions", 3, 4, "Filtrage presse négative, vigilance renforcée, examen renforcé", "Décision ACPR Delubac 2025 (grief 4)"),
        ("Produits", "Gestion de fortune / banque privée", 3, 4, "Origine des fonds et du patrimoine, revue annuelle", "ASR 2023 §3.2.3"),
        ("Produits", "Correspondance bancaire hors UE", 3, 4, "Questionnaire Wolfsberg, due diligence correspondant, interdiction banques fictives", "CMF L.561-10-3; AMLR art. 36"),
        ("Produits", "Trade finance", 2, 3, "Contrôle documentaire, prix anormaux, double usage, navires", "ASR 2023 §3.2.5"),
        ("Produits", "Crédit à la consommation (risque FT)", 3, 3, "Détection micro-crédits avant départ zone de conflit", "ASR 2023 §3.2.7"),
        ("Canaux", "Entrée en relation à distance", 3, 3, "Solution PVID / eIDAS, contrôles anti-fraude documentaire", "CMF R.561-5-1; AMLR art. 22"),
        ("Canaux", "Recours à des intermédiaires / apporteurs", 2, 3, "Contrats, audits, tierce introduction encadrée", "CMF L.561-7"),
        ("Géographie", "Flux vers/depuis pays GAFI liste grise/noire", 3, 4, "Surveillance des opérations effectives (pas seulement déclaratif)", "Décision ACPR Delubac 2025 (grief 3)"),
        ("Géographie", "Activité en Outre-mer (espèces, proximité zones à risque)", 3, 3, "Seuils adaptés, typologies ultramarines", "ASR 2023 §2.2.4; Tracfin cas 5"),
        ("Opérations", "Dépôts d'espèces importants ou fractionnés", 4, 3, "Scénarios de fractionnement, seuils, COSI", "CMF L.561-15-1"),
        ("Opérations", "Opérations incohérentes avec le profil financier", 3, 4, "Modèles d'alerte intégrant revenus/patrimoine/CA déclarés", "Décision ACPR Delubac 2025 (grief 1)"),
        ("Opérations", "Stock d'alertes non traitées / délais excessifs", 3, 4, "Pilotage des stocks, SLA, effectifs dédiés", "Décision ACPR Delubac 2025 (grief 2)"),
        ("Dispositif", "Défaut ou retard de déclaration de soupçon", 2, 4, "Arbre de décision DS, comité, délais, traçabilité", "CMF L.561-15; décision Delubac (griefs 6-7)"),
        ("Dispositif", "Gel des avoirs – filtrage incomplet", 2, 4, "Filtrage temps réel des virements, mise à jour quotidienne listes", "CMF L.562-4-1; arrêté 6 janv. 2021"),
    ],
    "FINTECH": [
        ("Clientèle", "Mules financières recrutées sur réseaux sociaux", 4, 4, "Détection de comptes de passage, device fingerprinting, vélocité", "ASR 2023 §3.3; Tracfin 2023"),
        ("Clientèle", "Usurpation d'identité / faux documents", 4, 3, "Vérification biométrique, liveness, contrôle MRZ", "ASR 2023 §2.2.3"),
        ("Clientèle", "Marchands à risque (jeux, crypto, contenus adultes, nutraceutiques)", 3, 3, "KYB marchand, MCC, contrôle site web, chargebacks", "Schémas cartes; DSP2"),
        ("Clientèle", "PPE et clients de pays tiers à haut risque", 2, 4, "Filtrage PPE/sanctions automatisé, vigilance renforcée", "AMLR art. 29-46"),
        ("Produits", "IBAN virtuels et comptes de cantonnement", 3, 4, "Traçabilité du donneur d'ordre final, contrôle des agents", "ASR 2023 §2.2.2"),
        ("Produits", "Monnaie électronique anonyme / cartes prépayées", 4, 4, "Plafonds, interdiction ME anonyme pour paiements à distance", "CMF R.561-16-1; AMLR art. 19"),
        ("Produits", "Paiements instantanés (SCT Inst)", 3, 3, "Filtrage sanctions quotidien, vérification bénéficiaire (VoP)", "Règl. (UE) 2024/886"),
        ("Canaux", "Distribution via agents et distributeurs de ME", 3, 3, "Contrôle des agents, formation, audits", "CMF L.523-1; L.525-8"),
        ("Canaux", "Onboarding 100 % digital", 4, 3, "PVID, contrôles d'IP/VPN, appareils", "AMLR art. 22"),
        ("Géographie", "Corridors Europe-Afrique-Caraïbes", 3, 3, "Scoring corridor, plafonds par pays", "ASR 2023 §3.3.3"),
        ("Opérations", "Comptes de passage (crédit/débit rapides)", 4, 4, "Ratio entrée/sortie, durée de détention des fonds", "Tracfin cas 17"),
        ("Opérations", "Fraude au virement / APP fraud", 4, 3, "Analyse comportementale, délais de rétention", "PSR (projet); Règl. 2024/886"),
        ("Opérations", "Fractionnement sous les seuils", 3, 3, "Agrégation multi-comptes et multi-cartes", "CMF L.561-15"),
        ("Dispositif", "Externalisation KYC / outils fournisseurs", 3, 3, "Contrôle des PSEE, DORA, audits", "DORA 2022/2554; arrêté 3 nov. 2014"),
        ("Dispositif", "Croissance rapide non accompagnée du dispositif LCB-FT", 3, 4, "Plan de staffing conformité, KPI d'alertes", "ASR 2023 §3.3.2"),
    ],
    "ASSURANCE": [
        ("Clientèle", "Souscripteurs PPE ou non-résidents", 2, 4, "Filtrage PPE, origine des fonds", "CMF L.561-10"),
        ("Clientèle", "Bénéficiaire du contrat ≠ souscripteur sans lien apparent", 3, 3, "Contrôle au dénouement, lien souscripteur/bénéficiaire", "CMF R.561-12"),
        ("Produits", "Assurance-vie et capitalisation (primes élevées)", 3, 3, "Origine des fonds au-delà de seuils, justificatifs", "ASR 2023 §5.2"),
        ("Produits", "Rachats anticipés malgré pénalités", 3, 3, "Alerte rachat précoce, analyse de cohérence", "Lignes directrices ACPR assurance"),
        ("Produits", "Contrats de capitalisation au porteur", 2, 4, "Identification du porteur à chaque opération", "CGI 990 A; CMF"),
        ("Produits", "Assurance rançon (rançongiciels)", 3, 3, "Filtrage sanctions des bénéficiaires de rançon", "ASR 2023 §5.3"),
        ("Canaux", "Distribution via courtiers / CGP", 3, 3, "Conventions, audits des intermédiaires", "ASR 2023 §6"),
        ("Géographie", "Primes payées depuis l'étranger / tiers payeurs", 3, 3, "Interdiction/justification tiers payeur", "CMF L.561-6"),
        ("Opérations", "Versements libres en espèces ou fractionnés", 2, 3, "Refus espèces, cumul des versements", "CMF L.112-6"),
        ("Opérations", "Avances et nantissements de contrats", 2, 3, "Contrôle des avances successives", "ASR 2023 §5.2"),
        ("Fraude", "Fraude à l'assurance (sinistres fictifs)", 3, 2, "Scoring sinistres, ALFA, contrôles terrain", "Code des assurances"),
    ],
    "JEUX": [
        ("Clientèle", "Joueurs sans ressources licites suffisantes", 3, 4, "Origine des fonds au-delà de 2 000 €, cohérence profil", "Tracfin cas 9; CMF L.561-13"),
        ("Clientèle", "Joueurs PPE / joueurs étrangers", 2, 3, "Filtrage PPE/sanctions à l'enregistrement", "CMF L.561-10"),
        ("Clientèle", "Prête-noms / comptes joueurs multiples", 3, 3, "Contrôle identité, device, adresses IP", "ANJ – lignes directrices LCB-FT"),
        ("Produits", "Rachat de tickets gagnants", 3, 4, "Traçabilité des gains, identification au paiement", "Tracfin 2023"),
        ("Produits", "Poker et jeux entre joueurs (chip dumping)", 3, 3, "Détection transferts inter-joueurs", "ANJ"),
        ("Produits", "Paris sportifs (matchs truqués)", 3, 4, "Monitoring cotes anormales, ANJ, intégrité", "Convention de Macolin"),
        ("Canaux", "Jeux en ligne (comptes multiples, VPN)", 3, 3, "Géolocalisation, empreinte appareil", "Loi 2010-476"),
        ("Opérations", "Mises en espèces élevées / échange plaques-espèces", 4, 3, "Seuils d'identification, registre", "CMF R.561-10; Tracfin cas 9"),
        ("Opérations", "Faible activité de jeu après dépôt (blanchiment par alimentation)", 3, 3, "Ratio mises/dépôts, retraits rapides", "ANJ"),
        ("Opérations", "Gains fréquents et conséquents incohérents", 3, 3, "Analyse des gains déclarés", "Tracfin cas 2"),
    ],
    "IMMOBILIER": [
        ("Clientèle", "Acquéreurs via SCI ou sociétés étrangères", 3, 4, "Identification des bénéficiaires effectifs", "CMF L.561-2 8°; Tracfin cas 7"),
        ("Clientèle", "Acquéreurs PPE / non-résidents", 3, 4, "Filtrage PPE, origine des fonds", "CMF L.561-10"),
        ("Produits", "Biens de prestige / immobilier de luxe", 3, 4, "Vigilance renforcée au-delà de seuils", "ASR 2023"),
        ("Produits", "Vente à prix décoté / montages successifs", 3, 4, "Comparaison prix marché (DVF)", "Tracfin cas 7"),
        ("Canaux", "Mandats sans rencontre physique", 2, 3, "Vérification à distance renforcée", "CMF R.561-5-2"),
        ("Opérations", "Acquisition sans prêt bancaire / apport important", 3, 4, "Justification origine des fonds", "Tracfin cas 7"),
        ("Opérations", "Fonds provenant de pays tiers à haut risque", 3, 4, "Vigilance renforcée géographique", "AMLR art. 29"),
        ("Opérations", "Location saisonnière avec loyers anormaux", 2, 3, "Cohérence loyers marché", "Tracfin"),
        ("Dispositif", "Absence de classification des risques chez les agents", 3, 3, "Cartographie, formation, procédures", "Contrôles DGCCRF"),
    ],
    "TRANSFERT": [
        ("Clientèle", "Expéditeurs multiples vers un même bénéficiaire collecteur", 4, 4, "Analyse de réseau expéditeurs/bénéficiaires", "Tracfin cas 17"),
        ("Clientèle", "Clientèle occasionnelle non identifiée", 4, 3, "Identification dès le 1er euro (transfert de fonds)", "CMF R.561-10 II"),
        ("Produits", "Transferts payés en espèces", 4, 4, "Plafonds, justificatifs, fractionnement", "ASR 2023 §3.3.3"),
        ("Canaux", "Réseau d'agents peu contrôlés", 4, 3, "Audits agents, mystery shopping, résiliation", "CMF L.523-1"),
        ("Canaux", "Hawala / systèmes de compensation informels", 3, 4, "Détection d'agents non déclarés", "GAFI 2026 hawala"),
        ("Géographie", "Corridors à risque (zones de conflit, liste grise)", 4, 4, "Scoring corridor, refus pays sous embargo", "GAFI; UE 2016/1675"),
        ("Opérations", "Volume et fréquence élevés par expéditeur", 4, 3, "Seuils de vélocité, agrégation", "Tracfin cas 17"),
        ("Opérations", "Informations incomplètes sur le donneur d'ordre (TFR)", 3, 4, "Contrôle des données accompagnant les virements", "Règl. (UE) 2023/1113"),
        ("Opérations", "Financement du terrorisme (petits montants)", 3, 4, "Scénarios FT, zones sensibles", "Tracfin cas 15-16"),
    ],
    "CRYPTO": [
        ("Clientèle", "Clients utilisant VPN / anonymisation", 4, 4, "Blocage TOR/VPN, géolocalisation", "MiCA; TFR"),
        ("Clientèle", "Projets crypto promus sur réseaux sociaux (rug pull)", 3, 4, "Liste noire AMF, due diligence projets", "Tracfin cas 3"),
        ("Produits", "Privacy coins / mixeurs / tumblers", 3, 4, "Interdiction, analyse on-chain", "AMLR art. 79"),
        ("Produits", "NFT à valorisation spectaculaire", 3, 3, "Analyse de wash trading", "Tracfin cas 11"),
        ("Produits", "Wallets non hébergés (self-hosted)", 4, 3, "Vérification propriété au-delà de 1 000 €", "Règl. (UE) 2023/1113 art. 14"),
        ("Canaux", "Plateformes DeFi / bridges cross-chain", 3, 4, "Analyse blockchain, scoring des contreparties", "GAFI R.15"),
        ("Géographie", "CASP non régulés / pays sans Travel Rule", 3, 4, "Due diligence contreparties VASP", "TFR art. 19"),
        ("Opérations", "Micro-transactions vers wallets défavorablement connus", 3, 4, "Outils de blockchain analytics", "Tracfin cas 13"),
        ("Opérations", "Conversion rapide fiat→crypto→fiat", 4, 3, "Détection de rebonds, durée de détention", "ASR 2023 §4.2"),
        ("Dispositif", "Transition PSAN → CASP MiCA (fin régime transitoire 1er juil. 2026)", 3, 3, "Agrément CASP, mise à jour procédures", "MiCA art. 143"),
    ],
    "CHANGE": [
        ("Clientèle", "Clientèle occasionnelle et touristes", 4, 3, "Identification au-delà de seuils, cumul", "CMF R.561-10"),
        ("Produits", "Change de grosses coupures / devises à risque", 4, 3, "Seuils, justificatifs origine", "ASR 2023 §3.5"),
        ("Géographie", "Zones frontalières / Outre-mer", 3, 3, "Seuils adaptés", "ASR 2023 §2.2.4"),
        ("Opérations", "Opérations fractionnées sur plusieurs bureaux", 3, 3, "Agrégation multi-sites", "CMF L.561-15"),
        ("Opérations", "Change suivi d'un transport physique d'espèces", 3, 4, "Rappel obligation déclarative douane", "Règl. (UE) 2018/1672"),
    ],
    "ENTREPRISE": [
        ("Tiers", "Intermédiaires / agents commerciaux à l'international", 3, 4, "Évaluation des tiers, clauses anticorruption", "Loi Sapin II art. 17"),
        ("Tiers", "Fournisseurs dans des pays sous sanctions", 2, 4, "Filtrage sanctions des tiers, export control", "Règl. (UE) 833/2014; 2021/821"),
        ("Clientèle", "Clients en lien avec PPE / marchés publics", 3, 3, "Due diligence, registre cadeaux", "Sapin II; Tracfin cas 14"),
        ("Opérations", "Fraude au président / faux fournisseur (FOVI)", 4, 3, "Double validation, rappel contre-appel", "Bonnes pratiques Banque de France"),
        ("Opérations", "Facturation fictive / surfacturation", 3, 3, "Rapprochement commande/livraison", "Tracfin cas 10"),
        ("Opérations", "Détournement de subventions publiques", 3, 3, "Contrôle des aides perçues", "Tracfin cas 4 et 6"),
        ("Produits", "Biens à double usage / contournement de sanctions", 2, 4, "Classification douanière, contrôles de destination finale", "Règl. (UE) 2021/821"),
        ("Dispositif", "Absence de cartographie anticorruption", 3, 3, "Cartographie AFA, code de conduite", "Recommandations AFA 2020"),
    ],
}
rf_rows = []
for sec, items in RF.items():
    for i, (cat, fac, p, imp, ctrl, ref) in enumerate(items, 1):
        rf_rows.append([f"{sec}-{i:02d}", sec, cat, fac, p, imp, p * imp, ctrl, ref])
write("risk_factors.csv", ["id", "secteur", "categorie", "facteur", "probabilite", "impact", "risque_brut", "dispositif_attenuation", "reference"], rf_rows)

# Typologies d'entreprise (personnalisation)
typos = [
    ["BANQUE", "Banque de détail / réseau", "1.0", "Banque de détail, crédits"],
    ["BANQUE", "Banque privée / gestion de fortune", "1.25", "Gestion de fortune"],
    ["BANQUE", "Banque d'affaires / BFI", "1.1", "BFI, trade finance"],
    ["BANQUE", "Néobanque", "1.2", "Onboarding digital, cartes"],
    ["BANQUE", "Banque de financement d'entreprises en difficulté", "1.15", "Crédits, affacturage"],
    ["FINTECH", "Établissement de paiement (EP)", "1.1", "Comptes de paiement, virements"],
    ["FINTECH", "Établissement de monnaie électronique (EME)", "1.25", "ME, cartes prépayées"],
    ["FINTECH", "PSP / acquéreur e-commerce", "1.15", "Acquisition marchands"],
    ["FINTECH", "Agent de prestataire de services de paiement", "1.05", "Distribution"],
    ["FINTECH", "Plateforme de financement participatif", "1.1", "Crowdfunding"],
    ["ASSURANCE", "Assureur vie / capitalisation", "1.15", "Épargne"],
    ["ASSURANCE", "Assureur non-vie", "0.85", "IARD"],
    ["ASSURANCE", "Courtier / intermédiaire en assurance", "0.95", "Distribution"],
    ["JEUX", "Casino terrestre", "1.2", "Espèces"],
    ["JEUX", "Opérateur de jeux en ligne", "1.1", "Comptes joueurs"],
    ["JEUX", "Opérateur de paris sportifs / hippiques", "1.1", "Paris"],
    ["IMMOBILIER", "Agence immobilière", "1.0", "Transactions"],
    ["IMMOBILIER", "Marchand de biens / promoteur", "1.15", "Achat-revente"],
    ["IMMOBILIER", "Gestion locative / location saisonnière haut de gamme", "1.0", "Location"],
    ["TRANSFERT", "Société de transfert d'argent (MTO)", "1.25", "Transferts internationaux"],
    ["TRANSFERT", "Agent / sous-agent MTO", "1.15", "Encaissement espèces"],
    ["CRYPTO", "CASP – plateforme d'échange", "1.25", "Échange crypto-fiat"],
    ["CRYPTO", "CASP – conservation (custody)", "1.1", "Conservation"],
    ["CRYPTO", "Émetteur de jetons / stablecoins (EMT/ART)", "1.2", "Émission"],
    ["CHANGE", "Bureau de change manuel", "1.15", "Espèces"],
    ["ENTREPRISE", "PME exportatrice", "1.0", "Export"],
    ["ENTREPRISE", "Grand groupe international", "1.1", "Multi-pays"],
    ["ENTREPRISE", "Négociant en métaux précieux / art", "1.25", "Biens de valeur"],
]
write("company_typologies.csv", ["secteur", "typologie", "coefficient", "activite_principale"], typos)

# ---------------------------------------------------------------------------
# 5. TYPOLOGIES BC-FT (Tracfin 2023-2024 + compléments)
# ---------------------------------------------------------------------------
typologies = [
    ["T01", "Art", "Blanchiment par l'achat d'œuvres d'art aux enchères", "BANQUE;ENTREPRISE", "Difficulté d'identification des BE; modification du nom de l'acquéreur; paiement fractionné; incohérence valeur/surface financière", "Tracfin 2023-24 cas 1"],
    ["T02", "Trafic de stupéfiants", "Blanchiment du produit du trafic de stupéfiants", "BANQUE;JEUX;TRANSFERT", "Dépôts d'espèces importants; comptes à l'étranger non déclarés; gains de jeux fréquents; voyages payés pour des tiers", "Tracfin 2023-24 cas 2"],
    ["T03", "Cryptoactifs", "Rug pull scam (escroquerie au projet crypto)", "CRYPTO;BANQUE", "Promotion sur réseaux sociaux; cryptoactifs sur liste noire AMF; secteur blockchain/NFT", "Tracfin 2023-24 cas 3"],
    ["T04", "Détournement de fonds publics", "Détournement de fonds européens", "BANQUE;ENTREPRISE", "Sociétés sans activité réelle; opérations incohérentes avec l'objet social; centralisation sur compte tiers", "Tracfin 2023-24 cas 4"],
    ["T05", "Escroquerie", "Escroquerie à la défiscalisation Girardin (Outre-mer)", "BANQUE;ASSURANCE", "Versements « Girardin » ou depuis SNC; absence d'agrément fiscal; conseiller non immatriculé", "Tracfin 2023-24 cas 5"],
    ["T06", "Fraude aux finances publiques", "Fraude à MaPrimeRénov'", "BANQUE;ENTREPRISE", "Sociétés récentes sans salariés; absence RGE; aides publiques exclusives au crédit", "Tracfin 2023-24 cas 6"],
    ["T07", "Immobilier", "Montage de ventes à prix décotés", "IMMOBILIER;BANQUE", "Prix bas vs marché; absence de prêt; acquéreurs non-résidents; presse négative", "Tracfin 2023-24 cas 7"],
    ["T08", "Ingérence étrangère", "Trafic d'influence via association culturelle", "BANQUE;FINTECH", "Virements de tiers depuis l'étranger; présence de PPE; lien avec pays sous sanctions", "Tracfin 2023-24 cas 8"],
    ["T09", "Jeu", "Blanchiment par le jeu", "JEUX;BANQUE", "Mises en espèces; absence de ressources licites; mouvements internationaux", "Tracfin 2023-24 cas 9"],
    ["T10", "Manipulation de comptabilité", "Escroquerie à la technologie inexistante", "BANQUE;ENTREPRISE", "Factures à la matérialité incertaine; surévaluation d'actifs; faible masse salariale", "Tracfin 2023-24 cas 10"],
    ["T11", "NFT", "Fraude fiscale par l'utilisation de NFT", "CRYPTO;BANQUE", "Hausse spectaculaire de valeur d'un NFT; plus-value non déclarée", "Tracfin 2023-24 cas 11"],
    ["T12", "Opacification de l'origine des fonds", "Trust et fraude fiscale", "BANQUE;ASSURANCE", "Sociétés-écrans; pays liste grise GAFI; trust non enregistré au registre des fiducies", "Tracfin 2023-24 cas 12"],
    ["T13", "Pédocriminalité", "Cryptoactifs et exploitation sexuelle de mineurs", "CRYPTO;FINTECH;TRANSFERT", "Micro-montants < 50 € en crypto; comptes chez plusieurs PSAN; wallets défavorablement connus", "Tracfin 2023-24 cas 13"],
    ["T14", "Probité", "Prise illégale d'intérêt et corruption", "BANQUE;ENTREPRISE", "Délais courts d'appel d'offres; sous-traitance sans prestation; bénéficiaire titulaire de mandat public", "Tracfin 2023-24 cas 14"],
    ["T15", "Réseaux sociaux", "FT via rémunération d'influenceurs", "FINTECH;BANQUE", "Transferts vers réseau social; portefeuille ME; presse négative", "Tracfin 2023-24 cas 15"],
    ["T16", "Terrorisme", "FT via cagnotte en ligne", "FINTECH;BANQUE;TRANSFERT", "Changement de comportement; cagnotte par client idéologiquement marqué; envois vers zones sensibles", "Tracfin 2023-24 cas 16"],
    ["T17", "Trafic de stupéfiants", "Réseau de collecte par transferts de fonds", "TRANSFERT;FINTECH", "Plusieurs expéditeurs vers un collecteur; cartes prépayées multiples; absence de lien économique", "Tracfin 2023-24 cas 17"],
    ["T18", "Fraude", "Mules financières (comptes de passage)", "FINTECH;BANQUE", "Crédit puis débit immédiat; jeunes clients; device partagé; virements instantanés", "ASR 2023; Europol EMMA"],
    ["T19", "Sanctions", "Contournement des sanctions via pays tiers", "BANQUE;ENTREPRISE;TRANSFERT", "Réexportations via Turquie/Asie centrale/EAU; biens à double usage; sociétés récemment créées", "Règl. 833/2014 art. 12g; FinCEN/FCA alerts"],
    ["T20", "Fraude", "Fraude au président / faux IBAN fournisseur", "ENTREPRISE;BANQUE", "Changement d'IBAN; urgence; confidentialité; pays de destination inhabituel", "OSMP Banque de France"],
    ["T21", "Commerce", "Blanchiment commercial (TBML) – sur/sous-facturation", "BANQUE;ENTREPRISE", "Prix anormaux; marchandises incohérentes; tiers payeurs", "GAFI TBML 2020"],
    ["T22", "Assurance", "Rachat anticipé de contrat d'assurance-vie", "ASSURANCE", "Rachat précoce malgré pénalités; versement par un tiers; bénéficiaire sans lien", "ACPR lignes directrices"],
    ["T23", "Cryptoactifs", "Mixeurs, chain-hopping et bridges", "CRYPTO", "Passage par mixeurs; conversions rapides multi-chaînes; DEX", "GAFI VA 2025"],
    ["T24", "Corruption", "Corruption d'agent public étranger via intermédiaire", "ENTREPRISE;BANQUE", "Commissions élevées; sociétés offshore; intermédiaire sans substance", "OCDE; Sapin II"],
]
write("typologies.csv", ["id", "theme", "intitule", "secteurs", "criteres_alerte", "source"], typologies)

# ---------------------------------------------------------------------------
# 6. RÉGLEMENTATIONS (format du modèle « Regulations Tracking »)
# ---------------------------------------------------------------------------
regs = [
    ["REG001", "AMLR – Règlement (UE) 2024/1624 (règlement uniforme LCB-FT)", "LCB-FT", "Parlement européen / Conseil", "2027-07-10", "À venir", "Règles uniformes CDD, BE (25 %), PPE, plafond espèces 10 000 €, interdiction comptes anonymes, élargissement assujettis (football pro, biens de luxe)", "Fort", "Gap analysis, refonte procédures KYC/EDD, remédiation art. 26", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2024/1624/oj"],
    ["REG002", "AMLA – Règlement (UE) 2024/1620 (Autorité européenne LCB-FT)", "LCB-FT", "UE", "2024-06-26", "En vigueur", "Création de l'AMLA (Francfort) ; supervision directe de ~40 entités à partir de 2028 ; RTS/ITS CDD, scoring des risques", "Fort", "Suivi des RTS, préparation sélection supervision directe", "Responsable conformité", "2026-10-18", "https://www.amla.europa.eu"],
    ["REG003", "AMLD6 – Directive (UE) 2024/1640", "LCB-FT", "UE", "2027-07-10", "À venir", "Registres BE interconnectés, CRF, registres comptes bancaires, accès « intérêt légitime »", "Moyen", "Suivre la transposition française", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/dir/2024/1640/oj"],
    ["REG004", "TFR – Règlement (UE) 2023/1113 (Travel Rule)", "LCB-FT / Crypto", "UE", "2024-12-30", "En vigueur", "Informations donneur d'ordre/bénéficiaire pour virements et transferts de crypto-actifs, wallets non hébergés > 1 000 €", "Fort", "Contrôle complétude des messages, procédure données manquantes", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2023/1113/oj"],
    ["REG005", "MiCA – Règlement (UE) 2023/1114", "Crypto", "UE / AMF", "2024-12-30", "En vigueur", "Agrément CASP ; fin du régime transitoire PSAN en France au 1er juillet 2026", "Fort", "Agrément CASP, gouvernance, LCB-FT", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2023/1114/oj"],
    ["REG006", "Règlement paiements instantanés (UE) 2024/886", "Paiements", "UE", "2025-10-09", "En vigueur", "Vérification du bénéficiaire (VoP) et filtrage sanctions quotidien au lieu du filtrage transactionnel", "Fort", "Filtrage quotidien de la base clients, VoP", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2024/886/oj"],
    ["REG007", "Arrêté du 6 janvier 2021 – dispositif de contrôle interne LCB-FT et gel", "LCB-FT", "Ministère de l'Économie", "2021-03-01", "En vigueur", "Classification des risques, procédures, contrôle interne, gel des avoirs", "Fort", "Mise à jour annuelle de la classification", "Responsable conformité", "2026-10-18", "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042907870"],
    ["REG008", "CMF – articles L.561-1 et s. / L.562-1 et s.", "LCB-FT", "France", "2016-12-01", "En vigueur", "Obligations de vigilance, déclaration de soupçon, gel des avoirs", "Fort", "Veille sur ordonnance de transposition AMLD6", "Responsable conformité", "2026-10-18", "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006072026/LEGISCTA000006154119/"],
    ["REG009", "Règlement délégué (UE) 2016/1675 modifié (2026/46 et 2026/83)", "LCB-FT", "Commission européenne", "2026-01-29", "En vigueur", "Liste UE des pays tiers à haut risque : ajout Bolivie, Îles Vierges britanniques, Russie ; retrait Burkina Faso, Mali, Mozambique, Nigeria, Afrique du Sud, Tanzanie", "Fort", "Mettre à jour le référentiel pays et les scénarios", "Responsable conformité", "2026-10-18", "https://finance.ec.europa.eu/financial-crime/anti-money-laundering-and-countering-financing-terrorism-international-level_en"],
    ["REG010", "GAFI – Plénière juin 2026", "LCB-FT", "GAFI", "2026-06-19", "En vigueur", "Liste grise : ajout Bosnie-Herzégovine et Irak ; retrait Algérie et Namibie (22 juridictions). Liste noire inchangée : Corée du Nord, Iran, Myanmar. R.6 révisée (exemptions humanitaires)", "Fort", "Mettre à jour le référentiel pays ; prochaine plénière octobre 2026", "Responsable conformité", "2026-10-18", "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html"],
    ["REG011", "GAFI – Recommandation 16 révisée (transparence des paiements)", "Paiements", "GAFI", "2030-12-31", "À venir", "Informations harmonisées sur les virements transfrontaliers, cartes et paiements, alignement nom/compte bénéficiaire", "Moyen", "Feuille de route ISO 20022, données structurées", "Responsable conformité", "2026-10-18", "https://www.fatf-gafi.org"],
    ["REG012", "DORA – Règlement (UE) 2022/2554", "Résilience opérationnelle", "UE", "2025-01-17", "En vigueur", "Gestion des risques TIC, prestataires critiques, incidents", "Moyen", "Registre d'information, tests", "RSSI", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2022/2554/oj"],
    ["REG013", "Loi Sapin II – programme anticorruption", "Anticorruption", "AFA", "2016-12-09", "En vigueur", "8 piliers : code de conduite, cartographie, évaluation des tiers, contrôles comptables, formation, alerte, sanctions, contrôle interne", "Moyen", "Cartographie anticorruption", "Responsable conformité", "2026-10-18", "https://www.agence-francaise-anticorruption.gouv.fr"],
    ["REG014", "RGPD – Règlement (UE) 2016/679", "Protection des données", "CNIL", "2018-05-25", "En vigueur", "Base légale des traitements LCB-FT, durées de conservation 5 ans", "Moyen", "Registre des traitements, AIPD filtrage", "DPO", "2026-10-18", "https://www.cnil.fr"],
    ["REG015", "AI Act – Règlement (UE) 2024/1689", "IA", "UE", "2026-08-02", "En vigueur", "Obligations pour systèmes d'IA à haut risque (dont scoring crédit) ; gouvernance des modèles LCB-FT", "Moyen", "Inventaire modèles IA, documentation, supervision humaine", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"],
    ["REG016", "PSD3 / PSR – paquet services de paiement", "Paiements", "UE", "2028-01-01", "À venir", "Lutte contre la fraude (partage d'informations, responsabilité usurpation), accès aux comptes", "Moyen", "Suivi trilogue / publication", "Responsable conformité", "2026-10-18", "https://finance.ec.europa.eu"],
    ["REG017", "Plafond paiements en espèces 10 000 € (AMLR art. 80)", "LCB-FT", "UE", "2027-07-10", "À venir", "Interdiction des paiements en espèces > 10 000 € (seuil national français plus bas maintenu : 1 000 €)", "Moyen", "Adapter seuils et contrôles", "Responsable conformité", "2026-10-18", "https://eur-lex.europa.eu/eli/reg/2024/1624/oj"],
]
write("regulations.csv", ["Identifiant unique", "Nom/titre de la réglementation", "Domaine concerné", "Source (autorité émettrice)",
                          "Date d'entrée en vigueur", "Statut", "Résumé des points clés", "Impact sur l'entreprise",
                          "Actions requises", "Responsable du suivi", "Date de dernière mise à jour", "Lien vers le texte intégral"], regs)

# ---------------------------------------------------------------------------
# 7. JURISPRUDENCE & SANCTIONS
# ---------------------------------------------------------------------------
juris = [
    ["J001", "2025-06-19", "ACPR – Commission des sanctions", "Banque Delubac & Cie (proc. 2024-02)", "France", "Blâme + 600 000 €",
     "Outil de surveillance ne tenant pas compte du profil financier ; 27 056 alertes en stock dont >25 % de plus de 4 mois ; surveillance pays GAFI limitée aux déclarations initiales ; vigilance renforcée PPE défaillante ; examens renforcés en retard ; 30 défauts de DS",
     "Calibrer les scénarios sur revenus/patrimoine/CA ; piloter les stocks d'alertes ; surveiller les flux pays effectifs ; tracer examens renforcés et DS", "BANQUE"],
    ["J002", "2022-11-22", "CJUE (C-37/20 et C-601/20, WM et Sovim)", "Registres des bénéficiaires effectifs", "UE", "Invalidation de l'accès public",
     "L'accès du grand public aux registres des BE porte une atteinte disproportionnée à la vie privée", "AMLD6 : accès fondé sur l'intérêt légitime ; adapter les sources de vérification BE", "TOUS"],
    ["J003", "2023-11-21", "DOJ / FinCEN / OFAC (États-Unis)", "Binance", "États-Unis", "≈ 4,3 Md$",
     "Défaut de programme AML, absence d'enregistrement MSB, violations de sanctions", "Gouvernance LCB-FT des plateformes crypto ; filtrage sanctions des utilisateurs", "CRYPTO"],
    ["J004", "2024-10-10", "DOJ / FinCEN / OCC (États-Unis)", "TD Bank", "États-Unis", "≈ 3 Md$",
     "Surveillance transactionnelle défaillante ayant permis le blanchiment de centaines de millions", "Couverture des scénarios, ressources de traitement, culture de conformité", "BANQUE"],
    ["J005", "2022-12-13", "DOJ (États-Unis)", "Danske Bank (succursale Estonie)", "Danemark/Estonie", "≈ 2 Md$",
     "Flux non-résidents à haut risque via la succursale estonienne", "Pilotage groupe des succursales, clientèle non-résidente", "BANQUE"],
    ["J006", "2021-04-19", "Parquet néerlandais", "ABN AMRO", "Pays-Bas", "480 M€ (transaction)",
     "Défaillances structurelles de CDD et de surveillance", "Remédiation KYC du stock clients", "BANQUE"],
    ["J007", "2018-09-04", "Parquet néerlandais", "ING", "Pays-Bas", "775 M€ (transaction)",
     "Comptes utilisés pour le blanchiment faute de vigilance", "Contrôle des comptes professionnels, scénarios", "BANQUE"],
    ["J008", "2024-10-02", "FCA (Royaume-Uni)", "Starling Bank", "Royaume-Uni", "≈ 29 M£",
     "Contrôles de criminalité financière insuffisants face à la croissance ; filtrage sanctions incomplet", "Faire croître le dispositif au rythme du business (fintech)", "FINTECH"],
    ["J009", "2017-12-21", "ACPR – Commission des sanctions", "BNP Paribas", "France", "Blâme + 10 M€",
     "Manquements au dispositif LCB-FT (procédures, DS, vigilance)", "Revue des procédures et du processus déclaratif", "BANQUE"],
    ["J010", "2017-07-19", "ACPR – Commission des sanctions", "Société Générale", "France", "Blâme + 5 M€",
     "Manquements en matière de dispositif LCB-FT et de déclarations de soupçon", "Qualité et délai des DS", "BANQUE"],
]
write("jurisprudence.csv", ["id", "date", "autorite", "entite", "juridiction", "sanction", "manquements", "enseignements", "secteur"], juris)

# ---------------------------------------------------------------------------
# 8. PPE – fonctions publiques importantes (JOUE C/2023/724 + catégories GAFI)
# ---------------------------------------------------------------------------
pep_fr = [
    "Président de la République", "Premier ministre", "Membres du Gouvernement", "Président du Sénat",
    "Président de l'Assemblée nationale", "Députés et sénateurs", "Dirigeants des partis ou groupements politiques",
    "Président et membres du Conseil constitutionnel", "Membres du Conseil d'État (fonctions juridictionnelles)",
    "Magistrats de la Cour des comptes", "Membres de la Cour de cassation",
    "Secrétaire général du Conseil constitutionnel", "Membres du Conseil général de la Banque de France",
    "Ambassadeurs et chargés d'affaires", "Chef d'état-major des armées et chefs d'état-major des armées",
    "Dirigeants d'entreprises publiques (DG, DGD, directoire, CA)", "Dirigeants de sociétés > 50 M€ de CA détenues majoritairement par des collectivités",
]
generic = [
    ("Chef d'État / de gouvernement", "Très élevé"), ("Ministre / secrétaire d'État", "Très élevé"),
    ("Parlementaire", "Élevé"), ("Membre d'une cour suprême / constitutionnelle", "Élevé"),
    ("Dirigeant de banque centrale", "Élevé"), ("Ambassadeur / officier supérieur des armées", "Élevé"),
    ("Dirigeant d'entreprise publique", "Élevé"), ("Dirigeant de parti politique", "Élevé"),
    ("Dirigeant d'organisation internationale", "Modéré"),
    ("Membre de la famille d'une PPE", "Selon PPE"), ("Personne étroitement associée à une PPE", "Selon PPE"),
    ("Élu régional / maire > 50 000 hab. (AMLR art. 2)", "Modéré"),
]
pep_rows = [["FRA", "France", "Nationale (JOUE C/2023/724)", f, "Élevé"] for f in pep_fr]
pep_rows += [["*", "Tous pays", "Catégorie GAFI / AMLR", g, r] for g, r in generic]
write("pep_functions.csv", ["iso3", "pays", "source", "fonction", "niveau_risque"], pep_rows)

# Registre de surveillance PPE (fictif, pour démo)
rng = random.Random(42)
first = ["Camille", "Jean", "Aminata", "Pierre", "Fatou", "Lucas", "Nadia", "Rafael", "Olga", "Kwame", "Sofia", "Marc"]
last = ["Durand", "Mbeki", "Joseph", "Martin", "Diallo", "Lefèvre", "Haddad", "Silva", "Ivanova", "Mensah", "Rossi", "Pierre-Louis"]
funcs = [g[0] for g in generic]
cty = [r for r in country_rows]
pep_watch = []
for i in range(1, 31):
    c = rng.choice(cty)
    f = rng.choice(funcs)
    start = date(2026, 10, 18) - timedelta(days=rng.randint(30, 900))
    pep_watch.append([f"PPE-{i:03d}", f"{rng.choice(first)} {rng.choice(last)} (fictif)", c[0], c[1], f,
                      rng.choice(["En fonction", "Ancienne PPE (< 12 mois)", "Ancienne PPE (> 12 mois)"]),
                      start.isoformat(), (start + timedelta(days=365)).isoformat(), c[13],
                      rng.choice(["Client actif", "Prospect", "Bénéficiaire effectif"])])
write("pep_watchlist.csv", ["id", "nom", "iso3", "pays", "fonction", "statut", "date_identification", "prochaine_revue",
                            "risque_pays_ppe", "relation"], pep_watch)

# ---------------------------------------------------------------------------
# 9. KYC – pièces par typologie de client
# ---------------------------------------------------------------------------
kyc = []
def k(t, piece, niveau, ref):
    kyc.append([t, piece, niveau, ref])
for t in ["Personne physique résidente", "Personne physique non-résidente", "Mineur / majeur protégé", "Entrepreneur individuel / profession libérale"]:
    k(t, "Pièce d'identité officielle en cours de validité avec photo", "Standard", "CMF R.561-5")
    k(t, "Justificatif de domicile < 3 mois", "Standard", "Bonnes pratiques ACPR")
    k(t, "Profession, revenus et patrimoine estimés", "Standard", "CMF R.561-12")
    k(t, "Objet et nature envisagée de la relation d'affaires", "Standard", "CMF L.561-5-1")
    k(t, "Filtrage PPE / sanctions / presse négative", "Standard", "CMF L.561-10; L.562-4-1")
    k(t, "Justificatif d'origine des fonds (au-delà des seuils internes)", "Renforcée", "CMF L.561-10-2")
    k(t, "Justificatif d'origine du patrimoine", "Renforcée", "AMLR art. 34")
    k(t, "Second document d'identité / vérification indépendante", "Renforcée", "CMF R.561-5-2")
k("Personne physique non-résidente", "Justificatif de résidence fiscale / NIF", "Standard", "CRS/FATCA")
k("Mineur / majeur protégé", "Jugement de tutelle/curatelle ou livret de famille", "Standard", "Code civil")
k("Mineur / majeur protégé", "Identité du représentant légal", "Standard", "CMF R.561-5")
k("Entrepreneur individuel / profession libérale", "Extrait INSEE/RNE ou inscription à l'ordre", "Standard", "CMF R.561-5")
for t in ["Société commerciale (SAS, SARL, SA)", "Société cotée", "Société civile / SCI", "Association / fondation / fonds de dotation", "Trust / fiducie / construction juridique", "Personne morale étrangère"]:
    k(t, "Extrait Kbis < 3 mois ou équivalent étranger", "Standard", "CMF R.561-5")
    k(t, "Statuts certifiés conformes", "Standard", "CMF R.561-5")
    k(t, "Identité et pouvoirs du représentant légal", "Standard", "CMF R.561-5")
    k(t, "Identification des bénéficiaires effectifs (≥ 25 % ou contrôle) + RBE", "Standard", "CMF R.561-1; AMLR art. 51")
    k(t, "Organigramme de détention jusqu'aux personnes physiques", "Standard", "AMLR art. 52")
    k(t, "Activité, chiffre d'affaires, pays d'activité, principaux partenaires", "Standard", "CMF R.561-12")
    k(t, "Derniers comptes annuels / liasse fiscale", "Renforcée", "Bonnes pratiques")
    k(t, "Origine des fonds et cohérence des flux attendus", "Renforcée", "CMF L.561-10-2")
    k(t, "Visite sur site / entretien avec le dirigeant", "Renforcée", "Bonnes pratiques")
k("Société cotée", "Preuve de cotation sur marché réglementé (vigilance simplifiée possible)", "Simplifiée", "CMF R.561-15")
k("Association / fondation / fonds de dotation", "Récépissé de déclaration en préfecture / JOAFE", "Standard", "Loi 1901")
k("Association / fondation / fonds de dotation", "Liste des dirigeants et principaux donateurs/bénéficiaires", "Renforcée", "GAFI R.8")
k("Trust / fiducie / construction juridique", "Acte constitutif, constituant, fiduciaire, bénéficiaires, protecteur", "Standard", "CMF R.561-3-0")
k("Trust / fiducie / construction juridique", "Enregistrement au registre des fiducies / trusts", "Standard", "CGI 1649 AB")
k("Personne morale étrangère", "Traduction certifiée et apostille des documents", "Standard", "Bonnes pratiques")
for t in ["PSAN / CASP (contrepartie)", "Établissement de paiement / EME (contrepartie)"]:
    k(t, "Agrément / enregistrement (AMF, ACPR, REGAFI)", "Standard", "MiCA; CMF L.522-6")
    k(t, "Questionnaire LCB-FT (type Wolfsberg CBDDQ)", "Standard", "CMF L.561-10-3")
    k(t, "Politique Travel Rule et outil blockchain analytics", "Renforcée", "Règl. (UE) 2023/1113")
k("PPE (tout type)", "Accord d'un membre de la direction pour l'entrée en relation", "Renforcée", "CMF R.561-20-2; AMLR art. 42")
k("PPE (tout type)", "Origine du patrimoine et des fonds", "Renforcée", "AMLR art. 42")
k("PPE (tout type)", "Surveillance renforcée continue + revue annuelle", "Renforcée", "AMLR art. 42")
write("kyc_requirements.csv", ["type_client", "piece", "niveau_vigilance", "reference"], kyc)

# ---------------------------------------------------------------------------
# 10. FRAUDE PAR SECTEUR
# ---------------------------------------------------------------------------
fraud = [
    ["FINTECH", "Fraude à l'authentification / ATO", "Changement d'appareil + ajout bénéficiaire + virement max", "Authentification forte, délai sur nouveau bénéficiaire"],
    ["FINTECH", "Fraude au faux conseiller bancaire", "Virements instantanés vers néocomptes, appel en cours", "Messages d'alerte, VoP, délais"],
    ["FINTECH", "Chargeback / friendly fraud", "Taux de rétrofacturation > 1 %", "Monitoring marchand, 3DS"],
    ["BANQUE", "Fraude documentaire au crédit", "Bulletins de salaire falsifiés, IBAN récents", "Contrôle documentaire automatisé"],
    ["BANQUE", "Fraude au chèque", "Chèques volés/falsifiés déposés sur comptes récents", "Délai d'indisponibilité, FNCI"],
    ["ASSURANCE", "Sinistres fictifs ou majorés", "Déclarations répétées, factures non conformes", "Scoring sinistres, expertise"],
    ["ASSURANCE", "Usurpation de bénéficiaire", "Changement de clause bénéficiaire tardif", "Vérification identité au dénouement"],
    ["JEUX", "Matchs truqués", "Mises massives sur événements mineurs", "Monitoring intégrité, ANJ"],
    ["JEUX", "Bonus abuse / multi-comptes", "Même appareil/IP sur plusieurs comptes", "Device fingerprinting"],
    ["IMMOBILIER", "Fraude au virement de l'acompte (FOVI notaire)", "Changement d'IBAN par mail", "Contre-appel, IBAN sécurisé"],
    ["IMMOBILIER", "Faux mandats / vente par non-propriétaire", "Propriétaire injoignable, urgence", "Vérification titre de propriété"],
    ["TRANSFERT", "Arnaques sentimentales / romance scam", "Envois répétés de personnes âgées vers l'étranger", "Questionnaire anti-arnaque, refus"],
    ["TRANSFERT", "Complicité d'agent", "Agent avec volumes anormaux, fractionnement", "Audit et scoring des agents"],
    ["CRYPTO", "Pig butchering / faux investissements", "Dépôts croissants vers plateforme inconnue", "Alertes clients, analyse on-chain"],
    ["CRYPTO", "Piratage de comptes / SIM swap", "Changement de numéro + retrait total", "2FA hors SMS, délai de retrait"],
    ["ENTREPRISE", "Fraude au président", "Demande urgente et confidentielle de virement international", "Double signature, procédure de rappel"],
    ["ENTREPRISE", "Faux fournisseur / changement d'IBAN", "Nouvel IBAN dans un pays différent", "Vérification indépendante du RIB"],
    ["CHANGE", "Faux billets", "Coupures neuves en série", "Détecteurs, formation"],
]
write("fraud_scenarios.csv", ["secteur", "fraude", "indicateurs", "controles"], fraud)

# ---------------------------------------------------------------------------
# 11. FORMATION – banque de questions
# ---------------------------------------------------------------------------
Q = [
    ("Fondamentaux LCB-FT", "Quelles sont les trois étapes classiques du blanchiment ?", "Placement, empilement, intégration", "Collecte, transfert, retrait|Dépôt, conversion, retrait|Identification, vérification, déclaration"),
    ("Fondamentaux LCB-FT", "À quelle autorité la déclaration de soupçon est-elle adressée en France ?", "Tracfin", "ACPR|AMF|Procureur de la République"),
    ("Fondamentaux LCB-FT", "Le client peut-il être informé de l'envoi d'une déclaration de soupçon ?", "Non, c'est interdit (tipping-off)", "Oui, systématiquement|Oui, s'il le demande|Oui, après 30 jours"),
    ("Fondamentaux LCB-FT", "Durée de conservation des documents KYC après la fin de la relation ?", "5 ans", "1 an|3 ans|10 ans"),
    ("Fondamentaux LCB-FT", "Selon l'ASR 2023 de l'ACPR, quel est le niveau de risque de la transmission de fonds ?", "Très élevé", "Faible|Modéré|Élevé"),
    ("KYC / CDD", "Seuil de détention définissant le bénéficiaire effectif d'une société ?", "Plus de 25 % du capital ou des droits de vote, ou contrôle", "Plus de 10 %|Plus de 50 %|Plus de 33 %"),
    ("KYC / CDD", "Que faire si l'identification du client est impossible ?", "Ne pas entrer en relation et envisager une DS", "Ouvrir le compte en mode dégradé|Demander un délai de 6 mois|Ouvrir avec un plafond"),
    ("KYC / CDD", "L'AMLR (art. 26) impose pour le stock clients existants :", "Une remédiation fondée sur les risques, prioritairement les clients à haut risque", "Aucune action|Une clôture des comptes anciens|Une revue tous les 10 ans"),
    ("KYC / CDD", "Quand l'AMLR devient-il applicable ?", "10 juillet 2027", "1er janvier 2026|10 juillet 2025|1er janvier 2030"),
    ("PPE", "Une PPE l'est-elle encore après la fin de ses fonctions ?", "Oui, au moins 12 mois après la cessation des fonctions", "Non, immédiatement plus|Oui, 3 mois|Oui, à vie systématiquement"),
    ("PPE", "Qui doit autoriser l'entrée en relation avec une PPE ?", "Un membre de la direction (senior management)", "Le chargé de clientèle seul|Tracfin|Le client lui-même"),
    ("PPE", "Quelle publication liste les fonctions PPE nationales des États membres ?", "Communication de la Commission au JOUE (C/2023/724)", "Le rapport annuel Tracfin|La liste GAFI|Le registre RBE"),
    ("Sanctions & gel", "Quelle autorité française publie le registre national des gels ?", "La DG Trésor", "L'ACPR|La Banque de France|Le ministère de l'Intérieur"),
    ("Sanctions & gel", "Pays inscrits sur la liste noire du GAFI (juin 2026) ?", "Corée du Nord, Iran, Myanmar", "Russie, Syrie, Cuba|Iran, Venezuela, Haïti|Afghanistan, Yémen, Libye"),
    ("Sanctions & gel", "Le règlement (UE) 2024/886 impose pour les paiements instantanés :", "Un filtrage quotidien des clients contre les listes de gel", "Aucun filtrage|Un filtrage mensuel|Un filtrage uniquement à l'entrée en relation"),
    ("Sanctions & gel", "Quels pays ont été ajoutés à la liste grise GAFI en juin 2026 ?", "Bosnie-Herzégovine et Irak", "Algérie et Namibie|Monaco et Bulgarie|Kenya et Liban"),
    ("Surveillance & DS", "Dans la décision Delubac (2025), quel était le stock d'alertes non traitées ?", "Plus de 27 000 alertes", "Environ 500|Environ 2 000|Aucune"),
    ("Surveillance & DS", "La surveillance des liens avec les pays à risque doit porter sur :", "Les opérations effectivement réalisées, pas seulement les déclarations initiales", "Uniquement les déclarations à l'entrée en relation|Uniquement les clients étrangers|Uniquement les espèces"),
    ("Surveillance & DS", "Une DS doit être envoyée :", "Préalablement à l'exécution de l'opération, sauf impossibilité", "Uniquement après clôture du compte|Une fois par an|Sur demande du client"),
    ("Crypto-actifs", "Au-delà de quel montant le CASP doit-il vérifier la propriété d'un wallet non hébergé ?", "1 000 €", "100 €|10 000 €|15 000 €"),
    ("Crypto-actifs", "Date de fin du régime transitoire PSAN en France vers l'agrément MiCA ?", "1er juillet 2026", "30 décembre 2024|1er janvier 2028|10 juillet 2027"),
    ("Crypto-actifs", "Un indicateur Tracfin pour l'exploitation sexuelle de mineurs via crypto :", "Montants faibles (< 50 €) vers des wallets défavorablement connus", "Gros virements SEPA|Achat d'immobilier|Assurance-vie"),
    ("Fraude", "Indicateur typique d'une mule financière :", "Crédit suivi d'un débit quasi immédiat vers des tiers", "Épargne régulière|Prélèvements de loyer|Salaire stable"),
    ("Fraude", "Meilleure parade à la fraude au faux fournisseur :", "Contre-appel sur un numéro connu avant tout changement d'IBAN", "Payer plus vite|Accepter les IBAN par mail|Supprimer la double validation"),
    ("Jeux & hasard", "Indicateur de blanchiment par le jeu (Tracfin cas 9) :", "Mises en espèces sans ressources licites identifiées", "Mises faibles régulières|Gains déclarés au fisc|Paiement par carte du joueur"),
    ("Immobilier", "Indicateur Tracfin dans l'immobilier (cas 7) :", "Prix de vente bas vs marché et absence de prêt bancaire", "Recours à un notaire|Diagnostic énergétique|Bien en résidence principale"),
    ("Assurance", "Indicateur de risque en assurance-vie :", "Rachat anticipé malgré pénalités, versement par un tiers", "Versements programmés|Clause bénéficiaire standard|Contrat de 15 ans"),
    ("AMLR / AMLA", "Où siège l'AMLA ?", "Francfort", "Paris|Bruxelles|Luxembourg"),
    ("AMLR / AMLA", "Combien d'entités l'AMLA supervisera-t-elle directement (à partir de 2028) ?", "Environ 40", "Environ 400|Toutes les banques|Aucune"),
    ("AMLR / AMLA", "Plafond européen des paiements en espèces prévu par l'AMLR ?", "10 000 €", "1 000 €|5 000 €|15 000 €"),
]
qrows = [[f"Q{i:03d}", m, q, a, d] for i, (m, q, a, d) in enumerate(Q, 1)]
write("quiz_bank.csv", ["id", "module", "question", "bonne_reponse", "distracteurs"], qrows)

# ---------------------------------------------------------------------------
# 12. SOURCES D'ACTUALITÉ & ARTICLES
# ---------------------------------------------------------------------------
feeds = [
    ["LCB-FT France", "https://news.google.com/rss/search?q=LCB-FT+OR+blanchiment+OR+Tracfin&hl=fr&gl=FR&ceid=FR:fr", "fr"],
    ["AMLA / AMLR", "https://news.google.com/rss/search?q=AMLA+OR+AMLR+anti-money+laundering+EU&hl=en&gl=US&ceid=US:en", "en"],
    ["Sanctions", "https://news.google.com/rss/search?q=sanctions+OFAC+OR+%22EU+sanctions%22&hl=en&gl=US&ceid=US:en", "en"],
    ["GAFI / FATF", "https://news.google.com/rss/search?q=FATF+OR+GAFI+grey+list&hl=en&gl=US&ceid=US:en", "en"],
    ["Fraude & crypto", "https://news.google.com/rss/search?q=crypto+money+laundering+OR+fraude+crypto&hl=fr&gl=FR&ceid=FR:fr", "fr"],
    ["ACPR sanctions", "https://news.google.com/rss/search?q=ACPR+commission+des+sanctions&hl=fr&gl=FR&ceid=FR:fr", "fr"],
]
write("news_feeds.csv", ["theme", "url", "langue"], feeds)

articles = [
    ["GAFI – Listes noire et grise", "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html", "Juridictions sous surveillance renforcée et appels à l'action, mises à jour à chaque plénière.", "Pays à risque"],
    ["AMLA – Autorité européenne LCB-FT", "https://www.amla.europa.eu", "Site officiel de l'AMLA : consultations, RTS/ITS, calendrier de supervision directe.", "Réglementation"],
    ["AMLR – Règlement (UE) 2024/1624", "https://eur-lex.europa.eu/eli/reg/2024/1624/oj", "Texte intégral du règlement uniforme LCB-FT applicable au 10 juillet 2027.", "Réglementation"],
    ["ACPR – LCB-FT", "https://acpr.banque-france.fr/fr/controler/lutte-contre-le-blanchiment-de-capitaux-et-le-financement-du-terrorisme", "Lignes directrices, analyses sectorielles et décisions de la Commission des sanctions.", "Superviseur"],
    ["Tracfin – Publications", "https://www.economie.gouv.fr/tracfin/publications", "Rapports annuels, état de la menace et lettres d'information aux déclarants.", "Typologies"],
    ["DG Trésor – Registre national des gels", "https://gels-avoirs.dgtresor.gouv.fr", "Registre consolidé des personnes et entités faisant l'objet d'un gel en France.", "Sanctions"],
    ["Carte des sanctions de l'UE", "https://www.sanctionsmap.eu", "Visualisation des régimes de mesures restrictives de l'UE par pays.", "Sanctions"],
    ["OFAC – Sanctions List Search", "https://sanctionssearch.ofac.treas.gov", "Recherche dans la liste SDN et autres listes américaines.", "Sanctions"],
    ["ONU – Liste consolidée du Conseil de sécurité", "https://main.un.org/securitycouncil/fr/content/un-sc-consolidated-list", "Liste consolidée des sanctions du Conseil de sécurité.", "Sanctions"],
    ["OpenSanctions", "https://www.opensanctions.org", "Base ouverte de sanctions, PPE et entités d'intérêt (données consolidées).", "Données"],
    ["Basel AML Index", "https://index.baselgovernance.org", "Classement annuel des risques de blanchiment par pays.", "Pays à risque"],
    ["Transparency International – IPC", "https://www.transparency.org/en/cpi", "Indice de perception de la corruption par pays.", "Corruption"],
    ["Europol – IOCTA / criminalité financière", "https://www.europol.europa.eu/crime-areas/economic-crime/money-laundering", "Analyses Europol sur le blanchiment et la criminalité organisée.", "Menace"],
    ["EBA – Lignes directrices LCB-FT", "https://www.eba.europa.eu/regulation-and-policy/anti-money-laundering-and-countering-financing-terrorism", "Orientations facteurs de risque, de-risking, accès aux services.", "Réglementation"],
    ["ICIJ – Enquêtes", "https://www.icij.org/investigations/", "Enquêtes internationales (Pandora, FinCEN Files) utiles pour la presse négative.", "Presse négative"],
    ["OCCRP", "https://www.occrp.org/en", "Journalisme d'investigation sur la corruption et le crime organisé.", "Presse négative"],
    ["AFA – Agence française anticorruption", "https://www.agence-francaise-anticorruption.gouv.fr", "Recommandations Sapin II, guides et contrôles.", "Anticorruption"],
    ["ANJ – Autorité nationale des jeux", "https://anj.fr", "Cadre LCB-FT des opérateurs de jeux.", "Jeux"],
]
write("articles.csv", ["titre", "url", "description", "categorie"], articles)

# ---------------------------------------------------------------------------
# 13. DONNÉES D'ENTRAÎNEMENT ML (synthétiques, reproductibles)
# ---------------------------------------------------------------------------
np.random.seed(7)
N = 4000
iso_list = [r[0] for r in country_rows]
idx_map = {r[0]: r[11] for r in country_rows}
sec_codes = [s[0] for s in sectors]
sec_risk = {"BANQUE": 2, "FINTECH": 3, "ASSURANCE": 1, "JEUX": 3, "IMMOBILIER": 3, "TRANSFERT": 4, "CRYPTO": 4, "CHANGE": 3, "ENTREPRISE": 2}
client_types = ["PP", "PM", "TRUST", "ASSO"]
rows = []
for i in range(N):
    iso = np.random.choice(iso_list, p=None)
    sec = np.random.choice(sec_codes)
    ctype = np.random.choice(client_types, p=[0.6, 0.3, 0.04, 0.06])
    pep = int(np.random.rand() < 0.05)
    adverse = int(np.random.poisson(0.25))
    cash = round(float(np.clip(np.random.beta(1.5, 5), 0, 1)), 3)
    nonface = int(np.random.rand() < 0.45)
    layers = int(np.random.choice([0, 1, 2, 3, 4], p=[0.55, 0.25, 0.1, 0.06, 0.04])) if ctype != "PP" else 0
    tx_month = int(np.random.lognormal(3, 1))
    avg_amt = float(round(np.random.lognormal(6.5, 1.3), 2))
    hrc_share = round(float(np.clip(np.random.beta(1, 8) + (0.4 if idx_map[iso] < 40 else 0), 0, 1)), 3)
    age_rel = int(np.random.randint(0, 240))
    country_risk = round(100 - idx_map[iso], 1)
    z = (-5.2 + 0.045 * country_risk + 2.2 * pep + 0.9 * adverse + 2.5 * cash + 0.5 * nonface + 0.55 * layers
         + 0.45 * sec_risk[sec] + 2.0 * hrc_share - 0.004 * age_rel + 0.25 * (ctype == "TRUST") + 0.0001 * avg_amt)
    p = 1 / (1 + np.exp(-z))
    label = int(np.random.rand() < p)
    rows.append([f"C{i:05d}", ctype, sec, iso, country_risk, pep, adverse, cash, nonface, layers, tx_month, avg_amt, hrc_share, age_rel, label])
write("training_clients.csv", ["client_id", "type_client", "secteur", "pays", "risque_pays", "ppe", "presse_negative",
                               "part_especes", "distance", "niveaux_detention", "nb_tx_mois", "montant_moyen",
                               "part_flux_pays_risque", "anciennete_mois", "suspect"], rows)

# Transactions de démonstration (surveillance)
tx = []
start = date(2026, 9, 1)
clients = [f"CL{i:04d}" for i in range(1, 121)]
for i in range(1500):
    c = rng.choice(clients)
    d = start + timedelta(days=rng.randint(0, 46))
    typ = rng.choice(["Virement SEPA", "Virement international", "Dépôt espèces", "Retrait espèces", "Carte", "Virement instantané", "Crypto on-ramp"])
    amt = round(abs(np.random.lognormal(5.8, 1.2)), 2)
    cty = rng.choice(["FRA"] * 12 + ["DEU", "BEL", "ESP", "HTI", "CMR", "ARE", "TUR", "CHN", "SEN", "CIV", "VNM", "GBR"])
    tx.append([f"TX{i:05d}", c, d.isoformat(), typ, amt, cty, rng.choice(["Débit", "Crédit"])])
# Injection de schémas suspects
for j in range(25):
    c = "CL0007"
    d = start + timedelta(days=j)
    tx.append([f"TXS{j:03d}", c, d.isoformat(), "Dépôt espèces", round(rng.uniform(8500, 9900), 2), "FRA", "Crédit"])
for j in range(12):
    d = start + timedelta(days=3 * j)
    tx.append([f"TXM{j:03d}", "CL0042", d.isoformat(), "Virement instantané", round(rng.uniform(1500, 4900), 2), "FRA", "Crédit"])
    tx.append([f"TXN{j:03d}", "CL0042", d.isoformat(), "Virement international", round(rng.uniform(1400, 4800), 2), "CMR", "Débit"])
for j in range(6):
    tx.append([f"TXR{j:03d}", "CL0099", (start + timedelta(days=5 * j)).isoformat(), "Virement international", round(rng.uniform(40000, 120000), 2), rng.choice(["RUS", "IRN", "PRK"]), "Débit"])
write("transactions_demo.csv", ["tx_id", "client_id", "date", "type", "montant", "pays_contrepartie", "sens"], tx)

# Portefeuille KYC de démonstration (remédiation)
port = []
for i in range(1, 201):
    t = rng.choice(["PP", "PP", "PP", "PM", "PM", "ASSO", "TRUST"])
    risk = rng.choices(["Faible", "Standard", "Élevé"], weights=[3, 5, 2])[0]
    last_rev = date(2026, 10, 18) - timedelta(days=rng.randint(10, 1800))
    idv = date(2026, 10, 18) + timedelta(days=rng.randint(-700, 2000))
    port.append([f"CL{i:04d}", f"Client {i:04d}", t, rng.choice(iso_list[:40] + ["HTI", "CMR", "RUS", "ARE", "VNM"]), risk,
                 last_rev.isoformat(), idv.isoformat(),
                 rng.choice(["Oui", "Oui", "Oui", "Non"]),  # justificatif domicile
                 rng.choice(["Oui", "Oui", "Non"]) if t != "PP" else "N/A",  # BE identifiés
                 rng.choice(["Oui", "Non"]),  # origine des fonds
                 rng.choice(["Oui", "Oui", "Oui", "Non"]),  # profession/activité
                 rng.choice(["Non", "Non", "Non", "Non", "Oui"])])  # ppe
write("kyc_portfolio_demo.csv", ["client_id", "nom", "type", "pays", "niveau_risque", "derniere_revue", "expiration_piece_identite",
                                 "justificatif_domicile", "be_identifies", "origine_fonds", "activite_documentee", "ppe"], port)

# Conformité sectorielle — check-list de mise en conformité
checks = {
    "COMMUN": [
        ("Gouvernance", "Responsable LCB-FT désigné et membre de la direction responsable (AMLR art. 11)", "AMLR art. 11; arrêté 6 janv. 2021 art. 4"),
        ("Gouvernance", "Classification des risques LCB-FT formalisée et mise à jour", "CMF L.561-4-1"),
        ("Gouvernance", "Procédures écrites (KYC, EDD, DS, gel) approuvées", "Arrêté 6 janv. 2021"),
        ("KYC", "Identification et vérification à l'entrée en relation", "CMF L.561-5"),
        ("KYC", "Identification des bénéficiaires effectifs et consultation RBE", "CMF L.561-46"),
        ("KYC", "Mise à jour périodique des dossiers selon le niveau de risque", "CMF L.561-6"),
        ("Vigilance renforcée", "Dispositif PPE (détection, accord direction, origine du patrimoine)", "CMF L.561-10"),
        ("Vigilance renforcée", "Pays tiers à haut risque (UE/GAFI) – mesures renforcées", "CMF L.561-10 4°"),
        ("Surveillance", "Surveillance des opérations calibrée sur le profil client", "Décision ACPR Delubac 2025"),
        ("Surveillance", "Délais de traitement des alertes pilotés (SLA)", "Décision ACPR Delubac 2025"),
        ("Surveillance", "Examen renforcé documenté (L.561-10-2)", "CMF L.561-10-2"),
        ("Déclaration", "Processus de DS Tracfin (Ermes) et traçabilité des décisions", "CMF L.561-15"),
        ("Gel des avoirs", "Filtrage des clients et des opérations contre les listes UE/ONU/France", "CMF L.562-4-1"),
        ("Formation", "Plan de formation annuel et attestations", "CMF L.561-34"),
        ("Contrôle", "Contrôle permanent et périodique du dispositif", "Arrêté 3 nov. 2014"),
        ("AMLR 2027", "Gap analysis AMLR réalisée et feuille de route validée", "Règl. (UE) 2024/1624"),
        ("AMLR 2027", "Plan de remédiation du stock clients (art. 26)", "AMLR art. 26"),
    ],
    "FINTECH": [("Spécifique", "Contrôle des agents et distributeurs de monnaie électronique", "CMF L.523-1"),
                ("Spécifique", "Traçabilité des IBAN virtuels jusqu'au donneur d'ordre final", "ASR 2023"),
                ("Spécifique", "Détection des mules financières et comptes de passage", "ASR 2023")],
    "BANQUE": [("Spécifique", "Due diligence correspondants bancaires hors UE", "CMF L.561-10-3"),
               ("Spécifique", "Origine du patrimoine pour la banque privée", "ASR 2023 §3.2.3")],
    "ASSURANCE": [("Spécifique", "Contrôle des rachats anticipés et tiers payeurs", "Lignes directrices ACPR"),
                  ("Spécifique", "Identification du bénéficiaire au dénouement", "CMF R.561-12")],
    "JEUX": [("Spécifique", "Identification des joueurs au-delà des seuils (2 000 €)", "CMF R.561-10"),
             ("Spécifique", "Suivi des gains et remboursements de mises", "ANJ")],
    "IMMOBILIER": [("Spécifique", "Vérification de l'origine des fonds de l'acquéreur", "CMF L.561-2 8°"),
                   ("Spécifique", "Analyse du prix au regard du marché (DVF)", "Tracfin cas 7")],
    "TRANSFERT": [("Spécifique", "Identification dès le premier euro et contrôle TFR", "Règl. (UE) 2023/1113"),
                  ("Spécifique", "Scoring des corridors et des agents", "ASR 2023 §3.3.3")],
    "CRYPTO": [("Spécifique", "Agrément CASP MiCA obtenu", "MiCA art. 59"),
               ("Spécifique", "Travel Rule et vérification des wallets non hébergés", "TFR art. 14"),
               ("Spécifique", "Outil d'analyse blockchain", "Bonnes pratiques AMF")],
    "CHANGE": [("Spécifique", "Agrégation des opérations multi-guichets", "ASR 2023 §3.5")],
    "ENTREPRISE": [("Spécifique", "Cartographie anticorruption Sapin II", "Loi Sapin II art. 17"),
                   ("Spécifique", "Évaluation des tiers et filtrage sanctions/export", "Règl. (UE) 2021/821")],
}
crow = []
for sec, items in checks.items():
    for i, (dom, ex, ref) in enumerate(items, 1):
        crow.append([f"{sec}-{i:02d}", sec, dom, ex, ref])
write("compliance_checklist.csv", ["id", "secteur", "domaine", "exigence", "reference"], crow)

# Fichiers vivants (feedback / logs) — créés vides s'ils n'existent pas
for name, header in [
    ("feedback.csv", ["date", "source", "objet_id", "prediction", "label_analyste", "commentaire"]),
    ("agent_log.csv", ["date", "agent", "action", "statut", "utilisateur", "details"]),
    ("adverse_keywords.csv", ["mot_cle", "langue", "poids", "categorie"]),
]:
    p = DATA / name
    if not p.exists() or name == "adverse_keywords.csv":
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

kw = [("blanchiment", "fr", 3, "BC"), ("money laundering", "en", 3, "BC"), ("corruption", "fr", 3, "Corruption"),
      ("pot-de-vin", "fr", 3, "Corruption"), ("bribery", "en", 3, "Corruption"), ("fraude", "fr", 2, "Fraude"),
      ("fraud", "en", 2, "Fraude"), ("escroquerie", "fr", 2, "Fraude"), ("scam", "en", 2, "Fraude"),
      ("détournement", "fr", 2, "Corruption"), ("embezzlement", "en", 2, "Corruption"), ("sanction", "fr", 2, "Sanctions"),
      ("sanctioned", "en", 3, "Sanctions"), ("terrorisme", "fr", 4, "FT"), ("terrorism", "en", 4, "FT"),
      ("trafic", "fr", 2, "Criminalité"), ("trafficking", "en", 3, "Criminalité"), ("cartel", "en", 3, "Criminalité"),
      ("mis en examen", "fr", 3, "Judiciaire"), ("condamné", "fr", 3, "Judiciaire"), ("indicted", "en", 3, "Judiciaire"),
      ("convicted", "en", 3, "Judiciaire"), ("perquisition", "fr", 2, "Judiciaire"), ("arrested", "en", 2, "Judiciaire"),
      ("évasion fiscale", "fr", 2, "Fiscal"), ("tax evasion", "en", 2, "Fiscal"), ("abus de biens sociaux", "fr", 3, "Corruption"),
      ("Ponzi", "en", 3, "Fraude"), ("Pandora Papers", "en", 2, "Opacité"), ("Panama Papers", "en", 2, "Opacité")]
with open(DATA / "adverse_keywords.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["mot_cle", "langue", "poids", "categorie"])
    w.writerows(kw)

# ---------------------------------------------------------------------------
# 14. DISPOSITIF DE CONTRÔLE (3 lignes de maîtrise) et FEUILLE DE ROUTE
# ---------------------------------------------------------------------------
# secteur | domaine | point de contrôle | niveau | fréquence | méthode / échantillon | indicateur (KPI) | seuil d'alerte | référence
CTRL = [
    ("COMMUN", "Gouvernance", "Validation annuelle de la classification des risques par l'organe de direction", "2e niveau", "Annuelle", "Revue du PV de validation", "Date de dernière validation", "> 12 mois", "CMF L.561-4-1; AMLR art. 9-11"),
    ("COMMUN", "Gouvernance", "Rapport annuel LCB-FT et gel (RACI) transmis au superviseur", "2e niveau", "Annuelle", "Contrôle de complétude du rapport", "Rapport transmis dans les délais", "Retard", "Arrêté 6 janv. 2021"),
    ("COMMUN", "KYC", "Complétude des dossiers à l'entrée en relation (4 yeux)", "1er niveau", "Continue", "100 % des ouvertures risque élevé, 5 % des autres", "Taux de dossiers complets", "< 95 %", "CMF L.561-5"),
    ("COMMUN", "KYC", "Contrôle qualité des dossiers KYC", "2e niveau", "Trimestrielle", "Échantillon aléatoire de 30 dossiers stratifié par risque", "Taux d'anomalies", "> 5 %", "CMF R.561-5"),
    ("COMMUN", "KYC", "Respect des échéances de revue périodique", "2e niveau", "Mensuelle", "Extraction des dossiers échus", "Dossiers en retard de revue", "> 2 % du portefeuille", "CMF L.561-6; AMLR art. 26"),
    ("COMMUN", "Bénéficiaires effectifs", "Identification des BE et rapprochement RBE (signalement des divergences)", "2e niveau", "Semestrielle", "Échantillon de 20 personnes morales", "Taux de BE identifiés", "< 98 %", "CMF L.561-46; AMLR art. 51-58"),
    ("COMMUN", "PPE", "Détection PPE et accord de la direction", "2e niveau", "Trimestrielle", "100 % des nouvelles PPE", "PPE sans accord direction", "> 0", "CMF R.561-20-2; AMLR art. 42"),
    ("COMMUN", "PPE", "Revue annuelle des PPE (origine du patrimoine)", "2e niveau", "Annuelle", "100 % du registre PPE", "Revues PPE en retard", "> 0", "AMLR art. 44"),
    ("COMMUN", "Gel des avoirs", "Mise à jour des listes de gel dans l'outil (UE/ONU/DG Trésor)", "1er niveau", "Quotidienne", "Journal de chargement des listes", "Délai de prise en compte d'une nouvelle désignation", "> 24 h", "CMF L.562-4-1"),
    ("COMMUN", "Gel des avoirs", "Test d'efficacité du filtrage (jeu de noms tests)", "2e niveau", "Semestrielle", "Injection de 50 noms tests (variantes, translittérations)", "Taux de détection", "< 100 % des vrais positifs", "Arrêté 6 janv. 2021 art. 12"),
    ("COMMUN", "Gel des avoirs", "Traitement des alertes de filtrage", "1er niveau", "Continue", "Revue des alertes et justifications de faux positifs", "Alertes > 24 h non traitées", "> 0", "CMF L.562-4"),
    ("COMMUN", "Surveillance", "Calibrage des scénarios (profil financier, pays effectifs)", "2e niveau", "Annuelle", "Revue below/above-the-line", "Scénarios revus dans l'année", "< 100 %", "Décision ACPR Delubac 2025 (griefs 1 et 3)"),
    ("COMMUN", "Surveillance", "Stock et délais de traitement des alertes", "2e niveau", "Mensuelle", "Tableau de bord des alertes", "Alertes > 30 jours", "> 5 % du stock", "Décision ACPR Delubac 2025 (grief 2)"),
    ("COMMUN", "Examen renforcé", "Finalisation des examens renforcés dans les délais", "2e niveau", "Mensuelle", "100 % des examens ouverts", "Examens > 60 jours", "> 0", "CMF L.561-10-2; décision Delubac (grief 5)"),
    ("COMMUN", "Déclarations", "Qualité et délai des déclarations de soupçon", "2e niveau", "Trimestrielle", "Revue de 100 % des DS et de 10 % des classements sans suite", "Délai moyen détection → DS", "> 30 jours", "CMF L.561-15"),
    ("COMMUN", "Déclarations", "Fins de relation pour motif LCB-FT précédées d'un examen de l'opportunité d'une DS", "2e niveau", "Trimestrielle", "100 % des clôtures LCB-FT", "Clôtures sans analyse DS", "> 0", "Décision ACPR Delubac 2025 (grief 2)"),
    ("COMMUN", "Formation", "Taux de formation annuelle des collaborateurs exposés", "2e niveau", "Annuelle", "Registre des formations et certificats", "Taux de collaborateurs formés", "< 95 %", "CMF L.561-34"),
    ("COMMUN", "Externalisation", "Contrôle des prestataires (KYC, filtrage, PSEE)", "2e niveau", "Annuelle", "Audit / questionnaire prestataire", "Prestataires critiques contrôlés", "< 100 %", "Arrêté 3 nov. 2014; DORA"),
    ("COMMUN", "Contrôle périodique", "Mission d'audit interne du dispositif LCB-FT", "3e niveau", "Tous les 2 à 3 ans", "Mission d'audit sur l'ensemble du dispositif", "Recommandations soldées dans les délais", "< 80 %", "Arrêté 3 nov. 2014"),
    ("COMMUN", "Modèles & IA", "Validation et suivi des modèles de scoring (dérive, biais)", "2e niveau", "Semestrielle", "PSI, back-testing, revue des seuils", "PSI maximal", "> 0,25", "AI Act 2024/1689; bonnes pratiques"),
    ("BANQUE", "Spécifique", "Due diligence des correspondants bancaires hors UE", "2e niveau", "Annuelle", "100 % des correspondants hors UE", "Questionnaires Wolfsberg à jour", "< 100 %", "CMF L.561-10-3"),
    ("BANQUE", "Spécifique", "Origine du patrimoine en banque privée", "2e niveau", "Semestrielle", "Échantillon de 20 clients patrimoniaux", "Dossiers justifiés", "< 95 %", "ASR 2023 §3.2.3"),
    ("FINTECH", "Spécifique", "Contrôle des agents et distributeurs de monnaie électronique", "2e niveau", "Semestrielle", "Visites / audits sur échantillon d'agents", "Agents audités", "< 20 % par an", "CMF L.523-1; L.525-8"),
    ("FINTECH", "Spécifique", "Détection des comptes de passage / mules", "1er niveau", "Continue", "Revue des alertes ratio entrées/sorties", "Comptes mules détectés après fraude signalée", "Hausse", "ASR 2023 §3.3"),
    ("FINTECH", "Spécifique", "Traçabilité des IBAN virtuels jusqu'au donneur d'ordre", "2e niveau", "Trimestrielle", "Échantillon de 30 flux IBAN virtuels", "Flux tracés", "< 100 %", "ASR 2023 §2.2.2"),
    ("ASSURANCE", "Spécifique", "Contrôle des rachats anticipés et tiers payeurs", "2e niveau", "Trimestrielle", "100 % des rachats < 2 ans au-delà du seuil", "Rachats analysés", "< 100 %", "Lignes directrices ACPR"),
    ("ASSURANCE", "Spécifique", "Identification du bénéficiaire au dénouement", "1er niveau", "Continue", "Contrôle avant paiement", "Paiements sans identification", "> 0", "CMF R.561-12"),
    ("JEUX", "Spécifique", "Identification des joueurs au-delà des seuils et origine des fonds", "1er niveau", "Continue", "Contrôle des paiements de gains", "Gains payés sans identification", "> 0", "CMF R.561-10; ANJ"),
    ("JEUX", "Spécifique", "Détection du chip dumping et des paris anormaux", "2e niveau", "Mensuelle", "Requêtes sur transferts inter-joueurs", "Alertes traitées", "< 100 %", "ANJ"),
    ("IMMOBILIER", "Spécifique", "Origine des fonds de l'acquéreur et cohérence du prix (DVF)", "2e niveau", "Trimestrielle", "Échantillon de 15 transactions", "Dossiers conformes", "< 95 %", "CMF L.561-2 8°; Tracfin cas 7"),
    ("TRANSFERT", "Spécifique", "Complétude des informations TFR", "1er niveau", "Continue", "Contrôle automatique des messages", "Transferts incomplets exécutés", "> 0", "Règl. (UE) 2023/1113"),
    ("TRANSFERT", "Spécifique", "Scoring et audit des agents", "2e niveau", "Trimestrielle", "Agents à volumes atypiques", "Agents à risque audités", "< 100 %", "ASR 2023 §3.3.3"),
    ("CRYPTO", "Spécifique", "Travel Rule et vérification des wallets non hébergés", "1er niveau", "Continue", "Contrôle des transferts > 1 000 €", "Transferts sans vérification", "> 0", "TFR art. 14"),
    ("CRYPTO", "Spécifique", "Analyse blockchain des dépôts (mixeurs, darknet, sanctions)", "1er niveau", "Continue", "100 % des dépôts entrants", "Dépôts à risque non bloqués", "> 0", "MiCA; GAFI R.15"),
    ("CHANGE", "Spécifique", "Agrégation des opérations multi-guichets", "2e niveau", "Mensuelle", "Requête sur identités récurrentes", "Fractionnements détectés", "Hausse", "ASR 2023 §3.5"),
    ("ENTREPRISE", "Spécifique", "Évaluation des tiers (anticorruption, sanctions, export)", "2e niveau", "Annuelle", "Échantillon de 25 tiers à risque", "Tiers évalués avant contrat", "< 100 %", "Loi Sapin II art. 17; Règl. 2021/821"),
    ("ENTREPRISE", "Spécifique", "Contrôles comptables anticorruption", "2e niveau", "Trimestrielle", "Revue des comptes sensibles (commissions, cadeaux)", "Écritures sans justificatif", "> 0", "Recommandations AFA"),
]
write("control_framework.csv", ["id", "secteur", "domaine", "point_de_controle", "niveau", "frequence", "methode_echantillon",
                                "indicateur", "seuil_alerte", "reference"],
      [[f"CTL-{i:03d}", *c] for i, c in enumerate(CTRL, 1)])

# phase | étape | description | livrables | durée (semaines) | responsable | secteur (COMMUN ou code)
STEPS = [
    ("1. Cadrage", "Lancement et cadrage du projet", "Comité de lancement, périmètre (entités, produits, pays), gouvernance projet", "Note de cadrage, planning", 1, "Direction / RCSI", "COMMUN"),
    ("1. Cadrage", "Diagnostic de maturité (gap analysis)", "Évaluation des exigences CMF et AMLR, entretiens, revue documentaire", "Rapport de diagnostic, score de maturité", 3, "Consultant / Conformité", "COMMUN"),
    ("2. Gouvernance", "Désignation des responsables", "Membre de la direction responsable LCB-FT, responsable conformité, déclarant/correspondant Tracfin", "Décisions de nomination, fiches de poste", 1, "Direction générale", "COMMUN"),
    ("2. Gouvernance", "Comité LCB-FT et reporting", "Création d'un comité trimestriel, tableau de bord et indicateurs", "Charte du comité, tableau de bord", 2, "Conformité", "COMMUN"),
    ("3. Risques", "Cartographie des risques LCB-FT", "Identification et cotation des risques (clients, produits, canaux, pays, opérations)", "Cartographie Excel validée", 4, "Conformité / Métiers", "COMMUN"),
    ("3. Risques", "Classification des clients (scoring)", "Paramétrage du score de risque client et des niveaux de vigilance", "Matrice de scoring", 2, "Conformité / IT", "COMMUN"),
    ("4. Procédures", "Rédaction du corpus procédural", "Procédures KYC, vigilance renforcée, PPE, surveillance, DS, gel, conservation", "Procédures et politique d'acceptation clients", 4, "Conformité", "COMMUN"),
    ("5. KYC", "Remédiation du stock clients", "Priorisation par risque (AMLR art. 26), relances, restrictions", "Plan de remédiation, courriers", 8, "Opérations KYC", "COMMUN"),
    ("6. Outils", "Filtrage sanctions et PPE", "Choix/paramétrage de l'outil, listes UE/ONU/DG Trésor, tests d'efficacité", "Outil en production, PV de tests", 4, "IT / Conformité", "COMMUN"),
    ("6. Outils", "Surveillance des opérations", "Scénarios calibrés sur le profil financier et les pays effectifs, gestion des alertes", "Catalogue de scénarios, SLA", 6, "IT / Conformité", "COMMUN"),
    ("7. Formation", "Plan de formation et sensibilisation", "Modules par population, quiz, certificats, registre", "Plan de formation, attestations", 2, "Conformité / RH", "COMMUN"),
    ("8. Contrôle", "Dispositif de contrôle permanent (2e niveau)", "Plan de contrôle, échantillonnage, fiches de contrôle, indicateurs", "Plan de contrôle annuel", 3, "Contrôle permanent", "COMMUN"),
    ("8. Contrôle", "Contrôle périodique (3e niveau)", "Intégration du dispositif LCB-FT au plan d'audit", "Plan d'audit pluriannuel", 1, "Audit interne", "COMMUN"),
    ("9. AMLR 2027", "Préparation AMLR / AMLA", "Alignement sur les RTS AMLA, calcul des BE, règles PPE, plafond espèces", "Feuille de route AMLR, attestation de préparation", 6, "Conformité", "COMMUN"),
    ("10. Pilotage", "Revue et amélioration continue", "Revue annuelle, rapport au superviseur, réentraînement des modèles", "Rapport annuel, plan d'actions N+1", 2, "Conformité / Direction", "COMMUN"),
    ("6. Outils", "Due diligence des correspondants bancaires", "Questionnaires Wolfsberg, revue des banques correspondantes hors UE", "Dossiers correspondants", 3, "Conformité", "BANQUE"),
    ("6. Outils", "Dispositif agents et IBAN virtuels", "Contrôle des agents/distributeurs, traçabilité des IBAN virtuels, détection des mules", "Procédure agents, scénarios mules", 4, "Conformité / Partenariats", "FINTECH"),
    ("6. Outils", "Contrôles rachats et dénouements", "Alertes de rachats anticipés, contrôle des tiers payeurs et bénéficiaires", "Scénarios assurance", 3, "Conformité / Gestion", "ASSURANCE"),
    ("6. Outils", "Identification des joueurs et suivi des gains", "Seuils d'identification, origine des fonds, intégrité sportive", "Procédure joueurs, reporting ANJ", 3, "Conformité / Opérations", "JEUX"),
    ("6. Outils", "Vigilance acquéreurs et prix", "Origine des fonds, BE des SCI, comparaison DVF", "Fiche transaction", 2, "Direction d'agence", "IMMOBILIER"),
    ("6. Outils", "Travel Rule et réseau d'agents", "Contrôle TFR, scoring des corridors et des agents", "Procédure TFR, audits agents", 4, "Conformité / Réseau", "TRANSFERT"),
    ("2. Gouvernance", "Agrément CASP (MiCA)", "Dossier d'agrément, fin du régime transitoire PSAN", "Agrément CASP", 8, "Direction / Juridique", "CRYPTO"),
    ("6. Outils", "Analyse blockchain et Travel Rule", "Outil d'analytics, vérification des wallets non hébergés > 1 000 €", "Outil en production", 4, "IT / Conformité", "CRYPTO"),
    ("6. Outils", "Agrégation multi-guichets", "Identification au-delà des seuils, détection des fractionnements", "Requêtes d'agrégation", 2, "Conformité", "CHANGE"),
    ("3. Risques", "Programme anticorruption Sapin II", "Cartographie anticorruption, évaluation des tiers, contrôles comptables", "Cartographie AFA, procédure tiers", 6, "Conformité", "ENTREPRISE"),
]
write("roadmap_steps.csv", ["phase", "etape", "description", "livrables", "duree_semaines", "responsable", "secteur"], [list(x) for x in STEPS])

print("Référentiels générés dans", DATA)
