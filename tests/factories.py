"""Small builders for test input. Each returns a CSV-style row (all values strings)."""

from rescueroute.models import Dataset
from rescueroute.validation import build_dataset, number_rows


def _row(defaults: dict, overrides: dict) -> dict:
    row = dict(defaults)
    row.update({key: str(value) for key, value in overrides.items()})
    return row


def donation_row(**overrides) -> dict:
    return _row({
        "donation_id": "D-1001", "donor_name": "Test Donor", "food_type": "prepared_meals",
        "quantity_lbs": "40", "posted_time": "12:00", "ready_time": "12:30",
        "expiry_time": "15:00", "pickup_area": "Downtown",
    }, overrides)


def recipient_row(**overrides) -> dict:
    return _row({
        "recipient_id": "R-201", "org_name": "Test Shelter",
        "accepted_food_types": "prepared_meals;produce", "capacity_lbs": "100",
        "area": "Downtown", "closing_time": "20:00",
    }, overrides)


def volunteer_row(**overrides) -> dict:
    return _row({
        "volunteer_id": "V-301", "volunteer_name": "Alex", "vehicle_capacity_lbs": "60",
        "area": "Downtown", "available_from": "12:00", "available_until": "18:00",
        "max_pickups": "3",
    }, overrides)


def make_dataset(donations=(), recipients=(), volunteers=()) -> Dataset:
    """Validate in-memory rows exactly as rows from CSV files would be."""
    return build_dataset(number_rows(list(donations)), number_rows(list(recipients)),
                         number_rows(list(volunteers)))
