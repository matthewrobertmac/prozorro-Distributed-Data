#!/usr/bin/env python3
"""
PLATINUM v3 — Logistic Regression Baseline
==========================================
Mirror of platinum_pipeline_v2.ipynb but swapping LightGBM for
sklearn LogisticRegression.  Produces the same metrics.csv and
a comparable chart suite for side-by-side comparison.

Usage:
    python platinum-v3-logistic-regression/run_pipeline.py
"""

import json, time, warnings, os, sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss, log_loss,
    precision_recall_curve, roc_curve, f1_score, precision_score,
    recall_score, accuracy_score, confusion_matrix, matthews_corrcoef,
    cohen_kappa_score, classification_report,
)
from sklearn.calibration import calibration_curve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
FIG_DIR = SCRIPT_DIR
RANDOM_SEED = 20260513
RUN_ID = datetime.utcnow().strftime("V_%Y%m%d_%H%M%S")

# ── Plot styling ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 180, "savefig.bbox": "tight",
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#333333", "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E5E5E5", "grid.linewidth": 0.6,
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "legend.frameon": False, "legend.fontsize": 9,
})
VARIANT_COLORS = {"peacetime": "#1f77b4", "wartime": "#d62728", "pooled": "#7e3ff2"}

# ── Snowflake connection ─────────────────────────────────────────────────────
sys.path.insert(0, str(SCRIPT_DIR.parent))
from live_dashboard.backend.main import build_snowflake_session

print(f"Run ID: {RUN_ID}")
print("Connecting to Snowflake...")
session = build_snowflake_session()

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Pull the SAME 10% daily-stratified sample used by v2
# ═══════════════════════════════════════════════════════════════════════════════
print("\nPhase 1: Loading FULL dataset from PROZORRO.PLATINUM.PLATINUM_COMPETITIVE_TENDERS ...")
sample_df = session.table("PROZORRO.PLATINUM.PLATINUM_COMPETITIVE_TENDERS").to_pandas()
print(f"  Loaded {len(sample_df):,} rows × {sample_df.shape[1]} columns")

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Feature Selection & Temporal Splits  (identical to v2)
# ═══════════════════════════════════════════════════════════════════════════════
TARGET = "SIGNAL_IS_SINGLE_BIDDER"
DATE_COL = "DATE_CREATED"
REGIME_BOUNDARY = "2022-10-12"

PRE_TENDER_FEATURES = [
    "PROCUREMENT_METHOD", "PROCUREMENT_METHOD_TYPE",
    "FLAG_BELOW_THRESHOLD_WITH_BIDDING", "PROCURER_KIND",
    "SIGNAL_EXPECTED_VALUE_UAH", "PROCURER_REGION",
    "SIGNAL_TENDER_PERIOD_DAYS", "SIGNAL_ENQUIRY_PERIOD_DAYS",
    "SIGNAL_DOCS_COUNT", "FLAG_HAS_GUARANTEE",
    "SIGNAL_GUARANTEE_AMOUNT_RATIO", "FLAG_FUNDERS_PRESENT",
    "FLAG_CPV_CONSTRUCTION", "FLAG_CPV_MEDICAL_PHARMA",
    "FLAG_CPV_IT_ELECTRONICS", "FLAG_CPV_ENGINEERING_SERVICES",
    "FLAG_CPV_ENERGY", "FLAG_CPV_FOODSERVICE",
    "FLAG_PROCURER_DEFENSE", "FLAG_PROCURER_MUNICIPAL",
    "FLAG_RECONSTRUCTION_RELATED", "FLAG_MISSING_TENDER_DOCUMENTATION",
    "FLAG_DESCRIPTION_LENGTH_SUSPICIOUS", "SIGNAL_LARGE_LOT_COUNT",
    "SIGNAL_TENDER_MODIFICATIONS_COUNT", "FLAG_LATE_MODIFICATION",
    "FLAG_IS_DECEMBER_PUBLISH", "FLAG_IS_YEAR_BOUNDARY_PUBLISH",
    "FLAG_IS_WARTIME_REGIME", "FLAG_IS_WARTIME_SIMPLIFIED",
    "FLAG_IS_UKRAINIAN_HOLIDAY_PUBLISH",
    "SIGNAL_NEAR_THRESHOLD_RATIO", "FLAG_NEAR_THRESHOLD_CLUSTER",
    "FLAG_LIKELY_SPLIT_CONTRACT",
]

CATEGORICAL_FEATURES = [
    "PROCUREMENT_METHOD", "PROCUREMENT_METHOD_TYPE", "PROCURER_KIND", "PROCURER_REGION",
]

# Missing-column guard
available = [c for c in PRE_TENDER_FEATURES if c in sample_df.columns]
missing = set(PRE_TENDER_FEATURES) - set(available)
if missing:
    print(f"  WARNING: Missing features (will skip): {missing}")
PRE_TENDER_FEATURES = available

y = sample_df[TARGET].astype(int)
X = sample_df[PRE_TENDER_FEATURES].copy()
dates = pd.to_datetime(sample_df[DATE_COL])
regime = np.where(dates >= REGIME_BOUNDARY, "wartime", "peacetime")
tender_ids = sample_df["TENDER_ID"] if "TENDER_ID" in sample_df.columns else pd.Series(range(len(sample_df)))

SPLITS = {
    "peacetime": {
        "train": ("2016-01-01", "2021-12-31"),
        "val":   ("2022-01-01", "2022-06-30"),
        "test":  ("2022-07-01", "2022-10-11"),
    },
    "wartime": {
        "train": ("2022-10-12", "2024-12-31"),
        "val":   ("2025-01-01", "2025-06-30"),
        "test":  ("2025-07-01", "2026-12-31"),
    },
}

def make_split_mask(ds, start, end):
    return (ds >= start) & (ds <= end)

datasets = {}
for variant, boundaries in SPLITS.items():
    ds = {}
    for split_name, (start, end) in boundaries.items():
        mask = make_split_mask(dates, start, end)
        ds[split_name] = {"X": X[mask].copy(), "y": y[mask].copy()}
        print(f"  {variant}/{split_name}: {mask.sum():,} rows, base_rate={y[mask].mean():.4f}")
    datasets[variant] = ds

pooled_train_mask = make_split_mask(dates, "2016-01-01", "2024-12-31")
pooled_val_mask   = make_split_mask(dates, "2025-01-01", "2025-06-30")
pooled_test_peace = make_split_mask(dates, "2022-04-01", "2022-10-11")
pooled_test_war   = make_split_mask(dates, "2025-07-01", "2026-12-31")

X_pooled = X.copy()
X_pooled["_IS_WARTIME"] = (regime == "wartime").astype(int)

datasets["pooled"] = {
    "train":          {"X": X_pooled[pooled_train_mask], "y": y[pooled_train_mask]},
    "val":            {"X": X_pooled[pooled_val_mask],   "y": y[pooled_val_mask]},
    "test_wartime":   {"X": X_pooled[pooled_test_war],   "y": y[pooled_test_war]},
    "test_peacetime": {"X": X_pooled[pooled_test_peace], "y": y[pooled_test_peace]},
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Train Logistic Regression  (replaces LightGBM)
# ═══════════════════════════════════════════════════════════════════════════════
print("\nPhase 3: Training Logistic Regression models ...")

def encode_and_scale(X_train, X_others_dict, cat_cols):
    """Label-encode categoricals (alphabetical), fill NaN, scale."""
    X_tr = X_train.copy()
    X_oth = {k: v.copy() for k, v in X_others_dict.items()}

    for col in cat_cols:
        if col not in X_tr.columns:
            continue
        # Build encoding from train
        categories = sorted(X_tr[col].dropna().unique())
        cat_map = {c: i for i, c in enumerate(categories)}
        X_tr[col] = X_tr[col].map(cat_map)
        for k in X_oth:
            X_oth[k][col] = X_oth[k][col].map(cat_map)

    # Fill NaN with -1 for categoricals, 0 for numerics
    for col in X_tr.columns:
        fill = -1 if col in cat_cols else 0
        X_tr[col] = X_tr[col].fillna(fill)
        for k in X_oth:
            X_oth[k][col] = X_oth[k][col].fillna(fill)

    scaler = StandardScaler()
    X_tr_scaled = pd.DataFrame(scaler.fit_transform(X_tr), columns=X_tr.columns, index=X_tr.index)
    X_oth_scaled = {}
    for k, df in X_oth.items():
        X_oth_scaled[k] = pd.DataFrame(scaler.transform(df), columns=df.columns, index=df.index)

    return X_tr_scaled, X_oth_scaled, scaler

models = {}
scalers = {}
training_logs = {}

for variant in ["peacetime", "wartime", "pooled"]:
    print(f"\n{'='*60}")
    print(f"Training: {variant.upper()} (Logistic Regression)")
    print(f"{'='*60}")

    ds = datasets[variant]
    cat_cols = [c for c in CATEGORICAL_FEATURES if c in ds["train"]["X"].columns]

    others = {k: v["X"] for k, v in ds.items() if k != "train"}
    X_tr_sc, X_oth_sc, scaler = encode_and_scale(ds["train"]["X"], others, cat_cols)

    t0 = time.time()
    clf = LogisticRegression(
        penalty="l2",
        C=1.0,
        max_iter=1000,
        solver="lbfgs",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    clf.fit(X_tr_sc, ds["train"]["y"])
    elapsed = time.time() - t0

    models[variant] = clf
    scalers[variant] = (scaler, cat_cols, X_oth_sc)

    val_key = "val"
    val_pred = clf.predict_proba(X_oth_sc[val_key])[:, 1]
    val_auc = roc_auc_score(ds[val_key]["y"], val_pred)
    val_ll  = log_loss(ds[val_key]["y"], val_pred)

    training_logs[variant] = {
        "elapsed_sec": round(elapsed, 1),
        "n_features": X_tr_sc.shape[1],
        "n_train": len(ds["train"]["y"]),
        "val_auc": val_auc,
        "val_logloss": val_ll,
    }
    print(f"  Val AUC: {val_auc:.4f}")
    print(f"  Val LogLoss: {val_ll:.4f}")
    print(f"  Time: {elapsed:.1f}s")

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Evaluation
# ═══════════════════════════════════════════════════════════════════════════════
print("\nPhase 4: Evaluation ...")

def evaluate_model(clf, X_test_scaled, y_test, label):
    pred = clf.predict_proba(X_test_scaled)[:, 1]
    pred_class = (pred >= 0.5).astype(int)
    metrics = {
        "label": label,
        "n": len(y_test),
        "base_rate": float(y_test.mean()),
        "auc_roc": float(roc_auc_score(y_test, pred)),
        "auc_pr": float(average_precision_score(y_test, pred)),
        "brier": float(brier_score_loss(y_test, pred)),
        "logloss": float(log_loss(y_test, pred)),
        "f1": float(f1_score(y_test, pred_class)),
        "precision": float(precision_score(y_test, pred_class, zero_division=0)),
        "recall": float(recall_score(y_test, pred_class, zero_division=0)),
        "accuracy": float(accuracy_score(y_test, pred_class)),
        "mcc": float(matthews_corrcoef(y_test, pred_class)),
        "kappa": float(cohen_kappa_score(y_test, pred_class)),
        "pred_mean": float(pred.mean()),
        "pred_std": float(pred.std()),
    }
    return metrics, pred

all_results = []
all_predictions = {}

for variant in ["peacetime", "wartime", "pooled"]:
    clf = models[variant]
    scaler, cat_cols, X_oth_sc = scalers[variant]
    ds = datasets[variant]
    test_splits = {k: v for k, v in ds.items() if "test" in k}
    for split_name in test_splits:
        label = f"{variant}/{split_name}"
        metrics, pred = evaluate_model(clf, X_oth_sc[split_name], ds[split_name]["y"], label)
        metrics["variant"] = variant
        metrics["split"] = split_name
        metrics["kind"] = "native"
        all_results.append(metrics)
        all_predictions[label] = {
            "y_true": ds[split_name]["y"].values, "y_score": pred,
            "variant": variant, "split": split_name, "kind": "native",
        }
        print(f"  {label}: AUC={metrics['auc_roc']:.4f}, LogLoss={metrics['logloss']:.4f}, n={metrics['n']:,}")

# Cross-regime transfer
print("\n--- Cross-regime transfer ---")
transfers = [("peacetime", "wartime", "test"), ("wartime", "peacetime", "test")]
for model_variant, data_variant, split_name in transfers:
    clf = models[model_variant]
    scaler_info = scalers[model_variant]
    scaler_obj, cat_cols_m, _ = scaler_info
    data = datasets[data_variant][split_name]

    X_t = data["X"].copy()
    for col in cat_cols_m:
        if col in X_t.columns:
            categories = sorted(datasets[model_variant]["train"]["X"][col].dropna().unique())
            cat_map = {c: i for i, c in enumerate(categories)}
            X_t[col] = X_t[col].map(cat_map)
    for col in X_t.columns:
        fill = -1 if col in cat_cols_m else 0
        X_t[col] = X_t[col].fillna(fill)
    X_t_sc = pd.DataFrame(scaler_obj.transform(X_t), columns=X_t.columns, index=X_t.index)

    label = f"{model_variant}_on_{data_variant}/{split_name}"
    metrics, pred = evaluate_model(clf, X_t_sc, data["y"], label)
    metrics["variant"] = model_variant
    metrics["split"] = f"transfer_{data_variant}_{split_name}"
    metrics["kind"] = "transfer"
    all_results.append(metrics)
    all_predictions[label] = {
        "y_true": data["y"].values, "y_score": pred,
        "variant": model_variant, "split": metrics["split"], "kind": "transfer",
    }
    print(f"  {label}: AUC={metrics['auc_roc']:.4f}")

results_df = pd.DataFrame(all_results)
results_df["run_id"] = RUN_ID
results_df["regime_boundary"] = REGIME_BOUNDARY
results_df["n_features"] = len(PRE_TENDER_FEATURES)

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Charts
# ═══════════════════════════════════════════════════════════════════════════════
print("\nPhase 5: Generating charts ...")

native_labels = [l for l, p in all_predictions.items() if p["kind"] == "native"]
transfer_labels = [l for l, p in all_predictions.items() if p["kind"] == "transfer"]

# ── Chart 1: ROC Overlay ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 7))
for label in native_labels + transfer_labels:
    p = all_predictions[label]
    fpr, tpr, _ = roc_curve(p["y_true"], p["y_score"])
    auc_val = roc_auc_score(p["y_true"], p["y_score"])
    ls = "-" if p["kind"] == "native" else "--"
    c = VARIANT_COLORS.get(p["variant"], "#999999")
    ax.plot(fpr, tpr, color=c, linestyle=ls, linewidth=1.5,
            label=f'{label} (AUC={auc_val:.4f})')
ax.plot([0,1],[0,1], "k--", lw=0.8, alpha=0.4)
ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves — Logistic Regression")
ax.legend(fontsize=7, loc="lower right")
fig.savefig(FIG_DIR / "04_roc_overlay.png"); plt.close(fig)
print("  Saved 04_roc_overlay.png")

# ── Chart 2: PR Overlay ──────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 7))
for label in native_labels + transfer_labels:
    p = all_predictions[label]
    prec, rec, _ = precision_recall_curve(p["y_true"], p["y_score"])
    ap = average_precision_score(p["y_true"], p["y_score"])
    ls = "-" if p["kind"] == "native" else "--"
    c = VARIANT_COLORS.get(p["variant"], "#999999")
    ax.plot(rec, prec, color=c, linestyle=ls, linewidth=1.5,
            label=f'{label} (AP={ap:.4f})')
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("Precision–Recall Curves — Logistic Regression")
ax.legend(fontsize=7, loc="lower left")
fig.savefig(FIG_DIR / "05_pr_overlay.png"); plt.close(fig)
print("  Saved 05_pr_overlay.png")

# ── Chart 3: Calibration ─────────────────────────────────────────────────────
fig, axes = plt.subplots(2, len(native_labels), figsize=(5*len(native_labels), 8))
if len(native_labels) == 1:
    axes = axes.reshape(-1, 1)
for i, label in enumerate(native_labels):
    p = all_predictions[label]
    fraction, mean_pred = calibration_curve(p["y_true"], p["y_score"], n_bins=10)
    axes[0, i].plot(mean_pred, fraction, "o-", color=VARIANT_COLORS.get(p["variant"], "#333"))
    axes[0, i].plot([0,1],[0,1], "k--", lw=0.8, alpha=0.4)
    axes[0, i].set_title(label, fontsize=10)
    axes[0, i].set_xlabel("Mean predicted"); axes[0, i].set_ylabel("Fraction positive")
    axes[1, i].hist(p["y_score"], bins=50, color=VARIANT_COLORS.get(p["variant"], "#333"), alpha=0.7)
    axes[1, i].set_xlabel("Predicted probability"); axes[1, i].set_ylabel("Count")
fig.suptitle("Calibration — Logistic Regression", fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(FIG_DIR / "06_calibration.png"); plt.close(fig)
print("  Saved 06_calibration.png")

# ── Chart 4: Confusion Matrices ──────────────────────────────────────────────
fig, axes = plt.subplots(1, len(native_labels), figsize=(5*len(native_labels), 4))
if len(native_labels) == 1:
    axes = [axes]
for i, label in enumerate(native_labels):
    p = all_predictions[label]
    cm = confusion_matrix(p["y_true"], (p["y_score"] >= 0.5).astype(int), normalize="true")
    im = axes[i].imshow(cm, cmap="Blues", vmin=0, vmax=1)
    for r in range(2):
        for c in range(2):
            axes[i].text(c, r, f"{cm[r,c]:.2f}", ha="center", va="center", fontsize=12)
    axes[i].set_title(label, fontsize=10)
    axes[i].set_xlabel("Predicted"); axes[i].set_ylabel("True")
    axes[i].set_xticks([0,1]); axes[i].set_yticks([0,1])
fig.suptitle("Confusion Matrices (row-normalized) — Logistic Regression", fontweight="bold")
fig.tight_layout()
fig.savefig(FIG_DIR / "07_confusion_matrices.png"); plt.close(fig)
print("  Saved 07_confusion_matrices.png")

# ── Chart 5: Feature Importance (LR coefficients) ────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 8))
for i, variant in enumerate(["peacetime", "wartime", "pooled"]):
    clf = models[variant]
    feature_names = datasets[variant]["train"]["X"].columns
    coefs = pd.Series(np.abs(clf.coef_[0]), index=feature_names).sort_values(ascending=True)
    top20 = coefs.tail(20)
    top20.plot.barh(ax=axes[i], color=VARIANT_COLORS[variant], alpha=0.8)
    axes[i].set_title(f"{variant.upper()} — Top 20 |coef|", fontsize=10)
    axes[i].set_xlabel("|Coefficient|")
fig.suptitle("Feature Importance (|Coefficients|) — Logistic Regression", fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(FIG_DIR / "10_feature_importance.png"); plt.close(fig)
print("  Saved 10_feature_importance.png")

# ── Chart 6: Score Distributions ──────────────────────────────────────────────
fig, axes = plt.subplots(1, len(native_labels), figsize=(5*len(native_labels), 4))
if len(native_labels) == 1:
    axes = [axes]
for i, label in enumerate(native_labels):
    p = all_predictions[label]
    y_true = p["y_true"]
    y_score = p["y_score"]
    axes[i].hist(y_score[y_true == 0], bins=50, alpha=0.6, color="blue", label="Negative", density=True)
    axes[i].hist(y_score[y_true == 1], bins=50, alpha=0.6, color="red", label="Positive", density=True)
    axes[i].set_title(label, fontsize=10)
    axes[i].set_xlabel("Predicted probability")
    axes[i].legend(fontsize=8)
fig.suptitle("Score Distributions — Logistic Regression", fontweight="bold")
fig.tight_layout()
fig.savefig(FIG_DIR / "13_score_distributions.png"); plt.close(fig)
print("  Saved 13_score_distributions.png")

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Save metrics
# ═══════════════════════════════════════════════════════════════════════════════
metrics_path = FIG_DIR / "metrics.csv"
results_df.to_csv(metrics_path, index=False)
print(f"\nSaved metrics to {metrics_path}")
print(results_df[["label", "auc_roc", "auc_pr", "logloss", "brier", "n", "base_rate"]].to_string(index=False))

session.close()
print(f"\n✅ Pipeline complete — all outputs in {FIG_DIR}")
