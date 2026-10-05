"""FIFO baseline: process donations strictly in arrival order.

Rule: donations are handled in order of posted_time (earliest first; ties keep
input file order). Each donation gets the first feasible recipient and volunteer,
scanning recipients and then volunteers in input file order. Urgency is ignored.
"""

from collections import deque

from .explain import explain_assignment, explain_unassigned, ordinal
from .matching import apply_trip, diagnose_no_match, find_first_feasible, initial_states
from .models import ASSIGNED, UNASSIGNED, Assignment, Dataset, Donation
from .timeutils import format_hhmm


def fifo_order(donations: list[Donation]) -> deque[Donation]:
    """Queue in arrival order. sorted() is stable, so equal posted_times keep file order."""
    return deque(sorted(donations, key=lambda donation: donation.posted_time))


def run_fifo(dataset: Dataset) -> list[Assignment]:
    """Schedule every donation with the FIFO rule. Returns one decision per donation."""
    recipient_states, volunteer_states = initial_states(dataset)
    queue = fifo_order(dataset.donations)
    decisions: list[Assignment] = []
    position = 0

    while queue:
        donation = queue.popleft()
        position += 1
        order_note = (f"It was processed {ordinal(position)} in FIFO arrival order "
                      f"(posted {format_hhmm(donation.posted_time)}).")

        trip = find_first_feasible(donation, recipient_states, volunteer_states)
        if trip is None:
            why = diagnose_no_match(donation, recipient_states, volunteer_states)
            decisions.append(Assignment(donation.donation_id, UNASSIGNED,
                                        explain_unassigned(donation, why, order_note)))
            continue

        recipient_state = recipient_states[trip.recipient_id]
        volunteer_state = volunteer_states[trip.volunteer_id]
        reason = explain_assignment(
            donation, trip, recipient_state.recipient, recipient_state.remaining_capacity,
            volunteer_state.volunteer,
            order_note + " FIFO takes the first feasible recipient and volunteer in list order.",
        )
        apply_trip(donation, trip, recipient_states, volunteer_states)
        decisions.append(Assignment(donation.donation_id, ASSIGNED, reason, trip.recipient_id,
                                    trip.volunteer_id, trip.pickup_time, trip.delivery_time))

    return decisions
