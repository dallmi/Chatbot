"""
Intranet Analytics Data Ingestion Script

This script loads the fact table and page inventory CSV files into a DuckDB database
and exports them to Parquet format for Power BI reporting.

The fact table columns are cleaned by removing the 'fact_' prefix.

Project structure:
    input/              - Place CSV source files here
    output/db/          - DuckDB database will be created here
    output/parquet/     - Parquet files for Power BI reporting
    notebooks/          - Jupyter notebooks for analysis
    reporting/          - Generated reports and exports
    scripts/            - This script and other utilities
"""

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
    export_parquet: bool = True
) -> None:
    """
    Ingest fact table and page inventory CSVs into DuckDB.

    Args:
        fact_csv_path: Path to the fact table CSV file
        page_inventory_csv_path: Path to the page inventory CSV file
        db_path: Path for the DuckDB database file
        export_parquet: Whether to export tables to Parquet format
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

        fact_count = con.execute("SELECT COUNT(*) FROM fact").fetchone()[0]
        print(f"Loaded {fact_count:,} rows into 'fact' table")

        # Ingest page inventory with cleaned column names
        print(f"Loading page inventory from: {page_inventory_csv_path}")
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

        inventory_count = con.execute("SELECT COUNT(*) FROM page_inventory").fetchone()[0]
        print(f"Loaded {inventory_count:,} rows into 'page_inventory' table")

        # Show schema info
        print("\n--- Fact Table Schema ---")
        schema = con.execute("DESCRIBE fact").fetchall()
        for col in schema:
            print(f"  {col[0]}: {col[1]}")

        print("\n--- Page Inventory Schema ---")
        schema = con.execute("DESCRIBE page_inventory").fetchall()
        for col in schema:
            print(f"  {col[0]}: {col[1]}")

        print(f"\nDatabase saved to: {db_path}")

        # Validate primary keys
        validate_primary_keys(con)

        # Export to Parquet for Power BI
        if export_parquet:
            export_to_parquet(con)

    finally:
        con.close()


def export_to_parquet(con: duckdb.DuckDBPyConnection) -> None:
    """
    Export tables to Parquet format for Power BI reporting.

    Creates:
        - fact.parquet: The fact table
        - page_inventory.parquet: The page inventory dimension
        - analytics_combined.parquet: Denormalized join of fact + page_inventory

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

    # Export combined/denormalized view for simpler Power BI reporting
    combined_parquet = OUTPUT_PARQUET_DIR / "analytics_combined.parquet"
    con.execute(f"""
        COPY (
            SELECT
                f.*,
                p.* EXCLUDE (marketingpageid)
            FROM fact f
            LEFT JOIN page_inventory p ON f.marketingpageid = p.marketingpageid
        ) TO '{combined_parquet}' (FORMAT PARQUET, COMPRESSION SNAPPY)
    """)
    combined_count = con.execute("""
        SELECT COUNT(*) FROM fact f
        LEFT JOIN page_inventory p ON f.marketingpageid = p.marketingpageid
    """).fetchone()[0]
    print(f"Exported combined view ({combined_count:,} rows) to: {combined_parquet}")

    print(f"\nParquet files saved to: {OUTPUT_PARQUET_DIR}")


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
  python ingest_data.py                    # Uses default paths
  python ingest_data.py --fact custom.csv  # Override fact file path

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

    args = parser.parse_args()

    ingest_data(
        args.fact,
        args.inventory,
        args.db,
        export_parquet=not args.no_parquet
    )


if __name__ == "__main__":
    main()
