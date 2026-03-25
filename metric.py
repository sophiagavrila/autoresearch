"""
Evaluation metric -- the file the agent modifies.

This is the metaresearch equivalent of train.py in autoresearch.
Everything here is fair game: the rubric, prompt structure, scoring logic,
parsing, number of LLM calls, chain-of-thought, multi-criteria decomposition, etc.

The goal: maximize concordance with human judgment on calibration pairs.
"""

import re

# ---------------------------------------------------------------------------
# Rubric: Naive baseline (agent replaces this with goal-specific criteria)
# ---------------------------------------------------------------------------

RUBRIC = """\
You are an expert evaluator. A user has the following goal:
---
{goal}
---

Rate the quality of the artifact below on a scale of 1-10, where:
  1 = completely fails to achieve the goal
  10 = perfectly achieves the goal

Think briefly about what the goal asks for, then score the artifact.

Respond with just a number (1-10).

Artifact to evaluate:
---
{artifact}
---"""


# ---------------------------------------------------------------------------
# Scoring function
# ---------------------------------------------------------------------------

def score(artifact: str, goal: str, llm) -> float:
    """
    Score a single artifact against the goal.

    Args:
        artifact: The text to evaluate
        goal: The subjective goal description
        llm: Callable -- llm(prompt: str) -> response: str

    Returns:
        Score between 0.0 (worst) and 1.0 (best)
    """
    prompt = RUBRIC.format(goal=goal, artifact=artifact)
    response = llm(prompt)
    return parse_score(response)


def parse_score(response: str) -> float:
    """Parse LLM response into a 0.0-1.0 score."""
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response.strip())
    if numbers:
        raw = float(numbers[0])
        # Clamp to 1-10 range, normalize to 0.0-1.0
        return max(0.0, min(1.0, raw / 10.0))
    return 0.5  # fallback
