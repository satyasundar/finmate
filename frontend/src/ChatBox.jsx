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

// Commenting for now to remove think block for performance issue
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

// New code only to render clean content from AI
// return (
//     <div className="chat-box" ref={chatRef}>
//         {
//             messages.map((msg, i) => {
//                 if (msg.role === "ai") {
//                     const hasThink = /<think>.*?<\/think>/gs.test(msg.content);
//                     const cleaned = msg.content.replace(/<think>.*?<\/think>/gs, "").trim();

//                     // 🧹 If message only contains <think> block, skip rendering
//                     if (hasThink && cleaned.length === 0) {
//                         return null;
//                     }

//                     // ✅ Render only the non-<think> part
//                     return (
//                         <div key={i} className="message ai">
//                             <ReactMarkDown>{cleaned}</ReactMarkDown>
//                         </div>
//                     );
//                 }

//                 // Render all user/system messages
//                 return (
//                     <div key={i} className={`message ${msg.role}`}>
//                         <ReactMarkDown>{msg.content}</ReactMarkDown>
//                     </div>
//                 );
//             })
//         }

//         {loading && messages[messages.length - 1]?.showDots && (
//             <div className="message ai">
//                 <LoadingDots />
//             </div>
//         )}
//     </div>
// );



}
