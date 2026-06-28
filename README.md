# Stack Optimizer for Claude Code

Auto-detect your project stack and configure Claude Code for it -- skills, MCP servers, hooks, and rules tailored to your framework, language, and database.

Run `/optimize` in any project, or use the CLI directly:

```
python ~/.claude/skills/optimize/optimize.py scan --dir my-project
```

## Why

Every time you start a new project or clone a repo, you have to re-explain your stack to Claude Code. This tool automates that: one command, your AI understands what you're building.

## Install

```
git clone https://github.com/8thsyn/claude-code-optimize ~/dev/claude-code-optimize
ln -s ~/dev/claude-code-optimize ~/.claude/skills/optimize
```

## Usage

```
cd my-project

python ~/.claude/skills/optimize/optimize.py scan       # what's in my stack?
python ~/.claude/skills/optimize/optimize.py recommend   # what should I add?
python ~/.claude/skills/optimize/optimize.py report      # what's configured?
python ~/.claude/skills/optimize/optimize.py list-sources  # where to find more tools
```

Or in a Claude Code session, just type: `/optimize`

## What it detects

Reads package.json, pyproject.toml, Cargo.toml, go.mod, and other config files to identify your exact stack:

| Category       | What's detected                                                                          |
| -------------- | ---------------------------------------------------------------------------------------- |
| Languages      | TypeScript, JavaScript, Python, Rust, Go                                                 |
| Frameworks     | Next.js, React, Vue, Svelte, Astro, Nuxt, Express, Fastify, Django, FastAPI, Flask, Vite |
| Databases      | Prisma, PostgreSQL, SQLite, MongoDB, Redis                                               |
| Testing        | Vitest, Jest, Playwright, Cypress, pytest                                                |
| CSS            | Tailwind CSS, shadcn/ui                                                                  |
| CI/CD          | GitHub Actions, Vercel, Netlify, GitLab CI                                               |
| Infrastructure | Docker, Terraform                                                                        |
| Mobile         | React Native                                                                             |

Falls back to file extension scanning when no config files exist (pure Python, Rust, Go repos).

## What it recommends

Each detected component maps to:

- **Skills** -- react-best-practices, shadcn, vercel-optimize, and more
- **MCP servers** -- playwright-mcp, chrome-devtools, sqlite, and more
- **Hooks** -- TypeScript type checking, build verification, linting
- **Rules** -- Framework-specific conventions written to `.claude/rules/`

The knowledge base handles inheritance automatically: Next.js detects as Next.js -> React -> TypeScript, and recommends tools for all three.

## Output example

```
Detected:
  framework: nextjs (95% confidence)
  framework: react (95% confidence)
  language: typescript (90% confidence)
  database: prisma (95% confidence)
  testing: vitest (95% confidence)

Recommended tools (15 total):

  Hooks:
    - PostToolUse: npx tsc --noEmit 2>/dev/null || true
    - PostToolUse: npx vitest run --changed 2>/dev/null || true

  MCP servers:
    - playwright-mcp -- MCP server for nextjs
    - chrome-devtools -- MCP server for nextjs

  Skills:
    - vercel-composition-patterns -- skill for nextjs
    - shadcn -- skill for nextjs
    - react-best-practices -- skill for nextjs
    - database-schema-designer -- skill for prisma
```

## Extending

Add your own framework or tool mappings to `recommendations.json`. Each entry specifies what to detect, what to recommend, and what to install:

```json
{
  "frameworks": {
    "my-framework": {
      "detect": { "dep": "my-framework" },
      "skills": ["my-custom-skill"],
      "mcps": ["my-custom-mcp"],
      "hooks": { "PostToolUse": ["npm run validate"] },
      "rules": ["Custom framework conventions"]
    }
  }
}
```

## Dependencies

Python 3.10+. Standard library only -- no pip packages required.

## Project structure

```
claude-code-optimize/
  SKILL.md              # Claude Code skill definition
  optimize.py           # CLI tool (single file, stdlib only)
  recommendations.json  # Curated knowledge base
  README.md
```

## License

MIT
