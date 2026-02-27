const API_BASE = "/api";

export interface Source {
  source_type: string;
  document: string;
  content: string;
  relevance_score: number;
  metadata: Record<string, unknown>;
}

export interface StreamChunk {
  type: "metadata" | "token" | "done" | "error";
  content?: string;
  strategy?: string;
  sources?: Source[];
}

export interface HealthStatus {
  status: string;
  neo4j_connected: boolean;
  chroma_ready: boolean;
  documents_ingested: number;
}

export interface IngestResult {
  status: string;
  documents_processed: number;
  chunks_created: number;
  graph_nodes_created: number;
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function triggerIngest(): Promise<IngestResult> {
  const res = await fetch(`${API_BASE}/ingest`, { method: "POST" });
  if (!res.ok) throw new Error("Ingestion failed");
  return res.json();
}

export async function* streamChat(message: string): AsyncGenerator<StreamChunk> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) throw new Error("Chat request failed");
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data: ")) {
        try {
          const data = JSON.parse(trimmed.slice(6));
          yield data as StreamChunk;
        } catch {
          // skip malformed chunks
        }
      }
    }
  }
}
