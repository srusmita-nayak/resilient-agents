import asyncio
import json
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from app.db.repository import Repository

class WebSocketManager:
    """Manages WebSocket subscribers with sequence-based replay and bounded buffers."""
    def __init__(self, repository: Repository):
        self.repository = repository
        self.active_connections: Set[WebSocket] = set()
        self.client_subscriptions: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            self.client_subscriptions[websocket] = {"run_id": None, "experiment_id": None, "last_seq": 0}

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)
            self.client_subscriptions.pop(websocket, None)

    async def handle_client_message(self, websocket: WebSocket, data: str) -> None:
        try:
            msg = json.loads(data)
            action = msg.get("action")

            if action == "subscribe":
                run_id = msg.get("run_id")
                exp_id = msg.get("experiment_id")
                from_seq = msg.get("from_seq", 0)

                async with self._lock:
                    sub = self.client_subscriptions.get(websocket)
                    if sub:
                        sub["run_id"] = run_id
                        sub["experiment_id"] = exp_id
                        sub["last_seq"] = from_seq

                # Replay historical events if run_id provided
                if run_id:
                    historical_events = self.repository.get_events_for_run(run_id=run_id, min_seq=from_seq, limit=1000)
                    for ev in historical_events:
                        await websocket.send_text(json.dumps({"type": "EVENT_REPLAY", "event": ev}))
                        if sub:
                            sub["last_seq"] = max(sub["last_seq"], ev["seq"])

            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": msg.get("timestamp")}))

        except Exception as ex:
            await websocket.send_text(json.dumps({"type": "ERROR", "message": str(ex)}))

    async def broadcast_event(self, event: Dict[str, Any]) -> None:
        """Broadcasts live event to matching subscribers."""
        ev_run_id = event.get("run_id")
        msg_text = json.dumps({"type": "EVENT_LIVE", "event": event})

        disconnected = []
        async with self._lock:
            for ws, sub in list(self.client_subscriptions.items()):
                # Check filter
                if sub["run_id"] and sub["run_id"] != ev_run_id:
                    continue
                try:
                    await ws.send_text(msg_text)
                    sub["last_seq"] = max(sub["last_seq"], event.get("seq", 0))
                except Exception:
                    disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws)
