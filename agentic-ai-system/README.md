# Agentic AI System — Multi-Step Task Pipeline

A production-ready agentic AI system with async pipelines, specialized agents,
Redis message queue, retry handling, and SSE streaming.

## Architecture

```
User → FastAPI Server → Orchestrator → Redis Queue → [Retriever | Analyzer | Writer]
                                                              ↓
                                              Results Aggregator → SSE Stream → User
```

## Tech Stack
- FastAPI + Uvicorn (async web server)
- Redis (message queue, FIFO via LPUSH/BRPOP)
- OpenAI API (LLM inference for Analyzer + Writer)
- SSE (Server-Sent Events for streaming)
- Docker + Docker Compose

## Quick Start

### Option A — Without Docker (local dev)

```bash
# 1. Clone and enter project
git clone <your-repo-url>
cd agentic-ai-system

# 2. Create virtual env
python -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (optional — mock works without it)

# 5. Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 6. Start the server
uvicorn src.server:app --reload --port 8000
```

### Option B — Full Docker

```bash
cp .env.example .env   # Add your API key if you have one
docker-compose up --build
```

## API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### Run a Task (streaming)
```bash
curl -N -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Research the benefits of async programming and write a summary"}'
```

### Queue Status
```bash
curl http://localhost:8000/queue/status
```

## API Docs
Visit: http://localhost:8000/docs

## Agents

| Agent | Role | Queue |
|-------|------|-------|
| RetrieverAgent | Fetches external data | retriever_queue |
| AnalyzerAgent | LLM-based analysis | analyzer_queue |
| WriterAgent | Final text generation + streaming | writer_queue |

## Failure Handling
- Each agent retries up to 3 times with exponential backoff
- Failed tasks are pushed to `dead_letter_queue` in Redis
- Inspect dead letters: `redis-cli lrange dead_letter_queue 0 -1`

## Project Structure
```
src/
├── server.py          # FastAPI app, SSE endpoints
├── orchestrator.py    # Task decomposition + pipeline
├── agents/
│   ├── base_agent.py  # Retry logic base class
│   ├── retriever.py   # Data fetching
│   ├── analyzer.py    # LLM analysis
│   └── writer.py      # Text generation + streaming
└── queue/
    └── redis_queue.py # Async Redis wrapper
```

## Testing Without API Key
The system works in mock mode automatically — no API key required for demo.
