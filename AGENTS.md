# HAchilles — AGENTS.md
> AI 에이전트를 위한 진입점. 이 파일을 매 세션 시작 시 가장 먼저 읽어라.
> 규칙은 짧고 구체적으로. 상세 내용은 docs/ 를 참조하라.

---

## 이 프로젝트가 하는 일
HAchilles는 AI 에이전트 시스템의 **하네스 설계 품질을 진단**하는 CLI 도구다.
`hachilles scan ./target` 명령 하나로 대상 프로젝트의 HAchilles Score(0-100)와 처방을 출력한다.

---

## 레이어 구조 (의존성 방향 — 위반 금지)
```
models  ←  scanner  ←  auditors  ←  score  ←  prescriptions  ←  report  ←  cli
```
역방향 import는 즉시 PR 거부. 위반 시 오류 메시지: "레이어 경계 위반 — docs/decisions/001-layer-architecture.md 참조"

---

## 핵심 규칙 (구체적이고 검증 가능한 것만)

### 코드
- **함수 크기**: 단일 함수 50줄 초과 금지. 초과 시 분리하라.
- **에러 처리**: `except Exception` 금지. 구체적 예외 타입만. `# [EXCEPTION] 이유` 주석 없는 bare except는 린터가 차단.
- **타입 힌트**: 모든 public 함수에 타입 힌트 필수. `mypy --strict` 통과.
- **테스트**: 새 Auditor 항목 추가 시 반드시 fixtures/sample_projects/ 에 테스트 케이스 추가.

### 커밋
- `feat:` / `fix:` / `refactor:` / `docs:` / `test:` prefix 필수.
- 에이전트가 실수를 저질렀을 때 → AGENTS.md에 한 줄 규칙 추가 → 같이 커밋.

### 진단 항목 추가/변경 규칙
- 새 진단 항목은 반드시 **실제로 발생한 실패 케이스**에서 출발한다. 이론적 필요성만으로 추가 금지.
- 각 항목에 `# [출처: 어떤 실패에서 나왔는가]` 주석 필수.

---

## 하면 안 되는 것 (금지 패턴)
- `auditors/` 에서 `cli.py` import 금지 (역방향)
- `report/` 에서 `score/` 직접 수정 금지
- `hachilles/` 외부 파일을 하드코딩 경로로 참조 금지 (`Path(__file__).parent` 사용)
- LLM API 호출을 `auditors/` 레이어에서 직접 하지 말 것 — Phase 2에서 별도 `llm_evaluator/` 레이어로 분리 예정

---

## 주요 파일 위치
| 파일 | 역할 |
|------|------|
| `src/hachilles/models/scan_result.py` | 모든 진단의 공통 데이터 구조 |
| `src/hachilles/scanner/scanner.py` | 대상 프로젝트 파일 시스템 파싱 |
| `src/hachilles/auditors/base.py` | Auditor 인터페이스 정의 |
| `src/hachilles/score/score_engine.py` | HAchilles Score 산출 로직 |
| `src/hachilles/cli.py` | Click CLI 진입점 |
| `docs/architecture.md` | 전체 아키텍처 및 레이어 설명 |
| `docs/decisions/` | ADR (Architecture Decision Records) |

---

## 세션 시작 시 체크리스트
1. `git log --oneline -5` 로 최근 변경사항 확인
2. `pytest -q` 로 현재 테스트 통과 확인
3. `ruff check src/` 로 린터 에러 없는지 확인
4. 작업할 기능이 `docs/decisions/` 에 결정 기록이 있는지 확인

---

*이 파일의 각 줄은 실제 실수에서 태어난 것이다. — HAchilles Harness Engineering 원칙 적용*
