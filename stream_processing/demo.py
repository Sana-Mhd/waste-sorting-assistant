"""Run the pipeline on a simulated conveyor belt.

From the repository root:

    python stream_processing/demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from stream_processing import (  # noqa: E402
    ConfidenceFilter,
    MaterialMapper,
    RouteAssigner,
    SorterStream,
    simulate_payloads,
)

MESSAGES = 12
SECONDS_BETWEEN_MESSAGES = 0.2


def main() -> None:
    """Print every item that passes the filter, at the moment it is processed."""
    pipeline = ConfidenceFilter(0.6) | MaterialMapper() | RouteAssigner()
    stream = SorterStream(simulate_payloads(MESSAGES, delay=SECONDS_BETWEEN_MESSAGES))

    print(f"{'item':10}{'confidence':>12}{'box area':>10}  {'material':10}route")
    passed = 0
    for item in pipeline.process(stream):
        passed += 1
        print(f"{item.item_id:10}{item.confidence:>12.2f}{item.box.area:>10}  {item.material:10}{item.routing_code}")
    print(f"\n{passed} of {MESSAGES} items passed; the rest were below the confidence threshold.")


if __name__ == "__main__":
    main()
