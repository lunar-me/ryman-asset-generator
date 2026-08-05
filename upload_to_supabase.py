#!/usr/bin/env python3
"""
Upload ryman_assets.csv to Supabase
===================================
Uses the official Supabase Python client.

The script:
  1. Deletes all existing rows in the target table (content reset)
  2. Bulk-inserts the CSV data in batches

Table creation
--------------
If the target table does not exist, the script attempts to create it by
calling the `exec_sql` Postgres function via `client.rpc()`. This function
must be created once in your database (see CREATE_EXEC_SQL_FUNCTION below).
It is a SECURITY DEFINER function that runs arbitrary SQL, so it should only
be created in a trusted environment.

Required environment variables:
    SUPABASE_URL                 e.g. https://xxxxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    service_role key (Project Settings → API)

Optional:
    SUPABASE_TABLE   Target table name (default: ryman_assets)
    CSV_PATH         Path to the CSV file (default: ryman_assets.csv)

Usage:
    export SUPABASE_URL="https://xxxxx.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    python upload_to_supabase.py

Requirements:
    pip install pandas supabase python-dotenv
"""

import math
import os
import sys
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from supabase import create_client, Client


# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE", "ryman_assets")
CSV_PATH = os.getenv("CSV_PATH", "ryman_assets.csv")
BATCH_SIZE = 500  # PostgREST / Supabase friendly batch size

# Optional: load .env file if present
try:
    from dotenv import load_dotenv

    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL") or SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or SUPABASE_SERVICE_ROLE_KEY
    )
    TABLE_NAME = os.getenv("SUPABASE_TABLE", TABLE_NAME)
    CSV_PATH = os.getenv("CSV_PATH", CSV_PATH)
except ImportError:
    pass

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing env vars. Need {SUPABASE_URL} and {SUPABASE_SERVICE_ROLE_KEY}.")

# Narrow types for the type checker (values are guaranteed non-None here)
assert SUPABASE_URL is not None
assert SUPABASE_SERVICE_ROLE_KEY is not None


CREATE_EXEC_SQL_FUNCTION = """
-- Run this ONCE in the Supabase SQL Editor to enable automatic table creation.
-- It creates a SECURITY DEFINER function that runs arbitrary SQL.
CREATE OR REPLACE FUNCTION exec_sql(sql text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    EXECUTE sql;
END;
$$;
"""


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ryman_assets (
    sys_id                  TEXT PRIMARY KEY,
    asset_tag               TEXT,
    serial_number           TEXT,
    ci_name                 TEXT,
    model                   TEXT,
    manufacturer            TEXT,
    asset_type              TEXT,
    category                TEXT,
    subcategory             TEXT,
    install_status          TEXT,
    state                   TEXT,
    lifecycle_stage         TEXT,
    assigned_to             TEXT,
    location                TEXT,
    department              TEXT,
    purchase_date           DATE,
    purchase_cost_nzd       NUMERIC(12, 2),
    po_number               TEXT,
    cost_center             TEXT,
    warranty_expiration     DATE,
    warranty_status         TEXT,
    encryption_status       TEXT,
    os_supported            TEXT,
    is_non_compliant        BOOLEAN,
    last_discovered         TIMESTAMP,
    days_since_last_seen    INTEGER,
    utilisation_score       INTEGER,
    useful_life_years       INTEGER,
    planned_refresh_date    DATE,
    refresh_year            INTEGER,
    remaining_life_years    NUMERIC(6, 2),
    disposal_date           DATE,
    disposal_method         TEXT,
    residual_value_nzd      NUMERIC(12, 2),
    owned_by                TEXT,
    company                 TEXT,
    notes                   TEXT
);

-- Optional: enable Row Level Security later and add policies as needed.
-- ALTER TABLE ryman_assets ENABLE ROW LEVEL SECURITY;
"""


def validate_env() -> None:
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        print("ERROR: Missing required environment variable(s):")
        for m in missing:
            print(f"  - {m}")
        print()
        print("Example:")
        print('  export SUPABASE_URL="https://xxxxx.supabase.co"')
        print('  export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."')
        print()
        print("Find these in: Supabase Dashboard → Project Settings → API")
        sys.exit(1)

    if not Path(CSV_PATH).is_file():
        print(f"ERROR: CSV file not found: {CSV_PATH}")
        print("Generate it first with:  python ryman-asset-generator.py")
        sys.exit(1)


def prepare_dataframe(df: pd.DataFrame) -> list:
    """Clean types and convert to list of JSON-serialisable dicts."""
    # Dates → ISO strings (or None)
    date_cols = [
        "purchase_date",
        "warranty_expiration",
        "planned_refresh_date",
        "disposal_date",
        "last_discovered",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df[col] = df[col].apply(
                lambda x: x.isoformat() if pd.notna(x) else None
            )

    # Booleans
    if "is_non_compliant" in df.columns:
        df["is_non_compliant"] = df["is_non_compliant"].fillna(False).astype(bool)

    # Replace inf/-inf with NaN (JSON cannot serialize them)
    df = df.replace([np.inf, -np.inf], np.nan)

    # Convert every cell to a JSON-safe value:
    #   - NaN → None
    #   - numpy scalars → native Python types
    #   - everything else stays as-is
    df = df.astype(object).where(pd.notnull(df), None)

    # Convert numpy types to native Python types (e.g. np.int64 → int)
    def _to_native(v):
        if v is None:
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            f = float(v)
            return None if math.isnan(f) or math.isinf(f) else f
        if isinstance(v, (np.bool_,)):
            return bool(v)
        return v

    records = df.to_dict(orient="records")
    return [
        {k: _to_native(v) for k, v in record.items()}
        for record in records
    ]


def get_client() -> Client:
    # Values are guaranteed non-None by the module-level check above.
    return create_client(
        cast(str, SUPABASE_URL),
        cast(str, SUPABASE_SERVICE_ROLE_KEY),
    )


def create_table(client: Client, table: str) -> bool:
    """Create the table by calling the exec_sql function via rpc()."""
    sql = CREATE_TABLE_SQL.replace("ryman_assets", table)
    try:
        client.rpc("exec_sql", {"sql": sql}).execute()
        return True
    except Exception as e:
        print(f"  Failed to create table via rpc: {e}")
        return False


def table_exists(client: Client, table: str) -> bool:
    """Best-effort check whether the table is reachable."""
    try:
        client.table(table).select("sys_id").limit(1).execute()
        return True
    except Exception:
        return False


def clear_table(client: Client, table: str) -> None:
    """Delete all rows. Uses a filter that matches every row."""
    print(f"Clearing existing rows in '{table}' ...")
    # PostgREST requires a filter; this matches all non-null primary keys
    client.table(table).delete().neq("sys_id", "").execute()
    print("  Table cleared.")


def insert_batches(client: Client, table: str, rows: list) -> int:
    total = len(rows)
    inserted = 0

    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        client.table(table).insert(batch).execute()
        inserted += len(batch)
        pct = inserted / total * 100
        print(f"  Inserted {inserted:,} / {total:,} rows ({pct:.0f}%)")

    return inserted


def upload() -> None:
    validate_env()

    print(f"Reading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"Rows to upload : {len(df):,}")
    print(f"Target table   : {TABLE_NAME}")

    rows = prepare_dataframe(df)

    print("Connecting to Supabase ...")
    client = get_client()

    if not table_exists(client, TABLE_NAME):
        print(f"Table '{TABLE_NAME}' does not exist. Attempting to create it ...")
        if create_table(client, TABLE_NAME):
            print("  Table created.")
        else:
            print()
            print(f"ERROR: Could not create table '{TABLE_NAME}'.")
            print()
            print("The script uses the 'exec_sql' Postgres function to create the table.")
            print("Run the following SQL ONCE in the Supabase SQL Editor to enable it:")
            print("-" * 60)
            print(CREATE_EXEC_SQL_FUNCTION)
            print("-" * 60)
            print()
            print("Then re-run this script. Alternatively, create the table manually:")
            print("-" * 60)
            print(CREATE_TABLE_SQL.replace("ryman_assets", TABLE_NAME))
            print("-" * 60)
            sys.exit(1)

    # Reset content (closest equivalent to "re-create" with the client library)
    clear_table(client, TABLE_NAME)

    print("Bulk inserting data ...")
    count = insert_batches(client, TABLE_NAME, rows)

    print()
    print("Upload complete.")
    print(f"  Table  : {TABLE_NAME}")
    print(f"  Rows   : {count:,}")
    print()
    print("You can now query it in the Supabase Table Editor or via the API.")


if __name__ == "__main__":
    upload()