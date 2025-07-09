from pydantic import BaseModel, Field
from typing import Optional

class QueryInfo(BaseModel):
    intent: Optional[str] = Field(None, description="What is the user trying to do? e.g., get spending, fetch statement")
    bank: Optional[str] = Field(None, description="Bank name such as ICICI, HDFC")
    account_no: Optional[str] = Field(None, description="masked account number, e.g., XXXXXXXX6193")
    month: Optional[str] = Field(None, description="Month related to query, e.g., 'May', 'June', 'last month'")
    year: Optional[str] = Field(None, description="Year of interest, e.g., 2024, 2025")
    date_range: Optional[str] = Field(
        None, 
        description=(
            "Exact date range in format 'dd-mm-yyyy to dd-mm-yyyy'. "
            "If the user mentions a month or year, convert it to the full range. "
            "For example, 'May 2024' becomes '01-05-2024 to 31-05-2024'. "
            "If not mentioned, leave this empty."
        )
    )
    query_hint:Optional[str] = Field(None, description="Gmail search hint or keyword suggestion")
    
    def __str__(self):
        return (
            f"Intent: {self.intent}, Bank: {self.bank}, Account No: {self.account_no}, "
            f"Month: {self.month}, Year: {self.year}, Date Range: {self.date_range} "
            f"Query Hint: {self.query_hint} "
        )