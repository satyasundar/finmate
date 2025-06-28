import duckdb
import pandas as pd
from langchain.tools import tool
import os
from logger import setup_logger

logger = setup_logger()

DB_PATH = "finance.db"

def init_duckdb():
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
                    date VARCHAR,
                    description VARCHAR,
                    amount DOUBLE,
                    balance DOUBLE,
                    mode VARCHAR,
                    type VARCHAR,
                    receiver VARCHAR
                )
            """)
    con.close()

@tool
def store_transactions_to_duckdb(transactions: list, db_path: str = DB_PATH) -> str:
    """
    Stores parsed transaction data into DuckDB, avoiding duplicate inserts.
    A duplicate is considered as a record with the same date, amount, and description.
    """
    logger.info(f"Entering store_transactions_to_duckdb() with {transactions} and {db_path} ")
    if not transactions:
        return "No transactions to insert"
    
    df = pd.DataFrame(transactions)
    if df.empty:
        return "Parsed transaction Dataframe is empty"
    
    con = duckdb.connect(db_path)
    init_duckdb()

    expected_cols = ["date", "description", "amount", "balance", "mode", "type", "receiver"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    #Avoid inserting duplicates (based on date, amount, description)
    existing = con.execute("SELECT date, amount, description FROM transactions").fetchdf()
    before = len(df)
    if not existing.empty:
        df = df.merge(existing, how="left", indicator=True, on=["date", "amount", "description"])
        df = df[df["_merge"] == "left_only"]
        df = df.drop(columns=["_merge"])

    inserted_count = len(df)
    if inserted_count > 0:
        con.register("new_txns", df)
        con.execute("INSERT INTO transactions SELECT * FROM new_txns")
    
    con.close()

    return f"Inserted {inserted_count} new transactions out of {before}."


@tool
def query_duckdb_tool(query: str, db_path: str = DB_PATH) -> str:
    """Runs a SQL query against the DuckDB database and returns results."""

    logger.info("Entering queey_duckdb_tool() ...")
    con = duckdb.connect(db_path)
    try:
        results_df = con.execute(query).fetchdf()
        if results_df.emppty:
            return "No data found."
        return results_df.to_markdown(index=False)
    except Exception as e:
        return f"Error running query: {e}"
    finally:
        con.close()
