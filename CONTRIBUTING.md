# Contributing to ChantePaFo

First off, thank you for taking the time to contribute! 🎵 ChantePaFo is a community project built on the idea that music parties should be fun, inclusive, and a little ridiculous. Every contribution — code, bug report, feature idea, design feedback — makes it better.

This guide covers **how to contribute** and **what we expect** from everyone in the community.

---

## Table of contents

1. [Code of Conduct](#code-of-conduct)
2. [How can I contribute?](#how-can-i-contribute)
3. [Development setup](#development-setup)
4. [Branching strategy](#branching-strategy)
5. [Commit conventions](#commit-conventions)
6. [Pull request process](#pull-request-process)
7. [Code quality standards](#code-quality-standards)
8. [Reporting bugs](#reporting-bugs)
9. [Suggesting features](#suggesting-features)

---

## Code of Conduct

### Our Pledge

ChantePaFo is a space for **everyone** to have fun, regardless of who they are. We pledge to make participation in our community a **harassment-free experience** for everyone, regardless of:

- Age
- Body size, disability, visible or invisible
- Ethnicity, race, nationality, or cultural background
- Gender identity or expression
- Level of experience (beginner, expert, or anything in between)
- Education
- Socio-economic status
- Sexual orientation
- Religion (or lack thereof)
- Personal appearance

### Our standards

**Examples of behavior that contributes to a positive environment:**

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members
- Helping newcomers feel welcome
- Celebrating silly karaoke performances (it's kind of the whole point)

**Examples of unacceptable behavior:**

- **Racism, sexism, homophobia, transphobia, ableism**, or any form of discrimination
- The use of sexualized language or imagery, and unwelcome sexual attention
- Trolling, insulting or derogatory comments, personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Gatekeeping ("you're not a *real* music fan because...")
- Mocking someone's musical taste, voice, or ability — ChantePaFo is about having fun, not judging
- Sharing copyrighted music in ways that violate artists' rights
- Any conduct which could reasonably be considered inappropriate in a friendly gathering

### Our responsibilities

Project maintainers are responsible for clarifying and enforcing our standards. They have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned with this Code of Conduct.

### Scope

This Code of Conduct applies within all project spaces (GitHub issues, pull requests, discussions, Discord, etc.) and in public spaces when an individual is representing the project.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated promptly and fairly. Maintainers are obligated to respect the privacy and security of the reporter.

Depending on the severity, consequences may include:
- A private warning
- A public warning
- Temporary ban from the project
- Permanent ban from the project

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.1.

---

## How can I contribute?

There are many ways to contribute, not all of them involve writing code:

- 🐛 **Report bugs** — see [Reporting bugs](#reporting-bugs)
- 💡 **Suggest features** — see [Suggesting features](#suggesting-features)
- 📖 **Improve documentation** — fix typos, clarify confusing sections, translate
- 🎨 **Design feedback** — UX suggestions, accessibility improvements
- 🧪 **Write tests** — coverage is always appreciated
- 💻 **Fix bugs or implement features** — pick an issue labeled `good first issue` if you're new
- 🎵 **Share playlists** — suggest genres or era selections for the game
- 🌍 **Translations** — help us make ChantePaFo available in more languages

---

## Development setup

See [DEVELOPMENT.md](DEVELOPMENT.md) for a complete development guide.

**TL;DR:**

```bash
git clone https://github.com/<your-user>/ChantePaFo.git
cd ChantePaFo
docker compose up -d
cd backend && uv sync --all-extras
cd ../frontend && npm install
```

Then launch backend + frontend in separate terminals and open `http://localhost:5173`.

---

## Branching strategy

```
feature/my-feature ──push──→ dev ──PR──→ main
                               │
                               └── deploys to staging
                                            │
                                            └── deploys to production
```

- **`feature/<name>`** — working branches, forked from `dev`
- **`dev`** — integration branch, auto-deploys to staging
- **`main`** — production branch, only accepts PRs from `dev`

**Never push directly to `main` or `dev`.** Always use pull requests.

### Typical workflow

```bash
# 1. Start from up-to-date dev
git checkout dev
git pull origin dev

# 2. Create a feature branch
git checkout -b feature/my-cool-feature

# 3. Make changes, write tests, commit
git add .
git commit -m "feat: add my cool feature"

# 4. Push and open a PR
git push -u origin feature/my-cool-feature
gh pr create --base dev --title "feat: add my cool feature"
```

---

## Commit conventions

We use **[Conventional Commits](https://www.conventionalcommits.org/)**. This is enforced by `commitlint` as a pre-commit hook — non-conforming commits will be rejected.

### Format

```
<type>: <description in lowercase, imperative, no period>

[optional body]

[optional footer]
```

### Types

| Type | Version bump | Use case | Example |
|------|-------------|----------|---------|
| `feat:` | **minor** (0.X.0) | New feature | `feat: add progressive karaoke mode` |
| `fix:` | **patch** (0.0.X) | Bug fix | `fix: fuzzy matching on accented characters` |
| `feat!:` | **major** (X.0.0) | Breaking change | `feat!: redesign scoring API` |
| `docs:` | — | Documentation only | `docs: update API endpoints` |
| `style:` | — | Formatting only | `style: reformat with ruff` |
| `refactor:` | — | Refactoring without feature change | `refactor: extract scoring module` |
| `test:` | — | Adding/updating tests | `test: add fuzzy edge cases` |
| `chore:` | — | Build, CI, deps, tooling | `chore: update dependencies` |
| `perf:` | — | Performance improvement | `perf: batch WebSocket events` |

### Breaking changes

Add `!` after the type or `BREAKING CHANGE:` in the footer:

```
feat!: redesign room system

BREAKING CHANGE: the /rooms API format has changed.
Existing clients will need to migrate.
```

### Rules

- **Lowercase**: `feat: add X`, not `feat: Add X`
- **Imperative**: `add`, not `added` or `adds`
- **No trailing period**
- **Concise**: single line, < 100 characters for the subject
- **Detailed body** if needed (optional, separated by a blank line)

---

## Pull request process

1. **Ensure CI passes** — lint, tests, and build must be green
2. **Write a clear PR description**:
   - What does this change do?
   - Why is it needed?
   - How to test it?
   - Screenshots/recordings if it's a visual change
3. **Link related issues** — "Closes #42" or "Fixes #42"
4. **Request review** — at least one maintainer must approve
5. **Respond to feedback** — discussions should be respectful and constructive
6. **Squash and merge** — keep the history clean; the merge commit message should still follow Conventional Commits

### What makes a good PR?

- ✅ Focused on a single change (not a mix of unrelated things)
- ✅ Includes tests (for backend logic and frontend composables)
- ✅ Documentation updated if behavior changes
- ✅ No hardcoded values — use design tokens for colors/sizes
- ✅ Passes SonarQube quality gate (no critical code smells, no vulnerabilities)
- ✅ Coverage remains above 70%

---

## Code quality standards

### Backend (Python)

- **Formatting**: `ruff format` (enforced)
- **Linting**: `ruff check` (enforced)
- **Type checking**: `mypy` strict mode
- **No docstrings** unless the logic is non-obvious
- **Test coverage**: minimum 70%

### Frontend (TypeScript / Vue)

- **Formatting**: `prettier` (enforced)
- **Linting**: `eslint` (enforced)
- **Type checking**: `vue-tsc` strict
- **Composition API** with `<script setup lang="ts">`
- **Design tokens only** — no hardcoded colors, sizes, or fonts in components; use CSS variables from `assets/tokens.css`
- **Test coverage**: minimum 70%

### Accessibility

- Semantic HTML (`<button>` not `<div onclick>`)
- ARIA labels on icon-only buttons
- Keyboard navigation must work
- Color contrast respects WCAG AA
- Don't rely on color alone to convey information

### Tests

Before opening a PR, make sure:

```bash
# Backend
cd backend
uv run pytest tests/ -v
uv run ruff check .
uv run ruff format --check .

# Frontend
cd frontend
npm run test
npx eslint src/ --max-warnings 0
npx prettier --check "src/**/*.{ts,vue,css}"
```

---

## Reporting bugs

Before filing a bug report:

1. **Search existing issues** — someone may have reported it already
2. **Try the latest version** — the bug may already be fixed in `dev`
3. **Gather info**: browser, OS, steps to reproduce, screenshots

### Bug report template

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Screenshots/recordings**
If applicable.

**Environment**
- OS: [e.g. macOS 14, Windows 11, Android 14]
- Browser: [e.g. Chrome 120, Firefox 121, Safari 17]
- Device: [e.g. iPhone 15, Desktop]
- Room mode when it happened: [e.g. Blindtest, Karaoke]

**Additional context**
Anything else relevant.
```

---

## Suggesting features

We love feature suggestions! Before filing one:

1. **Check existing issues** — maybe someone already suggested it
2. **Check the roadmap** in [README.md](README.md) — it might be planned
3. **Think about the spirit of the project** — fun, inclusive, silly > serious, competitive, gatekeeping

### Feature request template

```markdown
**Is your feature request related to a problem?**
A clear description. E.g. "It's frustrating when..."

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions you thought about.

**Additional context**
Mockups, references to similar games, why it fits ChantePaFo's vibe.
```

---

## License

By contributing to ChantePaFo, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

## Questions?

If anything is unclear, open a discussion on GitHub or reach out to the maintainers. We're happy to help.

**Now go chante pas faux! 🎵**
