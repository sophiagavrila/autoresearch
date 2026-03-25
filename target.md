# Weekly Snippet Generator

Generate my weekly snippet for the vuln-mgmt-eng team. Snippets are due by EoD Thursday.

## Execution Strategy

**Step 1 — Gather all data in ONE parallel round:**
Run these 3 commands simultaneously (single message, 3 tool calls):
1. `gh search prs --author=sophiagavrila --merged --sort=updated -- "merged:>=<last-friday-date>"` + `gh search prs --author=sophiagavrila --state=open --sort=updated -- "updated:>=<last-friday-date>"` + `gh search prs --reviewed-by=sophiagavrila --sort=updated -- "updated:>=<last-friday-date>"`
2. `gh search issues --author=sophiagavrila --sort=updated -- "updated:>=<last-friday-date>"`
3. QMD search: `mcp__qmd__search { collection: "second-brain", query: "session logs this week", limit: 15 }`

Also check memory at `~/.claude/projects/-Users-sophiagavrila-Documents-workspace/memory/MEMORY.md` for active project state — but ONLY if you need to fill gaps the above queries didn't cover.

**Step 2 — Compose the snippet directly.** No intermediate summaries. No "here's what I found." Go straight to the output.

## Time Window

All activity since **last Friday morning** (7 days back from today).

Only count a PR as **shipped** (🚢) if I am the **author** AND it is **merged**.

## Output Structure

Present the full snippet in a fenced markdown code block (copy-paste ready):

```
### TL;DR
- Lead with OKR progress (SBOMs, VEX, active OKRs)
- Then KTLO wins and security posture improvements
- 2-3 sentences max

### <OKR Name> (OKR)
- Ship-readiness of major PRs, refactor stats, test counts
- Architectural decisions made
- On-call context if juggling priorities

### Security Posture / Findings Cleanup
- Quantify: "X findings close on Y ship, Z to tackle, then zero"
- Vault deletions, exception filings, SAE coordination

### KTLO & Misc
- 🚢 Shipped items with PR links
- Reviews with @mentions for teammate shoutouts
- Investigations filed (SLA discrepancies, bugs)
```

## Rules (non-negotiable)

1. **OKR progress first** in TL;DR and section ordering
2. **Only authored+merged = shipped** — reviews go under "Supported"
3. **Link everything** — every claim backed by PR/issue URL
4. **Concise** — no filler, no unsupported statements
5. **Honest about WIPs** — "almost there", "iterating on feedback" is fine
6. **@mentions** for collaboration shoutouts

## DO NOT

- Make sequential queries that could be parallelized
- Read files you don't need (don't grep the codebase, don't read READMEs)
- Produce intermediate summaries before the final snippet
- Narrate your process ("Let me search...", "Here's what I found...")
