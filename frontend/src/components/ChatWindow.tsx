import { useState, useRef, useEffect } from "react";
import { Send, BookOpen } from "lucide-react";
import MessageBubble, { Message } from "./MessageBubble";
import SourcePanel from "./SourcePanel";
import { streamChat, Source } from "../api/client";

const SAMPLE_QUESTIONS = [
  "What is the average tax rate for corporations in California?",
  "How do I determine my filing status for Form 1040?",
  "What deductions do individuals in Texas typically claim?",
  "What does the Internal Revenue Code say about gross income?",
  "Compare average tax owed by state for partnerships in 2022",
];

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [showSources, setShowSources] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text?: string) {
    const message = text || input.trim();
    if (!message || isLoading) return;

    setInput("");

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
    };

    const assistantMsg: Message = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);

    try {
      let fullContent = "";
      let sources: Source[] = [];
      let strategy = "";

      for await (const chunk of streamChat(message)) {
        if (chunk.type === "metadata") {
          sources = chunk.sources || [];
          strategy = chunk.strategy || "";
          setActiveSources(sources);
          if (sources.length > 0) setShowSources(true);
        } else if (chunk.type === "token" && chunk.content) {
          fullContent += chunk.content;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: fullContent, strategy, sources, isStreaming: true }
                : m
            )
          );
        } else if (chunk.type === "done") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: fullContent, strategy, sources, isStreaming: false }
                : m
            )
          );
        } else if (chunk.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? {
                    ...m,
                    content: `Error: ${chunk.content}`,
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? {
                ...m,
                content: `Connection error. Make sure the backend is running.`,
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-col flex-1">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
                <BookOpen className="text-indigo-500" size={28} />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Ask about tax & financial data
              </h2>
              <p className="text-sm text-gray-500 mb-6 max-w-md">
                Query structured tax records, IRS form instructions, and the Internal Revenue Code.
                Powered by hybrid vector + graph retrieval.
              </p>
              <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
                {SAMPLE_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    className="text-left text-sm px-4 py-2.5 rounded-lg border border-gray-200 text-gray-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <div className="flex items-end gap-3 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about tax data, IRS forms, or regulations..."
                rows={1}
                className="w-full resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-gray-400"
                style={{ minHeight: "44px", maxHeight: "120px" }}
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="p-3 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Source panel */}
      {showSources && (
        <SourcePanel
          sources={activeSources}
          onClose={() => setShowSources(false)}
        />
      )}
    </div>
  );
}
