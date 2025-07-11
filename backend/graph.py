from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import add, subtract, multiply, devide
from tools import fetch_gmail_pdfs, decrypt_pdf_tool, extract_and_store_transactions_tool
from duckdb_tools import query_duckdb_tool
from schemas import QueryInfo

from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
import pprint
from pprint import pformat
#from logger import setup_logger
from datetime import datetime
from calendar import monthrange
import json
import logging

#logger = setup_logger()
logger = logging.getLogger(__name__)
today = datetime.today()

system_msg = f"""
You are a financial assistant. Today's date is {today.strftime('%Y-%m-%d')}. This date is in yyyy-mm-dd format. You can use this to reason time-based queries.
You can do following to answer queries.
- From user input message derive the query terms to find the relevant data.
- Relevant data may be there in DuckDB database. Check first.
- If it is not there in database, pull it from Gmail.
- Fetch bank statements from Gmail and download the attahment
- Extract and store transactions in database
Always create a plan and follow through, using tools as needed.
"""

# system_msg = f"""
# You are a financial assistant. Today's date is {today.strftime('%Y-%m-%d')}.
# You have access to the following tools: fetch_gmail_pdfs, decrypt_pdf_tool, extract_and_store_transactions_tool, query_duckdb_tool.
# Always use the available tools to answer the user's question. Do not just describe a plan—actually call the tools as needed to get the answer.
# If you need to fetch data, use the tools. Only answer directly if you are 100% sure you do not need to use a tool.
# """
tool_descriptions = """
Available tools:
- fetch_gmail_pdfs: Fetches bank statement PDFs from Gmail.
- decrypt_pdf_tool: Decrypts a PDF file.
- extract_and_store_transactions_tool: Extracts transactions from a PDF and stores them in the database.
- query_duckdb_tool: Queries the DuckDB database for financial data.
"""

schema_support_prompt = SystemMessage(content=(
    "You are a query extractor for a finance assistant. "
    "Your job is to extract a structured object from the user query that matches the following schema:\n\n"
    f"{json.dumps(QueryInfo.model_json_schema(), indent=2)}\n\n"
    "Only respond with a valid JSON object."
))

# {QueryInfo.schema_json(indent=2)}
#{json.dumps(QueryInfo.model_json_schema(), indent=2)}

# system_msg = f"""
# You are a helpful math assistant. You can answer queries about math.
# """




def get_llm(model: str):
    if model.startswith("ollama:"):
        model_name = model.split(":",1)[1]
        return ChatOllama(model=model_name, temperature=0.7, streaming=True)
    elif model.startswith("gemini:"):
        model_name = model.split(":", 1)[1]
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.7)
    else:
        raise ValueError(f"Unsupported model: {model}")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    plan: Optional[str]
    validated_query: Optional[QueryInfo]
    file_paths: Optional[str]
    transactions: Optional[list]
    db_result: Optional[str]
    confirmed: Optional[bool]
    awaiting_confirmation: Optional[bool]


def build_graph(model: str):
    llm = get_llm(model)
    logger.info(f"Selected Model: {llm}")
    llm_qry_schema = llm.with_structured_output(QueryInfo)
    tools = [
        #add, subtract, multiply, devide,
        fetch_gmail_pdfs,
        decrypt_pdf_tool,
        extract_and_store_transactions_tool,
        query_duckdb_tool
        ]
    llm_with_tools = llm.bind_tools(tools)
    #Define chatbot node
    # def chatbot(state: State):
    #     return {"messages": [llm.invoke(state["messages"])]}

    import re
    def extract_think_blocks(text):
        blocks = re.findall(r"<think>.*?</think>", text, re.DOTALL)
        return "\n".join(blocks) + "\n" if blocks else ""
    
    def planning_node(state):
        logger.info(f"1.Planning Node entered...")
        user_msg = state["messages"][-1].content
        #logger.info(f"User Msg: {user_msg} ")
        plan = (
            "<plan>\n"
            "1. Understand the user's intent from the query.\n"
            "2. Check DuckDB for relevant finance data.\n"
            "3. If not found, fetch bank statements from Gmail.\n"
            "4. Decrypt and extract transactions.\n"
            "5. Store in database if needed.\n"
            "6. Generate final answer using all context.\n"
            "</plan>"
        )

        gmail_hint = "subject:ICICI Bank Statement from dd-mm-yyyy to dd-mm-yyyy"
        
        existing_vq = state.get("validated_query")
        merged_query = {
            **(existing_vq if existing_vq else {}),
            #"query_hint": gmail_hint
        }
        logger.info(f"Before returning from Planning Node...\n Existing VQ:: {merged_query}")
        return {
            "plan": plan,
            "validated_query": QueryInfo(**merged_query),
            "messages": [AIMessage(content=plan)] + state["messages"],
            "confirmed": False
        }

    def validate_query_node(state):
        logger.info(f"2.Validation Node entered...")
        #logger.info(f"Current state at the beginning of Validation Node \n{state}\n")
        #user_message = state["messages"][-1]
        user_message = next(msg for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage))
        #logger.info(f"User Msg: {user_message.content}")
        #logger.info(f"Plan: {state["plan"]}")
        try:
            
            parsed = llm_qry_schema.invoke([schema_support_prompt, user_message])
            
            previous = state.get("validated_query", {})
            
            if isinstance(previous, QueryInfo):
                previous = previous.model_dump()
                logger.info(f"Existing vq : {previous}")
            merged = parsed.model_dump()
            logger.info(f"vq after - new parsed message from user: {merged}")

            for key, val in previous.items():
                if merged.get(key) in (None,"") and val:
                    merged[key] = val
            if merged.get("month") and not merged.get("year"):
                merged["year"] = str(datetime.today().year)
            final_query = QueryInfo(**merged)
            logger.info(f"Merged final_query: {final_query}")

            # if final_query.month and final_query.year and not final_query.date_range:
            #     try:
            #         months = {m.lower(): i for i, m in enumerate([
            #             "", "January", "February", "March", "April", "May", "June",
            #             "July", "August", "September", "October", "November", "December"
            #         ])}
            #         month_num = months[final_query.month.strip().lower()]
            #         year = int(final_query.year)
            #         last_day = monthrange(year, month_num)[1]
            #         start = f"01-{month_num:02d}-{year}"
            #         end = f"{last_day:02d}-{month_num:02d}-{year}"
            #         final_query.date_range = f"{start} to {end}"
            #     except Exception as e:
            #         logger.warning(f"Failed to infer date_range: {e}")

            if not final_query.bank or not final_query.month or not final_query.account_no:
                logger.warning("Missing required fields: bank or month or account_no")
                return {
                    "validated_query": final_query,
                    "messages": state["messages"] + [
                        AIMessage(content="Please provide missing details like bank, month, and account number.")
                    ]
                }
            
            #summary = f"✅ Got it! Here's what I know:\n{final_query}"
            summary = "✅ Got it! Here's what I know:\n"
            summary += "\n".join(f"{key}: {value}" for key, value in final_query.model_dump().items())

            return {
                "validated_query": final_query,
                "confirmed":False,
                "awaiting_confirmation": True,
                "messages": state["messages"] + [AIMessage(content=summary + "\n\nDo you want to proceed ?")]
                }
        
        except Exception as e:
            logger.warning(f"Validaion failed: {e}")
            return {
                "validated_query": state.get("validated_query"),
                "messages": state["messages"] + [AIMessage(content="❌ I couldn't understand your query, please rephrase it")]
            }

    def clarify_node(state):
        logger.info("🔁 Clarify Node: Asking user to fill missing fields.")
        logger.info(f"Current state at start of Clarify Node \n{state}\n")
        #logger.info(f"Clarify received validated_query: {state.get('validated_query')}")

        missing = []
        if "validated_query" in state and state["validated_query"] is not None:
            q = state["validated_query"]
            logger.info(f"q from state: {q}")
            if not q.bank:
                missing.append("bank")
            if not q.month:
                missing.append("month")
            if not q.account_no:
                missing.append("account_number")
        
        if not missing:
            logger.info(f"not coming here")
            missing = ["bank", "month", "account_number"]
        
        question = " To proceed, could you specify your " + " and ".join(missing) + "?"
        return {
            "messages": state["messages"] + [AIMessage(content=question)],
            "validated_query": state.get("validated_query")
        }

    def routing_logic(state):
        logger.info("Start routing logic")
        #logger.info(f"Current state at Routing Logic \n{state}\n")
        if state.get("__end__", False):
            return END
        q = state["validated_query"]
        if not q:
            logger.info("No validated_query found — clarifying.")
            return "clarify"
        if isinstance(q, QueryInfo):
            q = q.model_dump()
        missing = [k for k in ("bank", "month", "account_no") if not q.get(k)]
        logger.info(f"Validated Query Check: {q} — Missing: {missing}")

        

        if missing:
            return "clarify"
        if state.get("confirmed", False):
            logger.info(f"✅ Confirmed. Proceeding.")
            return "chatbot"
        if state.get("awaiting_confirmation", False):
            logger.info("Awaiting user confirmation.")
            return "confirm"
        
        logger.info("Unexpected state. Going to clarify.")
        return "clarify"
    
    # def chatbot_entry(state):
    #     if state.get("confirmed"):
    #         return "dummy"
    #     else:
    #         return "dummy"

    
    def dummy_node(state):
        logger.info("Reached Dummy Node")
        return {
            "messages": state["messages"] + [AIMessage(content="This is a Dummy node after confrimation. This is to be replaced by chatbot node")]
        }
    
    def confirm_node(state):
        logger.info("Confirm node start...")
        user_msg = next((m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None)
        logger.info(f"user's last message: {user_msg}")
        
        content = user_msg.content.strip().lower()
        if any(x in content for x in ["yes", "okay", "sure", "go ahead", "confirm", "proceed"]):
            return {
                **state,
                "confirmed": True,
                "awaiting_confirmation": False,
                "messages": state["messages"] + [AIMessage(content="✅ Great! Proceeding now...")]
            }
        elif any(x in content for x in ["no", "cancel", "stop"]):
            return {
                **state,
                "confirmed": False,
                "awaiting_confirmation": False,
                "messages": state["messages"] + [AIMessage(content="❌ Okay. Stopped. Ask me anything else.")]
            }
        
        #return END
        return {
            **state,
            #"messages": state["messages"] + [AIMessage(content="❓ Please confirm with 'yes' or 'no'.")],
            "messages": state["messages"],
            "__end__": True
        }
        
        # return {
        #     "messages": state["messages"] + [AIMessage(content="This is a confirmation node")]
        # }
        
     # define chatbot node with tool calls
    def chatbot(state: State):
        
        logger.info(f"****** Entering chatbot ...\n")

        messages = [SystemMessage(content=system_msg)]
        messages += state["messages"]
   
        refined_query = state["validated_query"]
        if refined_query:
            reformulated = (
                f"User intends to ask: "
                f"{refined_query.intent} for {refined_query.bank} account {refined_query.account_no} "
                f"in {refined_query.month} {refined_query.year}"
            )
            messages.append(SystemMessage(content=reformulated))
        # if refined_query:
        #     user_msg = f"What is my total spending for {refined_query.bank} account {refined_query.account_no} in {refined_query.month} {refined_query.year}?"
        #     messages.append(HumanMessage(content=user_msg))

        logger.info(f"Input Message Starts {'-' * 60} \n{pformat(messages)}\n Input Message End {'-' * 60}")
        #logger.info([msg.content for msg in messages])
        result = llm_with_tools.invoke(messages)
        #result = llm.invoke(messages)
        logger.info(f"AI Response Starts here {'-' * 60 } \n{pformat(result)}\n {'-' * 60}")

        reasoning = ""

        # to add all reasoinings together and show in final result
        for msg in state["messages"]:
            if isinstance(msg, AIMessage) and "<think>" in msg.content:
                thinking_blocks = extract_think_blocks(msg.content)
                reasoning += thinking_blocks
            
        result.content = reasoning + "\n" + result.content

        return {"messages": state["messages"] + [result] }
    
    builder = StateGraph(State)
    
    # builder.add_node("chatbot", chatbot)
    # builder.add_node("tools", ToolNode(tools))
    # builder.add_edge(START, "chatbot")
    # builder.add_conditional_edges("chatbot", tools_condition)
    # builder.add_edge("tools", "chatbot")

    builder.add_node("planning", planning_node)
    builder.add_node("validate", validate_query_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("confirm", confirm_node)
    builder.add_node("dummy", dummy_node)
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "planning")
    builder.add_edge("planning", "validate")
    builder.add_conditional_edges("validate", routing_logic)
    builder.add_conditional_edges("confirm", routing_logic)

    #builder.add_edge(START, "chatbot")
    builder.add_conditional_edges("chatbot", tools_condition)
    builder.add_edge("tools", "chatbot")

    
    
    return builder.compile()

if __name__ == "__main__":
    #graph = build_graph("ollama:qwen3")
    logger.info("logging test in graph.py")
