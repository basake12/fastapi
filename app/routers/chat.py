# app/routers/chat.py
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List
import json
import asyncio

from .. import models, schemas, database, oauth2
from ..redis_client import redis_client  # Global client from lifespan


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}}
)


# In-memory connection manager (for dev; Redis handles delivery)
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_text(json.dumps(message))
            except WebSocketDisconnect:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/{receiver_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    receiver_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user_ws)
):
    await manager.connect(current_user.id, websocket)
    listener_task = None

    try:
        # Subscribe to Redis Pub/Sub for this user
        pubsub = redis_client.pubsub()
        await run_in_threadpool(pubsub.subscribe, f"user:{current_user.id}")

        # Background Redis listener
        async def redis_listener():
            while True:
                msg = await run_in_threadpool(
                    pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    data = json.loads(msg["data"])
                    await manager.send_personal_message(data, current_user.id)
                await asyncio.sleep(0.01)

        listener_task = asyncio.create_task(redis_listener())

        # Main loop: receive from WebSocket
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            # Validate receiver
            if message.get("receiver_id") != receiver_id:
                await websocket.send_text(json.dumps({"error": "Invalid receiver"}))
                continue

            content = message.get("content")
            if not content or not isinstance(content, str):
                await websocket.send_text(json.dumps({"error": "Content required"}))
                continue

            # Save to DB
            db_message = models.ChatMessage(
                content=content.strip(),
                sender_id=current_user.id,
                receiver_id=receiver_id
            )
            db.add(db_message)
            db.commit()
            db.refresh(db_message)

            # Load full message with sender/receiver
            full_msg = db.query(models.ChatMessage).options(
                joinedload(models.ChatMessage.sender),
                joinedload(models.ChatMessage.receiver)
            ).filter(models.ChatMessage.id == db_message.id).first()

            if not full_msg:
                continue

            response = schemas.ChatMessageResponse.from_orm(full_msg)
            payload = response.dict()

            # Publish to receiver via Redis
            await run_in_threadpool(
                redis_client.publish,
                f"user:{receiver_id}",
                json.dumps(payload)
            )

            # Echo back to sender
            await manager.send_personal_message(payload, current_user.id)

    except WebSocketDisconnect:
        manager.disconnect(current_user.id, websocket)
    except Exception as e:
        print(f"Chat error: {e}")
        manager.disconnect(current_user.id, websocket)
        try:
            await websocket.close(code=1011)
        except:
            pass
    finally:
        if listener_task:
            listener_task.cancel()