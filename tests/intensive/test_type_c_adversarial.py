"""Type-C: Adversarial & Fault Injection Testing (적대적 결함 주입 테스트)

의도적으로 비정상·극단·악의적 입력을 주입해 시스템의 방어 능력을 검증한다.

검증 목표:
  ADV-01: 극단값 내성 — 음수, 매우 큰 수, 빈 리스트 등
  ADV-02: 경계 0값 내성 — 0줄, 0일, 0개 등
  ADV-03: None 전파 방지 — None 입력이 연산 오류로 전파되지 않음
  ADV-04: 병렬 실행 안전성 — 동시에 여러 ScanResult를 처리해도 결과가 일관
  ADV-05: 실제 파일시스템 결함 처리 — 존재하지 않는 경로, 권한 없는 파일
  ADV-06: 거대 프로젝트 내성 — 파일 수천 개를 가진 프로젝트에서 정상 동작
  ADV-07: 반복 호출 안정성 — 동일 엔진을 1,000회 반복 호출해도 메모리 누수·크래시 없음
  ADV-08: Scanner 인코딩 내성 — 특수문자·이모지·비 ASCII 포함 경로·파일명
"""

from __future__ import annotations

import threading
from copy import deepcopy
from pathlib import Path

import pytest

from hachilles.models.scan_result import ScanResult
from hachilles.scanner.scanner import Scanner
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _minimal_scan(tmp_path: Path) -> ScanResult:
    """가장 기본적인 ScanResult (기본값만 설정)."""
    return ScanResult(target_path=tmp_path)


# ── ADV-01: 극단값 내성 ───────────────────────────────────────────────────────

class TestAdversarialExtremeValues:

    def test_adv01_negative_agents_lines(self, tmp_path):
        """ADV-01a: agents_md_lines 음수 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_agents_md    = True
        scan.agents_md_lines  = -999
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_very_large_staleness(self, tmp_path):
        """ADV-01b: staleness_days 극단값(999,999일) → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_agents_md            = True
        scan.agents_md_lines          = 100
        scan.agents_md_staleness_days = 999_999
        scan.docs_avg_staleness_days  = 999_999.0
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_very_large_dependency_violations(self, tmp_path):
        """ADV-01c: dependency_violations 수천 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.dependency_violations = 100_000
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_suppress_ratio_above_1(self, tmp_path):
        """ADV-01d: bare_lint_suppression_ratio > 1.0 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.bare_lint_suppression_ratio = 999.9
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_suppress_ratio_negative(self, tmp_path):
        """ADV-01e: bare_lint_suppression_ratio < 0.0 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.bare_lint_suppression_ratio = -0.5
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_very_large_invalid_refs(self, tmp_path):
        """ADV-01f: invalid_agents_refs 수천 개 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_agents_md       = True
        scan.invalid_agents_refs = [f"ref_{i}" for i in range(10_000)]
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv01_very_large_docs_files(self, tmp_path):
        """ADV-01g: docs_files 수천 개 → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_docs_dir = True
        scan.docs_files   = [tmp_path / f"docs/doc_{i}.md" for i in range(5_000)]
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100


# ── ADV-02: 경계 0값 내성 ────────────────────────────────────────────────────

class TestAdversarialZeroBoundary:

    def test_adv02_zero_agents_lines(self, tmp_path):
        """ADV-02a: agents_md_lines=0 (빈 AGENTS.md) → 예외 없이 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_agents_md   = True
        scan.agents_md_lines = 0
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv02_zero_staleness(self, tmp_path):
        """ADV-02b: staleness_days=0 (방금 수정) → 만점 처리."""
        scan = _minimal_scan(tmp_path)
        scan.has_agents_md            = True
        scan.agents_md_lines          = 100
        scan.agents_md_staleness_days = 0
        from hachilles.auditors.entropy_auditor import EntropyAuditor
        em01 = EntropyAuditor()._audit_em01(scan)
        assert em01.passed, "staleness=0일 → EM-01 통과해야 함"

    def test_adv02_zero_docs_files(self, tmp_path):
        """ADV-02c: has_docs_dir=True but docs_files=[] → 처리 가능."""
        scan = _minimal_scan(tmp_path)
        scan.has_docs_dir = True
        scan.docs_files   = []
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv02_zero_dependency_violations(self, tmp_path):
        """ADV-02d: dependency_violations=0 → AC-05 만점."""
        scan = _minimal_scan(tmp_path)
        scan.dependency_violations = 0
        from hachilles.auditors.constraint_auditor import ConstraintAuditor
        con = ConstraintAuditor()
        ac05 = next(i for i in con.audit(scan).items if i.code == "AC-05")
        assert ac05.passed, "위반 0건 → AC-05 통과해야 함"


# ── ADV-03: None 전파 방지 ───────────────────────────────────────────────────

class TestAdversarialNonePropagation:

    def test_adv03_all_optional_fields_none(self, tmp_path):
        """ADV-03a: 선택적 필드 모두 None → 예외 없이 0~100점."""
        scan = ScanResult(target_path=tmp_path)
        scan.agents_md_path          = None
        scan.session_bridge_path     = None
        scan.linter_config_path      = None
        scan.agents_md_staleness_days = None
        scan.docs_avg_staleness_days  = None
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv03_scan_errors_do_not_affect_score(self, tmp_path):
        """ADV-03b: scan_errors가 있어도 스코어 계산에 영향을 주지 않음."""
        scan_clean = ScanResult(target_path=tmp_path)
        scan_error = deepcopy(scan_clean)
        scan_error.scan_errors = [
            "Permission denied: /etc/shadow",
            "UnicodeDecodeError: 'utf-8' codec can't decode",
        ]
        assert ENGINE.score(scan_clean).total == ENGINE.score(scan_error).total, \
            "scan_errors 존재가 점수에 영향을 줌 — scan_errors는 메타 정보로만 사용해야 함"


# ── ADV-04: 병렬 실행 안전성 ─────────────────────────────────────────────────

class TestAdversarialConcurrency:

    def test_adv04_concurrent_scoring(self, tmp_path):
        """ADV-04: 32개 스레드에서 동시에 ENGINE.score() 호출 → 결과 일관."""
        import random
        rng = random.Random(2024)

        def make_scan() -> ScanResult:
            s = ScanResult(target_path=tmp_path)
            s.has_agents_md  = rng.choice([True, False])
            s.agents_md_lines = rng.randint(0, 1000)
            s.has_linter_config = rng.choice([True, False])
            return s

        scans   = [make_scan() for _ in range(32)]
        expected = [ENGINE.score(s).total for s in scans]

        results = [None] * 32
        errors  = []

        def worker(idx: int) -> None:
            try:
                results[idx] = ENGINE.score(scans[idx]).total
            except Exception as exc:
                errors.append((idx, str(exc)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"병렬 실행 중 예외 {len(errors)}건: {errors[:3]}"
        assert results == expected, \
            f"병렬 실행 결과 불일치: {[(i, results[i], expected[i]) for i in range(32) if results[i] != expected[i]][:3]}"

    def test_adv04_concurrent_scanner(self, tmp_path):
        """ADV-04b: 여러 스레드에서 서로 다른 경로를 동시에 Scanner로 스캔."""
        errors = []

        def scan_worker(path: Path) -> None:
            try:
                Scanner(path).scan()
            except Exception as exc:
                errors.append(str(exc))

        # 서로 다른 tmp 하위 디렉토리 생성
        paths = []
        for i in range(8):
            p = tmp_path / f"proj_{i}"
            p.mkdir()
            (p / "AGENTS.md").write_text(f"# Project {i}\n")
            paths.append(p)

        threads = [threading.Thread(target=scan_worker, args=(p,)) for p in paths]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"병렬 Scanner 실행 중 예외: {errors[:3]}"


# ── ADV-05: 실제 파일시스템 결함 처리 ────────────────────────────────────────

class TestAdversarialFilesystem:

    def test_adv05_nonexistent_target_path_raises(self, tmp_path):
        """ADV-05a: 존재하지 않는 경로 → FileNotFoundError (빠른 실패 설계 검증).

        [설계 결정]
        Scanner는 생성자에서 경로 유효성을 검증하고 즉시 예외를 던진다.
        이것은 '빠른 실패(fail-fast)' 원칙 구현이다.
        callers는 Scanner 생성 전 경로 존재 여부를 확인해야 한다.
        """
        ghost_path = tmp_path / "does_not_exist" / "nowhere"
        with pytest.raises(FileNotFoundError, match="대상 경로를 찾을 수 없습니다"):
            Scanner(ghost_path)

    def test_adv05_not_a_directory_raises(self, tmp_path):
        """ADV-05a2: 파일 경로(디렉토리 아님) → NotADirectoryError."""
        file_path = tmp_path / "some_file.py"
        file_path.write_text("# code")
        with pytest.raises(NotADirectoryError):
            Scanner(file_path)

    def test_adv05_empty_directory(self, tmp_path):
        """ADV-05b: 빈 디렉토리 → 0점 가깝지만 예외 없음."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        scan   = Scanner(empty_dir).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv05_directory_with_only_binary_files(self, tmp_path):
        """ADV-05c: 바이너리 파일만 있는 디렉토리 → 예외 없음."""
        proj = tmp_path / "binary_proj"
        proj.mkdir()
        (proj / "model.bin").write_bytes(bytes(range(256)) * 100)
        (proj / "data.pkl").write_bytes(b"\x80\x04\x95" + b"\x00" * 50)
        scan   = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv05_agents_md_with_non_utf8_content(self, tmp_path):
        """ADV-05d: AGENTS.md가 비 UTF-8 인코딩 → scan_errors 기록 또는 graceful 처리."""
        proj = tmp_path / "encoding_proj"
        proj.mkdir()
        agents_path = proj / "AGENTS.md"
        # UTF-8로 디코딩 불가한 바이트 시퀀스 쓰기
        agents_path.write_bytes(b"# Project\n\xff\xfe invalid utf-8\n" + b"\x80" * 100)
        # 예외 없이 스캔돼야 함
        scan = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100


# ── ADV-06: 거대 프로젝트 내성 ───────────────────────────────────────────────

class TestAdversarialLargeProject:

    def test_adv06_many_docs_files(self, tmp_path):
        """ADV-06a: docs/ 에 500개 파일 → 정상 스코어 반환."""
        proj  = tmp_path / "large_proj"
        docs  = proj / "docs"
        docs.mkdir(parents=True)
        (proj / "AGENTS.md").write_text("# Guide\n" * 50)
        for i in range(500):
            (docs / f"doc_{i:04d}.md").write_text(f"# Doc {i}\n")
        scan   = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert isinstance(result.total, int)
        assert 0 <= result.total <= 100

    def test_adv06_very_large_agents_md(self, tmp_path):
        """ADV-06b: AGENTS.md가 10만 줄 → Scanner가 제한 내에서 처리."""
        proj = tmp_path / "huge_agents"
        proj.mkdir()
        agents_path = proj / "AGENTS.md"
        # _MAX_FILE_BYTES(512KB) 초과하도록 대용량 파일 생성
        agents_path.write_text("# line\n" * 100_000)
        # 예외 없이 처리, scan_errors 또는 라인수 0 처리 가능
        scan = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv06_deeply_nested_directory(self, tmp_path):
        """ADV-06c: 30단계 깊이 중첩 디렉토리 → 예외 없이 스캔."""
        deep = tmp_path
        for i in range(30):
            deep = deep / f"level_{i}"
        deep.mkdir(parents=True)
        (deep / "AGENTS.md").write_text("# Deep\n")
        scan   = Scanner(tmp_path).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100


# ── ADV-07: 반복 호출 안정성 ─────────────────────────────────────────────────

class TestAdversarialRepetition:

    def test_adv07_repeated_scoring_stable(self, tmp_path):
        """ADV-07: 동일 ScanResult로 500회 반복 → 매번 동일 결과, 예외 없음."""
        scan = ScanResult(target_path=tmp_path)
        scan.has_agents_md   = True
        scan.agents_md_lines = 200
        scan.has_linter_config = True
        scan.has_ci_gate     = True
        scan.has_gc_agent    = True
        scan.agents_md_staleness_days = 7
        scan.docs_avg_staleness_days  = 14.0

        first_total = ENGINE.score(scan).total
        for i in range(499):
            result = ENGINE.score(scan)
            assert result.total == first_total, \
                f"반복 {i+2}회: {result.total} ≠ {first_total} (결정론성 위반)"


# ── ADV-08: 인코딩 내성 ──────────────────────────────────────────────────────

class TestAdversarialEncoding:

    def test_adv08_unicode_project_path(self, tmp_path):
        """ADV-08a: 한글/이모지 포함 경로 → Scanner 예외 없이 동작."""
        proj = tmp_path / "하네스_프로젝트_🔧"
        proj.mkdir()
        (proj / "AGENTS.md").write_text("# 하네스 가이드\n에이전트 설정\n")
        scan   = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv08_unicode_filename_in_docs(self, tmp_path):
        """ADV-08b: docs/ 내 한글 파일명 → Scanner 예외 없이 처리."""
        proj = tmp_path / "project"
        docs = proj / "docs"
        docs.mkdir(parents=True)
        (proj / "AGENTS.md").write_text("# Guide\n")
        (docs / "아키텍처_설명.md").write_text("# 아키텍처\n설명\n")
        (docs / "conventions_규칙.md").write_text("# 규칙\n")
        scan   = Scanner(proj).scan()
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_adv08_emoji_in_agents_md_content(self, tmp_path):
        """ADV-08c: AGENTS.md 내용에 이모지 포함 → 라인 수 정상 계산."""
        proj = tmp_path / "emoji_proj"
        proj.mkdir()
        content = "\n".join([f"# Rule {i} 🔧🚀✅" for i in range(200)])
        (proj / "AGENTS.md").write_text(content, encoding="utf-8")
        scan = Scanner(proj).scan()
        assert scan.has_agents_md
        assert scan.agents_md_lines > 0
