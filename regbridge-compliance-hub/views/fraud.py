import plotly.graph_objects as go
import streamlit as st

from agents.registry import log
from core import auth
from core.data import SECTOR_LABELS, load
from core.ui import PLOTLY_LAYOUT, footer, hero, section
from generators import excel

hero("Fraude sectorielle", "Scénarios de fraude par secteur, indicateurs, contrôles recommandés et simulateur de scoring d'opération.",
     kicker="Agent A10 · Fraude")
if not auth.guard("pro"):
    st.stop()
fr, typ = load("fraud_scenarios.csv"), load("typologies.csv")
sec = st.selectbox("Secteur", list(SECTOR_LABELS), format_func=SECTOR_LABELS.get)
sub = fr[fr["secteur"] == sec]
section("Scénarios de fraude")
st.dataframe(sub[["fraude", "indicateurs", "controles"]], hide_index=True, use_container_width=True)
section("Typologies BC-FT liées")
st.dataframe(typ[typ["secteurs"].str.contains(sec)][["theme", "intitule", "criteres_alerte"]], hide_index=True, use_container_width=True)

section("Simulateur de scoring d'une opération")
c1, c2, c3 = st.columns(3)
amount = c1.number_input("Montant (€)", 0, 10_000_000, 4_500, step=500)
new_benef = c1.toggle("Nouveau bénéficiaire (< 24 h)")
new_device = c2.toggle("Nouvel appareil / changement de numéro")
urgent = c2.toggle("Urgence / pression (appel en cours, confidentialité)")
iban_change = c3.toggle("Changement d'IBAN récent")
foreign = c3.toggle("Destination pays à risque")
young = c1.toggle("Compte ouvert il y a < 30 jours")
night = c2.toggle("Opération nocturne / inhabituelle")
velocity = c3.slider("Opérations des dernières 24 h", 0, 30, 2)
score = min(100, (15 if amount > 10_000 else 8 if amount > 3_000 else 2) + 18 * new_benef + 16 * new_device + 14 * urgent + 15 * iban_change
            + 12 * foreign + 10 * young + 6 * night + min(velocity, 15) * 1.5)
decision = "Bloquer et contacter le client" if score >= 70 else "Mise en attente + vérification (VoP / rappel)" if score >= 40 else "Autoriser"
g = go.Figure(go.Indicator(mode="gauge+number", value=score, title={"text": decision},
                           gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#0B1F3A"},
                                  "steps": [{"range": [0, 40], "color": "#D1FADF"}, {"range": [40, 70], "color": "#FEF0C7"}, {"range": [70, 100], "color": "#FECDCA"}]}))
g.update_layout(**PLOTLY_LAYOUT, height=260)
st.plotly_chart(g, use_container_width=True)
if st.button("Journaliser la simulation"):
    log("A10", "Simulation fraude", details=f"{sec} score {score:.0f}")
st.download_button("⬇️ Référentiel fraude & typologies (Excel)", excel.dfs_to_xlsx({"Fraude": fr, "Typologies": typ}, "Référentiel fraude"), "Referentiel_fraude.xlsx")
footer()
