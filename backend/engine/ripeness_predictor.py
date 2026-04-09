"""
Ripeness Predictor — sigmoid-curve ripeness model per item category.
Accounts for storage temperature deviations and predicts exact ripeness dates.
"""
import math
from datetime import date, timedelta
from typing import Dict, Any, Optional


# Category-specific sigmoid parameters
RIPENESS_PROFILES = {
    "sigmoid": {"k": 0.8, "midpoint_ratio": 0.5},
    "fast_sigmoid": {"k": 1.5, "midpoint_ratio": 0.4},
    "slow_sigmoid": {"k": 0.4, "midpoint_ratio": 0.6},
    "linear": {"k": None, "midpoint_ratio": 0.5},
    "flat": {"k": 0.2, "midpoint_ratio": 0.8},
}

# Temperature acceleration factor: for every 1°C above optimal max, ripeness speeds up by this factor
TEMP_ACCELERATION_FACTOR = 0.05  # 5% faster per degree C above optimal


def sigmoid(x: float, k: float = 1.0, midpoint: float = 0.5) -> float:
    """Sigmoid function: returns 0..1 ripeness score"""
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - midpoint)))
    except OverflowError:
        return 1.0 if x > midpoint else 0.0


def calculate_ripeness_score(
    ripeness_curve: str,
    peak_day: int,
    shelf_life_days: int,
    days_since_received: int
) -> float:
    """
    Returns ripeness score: 0.0=completely unripe, 1.0=perfectly ripe, 2.0=overripe/expired
    """
    if days_since_received < 0:
        return 0.0

    profile = RIPENESS_PROFILES.get(ripeness_curve, RIPENESS_PROFILES["sigmoid"])
    x_normalized = days_since_received / max(1, shelf_life_days)

    if ripeness_curve == "linear":
        score = x_normalized * 2.0  # Linear 0 → 2 over shelf life
    elif profile["k"] is None:
        score = x_normalized * 2.0
    else:
        k = profile["k"]
        mid = profile["midpoint_ratio"]
        # Scale sigmoid to produce 1.0 at peak_day
        peak_normalized = peak_day / max(1, shelf_life_days)
        score = sigmoid(x_normalized, k=k * 6, midpoint=peak_normalized) * 2.0
    
    return round(min(2.5, max(0.0, score)), 3)


def temperature_adjusted_ripeness_days(
    base_ripeness_days: int,
    optimal_max_temp: float,
    actual_temp: float
) -> int:
    """Adjust ripeness timeline based on actual vs optimal temperature"""
    if actual_temp <= optimal_max_temp:
        return base_ripeness_days
    excess_temp = actual_temp - optimal_max_temp
    acceleration = 1.0 + (excess_temp * TEMP_ACCELERATION_FACTOR)
    adjusted = base_ripeness_days / acceleration
    return max(1, int(adjusted))


def predict_ripeness_date(
    received_date: date,
    ripeness_curve: str,
    peak_day: int,
    shelf_life_days: int,
    optimal_max_temp: float,
    actual_temp: Optional[float] = None
) -> Dict[str, Any]:
    """
    Predict when a batch will be at peak ripeness.
    Returns a dict with date, confidence, and human-readable status.
    """
    adjusted_peak = peak_day
    temp_note = ""

    if actual_temp is not None:
        adjusted_peak = temperature_adjusted_ripeness_days(peak_day, optimal_max_temp, actual_temp)
        if adjusted_peak != peak_day:
            temp_change = peak_day - adjusted_peak
            temp_note = (
                f"Storage temp is {actual_temp}°C (above optimal {optimal_max_temp}°C), "
                f"accelerating ripeness by {temp_change} days."
            )

    ripeness_date = received_date + timedelta(days=adjusted_peak)
    expiry_date = received_date + timedelta(days=shelf_life_days)
    today = date.today()
    days_until_ripe = (ripeness_date - today).days

    if days_until_ripe < 0:
        status = "overripe" if (today - ripeness_date).days < (shelf_life_days - adjusted_peak) else "expired"
    elif days_until_ripe == 0:
        status = "ripe_today"
    elif days_until_ripe <= 2:
        status = "ripening_soon"
    elif days_until_ripe <= 5:
        status = "maturing"
    else:
        status = "unripe"

    # Confidence based on curve type
    confidence_map = {
        "sigmoid": 0.88,
        "fast_sigmoid": 0.85,
        "slow_sigmoid": 0.82,
        "linear": 0.90,
        "flat": 0.75,
    }
    confidence = confidence_map.get(ripeness_curve, 0.80)
    if actual_temp and abs(actual_temp - optimal_max_temp) > 3:
        confidence -= 0.10

    return {
        "predicted_ripeness_date": ripeness_date.isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "days_until_ripe": max(0, days_until_ripe),
        "status": status,
        "confidence": round(confidence, 2),
        "adjusted_peak_day": adjusted_peak,
        "original_peak_day": peak_day,
        "temperature_note": temp_note,
        "recommendation": _get_recommendation(status, days_until_ripe, ripeness_date, expiry_date)
    }


def _get_recommendation(status: str, days_until: int, ripeness_date: date, expiry_date: date) -> str:
    days_to_expiry = (expiry_date - date.today()).days
    if status == "ripe_today":
        return "🟢 Use today — batch is at peak ripeness. Prioritize for today's deliveries."
    elif status == "ripening_soon":
        return f"🟡 Ripens in {days_until} day(s). Reserve for upcoming deliveries. Move to front of storage."
    elif status == "maturing":
        return f"🔵 Still maturing — ripe in {days_until} days. Ensure correct storage position."
    elif status == "unripe":
        return f"⚪ Unripe — ripe in {days_until} days (by {ripeness_date}). Store deep, do not rush to front."
    elif status == "overripe":
        return f"🔴 Overripe! {days_to_expiry} day(s) left before expiry. Use immediately or markdown."
    elif status == "expired":
        return "❌ EXPIRED — remove from storage immediately. Do not use for delivery."
    return "Check storage conditions."


def batch_ripeness_timeline(batches: list, window_days: int = 14) -> list:
    """
    For a list of batches, return a timeline of which are ripe on each day.
    Useful for the frontend RipenessTimeline chart.
    """
    today = date.today()
    timeline = []
    for day_offset in range(window_days):
        check_date = today + timedelta(days=day_offset)
        ripe_batches = []
        for b in batches:
            if hasattr(b, 'expected_ripeness_date') and b.expected_ripeness_date == check_date:
                ripe_batches.append({
                    "batch_id": b.batch_id,
                    "item_name": b.item.name if hasattr(b, 'item') and b.item else "Unknown",
                    "quantity_kg": b.quantity_kg,
                    "status": b.status
                })
        timeline.append({
            "date": check_date.isoformat(),
            "day_label": f"{'Today' if day_offset == 0 else f'Day +{day_offset}'}",
            "ripe_count": len(ripe_batches),
            "ripe_kg": sum(x["quantity_kg"] for x in ripe_batches),
            "batches": ripe_batches
        })
    return timeline
