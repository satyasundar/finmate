from pydantic import BaseModel, Field
from typing import Optional

class QueryInfo(BaseModel):
    intent: Optional[str] = Field(None, description="What is the user trying to do? e.g., get spending details, fetch statement")
    bank: Optional[str] = Field(None, description="Bank name such as ICICI, HDFC")
    account_no: Optional[str] = Field(None, description="account number converted to masked account number, e.g., XXXXXXXX6193, XXXXXXXX6110")
    month: Optional[str] = Field(None, description="Month related to query, e.g., 'May', 'June'")
    year: Optional[str] = Field(None, description="Year of interest, e.g., 2024, 2025")
    date_range: Optional[str] = Field(
        None, 
        description=(
            "Exact date range in format 'dd-mm-yyyy to dd-mm-yyyy'. "
            "If the user mentions a month or year, convert it to the full range. "
            "For example, 'May 2025' becomes '01-05-2025 to 31-05-2025'. "
            "If user has not mentioned any the year, it should be current year. For example, 'May' becomes '01-05-2025 to 31-05-2025'"
            "If user mentions multiple months, for example 'May and June' becomes ''01-05-2025 to 30-06-2025''"
            "If not mentioned, leave this empty."
        )
    )
    query_hint:Optional[str] = Field(None, description=(
        "Extract gmail search query from user's input in the exact format."
        "The format of the query is 'subject:ICICI Bank Statement from {start_date} to {end_date} for {account_no}'"
        "Here start_date and end_date is to be replaced with dated from user's input of date range"
        "account_no is to be replaced from user's input."
        "For example, 'subject:ICICI Bank Statement from 01-06-2025 to 30-06-2025 for XXXXXXXX6193', 'subject:ICICI Bank Statement from 01-06-2025 to 30-06-2025 for XXXXXXXX9469'"
        )
    )
    def __str__(self):
        return (
            f"Intent: {self.intent}, Bank: {self.bank}, Account No: {self.account_no}, "
            f"Month: {self.month}, Year: {self.year}, Date Range: {self.date_range} "
            f"Query Hint: {self.query_hint} "
        )