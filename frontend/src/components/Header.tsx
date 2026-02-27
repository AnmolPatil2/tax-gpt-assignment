import { Database, Activity } from "lucide-react";

interface HeaderProps {
  status: {
    neo4j: boolean;
    chroma: boolean;
    docs: number;
  } | null;
  onIngest: () => void;
  isIngesting: boolean;
}

export default function Header({ status, onIngest, isIngesting }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">T</span>
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">TaxGPT</h1>
          <p className="text-xs text-gray-500">Financial Chatbot</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {status && (
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Database size={12} />
              <span
                className={
                  status.neo4j ? "text-green-600" : "text-red-500"
                }
              >
                Neo4j {status.neo4j ? "OK" : "Down"}
              </span>
            </span>
            <span className="flex items-center gap-1">
              <Activity size={12} />
              <span
                className={
                  status.chroma ? "text-green-600" : "text-red-500"
                }
              >
                {status.docs.toLocaleString()} docs
              </span>
            </span>
          </div>
        )}

        <button
          onClick={onIngest}
          disabled={isIngesting}
          className="px-3 py-1.5 text-xs font-medium rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isIngesting ? "Ingesting..." : "Ingest Data"}
        </button>
      </div>
    </header>
  );
}
