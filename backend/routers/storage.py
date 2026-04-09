from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, StorageContainer, InventoryBatch, StoragePlacement, AuditLog
from engine.storage_optimizer import optimize_container, get_recommended_position, check_all_conflicts
from engine.event_bus import event_bus, Event, EventType
from datetime import date
from collections import defaultdict

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/containers")
def get_containers(db: Session = Depends(get_db)):
    containers = db.query(StorageContainer).filter(StorageContainer.is_active == True).all()
    return [_format_container(c, db) for c in containers]


@router.get("/layout")
def get_storage_layout(db: Session = Depends(get_db)):
    containers = db.query(StorageContainer).filter(StorageContainer.is_active == True).all()
    layout = []
    for c in containers:
        batches = (
            db.query(InventoryBatch)
            .filter(
                InventoryBatch.container_id == c.id,
                InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
            )
            .order_by(InventoryBatch.position_index)
            .all()
        )
        placements = []
        for b in batches:
            ri = b.item if b.item else None
            placements.append({
                "batch_id": b.batch_id,
                "item_name": ri.name if ri else "Unknown",
                "sku": ri.sku if ri else None,
                "quantity_kg": b.quantity_kg,
                "variety": b.variety,
                "position_index": b.position_index,
                "row": b.row, "col": b.col, "depth": b.depth,
                "expected_ripeness_date": b.expected_ripeness_date.isoformat() if b.expected_ripeness_date else None,
                "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
                "ripeness_score": b.ripeness_score,
                "status": b.status,
                "days_until_ripe": max(0, (b.expected_ripeness_date - date.today()).days) if b.expected_ripeness_date else 0,
            })
        layout.append({
            "container": _format_container(c, db),
            "placements": placements,
            "utilization_pct": round((c.current_load_kg / c.capacity_kg * 100) if c.capacity_kg else 0, 1)
        })
    return layout


@router.post("/optimize")
async def optimize_storage(db: Session = Depends(get_db)):
    containers = db.query(StorageContainer).filter(StorageContainer.is_active == True).all()
    total_moved = 0
    total_conflicts_resolved = 0
    all_conflicts = []

    for c in containers:
        batches = (
            db.query(InventoryBatch)
            .filter(
                InventoryBatch.container_id == c.id,
                InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
            )
            .all()
        )
        placements, conflicts = optimize_container(batches, c)
        all_conflicts.extend(conflicts)

        for p in placements:
            batch = db.query(InventoryBatch).filter(InventoryBatch.batch_id == p.batch_id).first()
            if batch:
                old_pos = batch.position_index
                if (batch.position_index != p.position_index or
                        batch.row != p.row or batch.col != p.col or batch.depth != p.depth):
                    batch.position_index = p.position_index
                    batch.row = p.row
                    batch.col = p.col
                    batch.depth = p.depth
                    total_moved += 1

                # Record placement
                existing_placement = db.query(StoragePlacement).filter(
                    StoragePlacement.batch_id == batch.id, StoragePlacement.is_current == True
                ).first()
                if existing_placement:
                    existing_placement.is_current = False

                db.add(StoragePlacement(
                    batch_id=batch.id, container_id=c.id,
                    position_index=p.position_index,
                    row=p.row, col=p.col, depth=p.depth,
                    conflict_flag=p.conflict_flag,
                    conflict_reason=p.conflict_reason,
                    is_current=True
                ))

        if conflicts:
            total_conflicts_resolved += len(conflicts)

    db.add(AuditLog(
        entity_type="StorageOptimizer", entity_id="all",
        action="OPTIMIZE",
        new_value={"moved": total_moved, "conflicts_resolved": total_conflicts_resolved}
    ))
    db.commit()

    await event_bus.publish(Event(
        EventType.STORAGE_OPTIMIZED,
        {"batches_repositioned": total_moved, "conflicts_resolved": total_conflicts_resolved},
        source="optimizer"
    ))

    return {
        "success": True,
        "batches_repositioned": total_moved,
        "conflicts_resolved": total_conflicts_resolved,
        "remaining_conflicts": all_conflicts
    }


@router.get("/conflicts")
def get_conflicts(db: Session = Depends(get_db)):
    containers = db.query(StorageContainer).all()
    batches_by_container = defaultdict(list)
    all_batches = db.query(InventoryBatch).filter(
        InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
    ).all()
    for b in all_batches:
        if b.container:
            batches_by_container[b.container.container_id].append(b)
    conflicts = check_all_conflicts(dict(batches_by_container))
    return {"total_conflicts": len(conflicts), "conflicts": conflicts}


@router.get("/placement/{batch_id}")
def get_recommended_placement(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(InventoryBatch).filter(InventoryBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    item = batch.item
    containers = db.query(StorageContainer).filter(
        StorageContainer.zone_type == (item.zone if item else "ambient"),
        StorageContainer.is_active == True
    ).all()
    recommendations = []
    for c in containers:
        existing = db.query(InventoryBatch).filter(
            InventoryBatch.container_id == c.id,
            InventoryBatch.status.in_(["in_stock", "reserved"])
        ).all()
        rec = get_recommended_position(batch.expected_ripeness_date, existing, c)
        rec["container_name"] = c.name
        recommendations.append(rec)
    return {"batch_id": batch_id, "recommendations": recommendations}


def _format_container(c: StorageContainer, db: Session) -> dict:
    batch_count = db.query(InventoryBatch).filter(
        InventoryBatch.container_id == c.id,
        InventoryBatch.status.in_(["in_stock", "reserved", "at_risk"])
    ).count()
    return {
        "container_id": c.container_id,
        "name": c.name,
        "zone_type": c.zone_type,
        "capacity_kg": c.capacity_kg,
        "current_load_kg": round(c.current_load_kg, 1),
        "utilization_pct": round((c.current_load_kg / c.capacity_kg * 100) if c.capacity_kg else 0, 1),
        "temp_c": c.temp_c,
        "dimensions": {"rows": c.rows, "cols": c.cols, "depths": c.depths},
        "total_positions": c.rows * c.cols * c.depths,
        "active_batches": batch_count
    }
