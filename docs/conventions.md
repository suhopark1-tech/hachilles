# HAchilles 코딩 컨벤션

## 언어 및 포매팅

- **Python 3.11+** 전용
- **ruff** 린터 + 포매터 (pyproject.toml의 [tool.ruff] 설정 준수)
- 줄 길이: 100자 이내
- 타입 힌트: 모든 public 함수에 필수. `from __future__ import annotations` 사용

## 함수/메서드 규칙

- **함수 길이**: 50줄 이하 (초과 시 분리)
- **파라미터**: 4개 이하 권장, 5개 이상이면 dataclass/TypedDict 사용
- **중첩 깊이**: 3단계 이하

## 예외 처리 규칙

- `except Exception:` 사용 금지 — 구체적 예외 타입 명시
- 불가피한 경우: `except Exception as e:  # [EXCEPTION] 이유` 형식으로 주석 필수
- `# noqa` / `# type: ignore` 사용 시 반드시 `# [EXCEPTION] 이유` 주석 추가

## 커밋 컨벤션

```
<type>(<scope>): <subject>

type: feat | fix | refactor | test | docs | chore
scope: scanner | auditors | score | cli | models | report

예시:
feat(scanner): CE-03 세션 브릿지 파일 탐지 추가
fix(auditors): CE-02 ADR 디렉토리 경로 인식 오류 수정
```

## 새 진단 항목 추가 방법

1. `ScanResult`에 필드 추가 (models/scan_result.py)
2. `Scanner`의 적절한 메서드에 스캔 로직 추가
3. 해당 `Auditor`에 audit 메서드 추가 (배점 포함)
4. `AGENTS.md`의 진단 항목 목록 업데이트
5. `docs/architecture.md`의 배점 테이블 업데이트
6. 테스트 추가 (`tests/auditors/`)

## 테스트 규칙

- 모든 Auditor의 각 항목: passed=True / False 케이스 최소 1개씩
- Scanner 테스트: `tests/fixtures/sample_projects/` 사용
- 픽스처 프로젝트: `minimal/` (모든 항목 통과), `no_harness/` (모든 항목 실패)

## 임포트 순서 (ruff isort 기준)

1. 표준 라이브러리
2. 서드파티 라이브러리
3. hachilles 내부 (레이어 순서 준수)
