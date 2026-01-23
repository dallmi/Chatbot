# Intranet Analytics Data Schema

This document describes the data schema for the Intranet Analytics database. Use this reference to understand the available tables, columns, and their meanings for querying and analysis.

---

## Tables Overview

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `fact` | Main fact table containing page view events | Composite: `visitdatekey` + `marketingpageid` + `viewingcontactid` |
| `page_inventory` | Dimension table with page metadata | `marketingpageid` |
| `employee_contact` | Dimension table with employee attributes | `contactid` |
| `dim_date` | Date dimension for time-based analysis | `datekey` |

---

## Table: `fact`

The main fact table containing individual page view events. Each row represents a visit to a page by a specific user on a specific date.

| Column | Type | Description | Sample Values |
|--------|------|-------------|---------------|
| `visitdatekey` | BIGINT | Date of the visit in YYYYMMDD format. Join to `dim_date.datekey` | `20251015`, `20251101` |
| `referrerapplicationid` | VARCHAR | Source channel that referred the visitor (how did they arrive at the page) | `Intranet`, `Email`, `Other` |
| `marketingpageid` | VARCHAR | Unique identifier for the page. Join to `page_inventory.marketingpageid` | GUID format |
| `views` | BIGINT | Number of page views in this visit | `1`, `2`, `5` |
| `viewingcontactid` | VARCHAR | Unique identifier for the visitor/employee. Join to `employee_contact.contactid` | GUID format |
| `flag` | VARCHAR | Status flag (usage unclear) | - |
| `visits` | BIGINT | Number of visits/sessions | `1`, `2` |
| `durationsum` | DOUBLE | Total page load time (seconds) | `45.5`, `120.0` |
| `durationavg` | DOUBLE | Average page load time (seconds) | `45.5`, `60.0` |
| `comments` | BIGINT | Number of comments made | `0`, `1`, `3` |
| `marketingpageidliked` | VARCHAR | Contains the page ID if the user liked the page; empty/null if not liked | GUID or empty |

### Key Metrics from fact table

- **Unique Visitors (UV):** `COUNT(DISTINCT viewingcontactid)`
- **Total Views:** `SUM(views)`
- **Total Visits:** `SUM(visits)`
- **Likes:** `COUNT(*) WHERE marketingpageidliked IS NOT NULL AND marketingpageidliked != ''`
- **Comments:** `SUM(comments)`
- **Engagements:** Likes + Comments

---

## Table: `page_inventory`

Dimension table containing metadata about each page in the intranet.

| Column | Type | Description | Sample Values |
|--------|------|-------------|---------------|
| `marketingpageid` | VARCHAR | **Primary Key.** Unique identifier for the page | GUID format |
| `websitename` | VARCHAR | Name of the website/portal the page belongs to | `Intranet`, `HR Portal`, `Sales Hub` |
| `websiteurl` | VARCHAR | Base URL of the website | `https://intranet.company.com` |
| `owningbusinessunit` | VARCHAR | Business unit that owns the page | `Corporate Communications`, `HR` |
| `pagename` | VARCHAR | Human-readable name/title of the page | `Company News`, `HR Policies`, `Q3 Results` |
| `fullpageurl` | VARCHAR | **Recommended.** Complete URL of the page | `https://intranet.company.com/news/article-123` |
| `sourcesystempageid` | VARCHAR | Page ID from the source system | - |
| `pageurl` | VARCHAR | Page URL (use `fullpageurl` instead) | - |
| `theme` | VARCHAR | Content theme/category | `News`, `Policy`, `Event` |
| `topic` | VARCHAR | Content topic | `Company Updates`, `Benefits`, `Training` |
| `theme_normalized` | VARCHAR | Standardized/cleaned version of theme | `News`, `Policy`, `Event` |
| `topic_normalized` | VARCHAR | Standardized/cleaned version of topic | `Company Updates`, `Benefits`, `Training` |
| `template` | VARCHAR | Page template used | `Article`, `Landing Page`, `Document` |
| `contenttype` | VARCHAR | Type of content | `News Article`, `Policy Document`, `Video` |
| `pagelanguage` | VARCHAR | Language of the page | `en`, `de`, `fr` |
| `newscategory` | VARCHAR | Category for news articles | `Corporate`, `Local`, `Industry` |
| `targetregion` | VARCHAR | Intended geographic audience | `Global`, `EMEA`, `Americas`, `APAC` |
| `targetorganization` | VARCHAR | Intended organizational audience | `All Employees`, `Sales`, `Engineering` |
| `sitename` | VARCHAR | Alternative site name field | - |
| `exclude` | VARCHAR | Exclusion flag (usage unclear) | - |
| `cnt` | BIGINT | Count field (usage unclear) | - |

---

## Table: `employee_contact`

Dimension table containing employee demographic and organizational attributes. Use this to analyze page views by employee segments.

| Column | Type | Description | Sample Values |
|--------|------|-------------|---------------|
| `contactid` | VARCHAR | **Primary Key.** Unique identifier for the employee. Join to `fact.viewingcontactid` | GUID format |
| `employeebusinessdivision` | VARCHAR | Business division the employee belongs to | `Group Functions`, `Global Wealth Management`, `Investment Bank`, `Personal & Corporate Banking`, `Asset Management`, `Non-Core and Legacy` |
| `employeeregion` | VARCHAR | Geographic region of the employee | `EMEA`, `Americas`, `APAC` |
| `employeeworkcountry` | VARCHAR | Country where the employee works | `Germany`, `United States`, `Singapore` |
| `employeegcrscountry` | VARCHAR | GCRS (Group Consolidation & Reporting System) country - finance-owned hierarchy used for organizational and cost centre reporting | `Germany`, `United States`, `Singapore` |
| `employeeclass` | VARCHAR | Employment classification | `Employee`, `External Staff`, `Intern`, `Trainee`, `Contractor`, `Agency/Temp`, `Assignee` |
| `employeefunction` | VARCHAR | Functional classification | `REV` (Revenue generating), `SUP` (Support functions) |
| `employeerank` | VARCHAR | Employee rank/level | Varies by organization |
| `ou_lvl_1` | VARCHAR | Organization Unit Level 1 (highest) | `Board of Directors` |
| `ou_lvl_2` | VARCHAR | Organization Unit Level 2 | `Group Executive Board`, `Board of Directors` |
| `ou_lvl_3` | VARCHAR | Organization Unit Level 3 | `Group Functions`, `Business Divisions`, `Group Internal Audit` |
| `ou_lvl_4` | VARCHAR | Organization Unit Level 4 | More granular organizational units |
| `ou_lvl_5` | VARCHAR | Organization Unit Level 5 (most granular) | Most granular organizational units |
| `employeecategory` | VARCHAR | Employee category (mostly empty) | - |
| `employeecluster` | VARCHAR | Employee cluster (empty) | - |
| `employeefamily` | VARCHAR | Employee family grouping | - |
| `employeerole` | VARCHAR | Employee role | - |

### Most Useful Employee Attributes for Analysis

1. **employeebusinessdivision** - Analyze by business division
2. **employeeregion** - Analyze by geographic region
3. **employeeclass** - Filter by employment type (Employee vs Contractor vs Intern, etc.)

---

## Table: `dim_date`

Date dimension table for time-based analysis. Provides various date attributes for filtering and grouping.

| Column | Type | Description | Sample Values |
|--------|------|-------------|---------------|
| `datekey` | BIGINT | **Primary Key.** Date in YYYYMMDD format. Join to `fact.visitdatekey` | `20251015`, `20251101` |
| `date` | DATE | Actual date value | `2025-10-15`, `2025-11-01` |
| `year` | INTEGER | Year | `2024`, `2025`, `2026` |
| `quarter` | INTEGER | Quarter number (1-4) | `1`, `2`, `3`, `4` |
| `quarter_name` | VARCHAR | Quarter label | `Q1`, `Q2`, `Q3`, `Q4` |
| `year_quarter` | VARCHAR | Year and quarter combined | `Q1 2025`, `Q4 2025` |
| `month` | INTEGER | Month number (1-12) | `1`, `6`, `12` |
| `month_name` | VARCHAR | Full month name | `January`, `June`, `December` |
| `month_short` | VARCHAR | Abbreviated month name | `Jan`, `Jun`, `Dec` |
| `year_month` | VARCHAR | Year-month in YYYY-MM format | `2025-01`, `2025-06`, `2025-12` |
| `week_number` | INTEGER | ISO week number (1-53) | `1`, `26`, `52` |
| `year_week` | VARCHAR | Year-week in ISO format | `2025-W01`, `2025-W26`, `2025-W52` |
| `day_of_month` | INTEGER | Day of the month (1-31) | `1`, `15`, `31` |
| `day_of_year` | INTEGER | Day of the year (1-366) | `1`, `100`, `365` |
| `day_of_week` | INTEGER | ISO day of week (1=Monday, 7=Sunday) | `1`, `5`, `7` |
| `day_name` | VARCHAR | Full day name | `Monday`, `Friday`, `Sunday` |
| `day_short` | VARCHAR | Abbreviated day name | `Mon`, `Fri`, `Sun` |
| `is_weekend` | BOOLEAN | True if Saturday or Sunday | `true`, `false` |
| `is_month_start` | BOOLEAN | True if first day of month | `true`, `false` |
| `is_month_end` | BOOLEAN | True if last day of month | `true`, `false` |
| `is_quarter_start` | BOOLEAN | True if first day of quarter | `true`, `false` |
| `is_quarter_end` | BOOLEAN | True if last day of quarter | `true`, `false` |
| `is_year_start` | BOOLEAN | True if January 1st | `true`, `false` |
| `is_year_end` | BOOLEAN | True if December 31st | `true`, `false` |

---

## Common Query Patterns

### 1. Unique Visitors by Region for a Date Range

```sql
SELECT
    e.employeeregion,
    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors
FROM fact f
LEFT JOIN employee_contact e ON f.viewingcontactid = e.contactid
WHERE f.visitdatekey BETWEEN 20251001 AND 20251031
GROUP BY e.employeeregion
ORDER BY unique_visitors DESC
```

### 2. Page Views by Website and Month

```sql
SELECT
    p.websitename,
    d.year_month,
    SUM(f.views) AS total_views,
    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors
FROM fact f
JOIN page_inventory p ON f.marketingpageid = p.marketingpageid
JOIN dim_date d ON f.visitdatekey = d.datekey
GROUP BY p.websitename, d.year_month
ORDER BY d.year_month, total_views DESC
```

### 3. Top Pages by Engagement

```sql
SELECT
    p.pagename,
    p.websitename,
    SUM(f.views) AS total_views,
    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
    SUM(CASE WHEN f.marketingpageidliked IS NOT NULL AND f.marketingpageidliked != '' THEN 1 ELSE 0 END) AS likes,
    SUM(f.comments) AS comments
FROM fact f
JOIN page_inventory p ON f.marketingpageid = p.marketingpageid
GROUP BY p.pagename, p.websitename
ORDER BY total_views DESC
LIMIT 20
```

### 4. Traffic by Referrer Channel

```sql
SELECT
    f.referrerapplicationid AS channel,
    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors,
    SUM(f.views) AS total_views
FROM fact f
GROUP BY f.referrerapplicationid
ORDER BY unique_visitors DESC
```

### 5. Employee Class Distribution of Visitors

```sql
SELECT
    e.employeeclass,
    COUNT(DISTINCT f.viewingcontactid) AS unique_visitors
FROM fact f
LEFT JOIN employee_contact e ON f.viewingcontactid = e.contactid
WHERE f.visitdatekey BETWEEN 20251001 AND 20251031
GROUP BY e.employeeclass
ORDER BY unique_visitors DESC
```

---

## Table Relationships

```
fact
  |-- visitdatekey -----> dim_date.datekey
  |-- marketingpageid --> page_inventory.marketingpageid
  |-- viewingcontactid -> employee_contact.contactid
```

---

## Notes for Chatbot Implementation

1. **Date Filtering:** Always use `visitdatekey` with YYYYMMDD integer format (e.g., `20251015` for October 15, 2025)

2. **UV Calculation:** Unique Visitors must be calculated as `COUNT(DISTINCT viewingcontactid)` - this cannot be pre-aggregated across different date ranges

3. **Likes Calculation:** A page is liked when `marketingpageidliked IS NOT NULL AND marketingpageidliked != ''`

4. **NULL Handling:** Use `LEFT JOIN` with `COALESCE` when joining to dimension tables - `LEFT JOIN` keeps all fact rows even without a match, and `COALESCE(column, 'Unknown')` replaces NULL values with a default

5. **Page URLs:** Use `fullpageurl` from `page_inventory` for page URL filtering

6. **Employee Attributes:** The most reliable employee attributes are: `employeebusinessdivision` and `employeeregion`
