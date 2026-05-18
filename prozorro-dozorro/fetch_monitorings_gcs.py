#!/usr/bin/env python3
"""
Dozorro Monitoring API → GCS Full Sync
========================================
Downloads ALL State Audit Service monitoring data (risk indicators, audits)
from the Prozorro Audit API → gs://dozorro-monitorings-gcs/
Self-terminates the GCE instance when complete.
"""

import json
import time
import gzip
import logging
import os
import sys
import signal
import subprocess
from datetime import datetime, timezone
from typing import Optional

import requests
from google.cloud import storage as gcs

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE        = "https://audit-api.prozorro.gov.ua/api/2.5"
BUCKET          = os.getenv("GCS_BUCKET", "dozorro-monitorings-gcs")
PROJECT         = os.getenv("GCP_PROJECT_ID", "zorro-493007")
FLUSH_EVERY     = int(os.getenv("FLUSH_EVERY", "1000"))
REQUEST_DELAY   = float(os.getenv("REQUEST_DELAY", "0.15"))
REQUEST_TIMEOUT = 30
CHECKPOINT_KEY  = "checkpoints/monitoring_sync_state.json"
DATA_PREFIX     = "monitorings"
SELF_TERMINATE  = os.getenv("SELF_TERMINATE", "true").lower() == "true"

# ── Logging ───────────────────────────────────────────────────────────────────
handlers = [logging.StreamHandler(sys.stdout)]
for path in ["/var/log/monitoring_sync.log", "/tmp/monitoring_sync.log"]:
    try:
        handlers.append(logging.FileHandler(path))
        break
    except:
        continue
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)
log = logging.getLogger("monitoring_sync")

# ── GCS client ────────────────────────────────────────────────────────────────
try:
    client = gcs.Client(project=PROJECT)
    bucket = client.bucket(BUCKET)
except Exception as e:
    log.error(f"Failed to initialize GCS client: {e}")
    sys.exit(1)

# ── Graceful shutdown ─────────────────────────────────────────────────────────
_shutdown = False
def _signal(sig, frame):
    global _shutdown
    log.info(f"Signal {sig} — finishing current batch then exiting.")
    _shutdown = True
signal.signal(signal.SIGTERM, _signal)
signal.signal(signal.SIGINT, _signal)

# ── Checkpoint ────────────────────────────────────────────────────────────────
def load_checkpoint() -> Optional[str]:
    blob = bucket.blob(CHECKPOINT_KEY)
    if blob.exists():
        try:
            return json.loads(blob.download_as_string())["next_page_url"]
        except Exception as e:
            log.error(f"Error reading checkpoint: {e}")
    return None

def save_checkpoint(next_page_url: str):
    blob = bucket.blob(CHECKPOINT_KEY)
    blob.upload_from_string(json.dumps({"next_page_url": next_page_url}), content_type="application/json")
    log.info(f"Checkpoint saved: {next_page_url}")

# ── Extraction ────────────────────────────────────────────────────────────────
def fetch_details(monitoring_id: str) -> Optional[dict]:
    url = f"{API_BASE}/monitorings/{monitoring_id}"
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json().get("data")
            elif r.status_code == 404:
                return None
            elif r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.warning(f"Error fetching {monitoring_id}: {e}. Retrying...")
            time.sleep(2 ** attempt)
    return None

def flush_batch(batch: list):
    if not batch: return
    
    # Use the date from the first item to structure folders
    dt = datetime.fromisoformat(batch[0]["dateModified"].replace("Z", "+00:00"))
    folder = f"{DATA_PREFIX}/{dt.strftime('%Y/%m/%d')}"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"monitorings_{timestamp}.jsonl.gz"
    path = f"{folder}/{filename}"
    
    blob = bucket.blob(path)
    
    # Write to local gz temp file
    temp_file = f"/tmp/{filename}"
    with gzip.open(temp_file, "wt", encoding="utf-8") as f:
        for item in batch:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    # Upload
    blob.upload_from_filename(temp_file, content_type="application/gzip")
    os.remove(temp_file)
    log.info(f"Uploaded {len(batch)} records to gs://{BUCKET}/{path}")

def run_sync():
    url = load_checkpoint() or f"{API_BASE}/monitorings?descending=1"
    log.info(f"Starting sync from: {url}")
    
    batch = []
    session = requests.Session()
    
    while url and not _shutdown:
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            page_data = r.json()
        except requests.exceptions.RequestException as e:
            log.error(f"Page request failed: {e}. Retrying in 10s...")
            time.sleep(10)
            continue
            
        items = page_data.get("data", [])
        if not items:
            log.info("Reached end of data stream.")
            break
            
        for item in items:
            if _shutdown: break
            monitoring_id = item["id"]
            
            details = fetch_details(monitoring_id)
            if details:
                batch.append(details)
                
            time.sleep(REQUEST_DELAY)
            
            if len(batch) >= FLUSH_EVERY:
                flush_batch(batch)
                batch = []
                save_checkpoint(url) # Save the last known page
        
        # Move to next page
        next_url = page_data.get("next_page", {}).get("uri")
        if not next_url or next_url == url:
            log.info("Pagination halted.")
            break
        url = next_url
        
    # Flush remaining
    if batch:
        flush_batch(batch)
        save_checkpoint(url)
        
    log.info("Sync complete or gracefully stopped.")

# ── Self-termination ──────────────────────────────────────────────────────────
def terminate_instance():
    if not SELF_TERMINATE:
        return
        
    log.info("Self-termination requested.")
    try:
        # Check if we are on GCE
        r = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/name", 
                         headers={"Metadata-Flavor": "Google"}, timeout=2)
        if r.status_code == 200:
            name = r.text
            zone_full = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/zone", 
                                     headers={"Metadata-Flavor": "Google"}).text
            zone = zone_full.split('/')[-1]
            log.info(f"Deleting instance {name} in {zone}...")
            subprocess.run(["gcloud", "compute", "instances", "delete", name, "--zone", zone, "--quiet"])
    except Exception as e:
        log.error(f"Could not self-terminate: {e}")

if __name__ == "__main__":
    run_sync()
    if not _shutdown:
        terminate_instance()
