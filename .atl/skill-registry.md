# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Code review for Reflex applications | reflex-code-review-expert | /var/home/yhoxr/.config/opencode/skills/reflex-code-review-expert/SKILL.md |
| "judgment day", "review adversarial", "dual review", "juzgar" | judgment-day | /var/home/yhoxr/.config/opencode/skills/judgment-day/SKILL.md |
| Creating a pull request, opening a PR | branch-pr | /var/home/yhoxr/.config/opencode/skills/branch-pr/SKILL.md |
| Creating GitHub issue, reporting bug, requesting feature | issue-creation | /var/home/yhoxr/.config/opencode/skills/issue-creation/SKILL.md |
| Writing Go tests, using teatest | go-testing | /var/home/yhoxr/.config/opencode/skills/go-testing/SKILL.md |
| Creating new skill, adding agent instructions | skill-creator | /var/home/yhoxr/.config/opencode/skills/skill-creator/SKILL.md |
| Reflex development (creating, modifying, debugging Reflex apps) | reflex-dev | /var/home/yhoxr/.agents/skills/reflex-dev/SKILL.md |
| Python development tasks | python-pro | /var/home/yhoxr/.agents/skills/python-pro/SKILL.md |
| Creating PRs, writing PR descriptions, using gh CLI | github-pr | /var/home/yhoxr/.agents/skills/github-pr/SKILL.md |
| Writing Python tests | pytest | /var/home/yhoxr/.agents/skills/pytest/SKILL.md |
| "how do I do X", "find a skill for X" | find-skills | /var/home/yhoxr/.agents/skills/find-skills/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### reflex-code-review-expert
- MUST load reflex-dev skill before providing detailed technical feedback
- MUST verify Reflex version in use (check requirements or imports) before making version-specific recommendations
- MUST NOT make suggestions that require breaking changes without clearly indicating the impact
- MUST provide specific code snippets in recommendations, never vague guidance
- MUST check workspace for existing Reflex patterns before suggesting new approaches
- MUST cite specific Reflex documentation or reliable sources for controversial claims
- MUST prioritize performance, security, and maintainability in that order

### reflex-dev
- State vars MUST be JSON-serializable (int, str, list, dict, bool, float) — only event handlers can modify state
- Use @rx.var for computed/derived values, @rx.event decorator for explicit event handlers
- Component props: size uses numeric values 1-9 ONLY (not "sm", "md", "lg")
- Use rx.cond() and rx.match() for conditional rendering — NOT Python if/else in component functions
- Variables with _ prefix are backend-only (not synced to frontend)
- Static files go in assets/ (NOT .web/_static — path changed to .web/build/client in 0.8.x)
- Use async def for I/O-bound event handlers to avoid blocking other users

### python-pro
- Type hints for ALL function signatures and class attributes
- PEP 8 compliance with black formatting (max 88 chars)
- Comprehensive docstrings (Google style)
- Test coverage >90% with pytest
- Custom exceptions for error handling
- Use async/await for I/O-bound operations

### pytest
- Use @pytest.fixture for reusable test data with proper teardown (yield)
- Use unittest.mock.patch for mocking external dependencies
- Use @pytest.mark.parametrize for multiple test cases
- Place shared fixtures in conftest.py at the tests/ root
- Use @pytest.mark.asyncio for async test functions

### github-pr
- PR title MUST follow conventional commits: `type(scope): description`
- PR body MUST include "Closes #N" to link issue
- Structure: ## Summary (1-3 bullets), ## Changes, ## Testing
- Keep commits atomic — one logical change per commit
- Use gh pr create with --title and --body flags

### branch-pr
- EVERY PR MUST link an approved issue (status:approved label)
- EVERY PR MUST have exactly ONE type:* label
- Branch name regex: `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`
- Automated checks must pass before merge is possible
- Use conventional commits: `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9\._-]+\))?!?: .+`

### issue-creation
- Blank issues are disabled — MUST use bug_report.yml or feature_request.yml template
- Every issue gets status:needs-review automatically on creation
- A maintainer MUST add status:approved before any PR can be opened
- Questions go to Discussions, NOT issues

### go-testing
- Use table-driven tests for multiple test cases with struct definitions
- Test Model state transitions directly via m.Update() — no need for teatest for simple tests
- Use teatest.NewTestModel() for full TUI integration tests
- Use golden file testing for visual output comparison (testdata/ directory)
- Mock os/exec dependencies with interfaces for testability

### judgment-day
- Launch TWO sub-agents via delegate (async, parallel) — NEVER sequential
- Both judges receive IDENTICAL prompt (no cross-contamination)
- Orchestrator synthesizes verdict after both complete
- After 2 fix iterations, ASK user before continuing — never escalate automatically
- Classify warnings: "real" (normal user can trigger) vs "theoretical" (requires contrived scenario)
- Theoretical warnings reported as INFO, NOT fixed

### skill-creator
- Skill structure: skills/{skill-name}/ with SKILL.md (required), assets/ (optional), references/ (optional)
- Frontmatter: name, description (MUST include trigger keywords), license (Apache-2.0), metadata
- Critical patterns section is most important — what AI MUST know
- Include Commands section with copy-paste commands

### find-skills
- Check skills.sh leaderboard first for popular, battle-tested skills
- Verify quality: prefer 1K+ installs, trust official sources (vercel-labs, anthropics)
- Present: skill name, install count, source, install command, link to learn more
- If no skill found: offer to help directly, suggest creating own skill

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | /var/home/yhoxr/Documentos/kakumi-app/AGENTS.md | Index — project guidelines for Kakumi App (Reflex-based Karate-Do tournament app) |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.

---

## Kakumi App Specific Standards (from AGENTS.md)

- **Python-First Policy**: 100% Python — no .js, .ts, .jsx, .tsx, .html, .css files
- **UI Framework**: Use reflex components exclusively (rx.Component, rx.State)
- **ORM**: Use sqlmodel for all database interactions
- **Database**: SQLite with SQLModel + Alembic for migrations
- **State Management**: rx.State classes with event handlers
- **WKF Compliance**: All scoring/tie-breaking/draw logic must follow WKF 2026 regulations in /docs
- **Naming**: Classes=PascalCase, functions/variables=snake_case, constants=UPPER_CASE
- **Line Length**: Maximum 88 characters (Black default)
- **File Organization**: kakumi_app/{components/, models/, pages/, styles/}
- **Testing**: Use reflex's session context for database isolation, pytest naming conventions
- **Migrations**: Keep small and focused, test on copy of production data, include downgrade paths