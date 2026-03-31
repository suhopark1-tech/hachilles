# ADR-002: Scanner 모듈 설계 원칙

**상태**: 확정
**날짜**: 2026-03-27
**결정자**: 박성훈

---

## 맥락

HAchilles의 모든 진단은 Scanner가 수집한 `ScanResult` 객체를 기반으로 한다. Scanner 설계의 품질이 진단 전체의 신뢰성을 결정한다.

---

## 핵심 설계 결정

### 1. ScanResult: 단일 진실 공급원 (SSOT)

**결정**: Auditor는 파일시스템에 직접 접근하지 않는다. `ScanResult`만 참조한다.

**근거**:
- Auditor의 단위 테스트가 `ScanResult` 픽스처로 가능해진다.
- 파일시스템 변경이 Auditor 로직에 영향을 주지 않는다.
- 향후 LLM 기반 원격 스캔(API로 받은 데이터)도 같은 Auditor로 처리 가능.

**결과**:
```
Scanner → ScanResult → Auditor (파일 접근 없음)
```

### 2. 제외 디렉토리: _EXCLUDE_DIRS

**결정**: `.git`, `node_modules`, `__pycache__`, `.venv` 등 노이즈 디렉토리를 모든 재귀 탐색에서 제외한다.

**근거**:
- `.git` 내 hook 파일이 Python 파일로 인식되는 오탐 방지.
- `node_modules`는 수십만 파일이 있어 탐색 시간 폭증.
- `__pycache__`의 `.pyc` 파일은 원본 `.py`의 중복 오탐.
- `_EXCLUDE_DIRS`를 중앙 상수로 관리하여 일관성 보장.

### 3. 메모리 안전: _MAX_FILE_BYTES / _MAX_TOTAL_BYTES

**결정**: 단일 파일 읽기 상한 512KB, 참조 검사 총량 상한 25MB.

**근거**:
- 자동 생성 파일(예: `package-lock.json` 5MB+)이 메모리를 독점하는 상황 방지.
- Large monorepo에서 AGENTS.md 참조 검사가 수 분이 걸리는 현상 방지.
- 상한 초과 시 잘라 읽으므로 거짓 음성(false negative) 가능성이 있으나, 이는 명시적으로 허용된 트레이드오프.

### 4. AGENTS.md 참조 유효성 (_check_agents_refs)

**결정**: backtick 식별자를 추출하되, `_COMMON_IDENTIFIERS`로 필터링 후 코드베이스에서 검색한다.

**근거**:
- `Path`, `None`, `list`, `dict` 같은 내장/표준 식별자를 AGENTS.md에서 참조해도 "무효 참조"로 오탐하면 노이즈가 많다.
- 60+개 Python/JS 공통 식별자를 필터링하면 실질적인 커스텀 식별자만 검사된다.

**한계 (Phase 2 개선 예정)**:
- AST 기반이 아닌 텍스트 기반 탐지 → 동적 클래스명, `__all__` 재내보내기 미탐 가능.
- 간단한 정의 패턴(`class X`, `def x`, `function x`)만 검색.

### 5. 린터 억제 비율 (_measure_bare_suppressions)

**결정**: `[EXCEPTION]` 키워드를 라인 **전체**에서 검색한다 (suppress 키워드 앞뒤 무관).

**v1.0 버그 수정 내용**:
```python
# 버그 (v1.0): noqa 뒤에 [EXCEPTION]이 오는지만 확인
r"#\s*noqa(?!.*\[EXCEPTION\])"  # [EXCEPTION]이 앞에 있으면 탐지 못함

# 수정 (v2.0): 라인 전체에서 [EXCEPTION] 검색
if _SUPPRESS_RE.search(line):
    if not _EXCEPTION_RE.search(line):  # 라인 어디에도 없으면 bare
        bare_count += 1
```

**올바른 예시**:
```python
# [EXCEPTION] 마이그레이션 스크립트라 Repo 직접 접근 필요
result = repo.get_all()  # noqa: E501

# NG: [EXCEPTION] 없는 억제 → bare suppress로 집계됨
result = repo.get_all()  # noqa
```

### 6. AC-04 금지 패턴 탐지 확장

**결정**: `docs/forbidden.md` 파일 없어도 AGENTS.md에 금지 섹션이 있으면 부분 인정.

**근거**:
- 소규모 프로젝트에서는 별도 파일 대신 AGENTS.md에 금지 패턴을 통합하는 것이 현실적.
- 단, `docs/forbidden.md`를 1순위로 권장하는 처방은 유지.

---

## ScanResult 필드 설계 원칙

| 필드 유형     | 설계 원칙                                           |
|-------------|---------------------------------------------------|
| `has_*`     | 존재 여부 bool. 후속 필드의 전제 조건으로 사용.        |
| `*_path`    | 발견된 파일 경로. `has_*=True`일 때만 의미 있음.       |
| `*_lines`   | 파일 라인 수. 0이면 비어있음을 의미.                  |
| `*_days`    | 경과 일수. `None`이면 git 히스토리 없음 (N/A).        |
| `*_ratio`   | 0.0~1.0 비율. 0.0이면 해당 항목 없음.                |
| `scan_errors`| 비치명적 오류 메시지 목록. 스캔 중단 없이 기록.        |

---

## 알려진 한계 및 로드맵

| 한계                              | 대응 계획                           |
|----------------------------------|-------------------------------------|
| AC-05 의존성 위반 미측정           | Sprint 3: AST import 분석 구현       |
| EM-03 참조 검사 정확도 한계        | Sprint 4: AST 기반 정의 탐지 고도화  |
| 멀티 레포 / 모노레포 지원 없음     | Phase 2: 경로 설정 옵션 추가         |
| Windows 경로 처리 미검증          | Sprint 3: CI에 Windows 테스트 추가   |
