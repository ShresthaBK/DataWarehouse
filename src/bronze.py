# src/bronze.py
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import DB_CONFIG
from src.utils import setup_logger, timer

logger = setup_logger()

# Database engine
engine = create_engine(
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# CSV file paths
CSV_FILES = {
    "crm_cust_info": "datasets/source_crm/cust_info.csv",
    "crm_prd_info": "datasets/source_crm/prd_info.csv",
    "crm_sales_details": "datasets/source_crm/sales_details.csv",
    "erp_loc_a101": "datasets/source_erp/loc_a101.csv",
    "erp_cust_az12": "datasets/source_erp/cust_az12.csv",
    "erp_px_cat_g1v2": "datasets/source_erp/px_cat_g1v2.csv"
}

# Bronze Table Definitions
BRONZE_TABLES = {
    "crm_cust_info": """
        cst_id INT,
        cst_key VARCHAR(50),
        cst_firstname VARCHAR(50),
        cst_lastname VARCHAR(50),
        cst_marital_status VARCHAR(50),
        cst_gndr VARCHAR(50),
        cst_create_date DATE
    """,
    "crm_prd_info": """
        prd_id INT,
        prd_key VARCHAR(50),
        prd_nm VARCHAR(50),
        prd_cost INT,
        prd_line VARCHAR(50),
        prd_start_dt DATE,
        prd_end_dt DATE
    """,
    "crm_sales_details": """
        sls_ord_num VARCHAR(50),
        sls_prd_key VARCHAR(50),
        sls_cust_id INT,
        sls_order_dt VARCHAR(50),
        sls_ship_dt VARCHAR(50),
        sls_due_dt VARCHAR(50),
        sls_sales INT,
        sls_quantity INT,
        sls_price INT
    """,
    "erp_loc_a101": "cid VARCHAR(50), cntry VARCHAR(50)",
    "erp_cust_az12": "cid VARCHAR(50), bdate DATE, gen VARCHAR(50)",
    "erp_px_cat_g1v2": "id VARCHAR(50), cat VARCHAR(50), subcat VARCHAR(50), maintenance VARCHAR(50)"
}

@timer
def create_bronze_tables():
    """Create bronze schema and tables."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))
        for table, ddl in BRONZE_TABLES.items():
            conn.execute(text(f"DROP TABLE IF EXISTS bronze.{table}"))
            conn.execute(text(f"CREATE TABLE bronze.{table} ({ddl})"))
            logger.info(f"Created table bronze.{table}")
            print(f"Created table bronze.{table}")
@timer
def load_bronze():
    """Load CSVs into bronze tables in the database."""
    for table, path in CSV_FILES.items():
        try:
            print(f"Loading {table} from {path} into database...")
            df_iter = pd.read_csv(path, chunksize=1000)  # chunking for large files
            total_rows = 0

            for chunk in df_iter:
                chunk.to_sql(
                    table,
                    engine,
                    schema='bronze',
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                total_rows += len(chunk)
                print(f"Inserted {total_rows} rows...", end="\r")

            print(f"\n{table} inserted successfully ({total_rows} rows)")
            logger.info(f"Loaded CSV into bronze.{table} ({total_rows} rows)")

        except Exception as e:
            logger.error(f"Failed to load {table}: {e}")
            print(f"Error loading {table}: {e}")


# @timer
# def load_bronze(print_only=True):
#     """Load CSVs into bronze tables OR print to console if print_only=True."""
#     for table, path in CSV_FILES.items():
#         try:
#             print(f"\nLoading {table} from {path}...")
#             df_iter = pd.read_csv(path, chunksize=1000)
#             total_rows = 0

#             for chunk in df_iter:
#                 total_rows += len(chunk)
#                 if print_only:
#                     print(f"\n--- {table} Chunk ({len(chunk)} rows) ---")
#                     print(chunk.head(5))  # print first 5 rows of each chunk
#                     print("...")
#                 else:
#                     # Normal database insert
#                     chunk.to_sql(
#                         table,
#                         engine,
#                         schema='bronze',
#                         if_exists='append',
#                         index=False,
#                         method='multi'
#                     )
#                 print(f"Processed {total_rows} rows...", end="\r")

#             print(f"\n{table} finished processing ({total_rows} rows)")

#         except Exception as e:
#             logger.error(f"Failed to load {table}: {e}")
#             print(f"Error loading {table}: {e}")
