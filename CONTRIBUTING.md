# Contributing to HAchilles

Thank you for your interest in contributing to HAchilles! 🦾

HAchilles is the open standard for measuring AI agent harness quality. Every contribution — bug reports, feature requests, documentation improvements, and code — helps the entire AI engineering community build more reliable, measurable, and predictable agents.

> **한국어 안내** | 기여해 주셔서 감사합니다. HAchilles는 글로벌 오픈소스 프로젝트이므로 이슈·PR은 영어를 기본으로 합니다. 한국어 질문과 토론은 [GitHub Discussions](https://github.com/suhopark1/hachilles/discussions)에서 환영합니다.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Branch Strategy & Protection Rules](#branch-strategy--protection-rules)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Using Badges Effectively](#using-badges-effectively)
- [Issue Templates](#issue-templates)
- [Diagnostic Item Contributions](#diagnostic-item-contributions)
- [License Agreement](#license-agreement)

---

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to uphold its standards. Violations may be reported to **suhopark1@gmail.com**.

---

## Ways to Contribute

### 🐛 Report Bugs
- Search [existing issues](https://github.com/suhopark1/hachilles/issues) first
- Use the **Bug Report** template — it guides you through the required information
- Include: OS, Python version, `hachilles --version` output, minimal reproduction steps

### ✨ Request Features
- Check the [Roadmap](README.md#roadmap) to avoid duplicates
- Use the **Feature Request** template
- Explain *which harness quality problem* the feature solves (CE / AC / EM context)

### 📖 Improve Documentation
- Fix typos, clarify explanations, add real-world examples
- Translate English docs summaries for non-English community members
- Add case studies or usage examples

### 🔧 Contribute Code
- Fix bugs, implement roadmap features, improve performance
- All PRs must pass CI (lint + license-check + test + self-audit ≥ 90 pts)
- New features must include tests

---

## Development Setup

**Prerequisites:** Python 3.10+, Node.js 20+ (for web UI), Git

```bash
# 1. Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/hachilles.git
cd hachilles

# 2. Add the upstream remote
git remote add upstream https://github.com/suhopark1/hachilles.git

# 3. Install all development dependencies
pip install -e ".[dev,web]"

# 4. Install pre-commit hooks (enforces lint + format on every commit)
pre-commit install

# 5. Verify your setup — all must pass
make lint          # ruff + mypy
make test          # 611 tests
hachilles scan .   # must be S-Grade (≥ 90 pts)
```

---

## Branch Strategy & Protection Rules

### Branch Model

```
main ─────────────────────────────────────────────── production
  └── develop ──────────────────────────────────────── integration
        ├── feat/github-actions-integration
        ├── fix/context-drift-detection-edge-case
        └── docs/update-architecture-diagram
```

| Branch | Purpose | Direct Push | Who Can Merge |
|--------|---------|-------------|---------------|
| `main` | Production releases — every commit is a release | ❌ Forbidden | Maintainer only, after full CI |
| `develop` | Integration branch for completed features | ❌ Forbidden | Maintainer after review |
| `feat/*` | New features | ✅ Author | Via PR to `develop` |
| `fix/*` | Bug fixes | ✅ Author | Via PR to `develop` or `main` (critical) |
| `docs/*` | Documentation only | ✅ Author | Via PR to `main` |
| `refactor/*` | Refactoring (no behavior change) | ✅ Author | Via PR to `develop` |
| `test/*` | Test additions / improvements | ✅ Author | Via PR to `develop` |

### Branch Naming Convention

```bash
feat/brief-lowercase-description          # ✅ correct
fix/ce-01-false-positive-on-empty-dir     # ✅ correct
docs/add-typescript-analysis-section      # ✅ correct
Feature/My New Feature                    # ❌ wrong (capitals, spaces)
my-change                                 # ❌ wrong (no type prefix)
```

### Branch Protection Rules (GitHub Settings)

The `main` and `develop` branches are protected. Maintainers configure the following in **Settings → Branches → Branch protection rules**:

**For `main`:**
- ✅ Require a pull request before merging
- ✅ Require approvals: **1 (minimum)**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging:
  - `lint` — ruff check + format
  - `license-check` — Apache 2.0 headers
  - `test (3.10)`, `test (3.11)`, `test (3.12)` — full test matrix
  - `typecheck` — mypy strict
  - `hachilles-self-audit` — S-Grade (≥ 90 pts)
  - `api-smoke-test` — FastAPI routes verified
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings
- ✅ Restrict who can push to matching branches: **maintainers only**

**For `develop`:**
- ✅ Require a pull request before merging
- ✅ Require status checks: `lint`, `license-check`, `test (3.11)`, `hachilles-self-audit`
- ✅ Require branches to be up to date

### Tagging & Releases

Only maintainers create release tags. Tags follow Semantic Versioning:

```bash
git tag -a v3.1.0 -m "Release v3.1.0: GitHub Actions integration"
git push origin v3.1.0
# → Triggers CI publish job → automatic PyPI upload
```

---

## Submitting a Pull Request

### Step-by-Step

```bash
# 1. Sync with upstream
git fetch upstream
git checkout develop
git merge upstream/develop

# 2. Create your branch
git checkout -b feat/your-feature-name

# 3. Make changes, commit often with clear messages
git commit -m "feat(auditors): add CE-06 tool description quality scoring"

# 4. Run checks before pushing
make lint          # Must pass — no ruff errors, no mypy errors
make test          # All 611+ tests must pass
hachilles scan .   # Score must be ≥ 90 (S-Grade)

# 5. Push and open PR
git push origin feat/your-feature-name
# → GitHub will show a "Compare & Pull Request" button
```

### PR Checklist

Before opening your PR, verify:

- [ ] `make lint` passes (zero errors)
- [ ] `make test` passes (all tests green)
- [ ] `hachilles scan .` score ≥ 90 / S-Grade
- [ ] Apache 2.0 license header present in any new `.py` files
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New public functions have docstrings
- [ ] Tests cover the changed behavior (new feature) or prove the bug is fixed (bug fix)
- [ ] No new `# type: ignore` without an `[EXCEPTION]` comment explaining why

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

**Types:** `feat` · `fix` · `docs` · `refactor` · `test` · `ci` · `chore`
**Scopes:** `cli` · `scanner` · `auditors` · `score` · `api` · `web` · `plugins` · `docs`

Examples:
```
feat(auditors): add AC-06 human-in-the-loop checkpoint detection
fix(scanner): handle symlinks in project root correctly
docs(readme): add TypeScript project usage example
test(score): add boundary tests for 0-point and 100-point edge cases
ci: add Python 3.13 to test matrix
```

---

## Coding Standards

HAchilles applies its own diagnostic framework to itself. Every contribution must respect the 3-pillar framework.

### Style & Quality Tools

| Tool | Purpose | Run with |
|------|---------|---------|
| `ruff check` | Lint (E/W/F/I/N/UP rules) | `make lint` |
| `ruff format` | Auto-formatting | `pre-commit` (automatic) |
| `mypy --strict` | Type checking | `make lint` |

```bash
# Auto-fix formatting issues
ruff format src/ tests/

# Fix auto-fixable lint issues
ruff check --fix src/ tests/

# Check types
mypy src/hachilles/ --ignore-missing-imports
```

### Architecture Rules (CE/AC enforcement)

HAchilles enforces a strict **9-layer unidirectional dependency**:

```
models ← scanner ← auditors ← score ← prescriptions ← report ← cli/api
```

**This means:**
- `models/` imports nothing from `hachilles.*`
- `scanner/` may import from `models/` only
- `auditors/` may import from `models/` and `scanner/` only
- `cli.py` and `api/` are the top-level consumers — they import everything but are imported by nothing

**Violation = CI failure.** Pre-commit hooks will catch this before you push.

### License Header (Apache 2.0)

Every new `.py` file in `src/hachilles/` must start with:

```python
# Copyright 2026 Park Sung Hoon (박성훈) <suhopark1@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

The CI `license-check` job enforces this — missing headers will fail the build.

---

## Testing Requirements

### Test Suite Overview (611 tests)

| Category | Count | File Pattern | Description |
|----------|-------|--------------|-------------|
| Unit Tests (UT) | ~94 | `test_*.py` | Isolated function/class tests |
| Contract Tests (CT) | ~65 | `auditors/contract.py` | Interface contract validation |
| Boundary Value Analysis (BVA) | ~39 | `intensive/test_type2_boundary.py` | Edge cases and value limits |
| Property-Based Tests (PBT) | ~1 | `intensive/test_type1_property.py` | Hypothesis-driven invariants |
| Mutation/Adversarial (MT/AT) | ~75 | `intensive/test_type_a_mutation.py` | Robustness under mutation |
| Integration Tests (IT) | ~108 | `test_integration_*.py` | Cross-component interactions |
| Architecture Tests (ARCH) | ~12 | `intensive/test_type_e_architecture.py` | Dependency direction enforcement |
| Regression + Other | ~217 | Various | Phase-specific and regression tests |

### Requirements Per Contribution Type

| Contribution Type | Required Tests |
|------------------|---------------|
| **Bug fix** | Regression test that fails before the fix, passes after |
| **New feature** | Happy path + ≥ 2 edge cases + error case |
| **New auditor item** | Contract test in `tests/auditors/contract.py` |
| **Score weight change** | Before/after snapshot tests + benchmark comparison |
| **API change** | Integration test in `tests/test_phase3_api.py` |

### Running Tests

```bash
pytest tests/ -v                        # Full suite
pytest tests/ -k "test_context"         # Filter by name
pytest tests/auditors/ -v               # Auditor tests only
pytest --cov=src/hachilles --cov-report=html  # With coverage report
```

---

## Using Badges Effectively

HAchilles provides status badges for use in your project's README after achieving a grade:

### Official HAchilles Score Badge (Static)

```markdown
[![HAchilles Score](https://img.shields.io/badge/HAchilles-84%20pts%20A--Grade-blue)](https://github.com/suhopark1/hachilles)
```

### Self-Hosted Dynamic Badge (After v3.1)

Once HAchilles Cloud launches (v3.1), dynamic badges will be available:

```markdown
[![HAchilles Score](https://badge.hachilles.dev/YOUR_REPO)](https://hachilles.dev/YOUR_REPO)
```

### Recommended Badge Stack for Your Project

```markdown
[![HAchilles Score](https://img.shields.io/badge/HAchilles-XX%20pts%20S--Grade-brightgreen)](STANDARDS.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/ci.yml/badge.svg)](...)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
```

---

## Issue Templates

HAchilles provides two structured issue templates to keep reports actionable:

### Bug Report Template

Located at `.github/ISSUE_TEMPLATE/bug_report.md`

Key sections:
- **Bug Description** — one paragraph, specific and factual
- **Steps to Reproduce** — minimal, numbered, includes the exact `hachilles` command
- **Expected vs Actual Behavior** — clear contrast
- **Environment** — HAchilles version, Python version, OS, installation method
- **Additional Context** — error output, screenshots if applicable

### Feature Request Template

Located at `.github/ISSUE_TEMPLATE/feature_request.md`

Key sections:
- **Problem Statement** — which harness quality problem this solves
- **Proposed Solution** — what you want to happen
- **Pillar Checkbox** — CE / AC / EM / cross-cutting
- **Use Case** — concrete scenario description

### Tips for Good Issues

✅ One issue = one problem or one feature request
✅ Search existing issues before opening a new one
✅ Include the output of `hachilles scan . --json` for diagnostic-related bugs
✅ For feature requests, reference the failure pattern you're trying to prevent
❌ Don't include API keys, passwords, or proprietary code in issues

---

## Diagnostic Item Contributions

Adding new CE/AC/EM diagnostic items is the most impactful contribution type — it directly expands what HAchilles can detect.

### Process

1. **Discuss first** — open a Feature Request issue with `[New Diagnostic Item]` in the title
2. **Define the item** in `STANDARDS.md`:
   - Item code (e.g., `CE-06`, `AC-06`, `EM-06`)
   - What it measures, why it matters
   - Pass/fail criteria (concrete, automatable)
   - Example of passing and failing code
3. **Implement** in the appropriate auditor:
   - `src/hachilles/auditors/context_auditor.py` — CE items
   - `src/hachilles/auditors/constraint_auditor.py` — AC items
   - `src/hachilles/auditors/entropy_auditor.py` — EM items
4. **Add prescription** in `src/hachilles/prescriptions/`
5. **Write contract tests** in `tests/auditors/contract.py`
6. **Write an ADR** (Architecture Decision Record) in `docs/decisions/`
7. **Update CHANGELOG.md** and `README.md` (feature matrix)

### Score Weight Policy

Changing existing score weights requires:
- Empirical justification (real-world project data preferred)
- Discussion in a GitHub Issue before implementation (label: `score-policy`)
- Migration guide in `CHANGELOG.md` (with before/after examples)

---

## License Agreement

By submitting a contribution to HAchilles, you agree that:

1. Your contribution is your original work or you have the right to submit it
2. Your contribution will be licensed under the **Apache License 2.0**
3. The project maintainer (Park Sung Hoon) retains the right to use contributions in commercial offerings built on top of HAchilles (open-core model)
4. You retain copyright of your contribution

No formal CLA (Contributor License Agreement) signature is required — submitting a PR constitutes agreement to these terms.

---

*Thank you for helping make AI agent development more reliable, measurable, and predictable.*

*— Park Sung Hoon (박성훈), HAchilles maintainer*
