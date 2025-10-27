# src/gold.py
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
def create_gold_schema():
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))
        logger.info("Gold schema created")


@timer
def build_dim_customers():
    with engine.begin() as conn:
        # Read Silver Tables
        crm = pd.read_sql("SELECT * FROM silver.crm_cust_info", engine)
        erp_cust = pd.read_sql("SELECT * FROM silver.erp_cust_az12", engine)
        erp_loc = pd.read_sql("SELECT * FROM silver.erp_loc_a101", engine)

        # Merge CRM + ERP info
        df = crm.merge(erp_cust, how="left", left_on="cst_key", right_on="cid", suffixes=("","_erp"))
        df = df.merge(erp_loc, how="left", left_on="cst_key", right_on="cid", suffixes=("","_loc"))

        # Gender fallback
        df["gender"] = df.apply(lambda x: x["cst_gndr"] if x["cst_gndr"]!="n/a" else x["gen"], axis=1)

        # Build final table
        df_gold = pd.DataFrame({
            "customer_key": range(1, len(df)+1),
            "customer_id": df["cst_id"],
            "customer_number": df["cst_key"],
            "first_name": df["cst_firstname"],
            "last_name": df["cst_lastname"],
            "country": df["cntry"],
            "marital_status": df["cst_marital_status"],
            "gender": df["gender"].fillna("n/a"),
            "birthdate": df["bdate"],
            "create_date": df["cst_create_date"]
        })

        df_gold.to_sql("dim_customers", engine, schema="gold", if_exists="replace", index=False)
        logger.info("Gold.dim_customers created")


@timer
def build_dim_products():
    with engine.begin() as conn:
        crm_prd = pd.read_sql("SELECT * FROM silver.crm_prd_info", engine)
        erp_px = pd.read_sql("SELECT * FROM silver.erp_px_cat_g1v2", engine)

        # Merge product info with ERP categories
        df = crm_prd.merge(erp_px, how="left", left_on="cat_id", right_on="id", suffixes=("","_erp"))

        # Only current products (prd_end_dt is NULL)
        df = df[df["prd_end_dt"].isna()]

        df_gold = pd.DataFrame({
            "product_key": range(1, len(df)+1),
            "product_id": df["prd_id"],
            "product_number": df["prd_key"],
            "product_name": df["prd_nm"],
            "category_id": df["cat_id"],
            "category": df["cat"],
            "subcategory": df["subcat"],
            "maintenance": df["maintenance"],
            "cost": df["prd_cost"],
            "product_line": df["prd_line"],
            "start_date": df["prd_start_dt"]
        })

        df_gold.to_sql("dim_products", engine, schema="gold", if_exists="replace", index=False)
        logger.info("Gold.dim_products created")


@timer
def build_fact_sales():
    with engine.begin() as conn:
        sales = pd.read_sql("SELECT * FROM silver.crm_sales_details", engine)
        dim_cust = pd.read_sql("SELECT * FROM gold.dim_customers", engine)
        dim_prd = pd.read_sql("SELECT * FROM gold.dim_products", engine)

        # Merge sales with dimensions
        df = sales.merge(dim_prd, how="left", left_on="sls_prd_key", right_on="product_number")
        df = df.merge(dim_cust, how="left", left_on="sls_cust_id", right_on="customer_id")

        df_gold = pd.DataFrame({
            "order_number": df["sls_ord_num"],
            "product_key": df["product_key"],
            "customer_key": df["customer_key"],
            "order_date": df["sls_order_dt"],
            "shipping_date": df["sls_ship_dt"],
            "due_date": df["sls_due_dt"],
            "sales_amount": df["sls_sales"],
            "quantity": df["sls_quantity"],
            "price": df["sls_price"]
        })

        df_gold.to_sql("fact_sales", engine, schema="gold", if_exists="replace", index=False)
        logger.info("Gold.fact_sales created")


def load_gold():
    create_gold_schema()
    build_dim_customers()
    build_dim_products()
    build_fact_sales()
    logger.info("Gold Layer ETL Completed")
