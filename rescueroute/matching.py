"""Feasibility checks used by the scheduler.

A donation can go to a recipient with a volunteer only when the food type,
recipient capacity, vehicle capacity, pickup limit, and all deadlines allow it.
When no pair works, diagnose_no_match() explains which rule blocked it.
"""

from dataclasses import dataclass

from .models import Dataset, Donation, Recipient, Volunteer
from .timeutils import format_hhmm

# Simulated travel model (an assumption, not real routing).
SAME_AREA_TRAVEL_MINUTES = 10
CROSS_AREA_TRAVEL_MINUTES = 25


def travel_minutes(from_area: str, to_area: str) -> int:
    return SAME_AREA_TRAVEL_MINUTES if from_area == to_area else CROSS_AREA_TRAVEL_MINUTES


@dataclass
class RecipientState:
    """What changes for a recipient during one scheduling run."""

    recipient: Recipient
    remaining_capacity: int


@dataclass
class VolunteerState:
    """What changes for a volunteer during one scheduling run."""

    volunteer: Volunteer
    free_at: int
    current_area: str
    pickups_done: int = 0


@dataclass(frozen=True)
class Trip:
    recipient_id: str
    volunteer_id: str
    pickup_time: int
    delivery_time: int


def initial_states(dataset: Dataset) -> tuple[dict[str, RecipientState], dict[str, VolunteerState]]:
    """Fresh run state for every recipient and volunteer, keeping input file order."""
    recipient_states = {
        rid: RecipientState(recipient, recipient.capacity_lbs)
        for rid, recipient in dataset.recipients.items()
    }
    volunteer_states = {
        vid: VolunteerState(volunteer, volunteer.available_from, volunteer.area)
        for vid, volunteer in dataset.volunteers.items()
    }
    return recipient_states, volunteer_states


def accepts_food(recipient: Recipient, donation: Donation) -> bool:
    return donation.food_type in recipient.accepted_food_types


def has_capacity(state: RecipientState, donation: Donation) -> bool:
    return state.remaining_capacity >= donation.quantity_lbs


def vehicle_fits(volunteer: Volunteer, donation: Donation) -> bool:
    return volunteer.vehicle_capacity_lbs >= donation.quantity_lbs


def has_pickups_left(state: VolunteerState) -> bool:
    return state.pickups_done < state.volunteer.max_pickups


def plan_trip(donation: Donation, recipient_state: RecipientState, volunteer_state: VolunteerState) -> Trip:
    """Earliest pickup and delivery times for this pair, without checking any rule."""
    arrive_at_donor = volunteer_state.free_at + travel_minutes(volunteer_state.current_area, donation.pickup_area)
    pickup = max(donation.ready_time, arrive_at_donor)
    delivery = pickup + travel_minutes(donation.pickup_area, recipient_state.recipient.area)
    return Trip(recipient_state.recipient.recipient_id, volunteer_state.volunteer.volunteer_id, pickup, delivery)


def missed_deadlines(donation: Donation, recipient_state: RecipientState,
                     volunteer_state: VolunteerState, trip: Trip) -> list[str]:
    """Readable list of every deadline this trip would miss (empty when on time)."""
    recipient = recipient_state.recipient
    volunteer = volunteer_state.volunteer
    missed = []
    if trip.delivery_time > donation.expiry_time:
        missed.append(f"the food expires at {format_hhmm(donation.expiry_time)}")
    if trip.delivery_time > recipient.closing_time:
        missed.append(f"{recipient.org_name} closes at {format_hhmm(recipient.closing_time)}")
    if trip.delivery_time > volunteer.available_until:
        missed.append(f"{volunteer.volunteer_name} ({volunteer.volunteer_id}) is only available "
                      f"until {format_hhmm(volunteer.available_until)}")
    return missed


def feasible_trip(donation: Donation, recipient_state: RecipientState,
                  volunteer_state: VolunteerState) -> Trip | None:
    """The trip for this pair if every rule is satisfied, otherwise None."""
    if not (accepts_food(recipient_state.recipient, donation)
            and has_capacity(recipient_state, donation)
            and vehicle_fits(volunteer_state.volunteer, donation)
            and has_pickups_left(volunteer_state)):
        return None
    trip = plan_trip(donation, recipient_state, volunteer_state)
    return None if missed_deadlines(donation, recipient_state, volunteer_state, trip) else trip


def find_first_feasible(donation: Donation, recipient_states: dict[str, RecipientState],
                        volunteer_states: dict[str, VolunteerState]) -> Trip | None:
    """First feasible pair, scanning recipients then volunteers in input file order."""
    for recipient_state in recipient_states.values():
        for volunteer_state in volunteer_states.values():
            trip = feasible_trip(donation, recipient_state, volunteer_state)
            if trip is not None:
                return trip
    return None


def apply_trip(donation: Donation, trip: Trip, recipient_states: dict[str, RecipientState],
               volunteer_states: dict[str, VolunteerState]) -> None:
    """Commit a trip: use up recipient capacity and move the volunteer."""
    recipient_state = recipient_states[trip.recipient_id]
    recipient_state.remaining_capacity -= donation.quantity_lbs

    volunteer_state = volunteer_states[trip.volunteer_id]
    volunteer_state.free_at = trip.delivery_time
    volunteer_state.current_area = recipient_state.recipient.area
    volunteer_state.pickups_done += 1


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def diagnose_no_match(donation: Donation, recipient_states: dict[str, RecipientState],
                      volunteer_states: dict[str, VolunteerState]) -> str:
    """Readable reason naming the first rule that rules out every recipient-volunteer pair.

    Rules are checked in order: food type, recipient capacity, vehicle capacity,
    volunteer pickup limit, then timing.
    """
    quantity = donation.quantity_lbs
    food = donation.food_type

    if not recipient_states:
        return "there are no valid recipients in the input data"
    if not volunteer_states:
        return "there are no valid volunteers in the input data"

    food_matches = [s for s in recipient_states.values() if accepts_food(s.recipient, donation)]
    if not food_matches:
        return f"no recipient accepts {food}"

    with_room = [s for s in food_matches if has_capacity(s, donation)]
    if not with_room:
        left = _join([f"{s.recipient.org_name} has {s.remaining_capacity} lbs left" for s in food_matches])
        return f"no recipient that accepts {food} had {quantity} lbs of remaining capacity ({left})"

    big_enough = [s for s in volunteer_states.values() if vehicle_fits(s.volunteer, donation)]
    if not big_enough:
        largest = max(s.volunteer.vehicle_capacity_lbs for s in volunteer_states.values())
        return f"no volunteer's vehicle can carry {quantity} lbs (largest vehicle: {largest} lbs)"

    with_pickups = [s for s in big_enough if has_pickups_left(s)]
    if not with_pickups:
        names = _join([f"{s.volunteer.volunteer_name} ({s.volunteer.volunteer_id})" for s in big_enough])
        return (f"every volunteer with a vehicle large enough for {quantity} lbs ({names}) "
                "had already reached their maximum number of pickups")

    # Every remaining pair passes the static rules, so each one must miss a deadline.
    # Report the pair that could deliver earliest.
    pairs = [(r, v, plan_trip(donation, r, v)) for r in with_room for v in with_pickups]
    best_r, best_v, best_trip = min(pairs, key=lambda pair: pair[2].delivery_time)
    missed = missed_deadlines(donation, best_r, best_v, best_trip)
    return (
        f"no recipient-volunteer pair could deliver it in time: the earliest possible delivery was "
        f"{format_hhmm(best_trip.delivery_time)} ({best_r.recipient.org_name} with "
        f"{best_v.volunteer.volunteer_name} ({best_v.volunteer.volunteer_id})), but {_join(missed)}"
    )
