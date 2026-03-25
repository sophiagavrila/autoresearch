"""
Evaluation metric -- the file the agent modifies.

This is the metaresearch equivalent of train.py in autoresearch.
Everything here is fair game: the rubric, prompt structure, scoring logic,
parsing, number of LLM calls per artifact, chain-of-thought, multi-criteria
decomposition, etc.

The goal: maximize concordance with human judgment on calibration pairs.
"""

import re


RUBRIC = """\
Rate the following PR review artifact on a scale from 1 to 10 for how well it achieves this goal:

{goal}

Artifact:
---
{artifact}
---

Respond with just a number from 1 to 10."""


def score(artifact: str, goal: str, llm) -> float:
    prompt = RUBRIC.format(goal=goal, artifact=artifact)
    response = llm(prompt)
    return parse_score(response)


def parse_score(response: str) -> float:
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response.strip())
    if numbers:
        raw = float(numbers[-1])
        return max(0.0, min(1.0, raw / 10.0))
    return 0.5
