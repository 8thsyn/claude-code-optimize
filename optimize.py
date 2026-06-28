#!/usr/bin/env python3
"""Project Stack Optimizer for Claude Code.

Detects your project's stack, recommends skills/MCPs/hooks/rules,
and installs them. One dependency: Python 3.10+.

Usage:
  python optimize.py scan [--dir .]       # Detect stack components
  python optimize.py recommend [--dir .]  # Recommend tools based on stack
  python optimize.py install <file>       # Install from a recommendation file
  python optimize.py report [--dir .]     # Show currently installed tools
  python optimize.py list-sources         # List top skill/MCP sources for discovery
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ─── Data Models ───────────────────────────────────────────────────────────


@dataclass
class DetectedComponent:
    category: str          # "language", "framework", "database", "testing", "css", "ci_cd", "mobile", "infra"
    name: str              # "typescript", "nextjs", etc.
    confidence: float      # 0.0 - 1.0
    detail: str = ""       # e.g. version or additional info
    files: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    components: list[DetectedComponent] = field(default_factory=list)
    project_name: str = ""
    project_dir: str = ""


@dataclass
class Recommendation:
    category: str
    name: str
    kind: str              # "skill", "mcp", "hook", "rule", "setting"
    summary: str
    reason: str
    install_steps: list[str] = field(default_factory=list)


# ─── Scanner ────────────────────────────────────────────────────────────────


class ProjectScanner:
    """Scans a project directory to detect stack components."""

    def __init__(self, project_dir: str | Path):
        self.root = Path(project_dir).resolve()
        self.result = ScanResult(project_dir=str(self.root))

    def scan(self) -> ScanResult:
        self.result.project_name = self.root.name
        self._try_read_package_json()
        self._try_read_pyproject_toml()
        self._try_read_cargo_toml()
        self._try_read_go_mod()
        self._detect_config_files()
        self._detect_docker()
        self._detect_ci()
        self._detect_fallback_languages()
        self._deduplicate()
        return self.result

    def _add(self, category: str, name: str, confidence: float, detail: str = "", files: list[str] | None = None):
        self.result.components.append(DetectedComponent(
            category=category, name=name, confidence=confidence,
            detail=detail, files=files or [],
        ))

    def _try_read_package_json(self):
        path = self.root / "package.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            self._add("language", "javascript", 0.8, files=[str(path)])
            if "typescript" in deps or Path(self.root / "tsconfig.json").exists():
                self._add("language", "typescript", 0.9, files=[str(path)])
            for fw_name, fw_config in FRAMEWORK_DETECT_MAP.items():
                dep = fw_config.get("dep")
                if dep and dep in deps:
                    self._add("framework", fw_name, 0.95, files=[str(path)])
            for test_name in ["vitest", "jest", "@playwright/test", "cypress"]:
                if test_name in deps:
                    label = test_name.replace("@playwright/test", "playwright_test").replace("@", "")
                    self._add("testing", label, 0.95, files=[str(path)])
            for db_name, db_deps in DB_DETECT_MAP.items():
                if any(d in deps for d in db_deps):
                    self._add("database", db_name, 0.9, files=[str(path)])
            for css_name in ["tailwindcss"]:
                if css_name in deps:
                    self._add("css", css_name.replace("tailwindcss", "tailwind"), 0.95, files=[str(path)])
            if "react-native" in deps:
                self._add("mobile", "react_native", 0.95, files=[str(path)])
        except (json.JSONDecodeError, KeyError):
            pass

    def _try_read_pyproject_toml(self):
        path = self.root / "pyproject.toml"
        if not path.exists():
            return
        self._add("language", "python", 0.8, files=[str(path)])
        try:
            text = path.read_text(encoding="utf-8")
            for fw_name, fw_config in PY_FRAMEWORK_DETECT_MAP.items():
                for marker in fw_config.get("markers", []):
                    if marker in text:
                        self._add("framework", fw_name, 0.9, files=[str(path)])
                        break
            if "pytest" in text:
                self._add("testing", "pytest", 0.9, files=[str(path)])
        except Exception:
            pass

    def _try_read_cargo_toml(self):
        path = self.root / "Cargo.toml"
        if not path.exists():
            return
        self._add("language", "rust", 0.9, files=[str(path)])

    def _try_read_go_mod(self):
        path = self.root / "go.mod"
        if not path.exists():
            return
        self._add("language", "go", 0.9, files=[str(path)])

    def _detect_config_files(self):
        checks = [
            ("css", "shadcn", self.root / "components.json", 0.95),
            ("css", "tailwind", self.root.glob("tailwind.config.*"), 0.85),
            ("database", "prisma", self.root / "prisma/schema.prisma", 0.95),
            ("infra", "terraform", list(self.root.glob("*.tf")), 0.9),
            ("deploy", "vercel", self.root / "vercel.json", 0.9),
            ("deploy", "netlify", self.root / "netlify.toml", 0.9),
        ]
        for category, name, target, confidence in checks:
            if isinstance(target, Path) and target.exists():
                self._add(category, name, confidence, files=[str(target)])
            elif isinstance(target, list) and target:
                self._add(category, name, confidence, files=[str(t) for t in target[:3]])

    def _detect_fallback_languages(self):
        """Detect languages by common file extensions when no config files exist."""
        py_files = list(self.root.rglob("*.py"))
        rs_files = list(self.root.rglob("*.rs"))
        js_files = list(self.root.rglob("*.js"))
        ts_files = list(self.root.rglob("*.ts"))
        go_files = list(self.root.rglob("*.go"))

        # Only trigger if we didn't already detect a language via config files
        has_lang = any(c.category == "language" for c in self.result.components)
        if has_lang:
            return

        if py_files:
            self._add("language", "python", 0.5, files=[str(py_files[0])])
        if rs_files:
            self._add("language", "rust", 0.5, files=[str(rs_files[0])])
        if ts_files:
            self._add("language", "typescript", 0.5, files=[str(ts_files[0])])
        elif js_files:
            self._add("language", "javascript", 0.5, files=[str(js_files[0])])
        if go_files:
            self._add("language", "go", 0.5, files=[str(go_files[0])])

    def _detect_docker(self):
        if (self.root / "Dockerfile").exists():
            self._add("infra", "docker", 0.9, files=["Dockerfile"])
        if (self.root / "docker-compose.yml").exists():
            self._add("infra", "docker", 0.85, files=["docker-compose.yml"])

    def _detect_ci(self):
        workflows = list(self.root.glob(".github/workflows/*.yml"))
        if workflows:
            self._add("ci_cd", "github_actions", 0.9, files=[str(w) for w in workflows[:3]])
        if (self.root / ".gitlab-ci.yml").exists():
            self._add("ci_cd", "gitlab_ci", 0.9, files=[".gitlab-ci.yml"])

    def _deduplicate(self):
        seen = set()
        unique: list[DetectedComponent] = []
        for c in self.result.components:
            key = (c.category, c.name)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        self.result.components = unique


# ─── Detection Mappings ─────────────────────────────────────────────────────

FRAMEWORK_DETECT_MAP = {
    "nextjs": {"dep": "next"},
    "react": {"dep": "react"},
    "vue": {"dep": "vue"},
    "svelte": {"dep": "svelte"},
    "astro": {"dep": "astro"},
    "nuxt": {"dep": "nuxt"},
    "express": {"dep": "express"},
    "fastify": {"dep": "fastify"},
    "nestjs": {"dep": "@nestjs/core"},
    "remix": {"dep": "@remix-run/react"},
    "solid": {"dep": "solid-js"},
    "trpc": {"dep": "@trpc/client"},
}

PY_FRAMEWORK_DETECT_MAP = {
    "fastapi": {"markers": ["fastapi"]},
    "django": {"markers": ["django"]},
    "flask": {"markers": ["flask"]},
}

DB_DETECT_MAP = {
    "postgresql": ["pg", "postgres", "@neondatabase/serverless"],
    "sqlite": ["better-sqlite3", "sql.js", "drizzle-orm/sqlite"],
    "mongodb": ["mongoose", "mongodb"],
    "redis": ["ioredis", "redis", "@upstash/redis"],
    "prisma": ["@prisma/client"],
}


# ─── Recommender ────────────────────────────────────────────────────────────


class Recommender:
    """Maps scan results to tool recommendations using the knowledge base."""

    def __init__(self, kb_path: str | Path | None = None):
        self._kb = self._load_kb(kb_path)

    def _load_kb(self, path: str | Path | None = None) -> dict[str, Any]:
        if path is None:
            path = Path(__file__).parent / "recommendations.json"
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load knowledge base: {e}", file=sys.stderr)
            return {}

    def recommend(self, scan: ScanResult) -> list[Recommendation]:
        """Generate recommendations from scan results."""
        results: list[Recommendation] = []
        seen: set[str] = set()

        # Track what's detected for inheritance resolution
        detected = {c.name: c for c in scan.components}

        # Check each detected component against the knowledge base
        for component in scan.components:
            if component.name == "javascript":
                continue  # Skip base langs, only recommend for typed/specific ones
            recs = self._get_for_component(component, detected)
            for r in recs:
                key = f"{r.kind}:{r.name}"
                if key not in seen:
                    seen.add(key)
                    results.append(r)

        # Also check for implied needs (e.g., has Docker but no docker rules)
        self._add_implied_recommendations(results, scan, seen)

        return results

    def _get_for_component(self, component: DetectedComponent, detected: dict[str, DetectedComponent]) -> list[Recommendation]:
        """Get recommendations for a single component, including inherited ones."""
        recs: list[Recommendation] = []
        kb = self._kb

        category_map: dict[str, str] = {
            "framework": "frameworks",
            "language": "languages",
            "testing": "testing",
            "database": "databases",
            "css": "css",
            "ci_cd": "ci_cd",
            "mobile": "mobile",
            "infra": "infra",
        }

        kb_category = category_map.get(component.category)
        if not kb_category:
            return recs

        entry = kb.get(kb_category, {}).get(component.name)
        if not entry:
            return recs

        # Handle inheritance (e.g., nextjs extends react)
        for parent_name in entry.get("extends", []):
            parent_component = DetectedComponent(
                category=component.category,
                name=parent_name,
                confidence=component.confidence * 0.9,
            )
            recs.extend(self._get_for_component(parent_component, detected))

        # Skills
        for skill_name in entry.get("skills", []):
            if skill_name not in {r.name for r in recs if r.kind == "skill"}:
                recs.append(Recommendation(
                    category=component.category,
                    name=skill_name,
                    kind="skill",
                    summary=f"{skill_name} — skill for {component.name}",
                    reason=entry.get("reason", f"Recommended for {component.name}"),
                    install_steps=self._skill_install_steps(skill_name),
                ))

        # MCPs
        for mcp_name in entry.get("mcps", []):
            if mcp_name not in {r.name for r in recs if r.kind == "mcp"}:
                recs.append(Recommendation(
                    category=component.category,
                    name=mcp_name,
                    kind="mcp",
                    summary=f"{mcp_name} — MCP server for {component.name}",
                    reason=entry.get("reason", f"Recommended for {component.name}"),
                    install_steps=self._mcp_install_steps(mcp_name),
                ))

        # Hooks
        for hook_event, hook_commands in entry.get("hooks", {}).items():
            for cmd in hook_commands:
                hook_name = f"{hook_event}: {cmd[:50]}"
                recs.append(Recommendation(
                    category=component.category,
                    name=f"hook_{hook_event}_{len(cmd)}",
                    kind="hook",
                    summary=hook_name,
                    reason=f"{hook_event} hook: {cmd[:80]}",
                    install_steps=[f"Add to settings.json: {hook_event} → {cmd}"],
                ))

        # Rules
        for rule_text in entry.get("rules", []):
            rule_name = f"rule_{hash(rule_text) & 0xFFFF:04x}"
            recs.append(Recommendation(
                category=component.category,
                name=rule_name,
                kind="rule",
                summary=f"Rule: {rule_text[:80]}",
                reason=entry.get("reason", "Recommended for your stack"),
                install_steps=[f"Add to .claude/rules/{component.name}.md"],
            ))

        return recs

    def _add_implied_recommendations(self, results: list[Recommendation], scan: ScanResult, seen: set[str]):
        """Add recommendations for things implied by the detected stack."""
        kb = self._kb

        # If the project has typescript but no typecheck hook, suggest it
        has_typescript = any(c.name == "typescript" for c in scan.components)
        has_typecheck_hook = any("tsc --noEmit" in r.summary for r in results)
        if has_typescript and not has_typecheck_hook:
            results.append(Recommendation(
                category="language", name="tsc_check", kind="hook",
                summary="hook: PostToolUse → npx tsc --noEmit",
                reason="TypeScript project without type checking — add a post-edit typecheck hook",
                install_steps=["Add PostToolUse hook: npx tsc --noEmit"],
            ))

    def _skill_install_steps(self, skill_name: str) -> list[str]:
        steps = []
        # Known skill repos
        known_skills = {
            "react-best-practices": "github.com/anthropics/skills",
            "shadcn": "github.com/anthropics/skills",
            "frontend-design": "github.com/anthropics/skills",
            "web-design-guidelines": "github.com/anthropics/skills",
            "design-system": "github.com/anthropics/skills",
            "vercel-composition-patterns": "github.com/anthropics/skills",
            "vercel-optimize": "github.com/anthropics/skills",
            "playwright-testing": "github.com/anthropics/skills",
            "database-schema-designer": "github.com/anthropics/skills",
            "framework-accessibility": "github.com/anthropics/skills",
        }
        source = known_skills.get(skill_name, "community repo")
        steps.append(f"Check if '{skill_name}' is already in ~/.claude/skills/")
        steps.append(f"If not, find it at {source}")
        steps.append(f"Symlink into ~/.claude/skills/")
        return steps

    def _mcp_install_steps(self, mcp_name: str) -> list[str]:
        mcp_configs = {
            "playwright-mcp": {"command": "npx", "args": ["@playwright/mcp"], "transport": "stdio"},
            "chrome-devtools": {"command": "npx", "args": ["@anthropic/chrome-devtools-mcp"], "transport": "stdio"},
            "sqlite": {"command": "uvx", "args": ["mcp-server-sqlite", "--db-path", "./data.db"], "transport": "stdio"},
            "better-icons": {"command": "npx", "args": ["better-icons"], "transport": "stdio"},
        }
        config = mcp_configs.get(mcp_name)
        if config:
            return [
                f"Add to mcp.json: {json.dumps({mcp_name: config}, indent=2)}",
            ]
        return [f"Find MCP server '{mcp_name}' and add to mcp.json"]


# ─── Installer ──────────────────────────────────────────────────────────────


class Installer:
    """Installs recommendations into the Claude Code configuration."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir).resolve()
        self.claude_dir = Path.home() / ".claude"
        self.skills_dir = self.claude_dir / "skills"
        self.project_claude_dir = self.project_dir / ".claude"
        self.project_claude_dir.mkdir(parents=True, exist_ok=True)

    def install(self, recommendations: list[Recommendation], dry_run: bool = False) -> list[str]:
        """Install recommendations. Returns list of actions taken."""
        actions: list[str] = []

        skills_to_add = [r for r in recommendations if r.kind == "skill"]
        mcps_to_add = [r for r in recommendations if r.kind == "mcp"]
        hooks_to_add = [r for r in recommendations if r.kind == "hook"]
        rules_to_add = [r for r in recommendations if r.kind == "rule"]

        if dry_run:
            if skills_to_add:
                actions.append(f"[DRY RUN] Would install {len(skills_to_add)} skills: {', '.join(r.name for r in skills_to_add)}")
            if mcps_to_add:
                actions.append(f"[DRY RUN] Would add {len(mcps_to_add)} MCP servers: {', '.join(r.name for r in mcps_to_add)}")
            if hooks_to_add:
                actions.append(f"[DRY RUN] Would add {len(hooks_to_add)} hooks")
            if rules_to_add:
                actions.append(f"[DRY RUN] Would add {len(rules_to_add)} rules")
            return actions

        # Install skills (symlink existing or report missing)
        for rec in skills_to_add:
            skill_name = rec.name
            skill_src = self.skills_dir / skill_name
            if skill_src.exists():
                actions.append(f"✓ Skill '{skill_name}' already installed")
            else:
                actions.append(f"⚠ Skill '{skill_name}' not found in {self.skills_dir}")
                actions.append(f"  Install: find the repo and symlink into ~/.claude/skills/{skill_name}")

        # Install MCP servers (add to mcp.json)
        mcp_config_path = self.claude_dir / "mcp.json"
        mcp_config: dict[str, Any] = {}
        if mcp_config_path.exists():
            try:
                mcp_config = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        mcp_changed = False
        known_mcp_configs = {
            "playwright-mcp": {"command": "npx", "args": ["@playwright/mcp"], "transport": "stdio"},
            "chrome-devtools": {"command": "npx", "args": ["@anthropic/chrome-devtools-mcp"], "transport": "stdio"},
            "sqlite": {"command": "uvx", "args": ["mcp-server-sqlite", "--db-path", "./data.db"], "transport": "stdio"},
            "better-icons": {"command": "npx", "args": ["better-icons"], "transport": "stdio"},
        }
        for rec in mcps_to_add:
            if rec.name in mcp_config:
                actions.append(f"✓ MCP '{rec.name}' already configured")
            elif rec.name in known_mcp_configs:
                mcp_config[rec.name] = known_mcp_configs[rec.name]
                mcp_changed = True
                actions.append(f"✓ Added MCP '{rec.name}' to config")
            else:
                actions.append(f"⚠ Unknown MCP '{rec.name}' — add manually to mcp.json")

        if mcp_changed:
            mcp_config_path.write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
            actions.append(f"Updated {mcp_config_path}")

        # Install hooks (add to settings.json)
        settings_path = self.project_claude_dir / "settings.json"
        settings: dict[str, Any] = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        hooks_changed = False
        for rec in hooks_to_add:
            summary = rec.summary
            # Parse hook event and command from summary
            match = re.match(r"(hook:\s*)?(\w+):\s*(.*)", summary)
            if match:
                event = match.group(2)
                command = match.group(3).strip()
                if "hooks" not in settings:
                    settings["hooks"] = {}
                if event not in settings["hooks"]:
                    settings["hooks"][event] = []
                if command not in settings["hooks"][event]:
                    settings["hooks"][event].append(command)
                    hooks_changed = True
                    actions.append(f"✓ Added {event} hook: {command[:60]}")

        if hooks_changed:
            settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
            actions.append(f"Updated {settings_path}")

        # Install rules (write .claude/rules/{component}.md)
        rules_dir = self.project_claude_dir / "rules"
        for rec in rules_to_add:
            rule_text = rec.summary.replace("Rule: ", "", 1)
            # Determine which component this rule belongs to
            component_name = rec.category
            rule_file = rules_dir / f"{component_name}.md"
            rules_dir.mkdir(parents=True, exist_ok=True)
            existing = ""
            if rule_file.exists():
                existing = rule_file.read_text(encoding="utf-8")
            if rule_text not in existing:
                with open(rule_file, "a", encoding="utf-8") as f:
                    f.write(f"- {rule_text}\n")
                actions.append(f"✓ Added rule to {rule_file}")

        return actions


# ─── CLI ────────────────────────────────────────────────────────────────────


def cmd_scan(args: list[str]) -> None:
    """Scan project and output detected stack."""
    project_dir = _parse_dir_arg(args)
    scanner = ProjectScanner(project_dir)
    result = scanner.scan()
    output: dict[str, Any] = {"project": result.project_name, "directory": result.project_dir}
    components: list[dict[str, Any]] = []
    for c in result.components:
        components.append({
            "category": c.category,
            "name": c.name,
            "confidence": c.confidence,
            "detail": c.detail,
            "files": c.files,
        })
    output["components"] = components
    print(json.dumps(output, indent=2))


def cmd_recommend(args: list[str]) -> None:
    """Scan project and generate recommendations."""
    project_dir = _parse_dir_arg(args)
    scanner = ProjectScanner(project_dir)
    scan = scanner.scan()
    recommender = Recommender()
    recommendations = recommender.recommend(scan)

    print(f"\n{'='*60}")
    print(f"  Stack Optimizer — {scan.project_name}")
    print(f"{'='*60}")

    if not scan.components:
        print("\n  No stack components detected.")
        print("  Run from a project directory with package.json, pyproject.toml, etc.\n")
        sys.exit(1)

    print(f"\n  Detected Components:")
    for c in sorted(scan.components, key=lambda x: (-x.confidence, x.category)):
        icon = {"language": "[L]", "framework": "[F]", "database": "[D]", "testing": "[T]", "css": "[C]", "ci_cd": "[CI]", "mobile": "[M]", "infra": "[I]", "deploy": "[P]"}.get(c.category, "[*]")
        print(f"    {icon} {c.category}: {c.name} ({(c.confidence*100):.0f}%)")

    if recommendations:
        print(f"\n  Recommendations ({len(recommendations)} total):")
        by_kind: dict[str, list[Recommendation]] = {}
        for r in recommendations:
            by_kind.setdefault(r.kind, []).append(r)

        for kind, items in sorted(by_kind.items()):
            kind_icon = {"skill": "[S]", "mcp": "[M]", "hook": "[H]", "rule": "[R]", "setting": "[C]"}.get(kind, "[*]")
            print(f"\n    {kind_icon} {kind.upper()} ({len(items)}):")
            for item in items[:10]:  # Show top 10 per kind
                print(f"      * {item.summary[:90]}")
            if len(items) > 10:
                print(f"      ... and {len(items) - 10} more")

        print(f"\n  To install: python optimize.py install <recommendations.json>")
        print(f"  Or: python optimize.py install --from-scan (in development)\n")
    else:
        print(f"\n  No specific recommendations for this stack.")
        print("  The knowledge base can be extended in recommendations.json\n")


def cmd_install(args: list[str]) -> None:
    """Install recommendations from a JSON file."""
    if not args or args[0].startswith("--"):
        print("Usage: python optimize.py install <recommendations.json> [--dir <project>] [--dry-run]")
        sys.exit(1)

    rec_file = Path(args[0])
    if not rec_file.exists():
        print(f"Error: {rec_file} not found")
        sys.exit(1)

    dry_run = "--dry-run" in args
    project_dir = _parse_dir_arg(args)

    try:
        data = json.loads(rec_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error parsing {rec_file}: {e}")
        sys.exit(1)

    recommendations = [Recommendation(**r) for r in data]
    installer = Installer(project_dir)
    actions = installer.install(recommendations, dry_run=dry_run)

    print(f"\n{'='*60}")
    print(f"  {'[DRY RUN] ' if dry_run else ''}Install Results")
    print(f"{'='*60}")
    for action in actions:
        print(f"  {action}")
    print(f"\n  {len(actions)} actions {'simulated' if dry_run else 'taken'}\n")


def cmd_report(args: list[str]) -> None:
    """Show current Claude Code tool installation state."""
    project_dir = _parse_dir_arg(args)
    claude_dir = Path.home() / ".claude"
    project_claude = Path(project_dir) / ".claude"

    print(f"\n{'='*60}")
    print(f"  Claude Code Configuration Report")
    print(f"{'='*60}")

    # Skills
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        skills = sorted(d.name for d in skills_dir.iterdir() if d.is_dir())
        print(f"\n  [SKILLS] Installed Skills ({len(skills)}):")
        for s in skills:
            print(f"    - {s}")
    else:
        print(f"\n  [SKILLS] No skills directory found")

    # MCP servers
    mcp_config = claude_dir / "mcp.json"
    if mcp_config.exists():
        try:
            mcps = json.loads(mcp_config.read_text(encoding="utf-8"))
            print(f"\n  [MCP] MCP Servers ({len(mcps)}):")
            for name in mcps:
                print(f"    - {name}")
        except (json.JSONDecodeError, OSError):
            print(f"\n  [MCP] Could not parse mcp.json")
    else:
        print(f"\n  [MCP] No mcp.json found")

    # Hooks
    for settings_path in [project_claude / "settings.json", claude_dir / "settings.json"]:
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
                hooks = settings.get("hooks", {})
                if hooks:
                    total = 0
                    for event, entries in hooks.items():
                        for entry in entries:
                            if isinstance(entry, dict) and "hooks" in entry:
                                total += len(entry["hooks"])
                            else:
                                total += 1
                    print(f"\n  [HOOKS] Hooks ({total} total):")
                    for event, entries in hooks.items():
                        for entry in entries:
                            if isinstance(entry, dict) and "hooks" in entry:
                                for h in entry["hooks"]:
                                    cmd = h.get("command", str(h)[:60])
                                    args = h.get("args", [])
                                    suffix = f" {args[0][:40]}..." if args and isinstance(args[0], str) else ""
                                    print(f"    - {event}: {cmd[:40]}{suffix}")
                            elif isinstance(entry, str):
                                print(f"    - {event}: {entry[:60]}")
            except (json.JSONDecodeError, OSError):
                pass

    # Rules
    rules_dir = project_claude / "rules"
    if rules_dir.exists():
        rules = sorted(rules_dir.glob("*.md"))
        if rules:
            print(f"\n  [RULES] Rules ({len(rules)} files):")
            for r in rules:
                print(f"    - {r.name}")

    print(f"\n  [DIR] Project: {Path(project_dir).resolve()}")
    print(f"\n")


def cmd_list_sources() -> None:
    """List top sources for skill/MCP discovery."""
    print(f"""
  [SOURCES] Top Sources for Claude Code Tools

  Skills:
    - github.com/anthropics/skills -- Official Anthropic skills (150k+ stars)
    - github.com/mattpocock/skills -- "Skills for Real Engineers"
    - SkillKit marketplace (agenstskills.com) -- 400,000+ skills

  MCP Servers:
    - github.com/punkpeye/awesome-mcp-servers -- Curated list of 1000+
    - github.com/modelcontextprotocol/servers -- Official MCP servers
    - MCP Registry (github.com/mcp) -- Anthropic's MCP marketplace

  Hooks:
    - docs.claude.com/en/hooks-guide -- Official hooks documentation
    - github.com/yurukusa/claude-code-hooks -- Community hook collection

  All-in-One:
    - github.com/rohitg00/awesome-claude-code-toolkit -- 176+ plugins, 135 agents, 20 hooks
    - github.com/FlorianBruniaux/claude-code-ultimate-guide -- Complete guide
    """.strip())


# ─── Utilities ──────────────────────────────────────────────────────────────


def _parse_dir_arg(args: list[str]) -> str:
    for i, a in enumerate(args):
        if a == "--dir" and i + 1 < len(args):
            return args[i + 1]
    return os.getcwd()


def print_usage() -> None:
    print(__doc__.strip())


# ─── Entry Point ────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        sys.exit(0 if len(sys.argv) < 2 else 0)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "scan": cmd_scan,
        "recommend": cmd_recommend,
        "install": cmd_install,
        "report": cmd_report,
        "list-sources": lambda _: cmd_list_sources(),
    }

    fn = commands.get(command)
    if fn is None:
        print(f"Unknown command: {command}\n", file=sys.stderr)
        print_usage()
        sys.exit(1)

    try:
        fn(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
