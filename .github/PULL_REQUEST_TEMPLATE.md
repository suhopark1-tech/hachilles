## Summary

<!-- What does this PR do? One paragraph max. -->

## Type of Change

- [ ] Bug fix (non-breaking fix for an existing issue)
- [ ] New feature (non-breaking addition)
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Documentation update
- [ ] Refactoring (no behavior change)
- [ ] Test addition / improvement
- [ ] CI / tooling update

## Related Issue

Closes #

## Checklist

### Code Quality
- [ ] `make lint` passes (ruff + mypy)
- [ ] `make test` passes (all 611+ tests)
- [ ] No new `# type: ignore` without `[EXCEPTION]` comment

### HAchilles Self-Audit Gate
- [ ] `hachilles scan .` score ≥ 90 (S-Grade maintained)
  - Before: `___` pts (Grade `_`)
  - After: `___` pts (Grade `_`)

### Documentation
- [ ] `CHANGELOG.md` updated (under `[Unreleased]`)
- [ ] `STANDARDS.md` updated if diagnostic criteria changed
- [ ] `docs/` updated if behavior or architecture changed
- [ ] New public APIs have docstrings

### Tests
- [ ] New tests cover the changed behavior
- [ ] Regression test added for bug fixes
- [ ] Contract tests updated if auditor interface changed

## Testing Notes

<!-- Describe how you tested this PR. What scenarios did you cover? -->

## Screenshots / Output

<!-- For CLI or UI changes, paste before/after output -->
