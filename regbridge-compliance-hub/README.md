# 🛡️ RegBridge Compliance Hub

**Plateforme RegTech de conformité LCB-FT, sanctions, embargos et fraude** — Streamlit · Python · HTML/CSS · JavaScript · Machine Learning.

15 agents spécialisés construisent l'architecture complète de conformité d'une entité (banque, fintech de paiement, assurance, jeux & hasard, immobilier, transfert d'argent, crypto-actifs, change manuel, entreprise) : cartographies des risques Excel, trames Word, certificats PDF, kits ZIP, surveillance des sanctions/PPE/presse négative, scoring ML auto-apprenant, tableau de bord mondial de la sécurité financière, comptes utilisateurs et offres payantes.

> Référentiel à jour au 18/10/2026 : GAFI (plénière de juin 2026), liste UE des pays tiers à haut risque (Règl. délégués 2026/46 et 2026/83, en vigueur au 29/01/2026), AMLR / AMLA / AMLD6, MiCA, TFR, décision ACPR Banque Delubac (19/06/2025).

---

## ✨ Fonctionnalités

| Agent | Rôle | Livrables | Offre |
|---|---|---|---|
| A01 Formation & Certification | Modules, quiz notés, vérification | **Certificat PDF** numéroté et vérifiable, feuille d'émargement Word | Découverte (quiz) / Pro (certificat) |
| A02 Remédiation KYC | Diagnostic du stock clients, priorisation AMLR art. 26 | Plan de remédiation **Excel**, courriers clients **Word** | Pro |
| A03 Cartographie des risques | Par secteur × typologie d'entreprise, options de profil, risques sur mesure | **Excel** à formules vivantes (brut/net, matrice, synthèse, plan d'action, pays, typologies) | Pro |
| A04 Examen renforcé | Trames L.561-10-2 par type de client et secteur | **Word** (EDD, DS, fiche PPE) | Pro |
| A05 Recueil KYC | Pièces par typologie (PP, PM, trust, association, PPE, PSAN…) | Fiches **Word**, matrice **Excel**, ZIP | Pro |
| A06 Sanctions & Embargos | Régimes UE/ONU/OFAC/France, GAFI, liste UE, **mise à jour** et historisation, filtrage de noms (unitaire et par lot) | Exports Excel, fiche d'alerte Word | Découverte (consultation) / Pro |
| A07 PPE | Risque PPE par pays, fonctions (JOUE C/2023/724), registre, échéances, recherche Wikidata/OpenSanctions | Registre **Excel**, fiche d'approbation | Pro |
| A08 Presse négative | Recherche en sources ouvertes (FR/EN), scoring par mots-clés **auto-pondérés** | Rapport **Word** | Pro |
| A09 Surveillance transactionnelle | 7 règles expertes + Isolation Forest, file priorisée, **poids appris** par retour analyste | Registre des alertes **Excel** | Pro |
| A10 Fraude sectorielle | Scénarios par secteur, simulateur de scoring | Référentiel Excel | Pro |
| A11 Veille & Jurisprudence | Calendrier AMLR/AMLA/AMLD6/MiCA/TFR…, décisions de sanction | Suivi au format « Regulations Tracking » | Découverte / Pro |
| A12 Mise en conformité | Diagnostic de maturité par secteur, radar, feuille de route | Rapport **Word** | Pro |
| A15 Contrôle & plan de conformité | Dispositif de contrôle sur 3 lignes de maîtrise (36 points : niveau, fréquence, échantillon, KPI, seuil d'alerte, référence) et plan de mise en conformité étape par étape selon secteur, taille et maturité | **PDF** (synthèse, Gantt, fiches étapes, dispositif de contrôle), infographie **JPEG**, plan de contrôle et feuille de route **Excel** | Pro |
| A13 Kit documentaire | Un dossier par secteur × 10 sous-dossiers | **ZIP** (≈ 200 documents Word/Excel pour 9 secteurs) | Entreprise |
| A14 Auto-amélioration (ML) | Scoring client GradientBoosting, explicabilité, champion/challenger, PSI | Registre des versions de modèles | Entreprise |

**Tableau de bord** : bandeau d'actualités défilant (JavaScript), compteurs animés et compte à rebours AMLR, **carte mondiale** (indice de sécurité financière, GAFI, liste UE, sanctions, IPC, risque PPE) avec sélection de période, **jauge** d'évolution de l'indice mondial, courbe historique, actualités par thème, échéances réglementaires, **cartes d'articles** de sécurité financière avec liens et descriptions.

**Comptes** : inscription (essai Pro 7 jours), connexion bcrypt, sessions, offres Découverte / Professionnel / Entreprise, paiement par lien Stripe + codes d'activation, console d'administration.

---

## 🧠 Machine learning et auto-amélioration

1. **Scoring client** (`core/ml.py`) — GradientBoosting entraîné sur `data/training_clients.csv` (4 000 profils synthétiques). Chaque décision d'analyste (« profil à risque confirmé / sain ») est ajoutée à `data/feedback_clients.csv` avec un poids ×3. Au réentraînement, le **challenger** n'est promu que si son AUC sur le même jeu de validation n'est pas dégradée ; sinon il est rejeté et tracé dans `models/registry.json`.
2. **Surveillance** — chaque règle a une précision estimée par un modèle **Bêta-Binomial** (`data/rule_weights.json`) mis à jour à chaque « vrai / faux positif » : le score des alertes futures s'adapte.
3. **Presse négative** — les poids des mots-clés (`data/adverse_keywords.csv`) augmentent ou diminuent selon la pertinence qualifiée par l'analyste.
4. **Dérive** — indice PSI entre la population d'entraînement et les populations récentes ; alerte « réentraîner » au-delà de 0,25.
5. **Journal des agents** (`data/agent_log.csv`) — exécutions, statuts et volumes, exploités par l'orchestrateur et le laboratoire ML.

---

## 🗂️ Architecture

```
regbridge-compliance-hub/
├── app.py                    # Point d'entrée : authentification, navigation, offres
├── views/                    # Pages (1 par agent + tableau de bord, orchestrateur, compte, admin)
├── agents/registry.py        # Déclaration des 14 agents + journal d'activité
├── core/
│   ├── auth.py               # Comptes, sessions, offres, codes d'activation, certificats (SQLite + bcrypt)
│   ├── data.py               # Accès aux référentiels CSV, indice de sécurité financière
│   ├── ml.py                 # Scoring, surveillance, auto-apprentissage, PSI
│   ├── screening.py          # Filtrage flou (RapidFuzz) contre listes de sanctions
│   ├── updater.py            # MAJ ONU, OFAC, UE (FSF), DG Trésor, GAFI + historisation
│   ├── feeds.py              # Actualités RSS (repli hors-ligne)
│   └── ui.py                 # Composants HTML/CSS/JS
├── generators/               # excel.py · word.py · pdf.py · plan.py · zipkit.py
├── assets/                   # style.css · components.js (ticker, compteurs, compte à rebours)
├── static/world_110m.json    # Fond de carte servi localement
├── data/*.csv                # 25 référentiels (pays, sanctions, typologies, KYC, PPE, réglementation…)
├── scripts/build_data.py     # Régénère tous les référentiels CSV
└── tests/                    # pytest (unitaires) + Playwright (UI)
```

### Référentiels CSV principaux
`countries.csv` (165 pays : GAFI, liste UE, sanctions, IPC, conflit, opacité, indice, risque PPE) · `index_history.csv` · `sanctions_regimes.csv` · `asr_2023_products.csv` · `risk_factors.csv` (95 facteurs) · `company_typologies.csv` · `typologies.csv` (Tracfin 2023-2024 + compléments) · `regulations.csv` · `jurisprudence.csv` · `pep_functions.csv` · `pep_watchlist.csv` · `kyc_requirements.csv` · `fraud_scenarios.csv` · `compliance_checklist.csv` · `control_framework.csv` · `roadmap_steps.csv` · `quiz_bank.csv` · `news_feeds.csv` · `articles.csv` · `training_clients.csv` · `transactions_demo.csv` · `kyc_portfolio_demo.csv`.

---

## 🚀 Installation

```bash
git clone https://github.com/<votre-compte>/regbridge-compliance-hub.git
cd regbridge-compliance-hub
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Compte administrateur par défaut : `admin@regbridge.fr` / `Admin!2026` — **à remplacer** via les secrets.

### Déploiement Streamlit Community Cloud
1. Pousser le dépôt sur GitHub.
2. Sur share.streamlit.io : *New app* → dépôt → `app.py`.
3. *Settings → Secrets* : copier `.streamlit/secrets.toml.example` et renseigner les valeurs.

### Secrets (`.streamlit/secrets.toml`)
```toml
ADMIN_EMAIL = "vous@votre-domaine.fr"
ADMIN_PASSWORD = "MotDePasseFort!2026"
STRIPE_LINK_PRO = "https://buy.stripe.com/..."
STRIPE_LINK_ENTERPRISE = "https://buy.stripe.com/..."
```

### Paiement
Créez deux *Payment Links* Stripe (Pro, Entreprise). Après paiement, générez un code d'activation dans **Administration → Codes d'activation** et transmettez-le au client, qui le saisit dans **Mon compte**. (Pour une activation automatique, brancher un webhook Stripe sur un petit service externe qui appelle `auth.create_code`.)

### Persistance
SQLite (`data/app.db`) et les CSV vivants sont stockés sur le disque de l'instance. Sur Streamlit Community Cloud, le disque est **éphémère** : pour la production, migrer les comptes vers une base managée (Supabase/PostgreSQL) — seules les fonctions de `core/auth.py` sont à adapter.

---

## 🔄 Mises à jour des listes
Onglet **Sanctions & Embargos** :
- *Mettre à jour ONU · OFAC · UE · DG Trésor* — télécharge les listes officielles (consolidated.xml ONU, SDN.CSV OFAC, fichier FSF de l'UE, registre national des gels) dans `data/cache/` ; le filtrage les utilise automatiquement.
- *Interroger le site du GAFI* — détecte les juridictions des dernières publications « increased monitoring » / « call for action », affiche les ajouts/retraits et les applique après validation.
- *Édition manuelle* — modifier GAFI, liste UE, sanctions, IPC… puis **Enregistrer et historiser** : l'indice est recalculé et un instantané daté alimente la jauge et la courbe du tableau de bord.

Prochaine plénière du GAFI : fin octobre 2026.

---

## 🧪 Tests
```bash
pytest -q                                   # générateurs, ML, filtrage, référentiels
python tests/smoke_ui.py http://localhost:8501 ./captures   # toutes les pages (Playwright)
python tests/flow_ui.py  http://localhost:8501 ./captures   # parcours fonctionnels
```

---

## 📚 Sources
ACPR — *Analyse sectorielle des risques LCB-FT* (2023) · Tracfin — *LCB-FT : état de la menace 2023-2024* · ACPR Commission des sanctions — décision Banque Delubac & Cie (proc. 2024-02, 19/06/2025) · JOUE C/2023/724 (fonctions PPE) · GAFI — listes noire et grise (juin 2026) · Règlements délégués (UE) 2026/46 et 2026/83 · Règlements (UE) 2024/1624 (AMLR), 2024/1620 (AMLA), Directive (UE) 2024/1640 (AMLD6), 2023/1113 (TFR), 2023/1114 (MiCA), 2024/886 (paiements instantanés) · CMF L.561-1 et s. · arrêté du 6 janvier 2021.

Les valeurs IPC sont **indicatives** (à actualiser avec la publication annuelle de Transparency International). Les montants des sanctions étrangères sont arrondis.

## ⚠️ Avertissement
Outil d'aide à la décision : il ne se substitue ni à l'analyse humaine, ni aux textes officiels, ni aux listes officielles de gel des avoirs. Les données de démonstration (clients, transactions, PPE, entités « TEST ») sont **fictives**.

© RegBridge Conseil — tous droits réservés.
