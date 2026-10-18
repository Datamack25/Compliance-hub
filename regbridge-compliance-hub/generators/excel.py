"""Générateurs Excel : cartographies des risques personnalisables et outils de pilotage prêts à l'emploi."""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

NAVY, TEAL, GOLD = "0B1F3A", "0E7490", "B8891B"
FILL_H = PatternFill("solid", fgColor=NAVY)
FILL_SUB = PatternFill("solid", fgColor="E6F4F7")
FONT_H = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
THIN = Side(style="thin", color="D0D7E2")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEVEL_FILLS = {"Faible": "D1FADF", "Modéré": "FEF0C7", "Élevé": "FDDCAB", "Très élevé": "FECDCA"}


def _title(ws, title: str, subtitle: str = "", width: int = 10):
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws["A2"] = subtitle
    ws["A2"].font = Font(italic=True, size=10, color="5B6B82")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)


def _header(ws, row: int, headers: list[str], widths: list[int] | None = None):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.fill, c.font, c.alignment, c.border = FILL_H, FONT_H, CENTER, BORDER
        if widths:
            ws.column_dimensions[get_column_letter(j)].width = widths[j - 1]
    ws.row_dimensions[row].height = 32
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _df_block(ws, df: pd.DataFrame, start_row: int = 4, widths: list[int] | None = None):
    widths = widths or [max(12, min(60, int(df[c].astype(str).str.len().quantile(0.9)) + 4)) if len(df) else 16 for c in df.columns]
    _header(ws, start_row, list(df.columns), widths)
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.border, c.alignment = BORDER, WRAP
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(df.columns))}{start_row + max(len(df), 1)}"


def to_bytes(wb: Workbook) -> bytes:
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def dfs_to_xlsx(sheets: dict[str, pd.DataFrame], title: str = "Export RegBridge") -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, df in sheets.items():
        ws = wb.create_sheet(name[:31])
        _title(ws, name, f"{title} — généré le {date.today():%d/%m/%Y}", max(len(df.columns), 4))
        _df_block(ws, df.fillna(""))
    return to_bytes(wb)


# ============================================================================ CARTOGRAPHIE
def risk_map(company: str, sector_code: str, sector_label: str, typology: str, coef: float,
             factors: pd.DataFrame, typologies: pd.DataFrame, countries: pd.DataFrame,
             options: dict, regs: pd.DataFrame, custom: pd.DataFrame | None = None) -> bytes:
    """Cartographie des risques LCB-FT personnalisée (formules Excel vivantes)."""
    f = factors[factors["secteur"] == sector_code].copy()
    if custom is not None and len(custom):
        f = pd.concat([f, custom], ignore_index=True)

    # --- personnalisation : ajustement des probabilités selon le profil
    def bump(mask, n=1):
        f.loc[mask, "probabilite"] = (f.loc[mask, "probabilite"] + n).clip(1, 4)

    if options.get("especes"):
        bump(f["facteur"].str.contains("espèces|Espèces|cash", regex=True))
    if options.get("non_residents"):
        bump(f["facteur"].str.contains("non-résident|pays|Pays|étranger|Géographie", regex=True) | (f["categorie"] == "Géographie"))
    if options.get("digital"):
        bump(f["facteur"].str.contains("distance|digital|Onboarding|ligne|VPN", regex=True))
    if options.get("ppe"):
        bump(f["facteur"].str.contains("PPE"))
    if options.get("crypto"):
        bump(f["facteur"].str.contains("crypto|wallet|NFT|blockchain", case=False, regex=True))
    if options.get("dispositif_jeune"):
        bump(f["categorie"] == "Dispositif")

    wb = Workbook()
    # ---------------- Couverture
    ws = wb.active
    ws.title = "Couverture"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 60
    ws["B3"] = "CARTOGRAPHIE DES RISQUES LCB-FT"
    ws["B3"].font = Font(bold=True, size=22, color=NAVY)
    ws["B4"] = "Blanchiment de capitaux, financement du terrorisme, sanctions & fraude"
    ws["B4"].font = Font(italic=True, size=12, color=TEAL)
    info = [("Entité", company), ("Secteur", sector_label), ("Typologie d'entreprise", typology),
            ("Coefficient typologie", coef), ("Date d'édition", date.today().strftime("%d/%m/%Y")), ("Version", "1.0"),
            ("Méthodologie", "Croisement menace × vulnérabilité (GAFI / ACPR ASR 2023), échelle 1-4, risque brut puis net"),
            ("Références", "CMF L.561-4-1 ; arrêté du 6 janvier 2021 ; Règl. (UE) 2024/1624 (AMLR) art. 10 ; ASR ACPR 2023"),
            ("Validation", "À approuver par l'organe de direction (AMLR art. 9-11) — revue au moins annuelle")]
    for i, (k, v) in enumerate(info, 6):
        ws.cell(row=i, column=2, value=k).font = Font(bold=True, color=NAVY)
        c = ws.cell(row=i, column=3, value=v)
        c.alignment = WRAP
        ws.cell(row=i, column=2).fill = FILL_SUB
    # ---------------- Méthodologie
    m = wb.create_sheet("Méthodologie")
    _title(m, "Méthodologie et échelles de cotation", "Inspirée de l'ASR 2023 de l'ACPR (échelle à 4 niveaux)", 6)
    _header(m, 4, ["Note", "Probabilité (menace)", "Impact", "Efficacité du dispositif", "Coef. d'atténuation"], [8, 34, 34, 40, 18])
    scale = [(1, "Rare / faible exposition", "Limité", "Bon (dispositif robuste)", 0.4),
             (2, "Possible", "Significatif", "Correct (améliorations mineures)", 0.6),
             (3, "Probable", "Majeur (sanction, réputation)", "Perfectible (lacunes)", 0.8),
             (4, "Quasi certain / très forte exposition", "Critique (retrait d'agrément)", "Insuffisant", 1.0)]
    for i, r in enumerate(scale, 5):
        for j, v in enumerate(r, 1):
            c = m.cell(row=i, column=j, value=v)
            c.border, c.alignment = BORDER, WRAP
    m["A11"] = "Coefficient de typologie appliqué au risque brut :"
    m["A11"].font = Font(bold=True)
    m["D11"] = coef
    m["D11"].fill = PatternFill("solid", fgColor="FEF0C7")
    m["A13"] = "Seuils du risque net : ≤ 3 Faible · ≤ 6 Modéré · ≤ 10 Élevé · > 10 Très élevé"
    m["A14"] = "Risque brut = Probabilité × Impact × coefficient typologie ; Risque net = Risque brut × coef. d'atténuation"
    # ---------------- Cartographie
    c = wb.create_sheet("Cartographie")
    _title(c, f"Cartographie — {sector_label} ({typology})", f"{company} — cellules jaunes modifiables, formules automatiques", 13)
    heads = ["ID", "Catégorie", "Facteur de risque", "Probabilité (1-4)", "Impact (1-4)", "Risque brut",
             "Dispositif d'atténuation", "Efficacité (1-4)", "Risque net", "Niveau", "Responsable", "Échéance", "Référence"]
    _header(c, 4, heads, [11, 14, 46, 12, 11, 11, 48, 12, 11, 13, 18, 13, 30])
    dv14 = DataValidation(type="whole", operator="between", formula1=1, formula2=4, showErrorMessage=True,
                          errorTitle="Valeur invalide", error="Saisir une note entre 1 et 4")
    c.add_data_validation(dv14)
    eff_default = 3 if options.get("dispositif_jeune") else 2
    yellow = PatternFill("solid", fgColor="FFF8DB")
    for i, r in enumerate(f.itertuples(), 5):
        vals = [r.id, r.categorie, r.facteur, int(r.probabilite), int(r.impact),
                f"=ROUND(D{i}*E{i}*Méthodologie!$D$11,1)", r.dispositif_attenuation, eff_default,
                f"=ROUND(F{i}*INDEX(Méthodologie!$E$5:$E$8,H{i}),1)",
                f'=IF(I{i}<=3,"Faible",IF(I{i}<=6,"Modéré",IF(I{i}<=10,"Élevé","Très élevé")))',
                "Responsable LCB-FT", "", r.reference]
        for j, v in enumerate(vals, 1):
            cell = c.cell(row=i, column=j, value=v)
            cell.border, cell.alignment = BORDER, WRAP
            if j in (4, 5, 8):
                cell.fill, cell.alignment = yellow, CENTER
                dv14.add(cell)
            if j in (6, 9, 10):
                cell.alignment = CENTER
                cell.font = Font(bold=True)
    last = 4 + len(f)
    c.conditional_formatting.add(f"F5:F{last}", ColorScaleRule(start_type="num", start_value=1, start_color="D1FADF",
                                                               mid_type="num", mid_value=8, mid_color="FEF0C7",
                                                               end_type="num", end_value=16, end_color="F97066"))
    c.conditional_formatting.add(f"I5:I{last}", ColorScaleRule(start_type="num", start_value=1, start_color="D1FADF",
                                                               mid_type="num", mid_value=6, mid_color="FEF0C7",
                                                               end_type="num", end_value=14, end_color="F97066"))
    for lvl, col in LEVEL_FILLS.items():
        c.conditional_formatting.add(f"J5:J{last}", CellIsRule(operator="equal", formula=[f'"{lvl}"'], fill=PatternFill("solid", fgColor=col)))
    c.auto_filter.ref = f"A4:M{last}"
    # ---------------- Matrice
    mx = wb.create_sheet("Matrice")
    _title(mx, "Matrice de chaleur probabilité × impact", "Nombre de facteurs par case (formules NB.SI.ENS)", 6)
    mx["A4"] = "Probabilité ↓ / Impact →"
    mx["A4"].font = Font(bold=True)
    for j in range(1, 5):
        h = mx.cell(row=4, column=j + 1, value=j)
        h.fill, h.font, h.alignment = FILL_H, FONT_H, CENTER
    for i, p in enumerate([4, 3, 2, 1], 5):
        h = mx.cell(row=i, column=1, value=p)
        h.fill, h.font, h.alignment = FILL_H, FONT_H, CENTER
        for j in range(1, 5):
            cell = mx.cell(row=i, column=j + 1, value=f"=COUNTIFS(Cartographie!$D$5:$D${last},{p},Cartographie!$E$5:$E${last},{j})")
            score = p * j
            col = "D1FADF" if score <= 3 else "FEF0C7" if score <= 6 else "FDDCAB" if score <= 10 else "FECDCA"
            cell.fill, cell.alignment, cell.border = PatternFill("solid", fgColor=col), CENTER, BORDER
            cell.font = Font(bold=True, size=14)
        mx.row_dimensions[i].height = 42
    for col in "ABCDE":
        mx.column_dimensions[col].width = 18
    # ---------------- Synthèse
    s = wb.create_sheet("Synthèse")
    _title(s, "Synthèse du profil de risque", "Calculée automatiquement à partir de l'onglet Cartographie", 4)
    _header(s, 4, ["Niveau de risque net", "Nombre de facteurs", "Part"], [26, 20, 12])
    for i, lvl in enumerate(["Faible", "Modéré", "Élevé", "Très élevé"], 5):
        s.cell(row=i, column=1, value=lvl).fill = PatternFill("solid", fgColor=LEVEL_FILLS[lvl])
        s.cell(row=i, column=2, value=f'=COUNTIF(Cartographie!$J$5:$J${last},"{lvl}")')
        s.cell(row=i, column=3, value=f"=IFERROR(B{i}/SUM($B$5:$B$8),0)").number_format = "0%"
        for j in (1, 2, 3):
            s.cell(row=i, column=j).border = BORDER
    s["A10"], s["B10"] = "Risque brut moyen", f"=ROUND(AVERAGE(Cartographie!F5:F{last}),2)"
    s["A11"], s["B11"] = "Risque net moyen", f"=ROUND(AVERAGE(Cartographie!I5:I{last}),2)"
    s["A12"], s["B12"] = "Niveau global (net)", '=IF(B11<=3,"Faible",IF(B11<=6,"Modéré",IF(B11<=10,"Élevé","Très élevé")))'
    for r in (10, 11, 12):
        s[f"A{r}"].font = Font(bold=True, color=NAVY)
    s["A14"] = "Niveau sectoriel ACPR (ASR 2023)"
    s["A14"].font = Font(bold=True)
    s["B14"] = options.get("asr_level", "")
    ch = BarChart()
    ch.title, ch.y_axis.title = "Répartition des risques nets", "Facteurs"
    ch.add_data(Reference(s, min_col=2, min_row=4, max_row=8), titles_from_data=True)
    ch.set_categories(Reference(s, min_col=1, min_row=5, max_row=8))
    ch.height, ch.width = 7.5, 14
    s.add_chart(ch, "E4")
    # ---------------- Plan d'action
    pa = wb.create_sheet("Plan d'action")
    _title(pa, "Plan d'action de remédiation", "Pré-rempli pour les facteurs à probabilité ≥ 3 — à compléter", 8)
    _header(pa, 4, ["ID risque", "Facteur", "Action corrective", "Priorité", "Responsable", "Échéance", "Statut", "Commentaire"],
            [11, 44, 50, 11, 18, 13, 14, 30])
    dv_st = DataValidation(type="list", formula1='"À lancer,En cours,Réalisé,Reporté"')
    dv_pr = DataValidation(type="list", formula1='"P1,P2,P3"')
    pa.add_data_validation(dv_st)
    pa.add_data_validation(dv_pr)
    hi = f[f["probabilite"] * f["impact"] >= 9]
    for i, r in enumerate(hi.itertuples(), 5):
        vals = [r.id, r.facteur, f"Renforcer : {r.dispositif_attenuation}", "P1" if r.probabilite * r.impact >= 12 else "P2",
                "Responsable LCB-FT", "", "À lancer", ""]
        for j, v in enumerate(vals, 1):
            cell = pa.cell(row=i, column=j, value=v)
            cell.border, cell.alignment = BORDER, WRAP
        dv_st.add(pa.cell(row=i, column=7))
        dv_pr.add(pa.cell(row=i, column=4))
    # ---------------- Pays
    p = wb.create_sheet("Risque pays")
    _title(p, "Référentiel risque pays", "GAFI (plénière juin 2026), liste UE (29/01/2026), sanctions, IPC indicatif", 8)
    cs = countries.copy()
    if options.get("countries"):
        cs = cs[cs["iso3"].isin(options["countries"])]
    cols = ["iso3", "pays", "region", "gafi_statut", "ue_pays_tiers_haut_risque", "niveau_sanctions", "regimes_sanctions",
            "indice_securite_financiere", "niveau_risque_pays"]
    _df_block(p, cs[cols].sort_values("indice_securite_financiere"), widths=[8, 24, 14, 12, 12, 12, 46, 14, 14])
    lastp = 4 + len(cs)
    for lvl, col in LEVEL_FILLS.items():
        p.conditional_formatting.add(f"I5:I{lastp}", CellIsRule(operator="equal", formula=[f'"{lvl}"'], fill=PatternFill("solid", fgColor=col)))
    # ---------------- Typologies
    t = wb.create_sheet("Typologies")
    _title(t, "Typologies BC-FT pertinentes", "Tracfin — état de la menace 2023-2024 et compléments", 6)
    tt = typologies[typologies["secteurs"].str.contains(sector_code)]
    _df_block(t, tt[["id", "theme", "intitule", "criteres_alerte", "source"]], widths=[7, 22, 40, 80, 24])
    # ---------------- Réglementation
    rg = wb.create_sheet("Réglementation")
    _title(rg, "Référentiel réglementaire", "Textes applicables et à venir (AMLR / AMLA / AMLD6 …)", 6)
    _df_block(rg, regs[["Identifiant unique", "Nom/titre de la réglementation", "Date d'entrée en vigueur", "Statut", "Résumé des points clés"]],
              widths=[10, 48, 14, 12, 80])
    order = ["Couverture", "Synthèse", "Cartographie", "Matrice", "Plan d'action", "Méthodologie", "Risque pays", "Typologies", "Réglementation"]
    wb._sheets = [wb[n] for n in order]
    wb.active = 0
    return to_bytes(wb)


# ============================================================================ OUTILS PRÊTS À L'EMPLOI
TEMPLATES = {
    "remediation_kyc": ("Plan de remédiation KYC", ["ID client", "Nom", "Type", "Niveau de risque", "Anomalie(s)", "Pièces manquantes",
                                                     "Priorité (AMLR art. 26)", "Date de relance 1", "Date de relance 2", "Date limite",
                                                     "Statut", "Mesure si non-réponse", "Chargé KYC"]),
    "registre_alertes": ("Registre des alertes LCB-FT", ["N° alerte", "Date", "Client", "Scénario", "Montant", "Analyste", "Date de prise en charge",
                                                         "Délai (jours)", "Conclusion", "Examen renforcé", "DS (O/N)", "Référence Ermes", "Date clôture"]),
    "registre_ppe": ("Registre des PPE", ["ID", "Nom", "Fonction", "Pays", "PPE / famille / proche", "Date d'identification", "Accord direction (nom/date)",
                                          "Origine du patrimoine", "Origine des fonds", "Fréquence de revue", "Prochaine revue", "Statut"]),
    "registre_gel": ("Registre gel des avoirs", ["Date", "Nom filtré", "Liste (UE/ONU/FR/OFAC)", "Score", "Faux positif (O/N)", "Justification",
                                                 "Fonds gelés (€)", "Déclaration DG Trésor (date)", "Analyste", "Validation"]),
    "plan_controle": ("Plan de contrôle permanent LCB-FT", ["Domaine", "Point de contrôle", "Fréquence", "Échantillon", "Responsable",
                                                            "Date", "Résultat", "Anomalies", "Plan d'action", "Statut"]),
    "registre_ds": ("Registre des déclarations de soupçon", ["N° interne", "Date de détection", "Client", "Typologie", "Montant", "Date DS",
                                                             "Délai détection-DS", "Référence Tracfin", "Droit d'opposition", "Suites"]),
    "registre_formation": ("Registre des formations", ["Collaborateur", "Service", "Module", "Date", "Durée", "Score", "N° certificat", "Prochaine échéance"]),
    "veille_reglementaire": ("Suivi des réglementations", ["Identifiant unique", "Nom/titre de la réglementation", "Domaine concerné", "Source (autorité émettrice)",
                                                           "Date d'entrée en vigueur", "Statut", "Résumé des points clés", "Impact sur l'entreprise",
                                                           "Actions requises", "Responsable du suivi", "Date de dernière mise à jour", "Lien vers le texte intégral"]),
    "questionnaire_ebr": ("Questionnaire d'auto-évaluation (EBR)", ["Domaine", "Question", "Réponse (Oui/Non/Partiel)", "Preuve", "Commentaire"]),
}


def template(kind: str, company: str = "", prefill: pd.DataFrame | None = None) -> bytes:
    title, cols = TEMPLATES[kind]
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    _title(ws, title, f"{company} — modèle RegBridge du {date.today():%d/%m/%Y}", len(cols))
    _header(ws, 4, cols, [max(14, min(40, len(c) + 6)) for c in cols])
    start = 5
    if prefill is not None and len(prefill):
        for i, row in enumerate(prefill.itertuples(index=False), start):
            for j, v in enumerate(row, 1):
                cell = ws.cell(row=i, column=j, value=v)
                cell.border, cell.alignment = BORDER, WRAP
        start += len(prefill)
    for i in range(start, start + 30):
        for j in range(1, len(cols) + 1):
            ws.cell(row=i, column=j).border = BORDER
    if "Statut" in cols:
        k = cols.index("Statut") + 1
        dv = DataValidation(type="list", formula1='"À traiter,En cours,Clôturé,Escaladé"')
        ws.add_data_validation(dv)
        dv.add(f"{get_column_letter(k)}5:{get_column_letter(k)}500")
    return to_bytes(wb)
