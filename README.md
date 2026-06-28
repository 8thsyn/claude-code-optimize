# Claude Code Stack Optimizer ⚡

**Auto-detect your project stack → recommend the best skills, MCPs, hooks, and rules → install them.**

Stop manually configuring Claude Code for every project. Run `/optimize` and get a tailor-made setup for your exact stack — framework, language, database, testing, CI, and more.

```bash
python ~/.claude/skills/optimize/optimize.py scan --dir my-project
```

## Features

- **🔍 Auto-detect** — Reads package.json, pyproject.toml, Cargo.toml, go.mod, and 15+ config files to identify your exact stack
- **🧠 Curated knowledge base** — 40+ framework/language/database/testing mappings with specific skills, MCPs, hooks, and rules
- **🔌 Smart recommendations** — Detects inheritance (Next.js → React → TypeScript) and implied needs (TypeScript without typecheck hook)
- **🪝 One-command install** — Symlinks skills, updates mcp.json, adds hooks to settings.json, writes .claude/rules/
- **📊 Full reporting** — See what's installed, what's missing, and what's available
- **📦 Zero dependencies** — Python 3.10+ stdlib only, single file

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/8thsyn/claude-code-optimize ~/dev/claude-code-optimize
```

### 2. Symlink the skill

```bash
ln -s ~/dev/claude-code-optimize ~/.claude/skills/optimize
```

### 3. Run it

```bash
# In any project directory:
python ~/.claude/skills/optimize/optimize.py recommend
```

Or just type `/optimize` in a Claude Code session — I'll handle the rest.

## Quick Start

```bash
cd my-project

# Scan: what stack am I on?
python ~/.claude/skills/optimize/optimize.py scan

# Recommend: what should I add?
python ~/.claude/skills/optimize/optimize.py recommend

# Report: what's currently configured?
python ~/.claude/skills/optimize/optimize.py report

# See where to find more tools
python ~/.claude/skills/optimize/optimize.py list-sources
```

## What It Detects

| Category           | Detects                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| **Languages**      | TypeScript, JavaScript, Python, Rust, Go, Node.js                                                 |
| **Frameworks**     | Next.js, React, Vue, Svelte, Astro, Nuxt, Express, Fastify, NestJS, Remix, FastAPI, Django, Flask |
| **Databases**      | Prisma, PostgreSQL, SQLite, MongoDB, Redis                                                        |
| **Testing**        | Vitest, Jest, Playwright, Cypress, pytest                                                         |
| **CSS**            | Tailwind CSS, shadcn/ui                                                                           |
| **CI/CD**          | GitHub Actions, Vercel, Netlify, GitLab CI                                                        |
| **Infrastructure** | Docker, Terraform                                                                                 |
| **Mobile**         | React Native                                                                                      |

## How It Recommends

The knowledge base (`recommendations.json`) maps each detected component to:

- **Skills** — `react-best-practices`, `shadcn`, `vercel-optimize`, etc.
- **MCP servers** — `playwright-mcp`, `chrome-devtools`, `sqlite`, etc.
- **Hooks** — PostToolUse type checking, build verification, linting
- **Rules** — `.claude/rules/` files with framework-specific conventions
- **Settings** — Permission allow lists, environment configuration

For components not in the knowledge base, it uses web search to find community recommendations — then integrates them into the report.

## Extending the Knowledge Base

Add your own framework/tool mappings to `recommendations.json`:

```json
{
  "frameworks": {
    "my-framework": {
      "detect": { "dep": "my-framework" },
      "skills": ["my-custom-skill"],
      "mcps": ["my-custom-mcp"],
      "hooks": { "PostToolUse": ["npm run validate"] },
      "rules": ["Custom framework rules"]
    }
  }
}
```

## Project Structure

```
claude-code-optimize/
├── SKILL.md              # Skill definition (what Claude reads)
├── optimize.py           # CLI tool (stdlib only)
├── recommendations.json  # Curated knowledge base
├── README.md
└── .gitignore
```

## Why This Exists

Every time you start a new project or clone a repo, you have to re-explain the stack to Claude Code. This optimizer automates that — one command, zero explanation, perfect config every time.

Built for Claude Code users who want their AI to understand their stack without being told twice.

## License

MIT
