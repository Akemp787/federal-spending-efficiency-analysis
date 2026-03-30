# Federal Spending Efficiency Analysis

## Project Overview
This project analyzes U.S. federal contract spending data from **2021 through 2024** to identify spending trends, compare agencies, and surface areas that may suggest inefficiencies or unusually rapid growth. The goal is to build a portfolio project that demonstrates end-to-end analytics skills: data sourcing, cleaning, transformation, SQL analysis, and dashboard development.

The dataset for this project comes from the **USAspending Award Data Archive**, which provides federal award and contract spending data. For this project, I am using contract data files covering fiscal years **2021, 2022, 2023, and 2024** as the raw source data for analysis.

## Data Source
**Source:** USAspending.gov – Award Data Archive  
**Dataset Type:** Contracts  
**Years Used:** 2021–2024  

Example source files:
- FY2021 contract data
- FY2022 contract data
- FY2023 contract data
- FY2024 contract data

These files were downloaded from the USAspending Award Data Archive and will be used as the base data for cleaning, transformation, and analysis.

## Project Objective
The objective of this project is to answer questions such as:
- How has federal contract spending changed from 2021 to 2024?
- Which departments or agencies account for the most contract spending?
- Which agencies or categories experienced the fastest spending growth?
- Are there patterns in the data that may indicate concentration, inefficiency, or unusual changes in obligations over time?

This project is intended as a portfolio piece to showcase analytics, business intelligence, and data storytelling skills for data analyst, business analyst, financial analyst, and government/defense-related roles.

## Planned Workflow
1. Download raw federal contract spending data from USAspending for 2021–2024.
2. Store raw files locally in a `data/raw/` folder.
3. Clean and transform the data using Python and/or Excel.
4. Combine yearly datasets into one analysis-ready dataset.
5. Load cleaned data into a structured format for querying.
6. Write SQL queries to analyze spending by year, agency, and category.
7. Build visualizations and dashboards in Power BI.
8. Summarize key insights and recommendations.

## Tools
- **Python** – data cleaning, transformation, analysis
- **Pandas / Jupyter Notebook** – data wrangling and exploratory analysis
- **SQL** – querying and aggregating spending data
- **Power BI** – dashboard creation and visualization
- **Excel** – quick validation and spot checks
- **Git / GitHub** – version control and project documentation

## Planned Repository Structure
```text
federal-spending-efficiency-analysis/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
├── sql/
├── dashboards/
├── outputs/
├── README.md
└── .gitignore