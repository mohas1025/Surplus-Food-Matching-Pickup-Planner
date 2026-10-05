# Data Schema

RescueRoute reads three CSV files from one data folder:

```
data/<dataset>/donations.csv
data/<dataset>/recipients.csv
data/<dataset>/volunteers.csv
```

All data is **simulated**. Field names below are the exact CSV column headers.

## Conventions

- **Times** use 24-hour `HH:MM` format (e.g. `09:05`, `17:30`). All times are on a
  single simulated day; overnight windows are not supported.
- **Quantities** are whole pounds (`lbs`). Donation quantity, recipient capacity, and
  vehicle capacity all use the same unit so they can be compared directly.
- **Areas** must be one of: `Downtown`, `Campus`, `Northside`, `Eastside`, `Westside`.
- **Food types** must be one of: `prepared_meals`, `produce`, `bakery`, `dairy`,
  `canned_goods`, `frozen`.
- Extra columns are ignored. Missing required columns cause the whole file to be rejected.
- A file with only a header row is valid and produces an empty list.

## donations.csv

| Column | Type | Rule | Example |
|---|---|---|---|
| `donation_id` | text | Required. Format `D-` + 4 digits. Unique within the file. | `D-1001` |
| `donor_name` | text | Required, non-empty. | `Campus Catering` |
| `food_type` | text | Required. One of the known food types. | `prepared_meals` |
| `quantity_lbs` | integer | Required. Positive whole number. | `40` |
| `posted_time` | `HH:MM` | Required. When the donation entered the system. Defines FIFO arrival order. Must be `<= ready_time`. | `12:50` |
| `ready_time` | `HH:MM` | Required. Earliest pickup time. Must be `< expiry_time`. | `13:00` |
| `expiry_time` | `HH:MM` | Required. Food must be delivered by this time. | `14:30` |
| `pickup_area` | text | Required. One of the known areas. | `Campus` |

Remaining shelf life is derived as `expiry_time - ready_time` (minutes).

## recipients.csv

| Column | Type | Rule | Example |
|---|---|---|---|
| `recipient_id` | text | Required. Format `R-` + 3 digits. Unique within the file. | `R-201` |
| `org_name` | text | Required, non-empty. | `Community Shelter` |
| `accepted_food_types` | list | Required. One or more known food types separated by `;`. Stored as a set. | `prepared_meals;bakery` |
| `capacity_lbs` | integer | Required. Positive whole number. Total pounds the recipient can accept today. | `120` |
| `area` | text | Required. One of the known areas. | `Downtown` |
| `closing_time` | `HH:MM` | Required. Deliveries must arrive by this time. | `18:00` |

## volunteers.csv

| Column | Type | Rule | Example |
|---|---|---|---|
| `volunteer_id` | text | Required. Format `V-` + 3 digits. Unique within the file. | `V-301` |
| `volunteer_name` | text | Required, non-empty. | `Alex` |
| `vehicle_capacity_lbs` | integer | Required. Positive whole number. Max pounds per trip. | `60` |
| `area` | text | Required. One of the known areas. Starting location. | `Campus` |
| `available_from` | `HH:MM` | Required. Must be `< available_until`. | `12:00` |
| `available_until` | `HH:MM` | Required. Deliveries must finish by this time. | `16:00` |
| `max_pickups` | integer | Required. Positive whole number. Max donations this volunteer carries today. | `3` |

## Assignment (output)

Every donation produces one decision record. Records rejected by validation are reported
separately as validation issues.

| Field | Meaning |
|---|---|
| `donation_id` | Donation being decided |
| `recipient_id` | Assigned recipient, or empty |
| `volunteer_id` | Assigned volunteer, or empty |
| `pickup_time` | Scheduled pickup (`HH:MM`), or empty |
| `delivery_time` | Scheduled delivery (`HH:MM`), or empty |
| `status` | `assigned` or `unassigned` |
| `reason` | Human-readable explanation of the decision |

## Validation issue (output)

| Field | Meaning |
|---|---|
| `file` | CSV file name |
| `row` | Line number in the file (header is line 1) |
| `record_id` | ID from the row, if readable |
| `field` | Column that failed |
| `message` | Human-readable explanation |

Invalid rows are skipped; valid rows are still processed.

## Simulated travel model

Travel time between areas is a fixed simulated assumption, not real routing:

- Same area: **10 minutes**
- Different areas: **25 minutes**

## Feasibility rules

A donation `D` can go to recipient `R` with volunteer `V` only if all hold:

1. `R` accepts `D.food_type`.
2. `R` has at least `D.quantity_lbs` remaining capacity.
3. `V.vehicle_capacity_lbs >= D.quantity_lbs`.
4. `V` has not reached `max_pickups`.
5. `pickup = max(D.ready_time, V free time + travel(V current area, D.pickup_area))`
   and `delivery = pickup + travel(D.pickup_area, R.area)`.
6. `delivery <= D.expiry_time`, `delivery <= R.closing_time`, and
   `delivery <= V.available_until`.

A volunteer's free time starts at `available_from`. After a delivery, the volunteer is free
at the delivery time and located in the recipient's area.
