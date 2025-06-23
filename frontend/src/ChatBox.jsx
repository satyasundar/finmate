import React, { useState, useRef, useEffect } from "react";
import ReactMarkDown from "react-markdown";
import "./ChatBox.css";

const Collapsible = ({ title, children }) => {
    const [isOpen, setIsOpen] = useState(true);

    const toggleOpen = () => {
        setIsOpen(!isOpen);
    };

    return (
        <div className="collapsible">
            <button onClick={toggleOpen} className="collapsible-toggle">
                {isOpen ? "[-]" : "[+]"} {title}
            </button>
            {isOpen && <div className="collapsible-content">{children}</div>}
        </div>
    )
};

const LoadingDots = () => (
    <div className="loading-dots">
        <span />
        <span />
        <span />
    </div>
);

export default function ChatBox({ messages, loading }) {
  const chatRef = useRef(null)


  const scrollToBottom = () => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behaviour: "smooth"});
  };

  useEffect(scrollToBottom, [messages]);

  return (
    <div className="chat-box" ref={chatRef}>
        {
            messages.map(
                (msg, i) => {
                    if (msg.role === "ai" && msg.content.includes("<think>")) {
                        return (
                            <React.Fragment key={i}>
                                {msg.content
                                    .split(/(<think>.*?<\/think>)/gs)
                                    .filter(Boolean)
                                    .map((section, j) => {
                                        if (section.startsWith("<think>")) {
                                            const thinkContent = section.replace(/<\/?think>/g, "");
                                            return (
                                                <div key={`${i}-${j}`} className="message think">
                                                    <Collapsible title="Thinking...">
                                                      <em>{thinkContent}</em>
                                                    </Collapsible>
                                                </div>
                                            );
                                        } else {
                                            return (
                                                <div key={`${i}-${j}`} className="message ai">
                                                    <ReactMarkDown>{section}</ReactMarkDown>
                                                </div>
                                            );
                                        }
                                    })}
                            </React.Fragment>
                        )
                    } else {
                        return (
                            <div key={i} className={`message ${msg.role}`}>
                                <ReactMarkDown>{msg.content}</ReactMarkDown>
                            </div>
                        )
                    }
                }
            )
        }
        {loading && messages[messages.length-1]?.showDots && (
            <div className="message ai">
                <LoadingDots />
            </div>
        )}
    </div>
  );

}
