# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""
Metaresearch: Metric Discovery Engine

Discovers evaluation metrics for subjective goals through iterative refinement.
The user provides ONLY a vague goal string. This harness auto-generates
calibration pairs, then evaluates metric.py against them to compute concordance.

This is the fixed harness -- do not modify.
The agent modifies metric.py to improve concordance with human judgment.

Usage:
    uv run metaresearch.py --goal "Make my API error messages more helpful"
    uv run metaresearch.py --goal "Improve the readability of my Python docstrings"
    echo "Make the onboarding flow feel faster" | uv run metaresearch.py

Analogous to prepare.py in autoresearch.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import textwrap

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CALIBRATION_CACHE = "calibration_pairs.yaml"
DEFAULT_NUM_PAIRS = 8

# ---------------------------------------------------------------------------
# LLM Client Factory
# ---------------------------------------------------------------------------

def _detect_provider():
    """Auto-detect the best available LLM provider.

    Priority:
      1. Explicit env var (METARESEARCH_PROVIDER or AUTOEVAL_PROVIDER)
      2. claude CLI in PATH  (uses Claude Code subscription — no API key needed)
      3. ANTHROPIC_API_KEY set → anthropic SDK
      4. OPENAI_API_KEY set  → openai SDK
    """
    explicit = (
        os.environ.get("METARESEARCH_PROVIDER")
        or os.environ.get("AUTOEVAL_PROVIDER")
    )
    if explicit:
        return explicit

    if shutil.which("claude"):
        return "claude-cli"

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"

    if os.environ.get("OPENAI_API_KEY"):
        return "openai"

    # Final fallback — will try claude-cli and fail with a clear error
    return "claude-cli"


def make_llm(provider=None, model=None, max_tokens=1024, temperature=0.0):
    """
    Create an LLM callable from environment config.
    Returns a function: prompt(str) -> response(str)

    Providers:
        claude-cli  — uses the `claude` CLI (Claude Code subscription, no API key)
        anthropic   — uses the Anthropic Python SDK (needs ANTHROPIC_API_KEY)
        openai      — uses the OpenAI Python SDK (needs OPENAI_API_KEY)
    """
    provider = provider or _detect_provider()

    if provider == "claude-cli":
        claude_path = shutil.which("claude")
        if not claude_path:
            print("Error: 'claude' CLI not found in PATH.")
            print("Install Claude Code or set METARESEARCH_PROVIDER=anthropic with an API key.")
            sys.exit(1)

        model_name = (
            model
            or os.environ.get("METARESEARCH_MODEL")
            or os.environ.get("AUTOEVAL_MODEL")
            or ""
        )

        def call(prompt: str) -> str:
            cmd = [claude_path, "-p", prompt, "--output-format", "text"]
            if model_name:
                cmd.extend(["--model", model_name])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(f"claude CLI failed (rc={result.returncode}): {result.stderr[:500]}")
            return result.stdout.strip()

        call.model = model_name or "claude-code-default"
        call.provider = "claude-cli"
        return call

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        model_name = (
            model
            or os.environ.get("METARESEARCH_MODEL")
            or os.environ.get("AUTOEVAL_MODEL")
            or "claude-sonnet-4-20250514"
        )

        def call(prompt: str) -> str:
            resp = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text

        call.model = model_name
        call.provider = provider
        return call

    elif provider == "openai":
        import openai
        base_url = (
            os.environ.get("METARESEARCH_BASE_URL")
            or os.environ.get("AUTOEVAL_BASE_URL")
        )
        client = openai.OpenAI(base_url=base_url) if base_url else openai.OpenAI()
        model_name = (
            model
            or os.environ.get("METARESEARCH_MODEL")
            or os.environ.get("AUTOEVAL_MODEL")
            or "gpt-4o-mini"
        )

        def call(prompt: str) -> str:
            resp = client.chat.completions.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content

        call.model = model_name
        call.provider = provider
        return call

    else:
        print(f"Unknown provider: {provider}")
        print("Available: claude-cli, anthropic, openai")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Calibration Pair Generation
# ---------------------------------------------------------------------------

CALIBRATION_PROMPT = textwrap.dedent("""\
    You are an expert at understanding subjective quality criteria.

    A user has this goal:
    ---
    {goal}
    ---

    Generate exactly {num_pairs} calibration pairs. Each pair consists of:
    - "better": An artifact (text example) that CLEARLY achieves the goal well
    - "worse": An artifact (text example) that CLEARLY falls short of the goal
    - "reason": A brief explanation of WHY the better example is superior

    The pairs should be diverse — cover different aspects, edge cases, and
    dimensions of the goal. Vary the difficulty: some pairs should be obvious
    (clearly better vs clearly worse), and a few should be subtle (both
    reasonable, but one is measurably better).

    Both the "better" and "worse" examples must be realistic artifacts someone
    might actually produce. Do not make the "worse" examples absurdly bad —
    they should be plausible but genuinely inferior.

    Output ONLY valid YAML in this exact format (no markdown fences, no
    preamble, no commentary — just the YAML):

    calibration_pairs:
      - better: |
          <better example 1>
        worse: |
          <worse example 1>
        reason: "<why better is better>"
      - better: |
          <better example 2>
        worse: |
          <worse example 2>
        reason: "<why better is better>"
      ...
""")


def generate_calibration_pairs(goal, llm, num_pairs=DEFAULT_NUM_PAIRS):
    """
    Auto-generate calibration pairs from a goal string using an LLM.

    Args:
        goal: The user's subjective goal description
        llm: LLM callable
        num_pairs: Number of pairs to generate (default: 8)

    Returns:
        List of dicts with 'better', 'worse', 'reason' keys
    """
    prompt = CALIBRATION_PROMPT.format(goal=goal.strip(), num_pairs=num_pairs)
    response = llm(prompt)

    # Strip markdown code fences if the LLM wraps its output
    cleaned = response.strip()
    cleaned = re.sub(r'^```(?:ya?ml)?\s*\n', '', cleaned)
    cleaned = re.sub(r'\n```\s*$', '', cleaned)

    try:
        data = yaml.safe_load(cleaned)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse calibration pairs YAML from LLM response.")
        print(f"YAML error: {e}")
        print(f"Raw response (first 500 chars):\n{response[:500]}")
        sys.exit(1)

    if not isinstance(data, dict) or "calibration_pairs" not in data:
        print("Error: LLM response missing 'calibration_pairs' key.")
        print(f"Parsed data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        sys.exit(1)

    pairs = data["calibration_pairs"]
    if not isinstance(pairs, list) or len(pairs) == 0:
        print("Error: calibration_pairs is empty or not a list.")
        sys.exit(1)

    # Validate each pair
    for i, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            print(f"Error: calibration pair {i} is not a dict.")
            sys.exit(1)
        if "better" not in pair or "worse" not in pair:
            print(f"Error: calibration pair {i} must have 'better' and 'worse' fields.")
            sys.exit(1)

    return pairs


def load_or_generate_pairs(goal, llm, cache_path=CALIBRATION_CACHE, regenerate=False):
    """
    Load calibration pairs from cache, or generate and cache them.

    If the cache file exists and regenerate is False, loads from cache.
    Otherwise, generates new pairs and writes them to the cache file.

    Args:
        goal: The user's goal string
        llm: LLM callable
        cache_path: Path to the YAML cache file
        regenerate: If True, force regeneration even if cache exists

    Returns:
        Dict with 'goal' and 'calibration_pairs' keys
    """
    if os.path.exists(cache_path) and not regenerate:
        print(f"Loading cached calibration pairs from {cache_path}")
        with open(cache_path) as f:
            data = yaml.safe_load(f)

        # Validate the cached data matches the current goal
        cached_goal = data.get("goal", "").strip()
        if cached_goal != goal.strip():
            print(f"Warning: cached goal differs from current goal.")
            print(f"  Cached: {cached_goal[:80]}...")
            print(f"  Current: {goal.strip()[:80]}...")
            print(f"  Use --regenerate to generate new pairs for the current goal.")

        pairs = data.get("calibration_pairs", [])
        if not pairs:
            print("Error: cached file has no calibration_pairs. Use --regenerate.")
            sys.exit(1)

        return data

    # Generate new pairs
    print(f"Generating calibration pairs from goal...")
    pairs = generate_calibration_pairs(goal, llm)
    print(f"Generated {len(pairs)} calibration pairs.")

    # Build the full data structure
    data = {
        "goal": goal.strip(),
        "calibration_pairs": pairs,
    }

    # Cache to disk for deterministic reruns
    with open(cache_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, width=120)
    print(f"Cached calibration pairs to {cache_path}")

    return data


# ---------------------------------------------------------------------------
# Meta-Evaluation: Concordance with Human Judgment (DO NOT CHANGE)
# ---------------------------------------------------------------------------

def evaluate(metric, goal_data, llm, runs=1, verbose=False):
    """
    Run the metric against all calibration pairs.

    For each pair, the metric scores both the 'better' and 'worse' artifact.
    If better_score > worse_score, the metric agrees with human judgment.

    Returns a dict with:
        concordance:  fraction of pairs ranked correctly (0.0 - 1.0)
        avg_margin:   average score difference (better - worse)
        correct:      number of correctly ranked pairs
        total:        total number of pairs
        total_calls:  number of LLM calls made
        details:      per-pair breakdown
    """
    goal = goal_data["goal"]
    pairs = goal_data["calibration_pairs"]

    correct = 0
    total = len(pairs)
    total_calls = 0
    details = []

    for i, pair in enumerate(pairs):
        better_scores = []
        worse_scores = []

        for _ in range(runs):
            better_score = metric.score(pair["better"], goal, llm)
            worse_score = metric.score(pair["worse"], goal, llm)
            better_scores.append(better_score)
            worse_scores.append(worse_score)
            total_calls += 2

        avg_better = sum(better_scores) / len(better_scores)
        avg_worse = sum(worse_scores) / len(worse_scores)
        margin = avg_better - avg_worse
        is_correct = avg_better > avg_worse

        if is_correct:
            correct += 1

        details.append({
            "pair": i,
            "better_score": round(avg_better, 4),
            "worse_score": round(avg_worse, 4),
            "margin": round(margin, 4),
            "correct": is_correct,
        })

        if verbose:
            status = "PASS" if is_correct else "FAIL"
            reason = pair.get("reason", "")
            print(f"  pair {i}: better={avg_better:.4f}  worse={avg_worse:.4f}  "
                  f"margin={margin:+.4f}  [{status}]")
            if reason and not is_correct:
                print(f"         reason: {reason}")

    concordance = correct / total if total > 0 else 0.0
    margins = [d["margin"] for d in details]
    avg_margin = sum(margins) / len(margins) if margins else 0.0

    return {
        "concordance": concordance,
        "avg_margin": avg_margin,
        "correct": correct,
        "total": total,
        "total_calls": total_calls,
        "details": details,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Metaresearch: Metric Discovery Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              uv run metaresearch.py --goal "Make my API error messages more helpful"
              uv run metaresearch.py --goal "Improve Python docstring readability"
              echo "Make the onboarding flow feel faster" | uv run metaresearch.py
              uv run metaresearch.py --goal "..." --regenerate --verbose --runs 3
        """),
    )
    parser.add_argument("--goal", default=None,
                        help="The subjective goal to discover a metric for (or pipe via stdin)")
    parser.add_argument("--runs", type=int, default=1,
                        help="Scoring runs per artifact for stability (default: 1)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show pair-by-pair results")
    parser.add_argument("--regenerate", action="store_true",
                        help="Force regeneration of calibration pairs even if cache exists")
    parser.add_argument("--cache", default=CALIBRATION_CACHE,
                        help=f"Path to calibration pairs cache (default: {CALIBRATION_CACHE})")
    parser.add_argument("--provider", default=None,
                        help="LLM provider override (anthropic/openai)")
    parser.add_argument("--model", default=None,
                        help="Model name override")
    args = parser.parse_args()

    t_start = time.time()

    # -----------------------------------------------------------------------
    # Resolve goal: CLI arg > stdin > error
    # -----------------------------------------------------------------------
    goal = args.goal
    if goal is None:
        if not sys.stdin.isatty():
            goal = sys.stdin.read().strip()
        if not goal:
            print("Error: No goal provided.")
            print("Use --goal '...' or pipe a goal string via stdin.")
            sys.exit(1)

    goal_preview = goal.strip().replace("\n", " ")[:80]
    print(f"Goal: {goal_preview}...")
    print()

    # -----------------------------------------------------------------------
    # Create LLM client (used for both pair generation and metric scoring)
    # -----------------------------------------------------------------------
    llm = make_llm(provider=args.provider, model=args.model)
    print(f"LLM: {llm.provider}/{llm.model}")
    print()

    # -----------------------------------------------------------------------
    # Load or generate calibration pairs
    # -----------------------------------------------------------------------
    goal_data = load_or_generate_pairs(
        goal, llm, cache_path=args.cache, regenerate=args.regenerate
    )
    n_pairs = len(goal_data["calibration_pairs"])
    print(f"Calibration pairs: {n_pairs}")
    print()

    # -----------------------------------------------------------------------
    # Load metric (fresh import to pick up agent edits)
    # -----------------------------------------------------------------------
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if "metric" in sys.modules:
        del sys.modules["metric"]
    import metric
    print(f"Metric: {os.path.abspath(metric.__file__)}")
    print()

    # -----------------------------------------------------------------------
    # Run evaluation
    # -----------------------------------------------------------------------
    if args.verbose:
        print("Pair results:")

    results = evaluate(metric, goal_data, llm, runs=args.runs, verbose=args.verbose)

    if args.verbose:
        print()

    # -----------------------------------------------------------------------
    # Print summary (grep-friendly, matches autoresearch output format)
    # -----------------------------------------------------------------------
    t_end = time.time()
    print("---")
    print(f"concordance:      {results['concordance']:.6f}")
    print(f"avg_margin:       {results['avg_margin']:.6f}")
    print(f"correct_pairs:    {results['correct']}/{results['total']}")
    print(f"total_llm_calls:  {results['total_calls']}")
    print(f"total_seconds:    {t_end - t_start:.1f}")
