# Federal Contract Spending Intelligence Dashboard: Trend, Concentration, and Efficiency Analysis (2021–2024)

## Project Summary
This project analyzes U.S. federal contract spending data from fiscal years 2021 through 2024 to identify multi-year spending trends, agency concentration patterns, and high-growth areas that may warrant closer review. The goal is to build a decision-focused analytics project that demonstrates end-to-end business analytics capability across data sourcing, cleaning, transformation, SQL analysis, KPI development, and dashboard reporting.

Rather than simply visualizing spending totals, this project is designed to support better decision-making by surfacing where contract obligations are concentrated, which agencies are growing fastest, and where year-over-year changes appear unusually large relative to the broader spending trend.

## Business Problem
Federal contract spending is large, complex, and distributed across many agencies. Decision-makers need a structured way to monitor how spending changes over time, where obligations are concentrated, and which areas may deserve closer review for planning, oversight, or resource prioritization.

This project addresses that need by transforming raw federal contract data into a set of decision-ready metrics and visual insights.

## Project Objective
The objective of this project is to use federal contract data to answer practical business and oversight questions such as:
- How did federal contract obligations change from 2021 to 2024?
- Which agencies accounted for the largest share of contract spending?
- Which agencies experienced the fastest year-over-year growth?
- How concentrated is contract spending among the top agencies?
- Which agencies show unusual volatility or sharp spending changes over time?
- What patterns suggest opportunities for closer spending review or resource optimization?

## Data Source
This project uses federal contract award data from the **USAspending Award Data Archive**. The archive provides downloadable award data by category and fiscal year. USAspending states that **full files** contain fiscal-year data up to the date the file was prepared, while **delta files** contain only new, modified, and deleted records since the previous file. For this project, the analysis is based on annual contract data files covering fiscal years **2021, 2022, 2023, and 2024**. :contentReference[oaicite:1]{index=1}

Primary source:
- USAspending.gov — Award Data Archive

Supporting reference:
- USAspending.gov — Federal Spending Guide :contentReference[oaicite:2]{index=2}

## Scope
- **Award Type:** Contracts
- **Time Period:** FY2021–FY2024
- **Primary Focus:** Federal contract obligations, agency-level trends, growth patterns, and spending concentration
- **Analytical Goal:** Produce an executive-style dashboard and supporting analysis that can inform review, prioritization, and decision-making

## Business Questions Being Solved
This project is built around the following core questions:

1. **Trend Analysis**
   - How has total federal contract spending changed year over year from 2021 to 2024?

2. **Agency Concentration**
   - Which agencies account for the largest share of total contract obligations?
   - Is spending concentrated among a relatively small number of agencies?

3. **Growth and Change Detection**
   - Which agencies experienced the largest absolute increase in contract obligations?
   - Which agencies experienced the fastest percentage growth?

4. **Oversight and Review Prioritization**
   - Which agencies combine high total spending with high growth?
   - Which agencies show volatility or sudden shifts that may warrant further review?

5. **Decision Support**
   - Where should leadership focus attention first if the goal is to monitor large spending centers and unusual changes in obligations?

## KPIs Tracked
The dashboard and analysis will focus on a set of business-relevant KPIs, including:

- **Total Contract Obligations**
- **Year-over-Year Spending Growth (%)**
- **Absolute Change in Obligations by Year**
- **Top 10 Agencies by Contract Spending**
- **Top 10 Agencies’ Share of Total Spend**
- **Fastest-Growing Agencies**
- **Largest Absolute Spending Increases**
- **Spending Concentration Ratio**
- **Agency Spending Volatility**
- **Multi-Year Growth Trend by Agency**

These KPIs are intended to move beyond descriptive totals and help highlight concentration, growth, and potential review areas.

## Analytical Approach
The project follows an end-to-end analytics workflow:

1. **Data Acquisition**
   - Download raw contract data files for FY2021–FY2024 from the USAspending Award Data Archive

2. **Data Cleaning and Standardization**
   - Review available fields and select analysis-relevant columns
   - Standardize field names and data types across years
   - Handle missing or inconsistent values
   - Prepare obligation amounts and agency fields for analysis

3. **Dataset Consolidation**
   - Combine yearly contract data into a unified analysis-ready dataset
   - Add fiscal year tagging and ensure consistent schema alignment

4. **Exploratory Data Analysis**
   - Review distributions, totals, and outliers
   - Validate trends across years and agencies

5. **SQL-Based Analysis**
   - Build reusable queries to calculate spending totals, rankings, year-over-year growth, and concentration metrics

6. **Dashboard Development**
   - Create a Power BI dashboard with executive KPIs, trend visuals, agency comparisons, and drilldown views

7. **Insight Generation**
   - Translate analysis into business findings and practical recommendations

## Techniques Used
This project is designed to showcase both technical and business analytics techniques, including:

- Data cleaning and transformation
- Schema standardization across multiple yearly files
- Exploratory data analysis
- Aggregation and summarization
- Trend analysis
- Year-over-year growth analysis
- Ranking and top-N analysis
- Concentration analysis
- Volatility analysis
- KPI design
- Dashboard storytelling
- Executive summary communication

## Tools and Technologies
- **Python** — data cleaning, preprocessing, and exploratory analysis
- **Pandas** — transformation and dataset consolidation
- **Jupyter Notebook** — analysis workflow and documentation
- **SQL** — querying, aggregation, ranking, and KPI generation
- **Power BI** — dashboard design and business intelligence reporting
- **Excel** — quick validation and spot checks
- **Git / GitHub** — version control and project documentation

## Planned Dashboard Views
The final dashboard is planned to include the following views:

### 1. Executive Overview
- Total contract obligations
- Year-over-year growth
- Top agency by spending
- Total agencies included
- Spending trend from 2021 to 2024

### 2. Agency Comparison
- Top agencies by total obligations
- Agency-level growth rates
- Agency spending by year
- Filters for year and agency

### 3. Concentration and Review Priorities
- Share of total spending held by top agencies
- Ranking of agencies by growth and scale
- Identification of agencies with both high spend and high growth

### 4. Drilldown Analysis
- Deeper breakdown by agency or sub-agency
- Detailed tables for targeted review
- Support for identifying unusual patterns and changes

## Expected Deliverables
This repository is intended to include:
- Clean project documentation
- Jupyter notebooks for cleaning and analysis
- SQL query files
- Power BI dashboard files and screenshots
- Key findings summary
- Reproducible project structure and methodology notes

### Data Availability
The full raw and cleaned contract datasets used in this project are too large to store directly in this GitHub repository.

This repository includes:
- project code
- notebooks
- SQL queries
- dashboard assets
- a small sample dataset for reference

To reproduce the analysis:
1. Download the FY2021–FY2024 contract files from the USAspending Award Data Archive
2. Place the raw files in the `data_raw/` directory
3. Run the cleaning and consolidation notebook
4. Generate the yearly and master cleaned datasets locally

## Repository Structure
```text
federal-spending-efficiency-analysis/
│
├── README.md
├── .gitignore
├── requirements.txt
│
├── data/
│   ├── raw/              # raw source files stored locally, typically ignored
│   ├── processed/        # cleaned or transformed outputs
│   └── sample/           # optional sample data for reference
│
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_exploratory_analysis.ipynb
│   └── 03_final_analysis.ipynb
│
├── sql/
│   ├── 01_total_spending_by_year.sql
│   ├── 02_top_agencies.sql
│   ├── 03_yoy_growth.sql
│   ├── 04_spending_concentration.sql
│   └── 05_volatility_analysis.sql
│
├── dashboards/
│   ├── federal_spending_dashboard.pbix
│   └── screenshots/
│
└── outputs/
    ├── executive_summary.md
    └── key_findings.md

