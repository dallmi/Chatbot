# Intranet Analytics Data Pipeline

A Python-based data pipeline for analyzing Intranet Analytics data using DuckDB, with Jupyter notebooks for analysis and Parquet export for Power BI reporting.

## Project Structure

```
Chatbot/
├── input/                  # Place your CSV source files here
│   ├── .gitkeep
│   ├── fact.csv           # Fact table (you provide this)
│   ├── page_inventory.csv # Page inventory (you provide this)
│   └── employee_contact.csv # Employee dimension (optional)
├── output/
│   ├── db/                # DuckDB database files (auto-generated)
│   │   ├── analytics.duckdb      # Detailed data (large)
│   │   └── analytics_agg.duckdb  # Aggregated data (small)
│   ├── parquet/           # Detailed Parquet files
│   │   ├── fact.parquet
│   │   ├── page_inventory.parquet
│   │   ├── employee_contact.parquet  # If employee_contact.csv provided
│   │   └── dim_date.parquet
│   └── parquet_agg/       # Aggregated Parquet for Power BI (recommended)
│       ├── fact_daily.parquet
│       ├── fact_daily_website.parquet
│       ├── fact_daily_employee.parquet  # If employee_contact.csv provided
│       ├── fact_monthly.parquet
│       ├── dim_date.parquet
│       ├── page_inventory.parquet
│       └── employee_contact.parquet  # If employee_contact.csv provided
├── notebooks/
│   ├── analysis.ipynb     # Detailed data analysis
│   └── analysis_agg.ipynb # Aggregated data analysis
├── scripts/
│   ├── ingest_data.py     # Data ingestion script
│   └── create_aggregations.py  # Aggregation script
├── reporting/             # For exported reports (CSV, Excel, PDF)
├── config/                # Configuration files (if needed)
├── requirements.txt       # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.9+
- pip

## Setup

### 1. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## Input Files

Place your CSV files in the `input/` folder:

### fact.csv

The fact table containing page view/visit data. Expected columns:

| Column | Description |
|--------|-------------|
| fact_visitdatekey | Date key (YYYYMMDD format) |
| fact_referrerapplicationid | Referrer application ID |
| fact_marketingPageId | Page ID (join key to page_inventory) |
| fact_views | Number of views |
| fact_viewingcontactid | Visitor contact ID (used for UV calculation) |
| fact_flag | Flag field |
| fact_visits | Number of visits |
| fact_durationsum | Total duration |
| fact_durationavg | Average duration |
| fact_comments | Number of comments |
| fact_marketingPageIdliked | PageID that was liked (presence indicates a like event) |

### page_inventory.csv

The page inventory/dimension table. Expected columns:

| Column | Description |
|--------|-------------|
| websitename | Website name |
| websiteurl | Website URL |
| owningbusinessunit | Owning business unit |
| pagename | Page name |
| fullpageurl | Full page URL |
| sourcesystempageid | Source system page ID |
| marketingpageid | Marketing page ID (primary key, join key to fact) |
| theme | Page theme |
| topic | Page topic |
| pageurl | Page URL |
| exclude | Exclude flag |
| Site name | Site name |
| theme - Copy | Theme (normalized format) |
| topic - Copy | Topic (normalized format) |
| template | Page template |
| contentType | Content type |
| pageLanguage | Page language |
| newsCategory | News category |
| targetRegion | Target region |
| targetOrganization | Target organization |
| cnt | Count |

### employee_contact.csv (Optional)

The employee contact dimension table for analyzing by employee attributes. Expected columns:

| Column | Description |
|--------|-------------|
| contactId | Contact ID (primary key, join key to fact.viewingcontactid) |
| employeebusinessdivision | Business division |
| employeeCategory | Employee category |
| employeeClass | Employee class |
| employeeCluster | Employee cluster |
| employeeFamily | Employee family |
| employeeFunction | Employee function |
| employeeGCRSCountry | GCRS country |
| employeeRank | Employee rank |
| employeeregion | Employee region |
| employeeRole | Employee role |
| employeeWorkCountry | Work country |
| OU_LVL_1 | Organizational unit level 1 |
| OU_LVL_2 | Organizational unit level 2 |
| OU_LVL_3 | Organizational unit level 3 |
| OU_LVL_4 | Organizational unit level 4 |
| OU_LVL_5 | Organizational unit level 5 |

### dim_date (Auto-generated)

A date dimension table is automatically generated during ingestion (2022-01-01 to 2040-12-31). Join to fact table via `datekey = visitdatekey`.

| Column | Description |
|--------|-------------|
| datekey | BIGINT in YYYYMMDD format (join key to fact.visitdatekey) |
| date | DATE value |
| year | Year (2022-2040) |
| quarter | Quarter number (1-4) |
| quarter_name | Quarter name (Q1, Q2, Q3, Q4) |
| year_quarter | Year and quarter (e.g., "Q1 2025") |
| month | Month number (1-12) |
| month_name | Full month name (January, February, etc.) |
| month_short | Abbreviated month name (Jan, Feb, etc.) |
| year_month | Year-month string (e.g., "2025-01") |
| week_number | ISO week number (1-53) |
| year_week | Year-week string (e.g., "2025-W01") |
| day_of_month | Day of month (1-31) |
| day_of_year | Day of year (1-366) |
| day_of_week | ISO day of week (1=Monday, 7=Sunday) |
| day_name | Full day name (Monday, Tuesday, etc.) |
| day_short | Abbreviated day name (Mon, Tue, etc.) |
| is_weekend | TRUE if Saturday or Sunday |
| is_month_start | TRUE if first day of month |
| is_month_end | TRUE if last day of month |
| is_quarter_start | TRUE if first day of quarter |
| is_quarter_end | TRUE if last day of quarter |
| is_year_start | TRUE if January 1st |
| is_year_end | TRUE if December 31st |

## Running the Pipeline

### Step 1: Ingest Data

Run the ingestion script to load CSVs into DuckDB and export to Parquet:

```bash
python scripts/ingest_data.py
```

This uses the default paths:
- `input/fact.csv`
- `input/page_inventory.csv`

**Incremental Loading (default):**

By default, the script uses incremental loading to retain historical data:
- **Fact table**: Keeps data outside the CSV date range, replaces overlapping dates
- **Page inventory**: Updates existing pages, adds new ones, keeps historical pages

This is useful when your source exports a rolling 90-day window - historical data beyond that window is preserved in DuckDB.

**Options:**

| Flag | Description |
|------|-------------|
| `--fact` | Path to fact table CSV (default: `input/fact.csv`) |
| `--inventory` | Path to page inventory CSV (default: `input/page_inventory.csv`) |
| `--db` | Custom DuckDB database path (optional) |
| `--no-parquet` | Skip Parquet export (optional) |
| `--full-refresh` | Replace all data instead of incremental merge |

**Output:**
- Creates `output/db/analytics.duckdb` - DuckDB database
- Creates `output/parquet/*.parquet` - Parquet files for Power BI
- Validates primary keys and reports any issues

### Step 1b: Create Aggregations (Recommended for Power BI)

The detailed fact table can be large (1GB+ for 90 days). For Power BI reporting, create pre-aggregated tables:

```bash
python scripts/create_aggregations.py
```

This reads from the detailed database and creates:
- `output/db/analytics_agg.duckdb` - Aggregated database (~50MB)
- `output/parquet_agg/*.parquet` - Aggregated Parquet files (~5MB total)

**Aggregation tables:**

| Table | Grain | Description |
|-------|-------|-------------|
| `fact_daily` | Date + Page | Daily metrics per page (UV, views, likes, etc.) |
| `fact_daily_website` | Date + Website | Daily metrics per website |
| `fact_daily_employee` | Date + Page + Employee Attributes | Daily metrics by page and employee attributes - enables UV by region/division filtered by website, page URL, or date range (if employee_contact.csv provided) |
| `fact_monthly` | Month + Page | Monthly metrics per page |

**Note:** UV in aggregated tables is pre-calculated at the grain level. For true cross-period UV (e.g., monthly UV for a website), use the detailed database.

### Step 2: Analyze Data in Jupyter

Start Jupyter and open an analysis notebook:

```bash
# Detailed data analysis (large dataset)
jupyter notebook notebooks/analysis.ipynb

# Aggregated data analysis (faster, smaller)
jupyter notebook notebooks/analysis_agg.ipynb
```

Or using JupyterLab:

```bash
jupyter lab notebooks/
```

### Step 3: Configure Filters (Optional)

In the notebook, modify the filter variables in the **Filter Configuration** section:

```python
# Website filter (case-insensitive contains)
FILTER_WEBSITE = "intranet"  # or None for all

# Date range filter (YYYYMMDD format)
FILTER_DATE_FROM = "20251001"
FILTER_DATE_TO = "20251031"

# URL filter (case-insensitive contains)
FILTER_PAGEURL = "/news/"  # or None for all
```

Then run all cells to see filtered results.

### Step 4: Use Parquet Files in Power BI

**Recommended: Use aggregated files** from `output/parquet_agg/` (much smaller, faster):

1. Open Power BI Desktop
2. Get Data > Parquet
3. Import files from `output/parquet_agg/`:
   - `fact_daily.parquet` or `fact_daily_website.parquet` - Pre-aggregated metrics
   - `fact_monthly.parquet` - Monthly aggregates
   - `page_inventory.parquet` - Page dimension
   - `dim_date.parquet` - Date dimension
4. Create relationships as needed (date fields are already included in aggregates)

**Alternative: Use detailed files** from `output/parquet/` (large, row-level detail):

1. Import from `output/parquet/`:
   - `fact.parquet` - Detailed fact table (can be 300MB+)
   - `page_inventory.parquet` - Page dimension
   - `dim_date.parquet` - Date dimension
2. Create relationships (star schema):
   - `fact.marketingpageid` → `page_inventory.marketingpageid`
   - `fact.visitdatekey` → `dim_date.datekey`

## Notebook Analysis Sections

The Jupyter notebook includes:

| Section | Description |
|---------|-------------|
| 1. Data Overview | Summary statistics |
| 2. UV Analysis | Daily, weekly, monthly, quarterly unique visitors |
| 3. Engagement Analysis | Likes + comments trends and top pages |
| 4. Top Pages | By views and unique visitors |
| 5. Referrer Analysis | Traffic by referrer application |
| 6. Overall Metrics | Engagement rates, views per visitor |
| 7. Quick Filters | Helper cells to search websites/URLs |
| 8. Visualizations | Charts for rows per website, UV trends, top pages, engagement |

## Key Metrics

- **UV (Unique Visitors)**: `COUNT(DISTINCT viewingcontactid)` - calculated at query time, not pre-aggregated
- **Likes**: `COUNT` of rows where `marketingpageidliked` is not null/empty (the field contains the PageID that was liked)
- **Engagement**: `likes + comments`
- **Engagement Rate**: `(likes + comments) / views * 100`

## Troubleshooting

### "Database not found" error in notebook

Make sure you've run the ingestion script first (Step 1).

### Primary key validation warnings

The ingestion script validates:
- `marketingpageid` uniqueness in page_inventory (rows with "Unknown" are excluded)
- Composite key uniqueness in fact table

Warnings indicate duplicate keys that may affect join accuracy.

### Memory issues with large datasets

DuckDB handles large datasets efficiently, but for very large files:
- Ensure sufficient disk space for the database
- Consider filtering data during ingestion

## License

Internal use only.
