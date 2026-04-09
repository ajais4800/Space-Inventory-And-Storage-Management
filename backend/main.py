"""
SISM — Smart Inventory & Storage Management
FastAPI main application entry point.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import create_tables
from engine.event_bus import event_bus, EventType, Event
from routers import inventory, storage, orders, procurement, ai, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed data, index into ChromaDB."""
    print("\n🚀 SISM Backend Starting...")
    create_tables()

    # Seed database if empty
    try:
        from seed_data import run_seed
        run_seed()
    except Exception as e:
        print(f"⚠️  Seeding skipped: {e}")

    # Index inventory into ChromaDB for RAG
    try:
        from database import SessionLocal, InventoryBatch, DeliveryOrder, PerishableItem
        from engine.rag_engine import index_inventory
        db = SessionLocal()
        batches = db.query(InventoryBatch).limit(300).all()
        orders_q = db.query(DeliveryOrder).limit(200).all()
        items = db.query(PerishableItem).all()
        count = index_inventory(batches, orders_q, items)
        print(f"  ✓ ChromaDB indexed {count} documents for RAG")
        db.close()
    except Exception as e:
        print(f"⚠️  ChromaDB indexing skipped: {e}")

    # Register event bus handlers
    async def on_batch_added(event: Event):
        """Re-run storage optimizer when a new batch is added."""
        try:
            from database import SessionLocal, StorageContainer, InventoryBatch
            from engine.storage_optimizer import optimize_container
            db = SessionLocal()
            containers = db.query(StorageContainer).filter(StorageContainer.is_active == True).all()
            for c in containers:
                batches = db.query(InventoryBatch).filter(
                    InventoryBatch.container_id == c.id,
                    InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
                ).all()
                optimize_container(batches, c)
            db.close()
        except Exception as e:
            print(f"Event handler error: {e}")

    event_bus.subscribe(EventType.BATCH_ADDED, on_batch_added)
    print("  ✓ Event bus handlers registered")
    print("✅ SISM Backend Ready!\n")

    yield
    print("👋 SISM Backend Shutting down...")


app = FastAPI(
    title="SISM — Smart Inventory & Storage Management",
    description="AI-powered perishable goods inventory, storage optimization, and procurement intelligence.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(inventory.router)
app.include_router(storage.router)
app.include_router(orders.router)
app.include_router(procurement.router)
app.include_router(ai.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "app": "SISM — Smart Inventory & Storage Management",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "SISM API"}


# ─── WebSocket Endpoints ────────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    event_bus.add_websocket_client(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "event": "CONNECTED",
            "payload": {"message": "Connected to SISM live dashboard feed"},
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }))
        while True:
            # Keep connection alive; events are pushed by event_bus
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"event": "PING", "payload": {}}))
    except WebSocketDisconnect:
        event_bus.remove_websocket_client(websocket)


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    event_bus.add_websocket_client(websocket)
    try:
        await websocket.send_text(json.dumps({
            "event": "CONNECTED",
            "payload": {"message": "Connected to SISM alerts feed"}
        }))
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"event": "PING", "payload": {}}))
    except WebSocketDisconnect:
        event_bus.remove_websocket_client(websocket)


@app.get("/api/events/recent")
def get_recent_events(n: int = 20):
    return event_bus.get_recent_events(n)


@app.get("/api/items")
def get_items(db=None):
    from database import SessionLocal, PerishableItem
    db = SessionLocal()
    items = db.query(PerishableItem).all()
    db.close()
    return [
        {
            "id": i.id, "sku": i.sku, "name": i.name, "category": i.category,
            "unit": i.unit, "zone": i.zone, "reorder_point_kg": i.reorder_point_kg,
            "lead_days": i.lead_days, "shelf_life_days": i.shelf_life_days,
            "ripeness_peak_day": i.ripeness_peak_day, "varieties": i.varieties
        }
        for i in items
    ]
