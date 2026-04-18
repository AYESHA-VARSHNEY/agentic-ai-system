import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Abstract base for all specialized agents."""
    
    def __init__(self, name: str, max_retries: int = 3, retry_delay: float = 1.0):
        self.name = name
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Core logic each agent must implement."""
        pass

    async def run_with_retry(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper: retry up to max_retries with exponential backoff."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[{self.name}] Attempt {attempt} for task: {task.get('step_id')}")
                result = await self.execute(task)
                logger.info(f"[{self.name}] Success on attempt {attempt}")
                return {"status": "success", "agent": self.name, "result": result}
            except Exception as e:
                last_error = e
                wait = self.retry_delay * (2 ** (attempt - 1))
                logger.warning(f"[{self.name}] Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                if attempt < self.max_retries:
                    await asyncio.sleep(wait)
        
        logger.error(f"[{self.name}] All {self.max_retries} attempts failed.")
        return {
            "status": "failed",
            "agent": self.name,
            "error": str(last_error),
            "dead_letter": True  # flag for dead-letter queue
        }
