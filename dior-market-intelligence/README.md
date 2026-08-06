# Dior Beauty Market Intelligence Prototype — Proxy Sell-out Analytics & Product Lifecycle Modeling

Projet portfolio construit pour une candidature **Business Analyst — Business Développement, Parfums Christian Dior (LVMH)**.

Objectif : récupération et harmonisation de données sell-out/sell-in, construction d'hypothèses de croissance et de projections de marché, analyses ad hoc, recommandations stratégiques 

## ⚠️ Transparence sur les données (à lire en premier)

| Type | Contenu | Statut |
|---|---|---|
| **Chiffres trimestriels/semestriels** (`data/quarterly_public_figures.csv`) | Résultats LVMH, L'Oréal, données Circana | **Réels, publics, sourcés** |
| **Série mensuelle sell-out/sell-in/stock** (`data/monthly_proxy_sellout.csv`) | Répartition mensuelle par région × ligne de produit | **Simulée**, calibrée sur des ordres de grandeur publics |
| **Cycle de vie des lancements** (`data/launch_lifecycle.csv`) | Vélocité de vente post-lancement, segment, canal | **Simulée** (aucune donnée Circana/NPD publique disponible) |

Les panels Circana / Beauty Research sont propriétaires et inaccessibles pour un projet portfolio. La démarche : **reproduire la méthodologie et le pipeline exacts**, avec une donnée proxy transparente, prête à être reconnectée à un vrai flux en production.

### Sur la taille du marché proxy

Total 2025 : **≈ 6,37 Md€ de sell-out proxy annuel**. Ce chiffre est volontairement distinct du CA Dior publié par LVMH (8 174 M€, lettre janvier 2026) : un panel sell-out mesure la consommation finale, pas les ventes de la marque à ses distributeurs. Le mot **proxy** doit systématiquement accompagner ce chiffre.

## Structure du projet

```
dior-market-intelligence/
├── data/
│   ├── quarterly_public_figures.csv    # chiffres réels et sourcés
│   ├── monthly_proxy_sellout.csv       # sell-out/sell-in/stock mensuel simulé
│   ├── launch_lifecycle.csv            # cycle de vie (segment, canal, décision)
│   ├── dashboard_data.json             # agrégats, forecasts, backtests, scénarios (généré)
│   └── dashboard_full.json             # payload complet du dashboard
├── src/
│   ├── 01_build_proxy_data.py          # génération proxy : scénarios Chine + modèle de stock
│   ├── 02_growth_forecast.py           # harmonisation, YoY/QoQ, forecast + backtest rolling-origin
│   └── 03_lifecycle_survival.py        # Kaplan-Meier par segment + table de décision
├── dashboard/
│   └── index.html                      # dashboard interactif (ouvrir dans un navigateur)
├── note/
│   └── note_flash_strategique.docx     # note stratégique 
├── requirements.txt
└── README.md
```

## Ce que chaque brique démontre (et ses limites assumées)

- **`01_build_proxy_data.py`** — harmonisation sell-out/sell-in. Deux points clés :
  - **Chine traitée en scénario, pas en fait établi** : `CHINA_SCENARIOS = {bearish: 0%, base: 5%, bullish: 12%}`. La question d'entretien "comment savez-vous que le rebond est de X% ?" trouve sa réponse dans le code même : on ne l'affirme jamais, on expose 3 hypothèses.
  - **Sell-in dérivé d'un vrai modèle de stock cible** : `Stock_t = Stock_t-1 + SellIn_t − SellOut_t`, avec une couverture cible qui varie (6,5 sem. avant Noël, 3,5 sem. post-fêtes, 5 sem. sinon) — pas un simple ratio sur la saisonnalité.
- **`02_growth_forecast.py`** — projections de marché, avec :
  - **YoY + rolling 12 mois** en plus du QoQ (le QoQ seul est trompeur sur une activité saisonnière).
  - **Backtest rolling-origin** : le forecast est validé sur plusieurs découpages train/test, MAPE et RMSE calculés et affichés — pas un fit "en confiance" sur 8 points.
  - **3 scénarios Chine** recalculés au niveau trimestriel pour comparaison directe.
- **`03_lifecycle_survival.py`** — transposition de la méthode Kaplan-Meier (déjà utilisée dans ChronoRisk sur un tout autre sujet) à la vélocité de lancement, enrichie de :
  - **Segment** (Core Fragrance / Haute Parfumerie / Maquillage / Limited Edition) et **canal** (Retail / E-commerce / Travel Retail).
  - **Table de décision** qui traduit le half-life en action concrète (CRM rapide / distribution standard / investissement storytelling).
- **Dashboard HTML** — vue Comex complète : KPIs, sell-out/mix, sell-in/stock, benchmark concurrentiel, scénarios Chine, validation backtest, cycle de vie par segment, simulateur de croissance interactif.
- **Note flash stratégique (.docx)** — livrable final avec sources citées, section dédiée aux limites du forecast.

## Limites assumées (à dire explicitement en entretien)

- 8 à 10 points trimestriels par région : aucun forecast automatique n'est robuste au sens statistique strict. Le MAPE (~9-10%) le montre plutôt que de le cacher.
- Le rebond Chine n'est jamais un fait : c'est un choix de scénario documenté et modifiable.
- Le modèle de stock est une approximation (couverture cible fixe par saison) — un vrai flux retail intégrerait aussi les ruptures et les promotions.
- En production, il faudrait 12 à 16 trimestres d'historique réel avant tout usage budgétaire ferme.

## Reproduire / faire évoluer

```bash
pip install -r requirements.txt
python src/01_build_proxy_data.py
python src/02_growth_forecast.py
python src/03_lifecycle_survival.py
```

Puis régénérer le dashboard en réinjectant `data/dashboard_full.json` dans `dashboard/template.html` (placeholder `__DATA_JSON__`).

## Prochaine étape naturelle (si le poste le permet)

Remplacer `monthly_proxy_sellout.csv` par une vraie extraction Circana/Beauty Research via connecteur SQL/API — le pipeline (agrégation, KPIs, forecast, backtest, dashboard) reste inchangé.
