import asyncio
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List

from .agents.retriever import RetrieverAgent
from .agents.analyzer import AnalyzerAgent
from .agents.writer import WriterAgent
from .queue.redis_queue import RedisQueue

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Master planner: breaks user task into steps, dispatches to agents,
    collects and aggregates results, handles failures.
    """

    def __init__(self, queue: RedisQueue):
        self.queue = queue
        self.retriever = RetrieverAgent()
        self.analyzer = AnalyzerAgent()
        self.writer = WriterAgent()

    def _decompose_task(self, user_task: str) -> List[Dict[str, Any]]:
        """Break a complex task into sequential steps."""
        task_id = str(uuid.uuid4())[:8]
        return [
            {
                "step_id": f"{task_id}-step-1",
                "type": "retrieve",
                "query": user_task,
                "source": "mock",
            },
            {
                "step_id": f"{task_id}-step-2",
                "type": "analyze",
                "instruction": f"Summarize and extract key insights for: {user_task}",
            },
            {
                "step_id": f"{task_id}-step-3",
                "type": "write",
                "format": "structured paragraphs",
            }
        ]

    async def _run_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single step with the appropriate agent."""
        step_type = step["type"]
        
        if step_type == "retrieve":
            return await self.retriever.run_with_retry(step)
        
        elif step_type == "analyze":
            step["data"] = context.get("retrieved_data", "")
            return await self.analyzer.run_with_retry(step)
        
        elif step_type == "write":
            step["analysis"] = context.get("analysis", "")
            return await self.writer.run_with_retry(step)
        
        else:
            raise ValueError(f"Unknown step type: {step_type}")

    async def run(self, user_task: str) -> AsyncGenerator[str, None]:
        """
        Main async pipeline: orchestrate all steps, stream partial progress,
        yield SSE-friendly text chunks.
        """
        steps = self._decompose_task(user_task)
        context: Dict[str, Any] = {}

        yield f"[Orchestrator] Task received. Decomposed into {len(steps)} steps.\n\n"

        for i, step in enumerate(steps, 1):
            await self.queue.enqueue("task_queue", step)
            yield f"[Step {i}/{len(steps)}] Starting: {step['type'].upper()} agent...\n"

            result = await self._run_step(step, context)

            if result["status"] == "failed":
                await self.queue.enqueue_dead_letter(step)
                yield f"[Step {i}] ❌ Failed after retries. Logged to dead-letter queue.\n"
                yield f"[Step {i}] Error: {result.get('error', 'Unknown error')}\n"
                return

            # Merge results into context for next step
            if step["type"] == "retrieve":
                context.update(result["result"])
                yield f"[Step {i}] ✅ Retrieval complete.\n"
            elif step["type"] == "analyze":
                context.update(result["result"])
                yield f"[Step {i}] ✅ Analysis complete.\n"
            elif step["type"] == "write":
                yield f"\n[Step {i}] ✅ Writing complete. Streaming final response:\n\n"
                # Stream final output word by word
                async for chunk in self.writer.stream_execute(step):
                    yield chunk

        yield "\n\n[Orchestrator] All steps complete."
