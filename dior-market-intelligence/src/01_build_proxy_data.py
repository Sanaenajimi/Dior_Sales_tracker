"""
01_build_proxy_data.py

OBJECTIF
--------
Circana / Beauty Research (les panels sell-out réels utilisés en interne par
Parfums Christian Dior) sont des donnees proprietaires, payantes, non
accessibles publiquement. je construits ici
un jeu de donnees mensuel PROXY :

  - calibre sur les ordres de grandeur publics Dior/LVMH (cf.
    data/quarterly_public_figures.csv, sources citees) mais volontairement
    distinct du CA de marque (panel = consommation finale, pas ventes a la
    marque -> cf. README)
  - avec une saisonnalite réaliste du secteur parfum/beaute
  - avec un evenement Chine traite comme un SCENARIO explicite (voir plus bas),
    pas comme un fait etabli
  - avec un vrai modele de stock (stock cible x semaines de couverture) pour
    deriver le sell-in a partir du sell-out, au lieu d'un simple ratio

Ce fichier ne represente pas des donnees Circana reelles.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# Chemin relatif : src/ -> ../data (fonctionne quel que soit l'endroit d'où
# le script est lancé, sur n'importe quelle machine qui clone le repo)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(42)

REGIONS = ["France", "Etats-Unis", "Chine", "Reste du Monde"]
LINES = ["Parfum Femme", "Parfum Homme", "Haute Parfumerie", "Maquillage"]

REGION_WEIGHT = {"France": 0.10, "Etats-Unis": 0.25, "Chine": 0.22, "Reste du Monde": 0.43}
LINE_WEIGHT = {"Parfum Femme": 0.40, "Parfum Homme": 0.27, "Haute Parfumerie": 0.10, "Maquillage": 0.23}

BASE_MONTHLY_SELLOUT_MEUR = 500

# Proxy de sell-out mensuel : ordre de grandeur de consommation finale (panel
# type Circana), volontairement distinct du CA de marque publie par LVMH.
# Ce n'est pas une donnee Circana reelle.

months = pd.date_range("2024-07-01", "2026-06-01", freq="MS")

def seasonality(month):
    m = month.month
    season = {
        1: 0.90, 2: 1.08, 3: 0.95, 4: 0.97, 5: 1.10, 6: 1.00,
        7: 1.05, 8: 1.02, 9: 0.93, 10: 0.98, 11: 1.15, 12: 1.35,
    }
    return season[m]

# ----------------------------------------------------------------------------
# CHINE : traitee comme un SCENARIO explicite, pas comme un fait constate.
#
# Question attendue en entretien : "comment savez-vous que le rebond Chine
# est de +12% ?" -> reponse : on ne le sait pas, on ne l'affirme jamais comme
# un fait unique. On expose 3 hypotheses, avec leur justification, et c'est au
# lecteur (Comex / marketing) de choisir celle qu'il retient pour ses
# projections -- exactement la logique d'un outil de decision, pas d'une
# boule de cristal.
# ----------------------------------------------------------------------------
CHINA_SCENARIOS = {
    "bearish": 0.00,  # pas de rattrapage confirme, la normalisation Q1/H1 2026 pourrait etre transitoire
    "base":    0.05,  # rattrapage modere, coherent avec les commentaires qualitatifs LVMH/L'Oreal H1 2026
    "bullish": 0.12,  # rattrapage fort si la dynamique Q2 2026 se confirme sur les 3 prochains trimestres
}
CHINA_SCENARIO_USED_FOR_HISTORY = "base"  # scenario retenu pour construire LA serie mensuelle canonique

def china_rebound_factor(month, scenario=CHINA_SCENARIO_USED_FOR_HISTORY):
    amplitude = CHINA_SCENARIOS[scenario]
    t = (month.year - 2024) * 12 + month.month
    t0 = (2025 - 2024) * 12 + 9  # sept 2025 = debut du rattrapage
    if t < t0:
        return 0.97
    progress = min((t - t0) / 9, 1.0)
    return 0.97 + progress * amplitude

def fashion_leather_drag(month):
    if month.year == 2026 and month.month == 3:
        return 0.985
    return 1.0

# ----------------------------------------------------------------------------
# SELL-IN via un vrai modele de stock cible, au lieu d'un ratio sur la saison :
#   Stock_t = Stock_(t-1) + SellIn_t - SellOut_t
#   Stock_cible_t = couverture_semaines_t * (SellOut_t / 4.33)
#   SellIn_t = SellOut_t + (Stock_cible_t - Stock_(t-1))
#
# La couverture cible (en semaines de sell-out a venir) varie dans l'annee :
# les distributeurs sur-couvrent avant Noel (construction de stock) et sous-couvrent en janvier-fevrier (destockage post-fetes) -- exactement la  mecanique qu'on chercherait a lire dans un vrai reporting retail.
# ----------------------------------------------------------------------------
def target_coverage_weeks(month):
    if month.month in (9, 10, 11):
        return 6.5   # constitution de stock avant Noel
    if month.month in (1, 2):
        return 3.5   # destockage post-fetes
    return 5.0       # couverture normale

rows = []
for region in REGIONS:
    for line in LINES:
        base = BASE_MONTHLY_SELLOUT_MEUR * REGION_WEIGHT[region] * LINE_WEIGHT[line]
        stock_prev = None
        for month in months:
            season = seasonality(month)
            china = china_rebound_factor(month) if region == "Chine" else 1.0
            drag = fashion_leather_drag(month)
            t = (month.year - 2024) * 12 + month.month
            trend = 1 + 0.0012 * t
            noise = np.random.normal(1.0, 0.035)
            sellout = base * season * china * drag * trend * noise

            coverage = target_coverage_weeks(month)
            target_stock = coverage * (sellout / 4.33)
            if stock_prev is None:
                stock_prev = target_stock  # amorçage : on part au niveau cible du premier mois
            sellin = sellout + (target_stock - stock_prev)
            sellin = max(sellin, 0)  # un sell-in negatif n'a pas de sens physique
            stock_t = stock_prev + sellin - sellout  # = target_stock par construction

            rows.append({
                "mois": month.strftime("%Y-%m"),
                "region": region,
                "ligne_produit": line,
                "sellout_meur": round(sellout, 2),
                "sellin_meur": round(sellin, 2),
                "stock_meur": round(stock_t, 2),
                "couverture_semaines": coverage,
            })
            stock_prev = stock_t

df = pd.DataFrame(rows)
df.to_csv(DATA_DIR / "monthly_proxy_sellout.csv", index=False)
print(df.shape)
print(df.head(10))
print("\nTotal sellout 2025 (proxy, M EUR):", df[df["mois"].str.startswith("2025")]["sellout_meur"].sum().round(1))
print("Total sellout 2026 H1 (proxy, M EUR):", df[df["mois"].str.startswith("2026-0")]["sellout_meur"].sum().round(1))
print("Stock moyen (M EUR):", df["stock_meur"].mean().round(1))
