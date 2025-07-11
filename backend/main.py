from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
from langchain_ollama import ChatOllama

from graph import build_graph
from logger import setup_logger
import logging
import json
from schemas import QueryInfo
from pprint import pformat

setup_logger()
logger = logging.getLogger(__name__)

# Use Ollama model
# llm = ChatOllama(model="qwen3", temperature=0.7, stream=True)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Change if React runs on another port
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    model: str = "qwen3"
    validated_query: Optional[QueryInfo] = None

# Direct implementation of ollama chat models
@app.post("/ollama")
async def ollama(request: ChatRequest):
    llm = ChatOllama(model=request.model, temperature=0.7)
    messages = [{"role": "user", "content": request.user_message}]

    async def token_stream():
        async for chunk in llm.astream(messages):
            yield chunk.content

    return StreamingResponse(token_stream(), media_type="text/plain")

# Langgraph implementation of chat models
@app.post("/chat-notworking")
async def chat(request: ChatRequest):
    state = {
        "messages": [{"role": "user", "content": request.user_message}]
    }

    graph = build_graph(request.model)

    async def event_stream():
        for chunk in graph.stream(state):
            
            # messages = chunk.get("chatbot")["messages"]
            # msg = chunk.get("messages")[-1]
            # yield msg.content
            # await asyncio.sleep(0)
            node_output = chunk.get("chatbot")
            if node_output and "messages" in node_output:
                last_msg = node_output["messages"][-1]
                yield last_msg.content
                await asyncio.sleep(0)

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.post("/chat")
async def stream_chat(request: ChatRequest):
    logger.info(f"\n{'=' * 60} START RUN {'=' * 60}")
    logger.info(f"***Incoming Request: {request}")
    state = {
        "messages": [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ],
        "validated_query": request.validated_query.model_dump() if request.validated_query else None,
        }
    logger.info(f"created state variable: \n {state}")
    graph = build_graph(request.model)
    final_state = await asyncio.to_thread(graph.invoke, state)
    logger.info(f"=== FINAL STATE ===\n{pformat(final_state)}")
    last_msg = final_state["messages"][-1]
    full_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # serialize validated query
    validated_query_json = ""
    if "validated_query" in final_state and final_state["validated_query"]:
        try:
            if hasattr(final_state["validated_query"], "model_dump"):
                validated_query_json = json.dumps(final_state["validated_query"].model_dump())
            else:
                validated_query_json = json.dumps(final_state["validated_query"])
        except Exception as e:
            logger.warning(f"Failed to encode validaed_query: {e}")
        

    async def response_generator():
        for char in full_response:
            yield char
            await asyncio.sleep(0.01)

        if validated_query_json:
            yield f"<END::validated_query:{validated_query_json}>"

    return StreamingResponse(response_generator(), media_type="text/plain")

if __name__=="__main__":
    logger.info("logging test")