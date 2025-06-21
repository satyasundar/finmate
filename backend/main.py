from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
from langchain_ollama import ChatOllama

# Use Ollama model
llm = ChatOllama(model="qwen3", temperature=0.7, stream=True)

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

@app.post("/ollama")
async def ollama(request: ChatRequest):
    messages = [{"role": "user", "content": request.user_message}]

    async def token_stream():
        for chunk in llm.stream(messages):
            yield chunk.content
            await asyncio.sleep(0)  # No delay for true streaming

    return StreamingResponse(token_stream(), media_type="text/plain")
