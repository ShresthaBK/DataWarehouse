from src.bronze import create_bronze_tables, load_bronze
from src.silver import create_silver_tables, transform_silver
from src.gold import load_gold  # updated

if __name__ == "__main__":
    print("===== Starting ETL Pipeline =====")
    create_bronze_tables()
    load_bronze()
    create_silver_tables()
    transform_silver()
    load_gold()
    print("===== ETL Pipeline Completed =====")
