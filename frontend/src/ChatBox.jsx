import React, { useState, useRef, useEffect } from "react";
//import "./ChatBox.css";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  //const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false)
  const chatRef = useRef(null)


  const scrollToBottom = () => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behaviour: "smooth"});
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const DEBUG_MODE = true;
    const userMsg = {role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("")
    //setResponse(""); // Reset response
    setLoading(true)

    const res = await fetch("http://localhost:8000/ollama", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: input }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let aiMsg = { role: "ai", content:"" }
    setMessages((prev) => [...prev, aiMsg]);

    const filterStream = createTagFilteringStreamHandler({
        tagsToFilter: ["think"],
        enabled: !DEBUG_MODE,
        onData: (filteredChunk) => {
          aiMsg.content += filteredChunk;
          setMessages((prev) => [...prev.slice(0, -1), { ...aiMsg }]);
        },
      });

    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      filterStream(chunk)
    }
    setLoading(false)
  };

  return (
    <div className="chat-container">
        <div className="chat-box" ref={chatRef}>
            {
                messages.map(
                    (msg, i) => (
                        <div key={i} className={`message ${msg.role}`}>
                            {msg.content}
                        </div>
                    )
                )
            }
            {loading && <div className="message ai">...</div>}
        </div>
        <div className="input-box">
            <textarea 
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Send a message"
            />
            <button onClick={handleSend} disabled={loading}>
                Send
            </button>
        </div>
    </div>
  );

}

function createTagFilteringStreamHandler({ 
    onData, 
    tagsToFilter = ["think"], 
    enabled = true 
  }) {
    let buffer = "";
    let skipping = false;
    let currentTag = "";
    
    const startTags = tagsToFilter.map(tag => `<${tag}>`);
    const endTags = tagsToFilter.map(tag => `</${tag}>`);
  
    return (chunk) => {
      buffer += chunk;
      let output = "";
  
      while (buffer.length > 0) {
        if (!skipping) {
          const nextStart = startTags
            .map(tag => buffer.indexOf(tag))
            .filter(i => i !== -1)
            .sort((a, b) => a - b)[0];
  
          if (nextStart === 0) {
            const matchedTag = startTags.find(tag => buffer.startsWith(tag));
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
  
      if (output && enabled) {
        onData(output);
      } else if (!enabled) {
        onData(chunk); // raw unfiltered chunk if dev mode
      }
    };
  }
  
