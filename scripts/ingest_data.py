"""
Intranet Analytics Data Ingestion Script

This script loads the fact table and page inventory CSV files into a DuckDB database
and exports them to Parquet format for Power BI reporting.

Features:
- Incremental loading (default): Retains historical data beyond the source's rolling window
  - Fact table: Keeps data outside CSV date range, replaces overlapping dates
  - Page inventory: Upserts based on marketingpageid
- Full refresh mode (--full-refresh): Replaces all data

The fact table columns are cleaned by removing the 'fact_' prefix.

Project structure:
    input/              - Place CSV source files here
    output/db/          - DuckDB database will be created here
    output/parquet/     - Parquet files for Power BI reporting
    notebooks/          - Jupyter notebooks for analysis
    reporting/          - Generated reports and exports
    scripts/            - This script and other utilities
"""

import os
import duckdb
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DB_DIR = PROJECT_ROOT / "output" / "db"
OUTPUT_PARQUET_DIR = PROJECT_ROOT / "output" / "parquet"
DEFAULT_DB_PATH = OUTPUT_DB_DIR / "analytics.duckdb"
DEFAULT_FACT_PATH = INPUT_DIR / "fact.csv"
DEFAULT_INVENTORY_PATH = INPUT_DIR / "page_inventory.csv"


def ingest_data(
    fact_csv_path: str | Path,
    page_inventory_csv_path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    export_parquet: bool = True,
    full_refresh: bool = False
) -> None:
    """
    Ingest fact table and page inventory CSVs into DuckDB.

    By default, uses incremental loading:
    - Fact table: Keeps historical data outside the CSV date range, replaces overlapping dates
    - Page inventory: Upserts based on marketingpageid (updates existing, adds new, keeps historical)

    Use full_refresh=True to replace all data (original behavior).

    Args:
        fact_csv_path: Path to the fact table CSV file
        page_inventory_csv_path: Path to the page inventory CSV file
        db_path: Path for the DuckDB database file
        export_parquet: Whether to export tables to Parquet format
        full_refresh: If True, replace all data; if False, use incremental merge
    """
    # Ensure paths are absolute
    fact_csv_path = Path(fact_csv_path).resolve()
    page_inventory_csv_path = Path(page_inventory_csv_path).resolve()
    db_path = Path(db_path).resolve()

    # Ensure output directories exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to DuckDB (creates file if it doesn't exist)
    con = duckdb.connect(str(db_path))

    try:
        # Ingest fact table
        print(f"Loading fact table from: {fact_csv_path}")

        if full_refresh:
            # Full refresh: replace all data
            print("  Mode: FULL REFRESH (replacing all data)")
            con.execute(f"""
                CREATE OR REPLACE TABLE fact AS
                SELECT
                    fact_visitdatekey AS visitdatekey,
                    fact_referrerapplicationid AS referrerapplicationid,
                    fact_marketingPageId AS marketingpageid,
                    fact_views AS views,
                    fact_viewingcontactid AS viewingcontactid,
                    fact_flag AS flag,
                    fact_visits AS visits,
                    fact_durationsum AS durationsum,
                    fact_durationavg AS durationavg,
                    fact_comments AS comments,
                    fact_marketingPageIdliked AS marketingpageidliked
                FROM read_csv('{fact_csv_path}', auto_detect=true)
            """)
        else:
            # Incremental: keep historical, replace overlapping date range
            print("  Mode: INCREMENTAL (keeping historical data)")

            # Create table if it doesn't exist
            con.execute("""
                CREATE TABLE IF NOT EXISTS fact (
                    visitdatekey BIGINT,
                    referrerapplicationid VARCHAR,
                    marketingpageid VARCHAR,
                    views BIGINT,
                    viewingcontactid VARCHAR,
                    flag VARCHAR,
                    visits BIGINT,
                    durationsum DOUBLE,
                    durationavg DOUBLE,
                    comments BIGINT,
                    marketingpageidliked VARCHAR
                )
            """)

            # Load CSV into staging table
            con.execute(f"""
                CREATE OR REPLACE TEMP TABLE fact_staging AS
                SELECT
                    fact_visitdatekey AS visitdatekey,
                    fact_referrerapplicationid AS referrerapplicationid,
                    fact_marketingPageId AS marketingpageid,
                    fact_views AS views,
                    fact_viewingcontactid AS viewingcontactid,
                    fact_flag AS flag,
                    fact_visits AS visits,
                    fact_durationsum AS durationsum,
                    fact_durationavg AS durationavg,
                    fact_comments AS comments,
                    fact_marketingPageIdliked AS marketingpageidliked
                FROM read_csv('{fact_csv_path}', auto_detect=true)
            """)

            # Get date range from staging
            date_range = con.execute("""
                SELECT MIN(visitdatekey) as min_date, MAX(visitdatekey) as max_date
                FROM fact_staging
            """).fetchone()
            min_date, max_date = date_range
            print(f"  CSV date range: {min_date} to {max_date}")

            # Count rows before
            before_count = con.execute("SELECT COUNT(*) FROM fact").fetchone()[0]

            # Delete overlapping date range
            deleted = con.execute(f"""
                DELETE FROM fact
                WHERE visitdatekey >= {min_date} AND visitdatekey <= {max_date}
            """).fetchone()

            # Insert all from staging
            con.execute("INSERT INTO fact SELECT * FROM fact_staging")

            # Drop staging table
            con.execute("DROP TABLE fact_staging")

            staging_count = con.execute(f"SELECT COUNT(*) FROM read_csv('{fact_csv_path}', auto_detect=true)").fetchone()[0]
            print(f"  Rows before: {before_count:,}, CSV rows: {staging_count:,}")

        fact_count = con.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
        print(f"  Total rows in 'fact' table: {fact_count:,}")

        # Ingest page inventory with cleaned column names
        print(f"\nLoading page inventory from: {page_inventory_csv_path}")

        if full_refresh:
            # Full refresh: replace all data
            print("  Mode: FULL REFRESH (replacing all data)")
            con.execute(f"""
                CREATE OR REPLACE TABLE page_inventory AS
                SELECT
                    websitename,
                    websiteurl,
                    owningbusinessunit,
                    pagename,
                    fullpageurl,
                    sourcesystempageid,
                    marketingpageid,
                    theme,
                    topic,
                    pageurl,
                    exclude,
                    "Site name" AS sitename,
                    "theme - Copy" AS theme_normalized,
                    "topic - Copy" AS topic_normalized,
                    template,
                    contentType AS contenttype,
                    pageLanguage AS pagelanguage,
                    newsCategory AS newscategory,
                    targetRegion AS targetregion,
                    targetOrganization AS targetorganization,
                    cnt
                FROM read_csv('{page_inventory_csv_path}', auto_detect=true)
                WHERE marketingpageid != 'Unknown'
            """)
        else:
            # Incremental: upsert based on marketingpageid
            print("  Mode: INCREMENTAL (upsert by marketingpageid)")

            # Create table if it doesn't exist
            con.execute("""
                CREATE TABLE IF NOT EXISTS page_inventory (
                    websitename VARCHAR,
                    websiteurl VARCHAR,
                    owningbusinessunit VARCHAR,
                    pagename VARCHAR,
                    fullpageurl VARCHAR,
                    sourcesystempageid VARCHAR,
                    marketingpageid VARCHAR,
                    theme VARCHAR,
                    topic VARCHAR,
                    pageurl VARCHAR,
                    exclude VARCHAR,
                    sitename VARCHAR,
                    theme_normalized VARCHAR,
                    topic_normalized VARCHAR,
                    template VARCHAR,
                    contenttype VARCHAR,
                    pagelanguage VARCHAR,
                    newscategory VARCHAR,
                    targetregion VARCHAR,
                    targetorganization VARCHAR,
                    cnt BIGINT
                )
            """)

            # Load CSV into staging table
            con.execute(f"""
                CREATE OR REPLACE TEMP TABLE page_inventory_staging AS
                SELECT
                    websitename,
                    websiteurl,
                    owningbusinessunit,
                    pagename,
                    fullpageurl,
                    sourcesystempageid,
                    marketingpageid,
                    theme,
                    topic,
                    pageurl,
                    exclude,
                    "Site name" AS sitename,
                    "theme - Copy" AS theme_normalized,
                    "topic - Copy" AS topic_normalized,
                    template,
                    contentType AS contenttype,
                    pageLanguage AS pagelanguage,
                    newsCategory AS newscategory,
                    targetRegion AS targetregion,
                    targetOrganization AS targetorganization,
                    cnt
                FROM read_csv('{page_inventory_csv_path}', auto_detect=true)
                WHERE marketingpageid != 'Unknown'
            """)

            # Count rows before
            before_count = con.execute("SELECT COUNT(*) FROM page_inventory").fetchone()[0]
            staging_count = con.execute("SELECT COUNT(*) FROM page_inventory_staging").fetchone()[0]

            # Delete pages that exist in staging (will be re-inserted with fresh values)
            con.execute("""
                DELETE FROM page_inventory
                WHERE marketingpageid IN (SELECT marketingpageid FROM page_inventory_staging)
            """)

            # Insert all from staging
            con.execute("INSERT INTO page_inventory SELECT * FROM page_inventory_staging")

            # Drop staging table
            con.execute("DROP TABLE page_inventory_staging")

            print(f"  Rows before: {before_count:,}, CSV rows: {staging_count:,}")

        inventory_count = con.execute("SELECT COUNT(*) FROM page_inventory").fetchone()[0]
        print(f"  Total rows in 'page_inventory' table: {inventory_count:,}")

        # Show schema info
        print("\n--- Fact Table Schema ---")
        schema = con.execute("DESCRIBE fact").fetchall()
        for col in schema:
            print(f"  {col[0]}: {col[1]}")

        print("\n--- Page Inventory Schema ---")
        schema = con.execute("DESCRIBE page_inventory").fetchall()
        for col in schema:
            print(f"  {col[0]}: {col[1]}")

        # Create date dimension table
        create_date_dimension(con)

        # Optimize database size
        print("\n--- Optimizing Database ---")
        con.execute("CHECKPOINT")
        con.execute("VACUUM")

        # Get database size
        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"Database size: {db_size_mb:.1f} MB")
        print(f"Database saved to: {db_path}")

        # Validate primary keys
        validate_primary_keys(con)

        # Export to Parquet for Power BI
        if export_parquet:
            export_to_parquet(con)

    finally:
        con.close()


def create_date_dimension(con: duckdb.DuckDBPyConnection) -> None:
    """
    Create a date dimension table with dates from 2022-01-01 to 2040-12-31.

    The table includes various date attributes useful for analytics:
    - datekey: BIGINT in YYYYMMDD format (join key to fact.visitdatekey)
    - Various date parts: year, quarter, month, week, day
    - Day/month names
    - Flags for weekends, month/quarter/year boundaries

    Args:
        con: Active DuckDB connection
    """
    print("\n--- Creating Date Dimension ---")

    con.execute("""
        CREATE OR REPLACE TABLE dim_date AS
        WITH date_range AS (
            SELECT UNNEST(generate_series(DATE '2022-01-01', DATE '2040-12-31', INTERVAL 1 DAY)) AS date
        )
        SELECT
            -- Primary key (BIGINT in YYYYMMDD format for joining with fact.visitdatekey)
            CAST(STRFTIME(date, '%Y%m%d') AS BIGINT) AS datekey,

            -- Date value
            date,

            -- Year
            YEAR(date) AS year,

            -- Quarter
            QUARTER(date) AS quarter,
            CONCAT('Q', QUARTER(date)) AS quarter_name,
            CONCAT('Q', QUARTER(date), ' ', YEAR(date)) AS year_quarter,

            -- Month
            MONTH(date) AS month,
            STRFTIME(date, '%B') AS month_name,
            STRFTIME(date, '%b') AS month_short,
            CONCAT(YEAR(date), '-', LPAD(CAST(MONTH(date) AS VARCHAR), 2, '0')) AS year_month,

            -- Week (ISO week number)
            WEEKOFYEAR(date) AS week_number,
            CONCAT(ISOYEAR(date), '-W', LPAD(CAST(WEEKOFYEAR(date) AS VARCHAR), 2, '0')) AS year_week,

            -- Day
            DAY(date) AS day_of_month,
            DAYOFYEAR(date) AS day_of_year,
            ISODOW(date) AS day_of_week,  -- 1=Monday, 7=Sunday
            STRFTIME(date, '%A') AS day_name,
            STRFTIME(date, '%a') AS day_short,

            -- Flags
            CASE WHEN ISODOW(date) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
            CASE WHEN DAY(date) = 1 THEN TRUE ELSE FALSE END AS is_month_start,
            CASE WHEN date = LAST_DAY(date) THEN TRUE ELSE FALSE END AS is_month_end,
            CASE WHEN MONTH(date) IN (1, 4, 7, 10) AND DAY(date) = 1 THEN TRUE ELSE FALSE END AS is_quarter_start,
            CASE WHEN MONTH(date) IN (3, 6, 9, 12) AND date = LAST_DAY(date) THEN TRUE ELSE FALSE END AS is_quarter_end,
            CASE WHEN MONTH(date) = 1 AND DAY(date) = 1 THEN TRUE ELSE FALSE END AS is_year_start,
            CASE WHEN MONTH(date) = 12 AND DAY(date) = 31 THEN TRUE ELSE FALSE END AS is_year_end

        FROM date_range
        ORDER BY date
    """)

    date_count = con.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
    min_date = con.execute("SELECT MIN(date) FROM dim_date").fetchone()[0]
    max_date = con.execute("SELECT MAX(date) FROM dim_date").fetchone()[0]
    print(f"Created 'dim_date' table with {date_count:,} rows ({min_date} to {max_date})")

    # Show schema
    print("\n--- Date Dimension Schema ---")
    schema = con.execute("DESCRIBE dim_date").fetchall()
    for col in schema:
        print(f"  {col[0]}: {col[1]}")


def export_to_parquet(con: duckdb.DuckDBPyConnection) -> None:
    """
    Export tables to Parquet format for Power BI reporting.

    Creates a star schema with:
        - fact.parquet: The fact table
        - page_inventory.parquet: The page inventory dimension
        - dim_date.parquet: The date dimension table

    In Power BI, join:
        - fact.marketingpageid -> page_inventory.marketingpageid
        - fact.visitdatekey -> dim_date.datekey

    Args:
        con: Active DuckDB connection with tables loaded
    """
    print("\n--- Exporting to Parquet ---")

    # Export fact table
    fact_parquet = OUTPUT_PARQUET_DIR / "fact.parquet"
    con.execute(f"COPY fact TO '{fact_parquet}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
    print(f"Exported fact table to: {fact_parquet}")

    # Export page inventory
    inventory_parquet = OUTPUT_PARQUET_DIR / "page_inventory.parquet"
    con.execute(f"COPY page_inventory TO '{inventory_parquet}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
    print(f"Exported page inventory to: {inventory_parquet}")

    # Export date dimension
    date_parquet = OUTPUT_PARQUET_DIR / "dim_date.parquet"
    con.execute(f"COPY dim_date TO '{date_parquet}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
    print(f"Exported date dimension to: {date_parquet}")

    print(f"\nParquet files saved to: {OUTPUT_PARQUET_DIR}")
    print("\nNote: Use star schema in Power BI - join fact to page_inventory and dim_date")


def validate_primary_keys(con: duckdb.DuckDBPyConnection) -> bool:
    """
    Validate primary keys in both tables and report any duplicates.

    Checks:
        - page_inventory: marketingpageid should be unique
        - fact: (visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid)
                should be unique

    Args:
        con: Active DuckDB connection with tables loaded

    Returns:
        True if all primary keys are valid, False if duplicates found
    """
    print("\n--- Validating Primary Keys ---")
    all_valid = True

    # Check page_inventory primary key (marketingpageid)
    inventory_dupes = con.execute("""
        SELECT marketingpageid, COUNT(*) as cnt
        FROM page_inventory
        GROUP BY marketingpageid
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()

    if inventory_dupes:
        all_valid = False
        print(f"\n  WARNING: page_inventory has duplicate marketingpageid values:")
        for row in inventory_dupes:
            print(f"    marketingpageid='{row[0]}' appears {row[1]} times")
    else:
        unique_pages = con.execute("SELECT COUNT(DISTINCT marketingpageid) FROM page_inventory").fetchone()[0]
        print(f"  page_inventory: OK - {unique_pages:,} unique marketingpageid values")

    # Check fact table composite primary key
    # First, check which key combinations have duplicates
    fact_dupes = con.execute("""
        SELECT
            visitdatekey,
            marketingpageid,
            viewingcontactid,
            referrerapplicationid,
            COUNT(*) as cnt
        FROM fact
        GROUP BY visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()

    if fact_dupes:
        all_valid = False
        total_dupes = con.execute("""
            SELECT COUNT(*) FROM (
                SELECT visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid
                FROM fact
                GROUP BY visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        print(f"\n  WARNING: fact table has {total_dupes:,} duplicate composite keys")
        print("  (visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid)")
        print("  Sample duplicates:")
        for row in fact_dupes[:5]:
            print(f"    date={row[0]}, page={row[1]}, contact={row[2]}, referrer={row[3]} -> {row[4]} rows")
    else:
        unique_keys = con.execute("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT visitdatekey, marketingpageid, viewingcontactid, referrerapplicationid
                FROM fact
            )
        """).fetchone()[0]
        total_rows = con.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
        print(f"  fact: OK - {unique_keys:,} unique composite keys (matches {total_rows:,} total rows)")

    # Additional analysis: check for orphaned fact records (no matching page_inventory)
    orphaned = con.execute("""
        SELECT COUNT(DISTINCT f.marketingpageid) as orphaned_pages,
               COUNT(*) as orphaned_rows
        FROM fact f
        LEFT JOIN page_inventory p ON f.marketingpageid = p.marketingpageid
        WHERE p.marketingpageid IS NULL
    """).fetchone()

    if orphaned[0] > 0:
        print(f"\n  INFO: {orphaned[1]:,} fact rows ({orphaned[0]:,} unique pages) have no matching page_inventory record")

    if all_valid:
        print("\n  All primary key validations passed!")
    else:
        print("\n  Some validations failed - review warnings above")

    return all_valid


def main():
    """Main entry point with example usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest analytics CSV files into DuckDB and export to Parquet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Example usage:
  python ingest_data.py                    # Incremental load (default)
  python ingest_data.py --full-refresh     # Replace all data
  python ingest_data.py --fact custom.csv  # Override fact file path

Incremental mode (default):
  - Fact table: Keeps historical data, replaces dates within CSV range
  - Page inventory: Updates existing pages, adds new, keeps historical

Full refresh mode (--full-refresh):
  - Replaces all data with CSV contents

Default paths:
  Fact CSV:          {DEFAULT_FACT_PATH}
  Page inventory:    {DEFAULT_INVENTORY_PATH}
  Output database:   {DEFAULT_DB_PATH}
  Output parquet:    {OUTPUT_PARQUET_DIR}
        """
    )
    parser.add_argument(
        "--fact",
        default=str(DEFAULT_FACT_PATH),
        help=f"Path to fact table CSV file (default: {DEFAULT_FACT_PATH})"
    )
    parser.add_argument(
        "--inventory",
        default=str(DEFAULT_INVENTORY_PATH),
        help=f"Path to page inventory CSV file (default: {DEFAULT_INVENTORY_PATH})"
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"Output DuckDB database path (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Skip Parquet export"
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Replace all data instead of incremental merge (default: incremental)"
    )

    args = parser.parse_args()

    ingest_data(
        args.fact,
        args.inventory,
        args.db,
        export_parquet=not args.no_parquet,
        full_refresh=args.full_refresh
    )


if __name__ == "__main__":
    main()
