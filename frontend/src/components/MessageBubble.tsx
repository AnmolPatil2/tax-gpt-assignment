import ReactMarkdown from "react-markdown";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    source_type: string;
    document: string;
    content: string;
    relevance_score: number;
  }>;
  strategy?: string;
  isStreaming?: boolean;
}

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] ${
          isUser
            ? "bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-3"
            : "bg-white border border-gray-200 rounded-2xl rounded-bl-md px-5 py-4 shadow-sm"
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm text-gray-800 leading-relaxed">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-indigo-500 animate-pulse ml-0.5 align-text-bottom rounded-sm" />
            )}
          </div>
        )}

        {!isUser && message.strategy && (
          <div className="mt-3 pt-2 border-t border-gray-100">
            <span className="inline-block text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              {message.strategy} retrieval
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
