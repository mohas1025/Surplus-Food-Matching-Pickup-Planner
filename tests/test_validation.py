"""Tests for loading and validating input data."""

from pathlib import Path

import pytest

from factories import donation_row, make_dataset, recipient_row, volunteer_row
from rescueroute.fifo import run_fifo
from rescueroute.loader import load_dataset
from rescueroute.validation import DONATION_COLUMNS, RECIPIENT_COLUMNS


def write_csv(folder: Path, name: str, header: tuple[str, ...], *lines: str) -> None:
    (folder / name).write_text(",".join(header) + "\n" + "".join(line + "\n" for line in lines))


def test_valid_rows_become_model_objects():
    dataset = make_dataset([donation_row()], [recipient_row()], [volunteer_row()])

    assert dataset.issues == []
    donation = dataset.donations[0]
    assert donation.donation_id == "D-1001"
    assert donation.quantity_lbs == 40
    assert donation.ready_time == 12 * 60 + 30
    assert dataset.recipients["R-201"].accepted_food_types == {"prepared_meals", "produce"}
    assert dataset.volunteers["V-301"].max_pickups == 3


def test_duplicate_donation_id_keeps_first_and_rejects_second():
    dataset = make_dataset([
        donation_row(donation_id="D-1001", donor_name="Original"),
        donation_row(donation_id="D-1001", donor_name="Copy"),
    ])

    assert [d.donor_name for d in dataset.donations] == ["Original"]
    assert len(dataset.issues) == 1
    issue = dataset.issues[0]
    assert issue.row == 3 and issue.field == "donation_id"
    assert "duplicate donation_id (already used on row 2)" in issue.message


def test_already_expired_donation_is_rejected():
    dataset = make_dataset([donation_row(ready_time="14:00", expiry_time="13:30")])

    assert dataset.donations == []
    assert len(dataset.issues) == 1
    assert dataset.issues[0].field == "expiry_time"
    assert "already expired" in dataset.issues[0].message


@pytest.mark.parametrize("overrides, field, expected", [
    ({"quantity_lbs": "-5"}, "quantity_lbs", "positive whole number (got '-5')"),
    ({"ready_time": "25:61"}, "ready_time", "not a valid 24-hour HH:MM time"),
    ({"food_type": "ice_cream"}, "food_type", "'ice_cream' is not a known food type"),
    ({"pickup_area": "Uptown"}, "pickup_area", "'Uptown' is not a known area"),
    ({"donation_id": "2008"}, "donation_id", "does not match the required format"),
])
def test_invalid_donation_field_is_rejected_with_readable_reason(overrides, field, expected):
    dataset = make_dataset([donation_row(**overrides)])

    assert dataset.donations == []
    assert [issue.field for issue in dataset.issues] == [field]
    assert expected in dataset.issues[0].message


def test_empty_and_header_only_files_load_as_empty_lists(tmp_path):
    write_csv(tmp_path, "donations.csv", DONATION_COLUMNS)            # header only
    write_csv(tmp_path, "recipients.csv", RECIPIENT_COLUMNS)
    (tmp_path / "volunteers.csv").write_text("")                      # completely empty

    dataset = load_dataset(tmp_path)

    assert dataset.donations == [] and dataset.recipients == {} and dataset.volunteers == {}
    assert len(dataset.issues) == 1 and "volunteers.csv is empty" in dataset.issues[0].message
    assert run_fifo(dataset) == []
