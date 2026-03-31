# HAchilles 진단 방법론 화이트페이퍼

**버전**: v3.0.0 · **작성자**: 박성훈 · **발행일**: 2026-03-29

> 이 문서는 HAchilles의 진단 로직을 완전히 공개합니다.
> 어떻게 측정하는지 투명하게 알 수 있어야 측정 결과를 신뢰할 수 있습니다.
> 모든 배점과 기준은 실제 소스 코드(`src/hachilles/auditors/`)와 1:1 일치합니다.

---

## 목차

1. [측정 철학](#1-측정-철학)
2. [3대 기둥 개요](#2-3대-기둥-개요)
3. [CE — 컨텍스트 엔지니어링 (40점)](#3-ce--컨텍스트-엔지니어링-40점)
4. [AC — 아키텍처 제약 설계 (35점)](#4-ac--아키텍처-제약-설계-35점)
5. [EM — 엔트로피 관리 (25점)](#5-em--엔트로피-관리-25점)
6. [5대 실패 패턴 평가](#6-5대-실패-패턴-평가)
7. [등급 산출 공식](#7-등급-산출-공식)
8. [JSON 출력 구조](#8-json-출력-구조)
9. [측정의 한계와 보완책](#9-측정의-한계와-보완책)
10. [버전별 변경 이력](#10-버전별-변경-이력)

---

## 1. 측정 철학

HAchilles는 세 가지 원칙을 기반으로 설계되었습니다.

**원칙 1 — 정적 분석 우선**: 코드를 실행하지 않고 파일 구조, 내용, 의존성만으로 진단합니다.
실행 환경 없이도 CI/CD 파이프라인 어디서나 동작합니다.

**원칙 2 — 결정론적 측정**: 같은 코드베이스에 대해 항상 같은 점수를 냅니다.
LLM 기반 분석(`--llm` 옵션)은 선택적이며, 기본 점수 산출에 포함되지 않습니다.

**원칙 3 — 측정 로직 공개**: 이 화이트페이퍼의 모든 배점·기준은 실제 소스 코드와 동기화됩니다.
점수에 이의가 있다면 GitHub Issue로 논의하세요.

---

## 2. 3대 기둥 개요

```
총점 100점 = CE (40점) + AC (35점) + EM (25점)
```

| 기둥 | 약어 | 배점 | 항목 수 | 핵심 질문 |
|------|------|------|--------|----------|
| 컨텍스트 엔지니어링 | CE | 40점 | 5 | AI 에이전트에게 충분한 컨텍스트가 제공되고 있나? |
| 아키텍처 제약 설계 | AC | 35점 | 5 | 코드 품질 게이트와 의존성 제약이 작동하고 있나? |
| 엔트로피 관리 | EM | 25점 | 5 | 문서와 코드가 신선하고 일관되게 유지되고 있나? |

가중치 배분 근거: 하네스 실패의 60% 이상이 컨텍스트 품질 문제(CE)에서 비롯되며,
아키텍처 결함(AC)이 35%, 엔트로피 폭발(EM)이 5~10%를 차지한다는 실증 분석에 기반합니다.
(출처: 「실전 하네스 엔지니어링」 6장)

---

## 3. CE — 컨텍스트 엔지니어링 (40점)

> 소스: `src/hachilles/auditors/context_auditor.py`

### CE-01: AGENTS.md 존재 및 라인 수 (10점)

**측정 대상**: 프로젝트 루트의 `AGENTS.md` 파일

**판정 기준**:
- 10점 (완전 통과): AGENTS.md 존재 + 50줄 이상 + 1,200줄 미만
- 5점 (부분 통과): AGENTS.md 존재하나 라인 수가 경고 범위(50줄 미만 또는 1,200줄 이상)
- 0점 (실패): AGENTS.md가 없거나 비어 있음

**참고**: 1,200줄 이상이면 "심각한 분리 필요" 경고와 함께 점수가 차감됩니다.
AGENTS.md가 너무 거대한 것도 컨텍스트 품질 저하의 신호입니다.

---

### CE-02: docs/ 구조 충실도 (10점)

**측정 대상**: `docs/` 디렉토리의 마크다운 파일 수 및 핵심 파일 존재 여부

**판정 기준**:
- 10점: `docs/`에 마크다운 파일 3개 이상 (architecture.md, conventions.md 등 핵심 파일 포함)
- 7점: 마크다운 파일 2개
- 4점: 마크다운 파일 1개
- 2점: `docs/` 디렉토리는 있으나 마크다운 파일 없음
- 0점: `docs/` 디렉토리 없음

---

### CE-03: 세션 브릿지 파일 존재 (8점)

**측정 대상**: `claude-progress.txt`, `session-bridge.md`, `PROGRESS.md` 또는 유사 파일

**판정 기준**:
- 8점: 세션 브릿지 파일 존재
- 0점: 없음

**배경**: 세션 브릿지 파일은 AI 에이전트가 이전 세션의 컨텍스트를 이어받기 위한
핵심 메커니즘입니다. 없으면 매 세션마다 컨텍스트 재구성이 필요합니다.

---

### CE-04: feature_list.json 존재 (6점)

**측정 대상**: 프로젝트 루트 또는 `docs/`의 `feature_list.json` 파일

**판정 기준**:
- 6점: 존재
- 0점: 없음

**배경**: 기능 목록 파일은 AI 에이전트가 프로젝트의 완료·미완료 기능을
정확히 파악하기 위한 구조화된 컨텍스트입니다.

---

### CE-05: architecture.md + conventions.md 존재 (6점)

**측정 대상**: `docs/architecture.md`와 `docs/conventions.md` (또는 유사 이름)

**판정 기준**:
- 6점: 두 파일 모두 존재
- 3점: 하나만 존재
- 0점: 둘 다 없음 (AGENTS.md도 없으면 측정 불가 처리)

---

## 4. AC — 아키텍처 제약 설계 (35점)

> 소스: `src/hachilles/auditors/constraint_auditor.py`

### AC-01: 린터 설정 파일 존재 (8점)

**측정 대상**: `ruff.toml`, `.ruff.toml`, `pyproject.toml ([tool.ruff])`, `.flake8`, `setup.cfg` 등

**판정 기준**:
- 8점: 린터 설정 파일 존재
- 0점: 없음

**배경**: 린터 없이는 코드 품질 게이트가 없는 것과 같습니다.
이 항목이 0점이면 AC-02, AC-03도 연쇄 실패할 가능성이 높습니다.

---

### AC-02: pre-commit 훅 설정 (7점)

**측정 대상**: `.pre-commit-config.yaml` 파일

**판정 기준**:
- 7점: 존재
- 0점: 없음

---

### AC-03: CI Gate (lint/test job) (8점)

**측정 대상**: `.github/workflows/` 또는 `.gitlab-ci.yml`, `Jenkinsfile` 등의 CI 설정

**판정 기준**:
- 8점: CI 파일 존재하고 lint 또는 test 잡이 확인됨
- 0점: CI 설정 없음

---

### AC-04: 금지 패턴 목록 (6점)

**측정 대상**: `docs/forbidden.md`, `AGENTS.md` 내 금지 섹션, `ruff` 규칙 설정 등

**판정 기준**:
- 6점: 금지 패턴이 명시적으로 문서화됨
- 0점: 없음

**배경**: 무엇을 하지 말아야 하는지를 명시하는 것이 코드 품질 유지의 핵심입니다.

---

### AC-05: 의존성 방향 위반 건수 (6점)

**측정 대상**: AST 분석으로 탐지된 레이어 위반(`layer_violations`)과 순환 의존성(`dependency_cycles`)

**판정 기준**:
- 6점: 위반 0건, 순환 0건
- 3점: 위반 1~2건 또는 순환 1건
- 0점: 위반 3건 이상 또는 순환 2건 이상

**계산식**: `violations_count = len(layer_violations) + len(dependency_cycles) * 2`

---

## 5. EM — 엔트로피 관리 (25점)

> 소스: `src/hachilles/auditors/entropy_auditor.py`

### EM-01: AGENTS.md 최신성 (6점)

**측정 대상**: `git log --follow -1 --format=%ci AGENTS.md`로 얻은 마지막 수정일

**판정 기준**:
- 6점: 30일 이내 수정
- 6점: git 이력 없음 (N/A — 만점 처리, 경고 메모 출력)
- 3점: 30~90일
- 0점: 90일 초과

---

### EM-02: docs/ 평균 최신성 (4점)

**측정 대상**: `docs/*.md` 파일들의 git 마지막 수정일 평균

**판정 기준**:
- 4점: 평균 30일 이내 또는 git 이력 없음 (N/A)
- 2점: 평균 30~90일
- 0점: 평균 90일 초과 또는 docs/ 없음

---

### EM-03: AGENTS.md 참조 유효성 (5점)

**측정 대상**: AGENTS.md 내부에서 참조하는 파일 경로들의 실존 여부

**판정 기준**:
- 5점: 무효 참조 0건
- 2점: 무효 참조 1~2건
- 0점: 무효 참조 3건 이상

---

### EM-04: GC 에이전트 존재 (5점)

**측정 대상**: `gc_agent.py` 파일 또는 CI 스케줄 잡에 garbage collection 작업 존재 여부

**판정 기준**:
- 5점: GC 에이전트 스크립트 또는 CI 스케줄 발견
- 0점: 없음

**배경**: GC 에이전트는 문서와 코드의 일관성을 자동으로 검사·정리하는 스크립트입니다.
없으면 엔트로피 관리를 수동으로만 수행해야 합니다.

---

### EM-05: 이유 없는 lint suppress 비율 (5점)

**측정 대상**: Python 소스의 `# type: ignore`, `# noqa`; TypeScript의 `// @ts-ignore`, `// eslint-disable` 중
`[EXCEPTION]` 근거 주석이 없는 "bare suppress" 비율

**계산식**:
```
bare_suppression_ratio = bare_suppresses / total_suppresses
```

**판정 기준**:
- 5점: 비율 < 10%
- 2점: 10% ≤ 비율 < 30%
- 0점: 비율 ≥ 30%

**[EXCEPTION] 주석 규칙**: 근거 없는 suppress는 AI 슬롭의 신호입니다.
`# type: ignore  # [EXCEPTION] 이유 설명` 형태만 허용합니다.

---

## 6. 5대 실패 패턴 평가

기본 점수(100점)와 별개로, 5대 실패 패턴의 위험도를 `CRITICAL / HIGH / MEDIUM / LOW / OK` 5단계로 평가합니다.
패턴 평가는 점수에 직접 영향을 주지 않으며, 개선 방향 안내에 사용됩니다.

> 소스: `src/hachilles/score/score_engine.py` — `_assess_pattern_risks()`

| 실패 패턴 | 위험 판단 기준 (CRITICAL) | 관련 항목 |
|----------|-------------------------|----------|
| **Context Drift** | CE 점수 비율 < 40% OR EM 점수 비율 < 40% | CE-01~05, EM-01~03 |
| **AI Slop** | AC-01/02/03 모두 실패 + EM-05 suppress 30% 이상 | AC-01, AC-02, AC-03, EM-05 |
| **Entropy Explosion** | EM 실패 항목 4개 이상 | EM-01~05 |
| **70-80% Wall** | 총점 60~80점 구간 + AC 또는 CE 실패 항목 다수 | AC-04, AC-05, CE-03~05 |
| **Over-engineering** | LLM 분석 필요 (`--llm` 옵션) | CE+AC+EM 종합 |

---

## 7. 등급 산출 공식

```python
total = ce_score + ac_score + em_score  # 0~100

if total >= 90:   grade = "S"   # 하네스 엔지니어링 모범 사례
elif total >= 75: grade = "A"   # 견고한 하네스 구조
elif total >= 60: grade = "B"   # 기본 하네스, 일부 개선 필요
elif total >= 40: grade = "C"   # 위험 수준 — 즉각 조치 필요
else:             grade = "D"   # 위기 수준 — 전면 재설계 검토

# CI 종료 코드
exit_code = 1 if total < 60 else 0   # C등급 이하 = CI 실패
```

---

## 8. JSON 출력 구조

`hachilles scan . --json` 출력의 최상위 키:

```json
{
  "hachilles_version": "3.0.0",
  "total": 100,
  "total_score": 100,
  "grade": "S",
  "grade_label": "하네스 엔지니어링 모범 사례",
  "pillars": {
    "context": {
      "score": 40,
      "full_score": 40,
      "items": [
        {
          "code": "CE-01",
          "pillar": "CE",
          "name": "AGENTS.md 존재 및 라인 수",
          "passed": true,
          "score": 10,
          "full_score": 10,
          "detail": "AGENTS.md 68줄 — 적절한 분량"
        }
      ]
    },
    "constraint": { "score": 35, "full_score": 35, "items": [] },
    "entropy":    { "score": 25, "full_score": 25, "items": [] }
  },
  "pattern_risks": [
    {
      "pattern": "Context Drift",
      "risk": "ok",
      "summary": "Context Drift 위험 없음",
      "evidence": []
    }
  ]
}
```

**GitHub Actions에서 사용 시**:
```bash
TOTAL=$(jq -r '.total' result.json)                      # 총점
GRADE=$(jq -r '.grade' result.json)                      # 등급
CE=$(jq -r '.pillars.context.score' result.json)         # CE 점수
AC=$(jq -r '.pillars.constraint.score' result.json)      # AC 점수
EM=$(jq -r '.pillars.entropy.score' result.json)         # EM 점수
```

---

## 9. 측정의 한계와 보완책

**한계 1 — 정적 분석의 본질적 한계**: 코드를 실행하지 않으므로 런타임 동작을 측정하지 못합니다.
→ 보완: `--llm` 옵션으로 Claude가 에이전트 정의를 동적으로 평가

**한계 2 — 언어 범위**: Python, TypeScript 이외의 언어는 기본 파일 구조 분석만 수행합니다.

**한계 3 — git 이력 의존성**: EM-01, EM-02는 git 이력이 있어야 최신성을 측정합니다.
git 이력이 없으면 N/A 처리(만점)로 경고 메모를 출력합니다.

---

## 10. 버전별 변경 이력

| 버전 | 주요 변경 |
|------|----------|
| v3.0.0 | TypeScript 분석 추가, EM-05 [EXCEPTION] 주석 규칙 도입, GC 에이전트(EM-04) 항목 추가 |
| v2.0.0 | AC-05 의존성 방향 위반 AST 탐지, 진단 이력(SQLite) 추가 |
| v1.0.0 | CE·AC·EM 3대 기둥 초기 설계 (CE-01~05, AC-01~05, EM-01~05), CLI 구현 |

---

*이 화이트페이퍼의 내용에 이의가 있거나 개선 제안이 있다면:*
*https://github.com/suhopark1/hachilles/issues 에서 논의해주세요.*

*HAchilles Standards Council에 참여하려면: [STANDARDS.md](../STANDARDS.md)*
