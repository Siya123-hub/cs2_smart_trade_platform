# -*- coding: utf-8 -*-
"""
WebSocket API 端点
提供实时双向通信支持
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional, List
import json
import logging
from datetime import datetime

from app.services.notification_service import ws_manager, notification_service, NotificationType
from app.core.security import get_current_user
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器（简化的连接状态）"""
    
    @staticmethod
    async def keep_alive(websocket: WebSocket):
        """保持连接活跃"""
        try:
            while True:
                # 发送ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                # 等待pong
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                    if data.get("type") == "pong":
                        continue
                except asyncio.TimeoutError:
                    break
        except Exception:
            pass
    
    @staticmethod
    async def handle_client_message(websocket: WebSocket, message: dict, current_user: User):
        """处理客户端消息"""
        msg_type = message.get("type")
        
        if msg_type == "ping":
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        elif msg_type == "subscribe":
            # 订阅主题
            topic = message.get("topic")
            logger.info(f"User {current_user.id} subscribed to {topic}")
            await websocket.send_json({
                "type": "subscribed",
                "topic": topic,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        elif msg_type == "unsubscribe":
            # 取消订阅
            topic = message.get("topic")
            logger.info(f"User {current_user.id} unsubscribed from {topic}")
            await websocket.send_json({
                "type": "unsubscribed",
                "topic": topic,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        elif msg_type == "heartbeat":
            # 心跳
            await websocket.send_json({
                "type": "heartbeat_ack",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")


import asyncio


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="认证token（可选，用于需要认证的连接）")
):
    """
    WebSocket端点
    
    支持两种模式：
    1. 认证模式：使用token进行身份验证
    2. 匿名模式：无需认证（限制功能）
    
    消息格式：
    - 发送: {"type": "ping"|"subscribe"|"heartbeat"|..., ...}
    - 接收: {"type": "notification"|"pong"|... , ...}
    """
    user_id: Optional[int] = None
    
    # 尝试认证
    if token:
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")
                if isinstance(user_id, str):
                    user_id = int(user_id)
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
            # 允许匿名连接
    
    # 如果是认证用户，建立连接
    if user_id:
        await ws_manager.connect(websocket, user_id)
        
        try:
            # 发送连接成功消息
            await websocket.send_json({
                "type": "connected",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket连接已建立"
            })
            
            # 消息处理循环
            while True:
                try:
                    # 接收客户端消息
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        
                        # 处理各类消息
                        await ConnectionManager.handle_client_message(
                            websocket, message, 
                            User(id=user_id, username="", email="") if user_id else None
                        )
                        
                    except json.JSONDecodeError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "无效的JSON格式"
                        })
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if user_id:
                ws_manager.disconnect(websocket)
    else:
        # 匿名模式（只读）
        await websocket.accept()
        
        try:
            await websocket.send_json({
                "type": "connected",
                "authenticated": False,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "匿名连接已建立，功能受限"
            })
            
            # 保持连接但不处理认证消息
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                except WebSocketDisconnect:
                    break
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Anonymous WebSocket error: {e}")


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="认证token（必需）")
):
    """
    通知专用WebSocket端点
    
    专门用于接收实时通知推送
    """
    # 验证token
    user_id = None
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            if isinstance(user_id, str):
                user_id = int(user_id)
    except Exception as e:
        await websocket.close(code=4001, reason="认证失败")
        return
    
    if not user_id:
        await websocket.close(code=4001, reason="无效的token")
        return
    
    # 建立连接
    await ws_manager.connect(websocket, user_id)
    
    try:
        # 发送确认
        await websocket.send_json({
            "type": "notification_connected",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 保持连接
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "mark_read":
                    # 标记通知为已读（可以扩展）
                    await websocket.send_json({
                        "type": "marked_read",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
    finally:
        ws_manager.disconnect(websocket)


# API端点：获取在线状态
@router.get("/ws/status")
async def get_websocket_status(
    current_user: User = Depends(get_current_user)
):
    """获取WebSocket连接状态"""
    return {
        "online": ws_manager.is_user_online(current_user.id),
        "connection_count": ws_manager.get_connection_count(current_user.id),
        "online_users": ws_manager.get_online_users()
    }


# API端点：发送测试通知
@router.post("/ws/test-notification")
async def send_test_notification(
    current_user: User = Depends(get_current_user)
):
    """发送测试通知"""
    await notification_service.send_notification(
        user_id=current_user.id,
        notification_type=NotificationType.SYSTEM,
        title="测试通知",
        content="这是一条测试通知",
        priority="normal"
    )
    
    return {"status": "success", "message": "测试通知已发送"}
