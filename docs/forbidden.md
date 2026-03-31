# HAchilles 금지 패턴 목록
# AC-04: 금지 패턴 목록 (6점)
#
# AI에게 이 파일을 코드 작성 전에 반드시 확인하도록 지시할 것.

---

## 1. 의존성 방향 위반 (최우선 금지)

HAchilles의 단방향 의존성 규칙:
```
models ← scanner ← auditors ← score ← prescriptions ← report ← cli
```

**금지 패턴:**
- `models`가 `scanner`, `auditors`, `score` 등을 import하는 것
- `scanner`가 `auditors` 이상을 import하는 것
- `auditors`가 `score`, `prescriptions`, `report`, `cli`를 import하는 것
- `prescriptions`가 `report`, `cli`를 import하는 것

**위반 예시:**
```python
# ✗ 금지: auditors에서 cli import
from hachilles.cli import console  # 역방향 의존성

# ✓ 허용: models는 어디서든 import 가능
from hachilles.models.scan_result import ScanResult
```

---

## 2. 비결정론적 채점 코드

**금지 패턴:**
- `random`, `uuid`, `datetime.now()`, `time.time()` 등을 채점 로직에 사용하는 것
- 외부 API 호출 결과를 직접 점수에 반영하는 것

**원칙:** 동일 `ScanResult` → 항상 동일 `HarnessScore`

```python
# ✗ 금지
import random
score = random.randint(0, 10)  # 채점에 비결정론 금지

# ✗ 금지
from datetime import datetime
score = 10 if datetime.now().hour < 12 else 5  # 시간 의존 채점 금지
```

---

## 3. 전역 상태 수정

**금지 패턴:**
- 모듈 레벨 가변 전역 변수 선언 및 수정
- `Scanner`, `Auditor`, `ScoreEngine` 인스턴스가 내부 상태를 누적하는 것
- 테스트 격리를 깨는 side-effect

```python
# ✗ 금지
_global_cache = {}  # 모듈 레벨 가변 상태

# ✓ 허용
_CONSTANTS = frozenset({"a", "b"})  # 불변 상수는 허용
```

---

## 4. Scanner 직접 파일 접근 우회

**금지 패턴:**
- Auditor가 `ScanResult`를 거치지 않고 파일시스템에 직접 접근하는 것
- `ScanResult` 없이 Auditor를 단독 실행하는 것

```python
# ✗ 금지: Auditor 내부에서 직접 파일 접근
class MyAuditor:
    def audit(self, scan):
        data = Path(scan.target_path / "file.md").read_text()  # Scanner 우회

# ✓ 허용: ScanResult의 필드만 사용
class MyAuditor:
    def audit(self, scan):
        return scan.has_agents_md  # ScanResult 필드 사용
```

---

## 5. 부분 점수 채점

**금지 패턴:**
- `AuditItem.score`가 0 또는 `full_score` 외의 값(부분 점수)을 가지는 것
- 단, N/A 처리(staleness=None)는 만점 처리 예외로 허용

```python
# ✗ 금지: 부분 점수
AuditItem(..., score=5, full_score=10)  # 5/10 부분 점수 금지

# ✓ 허용: 완전 통과 또는 완전 실패
AuditItem(..., passed=True,  score=10, full_score=10)
AuditItem(..., passed=False, score=0,  full_score=10)
```

---

## 참조

- 아키텍처 원칙: `docs/architecture.md`
- 설계 결정 기록: `docs/decisions/`
- AGENTS.md: 프로젝트 루트
