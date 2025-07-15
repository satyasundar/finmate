import React, { useState, useEffect, useRef } from "react";
import ChatBox from "./ChatBox";
import "./App.css";

const MODELS = [
  //"ollama:llama3.1",
  //"ollama:deepseek-r1",
  //"ollama:llama3-groq-tool-use",
  //"ollama:gemma3", 
  //"ollama:phi4",
  "gemini:gemini-2.0-flash",
  "gemini:gemini-2.5-flash-preview-05-20",
  "ollama:qwen3"
];
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

function mergeValidateQuery(oldQuery, newQuery) {
  if (!oldQuery) return newQuery;
  if (!newQuery) return oldQuery;
  const merged = {...oldQuery};
  for (const key of Object.keys(newQuery)) {
    if (newQuery[key] !== null && newQuery[key] !== "" && newQuery[key] !== undefined) {
      merged[key] = newQuery[key];
    }
  }
  return merged;
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);
  const [validatedQuery, setValidatedQuery] = useState(null);

  const handleSend = async (messageToSend = input) => {
    if (!messageToSend.trim()) return;

    const userMsg = { role: "user", content: messageToSend };
    // Add user message to local state
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    let aiMsg = { role: "ai", content: "", showDots: true };
    setMessages((prev) => [...prev, aiMsg]);

    // Prepare messages to send (exclude streaming/placeholder ai message)
    const messagesToSend = [...messages, userMsg].filter(
      (msg) => msg.role === "user" || msg.role === "ai"
    ).map(({ role, content }) => ({ role, content }));

    console.log(`Details Sent from frontend: 
      ${ JSON.stringify(messagesToSend) },
      ${selectedModel}, 
      ${validatedQuery}`);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: messagesToSend,
          model: selectedModel,
          validated_query: validatedQuery
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
  
        //intercept for validated_query
        if (chunk.startsWith("<END::validated_query:")) {
          console.log("Raw chunk for validated query: ", chunk);
          //const json = chunk.slice(24, -1);
          const jsonStart = chunk.indexOf("{");
          const jsonEnd = chunk.lastIndexOf("}") + 1;
          const json = chunk.slice(jsonStart, jsonEnd);
          try {
            const parsed = JSON.parse(json)
            //setValidatedQuery(parsed);
            setValidatedQuery(prev => mergeValidateQuery(prev, parsed));
          } catch (e) {
            console.error("Failed to parse validated_query", e);
          }
          
          continue;
        }
  
        filterStream(chunk);
      }

    } catch (err) {
      console.error("Error streaming response", err)
    } finally {
      setLoading(false)
    }
  };

  return (
    <div className={`app-container ${messages.length === 0 ? "initial-view" : ""}`}>
      <header className="app-header">
        <h2>Satya's FinMate</h2>
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
