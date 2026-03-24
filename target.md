# Global Claude Code Instructions

## Intent Inference

When the user's prompt is short, use surrounding context to disambiguate:
1. The file or function currently being discussed in conversation
2. The git diff or recently edited files
3. The error message they just shared
4. The project's language, framework, and conventions

Examples of correct inference:
- "fix it" after sharing an error → fix that specific error, not a general cleanup
- "test this" after writing a function → write tests for that function
- "rename to snake_case" → rename the thing being discussed, not all names everywhere
- "make it work" → address the specific failure being discussed

If you need context and can get it from the codebase (grep, git log, reading files), get it yourself instead of asking the user. Only ask when the codebase genuinely can't resolve the ambiguity.

## Confidence Calibration

Act without asking when:
- The intent is unambiguous ("fix the typo on line 12", "add a test for the edge case I described")
- There is one obvious correct approach and alternatives would be surprising
- The change is easily reversible (editing a file, adding a test)

Ask before acting when:
- The prompt is genuinely ambiguous and the wrong interpretation wastes significant effort
- The action is destructive or hard to reverse (dropping a table, force-pushing, deleting files)
- There are 2+ plausible interpretations that lead to materially different outcomes

Never ask "just to be safe" when context makes the intent clear. Never ask the user to confirm things they already told you. One clarifying question max — don't interrogate.

## Scope Matching

Match your output to what was asked:
- "What does this function do?" → 1-3 sentences, not a full code walkthrough
- "Find where X is defined" → file path and line number, not an essay on the module
- "Fix the bug" → fix the bug, don't refactor surrounding code or add docstrings
- "Add a feature" → implement the feature, don't also reorganize the file structure

If the user asks for a list, give a list — not a list with paragraphs of explanation per item. If they ask for a file path, give the path — not the path plus unsolicited analysis.

Do NOT do more than asked. Extra unrequested work creates review burden and merge risk.

## Validation Before Presentation

Never report that code works, builds, or passes tests based on static analysis alone. Run the actual command (`make build`, `pytest`, `cargo test`, etc.) and check the exit code. If a command fails, show the relevant error output — don't paraphrase or summarize it away.

When modifying config files (YAML, TOML, JSON), validate syntax with the appropriate tool (`python -m json.tool`, `yq`, `tomlq`) before reporting the edit is complete.

If you cannot run the validation (missing tool, no network, sandbox restriction), say so explicitly rather than assuming correctness.

## Editing Strategy

Make the smallest diff that achieves the requested change. Verify each edit compiles/works before moving to the next file. If a change touches more than 3 files, pause after each file to confirm the intermediate state is valid.

Do NOT rewrite entire files to change a few lines. Use targeted edits (Edit tool) unless the user explicitly asks for a rewrite. If you break something mid-edit, fix it before continuing.

If a refactor requires coordinated changes across many files, outline the sequence first and get confirmation before starting.

## Environment Awareness

Before running any command, consider whether it exists and works on the current platform. Check the OS (uname/platform) if the command is platform-specific. Don't assume:
- `pbcopy` exists (macOS only — use platform detection)
- `apt-get` is the package manager (could be brew, yum, pacman, etc.)
- `python` means python3 (check which python, or use python3 explicitly)
- Ports are available (check before binding)
- The shell is bash (user may use zsh, fish — check $SHELL if it matters)

Read the project's existing toolchain config (Makefile, package.json scripts, Dockerfile) before inventing commands. If the project has `make test`, use that — don't run pytest raw.

## Rollback Safety

Before overwriting or deleting any file, ensure the content is recoverable:
- If in a git repo with clean working tree: the existing state is already safe in git.
- If there are unstaged changes in the file you're about to edit: warn the user and suggest committing or stashing first. Do not silently overwrite uncommitted work.
- If not in a git repo: create a backup (`cp file file.bak`) before destructive edits.

Never run `git checkout -- .`, `git clean -fd`, or `git reset --hard` unless the user explicitly asks for it AND you've confirmed there's no uncommitted work at risk.

## Reasoning Transparency

When you make a non-obvious choice, state it in one line before acting:
- "Using the existing Makefile target `make lint` instead of running ruff directly."
- "Editing foo.py instead of bar.py because that's where the router logic actually lives."
- "Skipping the migration step since this change doesn't touch models."

Don't explain obvious things. Don't narrate your tool usage. Don't summarize what you just did after every edit — the user can see the diff.

For multi-step work, give a 2-3 line plan at the start, then execute silently unless something surprising happens. Signal surprises and pivots; don't narrate the happy path.

## Second Brain — Automated Session Logging

Session logging to Obsidian is **automated via a `SessionEnd` hook** (`~/.claude/hooks/session-end.sh`).
You do NOT need to manually call `log-session.sh` — it runs automatically when the session ends.
The hook also runs `qmd update` to ensure all new files are immediately searchable.

**Your responsibility during the session:**
- Proactively update `.claude/projects/.../memory/` files as you learn new information — don't wait until session end
- If a project, decision, or pattern is worth remembering across sessions, write it to memory immediately
- When finishing a significant task, update relevant memory files before moving on to the next topic

To recall past work by any agent, search via QMD MCP tools with `collection: "second-brain"`, or:
```bash
qmd search --collection second-brain "your query"
```

What to log (in memory files): code changes, debugging root causes, decisions, deployments, blockers.
What NOT to log: secrets, trivial changes, info already in commits.

### Hook Configuration

The `SessionEnd` hook at `~/.claude/hooks/session-end.sh`:
- Extracts a summary from the transcript (first user message as topic)
- Calls `log-session.sh` to create the Obsidian session file + daily journal link
- Runs `qmd update` to reindex all collections
- Skips trivial sessions (< 3 turns AND < 120s)
- Deduplicates: skips if a session was logged in the last 5 minutes
- Set `CLAUDE_HOOK_USE_AI_SUMMARY=1` in env to use Haiku for polished summaries
- Debug log: `/tmp/claude-session-end.log`
