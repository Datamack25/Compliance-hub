"""Certificats de formation PDF (ReportLab)."""
from __future__ import annotations

import hashlib
import io
from datetime import date

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

NAVY, TEAL, GOLD, GREY = HexColor("#0B1F3A"), HexColor("#0E7490"), HexColor("#B8891B"), HexColor("#5B6B82")


def cert_id(name: str, module: str, when: str) -> str:
    return "RB-" + hashlib.sha256(f"{name}|{module}|{when}".encode()).hexdigest()[:10].upper()


def certificate(name: str, module: str, score: float, company: str = "", hours: str = "2 h", when: date | None = None,
                issuer: str = "RegBridge Conseil") -> tuple[bytes, str]:
    when = when or date.today()
    cid = cert_id(name, module, when.isoformat())
    bio = io.BytesIO()
    W, H = landscape(A4)
    c = canvas.Canvas(bio, pagesize=(W, H))
    c.setTitle(f"Certificat {module} — {name}")
    # fond et cadres
    c.setFillColor(HexColor("#F7F9FC"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 70, W, 70, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, H - 76, W, 6, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.rect(28, 28, W - 56, H - 120, fill=0, stroke=1)
    c.setLineWidth(0.6)
    c.rect(36, 36, W - 72, H - 136, fill=0, stroke=1)
    # en-tête
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, H - 45, "RegBridge Compliance Hub")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 40, H - 45, "Académie conformité — LCB-FT · Sanctions · Fraude")
    # corps
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(W / 2, H - 150, "CERTIFICAT DE RÉUSSITE")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 13)
    c.drawCentredString(W / 2, H - 180, "Le présent certificat atteste que")
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(W / 2, H - 225, name)
    if company:
        c.setFillColor(GREY)
        c.setFont("Helvetica-Oblique", 12)
        c.drawCentredString(W / 2, H - 247, company)
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 13)
    c.drawCentredString(W / 2, H - 280, "a suivi avec succès le module de formation")
    c.setFont("Helvetica-Bold", 19)
    c.drawCentredString(W / 2, H - 310, f"« {module} »")
    c.setFont("Helvetica", 12)
    c.setFillColor(GREY)
    c.drawCentredString(W / 2, H - 338, f"Score obtenu : {score:.0f} %   ·   Durée : {hours}   ·   Délivré le {when:%d/%m/%Y}")
    c.drawCentredString(W / 2, H - 356, "Obligation de formation : CMF art. L.561-34 · Règlement (UE) 2024/1624 (AMLR) art. 11")
    # sceau
    c.setStrokeColor(GOLD)
    c.setFillColor(HexColor("#FFF8E6"))
    c.circle(W - 150, 105, 46, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W - 150, 112, "CERTIFIÉ")
    c.setFont("Helvetica", 8)
    c.drawCentredString(W - 150, 99, "LCB-FT")
    # signature et vérification
    c.setStrokeColor(NAVY)
    c.line(80, 95, 280, 95)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, 80, issuer)
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawString(80, 67, "Responsable pédagogique")
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(NAVY)
    c.drawCentredString(W / 2, 80, f"N° de certificat : {cid}")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GREY)
    c.drawCentredString(W / 2, 66, "Vérifiable dans RegBridge Compliance Hub › Formation › Vérifier un certificat")
    c.showPage()
    c.save()
    return bio.getvalue(), cid
