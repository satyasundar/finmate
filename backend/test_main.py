import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_stram_chat():
    # Prepare a simple chat payload matching CHatRequest Schema
    payload = {
        "user_message": "What is the total spending in the month of May 2025",
        #"model": "ollama:qwen3"
        "model": "ollama:llama3.1"
        #"model": "gemini:gemini-2.0-flash"
    }

    response = client.post("/chat", json=payload)
    assert response.status_code == 200

    content = "".join(chunk.decode() for chunk in response.iter_bytes())
    assert content != ""

    print("\nResponse :: ", content)
