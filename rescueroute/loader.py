"""Read the three input CSV files from a data folder."""

import csv
from pathlib import Path

from .models import Dataset, ValidationIssue
from .validation import (
    DONATION_COLUMNS,
    DONATIONS_FILE,
    RECIPIENT_COLUMNS,
    RECIPIENTS_FILE,
    VOLUNTEER_COLUMNS,
    VOLUNTEERS_FILE,
    Row,
    build_dataset,
)


class DataFileError(Exception):
    """A required data folder or file is missing."""


def read_csv_rows(path: Path, required_columns: tuple[str, ...]) -> tuple[list[Row], list[ValidationIssue]]:
    """Return (rows, file-level issues). Rows keep their line numbers for error messages."""
    if not path.is_file():
        raise DataFileError(f"Required data file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], [
                ValidationIssue(path.name, 1, None, "(file)",
                                f"{path.name} is empty (no header row); treated as having no records.")
            ]

        headers = {name.strip() for name in reader.fieldnames if name}
        missing = [column for column in required_columns if column not in headers]
        if missing:
            return [], [
                ValidationIssue(path.name, 1, None, ", ".join(missing),
                                f"{path.name} rejected — missing required column(s): {', '.join(missing)}. "
                                "No rows from this file were loaded.")
            ]

        rows: list[Row] = []
        for raw in reader:
            row = {key.strip(): (value or "").strip() for key, value in raw.items() if isinstance(key, str)}
            if any(row.values()):  # skip blank lines
                rows.append((reader.line_num, row))
    return rows, []


def load_dataset(data_dir: str | Path) -> Dataset:
    """Load and validate donations, recipients, and volunteers from one folder."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise DataFileError(f"Data folder not found: {data_dir}")

    donation_rows, donation_file_issues = read_csv_rows(data_dir / DONATIONS_FILE, DONATION_COLUMNS)
    recipient_rows, recipient_file_issues = read_csv_rows(data_dir / RECIPIENTS_FILE, RECIPIENT_COLUMNS)
    volunteer_rows, volunteer_file_issues = read_csv_rows(data_dir / VOLUNTEERS_FILE, VOLUNTEER_COLUMNS)

    dataset = build_dataset(donation_rows, recipient_rows, volunteer_rows)
    dataset.issues = donation_file_issues + recipient_file_issues + volunteer_file_issues + dataset.issues
    return dataset
