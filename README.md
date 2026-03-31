# Federal Contract Spending Intelligence Dashboard: Trend, Concentration, and Efficiency Analysis (2021–2024)

## Current Status
**Project stage:** Data cleaning and consolidation completed  

**Completed so far:**
- Downloaded and organized FY2021–FY2024 federal contract data from USAspending  
- Cleaned and standardized raw contract files across all four years  
- Combined yearly files into master cleaned datasets  
- Created a lean analysis-ready dataset for downstream KPI analysis and dashboard development  

**Current focus:**
- Exploratory analysis  
- KPI development  
- SQL query development  
- Power BI dashboard construction  

---

## Project Summary

This project analyzes U.S. federal contract spending from fiscal years 2021 through 2024 to identify spending trends, agency concentration, and high-growth areas that may warrant closer review.

It is structured to reflect real-world analytical workflows and demonstrate the ability to work with large-scale datasets, design business-relevant metrics, and communicate insights effectively.

The objective is not just to report total spending, but to transform raw federal contract data into decision-ready insights that highlight:
- where contract obligations are concentrated  
- which agencies are driving growth  
- where year-over-year changes may signal potential inefficiencies or areas for further review  

To accomplish this, the project builds an end-to-end analytics pipeline that:
- ingests large-scale public spending data (millions of records per year)  
- standardizes and consolidates multi-year datasets  
- develops KPI-driven analysis using Python and SQL  
- delivers insights through a business-focused dashboard  

The final output is designed to support analytical thinking aligned with roles in government contracting, financial analysis, and operations strategy, with a focus on scale, clarity, and decision relevance.

---

## Business Problem

Federal contract spending represents a significant portion of government expenditures and is distributed across numerous agencies, programs, and service areas. However, without structured analysis, it is difficult to quickly understand where spending is concentrated, how it is changing over time, and which areas may require closer review.

Decision-makers need a clear and consistent way to:
- monitor multi-year spending trends  
- identify which agencies control the largest share of contract obligations  
- detect unusually high growth or volatility in spending  
- prioritize areas for deeper review or resource optimization  

Raw contract-level data alone does not provide these insights. It must be transformed into aggregated, comparable, and decision-ready metrics.

This project addresses that gap by converting large-scale federal contract data into a structured analytical framework that supports trend analysis, concentration analysis, and growth detection across agencies.

---

## Project Objective

The objective of this project is to use federal contract data to answer practical business and oversight questions such as:
- How did federal contract obligations change from 2021 to 2024?  
- Which agencies accounted for the largest share of contract spending?  
- Which agencies experienced the fastest year-over-year growth?  
- How concentrated is contract spending among the top agencies?  
- Which agencies show unusual volatility or sharp spending changes over time?  
- What patterns suggest opportunities for closer spending review or resource optimization?  

---

## Data Source

This project uses federal contract award data from the USAspending Award Data Archive.

**Primary source:**  
https://www.usaspending.gov/download_center/award_data_archive  

**Supporting reference:**  
https://www.usaspending.gov/#/federal_spending  

---

## Scope
- **Award Type:** Contracts  
- **Time Period:** FY2021–FY2024  
- **Primary Focus:** Federal contract obligations, agency-level trends, growth patterns, and spending concentration  
- **Analytical Goal:** Produce an executive-style dashboard and supporting analysis that can inform review, prioritization, and decision-making  

---

## Business Questions Being Solved

### Trend Analysis
- How has total federal contract spending changed from 2021 to 2024?  
- Are spending increases consistent year-over-year, or are there periods of acceleration or slowdown?  

### Agency Concentration
- Which agencies account for the largest share of total contract obligations?  
- How concentrated is federal contract spending among the top agencies?  

### Growth and Change Detection
- Which agencies have experienced the largest absolute increases in spending?  
- Which agencies are growing the fastest in percentage terms?  
- Are there agencies whose growth significantly outpaces the overall trend?  

### Oversight and Review Prioritization
- Which agencies combine high total spending with high growth?  
- Which agencies show volatility or sharp year-over-year changes that may warrant further review?  

### Decision Support
- If leadership had to prioritize oversight or analysis efforts, which agencies should be reviewed first based on scale, growth, and variability?  

---

## KPIs Tracked

### Scale Metrics
- **Total Contract Obligations**  
- **Total Obligations by Year**

### Growth Metrics
- **Year-over-Year Growth (%)**  
- **Absolute Change in Obligations**  
- **Agency-Level Growth Rate**

### Concentration Metrics
- **Top 10 Agencies by Contract Spending**  
- **Top Agencies’ Share of Total Spend (%)**  
- **Spending Concentration Ratio**

### Oversight and Prioritization Metrics
- **High Spend + High Growth Agencies**  
- **Spending Volatility**  
- **Multi-Year Growth Trend**

---

## Analytical Approach

### 1. Data Acquisition
- Downloaded FY2021–FY2024 contract data from USAspending  

### 2. Data Cleaning and Standardization
- Standardized schemas across years  
- Converted data types  
- Handled missing values  
- Removed duplicates  

### 3. Scalable Data Processing
- Implemented chunk-based processing for large datasets  
- Processed multi-million-row files efficiently  

### 4. Dataset Consolidation
- Combined yearly data into a unified master dataset  
- Added fiscal year indicators  

### 5. Data Validation
- Verified row counts and totals  
- Checked data consistency and missingness  

### 6. Exploratory Analysis (In Progress)
- Trend analysis and distribution review  

### 7. SQL-Based Analysis (Planned)
- KPI and aggregation queries  

### 8. Dashboard Development (Planned)
- Power BI dashboard with executive KPIs  

### 9. Insight Generation (Planned)
- Translate analytical results into actionable business insights  

---

## Techniques Used
- Data cleaning and transformation  
- Multi-year schema standardization  
- Exploratory data analysis  
- Aggregation and summarization  
- Trend and growth analysis  
- Ranking and concentration analysis  
- KPI design  
- Dashboard storytelling  

---

## Tools and Technologies

- **Python (Pandas)** — large-scale data cleaning and transformation  
- **Jupyter Notebook** — workflow and documentation  
- **SQL** — aggregation and KPI analysis  
- **Power BI** — dashboard development  
- **Excel** — validation and quick checks  
- **Git / GitHub** — version control and project documentation  

---

## Data Availability

The full datasets are too large to store in this repository.

This repo includes:
- code and notebooks  
- SQL queries  
- project documentation  
- a small sample dataset  

To reproduce:
1. Download FY2021–FY2024 contract data from USAspending  
2. Place files in `data_raw/`  
3. Run the cleaning notebook  
4. Generate cleaned datasets locally  

---

## Repository Structure

federal-spending-efficiency-analysis/
│
├── README.md
├── .gitignore
│
├── data_cleaned/
│ └── sample/
│ └── sample_contracts_2021_2024_1000_rows.csv
│
├── notebooks/
│ └── 01_data_cleaning.ipynb
│
├── sql/ # (in progress)
├── dashboards/ # (in progress)
└── outputs/ # (in progress)

---
## Key Insights (Preview)

Preliminary analysis of FY2021–FY2024 federal contract data reveals several notable patterns:

- **Steady Growth in Federal Contract Spending**  
  Total contract obligations increased consistently from 2021 through 2023, indicating sustained expansion in federal contracting activity, followed by a slight stabilization in 2024.

- **High Concentration Among Top Agencies**  
  A small number of agencies account for a disproportionately large share of total contract obligations, suggesting that federal spending is highly concentrated rather than evenly distributed.

- **Variation in Agency Growth Rates**  
  While overall spending trends upward, growth is not uniform across agencies. Some agencies exhibit significantly higher growth rates than the overall trend, indicating potential shifts in priorities or funding allocation.

- **Emergence of High-Growth Agencies**  
  Certain agencies show both high total spending and strong year-over-year growth, making them key candidates for further analysis and oversight.

- **Potential Areas for Deeper Review**  
  Agencies with large spending levels combined with volatility or sudden increases may warrant closer examination to understand underlying drivers.

*Note: These insights are based on initial exploratory analysis and will be refined through further SQL-based analysis and dashboard development.*

## Next Steps

- Complete exploratory analysis  
- Build SQL query layer  
- Develop Power BI dashboard  
- Generate key insights and executive summary  