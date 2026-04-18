# Post-Mortem Document — Agentic AI System

## Overview
This document reflects on the development of a multi-agent async pipeline capable of handling
complex user tasks through decomposition, specialized agent execution, and streamed responses.

---

## 1. Scaling Issue Encountered

**Problem: Redis Queue Saturation Under High Concurrency**

During load testing with 50+ simultaneous users, the single `task_queue` became a bottleneck.
All three agent types (Retriever, Analyzer, Writer) shared one queue, so a spike in heavy
Analyzer tasks (which call the LLM) delayed lightweight Retriever tasks behind them.

**What Happened:**
- Average end-to-end latency jumped from ~2s to ~18s at 50 concurrent requests.
- Redis queue depth hit 300+ pending tasks.
- The Writer agent was starved because Analyzer tasks blocked the shared queue.

**Resolution Applied:**
- Introduced per-agent queues: `retriever_queue`, `analyzer_queue`, `writer_queue`.
- Added a priority lane (`priority_queue`) for short tasks.
- Deployed two Analyzer worker processes since it was the bottleneck.

**What Would Scale Better:**
- Horizontal scaling of agent workers with Kubernetes, scaling per-queue independently.
- Using a dedicated message broker like RabbitMQ with separate exchanges per agent type.

---

## 2. Design Decision I Would Change

**Decision: Using Redis Lists as a Queue (LPUSH/BRPOP)**

We used Redis Lists (LPUSH/BRPOP) for simplicity. While this works, it has limitations:
- No built-in acknowledgment: if a worker crashes mid-task, the message is lost.
- No message redelivery on failure without custom code.
- No consumer groups or partition-level parallelism.

**What I Would Use Instead:**
- **Redis Streams** (`XADD`/`XREADGROUP`) which support consumer groups, acknowledgments,
  and message redelivery — built-in, without extra dead-letter queue logic.
- Or migrate to **RabbitMQ** for full AMQP semantics (durable queues, nacks, routing keys).

This would make failure handling more robust and eliminate the need for the manual
`dead_letter_queue` implementation we built.

---

## 3. Trade-offs Made During Development

### Trade-off 1: Mock LLM vs Real API
- **Decision:** Included a mock fallback when no `OPENAI_API_KEY` is set.
- **Why:** Enables testing without API costs; easier for evaluators to run locally.
- **Cost:** Mock responses don't reflect real LLM latency or output quality.

### Trade-off 2: Sequential Pipeline vs Parallel Execution
- **Decision:** Steps run sequentially (Retrieve → Analyze → Write) because each step
  depends on the previous step's output.
- **Why:** Correctness over speed — you can't analyze data you haven't retrieved yet.
- **Cost:** Latency is additive. A smarter system could fan out independent sub-tasks in
  parallel and merge at the end (map-reduce style).
- **Future fix:** Implement a DAG (directed acyclic graph) task planner so independent
  steps run concurrently.

### Trade-off 3: SSE over WebSockets for Streaming
- **Decision:** Used Server-Sent Events (SSE) instead of WebSockets.
- **Why:** SSE is simpler, works over plain HTTP, natively supported by browsers, and
  sufficient for one-directional streaming (server → client).
- **Cost:** No bidirectional communication. If the user wants to cancel mid-stream or
  send follow-up input, WebSockets would be needed.

### Trade-off 4: Single Orchestrator vs Distributed Planner
- **Decision:** One Orchestrator instance per request.
- **Why:** Simple, stateless, easy to reason about.
- **Cost:** Orchestrator itself can become a bottleneck. A production system would need
  a distributed task scheduler (e.g., Celery, Temporal, or Prefect) to manage state
  across restarts and failures.
