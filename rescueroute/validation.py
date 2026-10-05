"""Turn raw CSV rows into validated model objects.

Each invalid row is skipped and produces one ValidationIssue per problem found,
so a single bad row never stops the rest of the data from loading.
"""

import re

from .models import Dataset, Donation, Recipient, ValidationIssue, Volunteer
from .timeutils import format_hhmm, parse_hhmm

KNOWN_FOOD_TYPES = frozenset(
    {"prepared_meals", "produce", "bakery", "dairy", "canned_goods", "frozen"}
)
KNOWN_AREAS = frozenset({"Downtown", "Campus", "Northside", "Eastside", "Westside"})
_AREA_BY_LOWER = {area.lower(): area for area in KNOWN_AREAS}

DONATIONS_FILE = "donations.csv"
RECIPIENTS_FILE = "recipients.csv"
VOLUNTEERS_FILE = "volunteers.csv"

DONATION_COLUMNS = (
    "donation_id", "donor_name", "food_type", "quantity_lbs",
    "posted_time", "ready_time", "expiry_time", "pickup_area",
)
RECIPIENT_COLUMNS = (
    "recipient_id", "org_name", "accepted_food_types",
    "capacity_lbs", "area", "closing_time",
)
VOLUNTEER_COLUMNS = (
    "volunteer_id", "volunteer_name", "vehicle_capacity_lbs", "area",
    "available_from", "available_until", "max_pickups",
)

DONATION_ID = re.compile(r"^D-\d{4}$")
RECIPIENT_ID = re.compile(r"^R-\d{3}$")
VOLUNTEER_ID = re.compile(r"^V-\d{3}$")

# A row is (line number in the file, {column: value}).
Row = tuple[int, dict[str, str]]


def number_rows(rows: list[dict]) -> list[Row]:
    """Attach line numbers to in-memory rows as if they came from a CSV (header = line 1)."""
    return [(line, row) for line, row in enumerate(rows, start=2)]


class _RowChecker:
    """Reads fields from one row and records every problem it finds."""

    def __init__(self, file: str, line: int, entity: str, row: dict, id_column: str):
        self.file = file
        self.line = line
        self.entity = entity
        self.row = row
        self.record_id = self.raw(id_column) or None
        self.issues: list[ValidationIssue] = []

    def raw(self, column: str) -> str:
        value = self.row.get(column)
        return "" if value is None else str(value).strip()

    def fail(self, column: str, problem: str) -> None:
        who = f"{self.entity} {self.record_id}" if self.record_id else f"{self.entity} with no ID"
        self.issues.append(
            ValidationIssue(self.file, self.line, self.record_id, column, f"{who} rejected — {problem}.")
        )

    def text(self, column: str) -> str | None:
        value = self.raw(column)
        if not value:
            self.fail(column, f"{column} is required but empty")
            return None
        return value

    def record_id_matching(self, column: str, pattern: re.Pattern, example: str) -> str | None:
        value = self.text(column)
        if value is not None and not pattern.match(value):
            self.fail(column, f"{column} '{value}' does not match the required format (e.g. {example})")
            return None
        return value

    def positive_int(self, column: str) -> int | None:
        value = self.text(column)
        if value is None:
            return None
        try:
            number = int(value)
        except ValueError:
            number = 0
        if number <= 0:
            self.fail(column, f"{column} must be a positive whole number (got '{value}')")
            return None
        return number

    def time(self, column: str) -> int | None:
        value = self.text(column)
        if value is None:
            return None
        try:
            return parse_hhmm(value)
        except ValueError as error:
            self.fail(column, f"{column} {error}")
            return None

    def area(self, column: str) -> str | None:
        value = self.text(column)
        if value is None:
            return None
        canonical = _AREA_BY_LOWER.get(value.lower())
        if canonical is None:
            self.fail(column, f"{column} '{value}' is not a known area ({', '.join(sorted(KNOWN_AREAS))})")
        return canonical

    def food_type(self, column: str) -> str | None:
        value = self.text(column)
        if value is None:
            return None
        food = value.lower()
        if food not in KNOWN_FOOD_TYPES:
            self.fail(column, f"{column} '{value}' is not a known food type ({', '.join(sorted(KNOWN_FOOD_TYPES))})")
            return None
        return food

    def food_type_set(self, column: str) -> frozenset[str] | None:
        value = self.text(column)
        if value is None:
            return None
        foods = {part.strip().lower() for part in value.split(";") if part.strip()}
        unknown = sorted(foods - KNOWN_FOOD_TYPES)
        if not foods:
            self.fail(column, f"{column} must list at least one food type")
            return None
        if unknown:
            self.fail(column, f"{column} contains unknown food type(s): {', '.join(unknown)}")
            return None
        return frozenset(foods)


def _check_duplicate(checker: _RowChecker, column: str, first_seen_row: dict[str, int]) -> None:
    """Reject a repeated ID. The first occurrence of an ID is the one that counts."""
    record_id = checker.record_id
    if record_id is None:
        return
    if record_id in first_seen_row:
        checker.fail(column, f"duplicate {column} (already used on row {first_seen_row[record_id]})")
    else:
        first_seen_row[record_id] = checker.line


def validate_donations(rows: list[Row], file: str = DONATIONS_FILE) -> tuple[list[Donation], list[ValidationIssue]]:
    donations: list[Donation] = []
    issues: list[ValidationIssue] = []
    first_seen_row: dict[str, int] = {}

    for line, row in rows:
        check = _RowChecker(file, line, "donation", row, "donation_id")
        donation_id = check.record_id_matching("donation_id", DONATION_ID, "D-1001")
        _check_duplicate(check, "donation_id", first_seen_row)
        donor_name = check.text("donor_name")
        food_type = check.food_type("food_type")
        quantity = check.positive_int("quantity_lbs")
        posted = check.time("posted_time")
        ready = check.time("ready_time")
        expiry = check.time("expiry_time")
        area = check.area("pickup_area")

        if posted is not None and ready is not None and posted > ready:
            check.fail("posted_time", f"posted_time {format_hhmm(posted)} is after ready_time {format_hhmm(ready)}")
        if ready is not None and expiry is not None and expiry <= ready:
            check.fail(
                "expiry_time",
                f"already expired: expiry_time {format_hhmm(expiry)} is not after ready_time {format_hhmm(ready)}",
            )

        if check.issues:
            issues.extend(check.issues)
            continue
        donations.append(Donation(donation_id, donor_name, food_type, quantity, posted, ready, expiry, area))

    return donations, issues


def validate_recipients(rows: list[Row], file: str = RECIPIENTS_FILE) -> tuple[dict[str, Recipient], list[ValidationIssue]]:
    recipients: dict[str, Recipient] = {}
    issues: list[ValidationIssue] = []
    first_seen_row: dict[str, int] = {}

    for line, row in rows:
        check = _RowChecker(file, line, "recipient", row, "recipient_id")
        recipient_id = check.record_id_matching("recipient_id", RECIPIENT_ID, "R-201")
        _check_duplicate(check, "recipient_id", first_seen_row)
        org_name = check.text("org_name")
        accepted = check.food_type_set("accepted_food_types")
        capacity = check.positive_int("capacity_lbs")
        area = check.area("area")
        closing = check.time("closing_time")

        if check.issues:
            issues.extend(check.issues)
            continue
        recipients[recipient_id] = Recipient(recipient_id, org_name, accepted, capacity, area, closing)

    return recipients, issues


def validate_volunteers(rows: list[Row], file: str = VOLUNTEERS_FILE) -> tuple[dict[str, Volunteer], list[ValidationIssue]]:
    volunteers: dict[str, Volunteer] = {}
    issues: list[ValidationIssue] = []
    first_seen_row: dict[str, int] = {}

    for line, row in rows:
        check = _RowChecker(file, line, "volunteer", row, "volunteer_id")
        volunteer_id = check.record_id_matching("volunteer_id", VOLUNTEER_ID, "V-301")
        _check_duplicate(check, "volunteer_id", first_seen_row)
        name = check.text("volunteer_name")
        vehicle = check.positive_int("vehicle_capacity_lbs")
        area = check.area("area")
        start = check.time("available_from")
        end = check.time("available_until")
        max_pickups = check.positive_int("max_pickups")

        if start is not None and end is not None and start >= end:
            check.fail(
                "available_until",
                f"available_until {format_hhmm(end)} is not after available_from {format_hhmm(start)}",
            )

        if check.issues:
            issues.extend(check.issues)
            continue
        volunteers[volunteer_id] = Volunteer(volunteer_id, name, vehicle, area, start, end, max_pickups)

    return volunteers, issues


def build_dataset(donation_rows: list[Row], recipient_rows: list[Row], volunteer_rows: list[Row]) -> Dataset:
    """Validate all three tables and collect their issues in one Dataset."""
    donations, donation_issues = validate_donations(donation_rows)
    recipients, recipient_issues = validate_recipients(recipient_rows)
    volunteers, volunteer_issues = validate_volunteers(volunteer_rows)
    return Dataset(donations, recipients, volunteers, donation_issues + recipient_issues + volunteer_issues)
