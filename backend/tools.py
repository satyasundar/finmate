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
def multiply(a: int, b: int) -> int:
    """Multiply 2 numbers a and b
    
    Args:
        a: first int
        b: second int
    """
    return a * b

@tool
def fetch_gmail_pdfs(query: str) -> str:
    """
    Searches Gmail for emails matching a query and fetches any attached PDFs. Return the location of downloaded files.
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
def extract_transactions_tool(path: str) -> list:
    """Parses as ICICI Bank PDF statement and returns a list of transactions"""

    return parse_icici_statement(path)