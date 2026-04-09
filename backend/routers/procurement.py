from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, ProcurementRecommendation, PerishableItem, AuditLog
from engine.procurement_engine import calculate_recommendations
from engine.rag_engine import generate_agentic_insights
from engine.event_bus import event_bus, Event, EventType
from datetime import date, datetime
from typing import Optional
import uuid

router = APIRouter(prefix="/api/procurement", tags=["procurement"])


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db), status: Optional[str] = None):
    query = db.query(ProcurementRecommendation).join(PerishableItem)
    if status:
        query = query.filter(ProcurementRecommendation.status == status)
    recs = query.order_by(ProcurementRecommendation.created_at.desc()).limit(100).all()
    return [_format_rec(r) for r in recs]


@router.post("/generate")
async def generate_recommendations(db: Session = Depends(get_db)):
    """Run agentic AI procurement engine to generate new recommendations."""
    recs_data = calculate_recommendations(db)
    created = []
    for r in recs_data:
        # Skip if a pending recommendation already exists for this item
        existing = db.query(ProcurementRecommendation).filter(
            ProcurementRecommendation.item_id == r["item_id"],
            ProcurementRecommendation.status == "pending"
        ).first()
        if existing:
            continue

        rec = ProcurementRecommendation(
            rec_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
            item_id=r["item_id"],
            recommended_qty_kg=r["recommended_qty_kg"],
            order_by_date=date.fromisoformat(r["order_by_date"]),
            expected_delivery_date=date.fromisoformat(r["expected_delivery_date"]),
            reason=r["reason"],
            ai_generated=True,
            status="pending",
            priority=r["priority"]
        )
        db.add(rec)
        created.append(r)

    db.add(AuditLog(
        entity_type="ProcurementEngine", entity_id="batch",
        action="AI_RECOMMEND", new_value={"generated": len(created)}
    ))
    db.commit()

    await event_bus.publish(Event(
        EventType.PROCUREMENT_GENERATED,
        {"count": len(created), "items": [r["item_name"] for r in created[:5]]},
        source="ai_agent"
    ))
    return {"generated": len(created), "recommendations": created}


@router.put("/{rec_id}/approve")
def approve_recommendation(rec_id: str, db: Session = Depends(get_db)):
    rec = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.rec_id == rec_id
    ).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    old_status = rec.status
    rec.status = "approved"
    rec.resolved_at = datetime.utcnow()
    db.add(AuditLog(
        entity_type="ProcurementRecommendation", entity_id=rec_id,
        action="UPDATE", old_value={"status": old_status}, new_value={"status": "approved"}
    ))
    db.commit()
    return _format_rec(rec)


@router.put("/{rec_id}/reject")
def reject_recommendation(rec_id: str, db: Session = Depends(get_db)):
    rec = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.rec_id == rec_id
    ).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = "rejected"
    rec.resolved_at = datetime.utcnow()
    db.commit()
    return _format_rec(rec)


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    recs = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.status.in_(["approved", "rejected", "ordered"])
    ).order_by(ProcurementRecommendation.resolved_at.desc()).limit(50).all()
    return [_format_rec(r) for r in recs]


def _format_rec(r: ProcurementRecommendation) -> dict:
    item = r.item if hasattr(r, 'item') and r.item else None
    return {
        "rec_id": r.rec_id,
        "item_name": item.name if item else "Unknown",
        "sku": item.sku if item else None,
        "recommended_qty_kg": r.recommended_qty_kg,
        "order_by_date": r.order_by_date.isoformat() if r.order_by_date else None,
        "expected_delivery_date": r.expected_delivery_date.isoformat() if r.expected_delivery_date else None,
        "reason": r.reason,
        "priority": r.priority,
        "status": r.status,
        "ai_generated": r.ai_generated,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
    }
