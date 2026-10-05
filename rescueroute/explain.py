"""Human-readable explanations for scheduling decisions."""

from .matching import Trip
from .models import Donation, Recipient, Volunteer
from .timeutils import format_duration, format_hhmm


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe_donation(donation: Donation) -> str:
    return f"{donation.quantity_lbs} lbs of {donation.food_type} from {donation.donor_name}"


def explain_assignment(donation: Donation, trip: Trip, recipient: Recipient, capacity_before: int,
                       volunteer: Volunteer, order_note: str) -> str:
    pickup = format_hhmm(trip.pickup_time)
    delivery = format_hhmm(trip.delivery_time)
    margin = format_duration(donation.expiry_time - trip.delivery_time)
    return (
        f"Assigned: Donation {donation.donation_id} ({describe_donation(donation)}) was assigned to "
        f"{recipient.org_name} ({recipient.recipient_id}) with volunteer {volunteer.volunteer_name} "
        f"({volunteer.volunteer_id}), pickup {pickup} and delivery {delivery}, because "
        f"{recipient.org_name} accepts {donation.food_type} and had {capacity_before} lbs of capacity left, "
        f"{volunteer.volunteer_name}'s {volunteer.vehicle_capacity_lbs} lbs vehicle can carry "
        f"{donation.quantity_lbs} lbs, and delivery at {delivery} is {margin} before the food expires "
        f"({format_hhmm(donation.expiry_time)}), before {recipient.org_name} closes "
        f"({format_hhmm(recipient.closing_time)}), and within {volunteer.volunteer_name}'s availability "
        f"(until {format_hhmm(volunteer.available_until)}). {order_note}"
    )


def explain_unassigned(donation: Donation, why: str, order_note: str) -> str:
    return (
        f"Unassigned: Donation {donation.donation_id} ({describe_donation(donation)}) could not be "
        f"assigned because {why}. {order_note}"
    )
