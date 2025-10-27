# src/silver.py
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import DB_CONFIG
from src.utils import setup_logger, timer

logger = setup_logger()

engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

@timer
def create_silver_tables():
    tables = {
        "crm_cust_info": """
            cst_id INT,
            cst_key VARCHAR(50),
            cst_firstname VARCHAR(50),
            cst_lastname VARCHAR(50),
            cst_marital_status VARCHAR(50),
            cst_gndr VARCHAR(50),
            cst_create_date DATE,
            dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """,
        "crm_prd_info": """
            prd_id INT,
            cat_id VARCHAR(50),
            prd_key VARCHAR(50),
            prd_nm VARCHAR(50),
            prd_cost INT,
            prd_line VARCHAR(50),
            prd_start_dt DATE,
            prd_end_dt DATE,
            dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """,
        "crm_sales_details": """
            sls_ord_num VARCHAR(50),
            sls_prd_key VARCHAR(50),
            sls_cust_id INT,
            sls_order_dt DATE,
            sls_ship_dt DATE,
            sls_due_dt DATE,
            sls_sales INT,
            sls_quantity INT,
            sls_price INT,
            dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """,
        "erp_loc_a101": "cid VARCHAR(50), cntry VARCHAR(50), dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "erp_cust_az12": "cid VARCHAR(50), bdate DATE, gen VARCHAR(50), dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "erp_px_cat_g1v2": "id VARCHAR(50), cat VARCHAR(50), subcat VARCHAR(50), maintenance VARCHAR(50), dwh_create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS silver"))
        for table, ddl in tables.items():
            conn.execute(text(f"DROP TABLE IF EXISTS silver.{table}"))
            conn.execute(text(f"CREATE TABLE silver.{table} ({ddl})"))
            logger.info(f"Created table silver.{table}")


@timer
def transform_silver():
    with engine.begin() as conn:
        # --------------------------
        # 1. crm_cust_info
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.crm_cust_info", engine)
        df = df.sort_values("cst_create_date").drop_duplicates(subset="cst_id", keep="last")
        df["cst_firstname"] = df["cst_firstname"].str.strip()
        df["cst_lastname"] = df["cst_lastname"].str.strip()
        df["cst_marital_status"] = df["cst_marital_status"].str.upper().map({"S":"Single","M":"Married"}).fillna("n/a")
        df["cst_gndr"] = df["cst_gndr"].str.upper().map({"F":"Female","M":"Male"}).fillna("n/a")
        df.to_sql("crm_cust_info", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.crm_cust_info")

        # --------------------------
        # 2. crm_prd_info
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.crm_prd_info", engine)
        # Create category id and product key
        df["cat_id"] = df["prd_key"].str[:5].str.replace("-", "_", regex=False)
        df["prd_key"] = df["prd_key"].str[6:]
        df["prd_cost"] = df["prd_cost"].fillna(0)
        df["prd_line"] = df["prd_line"].str.upper().map({
            "M": "Mountain",
            "R": "Road",
            "S": "Other Sales",
            "T": "Touring"
        }).fillna("n/a")
        df["prd_start_dt"] = pd.to_datetime(df["prd_start_dt"], errors="coerce").dt.date
        # Calculate prd_end_dt as day before next start_dt per product
        df = df.sort_values(["prd_key", "prd_start_dt"])
        df["prd_end_dt"] = df.groupby("prd_key")["prd_start_dt"].shift(-1) - pd.Timedelta(days=1)
        df.to_sql("crm_prd_info", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.crm_prd_info")

        # --------------------------
        # 3. crm_sales_details
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.crm_sales_details", engine)
        # Convert dates from int to datetime
        for col in ["sls_order_dt","sls_ship_dt","sls_due_dt"]:
            df[col] = pd.to_datetime(df[col].astype(str), errors="coerce", format="%Y%m%d").dt.date
        # Recalculate sales
        df["sls_sales"] = df.apply(
            lambda row: row["sls_quantity"] * abs(row["sls_price"])
            if pd.isna(row["sls_sales"]) or row["sls_sales"] <=0 or row["sls_sales"] != row["sls_quantity"] * abs(row["sls_price"])
            else row["sls_sales"], axis=1
        )
        # Recalculate price if needed
        df["sls_price"] = df.apply(
            lambda row: row["sls_sales"] / row["sls_quantity"] if pd.isna(row["sls_price"]) or row["sls_price"]<=0 else row["sls_price"], axis=1
        )
        df.to_sql("crm_sales_details", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.crm_sales_details")

        # --------------------------
        # 4. erp_cust_az12
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.erp_cust_az12", engine)
        df["cid"] = df["cid"].apply(lambda x: x[3:] if str(x).startswith("NAS") else x)
        df["bdate"] = pd.to_datetime(df["bdate"], errors="coerce")
        df["bdate"] = df["bdate"].apply(lambda x: x if pd.isna(x) or x <= pd.Timestamp.today() else None)
        df["gen"] = df["gen"].str.upper().map({"F":"Female","FEMALE":"Female","M":"Male","MALE":"Male"}).fillna("n/a")
        df.to_sql("erp_cust_az12", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.erp_cust_az12")

        # --------------------------
        # 5. erp_loc_a101
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.erp_loc_a101", engine)
        df["cid"] = df["cid"].str.replace("-", "")
        df["cntry"] = df["cntry"].replace({"DE":"Germany","US":"United States","USA":"United States"}).fillna("n/a")
        df.to_sql("erp_loc_a101", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.erp_loc_a101")

        # --------------------------
        # 6. erp_px_cat_g1v2
        # --------------------------
        df = pd.read_sql("SELECT * FROM bronze.erp_px_cat_g1v2", engine)
        df.to_sql("erp_px_cat_g1v2", engine, schema="silver", if_exists="replace", index=False)
        logger.info("Transformed silver.erp_px_cat_g1v2")
