"""Type-D: Regression & Snapshot Testing (회귀·스냅샷 테스트)

알려진 입력 패턴에 대해 점수 스냅샷을 고정하여,
코드 변경 시 의도하지 않은 점수 변화를 즉시 감지한다.

검증 목표:
  REG-01: 5가지 '표준 프로젝트 유형' 스냅샷 — 점수 변화 시 즉시 탐지
  REG-02: HAchilles 자가 진단 점수 — 자기 자신이 B등급(60점) 이상 유지
  REG-03: 특정 항목 수정 시 델타 회귀 — CE-01 배점이 10점인지 확인
  REG-04: 점수 공식 불변식 — 가중치 합 == 100 불변
  REG-05: 등급 경계값 고정 — S(90), A(75), B(60), C(40), D(0)가 변경되지 않음
  REG-06: 처방 필드 초기값 — 스캐너가 prescription을 채우지 않음
  REG-07: AuditItem 코드 명명 규칙 — CE/AC/EM 접두사 고정
  REG-08: 샘플 픽스처 프로젝트 점수 안정성
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.auditors.constraint_auditor import ConstraintAuditor
from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.auditors.entropy_auditor import EntropyAuditor
from hachilles.models.scan_result import Pillar, ScanResult
from hachilles.scanner.scanner import Scanner
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()
_PROJ_ROOT   = Path(__file__).parent.parent.parent
_FIXTURES    = _PROJ_ROOT / "tests" / "fixtures" / "sample_projects"


# ── REG-01: 표준 프로젝트 유형별 점수 스냅샷 ─────────────────────────────────

class TestRegressionSnapshots:
    """각 표준 프로젝트 유형의 점수 스냅샷.

    이 테스트들은 '현재 올바른 값'을 고정한다.
    채점 로직이 의도적으로 변경되면 이 스냅샷도 함께 업데이트해야 한다.
    """

    def _make(self, tmp_path: Path, **kwargs) -> ScanResult:
        scan = ScanResult(target_path=tmp_path)
        for k, v in kwargs.items():
            setattr(scan, k, v)
        return scan

    def test_reg01_perfect_project_scores_100(self, tmp_path):
        """REG-01-PERFECT: 완벽한 프로젝트 → 100점."""
        scan = self._make(
            tmp_path,
            has_agents_md=True, agents_md_lines=300,
            has_docs_dir=True, has_architecture_md=True,
            has_conventions_md=True, has_adr_dir=True,
            docs_files=[tmp_path / "docs" / "a.md"],
            has_session_bridge=True, has_feature_list=True,
            has_linter_config=True, has_pre_commit=True,
            has_ci_gate=True, has_forbidden_patterns=True,
            dependency_violations=0,
            agents_md_staleness_days=7, docs_avg_staleness_days=14.0,
            invalid_agents_refs=[], has_gc_agent=True,
            bare_lint_suppression_ratio=0.0,
        )
        result = ENGINE.score(scan)
        assert result.total == 100, f"완벽한 프로젝트 점수: {result.total} (기대: 100)"
        assert result.grade == "S"

    def test_reg01_zero_project_scores_low(self, tmp_path):
        """REG-01-ZERO: 모든 필드 기본값 프로젝트 → 낮은 점수."""
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        # 기본값 프로젝트는 EM에서 git 없음 N/A 처리로 EM 일부 점수 가능
        assert result.total <= 20, f"기본값 프로젝트 점수: {result.total} (기대: ≤20)"
        assert result.grade == "D"

    def test_reg01_context_only_project(self, tmp_path):
        """REG-01-CE: Context 완벽 + AC·EM 없음 → CE 40점.

        [설계 특성]
        AC-05(의존성 위반 = 0)는 린터/CI 설정 없이도 통과(6점)된다.
        따라서 constraint_score는 0이 아닌 6이 된다.
        """
        scan = self._make(
            tmp_path,
            has_agents_md=True, agents_md_lines=200,
            has_docs_dir=True, has_architecture_md=True,
            has_conventions_md=True, has_adr_dir=True,
            docs_files=[tmp_path / "docs" / "a.md"],
            has_session_bridge=True, has_feature_list=True,
        )
        result = ENGINE.score(scan)
        assert result.context_score == 40, f"CE 완벽 시 context_score={result.context_score}"
        # AC-05는 dependency_violations=0이면 통과 → 최소 6점
        assert result.constraint_score >= 6, \
            f"AC 없음 시 constraint_score={result.constraint_score} (AC-05 통과로 최소 6점)"
        assert result.constraint_score <= 14, \
            f"AC 없음 시 constraint_score={result.constraint_score} (린터/CI/pre-commit 없으므로 14점 이하)"

    def test_reg01_constraint_only_project(self, tmp_path):
        """REG-01-AC: Constraint 완벽 + CE·EM 없음 → AC 35점."""
        scan = self._make(
            tmp_path,
            has_linter_config=True, has_pre_commit=True,
            has_ci_gate=True, has_forbidden_patterns=True,
            dependency_violations=0,
        )
        result = ENGINE.score(scan)
        assert result.constraint_score == 35, f"AC 완벽 시 constraint_score={result.constraint_score}"

    def test_reg01_entropy_only_project(self, tmp_path):
        """REG-01-EM: Entropy 완벽 + CE·AC 없음 → EM 25점."""
        scan = self._make(
            tmp_path,
            has_agents_md=True,
            agents_md_staleness_days=5, docs_avg_staleness_days=10.0,
            invalid_agents_refs=[], has_gc_agent=True,
            bare_lint_suppression_ratio=0.0,
            has_docs_dir=True, docs_files=[tmp_path / "docs" / "a.md"],
        )
        result = ENGINE.score(scan)
        assert result.entropy_score == 25, f"EM 완벽 시 entropy_score={result.entropy_score}"


# ── REG-02: HAchilles 자가 진단 회귀 ────────────────────────────────────────

class TestRegressionSelfAudit:

    def test_reg02_hachilles_b_grade_or_above(self):
        """REG-02: HAchilles 자체 스캔 → 항상 B등급(60점) 이상 유지."""
        scan   = Scanner(_PROJ_ROOT).scan()
        result = ENGINE.score(scan)
        assert result.total >= 60, (
            f"HAchilles 자가 진단 {result.total}점({result.grade}) — B등급 미달!\n"
            f"  CE={result.context_score}/40, AC={result.constraint_score}/35, "
            f"EM={result.entropy_score}/25\n"
            f"  실패 항목: {[i.code for i in result.critical_items]}"
        )

    def test_reg02_hachilles_passes_min_ac_gates(self):
        """REG-02b: HAchilles 자체 스캔 → 린터+CI Gate 최소 통과."""
        scan = Scanner(_PROJ_ROOT).scan()
        assert scan.has_linter_config, "HAchilles 자신에 린터 설정 없음"
        assert scan.has_ci_gate,       "HAchilles 자신에 CI Gate 없음"

    def test_reg02_hachilles_has_agents_md(self):
        """REG-02c: HAchilles 자체 스캔 → AGENTS.md 존재."""
        scan = Scanner(_PROJ_ROOT).scan()
        assert scan.has_agents_md, "HAchilles 자신에 AGENTS.md 없음"


# ── REG-03: 특정 항목 배점 고정 ─────────────────────────────────────────────

class TestRegressionItemScores:
    """개별 AuditItem 배점이 변경되지 않았는지 고정."""

    def _perfect(self, tmp_path: Path) -> ScanResult:
        scan = ScanResult(target_path=tmp_path)
        scan.has_agents_md            = True
        scan.agents_md_lines          = 200
        scan.has_docs_dir             = True
        scan.has_architecture_md      = True
        scan.has_conventions_md       = True
        scan.has_adr_dir              = True
        scan.docs_files               = [tmp_path / "docs" / "a.md"]
        scan.has_session_bridge       = True
        scan.has_feature_list         = True
        scan.has_linter_config        = True
        scan.has_pre_commit           = True
        scan.has_ci_gate              = True
        scan.has_forbidden_patterns   = True
        scan.dependency_violations    = 0
        scan.agents_md_staleness_days = 5
        scan.docs_avg_staleness_days  = 10.0
        scan.invalid_agents_refs      = []
        scan.has_gc_agent             = True
        scan.bare_lint_suppression_ratio = 0.0
        return scan

    @pytest.mark.parametrize("code,expected_full", [
        ("CE-01", 10), ("CE-02", 10), ("CE-03", 8), ("CE-04", 6), ("CE-05", 6),
        ("AC-01",  8), ("AC-02",  7), ("AC-03", 8), ("AC-04", 6), ("AC-05", 6),
        ("EM-01",  6), ("EM-02",  4), ("EM-03", 5), ("EM-04", 5), ("EM-05", 5),
    ])
    def test_reg03_item_full_score_snapshot(self, tmp_path, code, expected_full):
        """REG-03: 각 AuditItem의 full_score가 스냅샷과 일치."""
        scan = self._perfect(tmp_path)
        result = ENGINE.score(scan)
        all_items = (
            result.context_result.items
            + result.constraint_result.items
            + result.entropy_result.items
        )
        item = next((i for i in all_items if i.code == code), None)
        assert item is not None, f"{code} 항목 없음"
        assert item.full_score == expected_full, \
            f"{code}: full_score={item.full_score} (기대={expected_full})"

    def test_reg03_total_full_score_is_100(self, tmp_path):
        """REG-03b: 모든 full_score 합산 == 100."""
        scan   = self._perfect(tmp_path)
        result = ENGINE.score(scan)
        total_full = sum(
            item.full_score
            for r in [result.context_result, result.constraint_result, result.entropy_result]
            for item in r.items
        )
        assert total_full == 100, f"전체 만점 합산: {total_full} (기대: 100)"


# ── REG-04: 점수 공식 불변식 ─────────────────────────────────────────────────

class TestRegressionFormula:

    def test_reg04_auditor_full_score_sum_100(self):
        """REG-04: 세 Auditor의 full_score 합 == 100 (불변식)."""
        total = sum([
            ContextAuditor().full_score,
            ConstraintAuditor().full_score,
            EntropyAuditor().full_score,
        ])
        assert total == 100

    def test_reg04_pillar_values_unchanged(self):
        """REG-04b: Pillar 열거형 값이 변경되지 않음."""
        assert Pillar.CONTEXT.value    == "context"
        assert Pillar.CONSTRAINT.value == "constraint"
        assert Pillar.ENTROPY.value    == "entropy"

    def test_reg04_context_full_score_is_40(self):
        """REG-04c: Context 기둥 만점 == 40."""
        assert ContextAuditor().full_score == 40

    def test_reg04_constraint_full_score_is_35(self):
        """REG-04d: Constraint 기둥 만점 == 35."""
        assert ConstraintAuditor().full_score == 35

    def test_reg04_entropy_full_score_is_25(self):
        """REG-04e: Entropy 기둥 만점 == 25."""
        assert EntropyAuditor().full_score == 25


# ── REG-05: 등급 경계값 고정 ─────────────────────────────────────────────────

class TestRegressionGradeBoundaries:
    """등급 경계가 S(90), A(75), B(60), C(40), D(0)로 고정돼 있는지 확인."""

    def _score_for_total(self, tmp_path: Path, target_total: int):
        """target_total에 맞는 HarnessScore 반환."""
        # perfect 기준에서 CE 일부만 조합해 원하는 점수 근처를 만들기 어려우므로
        # ScoreEngine 내부 등급 판정 함수를 직접 테스트
        from hachilles.score.score_engine import _GRADE_BOUNDS
        for threshold, grade, label in _GRADE_BOUNDS:
            if target_total >= threshold:
                return grade, label
        return "D", ""

    @pytest.mark.parametrize("total,expected_grade", [
        (100, "S"), (90, "S"), (89, "A"), (75, "A"),
        (74, "B"),  (60, "B"), (59, "C"), (40, "C"),
        (39, "D"),  (0,  "D"),
    ])
    def test_reg05_grade_boundary_fixed(self, tmp_path, total, expected_grade):
        """REG-05: 각 등급 경계점에서 올바른 등급 반환."""
        grade, _ = self._score_for_total(tmp_path, total)
        assert grade == expected_grade, \
            f"total={total}: grade={grade} (기대={expected_grade})"


# ── REG-06: 처방 필드 초기값 ─────────────────────────────────────────────────

class TestRegressionPrescription:

    def test_reg06_auditor_does_not_fill_prescription(self, tmp_path):
        """REG-06: Auditor는 prescription 필드를 채우지 않음 (처방 엔진 전담).

        이 규칙이 깨지면 처방 엔진 레이어 분리 원칙이 위반된 것이다.
        """
        scan = ScanResult(target_path=tmp_path)
        scan.has_agents_md = True
        scan.agents_md_lines = 200
        result = ENGINE.score(scan)
        for r in [result.context_result, result.constraint_result, result.entropy_result]:
            for item in r.items:
                assert item.prescription == "", \
                    f"{item.code}.prescription = '{item.prescription}' — Auditor가 처방을 채움"


# ── REG-07: AuditItem 코드 명명 규칙 ─────────────────────────────────────────

class TestRegressionNamingConvention:

    def test_reg07_item_codes_follow_pattern(self, tmp_path):
        """REG-07: 모든 AuditItem.code가 CE/AC/EM 접두사 + 숫자 형식."""
        import re
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        pattern = re.compile(r"^(CE|AC|EM)-\d{2}$")
        for r in [result.context_result, result.constraint_result, result.entropy_result]:
            for item in r.items:
                assert pattern.match(item.code), \
                    f"잘못된 코드 형식: '{item.code}'"

    def test_reg07_ce_codes_are_ce01_to_ce05(self, tmp_path):
        """REG-07b: Context 항목 코드가 CE-01~CE-05."""
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        ce_codes = [i.code for i in result.context_result.items]
        assert ce_codes == ["CE-01", "CE-02", "CE-03", "CE-04", "CE-05"]

    def test_reg07_ac_codes_are_ac01_to_ac05(self, tmp_path):
        """REG-07c: Constraint 항목 코드가 AC-01~AC-05."""
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        ac_codes = [i.code for i in result.constraint_result.items]
        assert ac_codes == ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05"]

    def test_reg07_em_codes_are_em01_to_em05(self, tmp_path):
        """REG-07d: Entropy 항목 코드가 EM-01~EM-05."""
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        em_codes = [i.code for i in result.entropy_result.items]
        assert em_codes == ["EM-01", "EM-02", "EM-03", "EM-04", "EM-05"]

    def test_reg07_total_15_items(self, tmp_path):
        """REG-07e: 전체 AuditItem 개수 == 15."""
        scan   = ScanResult(target_path=tmp_path)
        result = ENGINE.score(scan)
        all_items = (
            result.context_result.items
            + result.constraint_result.items
            + result.entropy_result.items
        )
        assert len(all_items) == 15, f"총 항목 수: {len(all_items)} (기대: 15)"


# ── REG-08: 샘플 픽스처 프로젝트 점수 안정성 ─────────────────────────────────

class TestRegressionFixtureProjects:

    def test_reg08_minimal_project_known_range(self):
        """REG-08a: minimal 픽스처 → B등급 범위 (CE 완벽 + AC 일부 + EM 일부).

        minimal 픽스처는 AGENTS.md, docs/, architecture.md, conventions.md를 갖추고 있어
        CE 40점 만점을 받는다. AC는 의존성 위반 없음으로 AC-05만 통과한다.
        스냅샷: 60~75점 범위의 B 또는 A 등급.
        """
        minimal = _FIXTURES / "minimal"
        if not minimal.exists():
            pytest.skip("minimal 픽스처 없음")
        scan   = Scanner(minimal).scan()
        result = ENGINE.score(scan)
        assert 55 <= result.total <= 80, \
            f"minimal 프로젝트 점수: {result.total} (기대: 55~80)\n" \
            f"CE={result.context_score}/40, AC={result.constraint_score}/35, EM={result.entropy_score}/25"

    def test_reg08_no_harness_project_d_or_c_grade(self):
        """REG-08b: no_harness 픽스처 → D 또는 C 등급."""
        no_harness = _FIXTURES / "no_harness"
        if not no_harness.exists():
            pytest.skip("no_harness 픽스처 없음")
        scan   = Scanner(no_harness).scan()
        result = ENGINE.score(scan)
        assert result.grade in {"D", "C"}, \
            f"no_harness 프로젝트 등급: {result.grade} (기대: D 또는 C)"
