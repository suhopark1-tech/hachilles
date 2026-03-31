# HAchilles Standards

> **AI 에이전트 하네스 품질 기준의 공개 표준**

[![HAchilles](https://img.shields.io/badge/HAchilles-100%20S%E2%80%93Grade-brightgreen)](.)
[![Standards Version](https://img.shields.io/badge/Standards-v1.0-blue)](.)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## HAchilles Standards란?

HAchilles Standards는 AI 에이전트 하네스의 품질을 측정하는 공개 기준입니다.
CE(컨텍스트 엔지니어링) · AC(아키텍처 제약) · EM(엔트로피 관리) 세 기둥의
측정 기준을 커뮤니티가 함께 관리합니다.

표준이 공개되어야 측정이 신뢰받을 수 있습니다.
측정이 신뢰받아야 품질 개선이 의미를 갖습니다.

---

## 현행 표준 (v1.0)

세부 측정 로직은 [docs/whitepaper.md](docs/whitepaper.md)를 참조하세요.

### CE — 컨텍스트 엔지니어링 기준 (40점)

| 항목 | 기준 요약 | 배점 |
|------|----------|------|
| CE-01 | AGENTS.md 존재 + 50줄 이상 + 1,200줄 미만 | 10 |
| CE-02 | `docs/`에 마크다운 파일 3개 이상 | 10 |
| CE-03 | 세션 브릿지 파일 존재 (claude-progress.txt 등) | 8 |
| CE-04 | feature_list.json 존재 | 6 |
| CE-05 | docs/architecture.md + docs/conventions.md 모두 존재 | 6 |

### AC — 아키텍처 제약 설계 기준 (35점)

| 항목 | 기준 요약 | 배점 |
|------|----------|------|
| AC-01 | 린터 설정 파일 존재 (ruff.toml, .flake8 등) | 8 |
| AC-02 | .pre-commit-config.yaml 존재 | 7 |
| AC-03 | CI 파이프라인에 lint/test 잡 존재 | 8 |
| AC-04 | 금지 패턴 목록 문서화 (docs/forbidden.md 등) | 6 |
| AC-05 | 레이어 위반 0건 + 순환 의존성 0건 (AST 분석) | 6 |

### EM — 엔트로피 관리 기준 (25점)

| 항목 | 기준 요약 | 배점 |
|------|----------|------|
| EM-01 | AGENTS.md git 최신성 30일 이내 | 6 |
| EM-02 | docs/ 평균 git 최신성 30일 이내 | 4 |
| EM-03 | AGENTS.md 내부 참조 파일 모두 실존 (무효 참조 0건) | 5 |
| EM-04 | GC 에이전트 존재 (gc_agent.py 또는 CI 스케줄) | 5 |
| EM-05 | 이유 없는 lint suppress 비율 < 10% ([EXCEPTION] 주석 필수) | 5 |

---

## 등급 기준

| 등급 | 점수 범위 | 의미 | HAchilles Certified? |
|------|----------|------|----------------------|
| **S** | 90~100 | 하네스 엔지니어링 모범 사례 | ✅ Certified |
| **A** | 75~89 | 견고한 하네스 구조 | ✅ Certified |
| **B** | 60~74 | 기본 하네스, 일부 개선 필요 | — |
| **C** | 40~59 | 위험 수준 — 즉각 조치 필요 | — |
| **D** | 0~39 | 위기 수준 — 전면 재설계 검토 | — |

**HAchilles Certified (A/S등급)**: 에이전트 팀 README에 아래 뱃지를 사용할 수 있습니다.

```markdown
[![HAchilles Certified](https://img.shields.io/badge/HAchilles-S%20Grade%20Certified-brightgreen)](https://github.com/suhopark1/hachilles/blob/main/STANDARDS.md)
```

---

## 표준 개정 프로세스

HAchilles Standards는 커뮤니티 기여를 통해 개정됩니다.

### 표준 개정 제안 방법

1. **GitHub Issue 작성**: `[Standards RFC]` 제목 접두사 사용
2. **RFC 형식 작성**:
   ```
   ## 문제 (Problem)
   현재 기준의 어떤 점이 부적절한가?

   ## 제안 (Proposal)
   어떻게 바꾸면 좋은가? (기준값 변경, 새 항목 추가, 삭제)

   ## 근거 (Rationale)
   왜 이 변경이 필요한가? 실증 사례가 있는가?

   ## 영향 (Impact)
   기존 점수에 얼마나 영향을 주는가? (하위 호환성)
   ```
3. **토론 기간**: 최소 14일 (RFC Open 상태 유지)
4. **병합 기준**: 반대 의견 없이 14일 경과 또는 유지 관리자 2인 승인

### 버전 관리

- **마이너 개정** (측정 기준 수치 조정): `v1.x`
- **메이저 개정** (새 기둥 추가, 가중치 변경): `v2.0` — 1년 deprecated 기간 후 적용

---

## 표준 채택 현황

HAchilles Standards v1.0을 채택한 프로젝트:

| 프로젝트 | 최근 점수 | 등급 | 채택일 |
|---------|----------|------|--------|
| HAchilles (자체) | 100점 | S | 2026-03-29 |

> 채택을 원하시면 GitHub Issue로 알려주세요. 이 목록에 추가합니다.

---

## 자주 묻는 질문

**Q: HAchilles Certified 뱃지는 어떻게 획득하나요?**
`hachilles scan .`으로 75점(A등급) 이상을 달성하면 뱃지를 사용할 수 있습니다.
별도 신청 프로세스는 없습니다. 점수는 코드베이스가 증거입니다.

**Q: 표준에 동의하지 않으면요?**
RFC 프로세스로 개정을 제안하세요. 모든 기준은 커뮤니티 논의로 바뀔 수 있습니다.

**Q: Harness 플러그인으로 만든 팀도 이 기준으로 평가하나요?**
네. HAchilles Standards는 생성 도구에 관계없이 동일하게 적용됩니다.
Harness 통합 가이드: [docs/harness-integration.md](docs/harness-integration.md)

**Q: 영어 AGENTS.md도 CE-01을 통과하나요?**
네. `## Role` / `## Forbidden` 등 영어 섹션도 동일하게 인정합니다.

---

## 유지 관리자

- **박성훈** (@suhopark1) — 초기 설계자 · 「실전 하네스 엔지니어링」 저자

커뮤니티 기여자는 3개 이상 의미 있는 RFC 기여 시 공동 유지 관리자로 초청합니다.

---

*HAchilles Standards v1.0 · 2026-03-29*
*이 문서 자체도 [MIT 라이선스](LICENSE)로 공개됩니다.*
