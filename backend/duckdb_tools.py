import duckdb
import pandas as pd
from langchain.tools import tool
import os
#from logger import setup_logger
import logging

# logger = setup_logger()
logger = logging.getLogger(__name__)

DB_PATH = "finance.db"

def init_duckdb():
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
                    date DATE,
                    description VARCHAR,
                    amount DOUBLE,
                    balance DOUBLE,
                    mode VARCHAR,
                    type VARCHAR,
                    receiver VARCHAR
                )
            """)
    con.close()


def store_transactions_to_duckdb(transactions: list, db_path: str = DB_PATH) -> str:
    """
    Stores parsed transaction data into DuckDB, avoiding duplicate inserts.
    A duplicate is considered as a record with the same date, amount, and description.
    """
    logger.info(f"Entering store_transactions_to_duckdb() with {len(transactions)} transactions and {db_path} database ")
    if not transactions:
        return "No transactions to insert"
    
    df = pd.DataFrame(transactions)
    if df.empty:
        return "Parsed transaction Dataframe is empty"
    
    df["date"] = pd.to_datetime(df["date"])
    
    con = duckdb.connect(db_path)
    #init_duckdb()

    expected_cols = ["date", "description", "amount", "balance", "mode", "type", "receiver", "bank", "account_no"]
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

    return f"Inserted {inserted_count} new transactions out of {before} into DuckDB database. Check the database now."


@tool
def query_duckdb_tool(query: str) -> str:
    """
    Runs a SQL query against the database and returns results. Transactions table holds all the transactions. 
    There are 2 types of transactions in the table, "DEBIT" type and "CREDIT" type.

    Table Details Provided with description of each column:
        Database Name : FINANCE
        Table Name  : TRANSACTIONS
        Table Schema : 
            transactions (
                    date DATE, [date loaded in yyyy-mm-dd format ]
                    description VARCHAR, [Description of transaction in string]
                    amount DOUBLE, [amount either credit or debit]
                    balance DOUBLE, [account balance after each transaction]
                    mode VARCHAR, [mode specifies the mode of transactions like UPI, NET BANKING, MOBILE BANKING etc]
                    type VARCHAR, [type specifies "DEBIT" or "CREDIT" type of transaction]
                    receiver VARCHAR, [receiver tells the recepient name mentioned in the transaction description]
                    bank VARCHAR, [This is bank name from user's query. like 'ICICI', 'HDFC' etc]
                    account_no VARCHAR [This is the account number for which the user querying details]
                )

    """

    logger.info("Entering query_duckdb_tool() ...")
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        results_df = con.execute(query).fetchdf()
        if results_df.empty:
            return "No data found."
        return results_df.to_markdown(index=False)
    except Exception as e:
        return f"Error running query: {e}"
    finally:
        con.close()


if __name__ == "__main__":
    query = """SELECT * FROM TRANSACTIONS"""
    result = query_duckdb_tool(query)
    print(result)