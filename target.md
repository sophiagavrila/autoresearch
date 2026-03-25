# Weekly Snippet Generator

Generate my weekly snippet for the vuln-mgmt-eng team. Due EoD Thursday.

## Execution (2 tool calls max)

**Single parallel round — 2 calls:**
1. **All GitHub activity** (one Bash call with `&&`-chained commands):
   ```bash
   gh search prs --author=sophiagavrila --merged --sort=updated --json number,title,repository,url -- "merged:>=<last-friday>" && \
   gh search prs --reviewed-by=sophiagavrila --sort=updated --json number,title,repository,url -- "updated:>=<last-friday>" && \
   gh search issues --author=sophiagavrila --sort=updated --json number,title,repository,url -- "updated:>=<last-friday>"
   ```
2. **Session context**: `mcp__qmd__search { collection: "second-brain", query: "week session logs", limit: 10 }`

Memory (`MEMORY.md`) only if gaps remain after the above.

**Then compose the snippet directly.** No preamble, no intermediate summaries.

## Rules

- Time window: last Friday → today
- **Shipped (🚢)** = I authored AND it merged. Reviews → "Supported" section.
- **OKR progress first** in TL;DR and section ordering
- **Link every claim** to a PR/issue URL
- **Concise** — no filler, no unsupported statements
- **@mentions** for collaboration shoutouts
- Honest about WIPs

## Output (copy-paste ready, fenced code block)

```markdown
### TL;DR
2-3 sentences. OKR progress leads, then KTLO/security posture.

### <OKR Name> (OKR)
Ship-readiness, refactor stats, test counts, architectural decisions.

### Security Posture
Quantify: "X close on Y ship, Z to tackle, then zero."

### KTLO & Misc
🚢 Shipped + links. Reviews with @mentions. Investigations filed.
```

## DO NOT

- Run queries sequentially that can be parallelized or chained
- Read files not needed for the snippet (no codebase grep, no READMEs)
- Narrate your process or produce intermediate summaries
- Over-fetch: 10 QMD results is enough, don't paginate or re-query
