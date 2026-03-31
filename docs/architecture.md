# HAchilles 아키텍처

## 레이어 구조 (의존성 방향)

```
models ← scanner ← auditors ← score ← prescriptions ← report ← cli
```

의존성은 **한 방향**으로만 흐른다. 하위 레이어가 상위 레이어를 import하는 것은 **절대 금지**.

## 레이어별 역할

| 레이어         | 모듈                                   | 역할                                          |
|--------------|----------------------------------------|----------------------------------------------|
| models       | `hachilles.models`                     | 공통 데이터 계약. 다른 hachilles 모듈 import 금지 |
| scanner      | `hachilles.scanner`                    | 파일시스템 탐색, ScanResult 수집               |
| auditors     | `hachilles.auditors`                   | ScanResult → AuditResult (15개 항목 진단)     |
| score        | `hachilles.score`                      | AuditResult 종합 → HarnessScore (0~100)       |
| prescriptions| `hachilles.prescriptions`              | 실패 항목 → 컨텍스트 특화 처방 생성 (Phase 2) |
| report       | `hachilles.report`                     | HarnessScore → HTML 리포트 (Phase 2)          |
| cli          | `hachilles.cli`                        | Click 기반 진입점. 모든 레이어 오케스트레이션  |

## 핵심 데이터 흐름

```
Path(target)
    ↓ Scanner.scan()
ScanResult          ← 파일시스템 원시 데이터
    ↓ ContextAuditor.audit()
    ↓ ConstraintAuditor.audit()
    ↓ EntropyAuditor.audit()
[AuditResult × 3]   ← 15개 진단 항목 결과
    ↓ ScoreEngine.score()
HarnessScore        ← 종합 점수 + 5대 패턴 위험도
    ↓ CLI / ReportGenerator
출력 (터미널 / JSON / HTML)
```

## 진단 항목 배점

| 코드   | 항목                      | 배점 | 기둥        |
|--------|--------------------------|------|-------------|
| CE-01  | AGENTS.md 존재 여부       | 10   | Context     |
| CE-02  | docs/ 구조 충실도         | 10   | Context     |
| CE-03  | 세션 브릿지 파일           | 8    | Context     |
| CE-04  | 완료 기준 구조화           | 6    | Context     |
| CE-05  | 아키텍처·컨벤션 문서 존재  | 6    | Context     |
| AC-01  | 린터 설정 파일             | 8    | Constraint  |
| AC-02  | pre-commit 훅             | 7    | Constraint  |
| AC-03  | CI Gate                  | 8    | Constraint  |
| AC-04  | 금지 패턴 목록             | 6    | Constraint  |
| AC-05  | 의존성 방향 위반           | 6    | Constraint  |
| EM-01  | AGENTS.md 최신성          | 6    | Entropy     |
| EM-02  | docs/ 평균 최신성          | 4    | Entropy     |
| EM-03  | AGENTS.md 참조 유효성     | 5    | Entropy     |
| EM-04  | GC 에이전트 존재           | 5    | Entropy     |
| EM-05  | 이유 없는 lint suppress    | 5    | Entropy     |
| **합계** |                          | **100** |          |

## 등급 기준

| 등급 | 점수    | 의미                         |
|------|---------|------------------------------|
| S    | 90~100  | 하네스 엔지니어링 모범 사례   |
| A    | 75~89   | 견고한 하네스 구조            |
| B    | 60~74   | 기본 하네스, 일부 개선 필요   |
| C    | 40~59   | 위험 수준 — 즉각 조치 필요   |
| D    | 0~39    | 위기 수준 — 전면 재설계 검토 |
