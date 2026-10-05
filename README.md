# Surplus-Food-Matching-Pickup-Planner

**RescueRoute** is an explainable Python application that coordinates time-sensitive
surplus-food donations with compatible recipient organizations and volunteer drivers.

> **Disclaimer:** RescueRoute is an educational prototype that uses **simulated data only**.
> It is not food-safety certified, not clinically or operationally validated, not approved
> for emergency operations, and not ready for real-world deployment.

**Central question:** How can we prioritize time-sensitive food donations and assign them to
compatible recipients and volunteers in a way that is efficient, transparent, and easy to explain?

## Current status: Week 1 (Foundation)

| Deliverable | Where |
|---|---|
| Team-role statement | [docs/team_roles.md](docs/team_roles.md) |
| Data schema | [docs/data_schema.md](docs/data_schema.md) |
| Sample input files | [data/sample/](data/sample/), [data/invalid_examples/](data/invalid_examples/) |
| Validation | [rescueroute/validation.py](rescueroute/validation.py), [rescueroute/loader.py](rescueroute/loader.py) |
| FIFO baseline | [rescueroute/fifo.py](rescueroute/fifo.py), [rescueroute/matching.py](rescueroute/matching.py) |
| Automated tests | [tests/](tests/) |

Later milestones will add the greedy urgency-first strategy, metrics, the FIFO-vs-greedy
comparison, more tests, and the dashboard.

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m rescueroute --data data/sample             # clean demo data
python -m rescueroute --data data/invalid_examples   # shows validation messages
```

The output shows the disclaimer, any validation issues, and one explained decision per
donation in FIFO order.

Example decisions from `data/sample` (line-wrapped here for reading):

```
 4. Assigned: Donation D-1004 (35 lbs of prepared_meals from Spring Gala (campus event)) was
    assigned to Community Shelter (R-201) with volunteer Alex (V-301), pickup 13:20 and delivery
    13:45, because Community Shelter accepts prepared_meals and had 60 lbs of capacity left,
    Alex's 60 lbs vehicle can carry 35 lbs, and delivery at 13:45 is 45 minutes before the food
    expires (14:30), before Community Shelter closes (20:00), and within Alex's availability
    (until 16:00). It was processed 4th in FIFO arrival order (posted 12:10). FIFO takes the
    first feasible recipient and volunteer in list order.

11. Unassigned: Donation D-1011 (30 lbs of prepared_meals from Riverside Catering) could not be
    assigned because no recipient-volunteer pair could deliver it in time: the earliest possible
    delivery was 13:55 (Northside Family Center with Sam (V-303)), but the food expires at 13:50.
    It was processed 11th in FIFO arrival order (posted 13:20).
```

## Test

```bash
pytest -v
```

Week 1 tests cover: valid rows, duplicate donation IDs, already-expired donations, invalid
field values, empty and header-only files, a normal compatible match, a nearly expired donation,
no compatible food type, and FIFO arrival order.

## How it works

```
CSV files -> loader.py -> validation.py -> Dataset -> fifo.py (uses matching.py, explain.py)
```

1. **Load** the three CSV files from a data folder.
2. **Validate** every row. Invalid rows are skipped with a readable reason; valid rows continue.
3. **Schedule** with FIFO, checking feasibility rules for every recipient-volunteer pair.
4. **Explain** each decision in plain language.

### Data structures

| Need | Structure | Why |
|---|---|---|
| Recipients and volunteers by ID | `dict` | O(1) lookup when applying a trip |
| Accepted food types | `frozenset` | O(1) membership check, immutable |
| Duplicate-ID detection | `dict` of first-seen row | Detects repeats and reports where the first one was |
| FIFO processing | `collections.deque` | O(1) `popleft()` in arrival order |
| Assignment history | `list` of `Assignment` | Keeps decisions in processing order |
| Changing capacity / volunteer position | `RecipientState`, `VolunteerState` | Scheduling never modifies the validated input |

### Feasibility rules

A donation can go to a recipient with a volunteer only if:

1. The recipient accepts the food type.
2. The recipient has enough remaining capacity.
3. The volunteer's vehicle can carry the quantity.
4. The volunteer has not reached their maximum pickups.
5. Delivery arrives no later than the food's expiry time, the recipient's closing time, and
   the end of the volunteer's availability.

Timing: `pickup = max(ready_time, volunteer free time + travel to donor)`,
`delivery = pickup + travel to recipient`. After a delivery the volunteer is free at the
delivery time, in the recipient's area.

### FIFO baseline rule

Donations are processed in order of `posted_time` (earliest first; ties keep the file order).
Each donation is assigned to the **first feasible recipient and volunteer**, scanning recipients
and then volunteers in file order. If none is feasible, the donation is marked unassigned and the
explanation names the first rule that blocked every option, checked in this order: food type,
recipient capacity, vehicle capacity, volunteer pickup limit, timing.

FIFO ignores urgency. In the sample data, D-1011 has only 20 minutes of shelf life but was
posted late. By the time FIFO reaches it, the nearby shelter's capacity is used by earlier,
less urgent donations, so it cannot be delivered before it expires.

## Assumptions

- All times are on one simulated day in `HH:MM` format; overnight windows are not supported.
- All quantities are whole pounds.
- Travel time is simulated: 10 minutes within an area, 25 minutes between areas.
- One donation per trip; a volunteer delivers before the next pickup.
- Capacity is a daily total per recipient.

## Project structure

```
rescueroute/      application package
  models.py       data classes and status constants
  timeutils.py    HH:MM parsing and formatting
  loader.py       CSV reading
  validation.py   field and row validation
  matching.py     feasibility rules, run state, no-match diagnosis
  fifo.py         FIFO baseline scheduler
  explain.py      human-readable explanations
  __main__.py     command-line entry point
data/             sample and invalid-example CSV files
docs/             team roles and data schema
tests/            pytest suite
```

## Team

See [docs/team_roles.md](docs/team_roles.md).
