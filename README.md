# autoresearch + metaresearch

![teaser](progress.png)

> **This is a fork of [@karpathy's autoresearch](https://github.com/karpathy/autoresearch).** The original repo lets an AI agent autonomously optimize LLM training code overnight. This fork adds **Phase 1: metaresearch** — a system that turns vague, subjective goals (like "make my PR reviews find real bugs") into **proven evaluation metrics**, no GPU required. Metaresearch runs first to discover *what "better" means*, then autoresearch (Phase 2) can optimize against that metric. Both phases use the same core loop: modify code, run, measure, keep or discard, repeat forever.

---

## What this repo does — the 30-second version

You give an AI agent a goal. It runs experiments autonomously while you sleep. You wake up to results.

```
                    ┌──────────────────────────────────────────────────────────┐
                    │              THE AUTORESEARCH LOOP                       │
                    │                                                          │
                    │    ┌─────────┐    ┌─────────┐    ┌──────────────┐        │
                    │    │ Modify  │───>│  Run    │───>│   Measure    │        │
                    │    │  code   │    │ experiment   │   metric     │        │
                    │    └─────────┘    └─────────┘    └──────┬───────┘        │
                    │         ^                               │                │
                    │         │         ┌──────────┐          │                │
                    │         │    NO   │  Better  │   YES    │                │
                    │         └─────────┤  than    │<─────────┘                │
                    │        git reset  │  before? │  git keep                 │
                    │                   └──────────┘                           │
                    │                                                          │
                    │              Repeat forever.                             │
                    └──────────────────────────────────────────────────────────┘
```

There are **two phases** — pick the one that matches your problem:

```
    PHASE 1: metaresearch                    PHASE 2: autoresearch
    ──────────────────────                   ─────────────────────
    "Make my X better"                       "Make a better model"
    (when you can't define                   (or optimize any artifact
     what 'better' means)                     against a known metric)

    Agent edits: metric.py                   Agent edits: train.py
    Metric:      concordance (higher=better) Metric:      val_bpb (lower=better)
    Needs:       LLM API key (or Claude Code)Needs:       NVIDIA GPU
    Speed:       ~100+ experiments/hour      Speed:       ~12 experiments/hour
    Output:      A proven score() function   Output:      Better LLM training code
```

**Phase 1 feeds Phase 2.** Metaresearch discovers what "better" means (the metric). Then autoresearch optimizes against that metric.

---

## How Phase 1 (metaresearch) works

This is the new part. Here's what happens step by step:

```
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                                                                          │
    │   YOU provide a goal string:                                             │
    │   "Make my API error messages more helpful for debugging"                │
    │                                                                          │
    │       │                                                                  │
    │       v                                                                  │
    │                                                                          │
    │   STEP 1: Generate calibration pairs (automatic, one-time)               │
    │   ┌────────────────────────────────────────────────────────────────┐      │
    │   │ The LLM generates 8 pairs of "better" vs "worse" examples    │      │
    │   │ that represent your goal. These are cached to disk.          │      │
    │   │                                                              │      │
    │   │  BETTER: "Error 403: Token expired at 14:23 UTC.            │      │
    │   │          Refresh via POST /auth/token. See: docs/auth.md"   │      │
    │   │                                                              │      │
    │   │  WORSE:  "Error: forbidden"                                  │      │
    │   └────────────────────────────────────────────────────────────────┘      │
    │       │                                                                  │
    │       v                                                                  │
    │                                                                          │
    │   STEP 2: The agent iterates on metric.py (runs autonomously)            │
    │   ┌────────────────────────────────────────────────────────────────┐      │
    │   │ Each iteration, the agent:                                   │      │
    │   │  1. Tweaks the rubric, prompt, or scoring logic              │      │
    │   │  2. Runs the metric against all 8 calibration pairs          │      │
    │   │  3. Measures concordance (did the metric rank them right?)   │      │
    │   │  4. Keeps improvements, discards regressions                 │      │
    │   │                                                              │      │
    │   │ Convergence target: concordance >= 0.9, avg_margin > 0.15   │      │
    │   └────────────────────────────────────────────────────────────────┘      │
    │       │                                                                  │
    │       v                                                                  │
    │                                                                          │
    │   DELIVERABLE: metric.py with a proven score() function                  │
    │   score(artifact, goal, llm) -> float  (0.0 = bad, 1.0 = perfect)       │
    │                                                                          │
    │   Use it in CI, evals, or pipe it into Phase 2 to optimize artifacts.   │
    │                                                                          │
    └──────────────────────────────────────────────────────────────────────────┘
```

**Concordance** = what fraction of calibration pairs the metric ranks correctly (1.0 = perfect).
**avg_margin** = how decisively it separates "better" from "worse" (higher = more confident).

---

## Quick start: metaresearch (Phase 1)

No GPU required. Just an LLM.

### 1. Clone and install

```bash
git clone https://github.com/sophiagavrila/autoresearch.git
cd autoresearch
uv sync
```

(Don't have `uv`? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 2. Set up LLM access (pick one)

| Method | Setup | Cost |
|--------|-------|------|
| **Claude Code CLI** (recommended) | Just have `claude` in your PATH | Uses your Claude Code subscription |
| **Anthropic API** | `export ANTHROPIC_API_KEY=sk-ant-...` | Pay per token |
| **OpenAI API** | `export OPENAI_API_KEY=sk-...` | Pay per token |

The harness auto-detects which provider is available. Override with `METARESEARCH_PROVIDER=anthropic` or `METARESEARCH_MODEL=claude-sonnet-4-20250514` if needed.

### 3. Run it manually (to see what it does)

```bash
# This generates calibration pairs + evaluates the baseline metric
uv run metaresearch.py --goal "Make my API error messages more helpful for debugging" --verbose
```

You'll see output like:

```
Goal: Make my API error messages more helpful for debugging...
LLM: claude-cli/claude-code-default
Generating calibration pairs from goal...
Generated 8 calibration pairs.
Cached calibration pairs to calibration_pairs.yaml

Pair results:
  pair 0: better=0.8000  worse=0.3000  margin=+0.5000  [PASS]
  pair 1: better=0.7000  worse=0.4000  margin=+0.3000  [PASS]
  pair 2: better=0.6000  worse=0.7000  margin=-0.1000  [FAIL]
  ...
---
concordance:      0.625000
avg_margin:       0.085714
correct_pairs:    5/8
total_llm_calls:  16
total_seconds:    12.3
```

That's your baseline. The agent's job is to push concordance toward 1.0.

### 4. Let the agent run autonomously

Open Claude Code (or any coding agent) in the repo and prompt:

```
Read metaresearch_program.md and let's kick off a new experiment.
My goal: "Make my API error messages more helpful for debugging"
```

Then walk away. The agent will:
- Create a branch (`metaresearch/mar25`)
- Establish a baseline
- Loop forever: modify `metric.py` -> commit -> evaluate -> keep/discard
- Stop only when it hits concordance >= 0.9 with avg_margin > 0.15, or you interrupt it

### 5. Use the proven metric

Once the agent converges, `metric.py` contains a battle-tested `score()` function:

```python
from metric import score
from metaresearch import make_llm

llm = make_llm()
result = score("Error: forbidden", "Make my API error messages more helpful", llm)
# result: 0.2 (bad)

result = score("Error 403: Token expired. Refresh via POST /auth/token.", "...", llm)
# result: 0.85 (good)
```

Or score any file directly:

```bash
uv run eval.py my-error-messages.md --goal "Make my API error messages more helpful"
```

---

## Example goals you can try

**Code quality:**
- `"Make PR reviews find real bugs and security vulnerabilities, not stylistic nitpicks"`
- `"Make code review comments scannable: severity, problem, impact, fix"`

**Documentation:**
- `"Make Python docstrings useful — a developer should understand what the function does, its edge cases, and when NOT to use it"`
- `"Make runbook steps precise enough that an on-call engineer at 3am can follow them without thinking"`

**User-facing text:**
- `"Make CLI help text scannable — users find what they need in under 5 seconds"`
- `"Make API error messages helpful for debugging — include what went wrong, why, and how to fix it"`

**Communication:**
- `"Make incident postmortem action items specific and assignable"`
- `"Make Slack standup updates informative without being wordy"`

**Security:**
- `"Make vulnerability descriptions actionable — engineers know what to fix and why it's urgent"`
- `"Make security finding titles distinguishable at a glance in a list of 200 findings"`

---

## Quick start: autoresearch (Phase 2)

> This is the original Karpathy autoresearch — LLM training optimization on a GPU.

**Requirements:** A single NVIDIA GPU (tested on H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download data and train tokenizer (one-time, ~2 min)
uv run prepare.py

# 4. Manually run a single training experiment (~5 min)
uv run train.py
```

If the above commands all work ok, your setup is working. Spin up Claude/Codex in this repo and prompt:

```
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```

The agent reads `program.md`, creates a branch, runs experiments autonomously (~12/hour, ~100 overnight), and advances the branch when it finds improvements.

---

## Project structure

```
metaresearch (Phase 1 — metric discovery, runs first)
├── metaresearch.py         Fixed: LLM client, calibration pairs, concordance eval (do not modify)
├── metric.py               Agent modifies: rubric, prompt, scoring logic
├── metaresearch_program.md Human edits: agent instructions for Phase 1
├── eval.py                 Score any artifact with the proven metric
├── calibration_pairs.yaml  Auto-generated, cached calibration pairs

autoresearch (Phase 2 — GPU model training, or optimize against proven metric)
├── prepare.py              Fixed: data prep, tokenizer, evaluation (do not modify)
├── train.py                Agent modifies: model architecture, optimizer, training loop
├── program.md              Human edits: agent instructions for Phase 2

shared
├── CLAUDE.md               Agent guidance for Claude Code
├── pyproject.toml          Dependencies
├── results.tsv             Experiment log (untracked by git)
└── progress.png            Training progress visualization
```

---

## How it works (Phase 2 — original autoresearch)

The repo is deliberately kept small and only really has three files that matter:

- **`prepare.py`** — fixed constants, one-time data prep (downloads training data, trains a BPE tokenizer), and runtime utilities (dataloader, evaluation). Not modified.
- **`train.py`** — the single file the agent edits. Contains the full GPT model, optimizer (Muon + AdamW), and training loop. Everything is fair game: architecture, hyperparameters, optimizer, batch size, etc. **This file is edited and iterated on by the agent**.
- **`program.md`** — baseline instructions for one agent. Point your agent here and let it go. **This file is edited and iterated on by the human**.

By design, training runs for a **fixed 5-minute time budget** (wall clock, excluding startup/compilation), regardless of the details of your compute. The metric is **val_bpb** (validation bits per byte) — lower is better, and vocab-size-independent so architectural changes are fairly compared.

If you are new to neural networks, this ["Dummy's Guide"](https://x.com/hooeem/status/2030720614752039185) looks pretty good for a lot more context.

## Design choices

- **Single file to modify.** The agent only touches `metric.py` (Phase 1) or `train.py` (Phase 2). This keeps the scope manageable and diffs reviewable.
- **Fixed time budget.** Phase 2 training always runs for exactly 5 minutes, regardless of your specific platform. This means you can expect approx 12 experiments/hour and approx 100 experiments while you sleep. There are two upsides of this design decision. First, this makes experiments directly comparable regardless of what the agent changes (model size, batch size, architecture, etc). Second, this means that autoresearch will find the most optimal model for your platform in that time budget. The downside is that your runs (and results) become not comparable to other people running on other compute platforms.
- **Self-contained.** No external dependencies beyond PyTorch and a few small packages. No distributed training, no complex configs. One GPU, one file, one metric.
- **Two phases compose.** Phase 1 (metaresearch) discovers the metric. Phase 2 (autoresearch) optimizes against it. Together, they handle even subjective goals end-to-end.

## Platform support

Phase 2 (autoresearch) currently requires a single NVIDIA GPU. In principle it is quite possible to support CPU, MPS and other platforms but this would also bloat the code. People can reference (or have their agents reference) the full/parent nanochat repository that has wider platform support and shows the various solutions (e.g. a Flash Attention 3 kernels fallback implementation, generic device support, autodetection, etc.), feel free to create forks or discussions for other platforms and I'm happy to link to them here in the README in some new notable forks section or etc.

**Phase 1 (metaresearch) runs anywhere** — it only needs an LLM API key or the Claude Code CLI. No GPU required.

Seeing as there seems to be a lot of interest in tinkering with autoresearch on much smaller compute platforms than an H100, a few extra words. If you're going to try running autoresearch on smaller computers (Macbooks etc.), I'd recommend one of the forks below. On top of this, here are some recommendations for how to tune the defaults for much smaller models for aspiring forks:

1. To get half-decent results I'd use a dataset with a lot less entropy, e.g. this [TinyStories dataset](https://huggingface.co/datasets/karpathy/tinystories-gpt4-clean). These are GPT-4 generated short stories. Because the data is a lot narrower in scope, you will see reasonable results with a lot smaller models (if you try to sample from them after training).
2. You might experiment with decreasing `vocab_size`, e.g. from 8192 down to 4096, 2048, 1024, or even - simply byte-level tokenizer with 256 possibly bytes after utf-8 encoding.
3. In `prepare.py`, you'll want to lower `MAX_SEQ_LEN` a lot, depending on the computer even down to 256 etc. As you lower `MAX_SEQ_LEN`, you may want to experiment with increasing `DEVICE_BATCH_SIZE` in `train.py` slightly to compensate. The number of tokens per fwd/bwd pass is the product of these two.
4. Also in `prepare.py`, you'll want to decrease `EVAL_TOKENS` so that your validation loss is evaluated on a lot less data.
5. In `train.py`, the primary single knob that controls model complexity is the `DEPTH` (default 8, here). A lot of variables are just functions of this, so e.g. lower it down to e.g. 4.
6. You'll want to most likely use `WINDOW_PATTERN` of just "L", because "SSSL" uses alternating banded attention pattern that may be very inefficient for you. Try it.
7. You'll want to lower `TOTAL_BATCH_SIZE` a lot, but keep it powers of 2, e.g. down to `2**14` (~16K) or so even, hard to tell.

I think these would be the reasonable hyperparameters to play with. Ask your favorite coding agent for help and copy paste them this guide, as well as the full source code.

## Notable forks

- [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos) (MacOS)
- [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx) (MacOS)
- [jsegov/autoresearch-win-rtx](https://github.com/jsegov/autoresearch-win-rtx) (Windows)
- [andyluo7/autoresearch](https://github.com/andyluo7/autoresearch) (AMD)

## Upstream

This repo is a fork of [karpathy/autoresearch](https://github.com/karpathy/autoresearch). More context on the original project: [tweet 1](https://x.com/karpathy/status/2029701092347630069), [tweet 2](https://x.com/karpathy/status/2031135152349524125).

*One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of "group meeting". That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents running across compute cluster megastructures in the skies. The agents claim that we are now in the 10,205th generation of the code base, in any case no one could tell if that's right or wrong as the "code" is now a self-modifying binary that has grown beyond human comprehension. This repo is the story of how it all began. -@karpathy, March 2026*.

## License

MIT
