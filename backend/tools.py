from langchain.tools import tool
from utils import search_gmail_with_pdfs, decrypt_with_pikepdf, parse_icici_statement, get_password_for_bank

@tool
def add(a: int, b: int) -> int:
    """Adds 2 integers a and b and retruns their sum
    
    Args:
        a: first int
        b: second int
    """
    return a + b

@tool
def subtract(a: int, b: int) -> int:
    """Subtract 2 integers a and b and retruns result
    
    Args:
        a: first int
        b: second int
    """
    return a - b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply 2 numbers a and b
    
    Args:
        a: first int
        b: second int
    """
    return a * b

@tool
def devide(a: int, b: int) -> int:
    """Devide 2 numbers a and b
    
    Args:
        a: first integer
        b: second integer
    """

    return a / b

@tool
def fetch_gmail_pdfs(query: str) -> str:
    """
    Search Gmail for emails with bank statements and fetch any attached PDFs. Return the locations of downloaded files.
    """
    try:
        print("Entering fetch_gmail_pdfs ...")
        results = search_gmail_with_pdfs(query)
        return "\n\n".join(results)
    except Exception as e:
        return f"Error fetching emails: {e}"

@tool
def decrypt_pdf_tool(path: str, bank: str = "ICICI") -> str:
    """
    Decrypt a password-protected bank statement PDF using known password format.
    Currently supportly ICICI.
    """
    password = get_password_for_bank(bank)
    if not password:
        return f"No password config found for bank: {bank}"
    decrypted_path = path.replace(".pdf","_decrypted.pdf")
    try:
        return decrypt_with_pikepdf(path, decrypted_path, password)
    except ValueError:
        return f"Failed to decrypt PDF with known password at {path}"

@tool
def extract_and_store_transactions_tool(path: str) -> list:
    """Takes the location of decrypted PDFs and parses them for retrieving the transactions. 
    Finally store the list of transactions into DuckDB database."""

    return parse_icici_statement(path)