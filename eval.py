# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""
Phase 2 evaluation harness for artifact optimization.

Reads a target artifact and scores it using the proven metric from Phase 1.
This is the Subjective Goal Mode equivalent of `uv run train.py`.

Usage:
    uv run eval.py target.md --goal "Make my API error messages more helpful"
    uv run eval.py target.md --goal-file calibration_pairs.yaml --verbose
"""
import argparse
import sys
import time

import yaml

# Reuse the LLM client from metaresearch
from metaresearch import make_llm
import metric


def resolve_goal(args):
    """Resolve the goal from CLI args, goal file, or error."""
    if args.goal:
        return args.goal

    if args.goal_file:
        with open(args.goal_file) as f:
            data = yaml.safe_load(f)
        goal = data.get("goal", "")
        if not goal:
            print(f"Error: {args.goal_file} has no 'goal' key.")
            sys.exit(1)
        return goal

    print("Error: Provide --goal or --goal-file.")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phase 2: Score an artifact with a proven metric",
    )
    parser.add_argument("target", nargs="?", default="target.md",
                        help="Path to the artifact to evaluate (default: target.md)")
    parser.add_argument("--goal", default=None,
                        help="The subjective goal string")
    parser.add_argument("--goal-file", default=None,
                        help="YAML file with a 'goal' key (e.g. calibration_pairs.yaml)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--provider", default=None, help="LLM provider override")
    parser.add_argument("--model", default=None, help="Model name override")
    args = parser.parse_args()

    goal = resolve_goal(args)

    with open(args.target) as f:
        artifact = f.read()

    if args.verbose:
        print(f"Target: {args.target} ({len(artifact)} chars)")
        print(f"Goal: {goal[:80]}...")
        print()

    t_start = time.time()
    llm = make_llm(provider=args.provider, model=args.model)

    if args.verbose:
        print(f"LLM: {llm.provider}/{llm.model}")
        print()

    s = metric.score(artifact, goal, llm)
    t_end = time.time()

    print("---")
    print(f"score:            {s:.6f}")
    print(f"total_seconds:    {t_end - t_start:.1f}")
