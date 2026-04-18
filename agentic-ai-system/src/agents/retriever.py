import httpx
from typing import Any, Dict
from .base_agent import BaseAgent

class RetrieverAgent(BaseAgent):
    """Fetches external data: web search, APIs, documents."""

    def __init__(self):
        super().__init__(name="RetrieverAgent")

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        query = task.get("query", "")
        source = task.get("source", "mock")

        if source == "mock":
            # Simulated retrieval (replace with real search API call)
            await __import__("asyncio").sleep(0.5)  # simulate network delay
            return {
                "retrieved_data": f"[Retrieved data for: '{query}'] "
                                  f"This is simulated content from an external source.",
                "source": "mock",
                "query": query
            }
        
        # Real HTTP retrieval example
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://api.example.com/search?q={query}")
            response.raise_for_status()
            return {"retrieved_data": response.json(), "source": source, "query": query}
