"""Kit documentaire complet : un dossier par secteur, sous-dossiers thématiques, trames Word et Excel prêtes à l'emploi."""
from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd

from generators import excel, word
from generators import plan as P

SUBFOLDERS = ["01_Gouvernance_et_procedures", "02_Cartographie_des_risques", "03_KYC_Recueil_et_remediation",
              "04_Vigilance_renforcee_EDD_PPE", "05_Surveillance_et_alertes", "06_Sanctions_Gel_Embargos",
              "07_Declarations_Tracfin", "08_Formation", "09_Controle_permanent", "10_Veille_reglementaire"]

CLIENT_TYPES = {
    "BANQUE": ["Personne physique résidente", "Société commerciale (SAS, SARL, SA)", "Trust / fiducie / construction juridique", "PPE (tout type)"],
    "FINTECH": ["Personne physique résidente", "Personne physique non-résidente", "Société commerciale (SAS, SARL, SA)", "Établissement de paiement / EME (contrepartie)"],
    "ASSURANCE": ["Personne physique résidente", "Personne physique non-résidente", "Société civile / SCI", "PPE (tout type)"],
    "JEUX": ["Personne physique résidente", "Personne physique non-résidente", "PPE (tout type)"],
    "IMMOBILIER": ["Personne physique résidente", "Société civile / SCI", "Personne morale étrangère", "PPE (tout type)"],
    "TRANSFERT": ["Personne physique résidente", "Personne physique non-résidente", "Association / fondation / fonds de dotation"],
    "CRYPTO": ["Personne physique résidente", "Société commerciale (SAS, SARL, SA)", "PSAN / CASP (contrepartie)"],
    "CHANGE": ["Personne physique résidente", "Personne physique non-résidente"],
    "ENTREPRISE": ["Société commerciale (SAS, SARL, SA)", "Personne morale étrangère", "Association / fondation / fonds de dotation"],
}


def _safe(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return "".join(ch if ch.isalnum() else "_" for ch in s).strip("_")[:60]


def build_kit(company: str, sectors: list[tuple[str, str]], ref: dict, progress=None) -> tuple[bytes, list[str]]:
    """ref = dict de DataFrames : factors, typologies, countries, regs, kyc, asr, sectors, checklist."""
    bio = io.BytesIO()
    manifest = []
    total = len(sectors)
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path: str, data: bytes):
            z.writestr(path, data)
            manifest.append(path)

        for k, (code, label) in enumerate(sectors):
            root = f"Kit_Conformite_{_safe(company) or 'Entite'}/{k + 1:02d}_{_safe(label)}"
            typ = ref["typologies"][ref["typologies"]["secteurs"].str.contains(code)]
            asr_level = ref["sectors"].set_index("code").loc[code, "niveau_asr"]
            # 01 Gouvernance
            add(f"{root}/{SUBFOLDERS[0]}/Procedure_LCB-FT_et_gel_{code}.docx",
                word.procedure(company, code, label, ref["factors"], ref["typologies"], ref["regs"]))
            add(f"{root}/{SUBFOLDERS[0]}/Politique_acceptation_clients_{code}.docx", word.acceptance_policy(company, label, ref["countries"]))
            # 02 Cartographie
            add(f"{root}/{SUBFOLDERS[1]}/Cartographie_risques_{code}.xlsx",
                excel.risk_map(company, code, label, "Standard", 1.0, ref["factors"], ref["typologies"], ref["countries"],
                               {"asr_level": asr_level}, ref["regs"]))
            # 03 KYC
            for ct in CLIENT_TYPES.get(code, []):
                kyc = ref["kyc"][ref["kyc"]["type_client"] == ct]
                add(f"{root}/{SUBFOLDERS[2]}/Fiche_KYC_{_safe(ct)}.docx", word.kyc_form(ct, company, kyc))
            add(f"{root}/{SUBFOLDERS[2]}/Plan_remediation_KYC.xlsx", excel.template("remediation_kyc", company))
            add(f"{root}/{SUBFOLDERS[2]}/Courrier_type_mise_a_jour_KYC.docx",
                word.remediation_letter(company, "[Nom du client]", ["Pièce d'identité en cours de validité", "Justificatif de domicile < 3 mois",
                                                                    "Justificatif de revenus / d'origine des fonds"]))
            # 04 EDD / PPE
            for ct in CLIENT_TYPES.get(code, [])[:2]:
                kyc_r = ref["kyc"][(ref["kyc"]["type_client"] == ct) & (ref["kyc"]["niveau_vigilance"] == "Renforcée")]
                add(f"{root}/{SUBFOLDERS[3]}/Trame_examen_renforce_{_safe(ct)}.docx", word.edd_template(ct, label, company, typ, kyc_r))
            add(f"{root}/{SUBFOLDERS[3]}/Fiche_approbation_PPE.docx", word.pep_form(company))
            add(f"{root}/{SUBFOLDERS[3]}/Registre_PPE.xlsx", excel.template("registre_ppe", company))
            # 05 Surveillance
            add(f"{root}/{SUBFOLDERS[4]}/Registre_alertes.xlsx", excel.template("registre_alertes", company))
            add(f"{root}/{SUBFOLDERS[4]}/Typologies_et_criteres_alerte_{code}.xlsx",
                excel.dfs_to_xlsx({"Typologies": typ[["id", "theme", "intitule", "criteres_alerte", "source"]]}, f"Typologies {label}"))
            # 06 Sanctions
            add(f"{root}/{SUBFOLDERS[5]}/Fiche_traitement_alerte_filtrage.docx", word.sanctions_alert_form(company))
            add(f"{root}/{SUBFOLDERS[5]}/Registre_gel_des_avoirs.xlsx", excel.template("registre_gel", company))
            add(f"{root}/{SUBFOLDERS[5]}/Referentiel_pays_GAFI_UE_sanctions.xlsx",
                excel.dfs_to_xlsx({"Pays": ref["countries"], "Régimes de sanctions": ref["sanctions"]}, "Référentiel pays"))
            # 07 Tracfin
            add(f"{root}/{SUBFOLDERS[6]}/Trame_declaration_de_soupcon.docx", word.ds_template(company, label))
            add(f"{root}/{SUBFOLDERS[6]}/Registre_DS.xlsx", excel.template("registre_ds", company))
            # 08 Formation
            add(f"{root}/{SUBFOLDERS[7]}/Feuille_emargement_formation.docx", word.training_attendance(company, f"LCB-FT — {label}"))
            add(f"{root}/{SUBFOLDERS[7]}/Registre_formations.xlsx", excel.template("registre_formation", company))
            # 09 Contrôle
            if "controls" in ref:
                cc = P.controls_for(ref["controls"], code)
                pre = pd.DataFrame({"Domaine": cc["domaine"], "Point de contrôle": cc["point_de_controle"], "Fréquence": cc["frequence"],
                                    "Échantillon": cc["methode_echantillon"], "Responsable": cc["niveau"], "Date": "", "Résultat": "",
                                    "Anomalies": "", "Plan d'action": "", "Statut": "À traiter"})
            else:
                chk = ref["checklist"][ref["checklist"]["secteur"].isin(["COMMUN", code])]
                pre = pd.DataFrame({"Domaine": chk["domaine"], "Point de contrôle": chk["exigence"], "Fréquence": "Trimestrielle",
                                    "Échantillon": "", "Responsable": "", "Date": "", "Résultat": "", "Anomalies": "", "Plan d'action": "",
                                    "Statut": "À traiter"})
            add(f"{root}/{SUBFOLDERS[8]}/Plan_controle_permanent.xlsx", excel.template("plan_controle", company, pre))
            if "roadmap" in ref and "controls" in ref:
                pl = P.build_plan(ref["roadmap"], code, "ETI")
                ct = P.controls_for(ref["controls"], code)
                add(f"{root}/{SUBFOLDERS[8]}/Plan_mise_en_conformite_et_dispositif_de_controle.pdf",
                    P.plan_pdf(company, label, "ETI", None, pl, ct))
                add(f"{root}/{SUBFOLDERS[8]}/Plan_mise_en_conformite_infographie.jpg", P.plan_jpeg(company, label, "ETI", pl))
            # 10 Veille
            add(f"{root}/{SUBFOLDERS[9]}/Suivi_reglementations.xlsx", excel.template("veille_reglementaire", company, ref["regs"]))
            if progress:
                progress((k + 1) / total, f"{label} : dossier généré")
        readme = (f"KIT DE CONFORMITÉ — {company}\nGénéré le {date.today():%d/%m/%Y} par RegBridge Compliance Hub\n\n"
                  "Structure : un dossier par secteur, 10 sous-dossiers thématiques (gouvernance, cartographie, KYC, EDD/PPE, surveillance, "
                  "sanctions, Tracfin, formation, contrôle, veille).\nLes documents sont des trames à adapter : ils ne remplacent pas "
                  "l'analyse juridique ni les textes officiels.\n\nFichiers :\n" + "\n".join(manifest))
        z.writestr(f"Kit_Conformite_{_safe(company) or 'Entite'}/LISEZ-MOI.txt", readme)
    return bio.getvalue(), manifest
