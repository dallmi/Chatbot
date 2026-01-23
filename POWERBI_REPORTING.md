# Power BI Reporting Guide

This guide provides DAX measures and setup instructions for answering key stakeholder questions using the Intranet Analytics data.

---

## Data Model Setup

### Import Parquet Files

Import the following files from `output/parquet/`:

| File | Table Name | Description |
|------|------------|-------------|
| `fact.parquet` | fact | Page view events |
| `page_inventory.parquet` | page_inventory | Page metadata |
| `employee_contact.parquet` | employee_contact | Employee attributes |
| `dim_date.parquet` | dim_date | Date dimension |

### Create Relationships

Set up a star schema with these relationships:

```
fact[marketingpageid] --> page_inventory[marketingpageid] (Many-to-One)
fact[viewingcontactid] --> employee_contact[contactid] (Many-to-One)
fact[visitdatekey] --> dim_date[datekey] (Many-to-One)
```

### Mark Date Table

Mark `dim_date` as the date table:
1. Select `dim_date` table
2. Table tools > Mark as date table
3. Select `date` column as the date column

---

## Core Measures

Create these foundational measures first. All other measures build on these.

```dax
// ============================================================
// CORE MEASURES - Create these first
// ============================================================

// Unique Visitors (UV) - The most important metric
UV = DISTINCTCOUNT(fact[viewingcontactid])

// Total Views
Total Views = SUM(fact[views])

// Total Visits
Total Visits = SUM(fact[visits])

// Likes (when marketingpageidliked has a value)
Likes =
COUNTROWS(
    FILTER(
        fact,
        NOT(ISBLANK(fact[marketingpageidliked])) && fact[marketingpageidliked] <> ""
    )
)

// Comments
Comments = SUM(fact[comments])

// Total Engagements (Likes + Comments)
Engagements = [Likes] + [Comments]

// Engagement Rate (%)
Engagement Rate =
DIVIDE(
    [Engagements],
    [Total Views],
    0
) * 100

// Total Employees (for reach calculation - update this number)
Total Employees = 75000  // UPDATE THIS with your actual employee count
```

---

## 1. Employee Reach Analysis

### Key Measures

```dax
// ============================================================
// EMPLOYEE REACH MEASURES
// ============================================================

// Overall Reach Rate (%)
Reach Rate =
DIVIDE(
    [UV],
    [Total Employees],
    0
) * 100

// Daily Average UV
Daily Average UV =
AVERAGEX(
    VALUES(dim_date[date]),
    CALCULATE([UV])
)

// Reach Rate by Region (use with employeeregion slicer)
Reach Rate by Segment =
VAR SegmentUV = [UV]
VAR SegmentTotal =
    CALCULATE(
        DISTINCTCOUNT(employee_contact[contactid]),
        ALLEXCEPT(employee_contact, employee_contact[employeeregion])
    )
RETURN
DIVIDE(SegmentUV, SegmentTotal, 0) * 100

// Reach Rate by Division (use with employeebusinessdivision slicer)
Reach Rate by Division =
VAR DivisionUV = [UV]
VAR DivisionTotal =
    CALCULATE(
        DISTINCTCOUNT(employee_contact[contactid]),
        ALLEXCEPT(employee_contact, employee_contact[employeebusinessdivision])
    )
RETURN
DIVIDE(DivisionUV, DivisionTotal, 0) * 100

// Month-over-Month Reach Change
Reach MoM Change =
VAR CurrentMonthUV = [UV]
VAR PreviousMonthUV =
    CALCULATE(
        [UV],
        DATEADD(dim_date[date], -1, MONTH)
    )
RETURN
DIVIDE(
    CurrentMonthUV - PreviousMonthUV,
    PreviousMonthUV,
    0
) * 100

// Reach Trend (Last 6 Months) - for sparkline
Reach Trend 6M =
CALCULATE(
    [UV],
    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -6, MONTH)
)
```

### Sample Questions & Answers

| Question | Visual Type | Measure | Slicers/Filters |
|----------|-------------|---------|-----------------|
| What percentage of employees visited the intranet today? | Card | `Reach Rate` | Date = Today |
| How many unique employees did we reach this week? | Card | `UV` | Date = This Week |
| What is our monthly reach rate? | Card | `Reach Rate` | Date = This Month |
| What percentage of EMEA employees did we reach? | Card | `Reach Rate by Segment` | employeeregion = EMEA |
| Which region has the lowest reach rate? | Table | `Reach Rate by Segment` | Group by employeeregion |
| Is our reach growing or declining? | Line Chart | `UV` | X-axis: year_month |
| How does this month compare to last month? | Card | `Reach MoM Change` | Date = This Month |

### Recommended Visuals

**Reach Dashboard:**
1. **Card**: Today's Reach Rate
2. **Card**: This Month's UV
3. **Card**: MoM Change %
4. **Bar Chart**: UV by Region
5. **Bar Chart**: UV by Business Division
6. **Line Chart**: Daily UV Trend (with 7-day moving average)
7. **Matrix**: Region x Division UV breakdown

---

## 2. Content Journey & Funnel Analysis

### Key Measures

```dax
// ============================================================
// CONTENT JOURNEY MEASURES
// ============================================================

// Homepage Visitors
Homepage Visitors =
CALCULATE(
    [UV],
    FILTER(
        page_inventory,
        page_inventory[contenttype] = "Homepage"
    )
)

// Article Visitors (employees who viewed any article)
Article Visitors =
CALCULATE(
    [UV],
    FILTER(
        page_inventory,
        page_inventory[contenttype] = "Article"
    )
)

// Homepage to Article Click-Through Rate
Homepage to Article CTR =
VAR HomepageVisitors = [Homepage Visitors]
VAR ArticleVisitors = [Article Visitors]
VAR BothVisitors =
    CALCULATE(
        DISTINCTCOUNT(fact[viewingcontactid]),
        FILTER(
            SUMMARIZE(
                fact,
                fact[viewingcontactid],
                "HasHomepage", CALCULATE(COUNTROWS(fact), page_inventory[contenttype] = "Homepage"),
                "HasArticle", CALCULATE(COUNTROWS(fact), page_inventory[contenttype] = "Article")
            ),
            [HasHomepage] > 0 && [HasArticle] > 0
        )
    )
RETURN
DIVIDE(BothVisitors, HomepageVisitors, 0) * 100

// Visitors Who Viewed Multiple Pages
Multi-Page Visitors =
COUNTROWS(
    FILTER(
        SUMMARIZE(
            fact,
            fact[viewingcontactid],
            "PageCount", DISTINCTCOUNT(fact[marketingpageid])
        ),
        [PageCount] > 1
    )
)

// Multi-Page Visitor Rate
Multi-Page Rate =
DIVIDE(
    [Multi-Page Visitors],
    [UV],
    0
) * 100

// Average Pages per Visitor
Avg Pages per Visitor =
DIVIDE(
    DISTINCTCOUNT(fact[marketingpageid]),
    [UV],
    0
)

// Views per Visitor
Views per Visitor =
DIVIDE(
    [Total Views],
    [UV],
    0
)

// Engagement Conversion (viewers who engaged)
Engagement Conversion =
VAR ViewersWhoEngaged =
    COUNTROWS(
        FILTER(
            SUMMARIZE(
                fact,
                fact[viewingcontactid],
                "HasEngagement",
                    CALCULATE(
                        COUNTROWS(
                            FILTER(
                                fact,
                                NOT(ISBLANK(fact[marketingpageidliked])) || fact[comments] > 0
                            )
                        )
                    )
            ),
            [HasEngagement] > 0
        )
    )
RETURN
DIVIDE(ViewersWhoEngaged, [UV], 0) * 100

// Channel Comparison - Email vs Intranet UV
Email UV =
CALCULATE(
    [UV],
    fact[referrerapplicationid] = "Email"
)

Intranet UV =
CALCULATE(
    [UV],
    fact[referrerapplicationid] = "Intranet"
)

// Email Engagement Rate
Email Engagement Rate =
CALCULATE(
    [Engagement Rate],
    fact[referrerapplicationid] = "Email"
)

// Intranet Engagement Rate
Intranet Engagement Rate =
CALCULATE(
    [Engagement Rate],
    fact[referrerapplicationid] = "Intranet"
)
```

### Sample Questions & Answers

| Question | Visual Type | Measure | Slicers/Filters |
|----------|-------------|---------|-----------------|
| What percentage of homepage visitors clicked through to read an article? | Card | `Homepage to Article CTR` | - |
| What percentage of visitors view more than one page? | Card | `Multi-Page Rate` | - |
| How deep do employees go into the site? | Card | `Avg Pages per Visitor` | - |
| Do Email visitors read more than Intranet visitors? | Table | `Views per Visitor` | Group by referrerapplicationid |
| What percentage of article viewers engage? | Card | `Engagement Conversion` | contenttype = Article |

### Recommended Visuals

**Journey Dashboard:**
1. **Funnel Chart**: Homepage > Article > Engagement
2. **Card**: Multi-Page Rate
3. **Card**: Avg Pages per Visitor
4. **Bar Chart**: UV by referrerapplicationid (channel)
5. **Comparison Chart**: Email vs Intranet Engagement Rate
6. **Table**: Top pages by UV with engagement rate

---

## 3. Content Performance

### Key Measures

```dax
// ============================================================
// CONTENT PERFORMANCE MEASURES
// ============================================================

// Top Pages Rank (use with pagename)
Page Rank by Views =
RANKX(
    ALL(page_inventory[pagename]),
    [Total Views],
    ,
    DESC,
    DENSE
)

Page Rank by UV =
RANKX(
    ALL(page_inventory[pagename]),
    [UV],
    ,
    DESC,
    DENSE
)

Page Rank by Engagement =
RANKX(
    ALL(page_inventory[pagename]),
    [Engagements],
    ,
    DESC,
    DENSE
)

// Theme Performance
Theme UV =
CALCULATE(
    [UV],
    ALLEXCEPT(page_inventory, page_inventory[theme])
)

Theme Engagement Rate =
CALCULATE(
    [Engagement Rate],
    ALLEXCEPT(page_inventory, page_inventory[theme])
)

// News Category Performance
News Category UV =
CALCULATE(
    [UV],
    ALLEXCEPT(page_inventory, page_inventory[newscategory])
)

// Content Type Performance
Content Type UV =
CALCULATE(
    [UV],
    ALLEXCEPT(page_inventory, page_inventory[contenttype])
)

// Average Engagement Rate (for benchmarking)
Avg Engagement Rate =
CALCULATE(
    [Engagement Rate],
    ALL(page_inventory)
)

// Above/Below Average Indicator
Performance vs Avg =
IF(
    [Engagement Rate] > [Avg Engagement Rate],
    "Above Average",
    "Below Average"
)

// Engagement Rate Variance from Average
Engagement Variance =
[Engagement Rate] - [Avg Engagement Rate]

// Website Performance
Website UV =
CALCULATE(
    [UV],
    ALLEXCEPT(page_inventory, page_inventory[websitename])
)
```

### Sample Questions & Answers

| Question | Visual Type | Measure | Slicers/Filters |
|----------|-------------|---------|-----------------|
| What are the top 10 pages by views? | Table | `Total Views`, `UV`, `Engagements` | Top N filter = 10 |
| Which articles got the most engagement? | Table | `Engagements`, `Engagement Rate` | contenttype = Article, Sort by Engagements |
| What content has the highest engagement rate? | Table | `Engagement Rate` | Filter: Views > 100 (avoid low-volume outliers) |
| How do articles perform compared to overview pages? | Clustered Bar | `UV`, `Engagement Rate` | Group by contenttype |
| Which themes drive the most traffic? | Bar Chart | `UV` | Group by theme |
| Which news categories get the most views? | Bar Chart | `Total Views` | Group by newscategory |
| Is this article above or below average? | Card | `Performance vs Avg` | Select specific page |

### Recommended Visuals

**Content Performance Dashboard:**
1. **Table**: Top 20 Pages (pagename, UV, Views, Engagements, Engagement Rate)
2. **Bar Chart**: UV by Theme
3. **Bar Chart**: UV by News Category
4. **Bar Chart**: UV by Content Type
5. **Scatter Plot**: UV vs Engagement Rate (identify high-performers)
6. **Card**: Total Pages with Engagement > 0

---

## 4. Strategic Message Effectiveness

### Key Measures

```dax
// ============================================================
// STRATEGIC MESSAGE EFFECTIVENESS MEASURES
// ============================================================

// Division Reach for Specific Content
// (Use with page filter to check which divisions saw specific content)
Division Reach for Content =
VAR ContentViewers = VALUES(fact[viewingcontactid])
RETURN
CALCULATE(
    DISTINCTCOUNT(fact[viewingcontactid]),
    TREATAS(ContentViewers, fact[viewingcontactid])
)

// Divisions NOT Reached (count of divisions with 0 UV for selected content)
Divisions Not Reached =
VAR AllDivisions = DISTINCTCOUNT(employee_contact[employeebusinessdivision])
VAR DivisionsReached =
    CALCULATE(
        DISTINCTCOUNT(employee_contact[employeebusinessdivision]),
        fact
    )
RETURN
AllDivisions - DivisionsReached

// Target Audience Match Rate
// Compare targetregion in page_inventory with employeeregion of actual visitors
Target Region Match Rate =
VAR TargetRegion = SELECTEDVALUE(page_inventory[targetregion])
VAR MatchingVisitors =
    CALCULATE(
        [UV],
        employee_contact[employeeregion] = TargetRegion
    )
VAR TotalVisitors = [UV]
RETURN
IF(
    TargetRegion = "Global",
    100,  // Global content targets everyone
    DIVIDE(MatchingVisitors, TotalVisitors, 0) * 100
)

// Strategy Content UV
Strategy Content UV =
CALCULATE(
    [UV],
    page_inventory[newscategory] = "Strategy"
)

// Strategy Content Engagement Rate
Strategy Engagement Rate =
CALCULATE(
    [Engagement Rate],
    page_inventory[newscategory] = "Strategy"
)

// Leadership Communications UV (Strategy + Culture + Thought leadership)
Leadership Comms UV =
CALCULATE(
    [UV],
    page_inventory[newscategory] IN {"Strategy", "Culture", "Thought leadership"}
)

// Leadership Comms Engagement Rate
Leadership Comms Engagement Rate =
CALCULATE(
    [Engagement Rate],
    page_inventory[newscategory] IN {"Strategy", "Culture", "Thought leadership"}
)

// Division Coverage (% of divisions that saw the content)
Division Coverage =
VAR TotalDivisions =
    CALCULATE(
        DISTINCTCOUNT(employee_contact[employeebusinessdivision]),
        ALL(employee_contact)
    )
VAR DivisionsReached =
    DISTINCTCOUNT(employee_contact[employeebusinessdivision])
RETURN
DIVIDE(DivisionsReached, TotalDivisions, 0) * 100

// Region Coverage
Region Coverage =
VAR TotalRegions =
    CALCULATE(
        DISTINCTCOUNT(employee_contact[employeeregion]),
        ALL(employee_contact)
    )
VAR RegionsReached =
    DISTINCTCOUNT(employee_contact[employeeregion])
RETURN
DIVIDE(RegionsReached, TotalRegions, 0) * 100

// Message Penetration (UV as % of workforce)
Message Penetration =
DIVIDE(
    [UV],
    [Total Employees],
    0
) * 100
```

### Sample Questions & Answers

| Question | Visual Type | Measure | Slicers/Filters |
|----------|-------------|---------|-----------------|
| Did our Strategy update reach all business divisions? | Card | `Division Coverage` | newscategory = Strategy |
| Which divisions did NOT see the quarterly results? | Table | Show divisions where UV = 0 | Filter specific page |
| How many employees saw the CEO message? | Card | `UV` | Filter: pagename contains "CEO" |
| What was the reach of strategic priorities announcement? | Card | `Message Penetration` | Filter specific page |
| Did employees engage with the Strategy news category? | Card | `Strategy Engagement Rate` | - |
| What is the engagement rate on leadership communications? | Card | `Leadership Comms Engagement Rate` | - |
| Did content targeted at APAC reach APAC employees? | Card | `Target Region Match Rate` | Filter: targetregion = APAC |
| Which divisions are we failing to engage? | Table | `UV`, `Engagement Rate` | Group by employeebusinessdivision, sort by Engagement Rate ASC |

### Recommended Visuals

**Strategic Effectiveness Dashboard:**
1. **Card**: Division Coverage %
2. **Card**: Region Coverage %
3. **Card**: Message Penetration %
4. **Matrix**: Content x Division UV (shows gaps)
5. **Bar Chart**: UV by Division for selected strategic content
6. **Bar Chart**: Engagement Rate by News Category
7. **Table**: Strategic pages with low reach (< target)

---

## Quick Reference: Common Filters

### Date Filters (use dim_date)

```dax
// Today
FILTER(dim_date, dim_date[date] = TODAY())

// This Week
FILTER(dim_date, dim_date[year_week] = FORMAT(TODAY(), "YYYY") & "-W" & FORMAT(WEEKNUM(TODAY()), "00"))

// This Month
FILTER(dim_date, dim_date[year_month] = FORMAT(TODAY(), "YYYY-MM"))

// Last 30 Days
FILTER(dim_date, dim_date[date] >= TODAY() - 30)

// This Quarter
FILTER(dim_date, dim_date[year_quarter] = "Q" & QUARTER(TODAY()) & " " & YEAR(TODAY()))
```

### Content Filters (use page_inventory)

```dax
// Articles only
page_inventory[contenttype] = "Article"

// Strategy news
page_inventory[newscategory] = "Strategy"

// Specific theme
page_inventory[theme] = "Who-We-Are"

// CEO communications (search by name)
CONTAINSSTRING(page_inventory[pagename], "CEO")
```

### Employee Filters (use employee_contact)

```dax
// EMEA employees
employee_contact[employeeregion] = "EMEA"

// Investment Bank
employee_contact[employeebusinessdivision] = "Investment Bank"

// Full-time employees only
employee_contact[employeeclass] = "Employee"
```

---

## Troubleshooting

### UV Shows Higher Than Expected
- Ensure relationships are correctly set up (fact to dimensions)
- Check that date filters are applied at the report level
- UV counts distinct visitors across the filtered context

### Engagement Rate Shows 0
- Verify that `marketingpageidliked` contains values (not all blank)
- Check that likes measure is correctly filtering non-blank values

### Missing Employee Data
- Some visitors may not match to employee_contact (external visitors)
- Use `COALESCE` or handle blanks in visuals

### Performance Issues
- With large fact tables, consider using aggregations or incremental refresh
- Limit table visuals to top N rows
- Use summarized measures instead of row-level calculations

---

## Visualization Best Practices

### When to Use Each Visual Type

| Visual | Best For | Example Use Case |
|--------|----------|------------------|
| **Card** | Single KPI display | Today's UV, Reach Rate %, MoM Change |
| **KPI** | KPI with target/trend | Reach Rate vs Target (e.g., 80%) |
| **Line Chart** | Trends over time | Daily/Weekly/Monthly UV |
| **Area Chart** | Cumulative trends | Cumulative reach over month |
| **Bar Chart (Horizontal)** | Comparing categories | UV by Region, UV by Division |
| **Column Chart (Vertical)** | Time-based comparisons | UV by Month |
| **Stacked Bar** | Part-to-whole by category | Engagement breakdown (Likes vs Comments) by Theme |
| **Pie/Donut** | Proportions (max 5-6 slices) | Channel mix (Email/Intranet/Other) |
| **Matrix** | Cross-tabulation | Region x Division UV |
| **Table** | Detailed data with sorting | Top pages with all metrics |
| **Funnel** | Sequential drop-off | Homepage > Article > Engagement |
| **Scatter Plot** | Correlation analysis | UV vs Engagement Rate |
| **Gauge** | Progress toward target | Reach Rate toward 80% goal |
| **Treemap** | Hierarchical proportions | Pages by Theme > Topic |

---

## Dashboard Blueprints

### 1. Executive Summary Dashboard

**Purpose:** Quick overview for leadership - answer "How are we doing?"

**Layout (3 rows):**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   CARD      │    CARD     │    CARD     │    CARD     │
│  Total UV   │ Reach Rate  │ Engagement  │  MoM Change │
│   52,340    │    69.8%    │    2.3%     │   +5.2%     │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────┬───────────────────────────┐
│      LINE CHART             │     BAR CHART             │
│   Daily UV Trend            │   UV by Region            │
│   (with 7-day MA)           │   (horizontal bars)       │
│                             │                           │
└─────────────────────────────┴───────────────────────────┘
┌─────────────────────────────┬───────────────────────────┐
│      BAR CHART              │     TABLE                 │
│   UV by Division            │   Top 10 Pages            │
│   (horizontal bars)         │   (pagename, UV, Eng%)    │
│                             │                           │
└─────────────────────────────┴───────────────────────────┘

SLICERS (top or side panel):
- Date Range (relative: Today/This Week/This Month/Custom)
- Website (dropdown)
```

**Visual Configurations:**

| Visual | Measure | Settings |
|--------|---------|----------|
| Card - Total UV | `UV` | Format: thousands separator |
| Card - Reach Rate | `Reach Rate` | Format: percentage, 1 decimal |
| Card - Engagement | `Engagement Rate` | Format: percentage, 1 decimal |
| Card - MoM Change | `Reach MoM Change` | Conditional formatting: green if positive |
| Line Chart | `UV` by `dim_date[date]` | Add trend line (7-day moving average) |
| Bar Chart - Region | `UV` by `employee_contact[employeeregion]` | Sort descending, data labels on |
| Bar Chart - Division | `UV` by `employee_contact[employeebusinessdivision]` | Sort descending, data labels on |
| Table | pagename, `UV`, `Engagement Rate` | Top N filter = 10, sort by UV desc |

---

### 2. Employee Reach Dashboard

**Purpose:** Answer "Who are we reaching?"

**Layout:**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   KPI       │    KPI      │    KPI      │    CARD     │
│ Reach Rate  │ Division    │  Region     │   Daily     │
│  vs 80%    │ Coverage    │  Coverage   │   Avg UV    │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────────────────────────────────┐
│              MATRIX (Heat Map)                          │
│    Division (rows) x Region (columns) = UV              │
│    Conditional formatting: darker = higher UV           │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────┬───────────────────────────┐
│      BAR CHART              │     BAR CHART             │
│   Reach Rate by Division    │   Reach Rate by Region    │
│   (target line at 80%)      │   (target line at 80%)    │
└─────────────────────────────┴───────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              LINE CHART                                 │
│   Monthly Reach Rate Trend (by Region - multi-line)    │
└─────────────────────────────────────────────────────────┘

SLICERS:
- Date Range
- Employee Class (Employee/Contractor/etc.)
- Website
```

**Visual Configurations:**

| Visual | Configuration |
|--------|---------------|
| KPI - Reach Rate | Target = 80%, trend by month |
| Matrix | Rows: employeebusinessdivision, Columns: employeeregion, Values: UV, Conditional formatting: background color scale |
| Bar Chart - Division | Add constant line at 80% target |
| Line Chart - Trend | Legend: employeeregion, separate line per region |

---

### 3. Content Performance Dashboard

**Purpose:** Answer "What content is working?"

**Layout:**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   CARD      │    CARD     │    CARD     │    CARD     │
│ Total Pages │  Avg Eng%   │ Pages w/    │  Top Page   │
│   Viewed    │   Overall   │ Engagement  │     UV      │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────────────────────────────────┐
│              SCATTER PLOT                               │
│   X: UV, Y: Engagement Rate, Size: Views                │
│   (identify high performers in top-right quadrant)      │
└─────────────────────────────────────────────────────────┘
┌────────────────┬────────────────┬────────────────────────┐
│   BAR CHART    │   BAR CHART    │     BAR CHART          │
│  UV by Theme   │ UV by Content  │   UV by News Category  │
│                │    Type        │                        │
└────────────────┴────────────────┴────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              TABLE (scrollable)                         │
│   pagename | websitename | UV | Views | Eng | Eng%     │
│   (sortable columns, top 50 with scroll)                │
└─────────────────────────────────────────────────────────┘

SLICERS:
- Date Range
- Website (multi-select)
- Theme (multi-select)
- Content Type (multi-select)
- News Category (multi-select)
```

**Visual Configurations:**

| Visual | Configuration |
|--------|---------------|
| Scatter Plot | X: UV, Y: Engagement Rate, Details: pagename, Size: Total Views, Add quadrant lines at median values |
| Bar Charts | All horizontal, sorted descending, data labels on |
| Table | Enable column sorting, add conditional formatting on Engagement Rate (color scale), filter to Views > 10 to avoid outliers |

---

### 4. Content Journey Dashboard

**Purpose:** Answer "How do employees navigate?"

**Layout:**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   CARD      │    CARD     │    CARD     │    CARD     │
│  Homepage   │  Article    │ Multi-Page  │  Avg Pages  │
│  Visitors   │  Visitors   │    Rate     │ per Visitor │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────────────────────────────────┐
│              FUNNEL CHART                               │
│   Homepage Visitors > Article Viewers > Engaged         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────┬───────────────────────────┐
│      DONUT CHART            │     CLUSTERED BAR         │
│   UV by Channel             │   Engagement Rate         │
│   (Email/Intranet/Other)    │   by Channel              │
└─────────────────────────────┴───────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              TABLE                                      │
│   Channel | UV | Views | Views/Visitor | Engagement%   │
└─────────────────────────────────────────────────────────┘

SLICERS:
- Date Range
- Employee Region
- Employee Division
```

**Visual Configurations:**

| Visual | Configuration |
|--------|---------------|
| Funnel | Categories: Stage (Homepage/Article/Engaged), Values: UV at each stage |
| Donut | Values: UV, Legend: referrerapplicationid, show percentages |
| Clustered Bar | Compare Engagement Rate side-by-side by channel |

---

### 5. Strategic Message Effectiveness Dashboard

**Purpose:** Answer "Did our message get through?"

**Layout:**

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│   GAUGE     │   GAUGE     │   GAUGE     │    CARD     │
│  Division   │   Region    │  Message    │  Strategy   │
│  Coverage   │  Coverage   │ Penetration │   Eng Rate  │
└─────────────┴─────────────┴─────────────┴─────────────┘
┌─────────────────────────────────────────────────────────┐
│              MATRIX (Gap Analysis)                      │
│   Strategic Pages (rows) x Division (columns) = UV      │
│   Conditional format: RED if UV = 0 (gap!)              │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────┬───────────────────────────┐
│      BAR CHART              │     COMPARISON            │
│   Strategic Content UV      │   Strategic vs General    │
│   by Division               │   Engagement Rate         │
└─────────────────────────────┴───────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│              TABLE                                      │
│   Strategic pages not reaching all divisions            │
│   pagename | Divisions Reached | Divisions Missing      │
└─────────────────────────────────────────────────────────┘

SLICERS:
- Date Range
- News Category (pre-select: Strategy, Culture)
- Page Name (searchable dropdown)
```

**Visual Configurations:**

| Visual | Configuration |
|--------|---------------|
| Gauge | Max value = 100%, target = 100%, color: green > 90%, yellow 70-90%, red < 70% |
| Matrix | Conditional formatting: cells with UV = 0 shown in RED background |
| Comparison Bar | Side-by-side bars: Strategic content Eng% vs All content Eng% |

---

## Report Templates

### Executive Summary Report
1. KPI Cards: UV, Reach Rate, Engagement Rate, MoM Change
2. Line Chart: Daily UV trend with benchmark line
3. Bar Chart: UV by Region
4. Bar Chart: Top 10 Pages by UV
5. Table: Strategic content performance

### Content Performance Report
1. Table: All pages with metrics (sortable)
2. Bar Charts: UV by Theme, Content Type, News Category
3. Scatter Plot: UV vs Engagement Rate
4. Filters: Date, Website, Content Type

### Employee Reach Report
1. Matrix: Region x Division UV
2. Bar Chart: Reach Rate by Division
3. Bar Chart: Reach Rate by Region
4. Trend: Monthly reach over time
5. Filters: Date range, Employee Class

### Strategic Communications Report
1. Cards: Division Coverage, Region Coverage, Penetration
2. Matrix: Strategic Content x Division (shows gaps)
3. Table: Pages not reaching all divisions
4. Engagement comparison: Strategic vs General content

---

## Slicer Configuration Tips

### Recommended Slicer Types

| Slicer | Type | Settings |
|--------|------|----------|
| Date Range | Relative date slicer | Include: Today, This Week, This Month, Last 30 Days, This Quarter, Custom |
| Website | Dropdown | Multi-select enabled |
| Region | Buttons or Dropdown | Single select for drill-down |
| Division | Buttons or Dropdown | Single select for drill-down |
| Content Type | Chiclet/Buttons | Visual selection |
| Theme | Dropdown | Multi-select enabled |
| News Category | Dropdown | Multi-select enabled |
| Page Name | Searchable Dropdown | For finding specific pages |

### Sync Slicers Across Pages

1. View > Sync slicers
2. Select the slicer
3. Check which pages it should sync to
4. Recommended: Sync Date Range across all pages
