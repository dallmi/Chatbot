"""
Aggregation Script for Intranet Analytics

Creates pre-aggregated tables from the detailed fact table for efficient Power BI reporting.
Reads from the detailed DuckDB and outputs to a separate aggregated DuckDB and Parquet files.

Aggregation tables:
    - fact_daily: Daily metrics per page (UV, views, likes, comments)
    - fact_daily_website: Daily metrics per website
    - fact_daily_employee: Daily metrics by employee attributes (division, country, etc.)
    - fact_monthly: Monthly metrics per page

Output:
    - output/db/analytics_agg.duckdb - Aggregated database
    - output/parquet_agg/*.parquet - Parquet files for Power BI
"""

import os
import duckdb
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DB_DIR = PROJECT_ROOT / "output" / "db"
OUTPUT_PARQUET_AGG_DIR = PROJECT_ROOT / "output" / "parquet_agg"
SOURCE_DB_PATH = OUTPUT_DB_DIR / "analytics.duckdb"
AGG_DB_PATH = OUTPUT_DB_DIR / "analytics_agg.duckdb"


def create_aggregations(
    source_db_path: str | Path = SOURCE_DB_PATH,
    agg_db_path: str | Path = AGG_DB_PATH,
    export_parquet: bool = True
) -> None:
    """
    Create aggregated tables from the detailed fact table.

    Args:
        source_db_path: Path to the source detailed DuckDB
        agg_db_path: Path for the aggregated DuckDB
        export_parquet: Whether to export tables to Parquet format
    """
    source_db_path = Path(source_db_path).resolve()
    agg_db_path = Path(agg_db_path).resolve()

    if not source_db_path.exists():
        raise FileNotFoundError(f"Source database not found: {source_db_path}")

    # Ensure output directories exist
    agg_db_path.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PARQUET_AGG_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing aggregated DB to start fresh
    if agg_db_path.exists():
        os.remove(agg_db_path)

    print(f"Source database: {source_db_path}")
    print(f"Aggregated database: {agg_db_path}")

    # Connect to aggregated DB
    con = duckdb.connect(str(agg_db_path))

    try:
        # Attach source database
        con.execute(f"ATTACH '{source_db_path}' AS source (READ_ONLY)")

        # Create fact_daily: Daily metrics per page
        print("\n--- Creating fact_daily ---")
        con.execute("""
            CREATE TABLE fact_daily AS
            SELECT
                d.datekey,
                d.date,
                d.year,
                d.quarter,
                d.month,
                d.month_name,
                d.year_month,
                d.week_number,
                d.year_week,
                d.day_of_week,
                d.day_name,
                d.is_weekend,
                f.marketingpageid,
                p.pagename,
                p.websitename,
                p.theme,
                p.topic,
                p.contenttype,
                p.template,
                COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
                SUM(f.views) AS views,
                SUM(f.visits) AS visits,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) AS likes,
                SUM(f.comments) AS comments,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) + SUM(f.comments) AS engagements,
                SUM(f.durationsum) AS durationsum,
                COUNT(*) AS row_count
            FROM source.fact f
            JOIN source.dim_date d ON f.visitdatekey = d.datekey
            LEFT JOIN source.page_inventory p ON f.marketingpageid = p.marketingpageid
            GROUP BY
                d.datekey, d.date, d.year, d.quarter, d.month, d.month_name,
                d.year_month, d.week_number, d.year_week, d.day_of_week,
                d.day_name, d.is_weekend,
                f.marketingpageid, p.pagename, p.websitename, p.theme,
                p.topic, p.contenttype, p.template
        """)
        count = con.execute("SELECT COUNT(*) FROM fact_daily").fetchone()[0]
        print(f"  Created {count:,} rows")

        # Create fact_daily_website: Daily metrics per website
        print("\n--- Creating fact_daily_website ---")
        con.execute("""
            CREATE TABLE fact_daily_website AS
            SELECT
                d.datekey,
                d.date,
                d.year,
                d.quarter,
                d.month,
                d.month_name,
                d.year_month,
                d.week_number,
                d.year_week,
                d.day_of_week,
                d.day_name,
                d.is_weekend,
                COALESCE(p.websitename, 'Unknown') AS websitename,
                COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
                SUM(f.views) AS views,
                SUM(f.visits) AS visits,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) AS likes,
                SUM(f.comments) AS comments,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) + SUM(f.comments) AS engagements,
                SUM(f.durationsum) AS durationsum,
                COUNT(DISTINCT f.marketingpageid) AS pages_viewed,
                COUNT(*) AS row_count
            FROM source.fact f
            JOIN source.dim_date d ON f.visitdatekey = d.datekey
            LEFT JOIN source.page_inventory p ON f.marketingpageid = p.marketingpageid
            GROUP BY
                d.datekey, d.date, d.year, d.quarter, d.month, d.month_name,
                d.year_month, d.week_number, d.year_week, d.day_of_week,
                d.day_name, d.is_weekend,
                COALESCE(p.websitename, 'Unknown')
        """)
        count = con.execute("SELECT COUNT(*) FROM fact_daily_website").fetchone()[0]
        print(f"  Created {count:,} rows")

        # Create fact_monthly: Monthly metrics per page
        print("\n--- Creating fact_monthly ---")
        con.execute("""
            CREATE TABLE fact_monthly AS
            SELECT
                d.year,
                d.quarter,
                d.month,
                d.month_name,
                d.year_month,
                MIN(d.date) AS month_start,
                f.marketingpageid,
                p.pagename,
                p.websitename,
                p.theme,
                p.topic,
                p.contenttype,
                p.template,
                COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
                SUM(f.views) AS views,
                SUM(f.visits) AS visits,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) AS likes,
                SUM(f.comments) AS comments,
                SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) + SUM(f.comments) AS engagements,
                SUM(f.durationsum) AS durationsum,
                COUNT(DISTINCT d.date) AS days_in_period,
                COUNT(*) AS row_count
            FROM source.fact f
            JOIN source.dim_date d ON f.visitdatekey = d.datekey
            LEFT JOIN source.page_inventory p ON f.marketingpageid = p.marketingpageid
            GROUP BY
                d.year, d.quarter, d.month, d.month_name, d.year_month,
                f.marketingpageid, p.pagename, p.websitename, p.theme,
                p.topic, p.contenttype, p.template
        """)
        count = con.execute("SELECT COUNT(*) FROM fact_monthly").fetchone()[0]
        print(f"  Created {count:,} rows")

        # Check if employee_contact table exists in source
        source_tables = [t[0] for t in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'source'").fetchall()]
        has_employee = 'employee_contact' in source_tables

        if has_employee:
            # Create fact_daily_employee: Daily metrics by website + key employee attributes
            # Grain: Date + Website + Region + Division (compact, for common use cases)
            # For page-level employee analysis, use the detailed database
            print("\n--- Creating fact_daily_employee ---")
            con.execute("""
                CREATE TABLE fact_daily_employee AS
                SELECT
                    d.datekey,
                    d.date,
                    d.year,
                    d.quarter,
                    d.month,
                    d.month_name,
                    d.year_month,
                    d.week_number,
                    d.year_week,
                    d.day_of_week,
                    d.day_name,
                    d.is_weekend,
                    COALESCE(p.websitename, 'Unknown') AS websitename,
                    COALESCE(e.employeeregion, 'Unknown') AS employeeregion,
                    COALESCE(e.employeebusinessdivision, 'Unknown') AS employeebusinessdivision,
                    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
                    SUM(f.views) AS views,
                    SUM(f.visits) AS visits,
                    SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) AS likes,
                    SUM(f.comments) AS comments,
                    SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) + SUM(f.comments) AS engagements,
                    SUM(f.durationsum) AS durationsum,
                    COUNT(DISTINCT f.marketingpageid) AS pages_viewed,
                    COUNT(*) AS row_count
                FROM source.fact f
                JOIN source.dim_date d ON f.visitdatekey = d.datekey
                LEFT JOIN source.page_inventory p ON f.marketingpageid = p.marketingpageid
                LEFT JOIN source.employee_contact e ON f.viewingcontactid = e.contactid
                GROUP BY
                    d.datekey, d.date, d.year, d.quarter, d.month, d.month_name,
                    d.year_month, d.week_number, d.year_week, d.day_of_week,
                    d.day_name, d.is_weekend,
                    COALESCE(p.websitename, 'Unknown'),
                    COALESCE(e.employeeregion, 'Unknown'),
                    COALESCE(e.employeebusinessdivision, 'Unknown')
            """)
            count = con.execute("SELECT COUNT(*) FROM fact_daily_employee").fetchone()[0]
            print(f"  Created {count:,} rows")

        # Copy dim_date for reference
        print("\n--- Copying dim_date ---")
        con.execute("CREATE TABLE dim_date AS SELECT * FROM source.dim_date")
        count = con.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
        print(f"  Copied {count:,} rows")

        # Copy page_inventory for reference
        print("\n--- Copying page_inventory ---")
        con.execute("CREATE TABLE page_inventory AS SELECT * FROM source.page_inventory")
        count = con.execute("SELECT COUNT(*) FROM page_inventory").fetchone()[0]
        print(f"  Copied {count:,} rows")

        # Copy employee_contact for reference (if exists)
        if has_employee:
            print("\n--- Copying employee_contact ---")
            con.execute("CREATE TABLE employee_contact AS SELECT * FROM source.employee_contact")
            count = con.execute("SELECT COUNT(*) FROM employee_contact").fetchone()[0]
            print(f"  Copied {count:,} rows")

        # Detach source
        con.execute("DETACH source")

        # Optimize
        print("\n--- Optimizing Database ---")
        con.execute("CHECKPOINT")
        con.execute("VACUUM")

        db_size_mb = os.path.getsize(agg_db_path) / (1024 * 1024)
        print(f"Aggregated database size: {db_size_mb:.1f} MB")

        # Export to Parquet
        if export_parquet:
            export_aggregations_to_parquet(con)

    finally:
        con.close()


def export_aggregations_to_parquet(con: duckdb.DuckDBPyConnection) -> None:
    """Export aggregated tables to Parquet format."""
    print("\n--- Exporting Aggregations to Parquet ---")

    # Get all tables in the database
    all_tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]

    # Export each table
    for table in all_tables:
        parquet_path = OUTPUT_PARQUET_AGG_DIR / f"{table}.parquet"
        con.execute(f"COPY {table} TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
        size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
        print(f"  {table}.parquet: {size_mb:.1f} MB")

    print(f"\nParquet files saved to: {OUTPUT_PARQUET_AGG_DIR}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create aggregated tables from detailed analytics data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Example usage:
  python create_aggregations.py                # Create aggregations
  python create_aggregations.py --no-parquet   # Skip Parquet export

Input:
  Source database:    {SOURCE_DB_PATH}

Output:
  Aggregated DB:      {AGG_DB_PATH}
  Parquet files:      {OUTPUT_PARQUET_AGG_DIR}
        """
    )
    parser.add_argument(
        "--source-db",
        default=str(SOURCE_DB_PATH),
        help=f"Source DuckDB path (default: {SOURCE_DB_PATH})"
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Skip Parquet export"
    )

    args = parser.parse_args()

    create_aggregations(
        source_db_path=args.source_db,
        export_parquet=not args.no_parquet
    )


if __name__ == "__main__":
    main()
