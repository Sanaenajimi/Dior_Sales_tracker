const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, Header, Footer,
} = require("docx");

const ACCENT = "7d5f36";
const DARK = "17181a";
const GREY = "6b6b6b";

function h(text, level) {
  return new Paragraph({ text, heading: level, spacing: { before: 240, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 21, ...opts })],
    spacing: { after: 140 },
  });
}
function bullet(text) {
  return new Paragraph({
    text,
    bullet: { level: 0 },
    spacing: { after: 80 },
  });
}
function sourceNote(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 16, color: GREY })],
    spacing: { after: 200 },
  });
}

function kpiCell(label, value, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: "F4F1EC" },
    margins: { top: 120, bottom: 120, left: 120, right: 120 },
    children: [
      new Paragraph({ children: [new TextRun({ text: label, size: 15, color: GREY })] }),
      new Paragraph({ children: [new TextRun({ text: value, size: 26, bold: true, color: DARK })] }),
    ],
  });
}

const doc = new Document({
  sections: [{
    properties: {
      page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1100, right: 1100 } },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "PARFUMS CHRISTIAN DIOR — BUSINESS DEVELOPPEMENT", size: 15, color: GREY })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Note flash stratégique — document portfolio, Sanae Najimi", size: 14, color: GREY })],
        })],
      }),
    },
    children: [
      new Paragraph({
        children: [new TextRun({ text: "NOTE FLASH STRATÉGIQUE", bold: true, size: 32, color: DARK })],
        spacing: { after: 40 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Sell-out / sell-in Q1–H1 2026 — lecture de marché et recommandations", size: 22, color: ACCENT, bold: true })],
        spacing: { after: 240 },
      }),

      h("1. Contexte", HeadingLevel.HEADING_2),
      p("Le premier semestre 2026 confirme une reprise du marché de la beauté prestige, portée par le rebond de la Chine et par la catégorie parfum. Parfums Christian Dior bénéficie des lancements de J'adore Intense et des eaux de parfum Dior Addict, tandis que la dynamique créative de Jonathan Anderson côté Mode & Maroquinerie accélère la désirabilité globale de la Maison."),
      sourceNote("Sources : LVMH — Lettres aux actionnaires janvier et juillet 2026 ; communiqué résultats S1 2026 (résultat opérationnel 8,7 Md€, marge 22,5%)."),

      h("2. Lecture chiffrée (proxy sell-out harmonisé)", HeadingLevel.HEADING_2),
      p("Sur la base d'un jeu de données sell-out/sell-in harmonisé (méthodologie détaillée en annexe technique), la dynamique 2026 se lit comme suit :"),
      new Table({
        width: { size: 9350, type: WidthType.DXA },
        rows: [
          new TableRow({ children: [
            kpiCell("Sell-out proxy 2025 (FY)", "6 374,3 M€", 3117),
            kpiCell("Sell-out proxy H1 2026", "3 097,0 M€", 3117),
            kpiCell("Croissance Chine YoY (scénario base)", "+4,5 %", 3116),
          ]}),
        ],
      }),
      new Paragraph({ text: "", spacing: { after: 160 } }),
      p("La lecture est volontairement en glissement annuel (YoY) plutôt qu'en variation trimestre sur trimestre (QoQ) : sur une activité aussi saisonnière que le parfum, un QoQ seul est trompeur. La croissance chinoise ci-dessus correspond au scénario \"base\" (rattrapage modéré, +5 points progressifs) — les scénarios bearish (0 pt) et bullish (+12 pts) sont modélisés séparément et disponibles dans le dashboard interactif, par souci de ne jamais présenter une hypothèse de marché comme un fait établi."),
      sourceNote("Sources : LVMH T1/S1 2026 ; L'Oréal T1/S1 2026 (Luxe +4,8% T1, groupe +6,5% S1) ; Circana US Prestige Beauty (+6% T1 2026)."),

      h("3. Positionnement concurrentiel", HeadingLevel.HEADING_2),
      bullet("L'Oréal Luxe (YSL, Prada, Armani, Valentino) surperforme actuellement sur le parfum en croissance à deux chiffres, tirée par des lancements type Prada Paradigme et YSL Libre, désormais n°1 mondial du parfum féminin."),
      bullet("LVMH Parfums & Cosmétiques reste stable en organique au S1 2026 (marge en légère hausse) — un écart de croissance face à L'Oréal Luxe qui mérite d'être suivi trimestre après trimestre."),
      bullet("Le marché Circana confirme que le parfum reste le premier moteur de croissance du prestige (24% des ventes, 37% de la croissance en valeur en 2025), avec une polarisation prix marquée : extraits/collections haut de gamme d'un côté, formats mini/travel de l'autre."),
      sourceNote("Sources : L'Oréal communiqués T1/S1 2026 ; Circana / WWD Fragrance Trends 2025."),

      h("4. Hypothèses de croissance — 2 scénarios", HeadingLevel.HEADING_2),
      p("Scénario A — Montée en gamme (effet mix-prix) : accélérer La Collection Privée et les extraits de parfum pour capter la clientèle prête à investir davantage, dans la continuité du lancement Cuir Saddle."),
      p("Scénario B — Accessibilité (effet volume) : renforcer l'offre mini/travel size et les formats découverte, segment en forte croissance en unités (jusqu'à +15% selon Circana sur le fragrance mass), pour capter une cible plus jeune et sensible au prix sans diluer le prestige de la Maison."),
      p("Le simulateur joint (dashboard interactif) permet de faire varier ces deux effets et de projeter leur impact sur les 2 prochains trimestres, région par région — un format directement réutilisable pour les exercices de type 3YP / roadmap budgétaire."),

      h("5. Recommandation", HeadingLevel.HEADING_2),
      p("Prioriser un double mouvement : (1) capitaliser sur le momentum chinois en accélérant la disponibilité des lancements Collection Privée sur ce marché tant que le rebond est confirmé, et (2) tester un format mini/travel sur 1-2 références phares (Sauvage, J'adore) en marché mature (France, US) pour capter la demande jeune sans cannibaliser le cœur de gamme — à valider par un test A/B sell-out sur 2 trimestres."),

      h("6. Limites et robustesse du forecast", HeadingLevel.HEADING_2),
      p("Un backtest rolling-origin (entraînement sur une fenêtre glissante, test sur les 2 trimestres suivants) donne un MAPE moyen de 9 à 10% selon les régions — une fourchette d'erreur assumée, pas cachée derrière un chiffre présenté \"en confiance\". Avec seulement 8 points trimestriels d'historique par région, aucun forecast automatique ne peut remplacer un jugement métier ferme ; il faudrait 12 à 16 trimestres réels avant de s'y fier pour un arbitrage budgétaire."),

      new Paragraph({ text: "", spacing: { after: 200 } }),
      new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 6, color: "E6E1D6" } },
        spacing: { before: 100 },
        children: [new TextRun({ text: "Annexe méthodologique", bold: true, size: 18, color: DARK })],
      }),
      p("Les chiffres trimestriels cités (LVMH, L'Oréal, Circana) sont réels et sourcés. La série mensuelle harmonisée sell-out/sell-in est une reconstruction proxy — un ordre de grandeur de consommation finale type panel Circana, volontairement distinct du chiffre de ventes brutes Dior publié par LVMH (8 174 M€, lettre janvier 2026). Le sell-in est dérivé d'un modèle de stock cible explicite (Stock_t = Stock_t-1 + Sell-in_t − Sell-out_t), pas d'un simple ratio. Le forecast utilise un lissage exponentiel à tendance amortie, validé par backtest rolling-origin (section 6). Méthodologie complète dans le repository du projet.", { size: 17, color: GREY }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => require("fs").writeFileSync("note_flash_strategique.docx", buf));
