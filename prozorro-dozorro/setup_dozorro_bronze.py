import os
import sys
import warnings
from pathlib import Path

# Suppress warnings for clean output
warnings.filterwarnings("ignore")

# Add parent directory to path so we can import from live_dashboard
sys.path.append(str(Path(__file__).parent.parent))

from live_dashboard.backend.main import build_snowflake_session

def setup_bronze():
    session = build_snowflake_session()
    
    try:
        print("Creating Database/Schema: PROZORRO.BRONZE")
        session.sql("CREATE SCHEMA IF NOT EXISTS PROZORRO.BRONZE").collect()
        
        print("Creating File Format: DOZORRO_JSON_FORMAT")
        session.sql("""
        CREATE OR REPLACE FILE FORMAT PROZORRO.BRONZE.DOZORRO_JSON_FORMAT
            TYPE = 'JSON'
            COMPRESSION = 'NONE'
            STRIP_OUTER_ARRAY = FALSE
            IGNORE_UTF8_ERRORS = TRUE
        """).collect()
        
        print("Creating External Stage: DOZORRO_GCS_STAGE")
        session.sql("""
        CREATE STAGE IF NOT EXISTS PROZORRO.BRONZE.DOZORRO_GCS_STAGE
            STORAGE_INTEGRATION = dozorro_gcs_int
            URL = 'gcs://dozorro-data-gcs/prozorro-tenders/'
            FILE_FORMAT = PROZORRO.BRONZE.DOZORRO_JSON_FORMAT
        """).collect()
        
        print("Creating Table: PROZORRO.BRONZE.RAW_DOZORRO_TENDERS")
        session.sql("""
        CREATE TABLE IF NOT EXISTS PROZORRO.BRONZE.RAW_DOZORRO_TENDERS (
            RAW_DATA VARIANT,
            FILENAME VARCHAR,
            FILE_ROW_SEQ NUMBER,
            LOAD_TIMESTAMP TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """).collect()
        
        print("Executing COPY INTO from External Stage...")
        # Note: Depending on data volume, this could take a few minutes.
        copy_result = session.sql("""
        COPY INTO PROZORRO.BRONZE.RAW_DOZORRO_TENDERS (RAW_DATA, FILENAME, FILE_ROW_SEQ)
        FROM (
            SELECT $1, metadata$filename, metadata$file_row_number
            FROM @PROZORRO.BRONZE.DOZORRO_GCS_STAGE
        )
        ON_ERROR = 'CONTINUE'
        """).collect()
        
        print("COPY INTO Result:")
        for row in copy_result:
            print(f"  File: {row['file']}, Status: {row['status']}, Rows loaded: {row['rows_loaded']}")
            
        print("\nVerifying row count in RAW_DOZORRO_TENDERS...")
        count_result = session.sql("SELECT COUNT(*) as CNT FROM PROZORRO.BRONZE.RAW_DOZORRO_TENDERS").collect()
        print(f"Total Rows: {count_result[0]['CNT']}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    setup_bronze()
