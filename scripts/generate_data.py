#!/usr/bin/env python3
"""Generate hospital simulated data for Hosfiital.

Usage:
  python scripts/generate_data.py --scenario normal --days 30 --seed 42 [--reset]
"""
import argparse
from datetime import datetime, timedelta
import sys

from generators.scenarios import run_scenario


def parse_args():
    p = argparse.ArgumentParser(description="Hosfiital data generator")
    p.add_argument("--scenario", choices=["normal", "saturation", "budget_overrun"], required=True)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD")
    p.add_argument("--reset", action="store_true", help="Reset generated data before inserting")
    return p.parse_args()


def main():
    args = parse_args()
    start_date = datetime.utcnow().date() if not args.start_date else datetime.fromisoformat(args.start_date).date()

    print(f"Running scenario={args.scenario} days={args.days} seed={args.seed} start_date={start_date} reset={args.reset}")
    run_scenario(name=args.scenario, days=args.days, seed=args.seed, start_date=start_date, reset=args.reset)


if __name__ == "__main__":
    main()
