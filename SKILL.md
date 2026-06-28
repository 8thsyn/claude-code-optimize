---
name: optimize
description: >
  Project stack optimizer: auto-detect your framework, language, database, and
  testing stack — then recommend and install the best Claude Code skills, MCP
  servers, hooks, and rules for it. Run `/optimize` in any project.
---

# Project Stack Optimizer

Analyzes your project, detects what you're building (framework, language, database, testing, CI), and recommends — then installs — the best Claude Code skills, MCP servers, hooks, and rules for your exact stack. Saves hours of manual config across every new or existing project.

## When to Use

- **Starting a new project** — `/optimize` to auto-configure Claude for your stack
- **Joining an existing project** — scan it to get the right tools loaded
- **"This project feels wrong"** — Claude keeps making the same mistake; the optimizer installs guardrails
- **Any project** where you want Claude to understand your stack without you explaining it

## How It Works

### Phase 1: Scan

The optimizer scans your project directory for config files (package.json, pyproject.toml, Cargo.toml, go.mod, etc.) and detects:

- **Language** — TypeScript, Python, Rust, Go, etc.
- **Framework** — Next.js, React, Django, FastAPI, Svelte, etc.
- **Database** — Prisma, PostgreSQL, SQLite, MongoDB, Redis
- **Testing** — Vitest, Jest, Playwright, pytest
- **CSS** — Tailwind, shadcn/ui
- **CI/CD** — GitHub Actions, Vercel, Netlify
- **Infrastructure** — Docker, Terraform

Run the scan:

```bash
python ~/.claude/skills/optimize/optimize.py scan [--dir <project>]
```

### Phase 2: Research

For each detected component, cross-reference against the curated knowledge base at `recommendations.json` — which maps frameworks → skills, languages → hooks, databases → MCP servers, etc.

For components not in the knowledge base, use web search to find community recommendations:

1. Search: `"Claude Code" "best skills" "<framework>" 2026`
2. Search: `"MCP server" "<database>" Claude Code`
3. Search: `"Claude Code hook" "<testing framework>"`

Synthesize findings into the recommend output.

Show the full recommendation report:

```bash
python ~/.claude/skills/optimize/optimize.py recommend [--dir <project>]
```

### Phase 3: Review & Confirm

Present the user with a categorized summary:

```
🧱 Framework: Next.js detected
  🛠 Skills to install: vercel-composition-patterns, shadcn, react-best-practices
  🔌 MCPs to add: playwright-mcp, chrome-devtools
  🪝 Hooks to add: build check on every edit
  📋 Rules to add: App Router conventions, Server Components default

🔤 Language: TypeScript detected
  🪝 Hooks to add: tsc --noEmit on every edit
  📋 Rules to add: no `any`, prefer interfaces

🗄 Database: Prisma detected
  🛠 Skills to install: database-schema-designer
  🔌 MCPs to add: sqlite
```

Ask for confirmation before installing.

### Phase 4: Install

On confirmation:

```bash
# Export recommendations to a JSON file for review
python ~/.claude/skills/optimize/optimize.py recommend --dir . > /tmp/recs.json

# Install (symlink skills, update mcp.json, add hooks, write rules)
# Use the install command with the recommendations:
# (Installation is done step-by-step by Claude following the prompt)
```

Installation steps (each confirmed):

1. **Skills** — Symlink from `~/.claude/skills/` if already cloned, or notify user of what to clone
2. **MCPs** — Add entries to `~/.claude/mcp.json`
3. **Hooks** — Add to `.claude/settings.json`
4. **Rules** — Write `.claude/rules/{category}.md` files
5. **Settings** — Add permissions to `.claude/settings.json`

### Phase 5: Report

Show the final state:

```bash
python ~/.claude/skills/optimize/optimize.py report [--dir <project>]
```

## Workflow

```
User: /optimize
Claude: Runs scan → shows detected stack → researches missing gaps
       → presents recommendations → asks for confirmation
       → installs → shows report
User: Approves (or modifies selection)
Claude: Installs → confirms → suggests next steps
```

## Common Mistakes

- **Skipping the confirm step** — always show the user what you're about to install before doing it
- **Installing duplicates** — check if a skill/MCP/hook already exists before adding
- **Overwhelming the user** — present 5-10 high-value recommendations, not everything. Focus on what makes the biggest difference.
- **Assuming the skills are cloned** — not all skills are in the skills directory. Check first, then guide the user.
