import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import ChatWindow from "./components/ChatWindow";
import { checkHealth, triggerIngest } from "./api/client";

interface StatusInfo {
  neo4j: boolean;
  chroma: boolean;
  docs: number;
}

export default function App() {
  const [status, setStatus] = useState<StatusInfo | null>(null);
  const [isIngesting, setIsIngesting] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const health = await checkHealth();
      setStatus({
        neo4j: health.neo4j_connected,
        chroma: health.chroma_ready,
        docs: health.documents_ingested,
      });
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  async function handleIngest() {
    setIsIngesting(true);
    try {
      await triggerIngest();
      await fetchHealth();
    } catch (err) {
      console.error("Ingestion failed:", err);
    } finally {
      setIsIngesting(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header status={status} onIngest={handleIngest} isIngesting={isIngesting} />
      <ChatWindow />
    </div>
  );
}
