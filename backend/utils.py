import os
import base64
import pprint
import mimetypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email import message_from_bytes
import pikepdf
import pdfplumber
import json
import re

from logger import setup_logger
logger = setup_logger()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def print_email_summary(message):
    logger.info(f"Enetering print_email_summary()")
    headers = message.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(No Subject)")
    from_ = next((h["value"] for h in headers if h["name"].lower() == "from"), "(Unknown Sender)")

    logger.info(f"Subject: {subject}")
    logger.info(f"From: {from_}")

    payload = message.get("payload", {})
    body_data = None

    # If it's plain text
    if payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data")
        # If multipart (e.g., text + HTML), find the plain text part
    elif payload.get("mimeType", "").startswith("multipart"):
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data")
                break

    if body_data:
        decoded_bytes = base64.urlsafe_b64decode(body_data.encode("UTF-8"))
        logger.info(f"Body:\n {decoded_bytes.decode("utf-8", errors="replace")}")
    else:
        logger.info(f"No plain text body found")

def extract_message_from_query(query):
    logger.info(f"Entering extract_message_from_query() with query: {query}")
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])

    if not messages:
        logger.info(f" NO messages found for query : {query}")
        return
    
    logger.info(f"✅ Found {len(messages)} message(s) for query")
    
    for i, msg_data in enumerate(messages[:3], 1):
        msg_id = msg_data["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

        print(f"🔍 Processing message {i} (ID: {msg_id})")
        print_email_summary(msg)

def save_pdf_from_message(msg, service, output_dir="downloads"):
    logger.info(f"Entering save_pdf_from_message() ...")
    found_pdfs = []
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    def process_part(part):
        filename = part.get("filename")
        body = part.get("body", {})
        if filename and filename.endswith(".pdf"):
            file_data = body.get("data")
            if not file_data and "attachmentId" in body:
                att_id = body["attachmentId"]
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg["id"], id=att_id
                ).execute()
                file_data = att["data"]

            if file_data:
                file_data_decoded = base64.urlsafe_b64decode(file_data)
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.join(output_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(file_data_decoded)
                found_pdfs.append(f"Downloaded: {file_path}")

    if parts:
        for part in parts:
            if part.get("parts"):  # handle nested multiparts
                for subpart in part["parts"]:
                    process_part(subpart)
            else:
                process_part(part)
    else:
        # Handle singlepart email with direct attachment
        process_part(payload)

    logger.info(f"PDFs found : {found_pdfs}")
    logger.info(f"Exitting save_pdf_from_message() ...")
    return found_pdfs


def get_gmail_service():
    
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)
    return service

def search_gmail_with_pdfs(query: str):
    logger.info(f"Entering search_gmail_with_pdfs...")
    query = "from:(estatement@icicibank.com) " + query
    service = get_gmail_service()
    logger.info(f"Search Query : {query} ")
    results = service.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])

    logger.info(f"✅ Found {len(messages)} message(s) for query")

    output = []
    for msg_meta in messages[:1]:
        msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
        #pprint.pprint(msg)
        print_email_summary(msg)
        found = save_pdf_from_message(msg, service)
        output.extend(found)
    
    return output if output else ["No PDFs found"]

def get_password_for_bank(bank):
    config_path = "password_config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError("password_config.json not found.")
    
    with open(config_path) as f:
        config = json.load(f)
    
    bank_info = config.get(bank.upper())
    
    if not bank_info:
        return None
    
    return bank_info["name"][:4].lower() + bank_info["dob"]

def decrypt_with_pikepdf(input_path, output_path, password):
    logger.info(f"Entering decrypt_with_pikepdf() ...")
    try:
        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(output_path)
        return output_path
    except pikepdf._qpdf.PasswordError:
        raise ValueError("Incorrect password or unsupported encryption")
    
def parse_icici_statement(path):
    logger.info(f"Entering parse_icici__statement() ...")
    transactions = []
    last_bal = 0
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            logger.info(f"\n📄 Processing page {page_num + 1}")
            text = page.extract_text()
            
            if not text:
                continue
            lines = text.split("\n")
            logger.info(f"Extracted {len(lines)} lines from page {page_num + 1}")
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Skip header
                if line.startswith("DATE MODE PARTICULARS"):
                    i += 1
                    continue
                # Handle balance forward (e.g., 01-04-2025 B/F 9841.12)
                bf_match = re.match(r"^(\d{2}-\d{2}-\d{4})\s+B/F\s+([\d,]+\.\d{2})$", line)
                if bf_match:
                    transactions.append({
                        "date": bf_match.group(1),
                        "description": "Balance Forward",
                        "amount": 0.0,
                        "balance": float(bf_match.group(2).replace(',', '')),
                        "mode": "B/F",
                        "type": "BALANCE"
                    })
                    last_bal = float(bf_match.group(2).replace(',', ''))
                    i += 1
                    continue

                # Handle UPI transactions
                # Handle generic UPI transaction spread across 3 lines (date in middle)
                upi_txn_match = re.match(
                    r"^(\d{2}-\d{2}-\d{4})\s+(?:(.*?)\s+)?([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
                    line
                    )
                
                if upi_txn_match:
                    date = upi_txn_match.group(1)
                    middle_desc = upi_txn_match.group(2).strip() if upi_txn_match.group(2) else ""
                    amount = float(upi_txn_match.group(3).replace(",", ""))
                    balance = float(upi_txn_match.group(4).replace(",", ""))

                    prev_desc = lines[i - 1].strip() if i - 1 >= 0 else ""
                    next_desc = lines[i + 1].strip() if i + 1 < len(lines) else ""

                    full_description = " ".join([prev_desc, middle_desc, next_desc]).strip()

                    receiver = full_description.split("/")[1]
                    mode = full_description.split("/")[0]

                    # # Heuristic: treat as UPI if 'UPI' is present in the description
                    # mode = "UPI" if "UPI" in full_description.upper() else "SIP" if "ACH" in full_description.upper() else "NEFT" if "NEFT" in full_description.upper() else "UNKNOWN"

                    transactions.append({
                        "date": date,
                        "type": "DEBIT" if last_bal > balance else "CREDIT",
                        "amount": amount,
                        "receiver": receiver,
                        "mode": mode,
                        "balance": balance,
                        "description": full_description
                    })
                    last_bal = balance
                    i += 2  # Skip the next line which we consumed
                    continue

                # Handle NET BANKING transactions
                netbank_match = re.match(
                    r"^(\d{2}-\d{2}-\d{4})NET BANKING\s+(.*?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
                    line
                )   
                if netbank_match:
                    date = netbank_match.group(1)
                    description = netbank_match.group(2).strip()
                    amount = float(netbank_match.group(3).replace(",", ""))
                    balance = float(netbank_match.group(4).replace(",", ""))

                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "mode": "NET BANKING",
                        "type": "DEBIT" if last_bal > balance else "CREDIT"
                    })
                    last_bal = balance
                    i += 1
                    continue

                # Handle MOBILE BANKING transactions
                mobile_match = re.match(
                    r"^(\d{2}-\d{2}-\d{4})MOBILE BANKING\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
                    line
                )
                if mobile_match:
                    date = mobile_match.group(1)
                    description = mobile_match.group(2).strip()
                    amount = float(mobile_match.group(3).replace(",", ""))
                    balance = float(mobile_match.group(4).replace(",", ""))
                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "mode": "MOBILE BANKING",
                        "type": "DEBIT" if last_bal > balance else "CREDIT",
                        "balance": balance
                    })
                    last_bal = balance
                    i += 1
                    continue
                # Handle ICICI DIRECT transactions
                icici_direct_match = re.match(
                    r"^(\d{2}-\d{2}-\d{4})ICICI DIRECT\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$",
                    line
                )   
                if icici_direct_match:
                    date = icici_direct_match.group(1)
                    description = icici_direct_match.group(2).strip()
                    amount = float(icici_direct_match.group(3).replace(",", ""))
                    balance = float(icici_direct_match.group(4).replace(",", ""))
                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount,
                        "mode": "ICICI DIRECT",
                        "type": "DEBIT" if last_bal > balance else "CREDIT",
                        "balance": balance
                    })
                    last_bal = balance
                    i += 1
                    continue
                i += 1

    return transactions



if __name__ == "__main__":
    #extract_message_from_query("from:(estatement@icicibank.com) bank statement")
    search_gmail_with_pdfs("bank statement")
  