// ═══════════════════════════════════════════════════════════════════
//  poems.js — Comprehensive data store for the Prozorro Research Platform
//  Contains: Shevchenko anthology, full paper content, all numerical data
// ═══════════════════════════════════════════════════════════════════

export const POEMS = [
  {
    uk: "Борітеся — поборете,\nВам Бог помагає!\nЗа вас правда, за вас слава\nІ воля святая!",
    en: "Struggle — and you shall overcome,\nFor God is with you!\nTruth is for you, glory is for you,\nAnd holy freedom!",
    attr: "Taras Shevchenko — The Caucasus (Кавказ), 1845"
  },
  {
    uk: "В своїй хаті своя й правда,\nІ сила, і воля.",
    en: "In your own home — your own truth,\nYour own strength, your own freedom.",
    attr: "Taras Shevchenko — Menì zdaiet'sia, 1847"
  },
  {
    uk: "Встане правда! встане воля!\nІ тобі одній, одній\nПомоляться всі народи\nВовіки і віки.",
    en: "Truth shall rise! Freedom shall rise!\nAnd to you alone, alone,\nAll peoples shall pray\nForever and ever.",
    attr: "Taras Shevchenko — Subterranean Streams, 1859"
  },
  {
    uk: "Як умру, то поховайте\nМене на могилі,\nСеред степу широкого,\nНа Вкраїні милій.",
    en: "When I die, bury me\nOn a hillock,\nAmid the wide steppe,\nIn my beloved Ukraine.",
    attr: "Taras Shevchenko — Zapovit (Testament), 1845"
  },
  {
    uk: "І на оновленій землі\nВрага не буде, супостата,\nА буде син, і буде мати,\nА будуть люде на землі.",
    en: "And on the newly-ransomed earth\nNo enemy, no foe shall be,\nBut there shall be a son, a mother,\nAnd there shall be folk on the earth.",
    attr: "Taras Shevchenko — І Архімед, і Галілей, 1860"
  },
  {
    uk: "Учітеся, брати мої,\nДумайте, читайте,\nІ чужому научайтесь,\nЙ свого не цурайтесь.",
    en: "Study, my brothers,\nThink and read,\nLearn from others,\nBut do not forsake your own.",
    attr: "Taras Shevchenko — І мертвим, і живим, 1845"
  }
];

export const PAPER = {
  title: "The Regime That Redistributed the Signal",
  subtitle: "How Ukraine's 2022 Wartime Procurement Reform Reorganized the Predictors of Non-Competitive Public Procurement",
  version: "V_20260513_223800",
  abstract: `Ukraine's Prozorro e-procurement platform publishes every public tender in machine-readable form. On 24 February 2022, emergency wartime simplified procurement procedures were introduced following Russia's full-scale invasion; in October 2022, Cabinet Resolution No. 1178 formalized these procedures — reducing timeline requirements, expanding direct contracting, and crucially normalizing single-bidder participation as a valid tender outcome rather than a cancellation trigger. We use the 24 February 2022 boundary as the regime split and exploit this regime change to ask not whether single-bidder rates changed in level, but whether the predictive structure of non-competitive outcomes changed.`,
  
  introduction: `Since the mid-2010s, a wave of digital public-procurement reforms has sought to leverage mandatory transparency to constrain the discretion that traditionally enabled non-competitive procurement outcomes (Bosio et al., 2022). Ukraine's Prozorro system, launched in 2016 and designed through a public–private partnership, is the most extensively documented instance: every tender's documentation, every submitted bid, every award decision, and every contract modification is published to a searchable public API. The architectural premise was that radical transparency would, by itself, raise the cost of collusion and lower the cost of external scrutiny sufficient to deter procurement corruption. The February 2022 Russian invasion of Ukraine provided a rare quasi-experimental opportunity. This paper asks: how did the 2022 regime change reshape the features that predict single-bidder outcomes?`,

  methodology: `We train three independent binary classifiers using an identical pipeline but different data subsets: a peacetime model (pre-2022-02-24), a wartime model (post-2022-02-24), and a pooled model with regime as a feature. This design separates the questions of predictive performance from predictive structure. LightGBM is the primary learner, chosen for its native handling of mixed-type features, missing values, and categoricals; for reliable non-linear learning at scale; and for compatibility with TreeSHAP. Hyperparameter search uses random search across fifty trials per model variant (independently per variant). Isotonic calibration is fitted on the validation fold.`,

  leakage: `Five layers prevent target leakage: (1) An authoritative allowlist of 51 pre-tender features; (2) An exhaustive blacklist of ~45 forbidden columns enumerating all WINNING_*, STAT_PRICE_*, SIGNAL_BID_*, auction-dynamic, and post-award signals; (3) SQL-view discipline with explicit SELECT lists generated from the allowlist; (4) A CI test suite blocking on any leakage violation; (5) A synthetic-oracle probe injecting Z_SYNTH = y + Gaussian(SNR=2) — the oracle must rank #1 by SHAP, and no real feature may exceed 50% of its importance. All three models passed; the largest real-feature ratio was 30.6%.`,

  discussion: `The quantitative story has three components. First, in-regime test performance is similar (AUC 0.771 vs. 0.791) while cross-regime transfer degrades asymmetrically — peacetime→wartime drops 0.130 AUC, 6.5× larger than the wartime→peacetime drop. Second, family-level SHAP confirms structural reorganization: Family A drops 2.3× while E, B, and I rise. Third, cluster analysis reveals wartime-specific tender archetypes that do not appear in peacetime output. The February 2022 wartime boundary is associated with a redistribution of predictive weight across feature families, not a reduction in overall predictability.`,

  conclusion: `Ukraine's 2022 wartime simplification did not reduce the predictability of non-competitive outcomes; it reorganized the features that carry predictive weight. Procedural-configuration features decline 2.3× while CPV-category, timing, and procurer-history rise. The broader lesson is that procurement-corruption research cannot rely on stable feature sets across regulatory regimes. When a regulatory environment changes, the predictors of single-bidder outcomes shift in structured, observable ways.`,

  contributions: [
    { icon: "⚖️", title: "Three-Model Comparative Design", body: "Independent peacetime, wartime, and pooled LightGBM classifiers trained on identical pipelines — separating predictive performance from predictive structure. The pooled model serves as an anchor for regime-specific SHAP comparisons." },
    { icon: "🔒", title: "Five-Layer Leakage Prevention", body: "Authoritative allowlist (51 features), exhaustive blacklist (~45 entries), SQL-view discipline, CI test suite, and synthetic-oracle probe. Largest real-feature ratio: 30.6% of oracle importance (FLAG_BELOW_THRESHOLD_WITH_BIDDING, peacetime)." },
    { icon: "📊", title: "SHAP Redistribution Quantified", body: "Family A (tender configuration) drops 2.3× (1.998 → 0.877, Cohen's d = −1.96). CPV-category (E), timing (B), and procurer-history (I) features rise. Effect sizes range from large (d = −1.96) to negligible (d = −0.20)." },
    { icon: "↔️", title: "Asymmetric Cross-Regime Transfer", body: "Peacetime→wartime loses 0.130 AUC (0.771 → 0.642). Wartime→peacetime loses only 0.020 AUC. The asymmetry (6.5×) indicates wartime contains genuinely novel predictive structure absent from peacetime data." },
    { icon: "🧪", title: "Corrected Permutation Test", body: "Feature-count-matched baseline with 1,000 permutations. Typology grouping is privileged in peacetime (p = 0.007) and pooled (p = 0.003) but NOT in wartime (p = 0.066) — structural relevance is itself regime-dependent." },
    { icon: "🔬", title: "SHAP-Vector Cluster Analysis", body: "k-means (k=10) on L2-normalized SHAP vectors produces 30 themes. All 10 peacetime clusters are Family-A-dominant. Wartime introduces E-dominant, D-dominant, and I-dominant clusters that do not appear in peacetime." }
  ],

  // Feature families with full paper data
  families: [
    { letter:"A", name:"Tender Configuration", count:11, mech:"Specification manipulation (I.a)", grounding:"Auriol (2006): restrictive procedure as gatekeeper", peace:1.998, war:0.877, pooledW:1.330, pooledP:2.361, delta:-1.121, ks:0.859, cohen:-1.96, direction:"↓ large", ablationP:0.069, ablationW:0.040, features:"PROCUREMENT_METHOD_TYPE, FLAG_RESTRICTED_PROCEDURE, FLAG_NO_CALL_FOR_TENDER, FLAG_BELOW_THRESHOLD_WITH_BIDDING, CONFIG_HAS_AUCTION, CONFIG_HAS_ENQUIRIES, CONFIG_MIN_BIDS, CONFIG_RESTRICTED" },
    { letter:"B", name:"Timing", count:7, mech:"Compressed timelines (II.a), late amendments (II.d)", grounding:"Bandiera et al. (2009): bureaucratic cost", peace:0.269, war:0.349, pooledW:0.324, pooledP:0.328, delta:0.080, ks:0.414, cohen:0.54, direction:"↑ medium", ablationP:0.055, ablationW:0.024, features:"SIGNAL_ENQUIRY_PERIOD_HOURS, SIGNAL_TENDER_PERIOD_HOURS, below-legal-min flags, peer-median ratio" },
    { letter:"C", name:"Calendar", count:5, mech:"Temporal sabotage (III)", grounding:"Descriptive; oversight avoidance", peace:0.041, war:0.066, pooledW:0.115, pooledP:0.082, delta:0.025, ks:0.508, cohen:0.78, direction:"↑ medium", ablationP:0.008, ablationW:0.012, features:"FLAG_IS_DECEMBER_PUBLISH, FLAG_IS_UKRAINIAN_HOLIDAY_PUBLISH, FLAG_IS_WARTIME_REGIME" },
    { letter:"D", name:"Value / Threshold", count:5, mech:"Sub-threshold fragmentation (VI.b)", grounding:"Bosio et al. (2022): threshold effects", peace:0.373, war:0.332, pooledW:0.358, pooledP:0.304, delta:-0.041, ks:0.108, cohen:-0.20, direction:"↓ negligible", ablationP:0.042, ablationW:0.028, features:"VALUE_AMOUNT (log), GUARANTEE_AMOUNT, DERIVED_NEAR_THRESHOLD_RATIO" },
    { letter:"E", name:"Item / CPV Structure", count:5, mech:"Taxonomic obfuscation (VI.a)", grounding:"Decarolis et al. (2020): discretion via specification", peace:0.356, war:0.515, pooledW:0.387, pooledP:0.300, delta:0.158, ks:0.245, cohen:0.59, direction:"↑ medium", ablationP:0.058, ablationW:0.054, features:"SIGNAL_ITEM_COUNT, SIGNAL_CPV_HETEROGENEITY, STAT_PRIMARY_CPV_4DIGIT" },
    { letter:"F", name:"Documentation Quality", count:2, mech:"Vague specs, documentation gaps (I.c)", grounding:"Lessig (2013): institutional opacity", peace:0.026, war:0.006, pooledW:0.021, pooledP:0.022, delta:-0.021, ks:0.948, cohen:-2.43, direction:"↓ large*", ablationP:0.003, ablationW:0.001, features:"FLAG_MISSING_TENDER_DOCUMENTATION, FLAG_DESCRIPTION_LENGTH_SUSPICIOUS" },
    { letter:"G", name:"Sector", count:7, mech:"Sector-specific base rates", grounding:"Bosio et al. (2022): sector heterogeneity", peace:0.023, war:0.035, pooledW:0.024, pooledP:0.026, delta:0.012, ks:0.335, cohen:0.81, direction:"↑ large", ablationP:0.005, ablationW:0.007, features:"FLAG_CPV_CONSTRUCTION, FLAG_CPV_MEDICAL_PHARMA, FLAG_RECONSTRUCTION_RELATED" },
    { letter:"H", name:"Procurer Identity", count:4, mech:"Entity-type base rates", grounding:"Bandiera et al. (2009): entity heterogeneity", peace:0.097, war:0.111, pooledW:0.102, pooledP:0.104, delta:0.014, ks:0.107, cohen:0.18, direction:"↑ negligible", ablationP:0.012, ablationW:0.015, features:"PROCURER_KIND, PROCURER_REGION, FLAG_PROCURER_DEFENSE, FLAG_PROCURER_MUNICIPAL" },
    { letter:"I", name:"Procurer History", count:9, mech:"Capture context (I.a, IV)", grounding:"Decarolis et al. (2020): revealed preference", peace:0.211, war:0.317, pooledW:0.292, pooledP:0.287, delta:0.106, ks:0.323, cohen:0.91, direction:"↑ large", ablationP:0.035, ablationW:0.022, features:"HIST_SINGLE_BIDDER_RATE_365D, HIST_SUPPLIER_HHI_365D, prior tender count" },
    { letter:"J", name:"CPV Market Context", count:3, mech:"Thin markets → single bidders", grounding:"Auriol (2006): market structure", peace:0.224, war:0.249, pooledW:0.258, pooledP:0.280, delta:0.025, ks:0.107, cohen:0.22, direction:"↑ small", ablationP:0.018, ablationW:0.012, features:"CPV_SUPPLIER_COUNT_365D, CPV_MARKET_HHI_365D, CPV base single-bidder rate" },
    { letter:"K", name:"Geographic Match", count:3, mech:"Geographic discrimination (I.d)", grounding:"TI-Ukraine: delivery-region manipulation", peace:0.007, war:0.014, pooledW:0.012, pooledP:0.011, delta:0.007, ks:0.394, cohen:0.96, direction:"↑ large", ablationP:0.002, ablationW:0.004, features:"Delivery-region count, procurer-region match flag" }
  ],

  // Full performance table from metrics.csv — Run V_20260513_223800 (34 features, full sample)
  performance: [
    { model:"Peacetime",             algo:"LightGBM", auc:0.783, logLoss:0.524, brier:0.183, accuracy:0.688, precision:0.824, recall:0.672, f1:0.741, n:10042, color:"#3b82f6" },
    { model:"Wartime",               algo:"LightGBM", auc:0.772, logLoss:0.558, brier:0.190, accuracy:0.708, precision:0.767, recall:0.748, f1:0.757, n:54858, color:"#f59e0b" },
    { model:"Pooled (wartime test)",  algo:"LightGBM", auc:0.768, logLoss:0.556, brier:0.190, accuracy:0.702, precision:0.753, recall:0.758, f1:0.756, n:54858, color:"#10b981" },
    { model:"Pooled (peacetime test)",algo:"LightGBM", auc:0.870, logLoss:0.425, brier:0.142, accuracy:0.795, precision:0.819, recall:0.885, f1:0.851, n:10042, color:"#059669" },
  ],

  // Transfer matrix — metrics.csv V_20260513_223800
  transfer: [
    { model:"Peacetime", test:"Peacetime", kind:"native",   n:10042, auc:0.783, logLoss:0.524, accuracy:0.688, precision:0.824, recall:0.672, f1:0.741 },
    { model:"Peacetime", test:"Wartime",   kind:"transfer", n:54858, auc:0.546, logLoss:0.715, accuracy:0.533, precision:0.632, recall:0.560, f1:0.594 },
    { model:"Wartime",   test:"Wartime",   kind:"native",   n:54858, auc:0.772, logLoss:0.558, accuracy:0.708, precision:0.767, recall:0.748, f1:0.757 },
    { model:"Wartime",   test:"Peacetime", kind:"transfer", n:10042, auc:0.771, logLoss:0.534, accuracy:0.705, precision:0.726, recall:0.891, f1:0.800 },
    { model:"Pooled",    test:"Wartime",   kind:"native",   n:54858, auc:0.768, logLoss:0.556, accuracy:0.702, precision:0.753, recall:0.758, f1:0.756 },
    { model:"Pooled",    test:"Peacetime", kind:"native",   n:10042, auc:0.870, logLoss:0.425, accuracy:0.795, precision:0.819, recall:0.885, f1:0.851 }
  ],

  // Permutation test results from Table 6b
  permutation: [
    { model:"Peacetime", baseAuc:0.771, typologyDeltaAuc:0.277, randomMeanDeltaAuc:0.137, randomStd:0.051, randomMaxDeltaAuc:0.293, pValue:0.007, significant:true },
    { model:"Wartime",   baseAuc:0.791, typologyDeltaAuc:0.267, randomMeanDeltaAuc:0.145, randomStd:0.069, randomMaxDeltaAuc:0.394, pValue:0.066, significant:false },
    { model:"Pooled",    baseAuc:0.792, typologyDeltaAuc:0.291, randomMeanDeltaAuc:0.128, randomStd:0.051, randomMaxDeltaAuc:0.307, pValue:0.003, significant:true }
  ],

  // Interpretation clusters from Table 9
  clusters: [
    { variant:"Peacetime", size:4386, dominant:"A", meanPred:0.526, label:"Tender config-dominant" },
    { variant:"Peacetime", size:2009, dominant:"A", meanPred:0.239, label:"Tender config-dominant (low-risk)" },
    { variant:"Peacetime", size:1955, dominant:"A", meanPred:0.962, label:"Tender config-dominant (high-risk)" },
    { variant:"Wartime",   size:3119, dominant:"A", meanPred:0.439, label:"Tender config-dominant" },
    { variant:"Wartime",   size:2569, dominant:"E", meanPred:0.733, label:"CPV structure-dominant" },
    { variant:"Wartime",   size:2468, dominant:"A", meanPred:0.396, label:"Tender config-dominant" },
    { variant:"Wartime",   size:1119, dominant:"E", meanPred:0.788, label:"CPV structure-dominant (high-risk)" },
    { variant:"Wartime",   size:909,  dominant:"D", meanPred:0.744, label:"Value/threshold-dominant" },
    { variant:"Wartime",   size:813,  dominant:"I", meanPred:0.719, label:"Procurer history-dominant" },
    { variant:"Pooled",    size:2922, dominant:"A", meanPred:0.467, label:"Tender config-dominant" },
    { variant:"Pooled",    size:1458, dominant:"E", meanPred:0.798, label:"CPV structure-dominant" },
    { variant:"Pooled",    size:941,  dominant:"A", meanPred:0.514, label:"Tender config-dominant" }
  ],

  // Sample statistics
  sample: { total:4540000, peacetimeFull:2599506, wartimeFull:1907783, testPeacetime:10042, testWartime:54858, nFeatures:34, regimeBoundary:"2022-10-12", peacetimeRate:0.662, wartimeRate:0.609 },

  // Temporal splits from Table in §4.3
  splits: {
    peacetime: { train:"2016-01-01 → 2021-03-31", val:"2021-04-01 → 2021-09-30", test:"2021-10-01 → 2022-02-23" },
    wartime:   { train:"2022-02-24 → 2024-12-31", val:"2025-01-01 → 2025-06-30", test:"2025-07-01 → 2025-12-31" },
    pooled:    { train:"2016-01-01 → 2024-12-31", val:"2025-01-01 → 2025-06-30", test:"Both peacetime & wartime test windows" }
  },

  refs: [
    "Acemoglu, D., Johnson, S., & Robinson, J. A. (2001). The colonial origins of comparative development. American Economic Review, 91(5), 1369–1401.",
    "Auriol, E. (2006). Corruption in procurement and public purchase. International Journal of Industrial Organization, 24(5), 867–885.",
    "Bandiera, O., Prat, A., & Valletti, T. (2009). Active and passive waste in government spending. American Economic Review, 99(4), 1278–1308.",
    "Bosio, E., Djankov, S., Glaeser, E., & Shleifer, A. (2022). Public procurement in law and practice. American Economic Review, 112(4), 1091–1117.",
    "Decarolis, F., Fisman, R., Pinotti, P., & Vannutelli, S. (2020). Rules, discretion, and corruption in procurement. NBER Working Paper No. 28209.",
    "Ke, G. et al. (2017). LightGBM: A highly efficient gradient boosting decision tree. NeurIPS 30.",
    "Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. NeurIPS 30.",
    "Lessig, L. (2013). Institutional corruptions. Edmond J. Safra Working Papers No. 1.",
    "Rose-Ackerman, S. (1999). Corruption and government. Cambridge University Press.",
    "Kaufmann, D., & Vicente, P. C. (2011). Legal corruption. Economics and Politics, 23(2), 195–219.",
    "Transparency International Ukraine. (2017–2023). Prozorro monitoring reports. ti-ukraine.org."
  ]
};
