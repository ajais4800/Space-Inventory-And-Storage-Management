"""
Event Bus — async event-driven system.
Events trigger: storage optimizer, RAG re-index, WebSocket push, alert generation.
"""
import asyncio
from typing import List, Callable, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    BATCH_ADDED = "BATCH_ADDED"
    BATCH_UPDATED = "BATCH_UPDATED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CHANGED = "ORDER_CHANGED"
    EXPIRY_ALERT = "EXPIRY_ALERT"
    STOCK_LOW = "STOCK_LOW"
    TEMP_DEVIATION = "TEMP_DEVIATION"
    STORAGE_OPTIMIZED = "STORAGE_OPTIMIZED"
    PLACEMENT_CONFLICT = "PLACEMENT_CONFLICT"
    PROCUREMENT_GENERATED = "PROCUREMENT_GENERATED"


class Event:
    def __init__(self, event_type: EventType, payload: Dict[str, Any], source: str = "system"):
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = datetime.utcnow().isoformat()
        self.id = f"{event_type.value}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"


class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {et: [] for et in EventType}
        self._history: List[Dict] = []
        self._websocket_clients: List = []

    def subscribe(self, event_type: EventType, handler: Callable):
        self._subscribers[event_type].append(handler)

    def add_websocket_client(self, ws):
        self._websocket_clients.append(ws)

    def remove_websocket_client(self, ws):
        if ws in self._websocket_clients:
            self._websocket_clients.remove(ws)

    async def publish(self, event: Event):
        """Publish event to all subscribers and WebSocket clients."""
        self._history.append({
            "id": event.id,
            "type": event.event_type.value,
            "payload": event.payload,
            "source": event.source,
            "timestamp": event.timestamp
        })
        # Keep last 200 events
        if len(self._history) > 200:
            self._history = self._history[-200:]

        # Notify subscribers
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Event handler error for {event.event_type}: {e}")

        # Push to WebSocket clients
        dead_clients = []
        for ws in self._websocket_clients:
            try:
                import json
                await ws.send_text(json.dumps({
                    "event": event.event_type.value,
                    "payload": event.payload,
                    "timestamp": event.timestamp
                }))
            except Exception:
                dead_clients.append(ws)
        for ws in dead_clients:
            self.remove_websocket_client(ws)

    def get_recent_events(self, n: int = 50) -> List[Dict]:
        return self._history[-n:]


# Global singleton event bus
event_bus = EventBus()
