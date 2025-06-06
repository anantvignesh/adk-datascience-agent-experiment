"""Load CSV or Excel files in ./data/ into a local SQLite database."""

import os
import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", DATA_DIR / "data.db"))


def load_files_to_sqlite():
    conn = sqlite3.connect(DB_PATH)
    for file in DATA_DIR.iterdir():
        if file.suffix.lower() in {".csv", ".xlsx", ".xls"}:
            table_name = file.stem
            if file.suffix.lower() == ".csv":
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            print(f"Loaded {file.name} into table {table_name}")
    conn.close()


if __name__ == "__main__":
    load_files_to_sqlite()
    print(f"SQLite database created at {DB_PATH}")
