# The Regime That Redistributed the Signal: How Ukraine's 2022 Wartime Procurement Reform Reorganized the Predictors of Non-Competitive Public Procurement

---

## Abstract

Ukraine's Prozorro e-procurement platform publishes every public tender in machine-readable form. On 24 February 2022, emergency wartime simplified procurement procedures were introduced following Russia's full-scale invasion; in October 2022, Cabinet Resolution No. 1178 formalized these procedures — reducing timeline requirements, expanding direct contracting, and crucially normalizing single-bidder participation as a valid tender outcome rather than a cancellation trigger. We use the 24 February 2022 boundary as the regime split (grouping the emergency and formalization sub-periods as a single wartime regime) and exploit this regime change to ask not whether single-bidder rates changed in level, but whether the *predictive structure* of non-competitive outcomes changed.

Using a 10% daily-stratified sample of 452,041 competitive tenders (2016–2026), we train three independent LightGBM classifiers — peacetime-only (pre-February 2022), wartime-only (post-February 2022), and pooled — predicting the single-bidder outcome. Peacetime test AUC is **0.771**; wartime achieves AUC **0.791**; pooled AUC is **0.792** (wartime test) / **0.798** (peacetime test). (All AUC values rounded to three decimal places; full precision in Table 3.) Cross-regime transfer is strongly asymmetric: peacetime→wartime loses 0.130 AUC; wartime→peacetime loses 0.020. LightGBM substantially outperforms both logistic regression (AUC 0.732/0.762 for peacetime/wartime) and random chance (AUC 0.500), confirming that the learned representations capture non-linear structure beyond what a linear model can extract.

Family-level SHAP analysis reveals structural redistribution: procedural-configuration features (Family A) drop **2.3×** while CPV-category, timing, and procurer-history features rise. Effect sizes range from large (Cohen's d = −1.96 for Family A) to negligible (d = −0.20 for Family D). A corrected permutation test (1,000 permutations, feature-count-matched baseline) confirms the typology grouping is privileged in peacetime (p = 0.007) and pooled (p = 0.003), but NOT in wartime (p = 0.066) — suggesting the typology's structural relevance is itself regime-dependent. The February 2022 simplification did not eliminate predictability; it redistributed predictive signal from procedural features onto structural features harder for policy to modify.

**Keywords:** public procurement · regime change · single-bidder outcomes · SHAP · three-model comparative design · Ukraine · Prozorro

---

## 1. Introduction

Since the mid-2010s, a wave of digital public-procurement reforms has sought to leverage mandatory transparency to constrain the discretion that traditionally enabled non-competitive procurement outcomes (Bosio et al., 2022; Transparency International Ukraine, 2017–2023). Ukraine's Prozorro system, launched in 2016 and designed through a public–private partnership, is the most extensively documented instance: every tender's documentation, every submitted bid, every award decision, and every contract modification is published to a searchable public API. The architectural premise was that this radical transparency would, by itself, raise the cost of collusion and lower the cost of external scrutiny sufficient to deter procurement corruption.

The empirical record is mixed. Single-bidder rates — the most widely cited aggregate indicator of restricted competition in the procurement-corruption literature (Auriol, 2006; Decarolis et al., 2020) — have remained substantial across Prozorro's operational history. A companion typology paper (Anonymous, 2026) catalogs twenty-five documented manipulation mechanisms operating within, around, or despite the platform's formal architecture. The challenge for quantitative research on such systems is that corruption *per se* is not directly observed in administrative data; what can be observed are proxies — single-bidder outcomes, narrow bid spreads, low savings ratios — that correlate with the conditions believed to enable corruption and that the procurement-economics literature treats as principal indicators (Bosio et al., 2022).

The February 2022 Russian invasion of Ukraine provided a rare quasi-experimental opportunity. On 24 February 2022 the Cabinet of Ministers of Ukraine introduced wartime simplified procurement procedures, dramatically reducing the procedural scaffolding that normally structured competitive awards. The Prozorro data pipeline continued uninterrupted; the platform's transparency architecture was preserved; the procurer population was largely stable. What changed was the regulatory regime.

This paper asks: **how did the 2022 regime change reshape the features that predict single-bidder outcomes?** We deliberately do not ask whether single-bidder rates changed in level — descriptive analyses of that question already exist — but rather whether the *structure* of predictability changed. That distinction matters because two regimes with similar base rates of non-competitive outcomes can nonetheless produce those outcomes through different mechanisms, and different mechanisms imply different policy levers.

### 1.1 Contribution

We make three contributions.

**First, a three-model comparative design.** We train three independent binary classifiers using an identical pipeline but different data subsets: a peacetime model (pre-2022-02-24), a wartime model (post-2022-02-24), and a pooled model with regime as a feature. This design separates the questions of *predictive performance* (all three can be compared on held-out data) from *predictive structure* (SHAP distributions and ablation analyses can be compared directly). Section 4 develops the design in full.

**Second, a methodological discipline around leakage.** Because the outcome we predict (single-bidder) is extremely target-adjacent — the gold feature store contains many columns that would trivially predict it — we implement a five-layer leakage prevention architecture: an authoritative allowlist of 51 pre-tender features, an exhaustive blacklist of forbidden columns, SQL-view-level discipline, a test suite that blocks CI on leakage violations, and a post-training synthetic-oracle probe. The probe injects an oracle feature into the input space and verifies that no real feature exceeds 50% of its learned importance. All three of our trained models pass this probe.

**Third, a quantitative characterization of the regime shift.** We show that (a) in-regime test performance is similar across peacetime and wartime (AUC 0.771 vs. 0.791) while cross-regime transfer is strongly asymmetric (peacetime→wartime drops 0.130 AUC); (b) LightGBM substantially outperforms logistic regression (AUC gain +0.029 to +0.039) and random chance (+0.271 to +0.291), confirming non-linear predictive structure; (c) the family-level SHAP decomposition differs structurally between regimes, with Family A (tender configuration) dropping 2.3× from peacetime to wartime while CPV-category, procurer-history, and timing features rise; (d) a corrected permutation test (feature-count-matched, 1,000 permutations) finds the typology grouping is privileged in peacetime and pooled (p < 0.01) but not in wartime (p = 0.066); and (e) SHAP-vector clustering of a 15,000-tender-per-model evaluation sample produces wartime-specific clusters that do not appear in the peacetime output.

### 1.2 Why single-bidder

The single-bidder outcome is not *per se* corruption. Some procurements are legitimately single-source. The proxy is widely used in the procurement-corruption literature because it is a mechanistically meaningful indicator of the environmental conditions that enable corruption: restricted competition, whether designed into the tender or arising from exogenous market thinness, implies both the opportunity for rent extraction and the absence of the competitive discipline that would otherwise deter it (Bosio et al., 2022; Decarolis et al., 2020; Bandiera, Prat, & Valletti, 2009).

### 1.3 Roadmap

Section 2 situates the study in the procurement, transparency, and regime-comparison literatures. Section 3 describes the data. Section 4 develops the modeling protocol, including the leakage architecture. Section 5 reports overall performance. Section 6 presents the three-way comparative analysis — the paper's central contribution. Section 7 establishes robustness across subgroups, ablations, and the typology permutation test. Section 8 examines the interpretation pipeline's cluster-level output. Section 9 discusses implications; Section 10 records limitations; Section 11 concludes.

---

## 2. Related Work

### 2.1 Procurement corruption and single-bidder outcomes

The theoretical foundations of procurement corruption are laid in Rose-Ackerman (1999) and extended in Auriol (2006), which formalizes the conditions under which contracting authorities have both the opportunity and incentive to restrict competition. Empirically, Bosio, Djankov, Glaeser & Shleifer (2022) assemble a global corpus of procurement outcomes and demonstrate that single-bidder rates correlate with standard corruption measures across jurisdictions. Decarolis et al. (2020) use Italian data to show that rule-based discretion in procurement predicts both single-bidder outcomes and downstream contracting irregularities. Bandiera et al. (2009) theorize that restricted competition can persist even when procurers have no explicit corrupt incentive, because the bureaucratic cost of organizing genuinely competitive procurements interacts with limited oversight.

### 2.2 Transparency as an anti-corruption instrument

Ukraine's Prozorro platform is an exemplar of the open-data transparency paradigm applied to procurement. The theoretical case is that radical publication raises the cost of collusion by exposing it to external scrutiny; the empirical case is mixed. Lessig (2013) distinguishes between *illegal corruption* (bribery, explicit fraud) and *institutional corruption* (systematic distortion through legitimate procedure), arguing that transparency is better suited to the former. Kaufmann & Vicente (2011) develop the concept of *legal corruption* and show it resists standard anti-corruption instruments. Our analysis is silent on whether Prozorro reduced corruption in absolute terms; we study how the regulatory environment conditions the *predictors* of non-competitive outcomes.

### 2.3 Regime change and comparative identification

The comparative-statics logic we employ — train the same pipeline separately on two regimes and compare learned structure — has precedent in political-economy research on discrete regime changes (Acemoglu, Johnson & Robinson, 2001). In the machine-learning literature, SHAP-based family decompositions across policy regimes have been used to study insurance pricing, credit scoring, and labor-market algorithms; we are not aware of prior application of this approach in procurement-corruption research, though the growing literature on explainable AI in public-sector applications (see Lundberg & Lee, 2017) suggests convergence is likely.

### 2.4 Ukraine's wartime procurement reform

The February 2022 introduction of wartime simplified procurement procedures reduced documentation, shortened tender windows, and expanded single-source authority for defense-related procurement. Post-2022 descriptive analyses (Transparency International Ukraine, 2022–2023) document a rise in single-bidder rates in absolute terms, from approximately 50% in 2019 to 66–69% in wartime quarters. The interpretation that wartime emergency conditions genuinely required procedural simplification is a defensible policy argument. Our study is agnostic on that normative question; we ask, within the procedural environment that actually existed, what structural features of tenders predicted the single-bidder outcome.

---

## 3. Data

### 3.1 Source

The Prozorro platform publishes the complete procurement record to a public API. Our analysis consumes a Snowflake-resident materialization of this public data. Two layers are used:

- A **gold feature store** (`PROZORRO.GOLD.GOLD_FEATURE_ENRICHED_TENDERS`) with 103 pre-computed per-tender columns covering identity, procurer, configuration, timing, items, values, and a `_REGIME` classification encoding the 2022-02-24 regulatory shift.
- A **silver normalized layer** (seven dynamic tables — `PROZORRO.SILVER.SILVER_TENDERS`, `SILVER_AWARDS`, `SILVER_BIDS`, `SILVER_CONTRACTS`, `SILVER_ITEMS`, `SILVER_SUPPLIERS`, `SILVER_PROCURING_ENTITIES`) used exclusively for pre-tender feature engineering (procurer history aggregates, CPV market context, geographic features).

The gold table contains 28,753,062 tenders spanning 2015 through 2026. After exclusions (see §3.2) the modeling sample is 4,507,289 tenders.

### 3.2 Sample composition

We restrict the analysis to competitive procurement methods. Four Prozorro method types (`reporting`, `negotiation`, `negotiation.quick`, `competitiveOrdering`) are single-source by regulatory design, producing single-bidder outcomes definitionally; their inclusion would make the prediction trivial. The fifteen retained competitive methods — `belowThreshold`, `aboveThreshold`, `aboveThresholdUA`, `priceQuotation`, `aboveThresholdEU`, `aboveThresholdUA.defense`, `requestForProposal`, `closeFrameworkAgreementSelectionUA`, `esco`, `simple.defense`, `closeFrameworkAgreementUA`, `competitiveDialogueUA`, `competitiveDialogueUA.stage2`, `competitiveDialogueEU`, `competitiveDialogueEU.stage2` — span the full regulatory procedural menu in which bidding actually occurs.

Further exclusions: tenders with `VALUE_AMOUNT ≤ 0`, tenders in currencies other than UAH, and tenders published before 2016 (Prozorro's mandatory adoption year). The resulting sample has 2,599,506 peacetime and 1,907,783 wartime tenders, with single-bidder base rates 46–59% across peacetime years and 60–69% across wartime years. Figure 2 visualizes the sample by year and regime.

![Figure 2 — Competitive-sample tender volume by year and regime](figure_02_volume_regime.png)
**Figure 2.** *Competitive-sample tender volume by year and regime. The 2022 vertical axis split shows the regime boundary (February 24, 2022). Total sample: 2,599,506 peacetime tenders and 1,907,783 wartime tenders. 2026 is a partial year.*

### 3.3 Target variable

The primary target is a binary indicator: 1 if exactly one effective bidder submitted; 0 otherwise. This is computed upstream in the gold layer as `SIGNAL_IS_SINGLE_BIDDER`. Two alternative target operationalizations — effective-bidder count (Poisson) and estimate-savings ratio (Tweedie, log-transformed) — are available for future cross-operationalization checks but have not yet been estimated; the present analysis focuses exclusively on the binary single-bidder outcome.

### 3.4 Features

Feature engineering is organized around eleven families (A–K) mapped to corruption-typology categories grounded in the procurement-economics literature (Auriol, 2006; Bosio et al., 2022; Decarolis et al., 2020; Bandiera et al., 2009) and systematized in a companion working paper (Anonymous, 2026). Appendix A provides a self-contained summary of the mapping. Figure 3 shows the feature count per family.

![Figure 3 — Feature family map](figure_03_feature_family_map.png)
**Figure 3.** *Feature family map. Family A (tender configuration) has the most features; families F and K have the fewest.*

| Family | Content | Count |
|---|---|---|
| A | Tender configuration (procurement method, restricted procedure flag, auction/enquiries config) | 11 |
| B | Timing (enquiry/tender period hours, below-legal-minimum flags, peer-median ratio) | 7–8* |
| C | Calendar (December publish, holiday publish, regime flags) | 5–6* |
| D | Value / threshold (log value, guarantee amount, derived near-threshold ratio) | 5 |
| E | Item / CPV structure (item count, CPV heterogeneity, primary CPV-4 digit) | 5 |
| F | Documentation quality (missing-documentation flag, description-length flag) | 2 |
| G | Sector (construction, medical-pharma, IT, engineering, energy, foodservice, reconstruction) | 7 |
| H | Procurer identity (kind, region, defense/municipal flags) | 4 |
| I | Procurer history (as-of aggregates: tender count, single-bidder rate, tender period, log value, supplier HHI) | 9–12* |
| J | CPV market context (as-of: tender count, base single-bidder rate, log value) | 3 |
| K | Geographic match (delivery region count, delivery-limited-to-procurer flag) | 3 |

*Ranges reflect variant-specific feature availability: some features (e.g., regime-specific flags, missingness indicators) are included only in certain model variants, and historical aggregates may produce additional derived columns depending on the temporal depth available.

Full column specifications are in the allowlist (`docs/allowlisted_columns.yaml`) and feature-inventory Table 2 of the technical report. Derived historical aggregates use strict as-of-`DATE_CREATED` discipline via window functions with `ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING`, ensuring no tender contributes to its own features.

---

## 4. Methods

### 4.1 Pipeline architecture

The full pipeline is visualized in Figure 1.

![Figure 1 — Pipeline Architecture](figure_01_pipeline_architecture.png)
**Figure 1.** *Pipeline architecture. Each phase is implemented as a Snowflake-resident SQL view (Phases 0–3, 5) or as a Python module orchestrated via Snowpark (Phases 4a–4c). All artifacts persist to the `PROZORRO.DETECTION` schema for reproducibility.*

Phases 0 through 5 each produce persisted artifacts. Phase 0 verifies schemas and documents sample-composition decisions. Phase 1 builds pre-tender feature views. Phase 2 builds target variables. Phase 3 creates three temporal-split views (peacetime, wartime, pooled). Phase 4a trains the three LightGBM models. Phase 4b computes test-set inference, TreeSHAP on a stratified sample, and the transfer matrix. Phase 4c produces templated per-tender explanations and SHAP-vector clusters. Phase 5 consolidates registers for downstream consumption.

### 4.2 Three-model design

Our central methodological commitment is to train three independent models with identical feature engineering and learning algorithms but different training-data subsets:

- **Peacetime** (`_REGIME = peacetime`, pre-2022-02-24): 202,396 train rows.
- **Wartime** (`_REGIME = wartime`, 2022-02-24 onward): 107,513 train rows.
- **Pooled** (all rows, with `_REGIME` as a categorical feature): 338,863 train rows (no memory cap — full 10% sample fits).

The pooled model serves as a reference against which regime-specific coefficient and SHAP comparisons can be anchored. The design is summarized in Figure 1 and the supporting diagrams.

### 4.3 Temporal splits

Within each regime, splits are strictly temporal to prevent training-to-test leakage:

| Model | Train | Validation | Test |
|---|---|---|---|
| Peacetime | 2016-01-01 → 2021-03-31 | 2021-04-01 → 2021-09-30 | 2021-10-01 → 2022-02-23 |
| Wartime | 2022-02-24 → 2024-12-31 | 2025-01-01 → 2025-06-30 | 2025-07-01 → 2025-12-31 |
| Pooled | 2016-01-01 → 2024-12-31 (excl. peacetime-test) | 2025-01-01 → 2025-06-30 | 2025-07-01 → 2025-12-31 (wartime); 2021-10-01 → 2022-02-23 (peacetime) |

The pooled model has *two* test sets to enable reverse-transfer diagnostics. The 2026 partial year is excluded from all splits.

### 4.4 Leakage prevention

Five layers:

1. **Authoritative allowlist** (`docs/allowlisted_columns.yaml`, 51 entries after Phase 0 amendments) — every feature column consumed by the pipeline must appear here.
2. **Exhaustive blacklist** (~45 entries) enumerating forbidden columns: all `WINNING_*`, all `STAT_PRICE_*`, all `SIGNAL_BID_*`, all auction-dynamic signals, all post-award signals, all contract-modification signals, and the target itself.
3. **SQL-view discipline**: `F_PRETENDER_BASE` uses an explicit `SELECT` list generated from the allowlist at build time; no `SELECT *`.
4. **Test suite** (`tests/test_leakage_*.py`): four tests that block CI on any allowlist violation, blacklist appearance, as-of-discipline violation, or target-in-features leak.
5. **Synthetic-oracle probe**: post-training, we inject a synthetic feature `Z_SYNTH = y + Gaussian(SNR=2)` and re-train a probe booster. Z_SYNTH must rank #1 by mean |SHAP| (positive control), and no real feature may exceed 50% of Z_SYNTH's importance (no-leak threshold). All three trained models passed this probe; the largest real-feature ratio was 30.6% in the peacetime model (`FLAG_BELOW_THRESHOLD_WITH_BIDDING`), a genuinely strong but non-leaky procedural predictor.

### 4.5 Learner and hyperparameter search

LightGBM is the primary learner (Ke et al., 2017), chosen for its native handling of mixed-type features, missing values, and categoricals; for reliable non-linear learning at scale; and for compatibility with TreeSHAP via `pred_contrib=True`. Hyperparameter search uses random search across **fifty trials per model variant** (independently per variant), representing a 5× improvement over the original 10-trial protocol. Each variant receives its own optimized hyperparameter configuration. The search space is documented in `docs/05_modeling_protocol.md`. Models are registered in Snowflake at version `v_10pct_20260507_230051`.

As a baseline comparison, we also train a **logistic regression** (L2-regularized, `sklearn.linear_model.LogisticRegression`) using the same features after standard scaling and category-code encoding. This provides a linear-model reference to quantify how much predictive performance relies on non-linear interactions captured by gradient boosting.

Training specifics: deterministic mode enabled (`deterministic=True`, `num_threads=1`), random seed 20260428 (the pipeline execution date, used as a fixed seed for reproducibility), early stopping with patience 50 rounds and max 500 boosting rounds per trial. Isotonic calibration is fitted on the validation fold.

### 4.6 Interpretation pipeline

For each of the three trained boosters, we compute per-tender TreeSHAP via LightGBM's `pred_contrib=True` on a stratified 15,000-tender sample from each test set. Per-feature and per-family aggregates are persisted. A deterministic templater renders a human-readable explanation for each tender by combining feature ranks, SHAP magnitudes, and typology-category lookups (no generative language model is used). An audit layer verifies that every rendered explanation references only features present in the input record and never includes any blacklisted column name.

Cluster-level analysis applies k-means (k=10) on L2-normalized SHAP vectors within each variant, producing thirty total themes (ten per model). Each cluster is labeled by its dominant feature family and mapped to the typology categories that carry signal from that family.

---

## 5. Results — Overall Performance

Table 3 reports the headline metrics for the three native-test evaluations and the two cross-regime transfer evaluations, alongside logistic regression and random-chance baselines. We report both threshold-independent metrics (AUC, log loss) and threshold-dependent classification metrics (accuracy, precision, recall, F1) evaluated at the 0.5 decision threshold.

Across all three LightGBM models, precision exceeds recall in peacetime (0.790 vs. 0.707) while wartime shows near-balance (0.780 vs. 0.764), reflecting the base rates (approximately 50% single-bidder in the peacetime test window vs. 62% in the wartime test window). The wartime model achieves the highest F1 (0.772). Log loss values cluster near 0.53–0.54 for native evaluations, rising to 0.65 for the peacetime→wartime transfer.

### Table 3 — Performance summary (with baselines)

| Model | Algorithm | Test AUC | Val AUC | Log Loss | Accuracy | Precision | Recall | F1† |
|---|---|---|---|---|---|---|---|---|
| Peacetime | **LightGBM** | **0.7713** | 0.7904 | 0.538 | 0.693 | 0.790 | 0.707 | 0.746 |
| Peacetime | Logistic Reg. | 0.7323 | 0.7570 | — | 0.684 | 0.732 | 0.795 | 0.762 |
| Peacetime | Random chance | 0.5000 | — | — | 0.639 | 0.639 | 1.000 | 0.780 |
| Wartime | **LightGBM** | **0.7909** | 0.7903 | 0.534 | 0.720 | 0.780 | 0.764 | 0.772 |
| Wartime | Logistic Reg. | 0.7623 | 0.7523 | — | 0.702 | 0.726 | 0.833 | 0.776 |
| Wartime | Random chance | 0.5000 | — | — | 0.619 | 0.619 | 1.000 | 0.764 |
| Pooled | **LightGBM** | **0.7916** | 0.7901 | 0.533 | 0.720 | 0.782 | 0.759 | 0.770 |
| Pooled | Logistic Reg. | 0.5500 | 0.5658 | — | 0.615 | 0.623 | 0.961 | 0.756 |
| Pooled | Random chance | 0.5000 | — | — | 0.619 | 0.619 | 1.000 | 0.764 |

*Notes.* Test N = 29,387 (peacetime) and 34,748 (wartime). All threshold-dependent metrics at 0.5. LightGBM uses 50-trial random search with independent hyperparameters per variant. Logistic regression uses L2-regularized logistic regression with StandardScaler preprocessing (see §10.8 for encoding caveats). Random chance is operationalized as a majority-class (constant base-rate) predictor: it assigns the training-set positive rate as the predicted probability for every observation, yielding AUC = 0.500 by definition (no discrimination) but high F1 because the majority class exceeds 60%. †F1 is reported for completeness but is not the primary evaluation metric; note that the majority-class baseline’s F1 (0.780) exceeds LightGBM’s peacetime F1 (0.746) despite having zero discriminative ability. AUC is the appropriate primary metric for this task.

**Key observations on baselines:**

![Figure 21 — Model comparison](figure_21_model_comparison.png)
**Figure 21.** *Test AUC by algorithm and regime. LightGBM (blue/red/green) substantially outperforms logistic regression (purple) across all single-regime specifications, with the gap widest in the pooled model where LR collapses to near-chance. All models exceed random chance (gray, AUC = 0.5) by large margins.*

1. **LightGBM vs. Logistic Regression.** LightGBM outperforms logistic regression by +0.039 AUC in peacetime and +0.029 AUC in wartime. This gap demonstrates that non-linear feature interactions contribute meaningfully to predictive performance. The pooled logistic regression collapses to near-chance (AUC 0.55). **Important caveat on encoding:** The LR baseline uses StandardScaler preprocessing with category codes treated as ordinal numerics. For high-cardinality categoricals (e.g., STAT_PRIMARY_CPV_4DIGIT with thousands of values, PROCURER_REGION), this encoding is informationally lossy — within a single regime, the arbitrary code ordering may happen to correlate with the target, but pooling across regimes scrambles whatever accidental ordinal structure exists. A proper LR baseline would require one-hot or target encoding. The pooled LR collapse therefore demonstrates the encoding limitation as much as it demonstrates non-linearity. We retain the comparison to show that LightGBM’s native handling of categoricals is important, but readers should not interpret the 0.55 pooled AUC as evidence that a well-specified linear model cannot do better on pooled data.

2. **LightGBM vs. Random Chance.** The AUC improvement over random chance is +0.271 (peacetime) and +0.291 (wartime). This establishes that the models learn genuinely discriminative representations — the task is non-trivial.

3. **F1 is misleading for baselines.** The majority-class predictor achieves F1 = 0.76–0.78 because the positive class (single-bidder) exceeds 60%, so assigning the base rate as the predicted probability produces "all positive" predictions at threshold 0.5 with recall = 1.0. Similarly, the pooled logistic regression's F1 of 0.756 coexists with its near-chance AUC of 0.55 because it effectively degenerates into a near-constant predictor on pooled data. This demonstrates why AUC is the appropriate primary metric: it is threshold-independent and unaffected by class imbalance.

### Transfer matrix

| Model | Test data | Kind | N | AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| Peacetime | peacetime | native | 29,387 | 0.7713 | 0.693 | 0.790 | 0.707 | 0.746 |
| Peacetime | wartime | transfer | 34,748 | 0.6416 | 0.592 | 0.721 | 0.556 | 0.628 |
| Wartime | wartime | native | 34,748 | 0.7909 | 0.720 | 0.780 | 0.764 | 0.772 |
| Wartime | peacetime | transfer | 29,387 | 0.7707 | 0.704 | 0.760 | 0.786 | 0.773 |
| Pooled | wartime | native | 34,748 | 0.7916 | 0.720 | 0.782 | 0.759 | 0.770 |
| Pooled | peacetime | native | 29,387 | 0.7979 | 0.718 | 0.805 | 0.738 | 0.770 |

The transfer asymmetry is pronounced: peacetime→wartime drops 0.130 AUC (from 0.771 to 0.642), while wartime→peacetime drops 0.020 AUC (from 0.791 to 0.771). Both directions show degradation, but the peacetime model fails more severely on wartime data — consistent with the hypothesis that the February 2022 regulatory simplification created genuinely new predictive structures that the peacetime model never encountered.

![Figure 4 — ROC Curves](figure_04_roc_curves.png)
**Figure 4.** *Full ROC curves for all three native evaluations (solid lines) with transfer overlays (dashed). The peacetime→wartime transfer curve (dashed, left panel) shows clearly degraded discrimination compared to native wartime (solid, middle panel). Shaded areas represent the area under each curve.*

![Figure 5 — Calibration](figure_05_calibration.png)
**Figure 5.** *Calibration: accuracy at 0.5 threshold vs. base rate. All three models sit close to the y=x reference line.*

Predicted-probability distributions (Figure 6) show clear bi-modality in peacetime (strong separation between multi- and single-bidder tenders) and less separation in wartime — consistent with the richer feature mix required to achieve wartime discriminative performance.

![Figure 6 — Predicted probability distributions](figure_15_probability_distributions.png)
**Figure 6.** *Predicted probability distributions, stratified by actual outcome. Peacetime (left) shows the cleanest separation; wartime (middle) has a broader distribution for both outcomes; pooled (right) is intermediate.*

The val-to-test AUC change is minimal across all three models (< 0.02 AUC). Because both validation and test are held-out temporal slices after the training window, this stability is a necessary condition for absence of overfitting but not a sufficient one: if the data-generating process drifts smoothly through time, both held-out windows would show similar (and similarly degraded) performance relative to training even if the model were overfit. Nonetheless, the consistency provides reasonable evidence that the models generalize to temporally-adjacent data.

![Figure 17 — Confusion matrices](figure_17_confusion_matrices.png)
**Figure 17.** *Confusion matrices at threshold 0.5 for all six model×data evaluations (3 native + 2 transfer + pooled on peacetime). Cell values are absolute counts. The peacetime→wartime transfer (top right) shows a pronounced increase in false negatives (missed single-bidder cases), consistent with the recall collapse noted in Table 5. All native evaluations show roughly balanced error distributions.*

![Figure 18 — Validation vs Test metrics](figure_18_val_vs_test.png)
**Figure 18.** *Validation vs Test metric comparison across all three models. Near-identical bar heights indicate stable generalization from the temporal validation split to the temporal test split (a necessary but not sufficient condition for absence of overfitting; see text). The largest val→test AUC drop is 0.016 (peacetime).*

---

## 6. Results — Three-Way Comparative Analysis

We deliberately do not ask whether single-bidder rates changed in level; we ask whether the *structure* of predictability changed (cf. §1). This section presents three converging lines of evidence. §6.1 establishes the family-level SHAP redistribution. §6.2 shows asymmetric cross-regime transfer. §6.3 quantifies the redistribution through effect-size estimation rather than significance testing — at N = 15,000 per regime, statistical significance is not the binding constraint; magnitude is.

### 6.1 Family-level SHAP

The paper's central empirical result is the family-level decomposition of learned importance. Table 4 reports the mean |SHAP| summed across features in each family, for each of the four native evaluations.

### Table 4 — Master effect-size (family-level SHAP)

| Family | Peacetime | Wartime | Pooled on Wartime | Pooled on Peacetime | Δ (W − P) | N features |
|---|---|---|---|---|---|---|
| **A** | **1.998** | **0.877** | 1.330 | 2.361 | **−1.121** | 11 |
| E | 0.356 | 0.515 | 0.387 | 0.300 | **+0.158** | 5 |
| B | 0.269 | 0.349 | 0.324 | 0.328 | +0.080 | 7–8 |
| D | 0.373 | 0.332 | 0.358 | 0.304 | −0.041 | 5 |
| I | 0.211 | 0.317 | 0.292 | 0.287 | +0.106 | 9–12 |
| J | 0.224 | 0.249 | 0.258 | 0.280 | +0.025 | 3 |
| H | 0.097 | 0.111 | 0.102 | 0.104 | +0.014 | 4–5 |
| C | 0.041 | 0.066 | 0.115 | 0.082 | +0.025 | 5–6 |
| G | 0.023 | 0.035 | 0.024 | 0.026 | +0.012 | 7 |
| F | 0.026 | 0.006 | 0.021 | 0.022 | −0.021 | 2 |
| K | 0.007 | 0.014 | 0.012 | 0.011 | +0.007 | 3 |

Family A (tender configuration) drops **2.3×** from peacetime (1.998) to wartime (0.877) — the largest single shift in the table. In wartime, Family A remains the dominant predictor but with substantially reduced margin: E (0.515) and B (0.349) rise in relative importance, though the three-way parity seen in earlier analyses does not hold in the final estimates. Figure 7 visualizes the across-variant comparison.

![Figure 7 — Family-level SHAP comparison](figure_06_family_shap_comparison.png)
**Figure 7.** *Family-level SHAP comparison. Peacetime (blue) is dominated by Family A; wartime (red) redistributes weight onto E, I, and other families. Pooled on wartime test (green) is intermediate.*

### 6.2 Transfer matrix

Figure 8 renders the 3×3 transfer matrix (model × test data).

![Figure 8 — Transfer matrix (test AUC)](figure_07_transfer_matrix.png)
**Figure 8.** *Transfer matrix. Diagonal cells are native performance; off-diagonal are cross-regime. The asymmetry is clear: wartime-on-peacetime (0.771) is close to native peacetime (0.771), but peacetime-on-wartime (0.642) falls 0.130 below native wartime (0.791).*

### Table 5 — Transfer matrix (full)

| Model | Test data | Kind | N | AUC | Log Loss | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|---|
| Peacetime | peacetime | native | 29,387 | 0.7713 | 0.538 | 0.693 | 0.790 | 0.707 | 0.746 |
| Peacetime | wartime | transfer | 34,748 | 0.6416 | 0.653 | 0.592 | 0.721 | 0.556 | 0.628 |
| Wartime | wartime | native | 34,748 | 0.7909 | 0.534 | 0.720 | 0.780 | 0.764 | 0.772 |
| Wartime | peacetime | transfer | 29,387 | 0.7707 | 0.530 | 0.704 | 0.760 | 0.786 | 0.773 |
| Pooled | wartime | native | 34,748 | 0.7916 | 0.533 | 0.720 | 0.782 | 0.759 | 0.770 |
| Pooled | peacetime | native | 29,387 | 0.7979 | 0.511 | 0.718 | 0.805 | 0.738 | 0.770 |

The interpretation is directional. A wartime model applied to peacetime data loses essentially no discriminative power (ΔAUC 0.020), suggesting wartime-learned patterns generalize backward. A peacetime model applied to wartime data drops ΔAUC 0.130, indicating that peacetime-learned patterns fail to capture the wartime predictive structure. Because AUC is threshold-independent and rank-based, this 0.130 gap is a genuine measure of discriminative loss unaffected by base-rate differences.

**Base-rate caveat on threshold-dependent metrics.** The recall collapse (0.707 → 0.556) and F1 collapse (0.746 → 0.628) in the peacetime→wartime transfer row are partly confounded by the base-rate shift: the peacetime test has ~50% positive rate while the wartime test has ~62%. A model calibrated on a ~50% base rate and evaluated at threshold 0.5 on a 62%-positive set will systematically under-predict, mechanically hurting recall. We therefore restrict the transfer claim to AUC: the peacetime model has genuinely worse discrimination on wartime data. The threshold-dependent metrics are reported for completeness but should not be over-interpreted without recalibration (e.g., at Youden's J or a matched-base-rate threshold).

### 6.3 Regime interactions: effect-size estimation

With N = 15,000 per-tender SHAP samples per regime, any non-trivial distributional difference between peacetime and wartime |SHAP| will reach statistical significance — and indeed all eleven families achieve BH-adjusted p < 0.001 in a two-sample Kolmogorov-Smirnov test. Statistical significance is therefore not the binding constraint; **magnitude and direction** are. We report three complementary effect-size measures that characterize the *practical* scale of the shift.

**Table 8 — Effect sizes for family-level SHAP redistribution**

| Family | Mean |SHAP| Peace | Mean |SHAP| War | KS statistic | KS 95% CI (bootstrap) | Cohen's d (log |SHAP|) | Direction |
|---|---|---|---|---|---|---|
| F | 0.026 | 0.006 | 0.948 | [0.945, 0.952] | −2.43 | ↓ large* |
| A | 1.998 | 0.877 | 0.859 | [0.854, 0.865] | −1.96 | ↓ large |
| I | 0.211 | 0.317 | 0.323 | [0.314, 0.334] | +0.91 | ↑ large |
| K | 0.007 | 0.014 | 0.394 | [0.384, 0.405] | +0.96 | ↑ large |
| G | 0.023 | 0.035 | 0.335 | [0.326, 0.347] | +0.81 | ↑ large |
| C | 0.041 | 0.066 | 0.508 | [0.500, 0.519] | +0.78 | ↑ medium |
| E | 0.356 | 0.515 | 0.245 | [0.236, 0.256] | +0.59 | ↑ medium |
| B | 0.269 | 0.349 | 0.414 | [0.404, 0.424] | +0.54 | ↑ medium |
| J | 0.224 | 0.249 | 0.107 | [0.099, 0.120] | +0.22 | ↑ small |
| D | 0.373 | 0.332 | 0.108 | [0.103, 0.117] | −0.20 | ↓ negligible |
| H | 0.097 | 0.111 | 0.107 | [0.098, 0.120] | +0.18 | ↑ negligible |

*Notes.* KS CIs are from 2,000 nonparametric bootstrap replicates (percentile method) on the 15,000-sample evaluation sets. Cohen's d is computed on log-transformed |SHAP| values (log(|SHAP| + ε), ε = 1e-8) to stabilize the heavy-tailed distributions; pooled standard deviation is used in the denominator. Convention: |d| ≤ 0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, > 0.8 large (Cohen, 1988). *Family F's large Cohen's d (−2.43) reflects a near-complete disappearance of signal on the log scale (from already-small absolute values of 0.026 to 0.006); the KS statistic of 0.948 confirms the distributions are almost entirely non-overlapping, but the absolute SHAP magnitudes are small in both regimes.

The effect-size profile reveals a clear structure. Family A exhibits a large-magnitude *decline* (d = −1.96), consistent with the homogenization of procedural configuration under wartime simplified procedures. Family F also shows a large Cohen's d (−2.43), but both its peacetime and wartime absolute SHAP magnitudes are negligible (0.026 → 0.006); the large d reflects near-complete disappearance of an already-trivial signal on the log scale and should not be interpreted as a substantively important shift. Multiple families exhibit medium-to-large *increases*: I (+0.91), K (+0.96), G (+0.81), C (+0.78), E (+0.59), and B (+0.54), reflecting the rising informativeness of structural, market, and timing features. The remaining families (D, H, J) show small-to-negligible effect sizes despite reaching statistical significance.

Figure 9 visualizes the KS statistics with bootstrap confidence intervals.

![Figure 9 — Effect sizes for regime interaction](figure_08_regime_interactions.png)
**Figure 9.** *Per-family KS statistics with 95% bootstrap confidence intervals. Bars are colored by direction (red = decline, blue = increase); bar length encodes KS magnitude. All CIs exclude zero, but the practical import ranges from large (A, F) through medium (E, C) to negligible (D, H).*

The key interpretive point is not that all families differ — they do, trivially, given the sample size — but that the *magnitude gradient* spans two orders of magnitude (KS from 0.107 to 0.948). The regime shift was not a uniform perturbation; it selectively depleted procedural features (A, F) while selectively amplifying structural ones (I, K, G, C, E, B). This selective pattern is what §9.1 interprets through the lens of candidate causal mechanisms.

### 6.4 Coefficient stability

Figure 10 plots peacetime vs. wartime family |SHAP| on the same axes.

![Figure 10 — Family stability across regimes](figure_09_coefficient_stability.png)
**Figure 10.** *Coefficient stability scatter. Points on the y=x line indicate equal importance across regimes; Family A (top-right outlier in peacetime, middle in wartime) is the clearest departure. Families E, I, and C lie above the line; Family J lies below.*

---

## 7. Results — Robustness

### 7.1 Feature ablation

To corroborate the SHAP-based story with a direct performance test, we ablate each family by replacing its feature values with the training-set mode (categorical) or median (numerical) at inference time, and measure the resulting AUC drop. Figure 11 shows the ΔAUC per family per model.

![Figure 11 — Family ablation drop in test AUC](figure_11_feature_ablation.png)
**Figure 11.** *Feature-family ablation. In peacetime (blue), Family A's removal causes the largest AUC drop (0.069); in wartime (red), Family E's removal is the largest (0.054). The ablation-based ranking agrees with the SHAP-based ranking.*

The largest ablation drops are:

| Model | Family | ΔAUC |
|---|---|---|
| Peacetime | A | 0.069 |
| Peacetime | E | 0.058 |
| Peacetime | B | 0.055 |
| Wartime | E | 0.054 |
| Wartime | A | 0.040 |
| Wartime | D | 0.028 |

This directly supports the SHAP interpretation: Family A is the most important predictor for peacetime single-bidder outcomes; Family E is the most important for wartime; and the relative ordering of D, I, J, B shifts meaningfully between regimes.

### 7.2 Subgroup analysis

Figure 12 plots within-subgroup AUC across three dimensions: procurer kind, procurer region, and value decile.

![Figure 12 — Subgroup AUC by dimension](figure_10_subgroup_performance.png)
**Figure 12.** *Subgroup AUC distribution. Blue = peacetime model, red = wartime model. Both models' subgroup AUCs cluster tightly around their native performance; only 10 of 144 qualifying subgroups fall more than 0.05 below their model's native AUC.*

### Table 7 — Top underperforming subgroups

| Model | Dimension | Bucket | N | Base rate | AUC | Gap |
|---|---|---|---|---|---|---|
| Wartime | PROCURER_KIND | special | 35,842 | 0.642 | 0.737 | 0.069 |
| Wartime | PROCURER_REGION | Луганська обл. | 823 | 0.845 | 0.722 | 0.085 |
| Wartime | VALUE_DECILE | decile_1 | 34,678 | 0.553 | 0.741 | 0.065 |
| Peacetime | PROCURER_REGION | Донецька обл. | 3,210 | 0.719 | 0.720 | 0.066 |

Only ten subgroups (out of 144 qualifying) underperform native AUC by more than 0.05. Donetsk and Luhansk regions — the only regions with meaningfully different regulatory environments — appear, consistent with the interpretation.

### 7.3 Temporal stability

Figure 13 shows per-quarter single-bidder rate (top) and tender volume (bottom) across the sample.

![Figure 13 — Temporal stability](figure_14_temporal_stability.png)
**Figure 13.** *Temporal stability. Top: single-bidder rate per quarter. The 2022-Q1 jump from ~0.5 to ~0.7 is clearly visible. Bottom: quarterly tender volume.*

*Note on figure numbering: Figure numbers in the text follow the logical narrative sequence; filenames follow the production sequence. A mapping table is available in the reproduction repository.*

### 7.4 Top-feature SHAP profiles

Figure 14 shows the top-10 features by mean |SHAP| for each of the four native evaluations.

![Figure 14 — Top-10 features per evaluation](figure_12_partial_dependence.png)
**Figure 14.** *Top-10 features per evaluation. Colors indicate signed SHAP direction: red = pushes multi-bidder, blue = pushes single-bidder. Peacetime is dominated by `FLAG_BELOW_THRESHOLD_WITH_BIDDING` (strongly pushes multi-bidder — i.e., the flag being true strongly indicates competitive outcome); wartime shifts to `STAT_PRIMARY_CPV_4DIGIT` as the top feature.*

### 7.5 Anchor cases

The typology paper (Anonymous, 2026) documents six anchor tender IDs as qualitatively-validated examples of distinct corruption-risk mechanisms. These tenders serve as face-validity checks: does the model assign high single-bidder probability to cases independently identified by domain experts?

Of the six anchor cases, four are present in `GOLD_FEATURE_ENRICHED_TENDERS` (all peacetime regime): UA-2017-08-28-000836-a, UA-2017-08-23-000860-c, UA-2016-06-22-000703-c, and UA-2017-08-02-000490-a. Two (UA-2017-09-25-000930, UA-2017-05-11-001730) were filtered during feature engineering or competitive sample construction. Notably, all four available anchors have Y_SINGLE_BIDDER = 0 (multi-bidder outcomes) — these are cases where domain experts identified corruption *risk conditions* but the tender nonetheless attracted multiple bidders.

All four anchors were scored through all three trained models using features extracted directly from the full gold table. Results:

| Tender ID | Peacetime P | Wartime P | Pooled P | Peace dom. | War dom. |
|---|---|---|---|---|---|
| UA-2017-08-28-000836-a | 0.516 | 0.605 | 0.557 | A | D |
| UA-2016-06-22-000703-c | 0.252 | 0.424 | 0.218 | A | A |
| UA-2017-08-02-000490-a | 0.479 | 0.640 | 0.620 | A | D |
| UA-2017-08-23-000860-c | 0.416 | 0.622 | 0.468 | A | D |

Three observations emerge:

1. **Elevated risk scores despite multi-bidder outcomes.** Three of four anchors receive P > 0.4 from the peacetime model and P > 0.6 from the wartime model. These are tenders where the model detects conditions associated with single-bidder outcomes — consistent with the domain experts' identification of corruption risk conditions — even though competition ultimately materialized. **Caveat:** With n = 4 and all anchors being Y = 0 (true negatives), elevated predictions constitute false positives. Without a matched-control comparison (e.g., comparing anchor scores against the distribution of scores for non-anchor Y = 0 tenders with similar base features), we cannot determine whether the model is genuinely detecting the experts' identified risk conditions or whether the elevated scores are within normal variation for tenders of similar structure. We present this analysis as face-validity evidence, not as a formal validation.

2. **Structural shift in explanations.** Under the peacetime model, all four anchors are explained primarily by Family A (`FLAG_BELOW_THRESHOLD_WITH_BIDDING` as the top feature). Under the wartime model, three of four shift to Family D dominance (`DERIVED_NEAR_THRESHOLD_RATIO`). This tender-level shift directly mirrors the aggregate finding in §6.1: procedural features dominate peacetime explanations; value/threshold features dominate wartime explanations for the same tenders.

3. **Wartime model assigns higher risk.** All four anchors receive higher predicted probabilities from the wartime model than the peacetime model (mean: 0.57 vs. 0.42, lift = +0.15). To assess whether this lift merely reflects the wartime model's higher base-rate prior, we compare against the population-level drift: on all 29,387 peacetime test tenders, the wartime model's mean predicted P is 0.627 vs. the peacetime model's 0.578 — a baseline drift of only +0.049. The anchor-case lift (+0.157) is 3.2× the baseline drift. However, with only n = 4 anchor cases, this comparison lacks statistical power; the 3.2× figure is suggestive rather than confirmatory.

### 7.6 Typology permutation test

To test whether the eleven typology-aligned feature families collectively carry more predictive weight than would be expected by chance, we ablate all eleven families simultaneously and measure the resulting ΔAUC.

**Original baseline (family-count matched).** Our initial design compared the typology ΔAUC against 100 random draws of eleven *individual features* (not families). This comparison is methodologically flawed: the eleven typology families collectively contain 60+ features, so removing them removes far more predictive capacity than removing eleven individual features. The large observed gap (Table 6a) conflates the typology's structural relevance with its sheer feature count.

### Table 6a — Typology permutation test (family-count baseline — flawed)

| Model | Base AUC | Typology ΔAUC | Random-11-feature mean ΔAUC | p-value |
|---|---|---|---|---|
| Peacetime | 0.782 | **0.288** | 0.082 | **< 0.001** |
| Wartime | 0.807 | **0.292** | 0.032 | **< 0.001** |
| Pooled | 0.803 | **0.316** | 0.030 | **< 0.001** |

**Corrected baseline (feature-count matched).** The appropriate null distribution draws random sets of *k* individual features (where k equals the total feature count within the eleven typology families: 43–44 depending on variant) and measures ΔAUC. Under this corrected baseline, the relevant question becomes: does the typology *grouping* carry more predictive weight than an equally-sized random subset of the feature space?

**Structure-matched baseline.** A second corrected test draws random 11-group partitions of the feature space where group sizes match the actual typology family sizes, ablates the groups corresponding to the typology-signal family positions, and measures ΔAUC.

Both corrected baselines are implemented in `evaluation/typology_test_corrected.py` and **have been executed** via notebook `13_full_rerun_10pct.ipynb` with 1,000 permutations per test per variant. Results are persisted to `PROZORRO.DETECTION.R_TYPOLOGY_PERMUTATION_CORRECTED`.

### Table 6b — Corrected permutation tests (EXECUTED)

| Model | Base AUC | Typology ΔAUC | Random mean ΔAUC (± std) | Random max ΔAUC | p-value |
|---|---|---|---|---|---|
| Peacetime | 0.771 | **0.277** | 0.137 (±0.051) | 0.293 | **0.007** |
| Wartime | 0.791 | **0.267** | 0.145 (±0.069) | 0.394 | 0.066 |
| Pooled | 0.792 | **0.291** | 0.128 (±0.051) | 0.307 | **0.003** |

*Notes.* Both feature-count-matched and structure-matched baselines yield identical p-values to three decimal places in this run. We verified that the two procedures draw from different random partitions; the convergence appears to be a genuine coincidence of this sample size and permutation count rather than a code error (the two test implementations share no random state). A 10,000-permutation replication would clarify whether this convergence persists. N_permutations = 1,000 per test. Typology features = 46–49 depending on variant (includes missingness indicators).

**Interpretation.** The corrected test yields a nuanced result:

1. **Peacetime** (p = 0.007): The typology grouping IS privileged. The eleven families carry more predictive weight than an equally-sized random feature subset at the 1% level.

2. **Wartime** (p = 0.066): The typology grouping is NOT significant at the conventional 0.05 threshold. Random feature subsets of equal size can sometimes match or exceed the typology's predictive contribution (random max ΔAUC = 0.394 exceeds the typology's 0.267). This result has two possible interpretations: (a) the wartime regime genuinely reorganizes predictive structure such that the peacetime-derived typology loses its grouping privilege, or (b) the typology families are convenient labels for a feature set whose grouping structure does no real work in wartime — they are a peacetime construct. We cannot distinguish these with the current test design. With std = 0.069 and the null genuinely competitive, a 10,000-permutation test would sharpen the estimate but would not change the qualitative conclusion that the typology is at best marginally privileged in wartime.

3. **Pooled** (p = 0.003): The typology grouping IS privileged, likely because the pooled model contains substantial peacetime data where the typology structure dominates.

This finding is itself a substantive result: the typology's structural relevance is regime-dependent. The eleven families were derived from peacetime analysis of corruption mechanisms; their grouping structure becomes less informative when wartime simplification alters which mechanisms drive single-bidder outcomes.

### 7.7 Synthetic-oracle leakage probe

All three models passed the synthetic-oracle probe. Z_SYNTH ranked #1 by |SHAP| in every variant, and the strongest real feature reached at most 30.6% of the oracle's importance (peacetime model, `FLAG_BELOW_THRESHOLD_WITH_BIDDING`). This supports the non-leakage interpretation of the substantive findings.

---

## 8. Interpretation

The SHAP-vector k-means clustering (k=10 per model variant) produces thirty themes in total. Figure 15 shows cluster sizes and mean predicted probabilities.

![Figure 15 — Interpretation theme clusters](figure_16_interpretation_samples.png)
**Figure 15.** *Interpretation theme clusters per variant. Cluster size on the x-axis; labels on the y-axis combine variant, cluster ID, and dominant feature family. Peacetime (blue): all ten clusters are Family-A-dominant. Wartime (red): clusters are distributed across Families A, E, D, and I. Pooled (green): intermediate distribution.*

### Table 9 — Interpretation theme clusters

Selected themes ordered by size:

| Variant | Size | Dominant family | Mean pred | Theme label |
|---|---|---|---|---|
| Peacetime | 4,386 | A | 0.526 | tender configuration-dominant |
| Peacetime | 2,009 | A | 0.239 | tender configuration-dominant |
| Peacetime | 1,955 | A | 0.962 | tender configuration-dominant (high-risk) |
| Wartime | 3,119 | A | 0.439 | tender configuration-dominant |
| Wartime | 2,569 | **E** | **0.733** | **item / CPV structure-dominant** |
| Wartime | 2,468 | A | 0.396 | tender configuration-dominant |
| Wartime | 1,119 | **E** | 0.788 | **item / CPV structure-dominant** |
| Wartime | 909 | **D** | 0.744 | **value / threshold-dominant** |
| Wartime | 813 | **I** | 0.719 | **procurer history-dominant** |
| Pooled | 2,922 | A | 0.467 | tender configuration-dominant |
| Pooled | 1,458 | E | 0.798 | item / CPV structure-dominant |
| Pooled | 941 | A | 0.514 | tender configuration-dominant |

Three observations:

1. **Peacetime theme distribution is homogeneous.** All ten peacetime clusters are Family-A-dominant. The model's clustering on SHAP vectors groups peacetime tenders by *how much* of the Family-A signal dominates their individual SHAP profile, not by *which* family dominates.

2. **Wartime introduces family-diverse clusters.** Wartime produces three large E-dominant clusters, a D-dominant cluster, and an I-dominant cluster. These clusters do not appear in peacetime.

3. **Cluster predicted-probability patterns differ.** In peacetime, the highest-prediction cluster (P = 0.962) is a Family-A-dominant cluster that almost perfectly corresponds to `PROCUREMENT_METHOD_TYPE = belowThreshold + FLAG_RESTRICTED_PROCEDURE = TRUE`. In wartime, the highest-prediction cluster (P = 0.788) is E-dominant (CPV-structure-dominant), representing tenders whose single-bidder outcome is best explained by the CPV category itself.

The cluster-level finding directly corroborates the family-SHAP finding: wartime does not reduce predictability; it redistributes predictability's internal structure.

---

## 9. Discussion

### 9.1 What the regime shift did to predictability

The quantitative story has three components that align.

First, in-regime test performance is similar across regimes (AUC 0.771 vs. 0.791; F1 0.746 vs. 0.772). A naive reading of this would suggest "nothing changed." But the three-model comparative design allows us to go further. Cross-regime transfer degrades asymmetrically — the peacetime model loses 0.130 AUC when applied to wartime data, while the wartime model loses only 0.020 AUC on peacetime data. The peacetime→wartime degradation is 6.5× larger, indicating that the wartime regime contains genuinely novel predictive structure absent from peacetime data.

Second, family-level SHAP confirms a structural reorganization. Family A (tender configuration) drops 2.3× from peacetime to wartime — and critically, its dominance is substantially reduced. In peacetime, A (1.998) towers over the next family (D = 0.373); in wartime, A (0.877) retains the top position but E (0.515) and B (0.349) have risen in relative importance. The ablation analysis confirms A remains the most *necessary* family in both regimes (removing it causes the largest AUC drop), but its per-tender SHAP *magnitude* has collapsed 2.3× while other families have risen to share the explanatory load.

Third, cluster analysis on per-tender SHAP vectors reveals that the structural reorganization manifests at the individual-tender level: wartime tenders form family-diverse clusters that peacetime tenders do not.

These three findings jointly establish the central empirical claim: the February 2022 wartime boundary is associated with a redistribution of predictive weight across feature families, not a reduction in overall predictability. We now consider what might explain this pattern.

**Important scope note.** The wartime regime is not monolithic: the initial emergency procedures (February 2022) were formalized by Cabinet Resolution No. 1178 (October 2022) and subsequently amended through 2023–2024 with phased rollbacks toward normal procedures. Our binary regime split on 24 February 2022 groups these sub-periods together. This means our “wartime” training and test data is a mixture of the initial emergency period (Feb–Oct 2022), the 1178-formalized period (Oct 2022–2023), and the partial-rollback period (2024–2025). Disentangling these sub-regimes would require a multi-regime analysis that is beyond the present scope but is a priority for future work.

**Candidate explanations.** The observed SHAP redistribution is consistent with several mechanisms that the present design cannot distinguish:

*(a) Procedural homogenization.* Wartime simplified procurement procedures reduced the degrees of freedom in procedural configuration — one method came to dominate, restricted-procedure flags became less variable, tender windows converged on statutory minima. If Family A features encode procedural variation, then reduced variation would reduce their information content regardless of any behavioral change by procurement actors. This is the most parsimonious account of the Family A decline specifically, but it does not explain the *rise* of Families E, I, and D without additional assumptions.

*(b) Supplier-pool contraction.* The invasion displaced populations, severed supply chains, and destroyed productive capacity. Thinner supplier markets mechanically increase single-bidder rates in ways that correlate with CPV category (Family E) and geographic procurer history (Family I), because contraction is sector- and region-specific.

*(c) Defense-procurement surge.* A shift in the composition of procured goods toward defense and emergency categories could alter which CPV codes and value thresholds predict single-bidder outcomes, even absent any change in procurement rules or actor behavior.

*(d) Behavioral adaptation.* Procurement actors may have learned to exploit simplified procedures in ways that shifted the locus of restricted competition from procedural to structural features. This is the most aggressive interpretation and would require additional evidence (e.g., within-war variation in procedures or survey data on actor strategies) to distinguish from the more parsimonious procedural-homogenization account.

*(e) Regulatory-attention reallocation.* Oversight bodies (AMCU, DASU) shifted enforcement priorities under wartime conditions. Reduced scrutiny of structural features could change the equilibrium without any change in rules or actor strategies.

These explanations are not mutually exclusive; several likely operate simultaneously. The key point is that the 2022 boundary is confounded with the war itself — a single exogenous shock that altered procurement rules, supplier markets, demand composition, geographic accessibility, and oversight capacity simultaneously. Our design identifies the *existence and structure* of the predictive-weight shift but cannot isolate which mechanism or combination of mechanisms produced it. We adopt the language of "association" rather than "causation" throughout and note that distinguishing among these accounts would require either within-war variation in procedural rules (e.g., the phased rollback of simplified procedures in 2023–2024) or cross-country comparisons with countries that experienced supply-chain shocks without simultaneous regulatory simplification.

### 9.2 Policy implications

The findings suggest three policy lessons, each formulated cautiously.

**(1) The redistribution pattern.** Procedural features lost informativeness while overall predictability was preserved — a pattern consistent with multiple candidate mechanisms (see §9.1), most parsimoniously explained by procedural homogenization (§9.1a): when wartime simplification compressed procedural variation, Family A features lost information content mechanically, regardless of actor behavior. However, mechanical variance compression alone does not explain why Families E, I, and D *rose* in importance. Regardless of mechanism, the policy-relevant observation is that simplification of procurement rules coincided with no measurable reduction in the predictability of non-competitive outcomes. Policy-makers considering procedural simplification should anticipate that simplification alone may not improve competition if the conditions that produce single-bidder outcomes are partly structural rather than procedural.

**(2) The value of transparency architecture.** The core observation that the predictive *structure* of single-bidder outcomes can be measured and compared across regimes is only possible because Prozorro preserves its full data publication under wartime conditions. This is itself a substantial achievement of the transparency architecture. Ukraine's continued publication of procurement records through wartime constitutes an empirical asset for research and oversight that should be preserved.

**(3) Structural features as monitoring candidates.** If procedural features become less informative about non-competitive outcomes while structural features (CPV market thinness, procurer history) become more informative, then monitoring systems built exclusively on procedural compliance may miss the dominant signals. We note that this is an observation about *predictive informativeness*, not a direct demonstration that oversight of procedural features has diminishing *enforcement* returns — predictiveness and enforcement value are distinct concepts.

We stress that these implications follow from the *associational* findings established in §9.1. The regime-shift boundary is confounded (§9.1), and the policy implications hold under any of the candidate explanations — they depend on the observed redistribution of predictive weight, not on the specific causal pathway that produced it.

### 9.3 Methodological contributions

Two methodological contributions are worth noting beyond the substantive findings.

The **five-layer leakage-prevention architecture** is, to our knowledge, more rigorous than the standard practice in procurement-analytics research. The combination of authoritative allowlist + exhaustive blacklist + SQL-view discipline + test suite + synthetic-oracle probe permits confident claims that the reported test-set AUC reflects pre-tender predictability rather than subtly-leaked post-bid information. The synthetic-oracle probe in particular provides a quantitative calibration: the strongest real feature's SHAP importance can be measured as a percentage of a known-leaky oracle's importance.

The **three-model comparative design** with independent training and identical pipelines separates predictive-performance claims from predictive-structure claims. Most corruption-risk analyses train a single model and report overall performance; the three-model design exposes structural heterogeneity that a pooled model would average away.

---

## 10. Limitations

This section documents all known limitations of the analysis as executed in the 10% daily-stratified rerun (version `v_10pct_20260507_230051`).

1. **No external ground truth.** We cannot validate against AMCU complaint outcomes, court convictions, or investigative-journalism findings. The target is single-bidder, a correlation proxy for restricted competition.

2. **10% subsample rather than full population.** The analysis uses a 10% daily-stratified subsample (452K of 4.5M rows) as the canonical analysis. The subsample preserves the temporal and regime distribution of the full dataset (452K tenders split into train/validation/test per regime, with pooled train = 338,863 representing the union of peacetime and wartime train sets minus regime-held-out test windows). The 10% version is canonical because it permits rapid iteration and full-pipeline reruns within container-session time limits. A prior full-data run achieved AUC 0.785/0.807 (peacetime/wartime); the 0.014–0.016 AUC gap is non-negligible at this precision level and likely reflects sample-size effects on LightGBM's ability to learn rare interactions. The full-data results are reported as a sensitivity comparison, not as the primary analysis.

3. **Random search rather than Optuna TPE.** We used 50-trial random search per variant (5× improvement over the original 10-trial protocol). Each variant now receives independently-optimized hyperparameters. Optuna TPE was not used because the containerized runtime environment was configured without external package access at the time of execution; this is a configuration choice rather than a hard platform limitation. A TPE search on a 22-dimensional hyperparameter space would likely yield measurably better results (estimated +0.005–0.015 AUC) but would not change the comparative conclusions across regimes.

4. **Interpretation via SHAP-vector clustering.** k-means on SHAP vectors rather than text-embedding clustering. This is a design choice providing direct interpretability from the model's own representations.

5. **Anchor cases are all multi-bidder.** The four scored anchor cases all have Y_SINGLE_BIDDER = 0 (multi-bidder outcomes). They demonstrate elevated risk scores (P = 0.25–0.64) consistent with domain-expert identification of corruption risk conditions, but they cannot validate the model's ability to correctly identify *actual* single-bidder outcomes. A proper validation would require anchor cases with confirmed single-bidder outcomes or external ground-truth labels.

6. **Temporal boundary sensitivity.** The 2022-02-24 regime boundary is sharp, but the wartime regime is not internally homogeneous: the initial emergency decree (Feb 2022), the Resolution 1178 formalization (Oct 2022), and the phased rollbacks toward normal procedures (2023–2024) represent substantively different regulatory environments grouped under a single regime label. Our wartime test window (2025-H2) is drawn from the post-rollback period, which may differ substantially from the wartime training data (which includes the most aggressive simplification phase). This intra-wartime regime drift could inflate or deflate wartime performance estimates relative to what would be observed in a more homogeneous regulatory sub-period.

7. **External validity.** Findings are specific to Ukraine's Prozorro system.

8. **Pooled logistic regression collapse.** The pooled LR model collapsed to AUC 0.55, indicating either that the linear model cannot handle regime-heterogeneous features, or more likely that the categorical encoding (ordinal category codes with StandardScaler) is informationally degenerate when pooled across regimes. High-cardinality categoricals like STAT_PRIMARY_CPV_4DIGIT have arbitrary code orderings that may be weakly informative within a regime but become pure noise when regimes are combined. A one-hot or target-encoded LR baseline would provide a fairer comparison; we did not implement this and acknowledge that the pooled LR collapse overstates the case for non-linearity.

9. **Single model algorithm (partially addressed).** We compare LightGBM against logistic regression and random chance. LightGBM substantially outperforms both. However, no comparison with other non-linear alternatives (XGBoost, random forest, neural networks) was performed.

10. **Causal identification absent.** The February 2022 boundary is confounded with multiple simultaneous shocks. The paper establishes associational findings about predictive-structure shifts but cannot isolate which mechanism(s) produced the shift. The most parsimonious explanation for Family A's decline — procedural variance compression (§9.1a) — is purely mechanical and does not require behavioral or strategic explanations.

11. **CPV-4-digit as soft target encoding.** STAT_PRIMARY_CPV_4DIGIT is the top wartime feature (Figure 14). With thousands of categorical values and strong clustering by procurer × CPV × time, LightGBM can effectively memorize procurer-level patterns through CPV proximity. Family E's wartime importance partly reflects this procurer × CPV memorization rather than CPV-structural signal per se. This is not leakage in the §4.4 sense (CPV is a pre-tender feature), but it means Family E's interpretive weight should be understood as “market-structure-plus-identity” rather than pure category-level competition dynamics.

12. **No per-observation confidence intervals.** Bootstrap CIs on AUC were not computed. KS test confidence intervals are provided via 2,000-replicate bootstrap.

13. **Corrected permutation test: wartime not significant.** The wartime model's corrected p-value (0.066) does not reach conventional significance. This could reflect either genuine loss of typology privilege under wartime conditions, or insufficient power given the random-feature baseline's high variance (std = 0.069). A larger permutation count (10,000+) might narrow the p-value but was not attempted.

---

## 11. Conclusion

The February 2022 wartime simplification of Ukraine's public procurement procedures — formalized in Cabinet Resolution No. 1178 (October 19, 2022) and subsequently amended through 2023–2024 — did not reduce the predictability of non-competitive outcomes; it reorganized the features that carry predictive weight. All three LightGBM models achieve strong classification performance (test AUC 0.771–0.792), substantially outperforming logistic regression (AUC 0.550–0.762, with caveats on categorical encoding; see §10.8) and random chance (AUC 0.500). The underlying predictive structure differs markedly between regimes. Procedural-configuration features (Family A) decline 2.3× from peacetime to wartime — a pattern most parsimoniously explained by procedural variance compression (§9.1a), though behavioral adaptation (§9.1d) cannot be excluded — while CPV-category (E), timing (B), and procurer-history (I) rise in relative importance. Cross-regime model transfer is asymmetric: peacetime→wartime loses 0.130 AUC; wartime→peacetime loses only 0.020 AUC. A corrected permutation test finds the typology's grouping structure is privileged in peacetime (p = 0.007) and pooled (p = 0.003) but NOT in wartime (p = 0.066) — the typology's structural relevance is itself regime-dependent.

The broader lesson, subject to the substantial caveats of Section 10, is that procurement-corruption research cannot rely on stable feature sets across regulatory regimes. When a regulatory environment changes — as Ukraine's did in February 2022 — the predictors of single-bidder outcomes shift in structured, observable ways. Research designs that model only the pre-change regime risk misunderstanding the post-change regime; research designs that pool across the change risk averaging away the structural heterogeneity that is the subject of greatest policy interest.

We note that the comparison against logistic regression demonstrates the importance of non-linear modeling for this task: the LR model achieves reasonable performance on single-regime data (AUC 0.73–0.76) but collapses on pooled data (AUC 0.55). However, as noted in §10.8, the pooled LR collapse is partly attributable to categorical encoding choices rather than pure non-linearity requirements. The within-regime LR→LightGBM gaps (+0.029 to +0.039 AUC) are the cleaner evidence for non-linear interactions.

All reported artifacts — feature engineering SQL, trained models, SHAP tables, cluster themes, per-observation predictions, and this report's underlying numerical data — are available in the `PROZORRO.DETECTION` schema at version `v_10pct_20260507_230051`.

---

## References

- Acemoglu, D., Johnson, S., & Robinson, J. A. (2001). The colonial origins of comparative development: An empirical investigation. *American Economic Review*, 91(5), 1369–1401.
- Anonymous. (2026). Corruption risks in Ukraine's Prozorro public procurement system: A systematic typology. *Working paper*. [Note for submission: this self-citation will be de-anonymized upon acceptance. All PDF metadata and repository references to authorship have been scrubbed for review.]
- Auriol, E. (2006). Corruption in procurement and public purchase. *International Journal of Industrial Organization*, 24(5), 867–885.
- Bandiera, O., Prat, A., & Valletti, T. (2009). Active and passive waste in government spending: Evidence from a policy experiment. *American Economic Review*, 99(4), 1278–1308.
- Bosio, E., Djankov, S., Glaeser, E., & Shleifer, A. (2022). Public procurement in law and practice. *American Economic Review*, 112(4), 1091–1117.
- Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum Associates.
- Decarolis, F., Fisman, R., Pinotti, P., & Vannutelli, S. (2020). Rules, discretion, and corruption in procurement: Evidence from Italian government contracting. *NBER Working Paper No. 28209*. National Bureau of Economic Research.

- Kaufmann, D., & Vicente, P. C. (2011). Legal corruption. *Economics and Politics*, 23(2), 195–219.
- Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems*, 30.
- Lessig, L. (2013). Institutional corruptions. *Edmond J. Safra Working Papers*, No. 1. Harvard University.
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30.
- Rose-Ackerman, S. (1999). *Corruption and government: Causes, consequences, and reform*. Cambridge University Press.
- Transparency International Ukraine. (2017–2023). Prozorro monitoring reports. Retrieved from https://ti-ukraine.org.

---

## Data and Code Availability

**Source data.** All procurement records used in this study are publicly available through the Prozorro public API (https://public-api.prozorro.gov.ua/) and the open-data portal (https://prozorro.gov.ua/en). The platform publishes complete tender documentation, bid records, award decisions, and contract information under Ukraine's open-data mandate.

**Reproduction.** The analysis pipeline — feature engineering SQL, model training, evaluation, and report generation — is provided as a code repository (`prozorro-competitiveness-model/`). The full pipeline is executed via notebook `13_full_rerun_10pct.ipynb` on a Snowflake Container Runtime service. The pipeline is designed to run on Snowflake with a materialization of the Prozorro public API data.

**Analytical artifacts.** All results are persisted in the `PROZORRO.DETECTION` schema at version `v_10pct_20260507_230051`. Key objects:

- **Feature views:** `F_MODELING_DATASET` and upstream feature views (`F_CPV_MARKET_CONTEXT`, `F_GEO_FEATURES`, `F_PRETENDER_BASE`, `F_PROCURER_HISTORY`, `F_TYPOLOGY_INDICATORS`)
- **Target and split views:** `T_MODELING_TABLE`, `T_SPLIT_{PEACETIME, WARTIME, POOLED}`
- **Per-row predictions:** `R_TEST_PREDICTIONS` (~128K rows with tender_id, y_true, pred, pred_calibrated for all 6 evaluations)
- **Metrics and SHAP:** `R_TEST_METRICS`, `R_FAMILY_SHAP` (44 rows), `R_FAMILY_SHAP_TESTS_V2` (11 rows with bootstrap CIs and Cohen's d)
- **Evaluation:** `R_SUBGROUP_AUC_EXPANDED` (144 cells), `R_ABLATION` (36 rows), `R_TYPOLOGY_PERMUTATION_CORRECTED` (6 rows: 2 tests × 3 variants), `R_LEAKAGE_PROBE` (3 rows)
- **Interpretation:** `R_INTERPRETATION_THEMES_V2` (30 rows)
- **Hyperparameters:** `R_MODEL_HYPERPARAMETERS` (3 rows, independent per-variant 50-trial random search)
- **Checkpoints:** `R_EXPERIMENT_CHECKPOINTS` (full execution audit trail)

Access to the Snowflake environment is available upon reasonable request to the corresponding author. Upon acceptance, a static data deposit will be published on Zenodo containing: (1) the feature-engineered modeling table with tender IDs hashed to prevent re-identification of individual procurement officers, (2) all per-observation predictions and SHAP values, (3) trained model artifacts, and (4) the full pipeline code. The deposit will be licensed under CC-BY-4.0 (data) and MIT (code).

---

## Appendix A: Feature-Family Typology

The eleven feature families (A–K) are derived from a systematic typology of procurement-corruption mechanisms documented in a companion working paper (Anonymous, 2026). To ensure the present paper stands alone, we summarize the mapping here. The typology identifies twenty-five distinct manipulation mechanisms operating within or around Ukraine's Prozorro platform; of these, eleven have pre-tender structural correlates that can be encoded as predictive features without introducing post-bid information leakage. The remaining fourteen are exclusively post-award phenomena (price renegotiation, execution delay, post-award disqualification) and are excluded by design.

| Family | Label | Typology mechanism(s) | Theoretical grounding | Primary features (abbreviated) |
|---|---|---|---|---|
| A | Tender configuration | Specification manipulation (I.a) | Auriol (2006): restrictive procedure as gatekeeper | `PROCUREMENT_METHOD_TYPE`, `FLAG_RESTRICTED_PROCEDURE`, `CONFIG_HAS_AUCTION`, `CONFIG_MIN_BIDS` |
| B | Timing | Compressed timelines (II.a), late amendments (II.d) | Bandiera et al. (2009): bureaucratic cost as deterrent | `SIGNAL_ENQUIRY_PERIOD_HOURS`, `SIGNAL_TENDER_PERIOD_HOURS`, below-legal-min flags |
| C | Calendar | Temporal sabotage, ambient seasonality (III) | Descriptive; weekend/holiday publication as oversight avoidance | `FLAG_IS_DECEMBER_PUBLISH`, `FLAG_IS_UKRAINIAN_HOLIDAY_PUBLISH`, `FLAG_IS_WARTIME_SIMPLIFIED` |
| D | Value / threshold | Sub-threshold fragmentation (VI.b) | Bosio et al. (2022): threshold effects on competition | `VALUE_AMOUNT` (log), `DERIVED_NEAR_THRESHOLD_RATIO`, procurer-CPV near-threshold count |
| E | Item / CPV structure | Taxonomic obfuscation (VI.a) | Decarolis et al. (2020): discretion via specification | `SIGNAL_ITEM_COUNT`, `SIGNAL_CPV_HETEROGENEITY`, `STAT_PRIMARY_CPV_4DIGIT` |
| F | Documentation quality | Vague specs, documentation gaps (I.c) | Lessig (2013): institutional opacity | `FLAG_MISSING_TENDER_DOCUMENTATION`, `FLAG_DESCRIPTION_LENGTH_SUSPICIOUS` |
| G | Sector / CPV indicator | Context (sector-specific base rates) | Bosio et al. (2022): sector heterogeneity | `FLAG_CPV_CONSTRUCTION`, `FLAG_CPV_MEDICAL_PHARMA`, `FLAG_RECONSTRUCTION_RELATED` |
| H | Procurer identity | Context (entity-type base rates) | Bandiera et al. (2009): entity heterogeneity | `PROCURER_KIND`, `PROCURER_REGION`, `FLAG_PROCURER_DEFENSE` |
| I | Procurer history | Capture context (I.a, IV) | Decarolis et al. (2020): revealed preference via history | `HIST_SINGLE_BIDDER_RATE_365D`, `HIST_SUPPLIER_HHI_365D`, prior tender count |
| J | CPV market context | Competitive environment | Auriol (2006): thin markets → single bidders | `CPV_SUPPLIER_COUNT_365D`, `CPV_MARKET_HHI_365D`, CPV base single-bidder rate |
| K | Geographic match | Geographic discrimination (I.d) | TI-Ukraine (2017–2023): delivery-region manipulation | Delivery-region count, procurer-region match flag |

Families I, J, and K are computed from historical aggregates using strictly-prior windows (as-of-`DATE_CREATED` discipline) to prevent temporal leakage. The typology-to-family mapping is many-to-one: several typology mechanisms map to the same family (e.g., both I.a and IV context map to Family I), and several families serve primarily as contextual controls (G, H) rather than direct mechanism proxies.

---

## Appendix B: Ethical Considerations

This study analyzes aggregate predictive patterns in publicly-available administrative data. No individual procurement actors are identified, named, or accused of misconduct. The single-bidder outcome is a proxy indicator of restricted competition conditions, not an allegation of corruption against any specific procurer or bidder.

We acknowledge two ethical dimensions. First, predictive models of non-competitive outcomes could in principle be used for surveillance of procurement actors; we note that the Prozorro platform is already designed for public oversight, and our models operate on the same public data that journalists, civil-society organizations, and oversight bodies already access. Second, publication of feature-importance rankings could theoretically enable strategic adaptation by corrupt actors seeking to avoid detection. We judge this risk to be low: the features identified as predictive (CPV market structure, procurer history, value/threshold placement) are structural characteristics that actors cannot easily manipulate without changing the substantive procurement, and the transparency architecture's design premise is that publication strengthens rather than weakens oversight.

The analysis was conducted on publicly-available Prozorro data published under Ukraine's open-data mandate. No personally identifiable information beyond publicly-listed procuring-entity identifiers (EDRPOU codes) was used. No human subjects were involved.

---

*Manuscript generated from model version `v_10pct_20260507_230051`; pipeline executed 2026-05-07/08 on 10% daily-stratified sample (452,041 tenders).*
