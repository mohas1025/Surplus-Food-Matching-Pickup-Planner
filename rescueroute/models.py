"""Core data model for RescueRoute.

Input records (Donation, Recipient, Volunteer) are immutable. Anything that
changes during scheduling (remaining capacity, volunteer position) lives in
separate run-state objects in matching.py, so scheduling never modifies the
validated input.

All times are minutes since midnight on one simulated day.
"""

from dataclasses import dataclass, field

# Decision statuses
ASSIGNED = "assigned"
UNASSIGNED = "unassigned"


@dataclass(frozen=True)
class Donation:
    donation_id: str
    donor_name: str
    food_type: str
    quantity_lbs: int
    posted_time: int
    ready_time: int
    expiry_time: int
    pickup_area: str


@dataclass(frozen=True)
class Recipient:
    recipient_id: str
    org_name: str
    accepted_food_types: frozenset[str]
    capacity_lbs: int
    area: str
    closing_time: int


@dataclass(frozen=True)
class Volunteer:
    volunteer_id: str
    volunteer_name: str
    vehicle_capacity_lbs: int
    area: str
    available_from: int
    available_until: int
    max_pickups: int


@dataclass(frozen=True)
class Assignment:
    """One decision about one donation, with its human-readable reason."""

    donation_id: str
    status: str
    reason: str
    recipient_id: str | None = None
    volunteer_id: str | None = None
    pickup_time: int | None = None
    delivery_time: int | None = None


@dataclass(frozen=True)
class ValidationIssue:
    """A problem found in an input row. The row is skipped; others still load."""

    file: str
    row: int
    record_id: str | None
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.file} row {self.row}: {self.message}"


@dataclass
class Dataset:
    """Validated input ready for scheduling."""

    donations: list[Donation] = field(default_factory=list)
    recipients: dict[str, Recipient] = field(default_factory=dict)
    volunteers: dict[str, Volunteer] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
