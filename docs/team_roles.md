# Team-Role Statement

Project: **RescueRoute** — an explainable surplus-food matching and pickup planner
(educational prototype, simulated data only).

Roles organize the work. They do not limit it. Every member helps with design,
debugging, testing, documentation, code review, and the final presentation, and
every member must be able to explain the whole system.

| Member | Primary role | Main responsibilities |
|---|---|---|
| Member A *(name TBD)* | Algorithm & Optimization Lead | FIFO scheduler, greedy urgency-first strategy, priority rule and tie-breakers, complexity analysis, FIFO-vs-greedy comparison |
| Member B *(name TBD)* | Data & Matching Lead | Input file format, validation, compatibility checks, capacity rules, data structures, test data |
| Member C *(name TBD)* | Product & Quality Lead | Explainable output, metrics, automated tests, README, demo materials, command-line and dashboard polish |

## Code ownership map

Primary owners review and lead changes in their area; anyone may contribute.

| Area | Files | Primary owner |
|---|---|---|
| Data model and validation | `rescueroute/models.py`, `rescueroute/loader.py`, `rescueroute/validation.py`, `data/` | Data & Matching Lead |
| Feasibility checks | `rescueroute/matching.py` | Data & Matching Lead |
| Scheduling | `rescueroute/fifo.py` | Algorithm & Optimization Lead |
| Explanations and command line | `rescueroute/explain.py`, `rescueroute/__main__.py` | Product & Quality Lead |
| Tests and documentation | `tests/`, `README.md`, `docs/` | Product & Quality Lead |

## Shared responsibilities

- Every pull request or commit touching another member's area is reviewed by that member.
- Every member writes at least some tests and some documentation.
- Every member commits from their own GitHub account so the history reflects real participation.
- Before the presentation, every member walks through the full pipeline
  (load, validate, match, schedule, explain) and can answer questions about any part.

## Week 1 deliverables

- [x] Team-role statement (this file)
- [x] Data schema (`docs/data_schema.md`)
- [x] Sample input files (`data/sample/`, `data/invalid_examples/`)
- [x] Validation (`rescueroute/validation.py`)
- [x] FIFO baseline (`rescueroute/fifo.py`)
- [x] At least 5 automated tests (`tests/`)
