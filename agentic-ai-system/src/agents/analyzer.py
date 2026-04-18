import os
import asyncio
from typing import Any, Dict
from openai import AsyncOpenAI
from .base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    """Analyzes and summarizes retrieved content using LLM."""

    def __init__(self):
        super().__init__(name="AnalyzerAgent")
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        data = task.get("data", "")
        instruction = task.get("instruction", "Summarize this content.")
        
        if not self.client:
            # Fallback mock for demo without API key
            await asyncio.sleep(0.3)
            return {
                "analysis": f"[Mock analysis] Analyzed content: '{str(data)[:100]}...' | Instruction: {instruction}",
                "tokens_used": 0
            }

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise analytical assistant."},
                {"role": "user", "content": f"Instruction: {instruction}\n\nContent:\n{data}"}
            ],
            max_tokens=500
        )
        return {
            "analysis": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }
