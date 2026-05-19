#!/usr/bin/env python3
"""Generate a one-page PDF write-up for the Prozorro project."""

from fpdf import FPDF

OUTPUT = "/Users/taras/Desktop/New College Florida Diia Data Proposal Applied Data Science/prozorro-Distributed-Data/Prozorro_Project_Writeup.pdf"

class WriteupPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, "Prozorro Competitiveness Predictor", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 5, "Applied Data Science -- Project Write-Up", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Matthew R. MacFarlane | New College of Florida", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def section(self, title, body):
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(25, 60, 120)
        self.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8.2)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 3.6, body)
        self.ln(1.2)

pdf = WriteupPDF(orientation="P", unit="mm", format="Letter")
pdf.set_auto_page_break(auto=False)
pdf.add_page()
pdf.set_margins(16, 10, 16)
pdf.set_y(22)

pdf.section("Prediction Question",
    "Given only the structural design of a Ukrainian government procurement tender -- its method type, "
    "publishing agency, sector, timing, and documentation profile -- can we predict whether the tender "
    "will attract only a single bidder? A single-bidder outcome is the dominant quantitative proxy for "
    "corruption risk in public procurement research (Fazekas & Kocsis, 2020). Ukraine's Prozorro system "
    "-- the world's most transparent national e-procurement platform -- publishes 28.7 million machine-"
    "readable tender records, and the full-scale Russian invasion of 2022 caused single-bidder rates to "
    "surge from ~50% to ~66%, making this prediction both urgent and policy-relevant."
)

pdf.section("Data Source",
    "The raw data originates from the Prozorro Open Data API (public.api.openprocurement.org), which "
    "exposes the complete lifecycle of every Ukrainian government purchase in OCDS (Open Contracting Data "
    "Standard) JSON format. We synced the full dataset to a Google Cloud Storage bucket via an autonomous, "
    "self-terminating GCE Compute Engine instance, then loaded it into Snowflake using COPY INTO. The "
    "medallion architecture proceeds: Bronze (1.88M raw JSON records) -> Gold (feature-enriched with 101 "
    "columns including CPV sector flags, threshold proximity signals, and temporal markers) -> Platinum "
    "(4.5M competitive tenders with 34 engineered pre-tender features and a 10% daily-stratified training "
    "sample preserving temporal representativeness)."
)

pdf.section("Architecture",
    "Prozorro API -> GCE (paginated sync) -> GCS Bucket -> Snowflake Bronze -> Gold -> Platinum\n"
    "Snowflake ML Registry <- LightGBM training (3 regime variants: peacetime, wartime, pooled)\n"
    "Google Cloud Run (FastAPI backend) <- Model serving endpoint\n"
    "Vite + React frontend (live dashboard) -> User browser\n\n"
    "The pipeline spans three cloud services (GCP Compute Engine, GCP Cloud Storage, Snowflake) and three "
    "medallion layers. The trained LightGBM model is registered in Snowflake's ML Registry with version "
    "tracking, then loaded by a FastAPI backend deployed on Google Cloud Run that serves real-time "
    "predictions. The frontend is a Vite/React application that pulls live tenders from the Prozorro API, "
    "scores them against the model, and renders interactive risk visualizations."
)

pdf.section("Model Approach",
    "We train LightGBM gradient boosted trees (Ke et al., 2017) across three temporal variants: peacetime "
    "(2016-2022), wartime (2022-2026), and pooled. The target is binary: single-bidder (1) vs. multi-bidder "
    "(0). All 34 features are strictly pre-tender to prevent target leakage. Hyperparameters: learning_rate "
    "= 0.03, num_leaves = 63, max_depth = 7, early stopping at 50 rounds. The wartime model achieves AUC = "
    "0.772, F1 = 0.757, accuracy = 70.8% on held-out 2025-2026 data; the pooled model achieves AUC = 0.870 "
    "on peacetime holdout. A logistic regression baseline achieves only AUC = 0.707, confirming that the "
    "nonlinear interactions captured by gradient boosting are essential. SHAP analysis reveals that the "
    "invasion redistributed predictive signal from procedural features (tender period, documentation) onto "
    "structural features (procurement method, procurer identity) -- the central empirical finding. Cross-regime "
    "transfer shows a striking asymmetry: wartime -> peacetime transfers well (AUC = 0.77), but peacetime -> "
    "wartime collapses (AUC = 0.55)."
)

pdf.section("Learnings",
    "The hardest lesson was that data engineering consumed 70% of the project effort. Syncing 28.7M records "
    "from a rate-limited API required building autonomous cloud workers with checkpointing and self-termination "
    "-- infrastructure that felt distant from \"data science\" but proved essential. The most surprising finding "
    "was the cross-regime transfer asymmetry: a model trained on 2.3 years of wartime data outperforms one "
    "trained on 6 years of peacetime data, even on peacetime test sets. This taught me that distributional "
    "stress can improve generalization by forcing models to rely on robust structural features rather than "
    "fragile procedural ones. If I were to start over, I would invest earlier in the State Audit Service "
    "monitoring data (which provides confirmed violation labels) rather than relying solely on the single-"
    "bidder proxy."
)

pdf.output(OUTPUT)
print(f"PDF saved to: {OUTPUT}")
