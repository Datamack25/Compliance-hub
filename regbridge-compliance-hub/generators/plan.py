"""Dispositif de contrôle et plan de mise en conformité étape par étape — exports PDF (ReportLab) et JPEG (Pillow)."""
from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.paths import ASSETS

FONT_DIR = ASSETS / "fonts"
try:
    pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    F, FB = "DejaVu", "DejaVu-Bold"
except Exception:  # pragma: no cover
    F, FB = "Helvetica", "Helvetica-Bold"

NAVY, TEAL, GOLD, GREY, LIGHT = "#0B1F3A", "#0E7490", "#B8891B", "#5B6B82", "#F4F6FA"
PHASE_COLORS = ["#0E7490", "#155E75", "#5925DC", "#B8891B", "#067647", "#B54708", "#0B4A6F", "#B42318", "#475467", "#0B1F3A"]
SIZE_COEF = {"TPE / PME": 0.8, "ETI": 1.0, "Grand groupe": 1.4}
PREREQ = {1: [], 2: [1], 3: [2], 4: [3], 5: [4], 6: [3], 7: [4], 8: [4], 9: [3], 10: [5, 6, 7, 8, 9]}
LINES = {"1er niveau": "Opérationnels (1re ligne)", "2e niveau": "Conformité / contrôle permanent (2e ligne)", "3e niveau": "Audit interne (3e ligne)"}


# ============================================================================ calcul du plan
def build_plan(steps: pd.DataFrame, sector: str, size: str = "ETI", maturity: float | None = None,
               start: date | None = None) -> pd.DataFrame:
    start = start or date.today()
    df = steps[steps["secteur"].isin(["COMMUN", sector])].copy()
    df["n_phase"] = df["phase"].str.extract(r"^(\d+)").astype(int)
    coef = SIZE_COEF.get(size, 1.0) * (1.3 - 0.6 * (maturity or 0) / 100 if maturity is not None else 1.0)
    df["duree"] = (df["duree_semaines"] * coef).round().clip(lower=1).astype(int)
    phase_end: dict[int, int] = {}
    starts = {}
    for ph in sorted(df["n_phase"].unique()):
        s0 = max([phase_end.get(p, 0) for p in PREREQ.get(ph, [])] or [0])
        starts[ph] = s0
        # étapes d'une même phase : enchaînées si dépendantes (ordre), sinon parallèles -> on enchaîne la 1re et parallélise les spécifiques
        sub = df[df["n_phase"] == ph]
        cur = s0
        for idx in sub.index:
            df.loc[idx, "debut_sem"] = cur if df.loc[idx, "secteur"] == "COMMUN" else s0
            if df.loc[idx, "secteur"] == "COMMUN":
                cur += df.loc[idx, "duree"]
        phase_end[ph] = int(max((df.loc[sub.index, "debut_sem"] + df.loc[sub.index, "duree"]).max(), cur))
    df["debut_sem"] = df["debut_sem"].astype(int)
    df["fin_sem"] = df["debut_sem"] + df["duree"]
    df["date_debut"] = df["debut_sem"].map(lambda w: start + timedelta(weeks=int(w)))
    df["date_fin"] = df["fin_sem"].map(lambda w: start + timedelta(weeks=int(w)))
    df = df.sort_values(["debut_sem", "n_phase"]).reset_index(drop=True)
    df.insert(0, "n", range(1, len(df) + 1))
    return df


def controls_for(controls: pd.DataFrame, sector: str) -> pd.DataFrame:
    return controls[controls["secteur"].isin(["COMMUN", sector])].copy()


# ============================================================================ PDF
def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName=FB, fontSize=24, leading=28, textColor=colors.HexColor(NAVY)),
        "h2": ParagraphStyle("h2", fontName=FB, fontSize=15, leading=19, textColor=colors.HexColor(NAVY), spaceAfter=6, spaceBefore=4),
        "h3": ParagraphStyle("h3", fontName=FB, fontSize=11, leading=14, textColor=colors.HexColor(TEAL)),
        "p": ParagraphStyle("p", fontName=F, fontSize=9, leading=12, textColor=colors.HexColor("#15233B"), alignment=TA_LEFT),
        "small": ParagraphStyle("s", fontName=F, fontSize=7.5, leading=9.5, textColor=colors.HexColor(GREY)),
        "cell": ParagraphStyle("c", fontName=F, fontSize=7.6, leading=9.4),
        "cellb": ParagraphStyle("cb", fontName=FB, fontSize=7.6, leading=9.4, textColor=colors.white),
    }


def _gantt(plan: pd.DataFrame, width: float) -> Drawing:
    rowh, label_w, top = 15, 7.2 * cm, 26
    total = int(plan["fin_sem"].max())
    h = top + rowh * len(plan) + 10
    d = Drawing(width, h)
    scale = (width - label_w - 10) / max(total, 1)
    # grille mensuelle
    for w in range(0, total + 1, 4):
        x = label_w + w * scale
        d.add(Line(x, 6, x, h - top + 6, strokeColor=colors.HexColor("#E3E8F0"), strokeWidth=0.5))
        d.add(String(x, h - 14, f"S{w}", fontName=F, fontSize=6.5, fillColor=colors.HexColor(GREY), textAnchor="middle"))
    for i, r in enumerate(plan.itertuples()):
        y = h - top - (i + 1) * rowh + 4
        col = colors.HexColor(PHASE_COLORS[(r.n_phase - 1) % len(PHASE_COLORS)])
        lab = f"{r.n:>2}. {r.etape}"
        d.add(String(4, y + 3, lab[:46], fontName=F, fontSize=7, fillColor=colors.HexColor("#15233B")))
        d.add(Rect(label_w + r.debut_sem * scale, y, max(r.duree * scale, 3), rowh - 5, fillColor=col, strokeColor=None, rx=3, ry=3))
        d.add(String(label_w + r.fin_sem * scale + 3, y + 3, f"{r.duree} sem.", fontName=F, fontSize=6, fillColor=colors.HexColor(GREY)))
    return d


def _on_page(company, sector_label):
    def draw(c, doc):
        W, H = landscape(A4)
        c.saveState()
        c.setFillColor(colors.HexColor(NAVY))
        c.rect(0, H - 1.0 * cm, W, 1.0 * cm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(FB, 9)
        c.drawString(1.2 * cm, H - 0.65 * cm, "RegBridge Compliance Hub — Dispositif de contrôle & plan de mise en conformité")
        c.setFont(F, 8)
        c.drawRightString(W - 1.2 * cm, H - 0.65 * cm, f"{company} · {sector_label}")
        c.setFillColor(colors.HexColor(GREY))
        c.drawString(1.2 * cm, 0.6 * cm, f"Document confidentiel — généré le {date.today():%d/%m/%Y}")
        c.drawRightString(W - 1.2 * cm, 0.6 * cm, f"Page {doc.page}")
        c.restoreState()
    return draw


def plan_pdf(company: str, sector_label: str, size: str, maturity: float | None, plan: pd.DataFrame,
             controls: pd.DataFrame, typologies: pd.DataFrame | None = None) -> bytes:
    S = _styles()
    bio = io.BytesIO()
    W, H = landscape(A4)
    doc = SimpleDocTemplate(bio, pagesize=(W, H), leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.6 * cm, bottomMargin=1.2 * cm,
                            title=f"Plan de mise en conformité — {company}", author="RegBridge Conseil")
    el = []
    end = plan["date_fin"].max()
    # ---------- page de garde + synthèse
    el += [Paragraph("PLAN DE MISE EN CONFORMITÉ LCB-FT", S["h1"]), Spacer(1, 4),
           Paragraph(f"et dispositif de contrôle — <b>{company}</b> · secteur <b>{sector_label}</b> · taille <b>{size}</b>"
                     + (f" · maturité initiale <b>{maturity:.0f} %</b>" if maturity is not None else ""), S["h3"]), Spacer(1, 14)]
    kpis = [("Étapes", str(len(plan))), ("Durée totale", f"{int(plan['fin_sem'].max())} semaines"),
            ("Fin prévisionnelle", end.strftime("%d/%m/%Y")), ("Points de contrôle", str(len(controls))),
            ("Échéance AMLR", "10/07/2027")]
    t = Table([[Paragraph(f"<font size=7 color='{GREY}'>{k.upper()}</font><br/><font size=15 name='{FB}' color='{NAVY}'>{v}</font>", S["p"])
                for k, v in kpis]], colWidths=[(W - 2.4 * cm) / 5] * 5, rowHeights=[1.7 * cm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E3E8F0")), ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#E3E8F0")),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    el += [t, Spacer(1, 14), Paragraph("Feuille de route (diagramme de Gantt)", S["h2"]), _gantt(plan, W - 2.4 * cm)]
    el.append(Paragraph("Les phases dépendantes s'enchaînent ; la remédiation KYC, les outils, la formation et le contrôle se déroulent en parallèle "
                        "après la rédaction des procédures. Durées ajustées selon la taille de l'entité et sa maturité.", S["small"]))
    el.append(PageBreak())
    # ---------- étapes
    el.append(Paragraph("Plan étape par étape", S["h2"]))
    cards = []
    for r in plan.itertuples():
        col = PHASE_COLORS[(r.n_phase - 1) % len(PHASE_COLORS)]
        num = Table([[Paragraph(f"<font name='{FB}' size=15 color='white'>{r.n}</font>", S["p"])]], colWidths=[1.1 * cm], rowHeights=[1.1 * cm])
        num.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(col)), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
        body = Paragraph(f"<font color='{col}' size=7>{r.phase.upper()}</font><br/><b>{r.etape}</b><br/>{r.description}<br/>"
                         f"<font color='{GREY}'>Livrables : {r.livrables}<br/>Responsable : {r.responsable} · "
                         f"{r.date_debut:%d/%m/%Y} → {r.date_fin:%d/%m/%Y} ({r.duree} sem.)</font>", S["p"])
        card = Table([[num, body]], colWidths=[1.4 * cm, (W - 2.4 * cm) / 2 - 1.9 * cm])
        card.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E3E8F0")),
                                  ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        cards.append(card)
    rows = [cards[i:i + 2] + ([""] if len(cards[i:i + 2]) == 1 else []) for i in range(0, len(cards), 2)]
    grid = Table(rows, colWidths=[(W - 2.4 * cm) / 2] * 2)
    grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    el += [grid, PageBreak()]
    # ---------- dispositif de contrôle
    el.append(Paragraph("Dispositif de contrôle — trois lignes de maîtrise", S["h2"]))
    lines = Table([[Paragraph(f"<font name='{FB}' color='white'>{k}</font><br/><font color='white' size=8>{v}</font>", S["p"]) for k, v in LINES.items()]],
                  colWidths=[(W - 2.4 * cm) / 3] * 3, rowHeights=[1.3 * cm])
    lines.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), colors.HexColor(TEAL)), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#5925DC")),
                               ("BACKGROUND", (2, 0), (2, 0), colors.HexColor(NAVY)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    el += [lines, Spacer(1, 8)]
    head = ["Domaine", "Point de contrôle", "Niveau", "Fréquence", "Méthode / échantillon", "Indicateur", "Seuil d'alerte", "Référence"]
    widths = [2.4, 5.8, 1.8, 2.4, 4.6, 3.6, 2.4, 4.1]
    data = [[Paragraph(h, S["cellb"]) for h in head]]
    for r in controls.sort_values(["niveau", "domaine"]).itertuples():
        data.append([Paragraph(str(x), S["cell"]) for x in (r.domaine, r.point_de_controle, r.niveau, r.frequence, r.methode_echantillon,
                                                              r.indicateur, r.seuil_alerte, r.reference)])
    ct = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D7E2")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(LIGHT)]), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el.append(ct)
    el.append(Spacer(1, 10))
    # ---------- pilotage
    el.append(KeepTogether([
        Paragraph("Pilotage et gouvernance du dispositif", S["h2"]),
        Paragraph("• Comité LCB-FT trimestriel : suivi des indicateurs, des stocks d'alertes et des examens renforcés, validation des plans d'action.<br/>"
                  "• Reporting annuel à l'organe de direction et au superviseur ; revue annuelle de la cartographie et du plan de contrôle.<br/>"
                  "• Toute anomalie dépassant un seuil d'alerte donne lieu à un plan d'action daté, suivi jusqu'à clôture.<br/>"
                  "• Enseignements de la décision ACPR Banque Delubac (19/06/2025) : scénarios calibrés sur le profil financier, surveillance des pays "
                  "sur les opérations effectives, pilotage des délais d'alertes, d'examens renforcés et de DS.", S["p"])]))
    doc.build(el, onFirstPage=_on_page(company, sector_label), onLaterPages=_on_page(company, sector_label))
    return bio.getvalue()


# ============================================================================ JPEG
def _font(size, bold=False):
    try:
        return ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)
    except Exception:  # pragma: no cover
        return ImageFont.load_default()


def _wrap(draw, text, font, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def plan_jpeg(company: str, sector_label: str, size: str, plan: pd.DataFrame) -> bytes:
    W, margin = 1800, 70
    card_h = 150
    gantt_h = 60 + 26 * len(plan)
    H = 260 + gantt_h + 90 + ((len(plan) + 1) // 2) * (card_h + 22) + 90
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)
    # en-tête
    d.rectangle([0, 0, W, 200], fill=NAVY)
    d.rectangle([0, 200, W, 208], fill=TEAL)
    d.text((margin, 42), "PLAN DE MISE EN CONFORMITÉ LCB-FT — ÉTAPE PAR ÉTAPE", font=_font(40, True), fill="white")
    d.text((margin, 104), f"{company}  ·  {sector_label}  ·  {size}", font=_font(26), fill="#C9D6EA")
    d.text((margin, 146), f"{len(plan)} étapes  ·  {int(plan['fin_sem'].max())} semaines  ·  fin prévisionnelle {plan['date_fin'].max():%d/%m/%Y}",
           font=_font(22), fill="#7DD3E8")
    # gantt
    y0 = 240
    d.text((margin, y0), "Feuille de route", font=_font(28, True), fill=NAVY)
    total = int(plan["fin_sem"].max())
    lx, gx1 = margin + 520, W - margin
    sc = (gx1 - lx) / max(total, 1)
    gy = y0 + 50
    for w in range(0, total + 1, 4):
        x = lx + w * sc
        d.line([x, gy, x, gy + 26 * len(plan)], fill="#E3E8F0", width=1)
        d.text((x - 10, gy - 22), f"S{w}", font=_font(14), fill=GREY)
    for i, r in enumerate(plan.itertuples()):
        y = gy + i * 26
        col = PHASE_COLORS[(r.n_phase - 1) % len(PHASE_COLORS)]
        d.text((margin, y + 3), f"{r.n:>2}. {r.etape}"[:52], font=_font(16), fill="#15233B")
        d.rounded_rectangle([lx + r.debut_sem * sc, y + 3, lx + r.fin_sem * sc, y + 21], radius=6, fill=col)
    # cartes étape par étape
    y = gy + 26 * len(plan) + 50
    d.text((margin, y), "Étape par étape", font=_font(28, True), fill=NAVY)
    y += 56
    cw = (W - 2 * margin - 30) // 2
    for i, r in enumerate(plan.itertuples()):
        cx = margin + (i % 2) * (cw + 30)
        cy = y + (i // 2) * (card_h + 22)
        col = PHASE_COLORS[(r.n_phase - 1) % len(PHASE_COLORS)]
        d.rounded_rectangle([cx, cy, cx + cw, cy + card_h], radius=14, fill="white", outline="#E3E8F0", width=2)
        d.rounded_rectangle([cx, cy, cx + 10, cy + card_h], radius=4, fill=col)
        d.ellipse([cx + 28, cy + 22, cx + 88, cy + 82], fill=col)
        num = str(r.n)
        f = _font(26, True)
        d.text((cx + 58 - d.textlength(num, font=f) / 2, cy + 36), num, font=f, fill="white")
        tx = cx + 110
        d.text((tx, cy + 16), r.phase.upper(), font=_font(14, True), fill=col)
        d.text((tx, cy + 38), r.etape[:60], font=_font(21, True), fill=NAVY)
        for k, line in enumerate(_wrap(d, r.description, _font(15), cw - 130)[:2]):
            d.text((tx, cy + 70 + k * 20), line, font=_font(15), fill="#344054")
        d.text((tx, cy + card_h - 30), f"{r.responsable}  ·  {r.date_debut:%d/%m/%Y} → {r.date_fin:%d/%m/%Y}  ·  {r.duree} sem.",
               font=_font(14), fill=GREY)
    d.text((margin, H - 50), f"RegBridge Compliance Hub — généré le {date.today():%d/%m/%Y} — document d'aide à la décision", font=_font(15), fill=GREY)
    bio = io.BytesIO()
    img.save(bio, "JPEG", quality=92, optimize=True)
    return bio.getvalue()
