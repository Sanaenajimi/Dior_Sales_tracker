"""
02_growth_forecast.py

Reproduit la mission "hypotheses de croissance, projections de marches" du
poste Business Analyst BD Dior :
  1. Harmonisation mensuel -> trimestriel
  2. Croissance QoQ, YoY et rolling 12 mois par region
  3. Projection a 2 trimestres par region (lissage exponentiel a tendance
     amortie -- PAS un Holt-Winters complet : 8 points trimestriels ne
     suffisent pas a estimer une saisonnalite propre, celle-ci etant deja
     injectee au niveau mensuel dans 01_build_proxy_data.py)
  4. VALIDATION ROLLING-ORIGIN (backtest) du forecast : MAPE / RMSE mesures
     sur plusieurs decoupages train/test, pas juste un fit "en confiance"
  5. CHINE traitee en 3 scenarios explicites (bearish/base/bullish) plutot
     qu'un pourcentage impose -- outil de decision, pas une affirmation

NOTE HONNETE SUR LES LIMITES : avec seulement 8-10 points trimestriels par
region, aucune methode de forecast n'est robuste au sens statistique strict.
Le backtest ci-dessous sert a QUANTIFIER cette fragilite (MAPE affiche), pas a
la nier. En production, il faudrait au moins 12-16 trimestres d'historique
avant de se fier a un forecast automatique pour une decision budgetaire.
"""

import json
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

DATA_DIR = "/home/claude/dior-market-intelligence/data"

df = pd.read_csv(f"{DATA_DIR}/monthly_proxy_sellout.csv")
df["date"] = pd.to_datetime(df["mois"])
df["quarter"] = df["date"].dt.to_period("Q").astype(str)

# --- Agregation trimestrielle ---
# ATTENTION : stock_meur est un NIVEAU (photo de fin de mois), pas un flux --
# on ne le somme jamais sur le trimestre. Il faut d'abord agreger TOUS les
# couples region x ligne au niveau mensuel (stock total du portefeuille a la
# fin de ce mois), puis prendre le stock de FIN de trimestre (dernier mois),
# comme un vrai bilan de stock.
q_total_flows = df.groupby("quarter")[["sellout_meur", "sellin_meur"]].sum().reset_index()
monthly_stock_total = df.groupby(["mois", "quarter"])["stock_meur"].sum().reset_index()
q_total_stock = (
    monthly_stock_total.sort_values("mois").groupby("quarter")["stock_meur"].last().reset_index()
)
q_total = q_total_flows.merge(q_total_stock, on="quarter")
q_region = df.groupby(["quarter", "region"])["sellout_meur"].sum().reset_index()

# --- Croissance QoQ, YoY, rolling 12 mois ---
q_total["growth_qoq_pct"] = q_total["sellout_meur"].pct_change() * 100
q_total["growth_yoy_pct"] = q_total["sellout_meur"].pct_change(4) * 100
q_total["rolling_12m_meur"] = q_total["sellout_meur"].rolling(4).sum()

# --- Couverture de stock (semaines) au niveau agrege, pour lecture retail ---
q_total["couverture_semaines_moy"] = (q_total["stock_meur"] / (q_total["sellout_meur"] / 13)).round(1)  # 1 trimestre = 13 semaines

# ----------------------------------------------------------------------------
# BACKTEST ROLLING-ORIGIN : on ne se contente pas d'un seul fit sur tout
# l'historique. On simule ce qu'un analyste aurait vu a 2 moments differents,
# et on mesure l'erreur reelle du forecast sur les trimestres suivants.
# ----------------------------------------------------------------------------
def backtest_region(values, min_train=4, horizon=2):
    """Rolling-origin backtest : pour chaque origine possible, on entraine sur
    les points disponibles et on projette `horizon` trimestres, qu'on compare
    aux vraies valeurs. Retourne la liste des erreurs (MAPE, RMSE) par split."""
    errors = []
    n = len(values)
    for origin in range(min_train, n - 1):
        train = values[:origin]
        test = values[origin:origin + horizon]
        if len(test) == 0:
            continue
        try:
            model = ExponentialSmoothing(train, trend="add", damped_trend=True)
            fit = model.fit()
            pred = fit.forecast(len(test))
        except Exception:
            continue
        mape = float(np.mean(np.abs((np.array(test) - pred) / np.array(test))) * 100)
        rmse = float(np.sqrt(np.mean((np.array(test) - pred) ** 2)))
        errors.append({"origin_quarter_index": origin, "mape_pct": round(mape, 1), "rmse_meur": round(rmse, 1)})
    return errors

backtests = {}
for region in df["region"].unique():
    series = q_region[q_region["region"] == region].sort_values("quarter")
    values = series["sellout_meur"].values
    splits = backtest_region(values)
    if splits:
        avg_mape = round(float(np.mean([s["mape_pct"] for s in splits])), 1)
        avg_rmse = round(float(np.mean([s["rmse_meur"] for s in splits])), 1)
    else:
        avg_mape, avg_rmse = None, None
    backtests[region] = {"splits": splits, "avg_mape_pct": avg_mape, "avg_rmse_meur": avg_rmse}

# --- Forecast final (entraine sur tout l'historique dispo) pour chaque region ---
# Validation rolling-origin ci-dessus deja realisee -- a renforcer en
# production avec davantage d'historique (12+ trimestres) avant tout usage
# budgetaire ferme.
forecasts = {}
for region in df["region"].unique():
    series = q_region[q_region["region"] == region].sort_values("quarter")
    values = series["sellout_meur"].values
    model = ExponentialSmoothing(values, trend="add", damped_trend=True)
    fit = model.fit()
    fcast = fit.forecast(2)
    resid_std = float(np.std(fit.resid)) if len(fit.resid) else 0.0
    forecasts[region] = {
        "history_quarters": series["quarter"].tolist(),
        "history_values": [round(v, 1) for v in values],
        "forecast_values": [round(v, 1) for v in fcast],
        "forecast_ci90_halfwidth": round(1.645 * resid_std, 1),  # intervalle ~90%, approx a partir des residus in-sample
        "backtest_avg_mape_pct": backtests[region]["avg_mape_pct"],
    }

# ----------------------------------------------------------------------------
# CHINE : 3 scenarios explicites plutot qu'un pourcentage arbitraire.
# On rejoue la construction du sell-out Chine sous les 3 hypotheses
# (bearish/base/bullish) pour montrer la sensibilite du forecast au choix
# d'hypothese -- c'est l'outil de decision demande, pas une prediction unique.
# Les amplitudes doivent rester identiques a celles de 01_build_proxy_data.py.
# ----------------------------------------------------------------------------
CHINA_SCENARIOS = {"bearish": 0.00, "base": 0.05, "bullish": 0.12}

def china_factor(month, amplitude):
    t = (month.year - 2024) * 12 + month.month
    t0 = (2025 - 2024) * 12 + 9
    if t < t0:
        return 0.97
    progress = min((t - t0) / 9, 1.0)
    return 0.97 + progress * amplitude

china_rows = df[df["region"] == "Chine"].copy()
china_scenarios_quarterly = {}
for scenario, amplitude in CHINA_SCENARIOS.items():
    # on neutralise le facteur "base" deja applique a l'historique, puis on
    # reapplique le facteur du scenario teste, pour comparer a iso-reste
    base_factor = china_rows["date"].apply(lambda m: china_factor(m, CHINA_SCENARIOS["base"]))
    scenario_factor = china_rows["date"].apply(lambda m: china_factor(m, amplitude))
    adjusted = china_rows["sellout_meur"] * (scenario_factor / base_factor)
    tmp = china_rows.copy()
    tmp["sellout_scenario"] = adjusted
    tmp["quarter"] = tmp["date"].dt.to_period("Q").astype(str)
    q_scenario = tmp.groupby("quarter")["sellout_scenario"].sum()
    china_scenarios_quarterly[scenario] = {
        "quarters": q_scenario.index.tolist(),
        "values": [round(v, 1) for v in q_scenario.values],
    }

# --- Series mensuelles par region (chart principal) ---
monthly_region = (
    df.groupby(["mois", "region"])["sellout_meur"].sum().reset_index()
    .pivot(index="mois", columns="region", values="sellout_meur")
    .reset_index()
)

# --- Stock / couverture mensuelle globale (pour le chart sell-in/stock) ---
monthly_stock = df.groupby("mois")[["sellout_meur", "sellin_meur", "stock_meur"]].sum().reset_index()

# --- Mix par ligne produit (12 derniers mois) ---
last_12 = df[df["date"] >= df["date"].max() - pd.DateOffset(months=11)]
mix_line = last_12.groupby("ligne_produit")["sellout_meur"].sum()
mix_line_pct = (mix_line / mix_line.sum() * 100).round(1).to_dict()

# --- KPIs ---
china_q = q_region[q_region["region"] == "Chine"].sort_values("quarter")
china_growth_yoy_pct = round(
    (china_q["sellout_meur"].iloc[-1] / china_q["sellout_meur"].iloc[-5] - 1) * 100, 1
) if len(china_q) >= 5 else None
global_growth_yoy_pct = round(q_total["growth_yoy_pct"].dropna().iloc[-1], 1) if q_total["growth_yoy_pct"].notna().any() else None

kpis = {
    "sellout_total_2025_meur": round(df[df["mois"].str.startswith("2025")]["sellout_meur"].sum(), 1),
    "sellout_total_2026h1_meur": round(df[df["mois"].str.startswith("2026-0")]["sellout_meur"].sum(), 1),
    "china_growth_yoy_pct": china_growth_yoy_pct,
    "global_growth_yoy_pct": global_growth_yoy_pct,
    "mix_ligne_produit_pct": mix_line_pct,
    "couverture_semaines_actuelle": float(q_total["couverture_semaines_moy"].iloc[-1]),
}

output = {
    "monthly_region": monthly_region.to_dict(orient="records"),
    "monthly_stock": monthly_stock.to_dict(orient="records"),
    "quarterly_total": q_total.to_dict(orient="records"),
    "forecasts_by_region": forecasts,
    "backtests_by_region": backtests,
    "china_scenarios_quarterly": china_scenarios_quarterly,
    "kpis": kpis,
}

with open(f"{DATA_DIR}/dashboard_data.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print("KPIs:", json.dumps(kpis, indent=2))
print("\nBacktest MAPE moyen par region:")
for r, b in backtests.items():
    print(f"  {r}: MAPE={b['avg_mape_pct']}%  RMSE={b['avg_rmse_meur']}M€  ({len(b['splits'])} splits)")
print("\nChine - forecast 2 prochains trimestres:", forecasts["Chine"]["forecast_values"],
      "  IC90 ± ", forecasts["Chine"]["forecast_ci90_halfwidth"])
print("Chine - scenarios (derniers trimestres):")
for s, v in china_scenarios_quarterly.items():
    print(f"  {s}: {v['values'][-3:]}")
