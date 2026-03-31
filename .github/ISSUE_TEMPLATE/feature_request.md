---
name: "✨ Feature Request"
about: Suggest a new feature or improvement for HAchilles
title: "[FEAT] "
labels: ["enhancement", "needs-discussion"]
assignees: suhopark1
---

## Problem Statement

<!-- What harness quality problem does this feature solve?
     Be specific: which pillar (CE/AC/EM) is underserved, which failure pattern is hard to detect, etc. -->

**Example:** "There is currently no way to detect when a project has no fallback paths defined (AC-04), 
so projects with missing error recovery receive no penalty."

## Proposed Solution

<!-- A clear description of what you want HAchilles to do.
     Code snippets, CLI examples, or mock output are very helpful. -->

```bash
# Example: what the new behavior would look like
hachilles scan . --detect-fallbacks
```

## Which Pillar / Diagnostic Area?

- [ ] **CE** — Context Engineering (CE-01 to CE-05)
- [ ] **AC** — Architectural Constraint (AC-01 to AC-05)
- [ ] **EM** — Entropy Management (EM-01 to EM-05)
- [ ] **New diagnostic item** — propose a new CE-0X / AC-0X / EM-0X item
- [ ] **CLI / UX improvement** — output, commands, options
- [ ] **API / Web UI** — REST API or dashboard feature
- [ ] **Integrations** — CI, IDE, cloud, external tools
- [ ] **Performance** — scanning speed, memory usage
- [ ] **Other** — describe below

## Failure Pattern Addressed (if applicable)

- [ ] Context Drift
- [ ] AI Slop
- [ ] Entropy Explosion
- [ ] Over-Engineering Trap
- [ ] 70-80 Wall
- [ ] None of the above / general improvement

## Use Case

<!-- Describe a concrete real-world scenario where this feature would be valuable.
     "As a developer working on a multi-agent customer service system, I need ..." -->

## Alternatives Considered

<!-- Any alternative approaches you considered and why you chose this one. -->

## Additional Context

<!-- Links, references, prior art, related issues, or papers that support this request. -->

---

> ✅ Check the [Roadmap](https://github.com/suhopark1/hachilles/blob/main/README.md#roadmap) before opening — your feature might already be planned.
> 🇰🇷 한국어로 작성하셔도 됩니다.
