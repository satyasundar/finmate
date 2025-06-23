from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(model: str):
    if model.startswith("ollama:"):
        model_name = model.split(":",1)[1]
        return ChatOllama(model=model_name, temperature=0.7, streaming=True)
    elif model.startswith("gemini:"):
        model_name = model.split(":", 1)[1]
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.7, streaming=True)
    else:
        raise ValueError(f"Unsupported model: {model}")

class State(TypedDict):
    messages: Annotated[list, add_messages]

def build_graph(model: str):
    llm = get_llm(model)

    builder = StateGraph(State)

    #Define chatbot node
    def chatbot(state: State):
        return {"messages": [llm.invoke(state["messages"])]}
    
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")

    return builder.compile()
