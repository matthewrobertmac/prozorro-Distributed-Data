"""
Prozorro Competitiveness Wartime — Snowflake Model Registry Inference
=====================================================================
Connects to Snowflake, loads PROZORRO_COMPETITIVENESS_WARTIME model
version V_20260428_233958, and runs predictions via the ML Registry.

Usage:
    python snowflake_inference.py                    # predict from Snowflake table
    python snowflake_inference.py --local path.csv   # predict from local CSV
    python snowflake_inference.py --output results.csv
"""

import os
import sys
import argparse
import logging
from pathlib import Path

from typing import Optional

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Load .env FIRST — before any os.getenv() calls
# ──────────────────────────────────────────────
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
            log.info("Loaded .env from %s", env_path)
    except ImportError:
        pass   # dotenv not installed — rely on shell env vars

_load_dotenv()   # must run before SNOWFLAKE_CONFIG is built

# ──────────────────────────────────────────────
# Config  (reads env vars after .env is loaded)
# ──────────────────────────────────────────────
SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT",   "xdc20991"),
    "user":      os.getenv("SNOWFLAKE_USER",       "MMACFA"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD",   ""),   # REQUIRED
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE",  "COMPUTE_WH"),
    "database":  os.getenv("SNOWFLAKE_DATABASE",   "PROZORRO"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA",     "DETECTION"),
    "role":      os.getenv("SNOWFLAKE_ROLE",       ""),   # optional
}

MODEL_NAME    = os.getenv("MODEL_NAME",    "PROZORRO_COMPETITIVENESS_WARTIME")
MODEL_VERSION = os.getenv("MODEL_VERSION", "V_20260428_233958")
MODEL_DB      = os.getenv("MODEL_DB",      "PROZORRO")
MODEL_SCHEMA  = os.getenv("MODEL_SCHEMA",  "DETECTION")

# Snowflake table to read input from (if not using --local)
INPUT_TABLE   = os.getenv("INPUT_TABLE",   "PROZORRO.DETECTION.TENDER_FEATURES")

# ──────────────────────────────────────────────
# Session factory
# ──────────────────────────────────────────────
def build_session():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.backends import default_backend
    from snowflake.snowpark import Session

    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", str(Path.home() / ".snowflake" / "rsa_key.p8"))
    with open(key_path, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None, backend=default_backend())

    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    private_key_bytes = private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )

    cfg = {
        "account":     os.getenv("SNOWFLAKE_ACCOUNT",   "xdc20991.us-east-1"),
        "user":        os.getenv("SNOWFLAKE_USER",       "MMACFA"),
        "private_key": private_key_bytes,
        "warehouse":   os.getenv("SNOWFLAKE_WAREHOUSE",  "COMPUTE_WH"),
        "database":    os.getenv("SNOWFLAKE_DATABASE",   "PROZORRO"),
        "schema":      os.getenv("SNOWFLAKE_SCHEMA",     "DETECTION"),
    }
    role = os.getenv("SNOWFLAKE_ROLE", "")
    if role:
        cfg["role"] = role

    log.info(
        "Connecting to Snowflake  account=%s  user=%s  warehouse=%s  db=%s  schema=%s",
        cfg["account"], cfg["user"], cfg["warehouse"], cfg["database"], cfg["schema"],
    )
    session = Session.builder.configs(cfg).create()
    log.info("Session created — Snowflake version: %s", session.sql("SELECT CURRENT_VERSION()").collect()[0][0])
    return session



# ──────────────────────────────────────────────
# Input data loaders
# ──────────────────────────────────────────────
def load_from_snowflake(session, table: str):
    log.info("Loading input features from Snowflake table: %s", table)
    df = session.table(table).to_pandas()
    log.info("Loaded %d rows × %d columns", *df.shape)
    return df


def load_from_csv(path: str):
    log.info("Loading input features from local CSV: %s", path)
    df = pd.read_csv(path)
    log.info("Loaded %d rows × %d columns", *df.shape)
    return df


# ──────────────────────────────────────────────
# Model loading + inference
# ──────────────────────────────────────────────
def load_model(session):
    from snowflake.ml.registry import Registry

    log.info("Opening ML Registry — db=%s  schema=%s", MODEL_DB, MODEL_SCHEMA)
    reg = Registry(session, database_name=MODEL_DB, schema_name=MODEL_SCHEMA)

    log.info("Fetching model: %s", MODEL_NAME)
    model = reg.get_model(MODEL_NAME)

    log.info("Loading version: %s", MODEL_VERSION)
    mv = model.version(MODEL_VERSION)
    return mv


def run_inference(session, mv, input_df: pd.DataFrame) -> pd.DataFrame:
    """Run model prediction. Output column is 'output_feature_0' (calibrated prob 0–1)."""
    log.info("Converting input to Snowpark DataFrame (%d rows)…", len(input_df))
    snow_df = session.create_dataframe(input_df)

    log.info("Running model.predict()…")
    predictions = mv.run(snow_df, function_name="predict")
    result_df = predictions.to_pandas() if hasattr(predictions, "to_pandas") else predictions

    # Confirmed output column from registry inspection
    if "output_feature_0" in result_df.columns:
        result_df = result_df.rename(columns={"output_feature_0": "PREDICTED_PROB"})
        result_df["PREDICTED_CLASS"] = (result_df["PREDICTED_PROB"] >= 0.5).astype(int)
    else:
        # Fallback: find any float [0,1] column
        for c in result_df.columns:
            try:
                vals = result_df[c].astype(float)
                if vals.between(0, 1).all():
                    log.warning("output_feature_0 not found; using column '%s' as probability", c)
                    result_df = result_df.rename(columns={c: "PREDICTED_PROB"})
                    result_df["PREDICTED_CLASS"] = (result_df["PREDICTED_PROB"] >= 0.5).astype(int)
                    break
            except Exception:
                pass

    log.info("Predictions complete — %d rows returned", len(result_df))
    return result_df


# ──────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────
def save_results(df: pd.DataFrame, output_path: Optional[str]):
    if output_path:
        df.to_csv(output_path, index=False)
        log.info("Results saved → %s", output_path)
    else:
        print("\n── Prediction Results (first 20 rows) ─────────────────")
        print(df.head(20).to_string(index=False))
        print(f"\nTotal rows: {len(df)}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Run Prozorro Competitiveness model inference via Snowflake ML Registry"
    )
    p.add_argument(
        "--local", metavar="CSV_PATH",
        help="Path to a local CSV file to use as input instead of the Snowflake table",
    )
    p.add_argument(
        "--table", default=INPUT_TABLE,
        help=f"Snowflake table to read features from (default: {INPUT_TABLE})",
    )
    p.add_argument(
        "--output", metavar="OUTPUT_CSV",
        help="Save predictions to this CSV file (default: print to stdout)",
    )
    p.add_argument(
        "--model", default=MODEL_NAME,
        help=f"Model name in registry (default: {MODEL_NAME})",
    )
    p.add_argument(
        "--version", default=MODEL_VERSION,
        help=f"Model version (default: {MODEL_VERSION})",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Allow CLI overrides for model name/version
    global MODEL_NAME, MODEL_VERSION
    MODEL_NAME    = args.model
    MODEL_VERSION = args.version

    session = build_session()

    try:
        if args.local:
            input_df = load_from_csv(args.local)
        else:
            input_df = load_from_snowflake(session, args.table)

        mv = load_model(session)
        predictions = run_inference(session, mv, input_df)
        save_results(predictions, args.output)

    finally:
        session.close()
        log.info("Snowflake session closed.")


if __name__ == "__main__":
    main()
