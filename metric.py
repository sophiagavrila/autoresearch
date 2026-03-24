"""
Evaluation metric -- the file the agent modifies.

This is the metaresearch equivalent of train.py in autoresearch.
Everything here is fair game: the rubric, prompt structure, scoring logic,
parsing, number of LLM calls, chain-of-thought, multi-criteria decomposition, etc.

The goal: maximize concordance with human judgment on calibration pairs.
"""

import json
import re

# ---------------------------------------------------------------------------
# Rubric: Multi-criteria decomposition for CLAUDE.md instruction quality
# ---------------------------------------------------------------------------

RUBRIC = """\
You are evaluating a CLAUDE.md instruction snippet for an AI coding assistant.
The goal is: {goal}

Score this instruction on 4 dimensions (1-10 each):

1. SPECIFICITY: Does it name concrete actions, tools, commands, or file types?
   A "10" says "run pytest and check exit code". A "1" says "make sure tests pass".

2. ACTIONABILITY: Could an agent follow this as a protocol without interpretation?
   A "10" is a decision tree with explicit conditions. A "1" is aspirational advice.

3. ANTI-PATTERNS: Does it explicitly name what NOT to do and why?
   A "10" lists specific prohibited actions with rationale. A "1" has no negative examples.

4. CONCISENESS: Is every sentence load-bearing? No fluff, no obvious advice?
   A "10" is tight — nothing to remove. A "1" is padded with "always strive to..." filler.

Think step-by-step: analyze the instruction against each criterion, give a brief
rationale for each score, then provide the 4 scores.

Respond in JSON:
{{"specificity": N, "actionability": N, "anti_patterns": N, "conciseness": N, "rationale": "brief"}}

Instruction to evaluate:
---
{artifact}
---"""


# ---------------------------------------------------------------------------
# Scoring function
# ---------------------------------------------------------------------------

def score(artifact: str, goal: str, llm) -> float:
    """
    Score a single artifact against the goal using multi-criteria decomposition.

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
    """Parse JSON response into a 0.0-1.0 composite score."""
    # Try JSON parse first
    try:
        # Extract JSON from response (may have surrounding text)
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            scores = []
            for key in ("specificity", "actionability", "anti_patterns", "conciseness"):
                val = data.get(key, 5)
                if isinstance(val, (int, float)):
                    scores.append(max(1, min(10, val)))
            if scores:
                # Weighted average: actionability and specificity matter most
                weights = [0.3, 0.3, 0.2, 0.2]  # spec, action, anti, concise
                weighted = sum(s * w for s, w in zip(scores, weights))
                return max(0.0, min(1.0, weighted / 10.0))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: extract first number
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response.strip())
    if numbers:
        raw = float(numbers[0])
        return max(0.0, min(1.0, raw / 10.0))
    return 0.5  # fallback
