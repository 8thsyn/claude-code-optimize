---
name: optimize
description: "Project stack optimizer: auto-detect your framework, language, database, and testing stack — then recommend and install the best Claude Code skills, MCP servers, hooks, and rules for it. Run `/optimize` in any project."
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep WebSearch"
---

# Project Stack Optimizer

Analyze your project, detect what you're building, and configure Claude Code for it — skills, MCPs, hooks, and rules for your exact stack.

## Quick Start

In any project, run the CLI:

```bash
python ~/.claude/skills/optimize/optimize.py recommend
```

Or tell Claude: `/optimize` and I'll handle the full flow.

## Full Workflow

### Phase 1: Scan

Run the scanner to detect your project's stack:

```bash
python ~/.claude/skills/optimize/optimize.py scan
```

This reads `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Dockerfile`, CI configs, and more. Outputs: language, framework, database, testing, CSS, CI/CD, infrastructure.

### Phase 2: Recommend

Cross-reference your stack against the curated knowledge base at `recommendations.json`, which maps 40+ components to specific skills, MCPs, hooks, and rules. For gaps, use WebSearch to find community tools.

```bash
python ~/.claude/skills/optimize/optimize.py recommend
```

### Phase 3: Review

Present a categorized summary to the user:

```
Detected:
  [F] framework: nextjs
  [L] language: typescript
  [D] database: prisma
  [T] testing: vitest

Recommendations:
  [S] react-best-practices — skill for nextjs
  [M] playwright-mcp — MCP server for nextjs
  [H] PostToolUse: npx tsc --noEmit
  [R] App Router conventions
```

Ask for confirmation before proceeding.

### Phase 4: Install

On confirmation:

1. Symlink skills from `~/.claude/skills/` (report if not found)
2. Add MCP servers to `~/.claude/mcp.json`
3. Add hooks to `.claude/settings.json`
4. Write `.claude/rules/{category}.md` files

### Phase 5: Report

Show the final state:

```bash
python ~/.claude/skills/optimize/optimize.py report
```

## See Sources

```bash
python ~/.claude/skills/optimize/optimize.py list-sources
```

Shows top repositories for finding more skills, MCP servers, and hooks.

## Extending

Add framework/tool mappings to `recommendations.json`. Each entry maps a detected component to skills, MCPs, hooks, rules, and settings. Entries can inherit from others (e.g., Next.js extends React which extends TypeScript).
