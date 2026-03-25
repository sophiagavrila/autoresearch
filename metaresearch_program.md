# metaresearch

Discover evaluation metrics for subjective goals. You are an autonomous researcher iterating on a scoring metric until it reliably captures intent — turning a vague goal string into a proven `score()` function.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar23`). The branch `metaresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b metaresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `metaresearch.py` — fixed harness: LLM client, calibration pair generation, concordance evaluation. Do not modify.
   - `metric.py` — the file you modify. Evaluation rubric, prompt, scoring logic.
4. **Verify LLM access**: Confirm that `ANTHROPIC_API_KEY` (or equivalent) is set. Run a quick test: `uv run metaresearch.py --goal "test" --dry-run` if available, or just proceed — the first real run will validate access.
5. **Get the goal from the user**: The user provides a single goal string. This is your only input. Examples:
   - "Make my API error messages more helpful for debugging"
   - "Improve the readability of my Python docstrings"
   - "Make the onboarding flow feel faster"
6. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
7. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off Phase 0.

## Phase 0 — Calibration Pair Generation

Before the discovery loop, you need calibration pairs — synthetic better/worse examples that define what "good" means for this goal. The harness generates these automatically.

1. **Run the harness with the user's goal**:
   ```bash
   uv run metaresearch.py --goal "user's goal here" --verbose > run.log 2>&1
   ```
   On first run, `metaresearch.py` detects that `calibration_pairs.yaml` does not exist and auto-generates 8 calibration pairs via LLM. It caches them to `calibration_pairs.yaml` so subsequent runs reuse the same pairs.

2. **Review the generated pairs**: Read `calibration_pairs.yaml`. Each pair has a `better` artifact, a `worse` artifact, and a `reason` explaining why better is better. Check that:
   - The pairs actually reflect the goal (not generic quality)
   - The "better" artifacts are clearly better than the "worse" artifacts
   - The reasons are specific and non-trivial
   - There's variety across the pairs (different aspects of the goal)

3. **Regenerate if needed**: If the pairs look bad (vague, wrong, or all testing the same dimension), delete `calibration_pairs.yaml` and re-run with `--regenerate`:
   ```bash
   rm calibration_pairs.yaml
   uv run metaresearch.py --goal "user's goal here" --regenerate --verbose > run.log 2>&1
   ```

4. **Record baseline**: The first run also evaluates the naive `metric.py` baseline against the pairs. Extract results:
   ```bash
   grep "^concordance:\|^avg_margin:" run.log
   ```
   This is your starting point. Log it to `results.tsv` as the baseline.

Once pairs look good and baseline is recorded, proceed to Phase 1.

## Phase 1 — Metric Discovery Loop

Each experiment evaluates your modified metric against all calibration pairs. You launch it as:
```bash
uv run metaresearch.py --goal "user's goal here" --verbose > run.log 2>&1
```

**What you CAN do:**
- Modify `metric.py` — this is the only file you edit. Everything is fair game: the rubric text, prompt structure, scoring scale, chain-of-thought reasoning, multi-criteria decomposition, few-shot examples, output parsing, number of LLM calls per artifact, etc.

**What you CANNOT do:**
- Modify `metaresearch.py`. It is read-only. It contains the fixed meta-evaluation, LLM client, and calibration pair generation.
- Modify `calibration_pairs.yaml` after Phase 0. It is fixed for the duration of the experiment.
- Install new packages or add dependencies.

**The goal is simple: get the highest concordance.** Concordance measures what fraction of calibration pairs your metric ranks correctly — 1.0 means perfect agreement with the generated judgment. Secondary goal: maximize avg_margin (how decisively the metric separates better from worse artifacts).

**Target**: concordance >= 0.9 with avg_margin > 0.15. This means the metric is "proven" — it reliably discriminates quality for this goal.

**What to try** (roughly ordered by likely impact):

1. **Specific rubric criteria**: Read the goal and the calibration pair reasons carefully. What makes "better" actually better? Name those dimensions explicitly in the rubric. A rubric that says "rate helpfulness 1-10" will always lose to one that says "rate on: (a) identifies the root cause, (b) suggests a fix, (c) includes relevant context."
2. **Chain-of-thought**: Have the LLM reason step-by-step before scoring. This often dramatically improves discrimination. Ask it to analyze the artifact against each criterion, then synthesize a score.
3. **Multi-criteria decomposition**: Score on 3-5 specific dimensions, then combine (weighted average, min, etc.). E.g., for error messages: specificity, actionability, context, tone.
4. **Scoring scale changes**: Try 1-5, 1-100, or even binary (good/bad) with confidence. Different scales work better for different goals.
5. **Structured JSON output**: Ask for JSON with per-criterion reasoning + scores for more reliable parsing and richer signal.
6. **Comparative framing**: Score the artifact relative to an ideal rather than in absolute terms. "How far is this from the best possible version?"
7. **Negative criteria**: Explicitly list what scores poorly — vagueness, missing context, jargon without explanation, etc.
8. **Prompt engineering**: System-level framing, role assignment ("You are an expert evaluator with 10 years of experience in..."), formatting, examples.

**What to avoid:**
- **Overfitting to calibration**: Do NOT hardcode all calibration pairs as few-shot examples — the metric must generalize to new artifacts, not just memorize the calibration set. Using 1-2 as illustrations is fine; using all of them is overfitting.
- **Excessive complexity**: A metric that makes 5 LLM calls per artifact is expensive and slow. Prefer single-call metrics unless multi-call clearly improves concordance.
- **Fragile parsing**: If the LLM's response format varies, your parser must handle it gracefully. Always have fallback parsing.

**Simplicity criterion**: All else being equal, simpler is better. A 0.01 concordance improvement from adding 30 lines of hacky prompting? Probably not worth it. A 0.01 improvement from removing unnecessary prompt text? Keep. An improvement of ~0 but much simpler code? Keep.

**The first run**: Your very first run establishes the baseline — the naive metric's concordance against the generated pairs. This was already done in Phase 0.

## Output format

When the script finishes it prints:

```
---
concordance:      0.714286
avg_margin:       0.085714
correct_pairs:    5/7
total_llm_calls:  14
total_seconds:    12.3
```

Extract the key metrics: `grep "^concordance:\|^avg_margin:" run.log`

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

The TSV has a header row and 5 columns:

```
commit	concordance	avg_margin	status	description
```

1. git commit hash (short, 7 chars)
2. concordance achieved (e.g. 0.857143) — use 0.000000 for crashes
3. avg_margin (e.g. 0.152000) — use 0.000000 for crashes
4. status: `keep`, `discard`, or `crash`
5. short text description of what this experiment tried

Example:

```
commit	concordance	avg_margin	status	description
a1b2c3d	0.625000	0.042000	keep	baseline (naive 1-10 rubric)
b2c3d4e	0.750000	0.110000	keep	added goal-specific criteria from calibration reasons
c3d4e5f	0.750000	0.095000	discard	chain-of-thought with 1-100 scale (margin regressed)
d4e5f6g	0.875000	0.185000	keep	multi-criteria: specificity + actionability + context
e5f6g7h	1.000000	0.234500	keep	structured JSON output with per-criterion reasoning
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `metaresearch/mar23`).

LOOP FOREVER:

1. Look at the git state: current branch/commit
2. Modify `metric.py` with an experimental idea — change the rubric, prompt, scoring logic, parsing, structure
3. git commit
4. Run the experiment: `uv run metaresearch.py --goal "user's goal here" --verbose > run.log 2>&1`
5. Read results: `grep "^concordance:\|^avg_margin:" run.log`
6. If grep output is empty, the run crashed. Run `tail -n 30 run.log` to read the traceback and attempt a fix.
7. Record the results in `results.tsv` (do NOT commit this file — keep it untracked)
8. If concordance improved (higher), you "advance" the branch, keeping the commit
9. If concordance is equal or worse, `git reset` back to where you started
10. If concordance >= 0.9 AND avg_margin > 0.15 — the metric is **proven**. Log a final entry, announce the result, and note that `metric.py` is ready for Phase 2 (autoresearch with subjective goal mode).

**Tie-breaking**: If concordance is equal to current best but avg_margin improved, keep the change — stronger margins make the metric more robust. If both concordance and avg_margin are equal or worse, discard.

**Crashes**: Usually a parsing error or API issue. Fix and re-run. If the idea is fundamentally broken, skip it, log "crash," and move on.

**Convergence stalls**: If you've been stuck at the same concordance for 5+ experiments, try something radically different — a completely different prompt structure, a different scoring paradigm (binary instead of numeric), multi-pass evaluation, or go back to the calibration pair reasons and look for patterns you missed.

**NEVER STOP**: Once the experiment loop has begun (after Phase 0), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, re-read the goal and calibration pair reasons for inspiration. Try combining strategies that each helped a little. Try removing things. The loop runs until the human interrupts you or you hit the convergence target.

As an example use case, a user might leave you running while they sleep. Each experiment takes ~30 seconds (LLM calls), so you can run far more experiments per hour than autoresearch (~100+/hour). The user wakes up to a proven metric.

## When you're done

When the metric achieves concordance >= 0.9 with avg_margin > 0.15, the metric is **proven**. The deliverable is `metric.py` — specifically its `score(artifact: str, goal: str, llm: callable) -> float` function.

This proven metric is the input to Phase 2: autoresearch's "Subjective Goal Mode" (see `program.md`). The two phases compose:

1. **metaresearch** (this file) discovers the metric from a vague goal
2. **autoresearch** (`program.md`) uses that metric to optimize any text artifact

The discovered metric IS the deliverable.
