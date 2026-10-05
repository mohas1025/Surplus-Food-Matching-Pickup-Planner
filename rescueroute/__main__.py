"""Command-line entry point: python -m rescueroute --data data/sample"""

import argparse
import sys

from .fifo import run_fifo
from .loader import DataFileError, load_dataset

DISCLAIMER = (
    "Educational prototype using simulated data. Not food-safety certified, not validated, "
    "and not for real-world operations."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rescueroute",
        description="Run the FIFO baseline on simulated donation data and explain each decision.",
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

    print("FIFO decisions:")
    for number, decision in enumerate(run_fifo(dataset), start=1):
        print(f"{number:>3}. {decision.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
