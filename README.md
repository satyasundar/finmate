# FinMate: Fullstack AI Financial Assistant

FinMate is a full-stack AI-powered financial assistant that helps users interactively manage and query their personal finances. It leverages advanced language models (Ollama, Gemini) to answer queries, fetch and process bank statements, and provide actionable insights—all through a modern chat interface.

---

## Logs
- To see the logs for existing run you can see the file **[backend.log](./backend/backend.log)**


## Features
- **Conversational AI:** Chat with an AI assistant about your finances.
- **Multi-Model Support:** Switch between Gemini and Ollama LLMs.
- **Automated Data Extraction:** Fetches bank statements from Gmail, decrypts PDFs, and extracts transactions.
- **Database Integration:** Stores and queries financial data using DuckDB.
- **Streaming Responses:** Real-time, streaming chat experience.
- **Interactive UI:** Modern React-based chat interface with markdown support and collapsible AI 'thinking' blocks.

---

## Tech Stack
- **Frontend:** React, Vite, react-markdown
- **Backend:** FastAPI, LangChain, LangGraph, Ollama, Gemini, DuckDB
- **Other:** Gmail API (for statement fetching), PDF parsing tools

---

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) Ollama and Gemini API access

### Backend Setup
1. Navigate to the `backend/` folder:
   ```bash
   cd backend
   ```
2. Install dependencies (add your requirements to `requirements.txt`):
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend/` folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## Usage
- Open your browser at [http://localhost:5173](http://localhost:5173)
- Start chatting with the AI assistant about your finances!
- Select your preferred LLM model from the dropdown.

---

## Folder Structure
```
fullstack-AI/
  backend/      # FastAPI backend, LangGraph, tools, database
  frontend/     # React frontend, chat UI
  finance.db    # DuckDB database file
```

---

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## License
[MIT](LICENSE)
