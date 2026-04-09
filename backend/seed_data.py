"""
Seed Data Generator — creates 500+ realistic perishable inventory records
Run once on startup if DB is empty.
"""
import random
import uuid
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from database import (
    SessionLocal, create_tables, PerishableItem, StorageContainer,
    InventoryBatch, DeliveryOrder, OrderItem, AIInsight, AuditLog
)
from data.catalog import PERISHABLES_CATALOG, STORAGE_CONTAINERS, CITIES, CLIENT_NAMES


def generate_batch_id():
    return f"BAT-{uuid.uuid4().hex[:8].upper()}"


def generate_order_id():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def seed_perishable_items(db: Session):
    if db.query(PerishableItem).count() > 0:
        return
    print("  → Seeding perishable items catalog...")
    for p in PERISHABLES_CATALOG:
        item = PerishableItem(
            sku=p["sku"], name=p["name"], category=p["category"],
            unit=p["unit"], reorder_point_kg=p["reorder_point_kg"],
            lead_days=p["lead_days"], storage_temp_min_c=p["storage_temp_min_c"],
            storage_temp_max_c=p["storage_temp_max_c"], shelf_life_days=p["shelf_life_days"],
            ripeness_curve=p["ripeness_curve"], ripeness_peak_day=p["ripeness_peak_day"],
            zone=p["zone"], varieties=p["varieties"]
        )
        db.add(item)
    db.commit()
    print(f"  ✓ {len(PERISHABLES_CATALOG)} perishable items seeded")


def seed_containers(db: Session):
    if db.query(StorageContainer).count() > 0:
        return
    print("  → Seeding storage containers...")
    for c in STORAGE_CONTAINERS:
        container = StorageContainer(
            container_id=c["container_id"], name=c["name"],
            zone_type=c["zone_type"], capacity_kg=c["capacity_kg"],
            rows=c["rows"], cols=c["cols"], depths=c["depths"],
            temp_c=c["temp_c"]
        )
        db.add(container)
    db.commit()
    print(f"  ✓ {len(STORAGE_CONTAINERS)} containers seeded")


def seed_inventory_batches(db: Session):
    if db.query(InventoryBatch).count() > 0:
        return
    print("  → Seeding 5000+ inventory batches...")
    items = db.query(PerishableItem).all()
    containers = db.query(StorageContainer).all()
    container_map = {c.zone_type: [] for c in containers}
    for c in containers:
        container_map[c.zone_type].append(c)

    today = date.today()
    batches_created = 0
    position_tracker = {}  # container_id -> next position index

    for item in items:
        # 150–250 batches per item (approx ~5000+ total)
        num_batches = random.randint(150, 250)
        matching_containers = container_map.get(item.zone, container_map.get("ambient", []))
        if not matching_containers:
            matching_containers = containers

        for i in range(num_batches):
            # Received anywhere from 10 days ago to 2 days ago
            days_ago = random.randint(0, 10)
            received = today - timedelta(days=days_ago)
            # Ripeness in peak_day ± 2 days from received
            ripeness_offset = item.ripeness_peak_day + random.randint(-1, 2)
            ripeness_date = received + timedelta(days=ripeness_offset)
            expiry_date = received + timedelta(days=item.shelf_life_days + random.randint(-1, 2))

            container = random.choice(matching_containers)
            cid = container.id
            if cid not in position_tracker:
                position_tracker[cid] = 0
            pos = position_tracker[cid]
            position_tracker[cid] += 1

            max_cells = container.rows * container.cols * container.depths
            row = (pos // (container.cols * container.depths)) % container.rows
            col = (pos // container.depths) % container.cols
            depth = pos % container.depths

            # Ripeness score based on days since received vs peak day
            days_since = (today - received).days
            if days_since < item.ripeness_peak_day:
                ripeness_score = round(days_since / item.ripeness_peak_day, 2)
            elif days_since == item.ripeness_peak_day:
                ripeness_score = 1.0
            else:
                ripeness_score = round(min(2.0, 1.0 + (days_since - item.ripeness_peak_day) / item.ripeness_peak_day), 2)

            # Status
            if expiry_date < today:
                status = random.choice(["expired", "wasted"])
            elif ripeness_score >= 1.8:
                status = "at_risk"
            else:
                status = random.choice(["in_stock", "in_stock", "in_stock", "reserved"])

            variety = random.choice(item.varieties) if item.varieties else None
            qty = round(random.uniform(20, 150), 1)
            temp_actual = round(item.storage_temp_min_c + random.uniform(0, 3), 1)

            batch = InventoryBatch(
                batch_id=generate_batch_id(),
                item_id=item.id,
                container_id=container.id,
                quantity_kg=qty,
                variety=variety,
                received_date=received,
                expected_ripeness_date=ripeness_date,
                expiry_date=expiry_date,
                storage_temp_actual_c=temp_actual,
                position_index=pos % max_cells,
                row=row, col=col, depth=depth,
                status=status,
                ripeness_score=ripeness_score
            )
            db.add(batch)
            container.current_load_kg = min(container.capacity_kg, container.current_load_kg + qty)
            batches_created += 1

    db.commit()
    print(f"  ✓ {batches_created} inventory batches seeded")


def seed_orders(db: Session):
    if db.query(DeliveryOrder).count() > 0:
        return
    print("  → Seeding 200+ delivery orders...")
    items = db.query(PerishableItem).all()
    today = date.today()
    orders_created = 0

    clients = CLIENT_NAMES[:50]

    for i in range(200):
        client = random.choice(clients)
        city = random.choice(CITIES)
        days_ahead = random.randint(1, 60)
        delivery_date = today + timedelta(days=days_ahead)
        priority = random.choices(
            ["low", "normal", "high", "urgent"],
            weights=[10, 60, 20, 10]
        )[0]
        status = random.choices(
            ["pending", "confirmed", "fulfilled"],
            weights=[50, 35, 15]
        )[0]

        order = DeliveryOrder(
            order_id=generate_order_id(),
            client_name=client,
            city=city,
            delivery_date=delivery_date,
            status=status,
            priority=priority
        )
        db.add(order)
        db.flush()

        # 1–5 line items per order
        num_items = random.randint(1, 5)
        selected_items = random.sample(items, min(num_items, len(items)))
        for item in selected_items:
            qty = round(random.uniform(20, 200), 1)
            unit_price = round(random.uniform(30, 300), 2)
            oi = OrderItem(
                order_id=order.id, item_id=item.id,
                quantity_kg=qty,
                fulfilled_kg=qty if status == "fulfilled" else 0.0,
                unit_price=unit_price
            )
            db.add(oi)

        orders_created += 1

    db.commit()
    print(f"  ✓ {orders_created} delivery orders seeded")


def seed_ai_insights(db: Session):
    if db.query(AIInsight).count() > 0:
        return
    print("  → Seeding initial AI insights...")
    insights = [
        {
            "insight_type": "expiry_alert",
            "title": "Strawberries Expiring in 24 Hours",
            "message": "3 batches of Strawberries (total 85kg) in REF-A are expiring tomorrow. Prioritize for next delivery or markdown immediately.",
            "severity": "critical"
        },
        {
            "insight_type": "stock_low",
            "title": "Banana Stock Below Reorder Point",
            "message": "Current usable banana stock (ripe within 3 days) is 145kg against a reorder point of 200kg. Recommend ordering 120kg from supplier by today.",
            "severity": "warning"
        },
        {
            "insight_type": "placement_conflict",
            "title": "LIFO Conflict Detected in Ambient Zone A",
            "message": "Batch BAT-CONFLICT01 (ripens in 2 days) is stored behind BAT-CONFLICT02 (ripens in 5 days). Re-optimize container layout to prevent delivery failure.",
            "severity": "warning"
        },
        {
            "insight_type": "demand_gap",
            "title": "Avocado Demand Exceeds Supply Next Week",
            "message": "Upcoming orders require 180kg of Avocados by Friday but only 95kg of ripe-ready stock available. Order 100kg by Wednesday (lead time: 3 days).",
            "severity": "critical"
        },
        {
            "insight_type": "stock_low",
            "title": "Spinach Running Low",
            "message": "Spinach stock at 65kg, below 80kg reorder point. Shelf life is only 5 days — order 60kg today for weekend deliveries.",
            "severity": "warning"
        },
        {
            "insight_type": "expiry_alert",
            "title": "Salmon Batches Approaching Expiry",
            "message": "Two Salmon batches (45kg total) expire in 36 hours. Flag for priority delivery to Chennai or Bangalore routes today.",
            "severity": "critical"
        },
    ]
    for ins in insights:
        ai = AIInsight(
            insight_id=f"INS-{uuid.uuid4().hex[:8].upper()}",
            **ins
        )
        db.add(ai)
    db.commit()
    print(f"  ✓ {len(insights)} AI insights seeded")


def run_seed():
    create_tables()
    db = SessionLocal()
    try:
        print("\n🌱 Seeding SISM database...")
        seed_perishable_items(db)
        seed_containers(db)
        seed_inventory_batches(db)
        seed_orders(db)
        seed_ai_insights(db)
        print("✅ Database seeding complete!\n")
    except Exception as e:
        print(f"❌ Seeding error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
