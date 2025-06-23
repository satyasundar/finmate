from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
from langchain_ollama import ChatOllama

from graph import build_graph

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


class ChatRequest(BaseModel):
    user_message: str
    model: str = "qwen3"

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
    state = {"messages": [{"role": "user", "content": request.user_message}]}
    graph = build_graph(request.model)
    final_state = await asyncio.to_thread(graph.invoke, state)
    last_msg = final_state["messages"][-1]
    full_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    async def response_generator():
        for char in full_response:
            yield char
            await asyncio.sleep(0.01)

    return StreamingResponse(response_generator(), media_type="text/plain")