# TaxGPT Financial Chatbot

A RAG-powered chatbot that answers financial and tax questions using **hybrid vector + graph retrieval** across structured tax data, IRS form instructions, and the Internal Revenue Code.

**Author**: Anmol Patil | [LinkedIn](https://www.linkedin.com/in/anmol-patil-96a478194/) 

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────────────────┐
│  React Frontend │────▶│       FastAPI Backend             │
│  (Chat UI)      │◀────│                                  │
└─────────────────┘     │  ┌────────────────────────────┐  │
                        │  │     Query Router (LLM)     │  │
                        │  └──────┬──────────┬──────────┘  │
                        │         │          │             │
                        │    ┌────▼───┐ ┌────▼─────┐      │
                        │    │ Vector │ │  Graph   │      │
                        │    │ Search │ │  Search  │      │
                        │    │ChromaDB│ │  Neo4j   │      │
                        │    └────┬───┘ └────┬─────┘      │
                        │         └─────┬────┘             │
                        │         ┌─────▼─────┐           │
                        │         │  GPT-4o   │           │
                        │         │ Generator │           │
                        │         └───────────┘           │
                        └──────────────────────────────────┘
```

The system combines two complementary retrieval strategies:

- **Vector Search (ChromaDB)**: Semantic similarity search across all document chunks — tax records, IRS form instructions, IRC sections, and financial presentations.
- **Graph Search (Neo4j)**: Structured knowledge graph over the tax dataset, enabling precise Cypher queries for aggregations, comparisons, and relationship traversal.

A **Query Router** (powered by GPT-4o-mini) classifies each user question into one of three retrieval paths: `structured` (graph-primary), `semantic` (vector-primary), or `hybrid` (both). This ensures each question is answered using the most appropriate retrieval strategy.

## Design Rationale

### Why Hybrid Retrieval?

Pure vector search struggles with precise numerical queries ("average tax rate for corporations in TX"), while pure graph queries can't handle open-ended conceptual questions ("how do I file Schedule C?"). The hybrid approach uses the right tool for each question type.

### Why Neo4j for Structured Data?

The CSV tax dataset has natural relational structure — taxpayer types, states, income sources, and deduction types are all interconnected. Modeling these as a knowledge graph allows:

- Aggregation queries via Cypher (average, sum, count, comparisons)
- Relationship traversal ("which income sources do partnerships in NY use?")
- Pattern discovery across multiple dimensions

An LLM generates Cypher queries from natural language, with the schema provided as context.

### Graph Schema

```
(:Transaction) -[:FILED_BY]-> (:TaxpayerType)
               -[:IN_STATE]-> (:State)
               -[:INCOME_FROM]-> (:IncomeSource)
               -[:CLAIMED_DEDUCTION]-> (:DeductionType)
               -[:IN_YEAR]-> (:TaxYear)

(:Document) -[:CONTAINS]-> (:Section)
```

### Chunking Strategy

| Source | Strategy | Details |
|--------|----------|---------|
| CSV (5,000 rows) | Row-level + aggregates | Each row becomes a vector chunk AND a graph node. Aggregate summaries per (TaxpayerType, State) are also embedded. |
| PDFs (7,000+ pages) | Page-based, 1000-token chunks | 200-token overlap preserves context across chunk boundaries. Section metadata retained for citations. |
| PPT (old .ppt format) | Slide-level | Multi-strategy extraction: python-pptx → OLE binary parsing → raw text extraction. |

### Streaming Responses

The chat endpoint uses Server-Sent Events (SSE) to stream GPT-4o's response token-by-token, providing a responsive user experience.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| LLM | OpenAI GPT-4o |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (embedded) |
| Graph DB | Neo4j 5.x Community |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Infrastructure | Docker Compose |

## Quick Start (Recommended)

```bash
git clone git@github.com:AnmolPatil2/tax-gpt-assignment.git
cd tax-gpt-assignment

# Set your OpenAI API key, then run setup
export OPENAI_API_KEY=sk-your-key-here
./setup.sh
```

The setup script checks prerequisites, installs dependencies, starts Neo4j, and prints the commands to launch the app. See below for manual setup.

> **Pre-built embeddings**: The repo includes `backend/chroma_data/` (via Git LFS) with 16,920 pre-computed vector embeddings. On first ingestion, the pipeline detects these and skips re-embedding — saving ~$0.50 in API costs and ~20 minutes of processing time.

## Manual Setup

### Prerequisites

- Docker and Docker Compose (for Neo4j)
- Node.js 18+ and npm
- Python 3.9+
- OpenAI API key

### 1. Clone and configure

```bash
git clone git@github.com:AnmolPatil2/tax-gpt-assignment.git
cd tax-gpt-assignment

# Set your OpenAI API key
cp backend/.env.example backend/.env
# Edit backend/.env and add your OPENAI_API_KEY
```

### 2. Start Neo4j

```bash
docker compose up neo4j -d
# Wait for Neo4j to be healthy (~15 seconds)
```

### 3. Start the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 4. Ingest the data

```bash
# With the backend running, trigger ingestion:
curl -X POST http://localhost:8000/api/ingest
```

This processes all CSV, PDF, and PPT files, populating both ChromaDB and Neo4j.
If pre-built embeddings are present in `backend/chroma_data/`, vector ingestion is skipped automatically. Only Neo4j graph data is loaded (~30 seconds).
If starting fresh (no chroma_data), full ingestion takes ~20 minutes depending on API rate limits.

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### Alternative: Docker Compose (all-in-one)

```bash
# Set your API key
export OPENAI_API_KEY=sk-your-key-here

# Start everything
docker compose up --build
```

## Usage

1. **Click "Ingest Data"** in the header to process all datasets (first time only).
2. **Ask questions** in the chat interface. Try the sample questions or ask your own.
3. **View sources** in the right panel to see which documents and graph queries were used.

### Example Questions

| Type | Example |
|------|---------|
| Structured | "What is the average tax rate for corporations in California?" |
| Structured | "Compare total tax owed by state for partnerships in 2022" |
| Semantic | "How do I determine my filing status for Form 1040?" |
| Semantic | "What does the Internal Revenue Code say about gross income?" |
| Hybrid | "What deductions do individuals in CA typically claim and how do they work?" |

## Testing

### Unit tests

```bash
cd backend
pytest tests/test_ingestion.py tests/test_retrieval.py -v
```

### Evaluation (requires running backend with ingested data)

```bash
cd backend
pytest tests/test_evaluation.py -v -s
```

The evaluation suite runs 15 test queries spanning structured, semantic, hybrid, and edge cases. It uses GPT-4o as a judge (LLM-as-judge pattern) to score each answer on relevance, accuracy, completeness, and clarity (1-5 scale).

## Project Structure

```
taxgpt-chatbot/
├── setup.sh                        # One-command setup script
├── docker-compose.yml              # Neo4j + backend + frontend
├── README.md
├── data/                           # Dataset files (CSV, PDF, PPT)
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings (env vars)
│   │   ├── api/
│   │   │   ├── routes.py           # /chat, /ingest, /health
│   │   │   └── schemas.py          # Pydantic models
│   │   ├── ingestion/
│   │   │   ├── pipeline.py         # Orchestrates all loaders
│   │   │   ├── csv_loader.py       # CSV → graph + vectors
│   │   │   ├── pdf_loader.py       # PDF → chunks → vectors
│   │   │   └── ppt_loader.py       # PPT text extraction → vectors
│   │   ├── retrieval/
│   │   │   ├── hybrid.py           # Merges vector + graph results
│   │   │   ├── query_router.py     # LLM-based query classification
│   │   │   ├── vector_store.py     # ChromaDB operations
│   │   │   └── graph_store.py      # Neo4j Cypher queries
│   │   └── llm/
│   │       ├── client.py           # OpenAI client wrapper
│   │       └── prompts.py          # All prompt templates
│   ├── chroma_data/                # Pre-built embeddings (Git LFS)
│   ├── tests/                      # Unit + integration tests
│   ├── evaluation/                 # Evaluation dataset (test_queries.json)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.tsx                  # Main app with health polling
    │   ├── components/              # Chat UI components
    │   └── api/client.ts            # SSE streaming client
    ├── package.json
    └── Dockerfile
```
