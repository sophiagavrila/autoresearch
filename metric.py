"""
Evaluation metric for PR review quality.

Scores PR reviews on whether they find real bugs, security vulnerabilities,
and substantive logic errors — not stylistic nitpicks. Optimized for
concordance with calibration pairs testing high-signal review quality.
"""

import re


RUBRIC = """\
You are a senior security engineer evaluating a PR review for quality.

Goal: {goal}

Score this PR review on 5 criteria (each 1-10):

1. **Bug detection**: Does it identify real bugs, vulnerabilities, or logic errors? (injection, race condition, auth bypass, data leak, off-by-one, null deref, resource leak) Score 1 if it misses critical issues or only finds stylistic problems.

2. **Specificity**: Does it name the exact risk, cite the exact line/file, and explain the mechanism? "Consider using X" scores low. "Line 47: unsanitized input in SQL query allows injection via..." scores high.

3. **Impact explanation**: Does it explain WHY the bug matters with concrete consequences? (data loss, financial damage, service crash, security breach) Vague "could be improved" scores 1.

4. **Actionable fix**: Does it suggest a concrete, correct fix the developer can apply? Code snippets score higher than prose. "Add validation" without specifics scores low.

5. **Signal-to-noise ratio**: Is EVERY comment about correctness, security, or reliability? Deduct heavily for: naming bikeshedding, import ordering, docstring suggestions, formatting preferences, comment style, or any suggestion that doesn't affect runtime behavior. A review with 1 critical finding and 0 noise scores higher than one with 1 critical finding and 5 stylistic nits.

Think step-by-step for each criterion, then output scores in this exact format:

BUG_DETECTION: <score>
SPECIFICITY: <score>
IMPACT: <score>
FIX_QUALITY: <score>
SIGNAL_NOISE: <score>
FINAL: <weighted average, weighting signal_noise and bug_detection 2x>

Artifact:
---
{artifact}
---"""


def score(artifact: str, goal: str, llm) -> float:
    prompt = RUBRIC.format(goal=goal, artifact=artifact)
    response = llm(prompt)
    return parse_score(response)


def parse_score(response: str) -> float:
    final_match = re.search(r'FINAL:\s*(\d+(?:\.\d+)?)', response)
    if final_match:
        raw = float(final_match.group(1))
        return max(0.0, min(1.0, raw / 10.0))

    scores = {}
    weights = {
        'BUG_DETECTION': 2.0,
        'SPECIFICITY': 1.0,
        'IMPACT': 1.0,
        'FIX_QUALITY': 1.0,
        'SIGNAL_NOISE': 2.0,
    }
    for label, weight in weights.items():
        match = re.search(rf'{label}:\s*(\d+(?:\.\d+)?)', response)
        if match:
            scores[label] = float(match.group(1))

    if scores:
        weighted_sum = sum(scores[k] * weights[k] for k in scores)
        total_weight = sum(weights[k] for k in scores)
        avg = weighted_sum / total_weight
        return max(0.0, min(1.0, avg / 10.0))

    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response.strip())
    if numbers:
        raw = float(numbers[-1])
        return max(0.0, min(1.0, raw / 10.0))
    return 0.5
