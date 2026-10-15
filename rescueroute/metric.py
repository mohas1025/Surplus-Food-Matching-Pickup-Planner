"""Metrics for evaluating RescueRoute scheduling strategies."""

from math import ceil

from .models import ASSIGNED, Assignment, Dataset


def calculate_metrics(
    dataset: Dataset,
    decisions: list[Assignment],
) -> dict[str, int | float]:
    """Calculate outcome metrics for scheduling strategy.

    Urgent rescue rate is the percentage of the earliest-expiring
    that were assigned.
    Capacity utilization uses total configured capacity as the denominator.
    A volunteer can carry one vehicle load per pickup, so volunteer capacity
    is vehicle capacity times maximum pickups.
    """
    donations_by_id = {
        donation.donation_id: donation
        for donation in dataset.donations
    }
    assigned_ids = {
        decision.donation_id
        for decision in decisions
        if decision.status == ASSIGNED
    }

    assigned_donations = [
        donation
        for donation in dataset.donations
        if donation.donation_id in assigned_ids
    ]
    unassigned_donations = [
        donation
        for donation in dataset.donations
        if donation.donation_id not in assigned_ids
    ]

    rescued_quantity = sum(
        donation.quantity_lbs for donation in assigned_donations
    )
    quantity_at_risk = sum(
        donation.quantity_lbs for donation in unassigned_donations
    )

    urgent_count = ceil(len(dataset.donations) * 0.20)
    urgent_donations = sorted(
        dataset.donations,
        key=lambda donation: donation.expiry_time,
    )[:urgent_count]
    urgent_assigned = sum(
        donation.donation_id in assigned_ids
        for donation in urgent_donations
    )
    urgent_rate = (
        urgent_assigned / len(urgent_donations) * 100
        if urgent_donations
        else 0.0
    )

    total_recipient_capacity = sum(
        recipient.capacity_lbs
        for recipient in dataset.recipients.values()
    )
    total_volunteer_capacity = sum(
        volunteer.vehicle_capacity_lbs * volunteer.max_pickups
        for volunteer in dataset.volunteers.values()
    )

    recipient_utilization = (
        rescued_quantity / total_recipient_capacity * 100
        if total_recipient_capacity
        else 0.0
    )
    volunteer_utilization = (
        rescued_quantity / total_volunteer_capacity * 100
        if total_volunteer_capacity
        else 0.0
    )

    return {
        "donations_received": len(dataset.donations),
        "donations_assigned": len(assigned_donations),
        "donations_unassigned": len(unassigned_donations),
        "food_quantity_rescued_lbs": rescued_quantity,
        "food_quantity_at_risk_lbs": quantity_at_risk,
        "urgent_rescue_rate_percent": round(urgent_rate, 2),
        "recipient_capacity_utilization_percent": round(
            recipient_utilization, 2
        ),
        "volunteer_capacity_utilization_percent": round(
            volunteer_utilization, 2
        ),
    }


def compare_metrics(
    fifo_metrics: dict[str, int | float],
    greedy_metrics: dict[str, int | float],
) -> dict[str, int | float]:
    """Return greedy-minus-FIFO differences for key outcome metrics."""
    keys = (
        "donations_assigned",
        "food_quantity_rescued_lbs",
        "urgent_rescue_rate_percent",
    )
    return {
        key: round(greedy_metrics[key] - fifo_metrics[key], 2)
        for key in keys
    }
