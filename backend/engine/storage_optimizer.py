"""
Storage Optimizer — LIFO-aware 3D bin-packing placement engine.
Sorts batches by ripeness date (earliest = front/position 0).
Assigns 3D coordinates (row, col, depth) per container.
Detects LIFO conflicts and generates corrective placement maps.
"""
from datetime import date
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class BatchPlacement:
    batch_id: str
    item_name: str
    quantity_kg: float
    expected_ripeness_date: date
    expiry_date: date
    container_id: str
    position_index: int
    row: int
    col: int
    depth: int
    conflict_flag: bool = False
    conflict_reason: str = ""
    ripeness_score: float = 0.0


def calculate_ripeness_score(batch: Any, today: date = None) -> float:
    """Score: 0=unripe, 1=perfect ripe, >1=overripe"""
    if today is None:
        today = date.today()
    peak_date = batch.expected_ripeness_date
    expiry_date = batch.expiry_date
    received_date = batch.received_date

    total_days = (expiry_date - received_date).days or 1
    days_elapsed = (today - received_date).days
    peak_day = (peak_date - received_date).days or 1

    if days_elapsed < 0:
        return 0.0
    elif days_elapsed <= peak_day:
        return round(days_elapsed / peak_day, 3)
    else:
        over = days_elapsed - peak_day
        remaining = max(1, (expiry_date - peak_date).days)
        return round(1.0 + (over / remaining), 3)


def optimize_container(
    batches: List[Any],
    container: Any,
    today: date = None
) -> Tuple[List[BatchPlacement], List[Dict]]:
    """
    Sort batches by expected_ripeness_date ascending (earliest ripe first = position 0).
    Assign 3D grid coordinates. Detect conflicts.
    Returns: (placements, conflicts)
    """
    if today is None:
        today = date.today()

    # Only place active batches
    active = [b for b in batches if b.status in ("in_stock", "reserved", "at_risk")]
    if not active:
        return [], []

    # Sort: earliest ripeness first (should be at front/exit)
    sorted_batches = sorted(active, key=lambda b: b.expected_ripeness_date)

    rows = container.rows
    cols = container.cols
    depths = container.depths
    total_positions = rows * cols * depths

    placements = []
    conflicts = []

    for idx, batch in enumerate(sorted_batches):
        if idx >= total_positions:
            break

        # 3D coordinate assignment
        # depth 0 = front (exit side), depth N = deepest
        # position_index 0 = most accessible
        pos = idx
        row = pos // (cols * depths)
        col = (pos // depths) % cols
        depth = pos % depths

        ripeness_score = calculate_ripeness_score(batch, today)

        # Conflict: a batch at a deeper position that is riper than the one in front
        conflict = False
        conflict_reason = ""
        if idx > 0:
            prev = sorted_batches[idx - 1]
            if batch.expected_ripeness_date < prev.expected_ripeness_date:
                conflict = True
                conflict_reason = (
                    f"Earlier ripening batch ({batch.batch_id}, ripes {batch.expected_ripeness_date}) "
                    f"is behind later ripening batch ({prev.batch_id}, ripes {prev.expected_ripeness_date})"
                )
                conflicts.append({
                    "batch_id": batch.batch_id,
                    "conflict_reason": conflict_reason,
                    "container": container.container_id
                })

        placement = BatchPlacement(
            batch_id=batch.batch_id,
            item_name=batch.item.name if hasattr(batch, 'item') and batch.item else "Unknown",
            quantity_kg=batch.quantity_kg,
            expected_ripeness_date=batch.expected_ripeness_date,
            expiry_date=batch.expiry_date,
            container_id=container.container_id,
            position_index=pos,
            row=row, col=col, depth=depth,
            conflict_flag=conflict,
            conflict_reason=conflict_reason,
            ripeness_score=ripeness_score
        )
        placements.append(placement)

    return placements, conflicts


def get_recommended_position(
    new_batch_ripeness_date: date,
    existing_batches: List[Any],
    container: Any
) -> Dict[str, Any]:
    """
    Given a new batch's ripeness date, find the correct 3D position in a container.
    """
    active = [b for b in existing_batches if b.status in ("in_stock", "reserved")]
    sorted_existing = sorted(active, key=lambda b: b.expected_ripeness_date)

    # Find insert position (where new batch fits chronologically)
    insert_pos = len(sorted_existing)
    for i, b in enumerate(sorted_existing):
        if new_batch_ripeness_date <= b.expected_ripeness_date:
            insert_pos = i
            break

    rows, cols, depths = container.rows, container.cols, container.depths
    total = rows * cols * depths

    if insert_pos >= total:
        return {
            "feasible": False,
            "message": f"Container {container.container_id} is full ({total} positions occupied)",
            "position_index": None, "row": None, "col": None, "depth": None
        }

    row = insert_pos // (cols * depths)
    col = (insert_pos // depths) % cols
    depth = insert_pos % depths

    return {
        "feasible": True,
        "container_id": container.container_id,
        "position_index": insert_pos,
        "row": row, "col": col, "depth": depth,
        "message": f"Place at row={row}, col={col}, depth={depth} (position {insert_pos} of {total}). "
                   f"This ensures LIFO order: your batch (ripes {new_batch_ripeness_date}) will be accessible before deeper batches."
    }


def check_all_conflicts(batches_by_container: Dict[str, List[Any]]) -> List[Dict]:
    """Check all containers for LIFO violations"""
    all_conflicts = []
    for container_id, batches in batches_by_container.items():
        active = [b for b in batches if b.status in ("in_stock", "reserved", "at_risk")]
        sorted_b = sorted(active, key=lambda b: b.position_index)
        for i in range(1, len(sorted_b)):
            curr = sorted_b[i]
            prev = sorted_b[i - 1]
            if curr.expected_ripeness_date < prev.expected_ripeness_date:
                all_conflicts.append({
                    "container_id": container_id,
                    "batch_id": curr.batch_id,
                    "position": i,
                    "issue": f"Batch {curr.batch_id} (ripes {curr.expected_ripeness_date}) is behind "
                             f"batch {prev.batch_id} (ripes {prev.expected_ripeness_date}) — LIFO violation"
                })
    return all_conflicts
