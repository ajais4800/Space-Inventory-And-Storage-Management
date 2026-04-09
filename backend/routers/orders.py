from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, DeliveryOrder, OrderItem, PerishableItem, AuditLog
from engine.procurement_engine import get_order_fulfillment
from engine.event_bus import event_bus, Event, EventType
from datetime import date, timedelta
from typing import Optional
import uuid

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/")
def get_orders(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    city: Optional[str] = None,
    days_ahead: int = 30,
    limit: int = 100,
    offset: int = 0
):
    today = date.today()
    query = db.query(DeliveryOrder)
    if status:
        query = query.filter(DeliveryOrder.status == status)
    if city:
        query = query.filter(DeliveryOrder.city == city)
    query = query.filter(DeliveryOrder.delivery_date >= today - timedelta(days=7))
    query = query.order_by(DeliveryOrder.delivery_date)
    total = query.count()
    orders = query.offset(offset).limit(limit).all()
    return {"total": total, "orders": [_format_order(o) for o in orders]}


@router.post("/")
async def create_order(payload: dict, db: Session = Depends(get_db)):
    order = DeliveryOrder(
        order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        client_name=payload.get("client_name"),
        city=payload.get("city"),
        delivery_date=date.fromisoformat(payload.get("delivery_date")),
        status="pending",
        priority=payload.get("priority", "normal"),
        notes=payload.get("notes")
    )
    db.add(order)
    db.flush()

    for li in payload.get("items", []):
        item = db.query(PerishableItem).filter(PerishableItem.sku == li.get("sku")).first()
        if item:
            db.add(OrderItem(
                order_id=order.id, item_id=item.id,
                quantity_kg=li.get("quantity_kg", 0),
                unit_price=li.get("unit_price", 0)
            ))

    db.add(AuditLog(
        entity_type="DeliveryOrder", entity_id=order.order_id,
        action="CREATE", new_value={"client": order.client_name, "date": str(order.delivery_date)}
    ))
    db.commit()
    db.refresh(order)

    await event_bus.publish(Event(
        EventType.ORDER_CREATED,
        {"order_id": order.order_id, "client": order.client_name, "delivery_date": str(order.delivery_date)},
        source="api"
    ))
    return _format_order(order)


@router.get("/fulfillment/{order_id}")
def get_fulfillment(order_id: str, db: Session = Depends(get_db)):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.order_id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return get_order_fulfillment(db, order.id)


@router.get("/upcoming")
def get_upcoming_orders(db: Session = Depends(get_db), days: int = 7):
    today = date.today()
    cutoff = today + timedelta(days=days)
    orders = (
        db.query(DeliveryOrder)
        .filter(
            DeliveryOrder.delivery_date >= today,
            DeliveryOrder.delivery_date <= cutoff,
            DeliveryOrder.status.in_(["pending", "confirmed"])
        )
        .order_by(DeliveryOrder.delivery_date)
        .all()
    )
    return [_format_order(o) for o in orders]


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, payload: dict, db: Session = Depends(get_db)):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.order_id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    old_status = order.status
    order.status = payload.get("status", order.status)
    db.add(AuditLog(
        entity_type="DeliveryOrder", entity_id=order.order_id,
        action="UPDATE", old_value={"status": old_status}, new_value={"status": order.status}
    ))
    db.commit()
    await event_bus.publish(Event(
        EventType.ORDER_CHANGED,
        {"order_id": order.order_id, "old_status": old_status, "new_status": order.status},
        source="api"
    ))
    return _format_order(order)


def _format_order(o: DeliveryOrder) -> dict:
    return {
        "order_id": o.order_id,
        "client_name": o.client_name,
        "city": o.city,
        "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
        "status": o.status,
        "priority": o.priority,
        "days_until_delivery": (o.delivery_date - date.today()).days if o.delivery_date else None,
        "items": [
            {
                "item_name": oi.item.name if oi.item else None,
                "sku": oi.item.sku if oi.item else None,
                "quantity_kg": oi.quantity_kg,
                "fulfilled_kg": oi.fulfilled_kg,
                "gap_kg": max(0, oi.quantity_kg - oi.fulfilled_kg),
                "unit_price": oi.unit_price
            }
            for oi in (o.order_items or [])
        ],
        "created_at": o.created_at.isoformat() if o.created_at else None
    }
