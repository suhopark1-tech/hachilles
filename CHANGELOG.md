# Changelog

HAchilles의 모든 주요 변경 사항을 기록합니다.
[Keep a Changelog](https://keepachangelog.com/) 규격 준수, [Semantic Versioning](https://semver.org/) 사용.

---

## [3.0.0] — 2026-03-29

### Added
- **REST API** — FastAPI 기반 5개 엔드포인트
  - `GET /api/health` — 헬스 체크 및 버전 확인
  - `POST /api/v1/scan` — 프로젝트 스캔 (전체 ScanResult 필드 반환)
  - `GET /api/v1/history` — SQLite 진단 이력 조회
  - `POST /api/v1/generate-agents` — AGENTS.md 자동 생성
- **웹 UI** — React + TypeScript + Vite SPA
  - `hachilles serve [--port] [--reload]` 커맨드로 실행
  - FastAPI StaticFiles를 통한 단일 서버 서빙
- **TypeScript 심층 분석** — `ScanResult`에 6개 필드 추가
  - `ts_has_eslint`, `ts_eslint_extends` — ESLint 설정 감지
  - `ts_has_strict`, `ts_has_path_aliases` — tsconfig 옵션 감지
  - `ts_test_files` — `*.test.ts` / `*.spec.ts` 파일 수
  - `ts_has_vitest_or_jest` — 테스트 프레임워크 설정 감지
- **플러그인 시스템** — `BaseAuditorPlugin` 상속으로 커스텀 진단 항목 확장
- **`hachilles generate-agents`** 커맨드 — 프로젝트 스캔 기반 맞춤형 AGENTS.md 자동 생성
- **GitHub Actions** — `web-build`, `api-smoke-test` 잡 추가
- **Makefile** — `make dev`, `make web-build`, `make serve`, `make build` 등
- **Docker 지원** — `Dockerfile` + `.dockerignore` 작성
- **통합 테스트** — `tests/test_integration_all_phases.py` 35개 케이스 (5개 유형)
- **`pyproject.toml`** — `httpx`, `anyio` 의존성 추가 (FastAPI TestClient)

### Changed
- `pyproject.toml` — 버전 `2.0.0` → `3.0.0`, `requires-python` `>=3.11` → `>=3.10`
- `README.md` — Phase 3 기능 전체 반영 (웹 UI, REST API, Docker, TypeScript 분석)
- `feature_list.json` — 버전 `0.2.0` → `3.0.0`, 17개 기능 모두 `implemented`
- `claude-progress.txt` — Phase 1/2/3 완료 이력 반영

### Fixed
- `api/models.py` — `ScanResponse`에 TypeScript 3개 필드 누락(`ts_eslint_extends`, `ts_has_path_aliases`, `ts_has_vitest_or_jest`) 추가
- `api/routes/scan.py` — 위 3개 필드 `scan_result`에서 올바르게 매핑
- `api/app.py` — `/api/health` 라우트를 `StaticFiles` mount 이전으로 이동 (라우트 우선순위 보정)
- `web/src/App.tsx` — `import React` 불필요 선언 제거 (TypeScript 빌드 오류 수정)
- `api/routes/agents.py`, `api/routes/scan.py`, `plugins/registry.py` — `type: ignore` 주석에 `[EXCEPTION]` 근거 추가 (EM-05 통과)
- `tests/test_integration_all_phases.py` — 3건 수정
  - `ReportGenerator.generate()` 인자 순서 수정 (`scan, score, presc` → `score, scan`)
  - HTML 리포트 키워드 검증을 한국어 기둥명으로 수정
  - `dependency_violations` 타입을 `set` → `int`로 수정

---

## [2.0.0] — 2026-03-28

### Added
- **AST 의존성 분석** — 소스 코드 AST 파싱으로 레이어 위반·순환 의존성 자동 탐지 (AC-05)
- **LLM Over-engineering 분석** — `--llm` 플래그, Claude/GPT API 기반 패턴 평가
- **진단 이력 추적** — SQLite 기반 `--save-history` 플래그, `hachilles history` 서브커맨드
- **`hachilles history <path>`** — 과거 진단 이력 조회 및 트렌드 분석
- **HTML 리포트 Phase 2** — AST 분석 결과·타임스탬프·LLM 점수 추가 반영
- `ScanResult` — `layer_violations`, `dependency_cycles`, `llm_over_engineering_score`, `scan_timestamp` 필드 추가
- **Phase 2 집중 테스트** — 575개 테스트 달성 (`test_phase2_ast.py`, `test_phase2_llm.py` 추가)

### Changed
- `pyproject.toml` — 버전 `1.0.0` → `2.0.0`, `llm` 옵션 의존성 그룹 추가 (`anthropic`, `openai`)
- `ScoreEngine` — AC-05 AST 분석 결과 반영

---

## [1.0.0] — 2026-03-27

### Added
- **Scanner** — 파일시스템 탐색으로 `ScanResult` 수집 (30개 필드)
- **ContextAuditor** — CE-01~06: AGENTS.md, docs 구조, 세션 브릿지, feature_list, 아키텍처 문서 연결 (40점)
- **ConstraintAuditor** — AC-01~06: 린터, pre-commit, CI, forbidden.md, 테스트 커버리지, 의존성 방향 (35점)
- **EntropyAuditor** — EM-01~03: 문서 최신성, AGENTS.md 참조 유효성, GC 에이전트, lint suppress 비율 (25점)
- **ScoreEngine** — 3대 기둥 15개 항목 → 0~100점 + S/A/B/C/D 등급 + 5대 패턴 위험도
- **PrescriptionEngine** — 실패 항목별 단계별 개선 처방 (15개 메서드)
- **ReportGenerator** — SVG 게이지·다크 테마 자기완결 HTML 리포트 (Jinja2)
- **CLI** — `hachilles scan <path> [--json] [--html] [--out]`
- **GC 에이전트** — `gc_agent.py` (오래된 캐시·리포트 정리)
- **AGENTS.md**, **docs/architecture.md**, **docs/conventions.md**, **docs/forbidden.md**
- **CI** — GitHub Actions (lint + test Python 3.11/3.12)
- **pre-commit** — ruff lint·format 훅
- 초기 테스트 433개 통과
- HAchilles 자가 진단 100점 S등급 달성
