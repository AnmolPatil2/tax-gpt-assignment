import { FileText, Database, X } from "lucide-react";

interface Source {
  source_type: string;
  document: string;
  content: string;
  relevance_score: number;
}

interface SourcePanelProps {
  sources: Source[];
  onClose: () => void;
}

function getIcon(sourceType: string) {
  if (sourceType === "graph_query") return <Database size={14} />;
  return <FileText size={14} />;
}

function getTypeBadge(sourceType: string) {
  const colors: Record<string, string> = {
    csv_row: "bg-blue-50 text-blue-700",
    csv_summary: "bg-blue-50 text-blue-700",
    pdf: "bg-amber-50 text-amber-700",
    ppt: "bg-purple-50 text-purple-700",
    graph_query: "bg-green-50 text-green-700",
  };
  return colors[sourceType] || "bg-gray-50 text-gray-700";
}

export default function SourcePanel({ sources, onClose }: SourcePanelProps) {
  if (sources.length === 0) return null;

  return (
    <div className="w-80 border-l border-gray-200 bg-white overflow-y-auto">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Sources</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      <div className="p-3 space-y-3">
        {sources.map((source, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-gray-400">{getIcon(source.source_type)}</span>
              <span className="text-xs font-medium text-gray-700 truncate flex-1">
                {source.document}
              </span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${getTypeBadge(
                  source.source_type
                )}`}
              >
                {source.source_type.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs text-gray-500 line-clamp-3 leading-relaxed">
              {source.content}
            </p>
            <div className="mt-2 flex items-center justify-between">
              <span className="text-[10px] text-gray-400">
                Relevance: {(source.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
