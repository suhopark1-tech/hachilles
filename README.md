# HAchilles 🦾

> **The definitive standard for AI agent harness quality measurement.**

[![CI](https://github.com/suhopark1/hachilles/actions/workflows/ci.yml/badge.svg)](https://github.com/suhopark1/hachilles/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/hachilles.svg)](https://pypi.org/project/hachilles/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hachilles.svg)](https://pypi.org/project/hachilles/)
[![HAchilles Score](https://img.shields.io/badge/HAchilles-100%20pts%20%E2%80%93%20S--Grade-brightgreen)](STANDARDS.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**0–100 quantitative diagnostics across 3 pillars · 15 items · 5 failure patterns**

*Official tool by the author of "Practical Harness Engineering" (실전 하네스 엔지니어링)*

> **한국어 요약** | HAchilles는 AI 에이전트 하네스 품질을 0~100점으로 정량 측정하는 오픈소스 CLI/API 도구입니다.
> CE(컨텍스트 설계)·AC(아키텍처 제약)·EM(엔트로피 관리) 3대 기둥으로 15개 항목을 진단합니다.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [3-Pillar Framework](#3-pillar-framework)
- [5 Failure Patterns](#5-failure-patterns)
- [For Harness Plugin Users](#for-harness-plugin-users)
- [Installation](#installation)
- [Usage](#usage)
- [Feature Matrix](#feature-matrix)
- [Grade Scale](#grade-scale)
- [Architecture](#architecture)
- [Docker](#docker)
- [Development](#development)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security Policy](#security-policy)
- [Community & Standards](#community--standards)
- [License](#license)

---

## Overview

HAchilles answers a question that no other tool asks:

> *"How well-engineered is the **harness** surrounding your AI agent?"*

Industry data shows only **34% of AI agent projects succeed in production**. The root cause in 80%+ of failures is not the model, not the API cost, and not the prompts in isolation — it is the **harness**: the context design, architectural constraints, and entropy management that define how reliably an AI agent operates.

HAchilles quantifies harness quality on a **0–100 scale** using a 3-pillar, 15-item diagnostic framework, with automated detection of 5 critical failure patterns.

---

## Quick Start

```bash
pip install hachilles
hachilles scan .
```

```
╭──────────────────────────────────╮
│   HAchilles Diagnostic Report    │
│   /your/project  ·  Grade: A     │
╰──────────────────────────────────╯

  Score: 84 / 100

  Context Engineering    28 / 40   ████████████░░░
  Architectural Const    31 / 35   ███████████████░
  Entropy Management     25 / 25   ████████████████

  ⚠ Failure Patterns:  Context Drift (MEDIUM)
```

> **CI gate:** Exit code 1 when score < 60 (Grade C or below).

---

## 3-Pillar Framework

| Pillar | Code | Weight | What It Measures |
|--------|------|--------|-----------------|
| Context Engineering | **CE** | 40 pts | System prompt quality, context window management, tool definitions, few-shot examples, context consistency |
| Architectural Constraint | **AC** | 35 pts | Tool access control, loop prevention, output validation layers, fallback design, human-in-the-loop checkpoints |
| Entropy Management | **EM** | 25 pts | State management complexity, dependency control, error propagation isolation, observability, version drift prevention |

Each pillar contains **5 diagnostic items** (CE-01~05, AC-01~05, EM-01~05) scored individually and aggregated.

---

## 5 Failure Patterns

HAchilles detects and measures the risk level of 5 failure patterns identified across real-world AI agent projects:

| Pattern | Severity | Pillar | Description |
|---------|----------|--------|-------------|
| **Context Drift** | 🔴 CRITICAL | CE | System prompt / context loses consistency over time due to accumulated ad-hoc changes |
| **AI Slop** | 🟠 HIGH | CE + AC | Agent produces plausible-sounding but valueless output due to underspecified tool definitions |
| **Entropy Explosion** | 🟡 MEDIUM | EM | Agent complexity grows uncontrollably — no one fully understands the system anymore |
| **Over-Engineering Trap** | 🟡 MEDIUM | AC + EM | System complexity far exceeds actual use cases, creating maintenance debt without ROI |
| **70-80 Wall** | 🟢 LOW | All | Score plateaus in the 70–80 range; further improvement requires non-linear structural investment |

---

## For Harness Plugin Users

If you built your agent team with [revfactory/harness](https://github.com/revfactory) or [harness-100](https://github.com/revfactory/harness-100), HAchilles is your natural next step.

| Tool | Role | Core Question |
|------|------|---------------|
| **Harness plugin** | **Build** agent teams | "What team structure should I create?" |
| **HAchilles** | **Measure** harness quality | "How well does the team I built actually perform?" |

They don't compete — they form a **Build → Measure → Improve** pipeline.

```bash
# After building with Harness, measure quality:
pip install hachilles
hachilles scan .
# → CE·AC·EM scores + improvement prescriptions
```

→ Full integration guide: [docs/harness-integration.md](docs/harness-integration.md)

---

## Installation

```bash
# CLI only (minimal)
pip install hachilles

# With web dashboard
pip install "hachilles[web]"

# With LLM analysis (Claude / GPT)
pip install "hachilles[web,llm]"

# Everything (dev + web + llm)
pip install "hachilles[all]"
```

**Development setup:**

```bash
git clone https://github.com/suhopark1/hachilles.git
cd hachilles
pip install -e ".[dev,web]"
pre-commit install
make test          # 611 tests must pass
hachilles scan .   # Self-audit must be S-Grade
```

---

## Usage

### CLI

```bash
# Scan current directory
hachilles scan .

# Scan a specific project
hachilles scan /path/to/your/project

# JSON output — for CI pipelines, scripts, dashboards
hachilles scan . --json

# Generate self-contained HTML report
hachilles scan . --html --out report.html

# LLM-powered over-engineering analysis (requires API key)
hachilles scan . --llm

# Save to history database & track trends over time
hachilles scan . --save-history
hachilles history .

# Auto-generate AGENTS.md from scan results
hachilles generate-agents .
```

### Web Dashboard

```bash
hachilles serve              # http://localhost:8000
hachilles serve --port 9000  # custom port
hachilles serve --reload     # dev mode with auto-reload
```

Open `http://localhost:8000` — React SPA with scan history, trend charts, and score breakdown.

### REST API

```bash
# Scan via API
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/project"}'

# Health check
curl http://localhost:8000/api/health
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check + version |
| `POST` | `/api/v1/scan` | Scan a project, return full ScanResult |
| `GET`  | `/api/v1/history` | Retrieve scan history (SQLite) |
| `GET`  | `/api/v1/compare` | Compare two scan results |
| `POST` | `/api/v1/generate-agents` | Generate AGENTS.md |

---

## Feature Matrix

| Feature | Description | Version |
|---------|-------------|---------|
| **CLI scan** | `hachilles scan <path>` — rich terminal output | v1.0 |
| **JSON output** | `--json` flag for CI/CD integration | v1.0 |
| **HTML report** | `--html` — self-contained SVG gauge, dark theme | v2.0 |
| **AST analysis** | Layer violation & circular dependency detection (AC-05) | v2.0 |
| **LLM analysis** | AI-powered over-engineering detection (`--llm`) | v2.0 |
| **Scan history** | SQLite-based history tracking & trend visualization | v2.0 |
| **REST API** | FastAPI — 5 endpoints, full OpenAPI spec | v3.0 |
| **Web UI** | React + TypeScript + Vite SPA | v3.0 |
| **TypeScript analysis** | ESLint, tsconfig, test coverage deep detection | v3.0 |
| **Plugin system** | `BaseAuditorPlugin` — extend with custom diagnostic items | v3.0 |
| **AGENTS.md generator** | `hachilles generate-agents` — project-aware output | v3.0 |

---

## Grade Scale

| Grade | Score Range | Meaning |
|-------|-------------|---------|
| **S** | 90 – 100 | Harness engineering best practice. Industry benchmark setter. |
| **A** | 75 – 89 | Robust harness. Production-ready with minor improvements possible. |
| **B** | 60 – 74 | Functional harness. Several improvements recommended. |
| **C** | 40 – 59 | Risk level. Significant issues present — immediate action required. |
| **D** | 0 – 39 | Crisis level. Full harness redesign strongly recommended. |

> **Note:** `hachilles scan` exits with code 1 for Grade C or below (score < 60), enabling CI gates.

---

## Architecture

HAchilles enforces a strict 9-layer unidirectional dependency:

```
models ← scanner ← auditors ← score ← prescriptions ← report ← cli / api
```

Reverse-direction imports are **forbidden** — enforced by pre-commit hooks and CI.

```
src/hachilles/
├── models/          # ScanResult data model (no deps)
├── scanner/         # File-system + AST scanner
├── auditors/        # CE / AC / EM auditors (3 pillars)
├── score/           # ScoreEngine — 0–100 + grade
├── prescriptions/   # Per-item improvement guidance
├── report/          # Jinja2 HTML report generator
├── llm/             # LLM client + evaluator (optional)
├── tracker/         # SQLite history tracker
├── plugins/         # Plugin registry + base class
├── api/             # FastAPI app + routes
└── cli.py           # Click CLI entry point
```

→ Full architecture details: [docs/architecture.md](docs/architecture.md)

---

## Docker

```bash
# Build
docker build -t hachilles:3.0.0 .

# Run web dashboard
docker run -p 8000:8000 hachilles:3.0.0

# CLI scan via volume mount (read-only)
docker run --rm \
  -v /path/to/your/project:/workspace:ro \
  hachilles:3.0.0 hachilles scan /workspace
```

---

## Development

```bash
make dev           # Install all dev dependencies
make lint          # ruff check + ruff format --check + mypy
make test          # Full test suite (611 tests)
make test-phase3   # Phase 3 (API + web) tests only
make web-build     # Build React frontend (Vite)
make serve         # Start web server (dev mode)
make build         # Build PyPI-ready distribution package
make clean         # Remove build artifacts
```

**Self-audit before every commit:**

```bash
hachilles scan .   # Must remain S-Grade (≥ 90 pts)
```

---

## Roadmap

Track our progress and planned features:

### v3.1 — Q2 2026
- [ ] **GitHub Actions native integration** — `hachilles-action` for zero-config CI gates
- [ ] **Score badge generator** — embed live HAchilles badge in any README
- [ ] **VS Code extension** — inline harness quality indicators while coding
- [ ] **Baseline comparison** — `hachilles scan . --compare-baseline`

### v3.2 — Q3 2026
- [ ] **Team / multi-repo dashboard** — aggregate scores across an organization
- [ ] **HAchilles Cloud (beta)** — hosted scanning with history, trends, and team views
- [ ] **Automated prescription PRs** — auto-generate fix PRs for common issues
- [ ] **Additional language support** — TypeScript/JavaScript native scanner (beyond tsconfig detection)

### v4.0 — Q4 2026
- [ ] **Real-time harness monitoring** — watch mode with live score updates
- [ ] **Regression alerting** — notify when score drops below threshold
- [ ] **Enterprise SSO / RBAC** — multi-tenant access control
- [ ] **Benchmark registry** — community-contributed harness quality benchmarks

> 💡 **Have a feature idea?** [Open a Feature Request](https://github.com/suhopark1/hachilles/issues/new?template=feature_request.md) — community input directly shapes the roadmap.

---

## Contributing

We welcome contributions of all kinds — bug reports, feature requests, documentation improvements, and code.

**Quick guide:**

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/hachilles.git

# 2. Create a branch
git checkout -b feat/your-feature-name

# 3. Make changes, run checks
make lint && make test
hachilles scan .   # Must remain S-Grade

# 4. Open a Pull Request
```

→ Full contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
→ Branch protection rules and workflow: [docs/branch-protection.md](docs/branch-protection.md)

**All PRs must maintain the S-Grade self-audit score (≥ 90 pts).** HAchilles measures itself with itself.

---

## Security Policy

> ⚠️ **Please do NOT open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in HAchilles, please report it **privately** by emailing:

**📧 suhopark1@gmail.com**

Include: a description of the vulnerability, steps to reproduce, potential impact, and your suggested fix if available.

We follow **coordinated disclosure**: we will acknowledge your report within 48 hours, assess it within 5 business days, and publish a fix before any public disclosure. You will be credited in the release notes (with your permission).

→ Full security policy: [SECURITY.md](SECURITY.md)

---

## Community & Standards

| Resource | Description |
|----------|-------------|
| [STANDARDS.md](STANDARDS.md) | Public CE·AC·EM diagnostic criteria — the measurement specification |
| [docs/whitepaper.md](docs/whitepaper.md) | Scoring algorithm, rationale, and research background |
| [docs/architecture.md](docs/architecture.md) | 9-layer architecture and dependency rules |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute code, docs, or diagnostic items |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting policy and supported versions |
| [CHANGELOG.md](CHANGELOG.md) | Version history: v1.0.0 → v2.0.0 → v3.0.0 |
| [GitHub Discussions](https://github.com/suhopark1/hachilles/discussions) | Questions, ideas, community Q&A (Korean welcome) |

**GitHub Topics:** `harness-quality` · `harness-diagnostics` · `ai-agent` · `llm` · `context-engineering` · `fastapi` · `cli`

---

## License

```
Copyright 2026 Park Sung Hoon (박성훈) <suhopark1@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

See [LICENSE](LICENSE) and [NOTICE](NOTICE) for full terms and third-party attributions.

---

<div align="center">

**HAchilles is itself a meta-example of harness engineering.**

Run `hachilles scan .` on this repository. Current result: **100 pts · S-Grade** ✅

*Build with Harness. Measure with HAchilles.*

</div>
