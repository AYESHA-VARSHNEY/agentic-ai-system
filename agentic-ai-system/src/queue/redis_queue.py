import json
import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class RedisQueue:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self._client = None
        self._available = False

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}",
                decode_responses=True,
                socket_connect_timeout=2
            )
            await self._client.ping()
            self._available = True
            logger.info("Redis connected.")
        except Exception as e:
            self._available = False
            logger.warning(f"Redis not available, running in mock mode: {e}")

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def enqueue(self, queue_name: str, task: Dict[str, Any]):
        if not self._available:
            logger.debug(f"[Mock Queue] Enqueued: {task.get('step_id')}")
            return
        await self._client.lpush(queue_name, json.dumps(task))

    async def dequeue(self, queue_name: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        result = await self._client.brpop(queue_name, timeout=timeout)
        if result:
            _, payload = result
            return json.loads(payload)
        return None

    async def enqueue_dead_letter(self, task: Dict[str, Any]):
        if not self._available:
            logger.error(f"[Mock Dead Letter] Task failed: {task.get('step_id')}")
            return
        await self._client.lpush("dead_letter_queue", json.dumps(task))

    async def publish(self, channel: str, message: Dict[str, Any]):
        if not self._available:
            return
        await self._client.publish(channel, json.dumps(message))

    async def get_queue_length(self, queue_name: str) -> int:
        if not self._available:
            return 0
        return await self._client.llen(queue_name)