from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import (
    get_db, InventoryBatch, DeliveryOrder, OrderItem, PerishableItem,
    StorageContainer, ProcurementRecommendation, AuditLog
)
from datetime import date, timedelta

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), sim_days: int = 0):
    today = date.today() + timedelta(days=sim_days)
    week_ahead = today + timedelta(days=7)
    next3days = today + timedelta(days=3)

    total_stock_kg = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
        InventoryBatch.status.in_(["in_stock", "reserved"])
    ).scalar() or 0

    expiring_soon = db.query(InventoryBatch).filter(
        InventoryBatch.expiry_date <= next3days,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
    ).count()

    expiring_soon_kg = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
        InventoryBatch.expiry_date <= next3days,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
    ).scalar() or 0

    pending_orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.status.in_(["pending", "confirmed"]),
        DeliveryOrder.delivery_date >= today,
        DeliveryOrder.delivery_date <= week_ahead
    ).count()

    containers = db.query(StorageContainer).all()
    total_capacity = sum(c.capacity_kg for c in containers)
    total_load = sum(c.current_load_kg for c in containers)
    storage_util_pct = round((total_load / total_capacity * 100) if total_capacity else 0, 1)

    ripe_today = db.query(InventoryBatch).filter(
        InventoryBatch.expected_ripeness_date == today,
        InventoryBatch.status.in_(["in_stock", "reserved"])
    ).count()

    ripe_today_kg = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
        InventoryBatch.expected_ripeness_date == today,
        InventoryBatch.status.in_(["in_stock", "reserved"])
    ).scalar() or 0

    pending_recs = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.status == "pending"
    ).count()

    urgent_recs = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.status == "pending",
        ProcurementRecommendation.priority == "urgent"
    ).count()

    total_batches = db.query(InventoryBatch).count()
    total_delivery_orders = db.query(DeliveryOrder).count()

    # Category breakdown
    cat_data = []
    items = db.query(PerishableItem).all()
    for item in items:
        qty = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
            InventoryBatch.item_id == item.id,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).scalar() or 0
        if qty > 0:
            cat_data.append({"name": item.name, "kg": round(qty, 1), "category": item.category})
    cat_data.sort(key=lambda x: x["kg"], reverse=True)

    return {
        "total_stock_kg": round(total_stock_kg, 1),
        "expiring_soon_batches": expiring_soon,
        "expiring_soon_kg": round(expiring_soon_kg, 1),
        "pending_orders_7d": pending_orders,
        "storage_utilization_pct": storage_util_pct,
        "total_capacity_kg": round(total_capacity, 1),
        "current_load_kg": round(total_load, 1),
        "ripe_today_batches": ripe_today,
        "ripe_today_kg": round(ripe_today_kg, 1),
        "pending_procurement_recs": pending_recs,
        "urgent_procurement_recs": urgent_recs,
        "stock_by_item": cat_data[:10],
        "total_containers": len(containers),
        "total_batches_all": total_batches,
        "total_delivery_orders_all": total_delivery_orders
    }


@router.get("/wastage")
def get_wastage(db: Session = Depends(get_db), days: int = 30):
    today = date.today()
    past = today - timedelta(days=days)
    wasted = db.query(InventoryBatch).filter(
        InventoryBatch.status.in_(["expired", "wasted"]),
        InventoryBatch.updated_at >= past
    ).all()

    by_item = {}
    for b in wasted:
        name = b.item.name if b.item else "Unknown"
        if name not in by_item:
            by_item[name] = {"item": name, "batches": 0, "kg": 0.0}
        by_item[name]["batches"] += 1
        by_item[name]["kg"] += b.quantity_kg

    wastage_list = sorted(by_item.values(), key=lambda x: x["kg"], reverse=True)
    total_wasted_kg = sum(w["kg"] for w in wastage_list)

    return {
        "period_days": days,
        "total_wasted_kg": round(total_wasted_kg, 1),
        "total_wasted_batches": len(wasted),
        "by_item": wastage_list
    }


@router.get("/demand")
def get_demand_trend(db: Session = Depends(get_db), days: int = 14, sim_days: int = 0):
    today = date.today() + timedelta(days=sim_days)
    trend = []
    items = db.query(PerishableItem).all()
    item_names = {i.id: i.name for i in items}

    for offset in range(days):
        d = today + timedelta(days=offset)
        day_orders = db.query(OrderItem).join(DeliveryOrder).filter(
            DeliveryOrder.delivery_date == d,
            DeliveryOrder.status.in_(["pending", "confirmed"])
        ).all()
        day_demand = {}
        for oi in day_orders:
            name = item_names.get(oi.item_id, "Unknown")
            day_demand[name] = round(day_demand.get(name, 0) + oi.quantity_kg, 1)

        ripe_kg = db.query(func.sum(InventoryBatch.quantity_kg)).filter(
            InventoryBatch.expected_ripeness_date == d,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).scalar() or 0

        trend.append({
            "date": d.isoformat(),
            "day_label": f"Day +{offset}" if offset > 0 else "Today",
            "total_demand_kg": round(sum(day_demand.values()), 1),
            "ripe_supply_kg": round(ripe_kg, 1),
            "demand_by_item": day_demand
        })
    return trend


@router.get("/storage-efficiency")
def get_storage_efficiency(db: Session = Depends(get_db)):
    containers = db.query(StorageContainer).all()
    data = []
    for c in containers:
        active_batches = db.query(InventoryBatch).filter(
            InventoryBatch.container_id == c.id,
            InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
        ).count()
        data.append({
            "container_id": c.container_id,
            "name": c.name,
            "zone_type": c.zone_type,
            "capacity_kg": c.capacity_kg,
            "current_load_kg": round(c.current_load_kg, 1),
            "utilization_pct": round((c.current_load_kg / c.capacity_kg * 100) if c.capacity_kg else 0, 1),
            "active_batches": active_batches,
            "temp_c": c.temp_c
        })
    return data


@router.get("/ripeness-timeline")
def get_ripeness_timeline_report(db: Session = Depends(get_db), days: int = 14):
    today = date.today()
    timeline = []
    for offset in range(days):
        d = today + timedelta(days=offset)
        batches = db.query(InventoryBatch).join(PerishableItem).filter(
            InventoryBatch.expected_ripeness_date == d,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).all()
        orders_due = db.query(DeliveryOrder).filter(
            DeliveryOrder.delivery_date == d,
            DeliveryOrder.status.in_(["pending", "confirmed"])
        ).count()
        timeline.append({
            "date": d.isoformat(),
            "label": f"Day +{offset}" if offset > 0 else "Today",
            "ripe_batches": len(batches),
            "ripe_kg": round(sum(b.quantity_kg for b in batches), 1),
            "items_ripe": list(set(b.item.name for b in batches if b.item)),
            "orders_due": orders_due
        })
    return timeline
