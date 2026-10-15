"""Tests for the greedy urgency-first scheduler, its deferral explanations, and the metrics."""

from factories import donation_row, make_dataset, recipient_row, volunteer_row
from rescueroute.fifo import run_fifo
from rescueroute.greedy import run_greedy
from rescueroute.metric import calculate_metrics, compare_metrics
from rescueroute.models import ASSIGNED, UNASSIGNED


def statuses(decisions):
    return {decision.donation_id: decision.status for decision in decisions}


def test_greedy_orders_by_expiry_then_quantity_then_posted_time():
    dataset = make_dataset(
        [donation_row(donation_id="D-1001", expiry_time="17:00"),
         donation_row(donation_id="D-1002", expiry_time="15:00", quantity_lbs=20, posted_time="12:05"),
         donation_row(donation_id="D-1003", expiry_time="15:00", quantity_lbs=30),
         donation_row(donation_id="D-1004", expiry_time="15:00", quantity_lbs=20, posted_time="12:00")],
        [recipient_row(capacity_lbs=500)],
        [volunteer_row(max_pickups=5)],
    )

    order = [d.donation_id for d in run_greedy(dataset)]

    # Earliest expiry first; among 15:00 ties, larger quantity; then earlier posted time.
    assert order == ["D-1003", "D-1004", "D-1002", "D-1001"]


def test_fifo_and_greedy_differ_when_urgent_donation_arrives_late():
    # One volunteer with one pickup: whichever donation is processed first gets the trip.
    dataset = make_dataset(
        [donation_row(donation_id="D-1001", posted_time="12:00", expiry_time="18:00"),
         donation_row(donation_id="D-1002", posted_time="12:10", expiry_time="13:00")],
        [recipient_row()],
        [volunteer_row(max_pickups=1)],
    )

    fifo = run_fifo(dataset)
    greedy = run_greedy(dataset)

    assert statuses(fifo) == {"D-1001": ASSIGNED, "D-1002": UNASSIGNED}
    assert statuses(greedy) == {"D-1001": UNASSIGNED, "D-1002": ASSIGNED}
    # D-1002 is the only urgent donation (20% of 2, rounded up), so greedy rescues it and FIFO does not.
    differences = compare_metrics(calculate_metrics(dataset, fifo), calculate_metrics(dataset, greedy))
    assert differences == {"donations_assigned": 0, "food_quantity_rescued_lbs": 0,
                           "urgent_rescue_rate_percent": 100.0}


def test_greedy_defers_long_shelf_life_donation_until_it_starves():
    # D-1001 arrives first but lasts longest; two urgent donations use up both pickups.
    dataset = make_dataset(
        [donation_row(donation_id="D-1001", posted_time="12:00", expiry_time="20:00"),
         donation_row(donation_id="D-1002", posted_time="12:05", expiry_time="13:30"),
         donation_row(donation_id="D-1003", posted_time="12:10", expiry_time="14:00")],
        [recipient_row(capacity_lbs=500)],
        [volunteer_row(max_pickups=2)],
    )

    decisions = run_greedy(dataset)
    starved = decisions[-1]

    assert [d.donation_id for d in decisions] == ["D-1002", "D-1003", "D-1001"]
    assert starved.donation_id == "D-1001" and starved.status == UNASSIGNED
    assert "maximum number of pickups" in starved.reason
    assert "considered after D-1003 because D-1003 expires earlier (14:00 vs 20:00)" in starved.reason
    assert "Deferred: it arrived 1st but the urgency rule moved it to 3rd" in starved.reason
    # FIFO serves D-1001 because it arrived first.
    assert statuses(run_fifo(dataset))["D-1001"] == ASSIGNED


def test_metrics_count_quantities_urgency_and_capacity_utilization():
    dataset = make_dataset(
        [donation_row(donation_id="D-1001", quantity_lbs=40, expiry_time="15:00"),
         donation_row(donation_id="D-1002", food_type="dairy", quantity_lbs=30, expiry_time="16:00")],
        [recipient_row(capacity_lbs=100)],
        [volunteer_row(vehicle_capacity_lbs=60, max_pickups=3)],
    )

    metrics = calculate_metrics(dataset, run_fifo(dataset))

    assert metrics["donations_received"] == 2
    assert metrics["donations_assigned"] == 1
    assert metrics["donations_unassigned"] == 1
    assert metrics["food_quantity_rescued_lbs"] == 40
    assert metrics["food_quantity_at_risk_lbs"] == 30   # nobody accepts dairy
    assert metrics["urgent_rescue_rate_percent"] == 100.0
    assert metrics["recipient_capacity_utilization_percent"] == 40.0
    # One 60 lbs vehicle with 3 pickups can carry 180 lbs in total.
    assert metrics["volunteer_capacity_utilization_percent"] == 22.22
