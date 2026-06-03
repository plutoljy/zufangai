"""
WebSocket 连接管理器
"""
import asyncio
import json
import time
from typing import Dict, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class ConnectionRateLimiter:
    """连接频率限制器"""

    def __init__(self):
        self.connection_attempts: Dict[str, list[float]] = {}
        self.max_attempts_per_minute = 10

    def check_rate_limit(self, user_id: str) -> bool:
        """检查连接频率"""
        now = time.time()
        attempts = self.connection_attempts.get(user_id, [])
        # 清理1分钟前的记录
        attempts = [t for t in attempts if now - t < 60]
        if len(attempts) >= self.max_attempts_per_minute:
            return False
        attempts.append(now)
        self.connection_attempts[user_id] = attempts
        return True


class ChatWebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_pool_size = 10000
        self.heartbeat_interval = 30
        self.message_queue = asyncio.Queue(maxsize=100000)
        self.rate_limiter = ConnectionRateLimiter()
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> bool:
        """建立WebSocket连接"""
        try:
            # 检查连接池是否已满
            if len(self.active_connections) >= self.connection_pool_size:
                logger.warning(f"连接池已满，拒绝用户 {user_id} 的连接")
                await websocket.close(code=1008, reason="连接池已满")
                return False

            # 检查频率限制
            if not self.rate_limiter.check_rate_limit(user_id):
                logger.warning(f"用户 {user_id} 连接频率超限")
                await websocket.close(code=1008, reason="连接频率超限")
                return False

            # 接受连接
            await websocket.accept()

            # 如果用户已有连接，关闭旧连接
            if user_id in self.active_connections:
                old_ws = self.active_connections[user_id]
                try:
                    await old_ws.close()
                except Exception as e:
                    logger.error(f"关闭旧连接失败: {e}")

            # 加入连接池
            self.active_connections[user_id] = websocket

            # 启动心跳
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(user_id))
            self._heartbeat_tasks[user_id] = heartbeat_task

            logger.info(f"用户 {user_id} 已连接，当前连接数: {len(self.active_connections)}")

            # 发送欢迎消息
            await self.send_message(user_id, {
                "type": "system",
                "data": {
                    "message": "连接成功",
                    "user_id": user_id,
                    "timestamp": time.time()
                }
            })

            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def disconnect(self, user_id: str):
        """断开连接"""
        try:
            # 取消心跳任务
            if user_id in self._heartbeat_tasks:
                self._heartbeat_tasks[user_id].cancel()
                del self._heartbeat_tasks[user_id]

            # 从连接池移除
            if user_id in self.active_connections:
                ws = self.active_connections[user_id]
                try:
                    await ws.close()
                except Exception:
                    pass
                del self.active_connections[user_id]

            logger.info(f"用户 {user_id} 已断开连接，当前连接数: {len(self.active_connections)}")

        except Exception as e:
            logger.error(f"断开连接失败: {e}")

    async def send_message(self, user_id: str, message: Dict) -> bool:
        """发送消息给指定用户"""
        try:
            if user_id not in self.active_connections:
                logger.warning(f"用户 {user_id} 不在线，无法发送消息")
                return False

            ws = self.active_connections[user_id]
            await ws.send_json(message)
            return True

        except WebSocketDisconnect:
            logger.warning(f"用户 {user_id} 连接已断开")
            await self.disconnect(user_id)
            return False
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: Dict,
        exclude_user: Optional[str] = None
    ):
        """广播消息到会话的所有参与者"""
        # 这里需要从数据库查询会话参与者
        # 暂时简化实现
        pass

    async def _heartbeat_loop(self, user_id: str):
        """心跳循环"""
        try:
            while user_id in self.active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_message(user_id, {
                    "type": "heartbeat",
                    "data": {"timestamp": time.time()}
                })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳循环异常: {e}")
            await self.disconnect(user_id)

    def is_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections

    def get_online_count(self) -> int:
        """获取在线用户数"""
        return len(self.active_connections)


# 全局WebSocket管理器实例
ws_manager = ChatWebSocketManager()
