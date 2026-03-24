# Global Claude Code Instructions

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

## Hook Configuration

The `SessionEnd` hook at `~/.claude/hooks/session-end.sh`:
- Extracts a summary from the transcript (first user message as topic)
- Calls `log-session.sh` to create the Obsidian session file + daily journal link
- Runs `qmd update` to reindex all collections
- Skips trivial sessions (< 3 turns AND < 120s)
- Deduplicates: skips if a session was logged in the last 5 minutes
- Set `CLAUDE_HOOK_USE_AI_SUMMARY=1` in env to use Haiku for polished summaries
- Debug log: `/tmp/claude-session-end.log`
