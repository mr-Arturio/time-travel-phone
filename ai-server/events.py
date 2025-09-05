cat > ai-server/events.py <<'PY'
import asyncio, json, uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

class EventBus:
    def __init__(self, max_events: int = 1000):
        self.events: "deque[dict]" = deque(maxlen=max_events)
        self.subscribers: "set[asyncio.Queue]" = set()

    def _sse(self, ev: dict) -> bytes:
        return (f"id: {ev['id']}\n"
                f"event: {ev['type']}\n"
                f"data: {json.dumps(ev, ensure_ascii=False)}\n\n").encode("utf-8")

    async def _broadcast(self, ev: dict):
        dead = []
        for q in list(self.subscribers):
            try:
                q.put_nowait(ev)
            except Exception:
                dead.append(q)
        for q in dead:
            self.subscribers.discard(q)

    def emit(self, ev_type: str, text: str = "", call_id: Optional[str] = None, **data) -> dict:
        ev = {
            "id": str(uuid.uuid4()),
            "ts": _now_iso(),
            "type": ev_type,
            "text": text,
            "call_id": call_id,
            "data": data or {},
        }
        self.events.append(ev)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(ev))
        except RuntimeError:
            pass
        return ev

import os
event_bus = EventBus(max_events=int(os.environ.get("EVENTS_MAX", "1000")))

# Routers
sse_router = APIRouter()
event_router = APIRouter()

@sse_router.get("/events")
async def events(request: Request):
    q: asyncio.Queue = asyncio.Queue()
    event_bus.subscribers.add(q)

    async def gen():
        for ev in list(event_bus.events)[-200:]:
            yield event_bus._sse(ev)
        try:
            while True:
                if await request.is_disconnected():
                    break
                ev = await q.get()
                yield event_bus._sse(ev)
        finally:
            event_bus.subscribers.discard(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

class ClientEvent(BaseModel):
    type: str
    text: Optional[str] = ""
    call_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@event_router.post("/event")
async def post_event(ev: ClientEvent):
    event_bus.emit(ev.type, ev.text or "", ev.call_id, **(ev.data or {}))
    return {"ok": True}
PY
