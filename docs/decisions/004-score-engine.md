# ADR-004: Score 엔진 설계

**상태**: 확정
**작성일**: 2026-03-27
**관련 STEP**: 2-4 (Score 엔진 설계)

---

## 1. 컨텍스트

STEP 2-3(Auditor 인터페이스)에서 세 Auditor(ContextAuditor, ConstraintAuditor, EntropyAuditor)의 계약이 확정됐다. 각 Auditor는 `ScanResult → AuditResult`를 반환한다. 이 결과들을 집계해 HAchilles Score(0-100점)와 등급(S/A/B/C/D), 5대 실패 패턴 리스크를 산출하는 **Score 엔진**이 필요하다.

---

## 2. 결정 사항

### 2-1. 단일 ScoreEngine 클래스 + HarnessScore 결과 객체

**결정**: `ScoreEngine` 클래스와 `HarnessScore` 데이터클래스를 분리한다.

**근거**:
- `ScoreEngine`은 연산(동사), `HarnessScore`는 결과(명사). 책임이 다르다.
- `HarnessScore`를 불변 결과 객체로 만들면 CLI, 처방 엔진, 리포트 레이어 모두 같은 객체를 재사용할 수 있다.
- `ScoreEngine`은 상태가 없어야 한다(Auditor 목록은 `__init__`에서 고정).

**대안 (기각)**: 단일 `ScoreEngine.score()` 메서드가 딕셔너리를 반환. 기각 이유 — 타입 정보 손실, IDE 자동완성 불가, 계약 강제 어렵다.

---

### 2-2. `__init__`에서 Auditor 계약 검증

**결정**: `ScoreEngine.__init__()`에서 `_validate_auditor_contract()`를 호출하여 즉시 AssertionError를 발생시킨다.

```python
assert sum(a.full_score for a in self._auditors) == 100
assert len(pillars) == len(set(pillars))
```

**근거**:
- Auditor 설정 오류는 **프로그래밍 오류**다. 런타임 입력 오류와 구분해야 한다.
- `AssertionError`는 "이 코드 경로에 도달해선 안 된다"는 의도를 명확히 전달한다.
- `score()` 호출마다 검증하지 않고 `__init__()`에서 한 번만 하면 성능 영향이 없다.
- CI에서 `python -c "from hachilles.score import ScoreEngine; ScoreEngine()"` 로 빠르게 검증 가능.

**대안 (기각)**: `score()`에서 매번 검증. 기각 이유 — 불필요한 반복 연산, "이미 알려진 오류"를 반복 체크하는 것은 낭비.

---

### 2-3. `_determine_grade`를 정적 메서드로 분리

**결정**: 등급 결정 로직을 `@staticmethod _determine_grade(total: int) -> tuple[str, str]`로 분리한다.

**근거**:
- 단위 테스트 시 `ScanResult` 픽스처 없이 경계값을 직접 테스트할 수 있다.
- `_GRADE_BOUNDS`의 변경이 등급 결정에만 영향을 미치도록 의존성을 명시한다.
- 정적 메서드는 "이 메서드는 인스턴스 상태에 의존하지 않는다"는 계약을 코드로 표현한다.

---

### 2-4. 패턴 리스크를 비율(ratio) 기반으로 계산

**결정**: Context Drift 리스크는 AuditResult의 `score/full_score` 비율로 계산한다.

```python
ctx_ratio = ctx.score / ctx.full_score
# 0.4 미만 → CRITICAL, 0.6 미만 → HIGH, 0.8 미만 → MEDIUM, 이상 → OK
```

**근거**:
- 절댓값(예: "CE-01이 실패하면 HIGH")보다 비율이 더 강건하다. 향후 배점이 조정돼도 임계값이 변하지 않는다.
- 비율 기반은 "전체 맥락에서 얼마나 나쁜가"를 직관적으로 표현한다.

**예외**: AI Slop은 개별 항목의 실패 건수로 계산한다. 이유 — AC-01/02/03, EM-05가 각각 독립적인 게이트를 의미하므로, "몇 개의 게이트가 열려 있는가"가 더 의미 있는 메트릭이다.

---

### 2-5. `HarnessScore.to_dict()` — 직렬화를 결과 객체가 담당

**결정**: CLI가 `json.dumps(dataclasses.asdict(score))`를 호출하는 대신, `HarnessScore.to_dict()`가 직렬화 책임을 진다.

**근거**:
- `dataclasses.asdict()`는 `Path`, `Enum` 등을 자동 변환하지 않아 JSON 직렬화 시 `TypeError` 발생.
- `to_dict()`에서 `Enum.value`, `Path` 변환을 한 번에 처리하면 CLI 레이어가 단순해진다.
- 직렬화 포맷 변경 시 수정 지점이 `to_dict()` 하나뿐이다.

**대안 (기각)**: 커스텀 `JSONEncoder` 작성. 기각 이유 — 오버엔지니어링. `to_dict()`로 충분하다.

---

### 2-6. Over-engineering 패턴은 Phase 2로 이연

**결정**: `Over-engineering` 패턴 리스크는 MVP에서 항상 `RiskLevel.OK`를 반환한다.

```python
# [TODO] Phase 2: 순환 복잡도·AST 분석으로 구현 예정
risks.append(PatternRisk(
    pattern="Over-engineering",
    risk=RiskLevel.OK,
    evidence=["[TODO] Phase 2 LLM 기반 분석 예정"],
))
```

**근거**:
- Over-engineering 탐지에는 함수 길이, 순환 복잡도, 클래스 계층 깊이 등 다양한 메트릭이 필요하다.
- Phase 1(결정론적)에서 의미 있는 임계값을 정하기 어렵다.
- **중요**: `to_dict()` 출력에 `Over-engineering`이 항상 `"ok"`로 포함되어, API 소비자가 Phase 2 도입 시 포맷 변경 없이 값만 바뀐다.

---

## 3. `HarnessScore` 프로퍼티 설계

| 프로퍼티 | 타입 | 목적 |
|---|---|---|
| `context_score` | `int` | CE 기둥 점수 (0~40) |
| `constraint_score` | `int` | AC 기둥 점수 (0~35) |
| `entropy_score` | `int` | EM 기둥 점수 (0~25) |
| `all_audit_results` | `list[AuditResult]` | 순서 고정 [CE, AC, EM] |
| `failed_items_by_pillar` | `dict[Pillar, list[AuditItem]]` | 기둥별 실패 항목 |
| `passed_rate` | `float` | 15개 항목 통과 비율 (0~1) |
| `critical_items` | `list[AuditItem]` | 실패 항목, 배점 내림차순 정렬 |
| `to_dict()` | `dict` | JSON 직렬화 |

`passed_rate`와 `critical_items`는 처방 엔진(Sprint 3)이 우선순위를 정할 때 사용한다.

---

## 4. 테스트 전략

```
TestGradeDetermination (11개)  — _determine_grade 정적 메서드 경계값
TestScoreCalculation   (6개)   — score() 기본 동작
TestHarnessScoreProps  (9개)   — 프로퍼티 계약
TestPatternRisks       (10개)  — 5대 패턴 진단
TestScoreEngineContract (5개)  — __init__ 계약 검증
TestToDictSerialization (4개)  — JSON 직렬화
TestEdgeCases          (4개)   — 방어적 경계

총: 49개 (기존 8개 포함 시 57개)
```

**핵심 원칙**: `_determine_grade`를 정적 메서드로 분리했기 때문에, 등급 경계값 테스트는 실제 Auditor를 실행하지 않아도 된다. 이로써 등급 로직의 변경이 다른 레이어에 파급되는 것을 방지한다.

---

## 5. 알려진 한계

| 항목 | 설명 | 해소 예정 |
|---|---|---|
| Over-engineering | 항상 OK (Phase 2) | Phase 2 |
| 70-80% Wall | 70~85점 범위만 체크, 실제 "정체 기간"은 미측정 | Phase 2 |
| 패턴 리스크 임계값 | 경험적 값, 실제 프로젝트 데이터로 보정 필요 | Sprint 5+ |

---

## 6. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-03-27 | 초안 작성 (STEP 2-4) |
