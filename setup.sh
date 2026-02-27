#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() { echo -e "\n${BLUE}[$1/${TOTAL_STEPS}]${NC} $2"; }
print_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_err()  { echo -e "  ${RED}✗${NC} $1"; }

TOTAL_STEPS=6
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  TaxGPT Financial Chatbot — Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Step 1: Check prerequisites ──────────────────────────────────────
print_step 1 "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 && print_ok "Python 3 found: $(python3 --version 2>&1)" || { print_err "Python 3 not found. Install Python 3.9+"; exit 1; }
command -v node    >/dev/null 2>&1 && print_ok "Node.js found: $(node --version)"           || { print_err "Node.js not found. Install Node 18+"; exit 1; }
command -v npm     >/dev/null 2>&1 && print_ok "npm found: $(npm --version)"                 || { print_err "npm not found"; exit 1; }
command -v docker  >/dev/null 2>&1 && print_ok "Docker found: $(docker --version 2>&1 | head -1)" || print_warn "Docker not found — Neo4j must be running manually"

# ── Step 2: OpenAI API Key ───────────────────────────────────────────
print_step 2 "Configuring environment..."

if [ ! -f backend/.env ]; then
    if [ -n "$OPENAI_API_KEY" ]; then
        cat > backend/.env <<EOF
OPENAI_API_KEY=$OPENAI_API_KEY
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=taxgpt2024
EOF
        print_ok "Created backend/.env from \$OPENAI_API_KEY"
    else
        cp backend/.env.example backend/.env
        print_warn "Created backend/.env from template — edit it and add your OPENAI_API_KEY"
        echo -e "    ${YELLOW}→ nano backend/.env${NC}"
    fi
else
    print_ok "backend/.env already exists"
fi

# ── Step 3: Start Neo4j ──────────────────────────────────────────────
print_step 3 "Starting Neo4j..."

if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j; then
        print_ok "Neo4j container already running"
    else
        docker compose up neo4j -d 2>/dev/null || docker-compose up neo4j -d 2>/dev/null || { print_warn "Could not start Neo4j via Docker. Start it manually."; }
        print_ok "Neo4j starting (may take ~15s to be ready)"
        echo -e "    Waiting for Neo4j to be healthy..."
        for i in $(seq 1 30); do
            if docker exec "$(docker ps -q --filter ancestor=neo4j:5-community 2>/dev/null | head -1)" cypher-shell -u neo4j -p taxgpt2024 'RETURN 1' >/dev/null 2>&1; then
                print_ok "Neo4j is ready"
                break
            fi
            sleep 2
        done
    fi
else
    print_warn "Docker not available. Make sure Neo4j is running on bolt://localhost:7687"
fi

# ── Step 4: Backend setup ────────────────────────────────────────────
print_step 4 "Setting up backend..."

cd "$PROJECT_DIR/backend"

if [ ! -d venv ]; then
    python3 -m venv venv
    print_ok "Created Python virtual environment"
fi

source venv/bin/activate
pip install -q -r requirements.txt
print_ok "Python dependencies installed"

cd "$PROJECT_DIR"

# ── Step 5: Frontend setup ───────────────────────────────────────────
print_step 5 "Setting up frontend..."

cd "$PROJECT_DIR/frontend"
npm install --silent 2>/dev/null
print_ok "Frontend dependencies installed"

cd "$PROJECT_DIR"

# ── Step 6: Done ─────────────────────────────────────────────────────
print_step 6 "Setup complete!"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Ready to go! Start the application:${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BLUE}Terminal 1 — Backend:${NC}"
echo -e "    cd backend && source venv/bin/activate"
echo -e "    uvicorn app.main:app --reload --port 8000"
echo ""
echo -e "  ${BLUE}Terminal 2 — Ingest data (first time only):${NC}"
echo -e "    curl -X POST http://localhost:8000/api/ingest"
echo ""
echo -e "  ${BLUE}Terminal 3 — Frontend:${NC}"
echo -e "    cd frontend && npm run dev"
echo ""
echo -e "  Then open ${BLUE}http://localhost:3000${NC} in your browser."
echo ""
echo -e "  ${YELLOW}Pre-built embeddings:${NC} If chroma_data/ was pulled from the repo,"
echo -e "  ingestion will detect existing vectors and skip re-embedding."
echo ""
