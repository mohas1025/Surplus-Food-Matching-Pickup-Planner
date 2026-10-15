# Surplus-Food-Matching-Pickup-Planner

**RescueRoute** is an explainable Python application that coordinates time-sensitive
surplus-food donations with compatible recipient organizations and volunteer drivers.

> **Disclaimer:** RescueRoute is an educational prototype that uses **simulated data only**.
> It is not food-safety certified, not clinically or operationally validated, not approved
> for emergency operations, and not ready for real-world deployment.

**Central question:** How can we prioritize time-sensitive food donations and assign them to
compatible recipients and volunteers in a way that is efficient, transparent, and easy to explain?

## Current status

| Deliverable | Where |
|---|---|
| Team-role statement | [docs/team_roles.md](docs/team_roles.md) |
| Data schema | [docs/data_schema.md](docs/data_schema.md) |
| Sample input files | [data/sample/](data/sample/), [data/invalid_examples/](data/invalid_examples/) |
| Validation | [rescueroute/validation.py](rescueroute/validation.py), [rescueroute/loader.py](rescueroute/loader.py) |
| FIFO baseline | [rescueroute/fifo.py](rescueroute/fifo.py), [rescueroute/matching.py](rescueroute/matching.py) |
| Greedy urgency-first strategy | [rescueroute/greedy.py](rescueroute/greedy.py) |
| Metrics and FIFO-vs-greedy comparison | [rescueroute/metric.py](rescueroute/metric.py) |
| Explanations | [rescueroute/explain.py](rescueroute/explain.py) |
| Automated tests | [tests/](tests/) |

RescueRoute runs from the command line.

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

The output shows, in order:

1. The disclaimer and any validation issues.
2. One explained decision per donation under **FIFO**.
3. One explained decision per donation under **greedy urgency-first**.
4. The metrics for both strategies.
5. The greedy-minus-FIFO differences.

Example decisions from `data/sample` (line-wrapped here for reading):

```
FIFO decisions:
 11. [unassigned] Unassigned: Donation D-1011 (30 lbs of prepared_meals from Riverside
    Catering) could not be assigned because no recipient-volunteer pair could deliver it in
    time: the earliest possible delivery was 13:55 (Northside Family Center with Sam (V-303)),
    but the food expires at 13:50. It was processed 11th in FIFO arrival order (posted 13:20).

Greedy urgency-first decisions:
  1. [assigned] Assigned: Donation D-1011 (30 lbs of prepared_meals from Riverside Catering)
    was assigned to Community Shelter (R-201) with volunteer Alex (V-301), pickup 13:30 and
    delivery 13:40, because Community Shelter accepts prepared_meals and had 150 lbs of
    capacity left, Alex's 60 lbs vehicle can carry 30 lbs, and delivery at 13:40 is 10 minutes
    before the food expires (13:50), before Community Shelter closes (20:00), and within Alex's
    availability (until 16:00). It was processed 1st in greedy urgency order (expires at
    13:50). ...

 12. [unassigned] Unassigned: Donation D-1003 (100 lbs of produce from Fresh Mart Grocery)
    could not be assigned because every volunteer with a vehicle large enough for 100 lbs
    (Jordan (V-302)) had already reached their maximum number of pickups. It was processed
    12th in greedy urgency order (expires at 21:00). ...
```

The same donation, D-1011, is lost under FIFO and rescued under greedy. D-1003 shows the
cost: greedy defers long-shelf-life food to the end, and by then the only large vehicle is
used up.

## Test

```bash
pytest -v
```

20 tests:

- `tests/test_validation.py`: valid rows, duplicate donation IDs, already-expired donations,
  invalid field values, empty and header-only files.
- `tests/test_fifo.py`: a normal compatible match, a nearly expired donation, no compatible
  food type, FIFO arrival order with file-order tie-breaking.
- `tests/test_matching_edge_cases.py`: insufficient recipient capacity, vehicle too small,
  volunteer at maximum pickups, recipient closes before delivery, volunteer unavailable before
  delivery, two donations competing for the same capacity, exact capacity accepted.

## How it works

```
CSV files -> loader.py -> validation.py -> Dataset -> fifo.py   -> metric.py -> comparison
                                                   -> greedy.py ->
                         (both schedulers use matching.py and explain.py)
```

1. **Load** the three CSV files from a data folder.
2. **Validate** every row. Invalid rows are skipped with a readable reason; valid rows continue.
3. **Schedule** the same data twice, with FIFO and with greedy. Both use the same
   feasibility rules for every recipient-volunteer pair.
4. **Explain** each decision in plain language.
5. **Measure** both runs with the same metrics and print the differences.

### Data structures

| Need | Structure | Why |
|---|---|---|
| Recipients and volunteers by ID | `dict` | O(1) lookup when applying a trip |
| Accepted food types | `frozenset` | O(1) membership check, immutable |
| Duplicate-ID detection | `dict` of first-seen row | Detects repeats and reports where the first one was |
| FIFO processing | `collections.deque` | O(1) `popleft()` in arrival order |
| Greedy processing | sorted `list` | Sorted once by the priority key; `sorted()` is stable, so final ties keep file order |
| Assignment history | `list` of `Assignment` | Keeps decisions in processing order |
| Changing capacity / volunteer position | `RecipientState`, `VolunteerState` | Scheduling never modifies the validated input |
| Assigned donation IDs (metrics) | `set` | O(1) check whether a donation was assigned |
| Metrics | `dict` | One named value per metric, easy to print and compare |

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

### Greedy urgency-first rule

Schedule the donation with the **earliest expiry time** first. If two donations expire at the
same time, schedule the **larger quantity** first. If still tied, schedule the **earlier posted
time** first. Any remaining ties keep input-file order. Each donation then goes to the first
feasible recipient and volunteer in file order, using the same feasibility rules as FIFO.
Every decision states the donation's position in greedy order and its expiry time.

- **What it optimizes locally:** at each step it serves the donation closest to spoiling, so
  the most urgent food gets first claim on volunteers and recipient capacity.
- **Why it is reasonable:** urgent food has the smallest delivery window. Food with a long
  shelf life still has time to be delivered later.
- **Where it can fail:** it can spend volunteer trips and capacity on small urgent donations
  and leave large, long-lasting donations with nothing. In the sample data it rescues every
  urgent donation but 50 fewer pounds in total than FIFO. It also takes the first feasible
  pair, not the best pair, and it assumes all donations are known before scheduling starts.
- **Fairness and starvation:** donations with a long shelf life are always scheduled last.
  If urgent donations keep arriving, a long-lasting donation may never be served. In the
  sample, D-1003 (100 lbs of produce) is lost this way. One fix is aging: raise a
  donation's priority the longer it waits.

## Metrics

Calculated for both strategies on the same input:

| Metric | Definition |
|---|---|
| Donations received / assigned / unassigned | Counts of donations |
| Food quantity rescued | Pounds of assigned donations |
| Food quantity at risk | Pounds of unassigned donations |
| Urgent rescue rate | % of the 20% earliest-expiring donations (rounded up) that were assigned |
| Recipient capacity utilization | Rescued pounds / total recipient capacity |
| Volunteer capacity utilization | Rescued pounds / sum of all vehicle capacities (one load per volunteer). Volunteers can make several trips, so this can exceed 100%. |

## FIFO vs greedy comparison

Results on `data/sample` (13 donations, 5 recipients, 5 volunteers):

| Metric | FIFO | Greedy | Greedy minus FIFO |
|---|---|---|---|
| Donations assigned | 8 | 8 | 0 |
| Donations unassigned | 5 | 5 | 0 |
| Food rescued (lbs) | 395 | 345 | -50 |
| Food at risk (lbs) | 370 | 420 | +50 |
| Urgent rescue rate | 66.67% | 100.0% | +33.33 |
| Recipient capacity utilization | 57.25% | 50.0% | -7.25 |
| Volunteer capacity utilization | 119.7% | 104.55% | -15.15 |

**What changed and why:**

- **D-1011** (30 lbs prepared meals, expires 13:50): lost under FIFO, rescued under greedy.
  FIFO reaches it late because it was posted late; by then Community Shelter, the only
  recipient in its area, has 25 lbs left. Greedy handles it first.
- **D-1010** (70 lbs produce): lost under FIFO, rescued under greedy. Under FIFO, the only
  volunteers big enough (Jordan and Riley) had already used all their pickups. Under greedy,
  Riley still had one trip left.
- **D-1002** (50 lbs bakery) and **D-1003** (100 lbs produce): rescued under FIFO, lost under
  greedy. They expire late (20:00 and 21:00), so greedy schedules them last, after every large
  enough volunteer has reached their pickup limit.
- **D-1006**, **D-1007**, **D-1013**: lost under both. They are too large for the available
  vehicles or capacity, or no recipient accepts the food type (frozen).

Greedy protects urgent food; FIFO rescues more total food here because early, large,
long-lasting donations get served first. The trade-off is urgency versus total quantity.

## Complexity

With n donations, r recipients, and v volunteers:

- **Ordering:** O(n log n) for both strategies (FIFO sorts by posted time, greedy by the
  urgency key).
- **Matching:** each donation checks up to r x v recipient-volunteer pairs, and each check is
  O(1) (dictionary lookup, frozenset membership), so O(n x r x v).
- **Total:** O(n log n + n x r x v) time and O(n + r + v) memory.

## Assumptions

- All times are on one simulated day in `HH:MM` format; overnight windows are not supported.
- All quantities are whole pounds.
- Travel time is simulated: 10 minutes within an area, 25 minutes between areas.
- One donation per trip; a volunteer delivers before the next pickup.
- Capacity is a daily total per recipient.
- Both strategies see all donations before scheduling starts.

## Project structure

```
rescueroute/      application package
  models.py       data classes and status constants
  timeutils.py    HH:MM parsing and formatting
  loader.py       CSV reading
  validation.py   field and row validation
  matching.py     feasibility rules, run state, no-match diagnosis
  fifo.py         FIFO baseline scheduler
  greedy.py       greedy urgency-first scheduler
  metric.py       metrics and FIFO-vs-greedy comparison
  explain.py      human-readable explanations
  __main__.py     command-line entry point
data/             sample and invalid-example CSV files
docs/             team roles and data schema
tests/            pytest suite
```

## Team

See [docs/team_roles.md](docs/team_roles.md).
