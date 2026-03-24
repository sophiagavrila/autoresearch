# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""
Phase 2 evaluation harness for CLAUDE.md optimization.

Reads the target artifact and scores it using the proven metric from Phase 1.
This is the Subjective Goal Mode equivalent of `uv run train.py`.

Usage:
    uv run eval.py target.md
    uv run eval.py target.md --verbose
"""
import sys
import time

# Reuse the LLM client from metaresearch
from metaresearch import make_llm
import metric

GOAL = (
    "Claude Code global instructions (CLAUDE.md) that maximize correct inference "
    "of developer intent from terse, ambiguous, or incomplete prompts. The "
    "instructions should ensure the agent: (1) validates outputs in the real "
    "environment before presenting them as correct, (2) makes incremental changes "
    "verified at each step rather than batch rewrites, (3) accounts for the actual "
    "execution environment and platform constraints before acting, (4) calibrates "
    "confidence correctly — acting decisively on clear intent, asking only when "
    "genuinely ambiguous, never over-specifying or micromanaging the developer, "
    "(5) matches output scope to what was actually requested — not exhaustive when "
    "curated was needed, not verbose when terse was expected, (6) creates rollback "
    "safety before destructive edits, and (7) gives the developer observability "
    "into its reasoning without requiring them to read every diff or trace every "
    "decision."
)

if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "target.md"
    verbose = "--verbose" in sys.argv

    with open(target_path) as f:
        artifact = f.read()

    if verbose:
        print(f"Target: {target_path} ({len(artifact)} chars)")
        print(f"Goal: {GOAL[:80]}...")
        print()

    t_start = time.time()
    llm = make_llm()

    if verbose:
        print(f"LLM: {llm.provider}/{llm.model}")
        print()

    s = metric.score(artifact, GOAL, llm)
    t_end = time.time()

    print("---")
    print(f"score:            {s:.6f}")
    print(f"total_seconds:    {t_end - t_start:.1f}")
