import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .orchestrator import Orchestrator
from .queue.redis_queue import RedisQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

redis_queue = RedisQueue(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_queue.connect()
    yield
    await redis_queue.disconnect()

app = FastAPI(
    title="Agentic AI System",
    description="Multi-agent async pipeline with streaming",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskRequest(BaseModel):
    task: str

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentic-ai-system"}

@app.post("/run")
async def run_task(req: TaskRequest):
    """
    Accept a complex task and stream back partial results via SSE.
    Frontend: use EventSource or fetch with ReadableStream.
    """
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty.")

    orchestrator = Orchestrator(queue=redis_queue)

    async def event_stream():
        async for chunk in orchestrator.run(req.task):
            # SSE format: data: <text>\n\n
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/queue/status")
async def queue_status():
    length = await redis_queue.get_queue_length("task_queue")
    dead = await redis_queue.get_queue_length("dead_letter_queue")
    return {"task_queue": length, "dead_letter_queue": dead}
