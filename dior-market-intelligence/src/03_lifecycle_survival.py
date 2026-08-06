"""
03_lifecycle_survival.py

Reutilise la methodologie de ChronoRisk (Kaplan-Meier applique a un risque
temporel) sur un probleme different : le risque de decrochage de la
dynamique de lancement -> combien de semaines un lancement Dior met-il, en
moyenne, a perdre 50% de sa velocite de vente vs son pic ?

AJOUT (v2) : la seule mesure "semaines avant demi-vie" ne dit pas quoi FAIRE.
On ajoute donc deux dimensions business (segment, canal) et une table de
decision qui traduit le half-life en action concrete -- c'est la question
qu'un manager BD posera systematiquement : "comment on utilise ce chiffre ?"

Donnees : simulees (aucun jeu de donnees public de courbes de lancement
parfum n'existe), mais la forme des courbes et les differences par segment
suivent la logique sectorielle connue : une edition limitee decroit plus vite
qu'un pilier de marque, la haute parfumerie (petite cible, forte fidelite)
decroit plus lentement.
"""

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

np.random.seed(7)

# launch : (segment, canal principal, vitesse de decroissance relative)
# vitesse plus faible = decroit plus lentement (tient plus longtemps)
LAUNCHES = [
    ("J'adore Intense",               "Core Fragrance",     "Retail",        (2, 5, 0.07, 0.10)),
    ("Dior Addict (EdP)",             "Core Fragrance",     "Retail",        (2, 5, 0.07, 0.10)),
    ("Sauvage Elixir",                "Core Fragrance",     "Travel Retail", (2, 4, 0.06, 0.09)),
    ("Miss Dior Essence",             "Core Fragrance",     "Retail",        (2, 5, 0.05, 0.08)),
    ("Dior Homme",                    "Core Fragrance",     "Retail",        (2, 5, 0.06, 0.09)),
    ("Cuir Saddle (Collection Privee)","Haute Parfumerie",  "Retail",        (3, 6, 0.03, 0.06)),
    ("Forever Skin Glow",             "Maquillage",         "E-commerce",    (1, 3, 0.09, 0.13)),
    ("Backstage Airflash Mist",       "Maquillage",         "E-commerce",    (1, 3, 0.09, 0.13)),
    ("Rouge Dior Limited Edition",    "Limited Edition",    "E-commerce",    (1, 2, 0.11, 0.16)),
    ("Noel Capsule Coffret",          "Limited Edition",    "Travel Retail", (1, 2, 0.12, 0.17)),
]

records = []
for launch, segment, canal, (pmin, pmax, dmin, dmax) in LAUNCHES:
    peak_week = np.random.uniform(pmin, pmax)
    decay_rate = np.random.uniform(dmin, dmax)
    weeks = np.arange(0, 40)
    velocity = np.where(
        weeks < peak_week,
        weeks / peak_week,
        np.exp(-decay_rate * (weeks - peak_week)),
    )
    below_50 = np.where(velocity < 0.5)[0]
    candidates = below_50[below_50 > peak_week]
    week_below_50 = candidates[0] if len(candidates) else 39
    censored = week_below_50 >= 39
    records.append({
        "launch": launch, "segment": segment, "canal": canal,
        "weeks_to_half_life": week_below_50, "censored": censored,
    })

df = pd.DataFrame(records)
df["event_observed"] = ~df["censored"]

# --- Kaplan-Meier global ---
kmf = KaplanMeierFitter()
kmf.fit(df["weeks_to_half_life"], event_observed=df["event_observed"])
median_half_life = kmf.median_survival_time_
survival_curve = kmf.survival_function_.reset_index()
survival_curve.columns = ["week", "survival_prob"]

# --- Kaplan-Meier par segment (la vraie valeur ajoutee business) ---
segment_medians = {}
for segment in df["segment"].unique():
    sub = df[df["segment"] == segment]
    if sub["event_observed"].sum() == 0:
        continue
    kmf_seg = KaplanMeierFitter()
    kmf_seg.fit(sub["weeks_to_half_life"], event_observed=sub["event_observed"])
    segment_medians[segment] = float(kmf_seg.median_survival_time_)

# ----------------------------------------------------------------------------
# TABLE DE DECISION : traduit le half-life + segment en action concrete.
# C'est la reponse directe a "comment utiliseriez-vous cette analyse pour
# decider ?" -- posee en entretien business dev.
# ----------------------------------------------------------------------------
def recommend_action(weeks, segment):
    if segment == "Limited Edition" or weeks < 12:
        return "Vélocité courte : activer CRM / relance retargeting rapidement, ne pas sur-stocker au-delà de S+8"
    elif weeks < 15:
        return "Vélocité standard : maintenir la distribution actuelle, réassort classique"
    else:
        return "Vélocité longue (fidélité forte) : investir en storytelling / contenu de marque plutôt qu'en promotion prix"

df["recommandation"] = df.apply(lambda r: recommend_action(r["weeks_to_half_life"], r["segment"]), axis=1)

print(df[["launch", "segment", "canal", "weeks_to_half_life", "recommandation"]].sort_values("weeks_to_half_life"))
print(f"\nMediane globale (semaines avant demi-vie) : {median_half_life:.1f}")
print("\nMediane par segment :")
for seg, med in segment_medians.items():
    print(f"  {seg}: {med:.1f} semaines")

df.to_csv("/home/claude/dior-market-intelligence/data/launch_lifecycle.csv", index=False)
survival_curve.to_csv("/home/claude/dior-market-intelligence/data/launch_survival_curve.csv", index=False)

import json
curve_json = survival_curve.round(3).to_dict(orient="records")
with open("/home/claude/dior-market-intelligence/data/survival_curve.json", "w") as f:
    json.dump({
        "curve": curve_json,
        "median_weeks": round(float(median_half_life), 1),
        "segment_medians": {k: round(v, 1) for k, v in segment_medians.items()},
        "launches": df.to_dict(orient="records"),
    }, f, indent=2, default=str)
