"""Greedy urgency-first scheduler.

What needs to be done
Earliest expiration first. Larger quantity first when expiration times ties. Earliest posted time 
first when the first two keys tie. Remaining ties preserve input file order.

For each donation, choose the first recipient and volunteer
in input file order. All feasibility rules are shared with FIFO.
"""

from .explain import explain_assignment, explain_unassigned, ordinal
from .matching import (
    apply_trip,
    diagnose_no_match,
    find_first_feasible,
    initial_states,
)
from .models import ASSIGNED, UNASSIGNED, Assignment, Dataset, Donation
from .timeutils import format_hhmm


def greedy_order(donations: list[Donation]) -> list[Donation]:
    """Sort donations by urgency, using deterministic tie-breakers."""
    return sorted(
        donations,
        key=lambda donation: (
            donation.expiry_time,
            -donation.quantity_lbs,
            donation.posted_time,
        ),
    )


def run_greedy(dataset: Dataset) -> list[Assignment]:
    """Schedule donations urgency-first, returning one decision per donation."""
    recipient_states, volunteer_states = initial_states(dataset)
    ordered_donations = greedy_order(dataset.donations)
    decisions: list[Assignment] = []

    for position, donation in enumerate(ordered_donations, start=1):
        order_note = (
            f"It was processed {ordinal(position)} in greedy urgency order "
            f"(expires at {format_hhmm(donation.expiry_time)}). "
            "The priority rule is earliest expiration first and then larger quantity, "
            "then earlier posting time. The remaining ties preserve input order."
        )

        trip = find_first_feasible(
            donation, recipient_states, volunteer_states
        )

        if trip is None:
            why = diagnose_no_match(
                donation, recipient_states, volunteer_states
            )
            decisions.append(
                Assignment(
                    donation.donation_id,
                    UNASSIGNED,
                    explain_unassigned(donation, why, order_note),
                )
            )
            continue

        recipient_state = recipient_states[trip.recipient_id]
        volunteer_state = volunteer_states[trip.volunteer_id]

        reason = explain_assignment(
            donation,
            trip,
            recipient_state.recipient,
            recipient_state.remaining_capacity,
            volunteer_state.volunteer,
            order_note
            + " Greedy chooses the first feasible recipient and volunteer "
            "in input file order.",
        )

        apply_trip(donation, trip, recipient_states, volunteer_states)

        decisions.append(
            Assignment(
                donation.donation_id,
                ASSIGNED,
                reason,
                trip.recipient_id,
                trip.volunteer_id,
                trip.pickup_time,
                trip.delivery_time,
            )
        )

    return decisions
