from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import (
    get_db, InventoryBatch, DeliveryOrder, OrderItem, PerishableItem,
    StorageContainer, AIInsight, AuditLog
)
from engine.rag_engine import query_rag, generate_agentic_insights
from engine.event_bus import event_bus, Event, EventType
from datetime import date, timedelta
from typing import Optional
import uuid

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
async def ai_chat(payload: dict, db: Session = Depends(get_db)):
    question = payload.get("message", "").strip()
    if not question:
        return {"answer": "Please ask a question.", "source": "validation"}
    result = query_rag(question)
    return result


@router.get("/insights")
def get_insights(db: Session = Depends(get_db), resolved: bool = False):
    insights = db.query(AIInsight).filter(
        AIInsight.resolved == resolved
    ).order_by(AIInsight.created_at.desc()).limit(50).all()
    return [_format_insight(i) for i in insights]


@router.post("/insights/generate")
async def generate_insights(db: Session = Depends(get_db)):
    """Use Gemini to proactively generate insights from current DB state."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    expiring_24h = db.query(InventoryBatch).filter(
        InventoryBatch.expiry_date <= tomorrow,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
    ).all()
    expiring_kg = sum(b.quantity_kg for b in expiring_24h)

    items = db.query(PerishableItem).all()
    below_reorder = []
    for item in items:
        total = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
            InventoryBatch.item_id == item.id,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).scalar() or 0
        if total < item.reorder_point_kg:
            below_reorder.append(item.name)

    containers = db.query(StorageContainer).all()
    total_cap = sum(c.capacity_kg for c in containers)
    total_load = sum(c.current_load_kg for c in containers)
    util_pct = (total_load / total_cap * 100) if total_cap else 0

    pending_7d = db.query(DeliveryOrder).filter(
        DeliveryOrder.delivery_date <= today + timedelta(days=7),
        DeliveryOrder.status.in_(["pending", "confirmed"])
    ).count()

    overripe = db.query(InventoryBatch).filter(
        InventoryBatch.ripeness_score >= 1.5,
        InventoryBatch.status.in_(["in_stock", "at_risk"])
    ).count()

    db_summary = {
        "total_batches": db.query(InventoryBatch).filter(InventoryBatch.status.in_(["in_stock", "reserved"])).count(),
        "expiring_24h": len(expiring_24h), "expiring_24h_kg": round(expiring_kg, 1),
        "below_reorder": below_reorder,
        "storage_util_pct": util_pct,
        "pending_orders_7d": pending_7d,
        "pending_demand_kg": 0,
        "conflicts": 0,
        "overripe": overripe
    }

    insight_text = generate_agentic_insights(db_summary)

    # Parse and store insights
    lines = [l.strip() for l in insight_text.split("\n\n") if l.strip()]
    created = []
    for line in lines[:5]:
        if not line:
            continue
        severity = "critical" if "🔴" in line else "warning" if "🟡" in line else "info"
        insight = AIInsight(
            insight_id=f"INS-{uuid.uuid4().hex[:8].upper()}",
            insight_type="agentic_ai",
            title=line[:80],
            message=line,
            severity=severity
        )
        db.add(insight)
        created.append(_format_insight(insight))
    db.commit()

    return {"generated": len(created), "insights": created}


@router.put("/insights/{insight_id}/resolve")
def resolve_insight(insight_id: str, db: Session = Depends(get_db)):
    from datetime import datetime
    insight = db.query(AIInsight).filter(AIInsight.insight_id == insight_id).first()
    if insight:
        insight.resolved = True
        insight.resolved_at = datetime.utcnow()
        db.commit()
    return {"resolved": True}


@router.get("/storage-advice")
def get_storage_advice(db: Session = Depends(get_db)):
    """AI-generated plain-English storage placement advice."""
    question = (
        "Looking at the current inventory batches, which items need to be repositioned? "
        "Identify any LIFO violations where a batch expiring sooner is stored behind one expiring later. "
        "Give specific batch IDs and recommended new positions."
    )
    return query_rag(question)


def _format_insight(i: AIInsight) -> dict:
    return {
        "insight_id": i.insight_id,
        "type": i.insight_type,
        "title": i.title,
        "message": i.message,
        "severity": i.severity,
        "resolved": i.resolved,
        "created_at": i.created_at.isoformat() if i.created_at else None
    }
