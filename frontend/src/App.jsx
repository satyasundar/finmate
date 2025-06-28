import React, { useState, useEffect, useRef } from "react";
import ChatBox from "./ChatBox";
import "./App.css";

const MODELS = ["ollama:qwen3", "ollama:gemma3",  "ollama:llama3.1", "gemini:gemini-2.0-flash","gemini:gemini-2.5-flash-preview-05-20"];
const DEBUG_MODE = true;

function createTagFilteringStreamHandler({
  onData,
  tagsToFilter = ["think"],
  enabled = true,
}) {
  if (!enabled) {
    return (chunk) => {
      onData(chunk);
    };
  }
  let buffer = "";
  let skipping = false;
  let currentTag = "";

  const startTags = tagsToFilter.map((tag) => `<${tag}>`);
  const endTags = tagsToFilter.map((tag) => `</${tag}>`);

  return (chunk) => {
    buffer += chunk;
    let output = "";

    while (buffer.length > 0) {
      if (!skipping) {
        const nextStart = startTags
          .map((tag) => buffer.indexOf(tag))
          .filter((i) => i !== -1)
          .sort((a, b) => a - b)[0];

        if (nextStart === 0) {
          const matchedTag = startTags.find((tag) => buffer.startsWith(tag));
          currentTag = matchedTag;
          skipping = true;
          buffer = buffer.slice(matchedTag.length);
          continue;
        }

        if (nextStart > 0) {
          output += buffer.slice(0, nextStart);
          buffer = buffer.slice(nextStart);
          continue;
        }

        output += buffer;
        buffer = "";
      } else {
        const closingTag = `</${currentTag.slice(1)}`; // e.g., </think>
        const endIdx = buffer.indexOf(closingTag);
        if (endIdx === -1) {
          buffer = ""; // Still in hidden block, discard buffer
          return;
        } else {
          buffer = buffer.slice(endIdx + closingTag.length);
          skipping = false;
          currentTag = "";
        }
      }
    }

    if (output) {
      onData(output);
    }
  };
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);

  const handleSend = async (messageToSend = input) => {
    if (!messageToSend.trim()) return;

    const userMsg = { role: "user", content: messageToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    let aiMsg = { role: "ai", content: "", showDots: true };
    setMessages((prev) => [...prev, aiMsg]);

    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_message: messageToSend,
        model: selectedModel,
      }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

   

    const filterStream = createTagFilteringStreamHandler({
      tagsToFilter: ["think"],
      enabled: !DEBUG_MODE,
      onData: (filteredChunk) => {
        if (filteredChunk.trim()) {
          aiMsg.showDots = false;
        }
        aiMsg.content += filteredChunk;
        setMessages((prev) => [...prev.slice(0, -1), { ...aiMsg }]);
      },
    });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      filterStream(chunk);
    }
    setLoading(false);
  };

  return (
    <div className={`app-container ${messages.length === 0 ? "initial-view" : ""}`}>
      <header className="app-header">
        <h2>Satya Nayak's Assistant</h2>
        <div className="model-selector">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {MODELS.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>
      </header>
      <ChatBox
        messages={messages}
        loading={loading}
      />
      <div className="input-box">
            <textarea 
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Send a message"
                disabled={loading}
            />
            <button onClick={() => handleSend()} disabled={loading}>
                Send
            </button>
        </div>
    </div>
  );
}

export default App;
