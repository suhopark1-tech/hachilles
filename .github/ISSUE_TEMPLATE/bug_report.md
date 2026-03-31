---
name: "🐛 Bug Report"
about: Report a reproducible bug in HAchilles
title: "[BUG] "
labels: ["bug", "needs-triage"]
assignees: suhopark1
---

## Bug Description

<!-- A clear and concise description of the bug. One paragraph. -->

## Steps to Reproduce

<!-- Provide the minimum steps to reproduce the bug. -->

```bash
# 1. Setup (if needed)

# 2. The command that triggers the bug
hachilles scan /path/to/project

# 3. Expected vs actual behavior
```

1.
2.
3.

## Expected Behavior

<!-- What you expected to happen. -->

## Actual Behavior

<!-- What actually happened. Paste the full error output below. -->

<details>
<summary>Error output (click to expand)</summary>

```
paste error output here
```

</details>

## HAchilles Scan Output

<!-- If the bug is diagnostic-related, paste: hachilles scan . --json -->

<details>
<summary>hachilles scan --json (click to expand)</summary>

```json

```

</details>

## Environment

| Item | Value |
|------|-------|
| HAchilles version | `hachilles --version` output |
| Python version | `python --version` output |
| Operating System | e.g., macOS 15.1, Ubuntu 22.04, Windows 11 |
| Installation method | `pip install hachilles` / `pip install -e .` / Docker |
| Project type being scanned | e.g., Python CLI, FastAPI app, multi-agent system |

## Additional Context

<!-- Any other context that helps reproduce the issue — related issues, screenshots, PRs, etc. -->

---

> 🇰🇷 **한국어 사용자** — 이슈를 영어로 작성하기 어려우시면 한국어로 작성하셔도 됩니다.
> [GitHub Discussions](https://github.com/suhopark1/hachilles/discussions)에서는 항상 한국어를 환영합니다.
>
> ⚠️ **Security vulnerabilities** — please do NOT report security issues here. Email **suhopark1@gmail.com** instead.
