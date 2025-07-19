import asyncio
import json
import logging
from typing import Dict, Set, AsyncGenerator, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubSubManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.PubSub] = None
        self.subscriptions: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

    async def connect(self):
        """连接Redis并初始化发布订阅"""
        self.redis = aioredis.from_url(
            self.redis_url, 
            encoding="utf-8", 
            decode_responses=True
        )
        self.pubsub = self.redis.pubsub()
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_messages())

    async def disconnect(self):
        """断开Redis连接"""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                logger.info("Message dispatch task cancelled")
        
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        logger.info("Redis connections closed")

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """订阅频道并返回消息队列"""
        async with self._lock:
            queue = asyncio.Queue(maxsize=100)
            
            if channel not in self.subscriptions:
                self.subscriptions[channel] = set()
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to new channel: {channel}")
            
            self.subscriptions[channel].add(queue)
            logger.info(f"New subscriber on channel: {channel}. Total: {len(self.subscriptions[channel])}")
            return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """取消订阅频道"""
        async with self._lock:
            if channel in self.subscriptions:
                self.subscriptions[channel].discard(queue)
                
                if not self.subscriptions[channel]:
                    del self.subscriptions[channel]
                    await self.pubsub.unsubscribe(channel)
                    logger.info(f"Unsubscribed from channel: {channel}")

    async def publish(self, channel: str, message: dict):
        """发布消息到指定频道"""
        if not self.redis:
            raise RuntimeError("Redis connection not established")
            
        await self.redis.publish(channel, json.dumps(message))
        logger.info(f"Published message to {channel}: {message}")

    async def _dispatch_messages(self):
        """分发从Redis接收的消息到所有订阅者"""
        while self._running:
            try:
                # 如果没有活跃订阅，短暂休眠
                if not self.subscriptions:
                    await asyncio.sleep(1)
                    continue
                
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message is not None:
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode message: {message['data']}")
                        continue
                    
                    if channel in self.subscriptions:
                        for queue in list(self.subscriptions[channel]):
                            try:
                                # 非阻塞方式放入队列
                                queue.put_nowait(data)
                            except asyncio.QueueFull:
                                logger.warning(f"Queue full for channel {channel}. Dropping message.")
            
            except asyncio.CancelledError:
                logger.info("Message dispatch task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in message dispatch: {e}")
                await asyncio.sleep(1)  # 防止错误循环

class NotificationService:
    def __init__(self, pubsub_manager: PubSubManager):
        self.pubsub_manager = pubsub_manager

    async def event_generator(
        self, request: Request, channel: str
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """生成SSE事件流"""
        queue = await self.pubsub_manager.subscribe(channel)
        try:
            while True:
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    logger.info("Client disconnected")
                    break
                
                try:
                    # 等待消息或超时
                    message = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield ServerSentEvent(
                        event="message",
                        data=json.dumps(message),
                        retry=3000  # 客户端重连时间(ms)
                    )
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ServerSentEvent(event="ping", data="")
                
        except asyncio.CancelledError:
            logger.info("Connection cancelled by client")
        finally:
            await self.pubsub_manager.unsubscribe(channel, queue)
            logger.info(f"Unsubscribed from channel: {channel}")

# 消息模型
class MessageModel(BaseModel):
    event_type: str
    data: dict
    timestamp: Optional[float] = None

# FastAPI 应用初始化
app = FastAPI()
pubsub_manager = PubSubManager()
notification_service = NotificationService(pubsub_manager)

@app.on_event("startup")
async def startup_event():
    await pubsub_manager.connect()
    logger.info("PubSub service started")

@app.on_event("shutdown")
async def shutdown_event():
    await pubsub_manager.disconnect()
    logger.info("PubSub service stopped")

@app.get("/sse/{channel}")
async def sse_endpoint(request: Request, channel: str):
    """SSE事件流端点"""
    return EventSourceResponse(
        notification_service.event_generator(request, channel),
        ping=15,  # 自动发送ping事件的间隔（秒）
        ping_message_factory=lambda: ServerSentEvent(event="ping", data="")
    )

@app.post("/publish/{channel}")
async def publish_message(channel: str, message: MessageModel):
    """发布消息到指定频道"""
    # 添加时间戳
    message.timestamp = asyncio.get_event_loop().time()
    await pubsub_manager.publish(channel, message.dict())
    return {"status": "success", "channel": channel}

# 健康检查端点
@app.get("/health")
async def health_check():
    """服务健康检查"""
    return {
        "status": "ok",
        "redis_connected": pubsub_manager.redis is not None and await pubsub_manager.redis.ping(),
        "subscriptions": len(pubsub_manager.subscriptions)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)