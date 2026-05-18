"""
FastAPI backend — fetches live Prozorro tenders, engineers features,
runs PROZORRO_COMPETITIVENESS_POOLED model via Snowflake ML Registry.
"""
import os, asyncio, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger("prozorro_api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Prozorro Live Risk API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROZORRO_API = "https://public-api.prozorro.gov.ua/api/2.5"
WARTIME_START = datetime(2022, 2, 24, tzinfo=timezone.utc)

COMPETITIVE_METHODS = {
    "belowThreshold","aboveThreshold","aboveThresholdUA","priceQuotation",
    "aboveThresholdEU","aboveThresholdUA.defense","requestForProposal",
    "closeFrameworkAgreementSelectionUA","esco","simple.defense",
    "closeFrameworkAgreementUA","competitiveDialogueUA","competitiveDialogueUA.stage2",
    "competitiveDialogueEU","competitiveDialogueEU.stage2",
}

CPV_CONSTRUCTION   = {"45"}
CPV_MEDICAL        = {"33","85"}
CPV_IT             = {"30","32","48","50","72"}
CPV_ENGINEERING    = {"71","73"}
CPV_ENERGY         = {"09","31","65"}
CPV_FOOD           = {"03","15"}
CPV_RECONSTRUCTION = {"45","44","43"}

def cpv_flag(cpv2: str, groups: set) -> bool:
    return cpv2 in groups

def engineer_features(t: dict) -> dict:
    """Extract model features from raw Prozorro API tender dict."""
    val  = t.get("value") or {}
    ent  = t.get("procuringEntity") or {}
    eid  = (ent.get("identifier") or {})
    addr = (ent.get("address") or {})
    items = t.get("items") or []

    # dates
    date_str = t.get("datePublished") or t.get("dateModified") or ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    # timing
    def period_hours(p: dict) -> Optional[float]:
        s, e = p.get("startDate"), p.get("endDate")
        if not s or not e:
            return None
        try:
            return (datetime.fromisoformat(e.replace("Z","+00:00")) -
                    datetime.fromisoformat(s.replace("Z","+00:00"))).total_seconds() / 3600
        except Exception:
            return None

    enq_h  = period_hours(t.get("enquiryPeriod") or {})
    tend_h = period_hours(t.get("tenderPeriod") or {})

    # CPV
    cpvs = [((i.get("classification") or {}).get("id") or "")[:2] for i in items]
    cpvs4 = list({((i.get("classification") or {}).get("id") or "")[:4] for i in items if i.get("classification")})
    primary_cpv4 = cpvs4[0] if cpvs4 else None
    unique_cpv2  = set(cpvs)

    method = t.get("procurementMethodType","")
    proc_method = t.get("procurementMethod","")
    amount = float(val.get("amount") or 0)

    # near-threshold heuristic (UA thresholds: 200k, 1.5M UAH)
    near_thresh = None
    for thr in [200_000, 1_500_000, 5_000_000]:
        ratio = amount / thr if thr else None
        if ratio and 0.8 <= ratio <= 1.05:
            near_thresh = ratio
            break

    kind = ent.get("kind","")

    return {
        "PROCUREMENT_METHOD_TYPE": method,
        "PROCUREMENT_METHOD":      proc_method,
        "FLAG_RESTRICTED_PROCEDURE": proc_method in ("selective","limited"),
        "FLAG_NO_CALL_FOR_TENDER":   proc_method == "limited",
        "SIGNAL_ENQUIRY_PERIOD_HOURS": enq_h,
        "SIGNAL_TENDER_PERIOD_HOURS":  tend_h,
        "SIGNAL_ENQUIRY_PERIOD_BELOW_LEGAL_MIN": (enq_h is not None and enq_h < 120),
        "SIGNAL_TENDER_PERIOD_BELOW_LEGAL_MIN":  (tend_h is not None and tend_h < 120),
        "FLAG_IS_DECEMBER_PUBLISH":    dt.month == 12,
        "FLAG_IS_YEAR_BOUNDARY_PUBLISH": dt.month in (12, 1),
        "FLAG_IS_WARTIME_REGIME":       dt >= WARTIME_START,
        "FLAG_IS_WARTIME_SIMPLIFIED":   dt >= WARTIME_START,
        "VALUE_AMOUNT": amount,
        "VALUE_CURRENCY": val.get("currency","UAH"),
        "SIGNAL_NEAR_THRESHOLD_RATIO":  near_thresh,
        "FLAG_NEAR_THRESHOLD_CLUSTER":  near_thresh is not None,
        "SIGNAL_ITEM_COUNT":      len(items),
        "SIGNAL_CPV_HETEROGENEITY": len(unique_cpv2),
        "STAT_PRIMARY_CPV_4DIGIT":  primary_cpv4,
        "FLAG_MISSING_TENDER_DOCUMENTATION": not bool(t.get("documents")),
        "FLAG_DESCRIPTION_LENGTH_SUSPICIOUS": len(t.get("description","")) < 20,
        "FLAG_CPV_CONSTRUCTION":   any(cpv_flag(c, CPV_CONSTRUCTION) for c in unique_cpv2),
        "FLAG_CPV_MEDICAL_PHARMA": any(cpv_flag(c, CPV_MEDICAL) for c in unique_cpv2),
        "FLAG_CPV_IT_ELECTRONICS": any(cpv_flag(c, CPV_IT) for c in unique_cpv2),
        "FLAG_CPV_ENGINEERING_SERVICES": any(cpv_flag(c, CPV_ENGINEERING) for c in unique_cpv2),
        "FLAG_CPV_ENERGY":     any(cpv_flag(c, CPV_ENERGY) for c in unique_cpv2),
        "FLAG_CPV_FOODSERVICE": any(cpv_flag(c, CPV_FOOD) for c in unique_cpv2),
        "FLAG_RECONSTRUCTION_RELATED": any(cpv_flag(c, CPV_RECONSTRUCTION) for c in unique_cpv2),
        "PROCURER_KIND":   kind,
        "PROCURER_REGION": addr.get("region",""),
        "FLAG_PROCURER_DEFENSE":   kind == "defense",
        "FLAG_PROCURER_MUNICIPAL": kind in ("general","authority"),
    }


def score_tender_heuristic(features: dict) -> float:
    """
    Rule-based risk score (0-1) when Snowflake model is unavailable.
    Mirrors the model's top SHAP drivers from the paper.
    """
    score = 0.45  # wartime base rate

    if features.get("FLAG_RESTRICTED_PROCEDURE"):       score += 0.15
    if features.get("FLAG_NO_CALL_FOR_TENDER"):         score += 0.10
    if features.get("FLAG_NEAR_THRESHOLD_CLUSTER"):     score += 0.08
    if features.get("FLAG_MISSING_TENDER_DOCUMENTATION"): score += 0.06
    if features.get("FLAG_IS_DECEMBER_PUBLISH"):        score += 0.05
    if features.get("FLAG_PROCURER_DEFENSE"):           score += 0.05
    if features.get("SIGNAL_ENQUIRY_PERIOD_BELOW_LEGAL_MIN"): score += 0.07
    if features.get("SIGNAL_TENDER_PERIOD_BELOW_LEGAL_MIN"):  score += 0.07
    if features.get("FLAG_CPV_CONSTRUCTION"):           score += 0.04
    if features.get("FLAG_DESCRIPTION_LENGTH_SUSPICIOUS"): score += 0.03
    # item heterogeneity lowers risk slightly
    if (features.get("SIGNAL_CPV_HETEROGENEITY") or 0) > 3: score -= 0.04

    return round(min(max(score, 0.05), 0.97), 3)


def build_snowflake_session():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption
    from cryptography.hazmat.backends import default_backend
    from snowflake.snowpark import Session

    raw_key = os.getenv("SNOWFLAKE_PRIVATE_KEY_RAW")
    if raw_key:
        import base64
        key_content = base64.b64decode(raw_key)
        pk = load_pem_private_key(key_content, password=None, backend=default_backend())
    else:
        key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", str(Path.home() / ".snowflake" / "rsa_key.p8"))
        with open(key_path, "rb") as f:
            pk = load_pem_private_key(f.read(), password=None, backend=default_backend())
    
    pk_bytes = pk.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())

    cfg = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT", "xdc20991.us-east-1"),
        "user":      os.getenv("SNOWFLAKE_USER",    "MMACFA"),
        "private_key": pk_bytes,
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE","COMPUTE_WH"),
        "database":  os.getenv("SNOWFLAKE_DATABASE", "PROZORRO"),
        "schema":    os.getenv("SNOWFLAKE_SCHEMA",   "DETECTION"),
    }
    return Session.builder.configs(cfg).create()


def enrich_from_snowflake_history(features_list: List[dict], session) -> List[dict]:
    """
    Enrich engineered features with historical aggregates from Snowflake.
    Computes Family I (procurer history) and Family J (CPV market context)
    by querying past records in the gold table — the same logic as the
    F_PROCURER_HISTORY and F_CPV_MARKET_CONTEXT views, computed on-demand.
    LightGBM handles any remaining NaN columns natively.
    """
    edrpous = list({f.get("_PROCURER_EDRPOU", "") for f in features_list if f.get("_PROCURER_EDRPOU")})
    cpv4s   = list({f.get("STAT_PRIMARY_CPV_4DIGIT", "") for f in features_list if f.get("STAT_PRIMARY_CPV_4DIGIT")})

    procurer_stats = {}
    cpv_stats = {}

    # ── Procurer history (Family I) ─────────────────────
    if edrpous:
        escaped = ",".join(f"'{e}'" for e in edrpous)
        sql = f"""
            SELECT
                PROCURER_EDRPOU,
                COUNT(*)                                       AS HIST_TENDER_COUNT,
                AVG(SIGNAL_IS_SINGLE_BIDDER::INT)              AS HIST_SINGLE_BIDDER_RATE,
                AVG(SIGNAL_TENDER_PERIOD_HOURS)                AS HIST_AVG_TENDER_PERIOD_HOURS,
                AVG(VALUE_AMOUNT)                              AS HIST_AVG_VALUE_AMOUNT,
                APPROX_TOP_K(WINNING_SUPPLIER_EDRPOU, 100)     AS _top_k   -- for HHI proxy
            FROM PROZORRO.GOLD.GOLD_FEATURE_ENRICHED_TENDERS
            WHERE PROCURER_EDRPOU IN ({escaped})
              AND STATUS = 'complete'
            GROUP BY PROCURER_EDRPOU
        """
        try:
            rows = session.sql(sql).collect()
            for row in rows:
                procurer_stats[row["PROCURER_EDRPOU"]] = {
                    "HIST_PROCURER_TENDER_COUNT":        row["HIST_TENDER_COUNT"],
                    "HIST_SINGLE_BIDDER_RATE_365D":      row["HIST_SINGLE_BIDDER_RATE"],
                    "HIST_AVG_TENDER_PERIOD_HOURS":      row["HIST_AVG_TENDER_PERIOD_HOURS"],
                    "HIST_LOG_VALUE_AMOUNT":             (
                        __import__("math").log1p(row["HIST_AVG_VALUE_AMOUNT"])
                        if row["HIST_AVG_VALUE_AMOUNT"] else None
                    ),
                }
        except Exception as e:
            log.warning("Procurer history query failed: %s", e)

    # ── CPV market context (Family J) ───────────────────
    if cpv4s:
        escaped_cpv = ",".join(f"'{c}'" for c in cpv4s)
        sql_cpv = f"""
            SELECT
                STAT_PRIMARY_CPV_4DIGIT,
                COUNT(DISTINCT WINNING_SUPPLIER_EDRPOU)        AS CPV_UNIQUE_SUPPLIER_COUNT,
                AVG(SIGNAL_IS_SINGLE_BIDDER::INT)              AS CPV_SINGLE_BIDDER_RATE,
                AVG(VALUE_AMOUNT)                              AS CPV_AVG_VALUE
            FROM PROZORRO.GOLD.GOLD_FEATURE_ENRICHED_TENDERS
            WHERE STAT_PRIMARY_CPV_4DIGIT IN ({escaped_cpv})
              AND STATUS = 'complete'
            GROUP BY STAT_PRIMARY_CPV_4DIGIT
        """
        try:
            rows = session.sql(sql_cpv).collect()
            for row in rows:
                cpv_stats[row["STAT_PRIMARY_CPV_4DIGIT"]] = {
                    "CPV_UNIQUE_SUPPLIER_COUNT_365D": row["CPV_UNIQUE_SUPPLIER_COUNT"],
                    "CPV_SINGLE_BIDDER_BASE_RATE":    row["CPV_SINGLE_BIDDER_RATE"],
                    "CPV_LOG_AVG_VALUE":              (
                        __import__("math").log1p(row["CPV_AVG_VALUE"])
                        if row["CPV_AVG_VALUE"] else None
                    ),
                }
        except Exception as e:
            log.warning("CPV market query failed: %s", e)

    # ── Merge into feature dicts ─────────────────────────
    enriched = []
    for f in features_list:
        f = dict(f)  # copy
        edrpou = f.pop("_PROCURER_EDRPOU", None)
        if edrpou and edrpou in procurer_stats:
            f.update(procurer_stats[edrpou])
        cpv4 = f.get("STAT_PRIMARY_CPV_4DIGIT")
        if cpv4 and cpv4 in cpv_stats:
            f.update(cpv_stats[cpv4])
        enriched.append(f)

    log.info("Enriched %d tenders: %d procurer matches, %d CPV matches",
             len(enriched), len(procurer_stats), len(cpv_stats))
    return enriched


_LOCAL_MODEL_CACHE = None

def run_model_on_features(features_list: List[dict]) -> List[float]:
    """Score features via Snowflake ML Registry. Falls back to heuristic.

    Output column confirmed as 'output_feature_0' (DOUBLE, calibrated probability 0–1).
    Uses locally cached model inference to avoid slow round-trips to Snowflake.
    """
    global _LOCAL_MODEL_CACHE
    try:
        import pandas as pd
        
        if _LOCAL_MODEL_CACHE is None:
            session = build_snowflake_session()
            try:
                from snowflake.ml.registry import Registry
                reg = Registry(session, database_name="PROZORRO", schema_name="PLATINUM")
                mv  = reg.get_model("PLATINUM_COMPETITIVENESS_WARTIME").version("V_20260513_CUSTOM")
                _LOCAL_MODEL_CACHE = mv.load()
            finally:
                session.close()

        df  = pd.DataFrame(features_list)
        # Model signature expects DOUBLE for all columns — cast everything to float64
        # Booleans → 1.0/0.0, strings (method/region) → NaN (LightGBM handles missing)
        for col in df.columns:
            if df[col].dtype == bool:
                df[col] = df[col].astype(float)
            elif df[col].dtype == object:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        # Fill missing composite features for the wartime model
        df["COMPOSITE_CRI_PROCEDURE_RESTRICTIVENESS"] = 0.0
        df["_PEER_GROUP_SIZE"] = 1.0

        # Keep only the columns expected by the wartime model in correct order
        # (34 features — no _IS_WARTIME since model was trained on wartime data only)
        MODEL_COLS = [
            'PROCUREMENT_METHOD', 'PROCUREMENT_METHOD_TYPE', 'FLAG_BELOW_THRESHOLD_WITH_BIDDING',
            'FLAG_NON_PRICE_AWARD_CRITERIA', 'SIGNAL_ENQUIRY_PERIOD_HOURS', 'SIGNAL_TENDER_PERIOD_HOURS',
            'SIGNAL_ENQUIRY_PERIOD_BELOW_LEGAL_MIN', 'SIGNAL_TENDER_PERIOD_BELOW_LEGAL_MIN',
            'SIGNAL_TENDER_PERIOD_RATIO_TO_PEER_MEDIAN', 'FLAG_IS_DECEMBER_PUBLISH',
            'FLAG_IS_YEAR_BOUNDARY_PUBLISH', 'FLAG_IS_UKRAINIAN_HOLIDAY_PUBLISH', 'FLAG_IS_WARTIME_REGIME',
            'FLAG_IS_WARTIME_SIMPLIFIED', 'VALUE_AMOUNT', 'SIGNAL_ITEM_COUNT', 'SIGNAL_CPV_HETEROGENEITY',
            'SIGNAL_LARGE_LOT_COUNT', 'STAT_PRIMARY_CPV_4DIGIT', 'FLAG_MISSING_TENDER_DOCUMENTATION',
            'FLAG_DESCRIPTION_LENGTH_SUSPICIOUS', 'FLAG_CPV_CONSTRUCTION', 'FLAG_CPV_MEDICAL_PHARMA',
            'FLAG_CPV_IT_ELECTRONICS', 'FLAG_CPV_ENGINEERING_SERVICES', 'FLAG_CPV_ENERGY',
            'FLAG_CPV_FOODSERVICE', 'FLAG_RECONSTRUCTION_RELATED', 'PROCURER_KIND', 'PROCURER_REGION',
            'FLAG_PROCURER_DEFENSE', 'FLAG_PROCURER_MUNICIPAL', 'COMPOSITE_CRI_PROCEDURE_RESTRICTIVENESS',
            '_PEER_GROUP_SIZE'
        ]
        # Add any missing columns as NaN
        for col in MODEL_COLS:
            if col not in df.columns:
                df[col] = float("nan")
        df = df[MODEL_COLS].astype(float)
        
        # Run inference locally with cached model
        result_df = _LOCAL_MODEL_CACHE.predict(df)

        # Primary: confirmed column name from registry inspection
        if "output_feature_0" in result_df.columns:
            return [round(float(v), 3) for v in result_df["output_feature_0"]], "snowflake_model"

        # Fallback: any float column in [0,1] range
        for c in result_df.columns:
            try:
                vals = result_df[c].astype(float)
                if vals.between(0, 1).all():
                    log.info("Using fallback probability column: %s", c)
                    return [round(float(v), 3) for v in vals], "snowflake_model"
            except Exception:
                pass

        log.warning("No probability column found in model output: %s", list(result_df.columns))
        return [score_tender_heuristic(f) for f in features_list], "heuristic"
    except Exception as e:
        msg = str(e)
        if "not logged for inference in Warehouse" in msg:
            log.warning("Model needs WAREHOUSE target. Using heuristic.")
        else:
            log.warning("Snowflake model unavailable — FULL ERROR: %s", msg)
        return [score_tender_heuristic(f) for f in features_list], "heuristic"


@app.get("/api/tenders")
async def get_live_tenders(limit: int = 50, date_from: str = "", proc_method: str = ""):
    """Fetch tenders from Prozorro API and score them.
    date_from:   optional ISO date e.g. '2023-01-01T00:00:00Z'
    proc_method: 'open' | 'selective' | 'limited' | '' (all)
      - open:      procurementMethod == 'open'      (anyone can bid)
      - selective: procurementMethod == 'selective' (pre-qualified list only)
      - limited:   procurementMethod == 'limited'   (direct negotiation)
    """
    async with httpx.AsyncClient(timeout=30) as client:
        all_ids: list = []
        page_offset: str | None = None
        while len(all_ids) < 300:
            params: dict = {"descending": 1, "limit": 100}
            if page_offset:
                params["offset"] = page_offset
            if date_from:
                params["dateModified"] = date_from
            resp = await client.get(f"{PROZORRO_API}/tenders", params=params)
            if resp.status_code != 200:
                break
            body = resp.json()
            page_ids = [item["id"] for item in body.get("data", [])]
            if not page_ids:
                break
            all_ids.extend(page_ids)
            page_offset = body.get("next_page", {}).get("offset")
            if not page_offset:
                break

        results = []
        batch = all_ids[:200]
        tasks = [client.get(f"{PROZORRO_API}/tenders/{tid}") for tid in batch]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        seen_methods: dict = {}
        for r in responses:
            if isinstance(r, Exception) or r.status_code != 200:
                continue
            t = r.json().get("data", {})
            # Filter by procurementMethod (open / selective / limited)
            if proc_method and t.get("procurementMethod", "") != proc_method:
                continue
            method = t.get("procurementMethodType", "unknown")
            if seen_methods.get(method, 0) >= 15:
                continue
            seen_methods[method] = seen_methods.get(method, 0) + 1
            results.append(t)
            if len(results) >= limit:
                break

    if not results:
        raise HTTPException(404, f"No tenders found (proc_method={proc_method!r})")

    # Step 3: engineer base features (Families A–H, structural flags)
    raw_features = []
    for t in results:
        feat = engineer_features(t)
        # stash EDRPOU for history lookup, will be popped before scoring
        ent = t.get("procuringEntity") or {}
        feat["_PROCURER_EDRPOU"] = ((ent.get("identifier") or {}).get("id") or "")
        raw_features.append(feat)

    # Step 4: enrich with Families I & J from Snowflake historical aggregates
    scorer_source = "snowflake_model"
    try:
        session = build_snowflake_session()
        try:
            enriched_features = enrich_from_snowflake_history(raw_features, session)
        finally:
            session.close()
    except Exception as e:
        log.warning("Could not open Snowflake for history enrichment: %s", e)
        enriched_features = [{k: v for k, v in f.items() if not k.startswith("_")} for f in raw_features]
        scorer_source = "heuristic"

    # Step 5: score via ML Registry model
    result = run_model_on_features(enriched_features)
    if isinstance(result, tuple):
        scores, scorer_source = result
    else:
        scores = result

    output = []
    for t, feat, score in zip(results, raw_features, scores):
        bids = t.get("bids") or []
        unique_bidders = len({
            (b.get("tenderers") or [{}])[0].get("identifier", {}).get("id", f"b{i}")
            for i, b in enumerate(bids)
        }) if bids else None

        tid = str(t.get("id") or t.get("tenderID") or "")
        
        interpretation = "Low Risk"
        if score >= 0.65:
            reasons = []
            if feat.get("FLAG_RESTRICTED_PROCEDURE"): reasons.append("restricted procedure type")
            if feat.get("FLAG_NEAR_THRESHOLD_CLUSTER"): reasons.append("near-threshold value")
            if feat.get("SIGNAL_TENDER_PERIOD_BELOW_LEGAL_MIN"): reasons.append("abnormally short tender period")
            if feat.get("FLAG_MISSING_TENDER_DOCUMENTATION"): reasons.append("missing documentation")
            if len(reasons) > 0:
                interpretation = "High risk due to " + ", ".join(reasons) + "."
            else:
                interpretation = "High risk based on complex structural features."
        elif score >= 0.45:
            interpretation = "Medium risk due to combination of peacetime and wartime predictive factors."

        output.append({
            "id":          t.get("tenderID", t["id"][:16]),
            "title":       t.get("title", ""),
            "title_en":    None,
            "href":        f"https://prozorro.gov.ua/tender/{t['id']}",
            "method":      t.get("procurementMethodType",""),
            "status":      t.get("status",""),
            "value_uah":   feat["VALUE_AMOUNT"],
            "procurer":    (t.get("procuringEntity") or {}).get("name","")[:60],
            "procurer_en": None,
            "region":      feat["PROCURER_REGION"],
            "date":        t.get("datePublished","")[:10],
            "cpv4":        feat["STAT_PRIMARY_CPV_4DIGIT"],
            "interpretation": interpretation,
            "item_count":  feat["SIGNAL_ITEM_COUNT"],
            "bid_count":   unique_bidders,
            "is_single_bidder": (unique_bidders == 1) if unique_bidders else None,
            "risk_score":  score,
            "risk_level":  "HIGH" if score >= 0.65 else ("MEDIUM" if score >= 0.45 else "LOW"),
            "wartime":     feat["FLAG_IS_WARTIME_REGIME"],
            "flags": {
                "restricted":   feat["FLAG_RESTRICTED_PROCEDURE"],
                "near_thresh":  feat["FLAG_NEAR_THRESHOLD_CLUSTER"],
                "short_period": feat["SIGNAL_TENDER_PERIOD_BELOW_LEGAL_MIN"],
                "no_docs":      feat["FLAG_MISSING_TENDER_DOCUMENTATION"],
                "december":     feat["FLAG_IS_DECEMBER_PUBLISH"],
            },
            "source": scorer_source,
        })

    return {"tenders": output, "fetched_at": datetime.utcnow().isoformat() + "Z"}


# ── On-demand translation cache (LRU) ──────────────────────────────────────
_TRANSLATION_CACHE: dict = {}  # key: text_hash → translated string
_TRANSLATION_CACHE_MAX = 2000

from pydantic import BaseModel as _BaseModel
class TranslateRequest(_BaseModel):
    title: str = ""
    procurer: str = ""

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    """Translate Ukrainian title/procurer to English on demand via Snowflake Cortex.
    Results are cached server-side so repeated hovers don't re-query."""
    import hashlib
    cache_key = hashlib.md5((req.title + "||" + req.procurer).encode()).hexdigest()
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    title_en = req.title
    procurer_en = req.procurer
    try:
        session = build_snowflake_session()
        try:
            title_sql = req.title.replace("'", "''")
            procurer_sql = req.procurer.replace("'", "''")
            sql = f"""SELECT
                SNOWFLAKE.CORTEX.TRANSLATE('{title_sql}', 'uk', 'en') AS TITLE_EN,
                SNOWFLAKE.CORTEX.TRANSLATE('{procurer_sql}', 'uk', 'en') AS PROCURER_EN"""
            row = session.sql(sql).collect()[0]
            title_en = row["TITLE_EN"]
            procurer_en = row["PROCURER_EN"]
        finally:
            session.close()
    except Exception as e:
        log.warning("Translation failed: %s", e)

    result = {"title_en": title_en, "procurer_en": procurer_en}
    # Evict oldest entries if cache is full
    if len(_TRANSLATION_CACHE) >= _TRANSLATION_CACHE_MAX:
        oldest = next(iter(_TRANSLATION_CACHE))
        del _TRANSLATION_CACHE[oldest]
    _TRANSLATION_CACHE[cache_key] = result
    return result


@app.get("/api/paper-stats")
async def paper_stats():
    """Return key statistics from the published research paper — platinum-v2 run V_20260513_223800."""
    return {
        "sample": {"total": 4540000, "peacetime": 2599506, "wartime": 1907783,
                   "test_peacetime": 10042, "test_wartime": 54858},
        "performance": [
            {"model":"Peacetime","algo":"LightGBM","auc":0.783,"f1":0.741,"precision":0.824,"recall":0.672,"brier":0.183,"logloss":0.524,"n":10042},
            {"model":"Wartime",  "algo":"LightGBM","auc":0.772,"f1":0.757,"precision":0.767,"recall":0.748,"brier":0.190,"logloss":0.558,"n":54858},
            {"model":"Pooled (wartime test)","algo":"LightGBM","auc":0.768,"f1":0.756,"precision":0.753,"recall":0.758,"brier":0.190,"logloss":0.556,"n":54858},
            {"model":"Pooled (peacetime test)","algo":"LightGBM","auc":0.870,"f1":0.851,"precision":0.819,"recall":0.885,"brier":0.142,"logloss":0.425,"n":10042},
        ],
        "transfer_matrix": [
            {"model":"Peacetime","test":"Peacetime","kind":"native",  "auc":0.783,"n":10042},
            {"model":"Peacetime","test":"Wartime",  "kind":"transfer","auc":0.546,"n":54858},
            {"model":"Wartime",  "test":"Wartime",  "kind":"native",  "auc":0.772,"n":54858},
            {"model":"Wartime",  "test":"Peacetime","kind":"transfer","auc":0.771,"n":10042},
            {"model":"Pooled",   "test":"Wartime",  "kind":"native",  "auc":0.768,"n":54858},
            {"model":"Pooled",   "test":"Peacetime","kind":"native",  "auc":0.870,"n":10042},
        ],
        "family_shap": [
            {"family":"A","label":"Tender Config",    "peacetime":1.998,"wartime":0.877,"delta":-1.121,"effect":"large↓"},
            {"family":"E","label":"Item / CPV",       "peacetime":0.356,"wartime":0.515,"delta": 0.158,"effect":"medium↑"},
            {"family":"B","label":"Timing",           "peacetime":0.269,"wartime":0.349,"delta": 0.080,"effect":"medium↑"},
            {"family":"D","label":"Value / Threshold","peacetime":0.373,"wartime":0.332,"delta":-0.041,"effect":"negligible↓"},
            {"family":"I","label":"Procurer History", "peacetime":0.211,"wartime":0.317,"delta": 0.106,"effect":"large↑"},
            {"family":"J","label":"CPV Market",       "peacetime":0.224,"wartime":0.249,"delta": 0.025,"effect":"small↑"},
            {"family":"H","label":"Procurer Identity","peacetime":0.097,"wartime":0.111,"delta": 0.014,"effect":"negligible↑"},
            {"family":"C","label":"Calendar",         "peacetime":0.041,"wartime":0.066,"delta": 0.025,"effect":"medium↑"},
            {"family":"G","label":"Sector",           "peacetime":0.023,"wartime":0.035,"delta": 0.012,"effect":"small↑"},
            {"family":"F","label":"Documentation",    "peacetime":0.026,"wartime":0.006,"delta":-0.021,"effect":"large↓"},
            {"family":"K","label":"Geographic",       "peacetime":0.007,"wartime":0.014,"delta": 0.007,"effect":"large↑"},
        ],
        "permutation_test": [
            {"model":"Peacetime","p_value":0.007,"significant":True},
            {"model":"Wartime",  "p_value":0.066,"significant":False},
            {"model":"Pooled",   "p_value":0.003,"significant":True},
        ],
        "regime_stats": {
            "peacetime_single_bidder_rate": 0.662,
            "wartime_single_bidder_rate":   0.609,
            "regime_boundary": "2022-10-12",
            "family_a_drop_factor": 2.3,
            "transfer_auc_drop_pw": 0.237,
            "transfer_auc_drop_wp": 0.012,
            "n_features": 34,
            "run_id": "V_20260513_223800",
        }
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    # Serve images and other static files from the Vite build output
    if (frontend_dist / "img").exists():
        app.mount("/img", StaticFiles(directory=str(frontend_dist / "img")), name="img")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve the API if requested path matches /api
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        # Check if the requested file exists in dist (e.g. .png, .ico, .json)
        file_path = frontend_dist / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html (SPA routing)
        return FileResponse(frontend_dist / "index.html")
