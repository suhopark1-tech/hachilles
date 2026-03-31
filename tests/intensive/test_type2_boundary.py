"""Type-2: Boundary Value Analysis (경계값 분석)

각 진단 항목의 경계값에서 점수 전이(score transition)가 정확히 이루어지는지 검증한다.
동등 분할(equivalence partitioning) + 경계값 분석(BVA) 기법을 결합한다.

검증 대상:
  BVA-CE01: AGENTS.md 라인 수 경계 (0, 1, 599, 600, 1199, 1200줄)
  BVA-CE02: docs/ 항목 수 경계 (0, 1, 2, 3개)
  BVA-EM01: AGENTS.md 신선도 경계 (13, 14, 29, 30일)
  BVA-EM02: docs/ 신선도 경계 (29, 30, 59, 60일)
  BVA-EM05: bare suppress 비율 경계 (0.099, 0.1, 0.299, 0.3)
  BVA-GRADE: 등급 전이 경계 (39/40, 59/60, 74/75, 89/90)
  BVA-AC05: 의존성 위반 건수 경계 (0, 1, 4, 5)
  BVA-EM03: 무효 참조 건수 경계 (0, 1, 2, 3)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.auditors.constraint_auditor import ConstraintAuditor
from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.auditors.entropy_auditor import EntropyAuditor
from hachilles.models.scan_result import ScanResult
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()
CTX = ContextAuditor()
CON = ConstraintAuditor()
ENT = EntropyAuditor()


def _base_scan(tmp_path: Path) -> ScanResult:
    """최소한의 기본 ScanResult — 각 테스트에서 특정 필드만 변경."""
    scan = ScanResult(target_path=tmp_path)
    scan.has_agents_md = True
    scan.has_docs_dir = True
    scan.docs_files = [tmp_path / "docs" / "arch.md"]
    return scan


# ─────────────────────────────────────────────────────────
# BVA-CE01: AGENTS.md 라인 수
# ─────────────────────────────────────────────────────────

class TestBvaCe01AgentsMdLines:
    """CE-01 경계: 0 / 1~599(정상) / 600~1199(경고) / 1200+(감점)"""

    @pytest.mark.parametrize("lines,expected_score,expected_passed", [
        (0,    5, False),   # 빈 파일 → 절반
        (1,   10, True),    # 최소 1줄 → 만점
        (599, 10, True),    # 경고 직전 → 만점
        (600, 10, True),    # 경고 경계 → 만점(경고만)
        (1199, 10, True),   # 감점 직전 → 만점(경고만)
        (1200,  5, False),  # 감점 경계 → 절반
        (5000,  5, False),  # 극단값 → 절반
    ])
    def test_ce01_lines_boundary(self, tmp_path, lines, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.agents_md_lines = lines
        item = CTX._audit_ce01(scan)
        assert item.score == expected_score, (
            f"lines={lines}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed, (
            f"lines={lines}: passed={item.passed}, 기대={expected_passed}"
        )


# ─────────────────────────────────────────────────────────
# BVA-CE02: docs/ 항목 수
# ─────────────────────────────────────────────────────────

class TestBvaCe02DocsStructure:
    """CE-02 경계: 0개→2점, 1개→4점, 2개→7점, 3개→10점"""

    @pytest.mark.parametrize("arch,conv,adr,expected_score,expected_passed", [
        (False, False, False,  2, False),  # 0/3
        (True,  False, False,  4, False),  # 1/3
        (True,  True,  False,  7, False),  # 2/3
        (True,  True,  True,  10, True),   # 3/3
    ])
    def test_ce02_docs_score_map(
        self, tmp_path, arch, conv, adr, expected_score, expected_passed
    ):
        scan = _base_scan(tmp_path)
        scan.has_architecture_md = arch
        scan.has_conventions_md = conv
        scan.has_adr_dir = adr
        item = CTX._audit_ce02(scan)
        assert item.score == expected_score
        assert item.passed == expected_passed


# ─────────────────────────────────────────────────────────
# BVA-EM01: AGENTS.md 신선도 (일 수 경계)
# ─────────────────────────────────────────────────────────

class TestBvaEm01AgentsStaleness:
    """EM-01 경계: 0~13일→6pts / 14~29일→3pts(warn) / 30일+→0pts"""

    @pytest.mark.parametrize("days,expected_score,expected_passed", [
        (0,   6, True),   # 최신
        (13,  6, True),   # 경고 직전
        (14,  3, True),   # warn 경계 (passed=True 유지)
        (29,  3, True),   # 실패 직전 (warn)
        (30,  0, False),  # 실패 경계
        (365, 0, False),  # 극단값
    ])
    def test_em01_staleness_boundary(self, tmp_path, days, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.agents_md_staleness_days = days
        item = ENT._audit_em01(scan)
        assert item.score == expected_score, (
            f"days={days}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed, (
            f"days={days}: passed={item.passed}, 기대={expected_passed}"
        )


# ─────────────────────────────────────────────────────────
# BVA-EM02: docs/ 평균 신선도
# ─────────────────────────────────────────────────────────

class TestBvaEm02DocsStaleness:
    """EM-02 경계: 0~29일→4pts / 30~59일→2pts(warn) / 60일+→0pts"""

    @pytest.mark.parametrize("avg_days,expected_score,expected_passed", [
        (0.0,  4, True),
        (29.9, 4, True),
        (30.0, 2, True),   # warn 경계
        (59.9, 2, True),   # 실패 직전
        (60.0, 0, False),  # 실패 경계
        (180.0, 0, False),
    ])
    def test_em02_docs_staleness_boundary(self, tmp_path, avg_days, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.docs_avg_staleness_days = avg_days
        item = ENT._audit_em02(scan)
        assert item.score == expected_score, (
            f"avg={avg_days}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed


# ─────────────────────────────────────────────────────────
# BVA-EM05: Bare Suppress 비율
# ─────────────────────────────────────────────────────────

class TestBvaEm05SuppressRatio:
    """EM-05 경계: <0.1→5pts / 0.1~<0.3→2pts(warn) / 0.3+→0pts"""

    @pytest.mark.parametrize("ratio,expected_score,expected_passed", [
        (0.0,   5, True),
        (0.099, 5, True),   # warn 직전
        (0.1,   2, False),  # warn 경계 → passed=False
        (0.299, 2, False),
        (0.3,   0, False),  # 실패 경계
        (1.0,   0, False),
    ])
    def test_em05_suppress_ratio_boundary(self, tmp_path, ratio, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.bare_lint_suppression_ratio = ratio
        item = ENT._audit_em05(scan)
        assert item.score == expected_score, (
            f"ratio={ratio}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed


# ─────────────────────────────────────────────────────────
# BVA-GRADE: 등급 전이 경계값
# ─────────────────────────────────────────────────────────

class TestBvaGradeBoundary:
    """등급 전이: D→C at 40, C→B at 60, B→A at 75, A→S at 90"""

    @pytest.mark.parametrize("total,expected_grade", [
        (0,   "D"),
        (39,  "D"),
        (40,  "C"),   # D→C 전이
        (59,  "C"),
        (60,  "B"),   # C→B 전이
        (74,  "B"),
        (75,  "A"),   # B→A 전이
        (89,  "A"),
        (90,  "S"),   # A→S 전이
        (100, "S"),
    ])
    def test_grade_transition(self, total, expected_grade):
        grade, _ = ScoreEngine._determine_grade(total)
        assert grade == expected_grade, f"total={total}: grade={grade}, 기대={expected_grade}"

    def test_all_possible_total_scores_have_valid_grade(self):
        """0~100 모든 정수 총점에 대해 유효한 등급이 반환되어야 한다."""
        valid_grades = {"S", "A", "B", "C", "D"}
        for total in range(101):
            grade, label = ScoreEngine._determine_grade(total)
            assert grade in valid_grades, f"total={total}: 유효하지 않은 등급 {grade}"
            assert label, f"total={total}: 빈 등급 레이블"


# ─────────────────────────────────────────────────────────
# BVA-AC05: 의존성 위반 건수
# ─────────────────────────────────────────────────────────

class TestBvaAc05DependencyViolations:
    """AC-05: 0건→6pts / 1~4건→3pts(warn) / 5건+→0pts"""

    @pytest.mark.parametrize("violations,expected_score,expected_passed", [
        (0, 6, True),
        (1, 3, False),   # warn 경계
        (4, 3, False),
        (5, 0, False),   # 실패 경계
        (20, 0, False),
    ])
    def test_ac05_violations_boundary(self, tmp_path, violations, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.dependency_violations = violations
        item = CON._audit_ac05(scan)
        assert item.score == expected_score, (
            f"violations={violations}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed


# ─────────────────────────────────────────────────────────
# BVA-EM03: AGENTS.md 무효 참조 건수
# ─────────────────────────────────────────────────────────

class TestBvaEm03InvalidRefs:
    """EM-03: 0건→5pts / 1~2건→2pts(warn) / 3건+→0pts"""

    @pytest.mark.parametrize("n_refs,expected_score,expected_passed", [
        (0, 5, True),
        (1, 2, False),   # warn 경계
        (2, 2, False),
        (3, 0, False),   # 실패 경계
        (10, 0, False),
    ])
    def test_em03_invalid_refs_boundary(self, tmp_path, n_refs, expected_score, expected_passed):
        scan = _base_scan(tmp_path)
        scan.invalid_agents_refs = [f"bad_ref_{i}" for i in range(n_refs)]
        item = ENT._audit_em03(scan)
        assert item.score == expected_score, (
            f"n_refs={n_refs}: score={item.score}, 기대={expected_score}"
        )
        assert item.passed == expected_passed
