import os
import asyncio
from typing import Any, Dict, AsyncGenerator
from openai import AsyncOpenAI
from .base_agent import BaseAgent

class WriterAgent(BaseAgent):
    """Generates final formatted output, supports streaming."""

    def __init__(self):
        super().__init__(name="WriterAgent")
        api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        analysis = task.get("analysis", "")
        format_hint = task.get("format", "paragraph")

        if not self.client:
            await asyncio.sleep(0.4)
            return {
                "final_text": f"[Mock output] Here is a well-written response based on: "
                              f"'{str(analysis)[:80]}...' formatted as {format_hint}.",
                "streamed": False
            }

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a skilled writer. Output format: {format_hint}."},
                {"role": "user", "content": f"Write a final response based on:\n{analysis}"}
            ],
            max_tokens=800
        )
        return {
            "final_text": response.choices[0].message.content,
            "streamed": False
        }

    async def stream_execute(self, task: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streaming version: yields chunks as they arrive."""
        analysis = task.get("analysis", "")
        format_hint = task.get("format", "paragraph")

        if not self.client:
            mock_text = f"Here is a detailed response based on the analysis provided. " \
                        f"The key findings are summarized and formatted as {format_hint}."
            for word in mock_text.split():
                yield word + " "
                await asyncio.sleep(0.05)
            return

        stream = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a skilled writer. Output format: {format_hint}."},
                {"role": "user", "content": f"Write a final response based on:\n{analysis}"}
            ],
            max_tokens=800,
            stream=True
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
