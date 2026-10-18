"""Tests unitaires : générateurs, ML, filtrage. Lancement : pytest -q"""
import io
import sys
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import ml, screening  # noqa: E402
from generators import excel, pdf, word, zipkit  # noqa: E402

D = Path(__file__).resolve().parents[1] / "data"
R = lambda n: pd.read_csv(D / n, keep_default_na=False, na_values=[""])  # noqa: E731


def ref():
    return dict(factors=R("risk_factors.csv"), typologies=R("typologies.csv"), countries=R("countries.csv"), regs=R("regulations.csv"),
                kyc=R("kyc_requirements.csv"), sectors=R("sectors.csv"), checklist=R("compliance_checklist.csv"),
                sanctions=R("sanctions_regimes.csv"), roadmap=R("roadmap_steps.csv"), controls=R("control_framework.csv"))


def test_countries_reference():
    c = R("countries.csv")
    assert (c["gafi_statut"] == "noire").sum() == 3
    assert (c["gafi_statut"] == "grise").sum() == 22
    assert c["ue_pays_tiers_haut_risque"].sum() == 26
    assert c["indice_securite_financiere"].between(0, 100).all()


def test_risk_map_has_formulas():
    r = ref()
    b = excel.risk_map("Test", "FINTECH", "Fintech", "EME", 1.25, r["factors"], r["typologies"], r["countries"],
                       {"especes": True, "asr_level": "Élevé"}, r["regs"])
    wb = openpyxl.load_workbook(io.BytesIO(b))
    assert wb.sheetnames[:3] == ["Couverture", "Synthèse", "Cartographie"]
    assert str(wb["Cartographie"]["F5"].value).startswith("=ROUND(")


def test_word_and_pdf():
    r = ref()
    assert word.edd_template("Personne physique résidente", "Banque", "T", r["typologies"].head(3), r["kyc"].head(3))[:2] == b"PK"
    data, cid = pdf.certificate("Jane Doe", "Fondamentaux", 90)
    assert data[:4] == b"%PDF" and cid.startswith("RB-")


def test_zip_kit_structure():
    b, manifest = zipkit.build_kit("Démo", [("CRYPTO", "Crypto-actifs")], ref())
    z = zipfile.ZipFile(io.BytesIO(b))
    assert any("02_Cartographie_des_risques" in n for n in z.namelist())
    assert len(manifest) >= 20


def test_ml_monitor_flags_injected_patterns():
    alerts = ml.monitor(R("transactions_demo.csv"), R("countries.csv")).set_index("client_id")
    assert "R1" in alerts.loc["CL0007", "regles"]
    assert "R6" in alerts.loc["CL0099", "regles"]
    assert alerts.loc["CL0099", "priorite"] == "Critique"


def test_ml_scoring():
    if ml.champion() is None:
        ml.train()
    row = R("training_clients.csv").iloc[0].to_dict()
    p = ml.score_clients(pd.DataFrame([row]))[0]
    assert 0 <= p <= 1


def test_screening_demo():
    res = screening.screen("Golden Crescent Trading", screening.all_lists(), 80)
    assert len(res) and res.iloc[0]["score"] >= 80


def test_compliance_plan_exports():
    from generators import plan as P
    pl = P.build_plan(R("roadmap_steps.csv"), "CRYPTO", "TPE / PME", 30)
    assert pl["etape"].str.contains("CASP").any()
    assert (pl["fin_sem"] > pl["debut_sem"]).all()
    ct = P.controls_for(R("control_framework.csv"), "CRYPTO")
    assert set(ct["niveau"]) == {"1er niveau", "2e niveau", "3e niveau"}
    assert P.plan_pdf("T", "Crypto", "TPE / PME", 30, pl, ct)[:4] == b"%PDF"
    assert P.plan_jpeg("T", "Crypto", "TPE / PME", pl)[:2] == b"\xff\xd8"
