# 🧱 Python Data Warehouse Project (Pandas + PostgreSQL)

This project demonstrates a complete **data warehouse pipeline** built using **Python, Pandas, and PostgreSQL**. It follows the modern ELT (Extract, Load, Transform) approach, transforming data through **Bronze**, **Silver**, and **Gold** layers — similar to enterprise data lakehouse architectures.  

---

## ⚙️ Overview

The pipeline processes raw CRM and ERP data stored in CSV files, cleans and standardizes them using Pandas, and loads the final analytical models into PostgreSQL. The process is divided into three key layers:

- **Bronze Layer** → Raw data ingestion from CSVs  
- **Silver Layer** → Data cleaning, standardization, and transformations  
- **Gold Layer** → Creation of fact and dimension tables for analytics  

---

## 🧩 Project Structure
python-data-warehouse/

│
├── src/
│ ├── bronze.py # Ingests raw CSV data into PostgreSQL (Bronze layer)
│ ├── silver.py # Cleans and standardizes Bronze data (Silver layer)
│ ├── gold.py # Builds star schema (Gold layer)
│ ├── config.py # Database connection configuration
│ └── utils.py # Logging and performance tracking utilities
│
├── datasets/ # Input raw CSV files
├── logs/ # ETL process logs
├── requirements.txt # Python dependen
cies
└── README.md # Project documentation

---

## 🧰 Setup Guide

###Clone the Repository

>cd python-data-warehouse

>Create and Activate Virtual Environment
>python3 -m venv venv
>source venv/bin/activate

###Install Dependencies
>pip install -r requirements.txt


##Future enahancmenet
Add orchestration using Airflow or Prefect
Automate incremental data loads
Visualize Gold layer using Power BI, Tableau
