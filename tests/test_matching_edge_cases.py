
"""Additional matching edge-case tests for RescueRoute."""

from factories import donation_row, make_dataset, recipient_row, volunteer_row
from rescueroute.fifo import run_fifo
from rescueroute.models import ASSIGNED, UNASSIGNED


def test_recipient_has_insufficient_capacity():
    dataset = make_dataset(
        [donation_row(quantity_lbs=40)],
        [recipient_row(capacity_lbs=20)],
        [volunteer_row()],
    )

    decision = run_fifo(dataset)[0]

    assert decision.status == UNASSIGNED
    assert "remaining capacity" in decision.reason


def test_volunteer_vehicle_is_too_small():
    dataset = make_dataset(
        [donation_row(quantity_lbs=40)],
        [recipient_row()],
        [volunteer_row(vehicle_capacity_lbs=20)],
    )

    decision = run_fifo(dataset)[0]

    assert decision.status == UNASSIGNED
    assert "largest vehicle: 20 lbs" in decision.reason


def test_volunteer_reaches_maximum_pickups():
    dataset = make_dataset(
        [
            donation_row(donation_id="D-1001"),
            donation_row(donation_id="D-1002"),
        ],
        [recipient_row()],
        [volunteer_row(max_pickups=1)],
    )

    decisions = run_fifo(dataset)

    assert decisions[0].status == ASSIGNED
    assert decisions[1].status == UNASSIGNED
    assert "maximum number of pickups" in decisions[1].reason


def test_recipient_closes_before_delivery():
    dataset = make_dataset(
        [donation_row()],
        [recipient_row(closing_time="12:35")],
        [volunteer_row()],
    )

    decision = run_fifo(dataset)[0]

    assert decision.status == UNASSIGNED
    assert "closes at 12:35" in decision.reason


def test_volunteer_unavailable_before_delivery():
    dataset = make_dataset(
        [donation_row()],
        [recipient_row()],
        [volunteer_row(available_until="12:35")],
    )

    decision = run_fifo(dataset)[0]

    assert decision.status == UNASSIGNED
    assert "only available until 12:35" in decision.reason


def test_competing_donations_use_up_recipient_capacity():
    dataset = make_dataset(
        [
            donation_row(donation_id="D-1001", quantity_lbs=40),
            donation_row(donation_id="D-1002", quantity_lbs=40),
        ],
        [recipient_row(capacity_lbs=60)],
        [volunteer_row(max_pickups=3)],
    )

    decisions = run_fifo(dataset)

    assert decisions[0].status == ASSIGNED
    assert decisions[1].status == UNASSIGNED
    assert "20 lbs left" in decisions[1].reason


def test_exact_capacity_is_accepted():
    dataset = make_dataset(
        [donation_row(quantity_lbs=40)],
        [recipient_row(capacity_lbs=40)],
        [volunteer_row(vehicle_capacity_lbs=40)],
    )

    decision = run_fifo(dataset)[0]

    assert decision.status == ASSIGNED
    assert decision.recipient_id == "R-201"
    assert decision.volunteer_id == "V-301"
