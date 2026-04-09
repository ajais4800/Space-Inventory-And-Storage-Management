from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import List, Optional
from database import get_db, InventoryBatch, PerishableItem, StorageContainer, AuditLog
from engine.ripeness_predictor import predict_ripeness_date, batch_ripeness_timeline
from engine.event_bus import event_bus, Event, EventType
import uuid

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/")
def get_inventory(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    query = (
        db.query(InventoryBatch)
        .join(PerishableItem)
        .join(StorageContainer, isouter=True)
    )
    if status:
        query = query.filter(InventoryBatch.status == status)
    if category:
        query = query.filter(PerishableItem.category == category)
    if search:
        query = query.filter(PerishableItem.name.ilike(f"%{search}%"))

    total = query.count()
    batches = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [_format_batch(b) for b in batches]
    }


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), days: int = 3):
    today = date.today()
    cutoff = today + timedelta(days=days)
    expiring = (
        db.query(InventoryBatch)
        .join(PerishableItem)
        .filter(
            InventoryBatch.expiry_date <= cutoff,
            InventoryBatch.expiry_date >= today,
            InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
        )
        .order_by(InventoryBatch.expiry_date)
        .all()
    )
    below_reorder = (
        db.query(PerishableItem)
        .all()
    )
    reorder_alerts = []
    for item in below_reorder:
        total_stock = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
            InventoryBatch.item_id == item.id,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).scalar() or 0
        if total_stock < item.reorder_point_kg:
            reorder_alerts.append({
                "item": item.name, "sku": item.sku,
                "current_kg": round(total_stock, 1),
                "reorder_point_kg": item.reorder_point_kg,
                "gap_kg": round(item.reorder_point_kg - total_stock, 1),
                "lead_days": item.lead_days
            })
    return {
        "expiring_soon": [_format_batch(b) for b in expiring],
        "below_reorder_point": reorder_alerts
    }


@router.get("/expiry")
def get_expiry_batches(db: Session = Depends(get_db), days: int = 7):
    today = date.today()
    cutoff = today + timedelta(days=days)
    batches = (
        db.query(InventoryBatch)
        .join(PerishableItem)
        .filter(
            InventoryBatch.expiry_date <= cutoff,
            InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
        )
        .order_by(InventoryBatch.expiry_date)
        .all()
    )
    return [_format_batch(b) for b in batches]


@router.get("/ripeness-timeline")
def get_ripeness_timeline(db: Session = Depends(get_db), days: int = 14):
    batches = (
        db.query(InventoryBatch)
        .join(PerishableItem)
        .filter(InventoryBatch.status.in_(["in_stock", "reserved"]))
        .all()
    )
    return batch_ripeness_timeline(batches, window_days=days)


@router.post("/batch")
async def add_batch(payload: dict, db: Session = Depends(get_db)):
    item = db.query(PerishableItem).filter(PerishableItem.sku == payload.get("sku")).first()
    if not item:
        raise HTTPException(404, f"Item with SKU '{payload.get('sku')}' not found")

    container = db.query(StorageContainer).filter(
        StorageContainer.container_id == payload.get("container_id")
    ).first()

    received_date = date.fromisoformat(payload.get("received_date", date.today().isoformat()))
    ripeness_pred = predict_ripeness_date(
        received_date=received_date,
        ripeness_curve=item.ripeness_curve,
        peak_day=item.ripeness_peak_day,
        shelf_life_days=item.shelf_life_days,
        optimal_max_temp=item.storage_temp_max_c,
        actual_temp=payload.get("storage_temp_actual_c")
    )

    from datetime import datetime as dt
    ripeness_date = date.fromisoformat(ripeness_pred["predicted_ripeness_date"])
    expiry_date = date.fromisoformat(ripeness_pred["expiry_date"])

    batch = InventoryBatch(
        batch_id=f"BAT-{uuid.uuid4().hex[:8].upper()}",
        item_id=item.id,
        container_id=container.id if container else None,
        quantity_kg=payload.get("quantity_kg", 0),
        variety=payload.get("variety"),
        received_date=received_date,
        expected_ripeness_date=ripeness_date,
        expiry_date=expiry_date,
        storage_temp_actual_c=payload.get("storage_temp_actual_c"),
        status="in_stock",
        ripeness_score=0.0,
        notes=payload.get("notes")
    )
    db.add(batch)
    if container:
        container.current_load_kg += payload.get("quantity_kg", 0)

    db.add(AuditLog(
        entity_type="InventoryBatch", entity_id=batch.batch_id,
        action="CREATE", new_value={"sku": item.sku, "qty_kg": payload.get("quantity_kg")}
    ))
    db.commit()
    db.refresh(batch)

    await event_bus.publish(Event(
        EventType.BATCH_ADDED,
        {"batch_id": batch.batch_id, "item": item.name, "qty_kg": batch.quantity_kg},
        source="api"
    ))
    return {**_format_batch(batch), "ripeness_prediction": ripeness_pred}


@router.get("/{batch_id}")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(InventoryBatch).join(PerishableItem).filter(
        InventoryBatch.batch_id == batch_id
    ).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return _format_batch(batch)


def _format_batch(b: InventoryBatch) -> dict:
    item = b.item if hasattr(b, 'item') and b.item else None
    container = b.container if hasattr(b, 'container') and b.container else None
    return {
        "batch_id": b.batch_id,
        "item_name": item.name if item else "Unknown",
        "sku": item.sku if item else None,
        "category": item.category if item else None,
        "quantity_kg": b.quantity_kg,
        "variety": b.variety,
        "received_date": b.received_date.isoformat() if b.received_date else None,
        "expected_ripeness_date": b.expected_ripeness_date.isoformat() if b.expected_ripeness_date else None,
        "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
        "status": b.status,
        "ripeness_score": b.ripeness_score,
        "position": {"index": b.position_index, "row": b.row, "col": b.col, "depth": b.depth},
        "container": {"id": container.container_id, "name": container.name} if container else None,
        "storage_temp_c": b.storage_temp_actual_c,
        "days_until_ripe": max(0, (b.expected_ripeness_date - date.today()).days) if b.expected_ripeness_date else None,
        "days_until_expiry": (b.expiry_date - date.today()).days if b.expiry_date else None,
    }
