# ADR-003: Auditor 인터페이스 설계 원칙

**상태**: 확정
**날짜**: 2026-03-27
**결정자**: 박성훈

---

## 맥락

HAchilles는 15개 진단 항목을 3개 Auditor에 분산한다. 각 Auditor가 독립적으로 개발·테스트 가능하려면 명확한 인터페이스 계약이 필요하다. 또한 새 진단 항목 추가 시 기존 코드 변경을 최소화해야 한다.

---

## 인터페이스 설계

### BaseAuditor 추상 API

```python
class BaseAuditor(ABC):
    @property
    @abstractmethod
    def pillar(self) -> Pillar: ...          # 담당 기둥

    @property
    @abstractmethod
    def full_score(self) -> int: ...         # 만점 (실행 없이 쿼리 가능)

    @property
    @abstractmethod
    def item_codes(self) -> list[str]: ...   # 진단 코드 목록 (실행 없이 쿼리 가능)

    @abstractmethod
    def audit(self, scan: ScanResult) -> AuditResult: ...  # 핵심 진단

    def verify_result(self, result: AuditResult) -> list[str]: ...  # 계약 검증 (구체)
```

### 계약 불변식 (Invariant)

| 불변식 | 근거 |
|--------|------|
| `result.pillar == self.pillar` | AuditResult가 어떤 기둥인지 명시 |
| `result.full_score == self.full_score` | 만점이 선언값과 일치 |
| `{item.code} == set(item_codes)` | 누락/중복 코드 방지 |
| `0 ≤ result.score ≤ full_score` | 점수 범위 보장 |
| `sum(full_score of 3 auditors) == 100` | 시스템 레벨 불변식 |

---

## 핵심 설계 결정

### 1. ABC(추상 기반 클래스) vs typing.Protocol

**결정**: ABC 선택.

**비교**:

| 관점 | ABC | Protocol |
|------|-----|---------|
| 계약 강제 | 인스턴스화 시 컴파일 타임 오류 | 런타임 오류 (덕 타이핑) |
| 계약 테스트 | 상속으로 자동 적용 | 별도 fixture 필요 |
| 공통 구현 공유 | `verify_result()` 같은 구체 메서드 제공 가능 | 불가 |
| 타입 체커 | isinstance() 보장 | 구조적 서브타이핑 |

**근거**: `verify_result()` 같은 공통 헬퍼를 기반 클래스에 두고, 새 Auditor 작성자가 자동으로 상속받길 원한다. Protocol은 이를 지원하지 않는다.

### 2. full_score: 실행 전 쿼리 가능성

**결정**: `full_score`를 추상 프로퍼티로 선언하여 `audit()` 실행 없이 만점을 쿼리 가능하게 한다.

**근거**:
- ScoreEngine이 시작 시 세 Auditor의 `full_score` 합이 100인지 검증할 수 있다.
- CLI가 "X/100점" 포맷을 표시할 때 스캔 없이 분모를 계산할 수 있다.
- 새 Auditor 추가 시 배점 합산 오류를 즉시 발견할 수 있다.

**구현 패턴** (각 Auditor에서):
```python
@property
def full_score(self) -> int:
    # 모듈 상수 합산으로 선언 → 개별 배점 변경 시 자동 반영
    return _AGENTS_MD_FULL + _DOCS_STRUCT_FULL + _SESSION_FULL + ...
```

### 3. 무상태 설계 (Stateless Auditor)

**결정**: Auditor 인스턴스는 상태(state)를 보유하지 않는다.

**근거**:
- ScoreEngine이 하나의 Auditor 인스턴스를 여러 ScanResult에 재사용 가능.
- 테스트가 픽스처 초기화 없이 Auditor를 바로 사용 가능.
- 동시성 안전 (멀티스레드 환경에서 Auditor 공유 가능).

**금지 패턴**:
```python
# NG: Auditor에 상태 저장
class BadAuditor(BaseAuditor):
    def __init__(self):
        self._cache = {}  # ← 금지

    def audit(self, scan):
        self._last_scan = scan  # ← 금지
```

### 4. AuditorContractTest 패턴

**결정**: 새 Auditor의 테스트는 `AuditorContractTest`를 상속하여 16개 계약 검증 테스트를 자동 적용한다.

**근거**:
- 새 Auditor 작성자가 계약 검증 테스트를 직접 작성할 필요가 없다.
- 계약 변경 시 모든 Auditor에 일괄 적용된다.
- 새 항목 추가 시 `full_scan` 픽스처만 업데이트하면 된다.

**적용 구조**:
```
AuditorContractTest (16개 계약 테스트)
    ├── TestContextAuditorContract    (+3개 기둥별 테스트)
    ├── TestConstraintAuditorContract (+3개 기둥별 테스트)
    └── TestEntropyAuditorContract    (+3개 기둥별 테스트)
```

### 5. item_codes와 AuditItem.code 동기화

**결정**: `item_codes`는 Auditor 클래스에, 실제 `AuditItem.code`는 각 audit 메서드에 하드코딩한다. `verify_result()`가 두 값의 집합 일치를 검증한다.

**근거**:
- `item_codes`를 AuditItem 목록에서 유도하려면 audit()를 실행해야 한다.
- 선언과 구현이 다를 때 `verify_result()`가 즉시 발견한다.
- 코드 추가 시 두 곳을 모두 업데이트해야 한다는 점은 명시적 아키텍처의 트레이드오프로 허용.

---

## 새 Auditor 추가 체크리스트

새 진단 기둥 `XY`를 추가할 때:

```
□ 1. ScanResult에 필요한 원시 데이터 필드 추가 (models/scan_result.py)
□ 2. Scanner에 _scan_xy() 메서드 추가
□ 3. BaseAuditor 상속 → pillar, full_score, item_codes, audit() 구현
□ 4. AGENTS.md 진단 항목 목록 업데이트
□ 5. docs/architecture.md 배점 테이블 업데이트
□ 6. AuditorContractTest 상속 테스트 작성 (full_scan 픽스처 포함)
□ 7. ScoreEngine._auditors 목록에 추가
□ 8. 세 기둥 full_score 합 != 100이면 ScoreEngine 시작 시 오류 발생 확인
```

---

## 결과

- 각 Auditor는 독립적으로 개발·테스트 가능
- ScoreEngine 변경 없이 새 Auditor 추가 가능 (등록만 하면 됨)
- 계약 위반은 `verify_result()` 또는 `AuditorContractTest`로 즉시 발견
- 세 Auditor 합산 검증으로 배점 합계 오류 방지
