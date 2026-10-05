"""Tests for the FIFO baseline scheduler and its explanations."""

from factories import donation_row, make_dataset, recipient_row, volunteer_row
from rescueroute.fifo import run_fifo
from rescueroute.models import ASSIGNED, UNASSIGNED


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def only_decision(dataset):
    decisions = run_fifo(dataset)
    assert len(decisions) == 1
    return decisions[0]


def test_normal_compatible_match_is_assigned_with_explanation():
    dataset = make_dataset([donation_row()], [recipient_row()], [volunteer_row()])

    decision = only_decision(dataset)

    assert decision.status == ASSIGNED
    assert (decision.recipient_id, decision.volunteer_id) == ("R-201", "V-301")
    # Volunteer is free at 12:00 in Downtown, food is ready 12:30, same-area delivery takes 10 min.
    assert (decision.pickup_time, decision.delivery_time) == (minutes("12:30"), minutes("12:40"))
    for fragment in ("Assigned: Donation D-1001", "Test Shelter accepts prepared_meals",
                     "had 100 lbs of capacity left", "60 lbs vehicle can carry 40 lbs",
                     "1st in FIFO arrival order"):
        assert fragment in decision.reason


def test_nearly_expired_donation_is_unassigned_because_it_would_arrive_too_late():
    dataset = make_dataset(
        [donation_row(ready_time="12:30", expiry_time="12:50")],
        [recipient_row(area="Eastside")],          # 25 minutes away
        [volunteer_row()],
    )

    decision = only_decision(dataset)

    assert decision.status == UNASSIGNED
    assert decision.recipient_id is None and decision.volunteer_id is None
    assert "earliest possible delivery was 12:55" in decision.reason
    assert "the food expires at 12:50" in decision.reason


def test_no_recipient_accepts_food_type():
    dataset = make_dataset([donation_row(food_type="dairy")], [recipient_row()], [volunteer_row()])

    decision = only_decision(dataset)

    assert decision.status == UNASSIGNED
    assert "because no recipient accepts dairy" in decision.reason


def test_fifo_follows_posted_time_and_keeps_file_order_for_ties():
    dataset = make_dataset(
        [donation_row(donation_id="D-1003", posted_time="12:30"),
         donation_row(donation_id="D-1001", posted_time="12:00"),
         donation_row(donation_id="D-1002", posted_time="12:30")],
        [recipient_row(capacity_lbs=500)],
        [volunteer_row(max_pickups=5)],
    )

    order = [d.donation_id for d in run_fifo(dataset)]

    assert order == ["D-1001", "D-1003", "D-1002"]
