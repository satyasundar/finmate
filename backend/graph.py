from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import add, subtract, multiply, devide
from tools import fetch_gmail_pdfs, decrypt_pdf_tool, extract_and_store_transactions_tool
from duckdb_tools import query_duckdb_tool

from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
import pprint
from pprint import pformat
from logger import setup_logger
from datetime import datetime

logger = setup_logger()
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

def build_graph(model: str):
    llm = get_llm(model)
    logger.info(f"Selected Model: {llm}")
    tools = [
        add, subtract, multiply, devide,
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

    # define chatbot node with tool calls
    def chatbot(state: State):
        
        logger.info(f"****** Entering chatbot ...\n")

        messages = [SystemMessage(content= system_msg)]
        messages += state["messages"]
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
    
    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges("chatbot", tools_condition)
    builder.add_edge("tools", "chatbot")

    return builder.compile()

if __name__ == "__main__":
    graph = build_graph("ollama:qwen3")
