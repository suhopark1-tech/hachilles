# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.x     | ✅ Active support |
| 2.x     | ⚠️ Security fixes only |
| 1.x     | ❌ End of life |

> **한국어** | 보안 취약점은 공개 이슈가 아닌 이메일로 제보해 주세요.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Please report security vulnerabilities by emailing:

**suhopark1@gmail.com**

Include in your report:
- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if you have one)

### Response Timeline

| Stage | Target Time |
|-------|-------------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix or mitigation | Within 30 days (critical: 7 days) |
| Public disclosure | After fix is released |

We follow coordinated disclosure. We ask that you keep vulnerability details private until we've had a reasonable time to address them.

---

## Scope

### In Scope

- `src/hachilles/` — core library and CLI
- `src/hachilles/api/` — REST API (FastAPI)
- Dependencies with known CVEs that affect HAchilles users

### Out of Scope

- Vulnerabilities in user-provided codebases being scanned
- Issues in development dependencies (`[dev]` extras)
- Theoretical attacks with no practical impact

---

## Security Design Notes

HAchilles is a **read-only diagnostic tool**. It does not:
- Write to the scanned codebase
- Execute code from the scanned project
- Send scan results to external services (unless you explicitly use `--llm` with an API key)

The LLM feature (`--llm`) sends **only** structural metadata (counts, patterns) to the configured AI API — never raw source code content.

---

## Acknowledgments

We are grateful to the security researchers who responsibly disclose vulnerabilities. Contributors who report valid security issues will be credited in the release notes (with permission).
