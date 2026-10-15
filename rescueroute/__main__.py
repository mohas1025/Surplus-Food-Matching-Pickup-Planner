"""Command-line entry point: python -m rescueroute --data data/sample"""

import argparse
import sys

from .fifo import run_fifo
from .greedy import run_greedy
from .loader import DataFileError, load_dataset
from .metric import calculate_metrics, compare_metrics

DISCLAIMER = (
    "Educational prototype using simulated data. Not food-safety certified, not validated, "
    "and not for real-world operations."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rescueroute",
        description="Run FIFO and greedy urgency-first on simulated donation data, explain each "
                    "decision, and compare the metrics of both strategies.",
    )
    parser.add_argument("--data", default="data/sample",
                        help="folder containing donations.csv, recipients.csv, volunteers.csv")
    args = parser.parse_args(argv)

    try:
        dataset = load_dataset(args.data)
    except DataFileError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(DISCLAIMER)
    print()
    if dataset.issues:
        print("Validation issues (these rows were skipped):")
        for issue in dataset.issues:
            print(f"  - {issue}")
        print()

    # Run both strategies on the same validated data.
    fifo_decisions = run_fifo(dataset)
    greedy_decisions = run_greedy(dataset)

    print("FIFO decisions:")
    for number, decision in enumerate(fifo_decisions, start=1):
        print(f"{number:>3}. [{decision.status}] {decision.reason}")

    print("\nGreedy urgency-first decisions:")
    for number, decision in enumerate(greedy_decisions, start=1):
        print(f"{number:>3}. [{decision.status}] {decision.reason}")

    fifo_metrics = calculate_metrics(dataset, fifo_decisions)
    greedy_metrics = calculate_metrics(dataset, greedy_decisions)

    print("\nFIFO metrics:")
    for name, value in fifo_metrics.items():
        print(f"  {name}: {value}")

    print("\nGreedy metrics:")
    for name, value in greedy_metrics.items():
        print(f"  {name}: {value}")

    # Compare greedy results against FIFO.
    differences = compare_metrics(fifo_metrics, greedy_metrics)

    print("\nGreedy minus FIFO:")
    for name, value in differences.items():
        print(f"  {name}: {value:+}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
