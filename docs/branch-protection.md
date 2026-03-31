# Branch Protection Rules — HAchilles

This document explains how to configure GitHub Branch Protection Rules for the HAchilles repository. These rules are essential for maintaining code quality and preventing accidental pushes to production branches.

> 이 문서는 HAchilles 저장소의 브랜치 보호 규칙 설정 방법을 설명합니다.

---

## Why Branch Protection Matters

Without branch protection:
- A force push could overwrite `main` and lose release history
- A failing commit could break the published PyPI package
- A PR without review could introduce regressions
- The HAchilles self-audit score could drop below S-Grade undetected

Branch protection rules enforce the quality gates that HAchilles itself measures (AC-02: Loop Prevention, AC-03: Output Validation, AC-05: Human-in-the-Loop).

---

## Setup Instructions

### Step 1: Navigate to Branch Settings

1. Open your repository on GitHub: `github.com/suhopark1/hachilles`
2. Click **Settings** (gear icon, top menu)
3. Click **Branches** in the left sidebar
4. Click **Add branch protection rule**

---

### Step 2: Configure `main` Branch Protection

**Branch name pattern:** `main`

#### Pull Requests
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners (when CODEOWNERS file is added)

#### Status Checks
- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - Add these required status checks (they appear after CI has run at least once):
    - `lint`
    - `license-check`
    - `test (3.10)`
    - `test (3.11)`
    - `test (3.12)`
    - `typecheck`
    - `hachilles-self-audit`
    - `api-smoke-test`

#### Conversation Resolution
- ✅ **Require conversation resolution before merging**

#### Push Restrictions
- ✅ **Do not allow bypassing the above settings**
- ✅ **Restrict who can push to matching branches**
  - Add only the repository owner / maintainers

#### Force Push & Deletion
- ❌ Allow force pushes — **leave unchecked**
- ❌ Allow deletions — **leave unchecked**

---

### Step 3: Configure `develop` Branch Protection

**Branch name pattern:** `develop`

Apply the same rules as `main` with these differences:
- Required approvals: `1` (same)
- Required status checks (lighter set):
  - `lint`
  - `license-check`
  - `test (3.11)` (single version for speed)
  - `hachilles-self-audit`
- Allow pushes from: maintainers + collaborators with write access

---

### Step 4: Add CODEOWNERS (Optional but Recommended)

Create `.github/CODEOWNERS`:

```
# Global rule: maintainer must review all changes
* @suhopark1

# Core scoring logic requires extra scrutiny
src/hachilles/score/        @suhopark1
src/hachilles/auditors/     @suhopark1
STANDARDS.md                @suhopark1
```

With CODEOWNERS, GitHub automatically requests a review from the owner whenever the covered paths change.

---

## Required Status Checks Reference

| Check Name | CI Job | What It Validates |
|------------|--------|-------------------|
| `lint` | `lint` | ruff check + ruff format |
| `license-check` | `license-check` | Apache 2.0 headers in all .py files |
| `test (3.10)` | `test` matrix | Full 611-test suite on Python 3.10 |
| `test (3.11)` | `test` matrix | Full 611-test suite on Python 3.11 |
| `test (3.12)` | `test` matrix | Full 611-test suite on Python 3.12 |
| `typecheck` | `typecheck` | mypy --strict type checking |
| `hachilles-self-audit` | `hachilles-self-audit` | Self-audit score ≥ 90 (S-Grade) |
| `api-smoke-test` | `api-smoke-test` | All 5 FastAPI routes registered |

---

## Bypassing Protection (Emergency Only)

In rare emergency situations (e.g., critical security hotfix), a repository admin can temporarily allow bypassing. After the emergency:
1. Document the bypass in the commit message and PR description
2. Immediately re-enable protection
3. Create a post-mortem issue explaining why the bypass was necessary

---

## Verifying Your Setup

After configuring, verify by:

```bash
# Try to push directly to main — should be rejected
git checkout main
echo "test" >> README.md
git commit -m "test direct push"
git push origin main
# Expected: "remote: error: GH006: Protected branch update failed"
```

If GitHub rejects the push, your branch protection is correctly configured. ✅

---

## Common Issues

| Problem | Solution |
|---------|---------|
| "Required status check not found" | CI must run at least once before status checks appear in the dropdown |
| "Merge blocked — outdated branch" | Run `git merge upstream/main` to update your branch |
| "Self-audit failing" | Run `hachilles scan .` locally — find and fix the failing items |
| "License-check failing" | Run the Python header script or add the Apache 2.0 header manually |
