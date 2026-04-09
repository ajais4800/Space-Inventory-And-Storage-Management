"""
Procurement Engine — AI-driven purchase recommendation engine.
Compares projected demand vs usable (ripeness-adjusted) stock.
Factors in lead times to generate timely purchase orders.
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database import PerishableItem, InventoryBatch, DeliveryOrder, OrderItem


def get_usable_stock(db: Session, item_id: int, by_date: date) -> float:
    """
    Returns total kg of a given item that will be ripe and usable by a given date.
    Excludes expired, delivered, or wasted batches. Also excludes batches ripe AFTER the date.
    """
    batches = (
        db.query(InventoryBatch)
        .filter(
            InventoryBatch.item_id == item_id,
            InventoryBatch.status.in_(["in_stock", "reserved"]),
            InventoryBatch.expected_ripeness_date <= by_date,
            InventoryBatch.expiry_date >= date.today()
        )
        .all()
    )
    return sum(b.quantity_kg for b in batches)


def get_demand_for_period(db: Session, item_id: int, start: date, end: date) -> float:
    """Returns total kg of item demanded in pending/confirmed orders in a date window."""
    order_items = (
        db.query(OrderItem)
        .join(DeliveryOrder)
        .filter(
            OrderItem.item_id == item_id,
            DeliveryOrder.delivery_date >= start,
            DeliveryOrder.delivery_date <= end,
            DeliveryOrder.status.in_(["pending", "confirmed"])
        )
        .all()
    )
    return sum(oi.quantity_kg for oi in order_items)


def calculate_recommendations(db: Session) -> List[Dict[str, Any]]:
    """
    Main procurement engine. For each item:
    1. Check demand in next `lead_days + 3` window
    2. Check usable stock for that window
    3. If gap exists, recommend order quantity and timing
    """
    items = db.query(PerishableItem).all()
    today = date.today()
    recommendations = []

    for item in items:
        window_days = item.lead_days + 5  # Look ahead: lead time + 5 day buffer
        window_end = today + timedelta(days=window_days)

        demand = get_demand_for_period(db, item.id, today, window_end)
        usable = get_usable_stock(db, item.id, window_end)

        # Always check against reorder point too
        total_stock_kg = sum(
            b.quantity_kg for b in db.query(InventoryBatch)
            .filter(InventoryBatch.item_id == item.id, InventoryBatch.status.in_(["in_stock", "reserved"]))
            .all()
        )

        gap = demand - usable
        below_reorder = total_stock_kg < item.reorder_point_kg

        if gap > 0 or below_reorder:
            # How much to order
            reorder_gap = max(0, item.reorder_point_kg - total_stock_kg)
            qty_to_order = round(max(gap * 1.15, reorder_gap) + 20, 1)  # 15% safety buffer + 20kg minimum

            order_by_date = today  # Order today to meet lead time
            expected_delivery = today + timedelta(days=item.lead_days)

            # Priority
            if gap > 100 or (below_reorder and total_stock_kg < item.reorder_point_kg * 0.5):
                priority = "urgent"
            elif gap > 50 or below_reorder:
                priority = "high"
            else:
                priority = "normal"

            reason_parts = []
            if gap > 0:
                reason_parts.append(
                    f"Demand of {demand:.1f}kg exceeds usable stock ({usable:.1f}kg) "
                    f"for {window_days}-day window. Gap: {gap:.1f}kg."
                )
            if below_reorder:
                reason_parts.append(
                    f"Current stock ({total_stock_kg:.1f}kg) is below reorder point ({item.reorder_point_kg}kg)."
                )

            recommendations.append({
                "item_id": item.id,
                "item_name": item.name,
                "sku": item.sku,
                "recommended_qty_kg": qty_to_order,
                "order_by_date": order_by_date.isoformat(),
                "expected_delivery_date": expected_delivery.isoformat(),
                "current_stock_kg": round(total_stock_kg, 1),
                "usable_stock_kg": round(usable, 1),
                "demand_kg": round(demand, 1),
                "gap_kg": round(max(gap, 0), 1),
                "priority": priority,
                "reason": " ".join(reason_parts) or "Below safety reorder point.",
                "lead_days": item.lead_days,
                "window_days": window_days
            })

    # Sort by priority
    priority_order = {"urgent": 0, "high": 1, "normal": 2}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))
    return recommendations


def get_order_fulfillment(db: Session, order_id: int) -> Dict[str, Any]:
    """
    For a given order, determine which batches can fulfill each line item.
    Returns fulfillment plan with batch assignments and gaps.
    """
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        return {"error": "Order not found"}

    fulfillment = {
        "order_id": order.order_id,
        "client": order.client_name,
        "city": order.city,
        "delivery_date": order.delivery_date.isoformat(),
        "line_items": []
    }

    for oi in order.order_items:
        item = oi.item
        # Find batches that will be ripe on or before delivery date
        usable_batches = (
            db.query(InventoryBatch)
            .filter(
                InventoryBatch.item_id == item.id,
                InventoryBatch.status.in_(["in_stock", "reserved"]),
                InventoryBatch.expected_ripeness_date <= order.delivery_date,
                InventoryBatch.expiry_date >= order.delivery_date
            )
            .order_by(InventoryBatch.expected_ripeness_date)
            .all()
        )

        allocated = []
        remaining = oi.quantity_kg
        for batch in usable_batches:
            if remaining <= 0:
                break
            take = min(batch.quantity_kg, remaining)
            allocated.append({
                "batch_id": batch.batch_id,
                "quantity_kg": round(take, 1),
                "ripeness_date": batch.expected_ripeness_date.isoformat(),
                "variety": batch.variety
            })
            remaining -= take

        fulfillment["line_items"].append({
            "item": item.name,
            "sku": item.sku,
            "required_kg": oi.quantity_kg,
            "allocated_kg": round(oi.quantity_kg - remaining, 1),
            "gap_kg": round(max(0, remaining), 1),
            "fulfillable": remaining <= 0,
            "batches": allocated
        })

    return fulfillment
