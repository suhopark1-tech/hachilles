"""세 Auditor의 계약 테스트 — AuditorContractTest 자동 적용.

각 클래스는 AuditorContractTest를 상속해 계약 검증 테스트 전체를 자동 실행한다.
추가로 기둥 특유의 검증(pillar 값 등)을 오버라이드/추가한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.auditors.constraint_auditor import ConstraintAuditor
from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.auditors.entropy_auditor import EntropyAuditor
from hachilles.models.scan_result import Pillar, ScanResult
from tests.auditors.contract import AuditorContractTest

# ── 픽스처 헬퍼 ──────────────────────────────────────────────────────────────

def _make_full_context_scan(tmp_path: Path) -> ScanResult:
    """ContextAuditor 모든 항목 통과 스캔."""
    scan = ScanResult(target_path=tmp_path)
    scan.has_agents_md = True
    scan.agents_md_path = tmp_path / "AGENTS.md"
    scan.agents_md_lines = 300
    scan.has_docs_dir = True
    scan.has_architecture_md = True
    scan.has_conventions_md = True
    scan.has_adr_dir = True
    scan.has_session_bridge = True
    scan.session_bridge_path = tmp_path / "claude-progress.txt"
    scan.has_feature_list = True
    return scan


def _make_full_constraint_scan(tmp_path: Path) -> ScanResult:
    """ConstraintAuditor 모든 항목 통과 스캔."""
    scan = ScanResult(target_path=tmp_path)
    scan.has_linter_config = True
    scan.linter_config_path = tmp_path / "pyproject.toml"
    scan.has_pre_commit = True
    scan.has_ci_gate = True
    scan.has_forbidden_patterns = True
    scan.dependency_violations = 0
    return scan


def _make_full_entropy_scan(tmp_path: Path) -> ScanResult:
    """EntropyAuditor 모든 항목 통과 스캔 (git N/A → 만점 처리)."""
    scan = ScanResult(target_path=tmp_path)
    scan.has_agents_md = True
    scan.agents_md_path = tmp_path / "AGENTS.md"
    scan.has_docs_dir = True
    scan.docs_files = [tmp_path / "docs" / "architecture.md"]
    # git 없음 → staleness = None → N/A 만점 처리
    scan.agents_md_staleness_days = None
    scan.docs_avg_staleness_days = None
    scan.invalid_agents_refs = []
    scan.has_gc_agent = True
    scan.bare_lint_suppression_ratio = 0.0
    return scan


# ── ContextAuditor 계약 테스트 ────────────────────────────────────────────────

class TestContextAuditorContract(AuditorContractTest):
    """ContextAuditor 계약 자동 검증 (16개 테스트 상속)."""

    @pytest.fixture
    def auditor(self):
        return ContextAuditor()

    @pytest.fixture
    def empty_scan(self, tmp_path):
        return ScanResult(target_path=tmp_path)

    @pytest.fixture
    def full_scan(self, tmp_path):
        return _make_full_context_scan(tmp_path)

    # 기둥 특유 검증
    def test_pillar(self, auditor):
        assert auditor.pillar == Pillar.CONTEXT

    def test_full_score_is_40(self, auditor):
        assert auditor.full_score == 40

    def test_item_codes_are_ce_series(self, auditor):
        assert auditor.item_codes == ["CE-01", "CE-02", "CE-03", "CE-04", "CE-05"]


# ── ConstraintAuditor 계약 테스트 ─────────────────────────────────────────────

class TestConstraintAuditorContract(AuditorContractTest):
    """ConstraintAuditor 계약 자동 검증 (16개 테스트 상속)."""

    @pytest.fixture
    def auditor(self):
        return ConstraintAuditor()

    @pytest.fixture
    def empty_scan(self, tmp_path):
        return ScanResult(target_path=tmp_path)

    @pytest.fixture
    def full_scan(self, tmp_path):
        return _make_full_constraint_scan(tmp_path)

    # 기둥 특유 검증
    def test_pillar(self, auditor):
        assert auditor.pillar == Pillar.CONSTRAINT

    def test_full_score_is_35(self, auditor):
        assert auditor.full_score == 35

    def test_item_codes_are_ac_series(self, auditor):
        assert auditor.item_codes == ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05"]


# ── EntropyAuditor 계약 테스트 ────────────────────────────────────────────────

class TestEntropyAuditorContract(AuditorContractTest):
    """EntropyAuditor 계약 자동 검증 (16개 테스트 상속)."""

    @pytest.fixture
    def auditor(self):
        return EntropyAuditor()

    @pytest.fixture
    def empty_scan(self, tmp_path):
        return ScanResult(target_path=tmp_path)

    @pytest.fixture
    def full_scan(self, tmp_path):
        return _make_full_entropy_scan(tmp_path)

    # 기둥 특유 검증
    def test_pillar(self, auditor):
        assert auditor.pillar == Pillar.ENTROPY

    def test_full_score_is_25(self, auditor):
        assert auditor.full_score == 25

    def test_item_codes_are_em_series(self, auditor):
        assert auditor.item_codes == ["EM-01", "EM-02", "EM-03", "EM-04", "EM-05"]


# ── 시스템 레벨: 세 Auditor 합산 검증 ───────────────────────────────────────

class TestAuditorSystemContract:
    """세 Auditor를 시스템으로 볼 때의 계약 검증."""

    @pytest.fixture
    def all_auditors(self):
        return [ContextAuditor(), ConstraintAuditor(), EntropyAuditor()]

    def test_total_full_score_is_100(self, all_auditors):
        """세 Auditor의 full_score 합계가 정확히 100이어야 한다."""
        total = sum(a.full_score for a in all_auditors)
        assert total == 100, (
            f"세 Auditor full_score 합 = {total} (100이어야 함)\n"
            + "\n".join(
                f"  {a.__class__.__name__}: {a.full_score}"
                for a in all_auditors
            )
        )

    def test_all_pillars_covered(self, all_auditors):
        """세 Auditor가 세 기둥을 각각 담당해야 한다."""
        pillars = {a.pillar for a in all_auditors}
        assert pillars == {Pillar.CONTEXT, Pillar.CONSTRAINT, Pillar.ENTROPY}

    def test_no_duplicate_item_codes(self, all_auditors):
        """모든 Auditor의 item_codes에 중복이 없어야 한다."""
        all_codes: list[str] = []
        for a in all_auditors:
            all_codes.extend(a.item_codes)
        assert len(all_codes) == len(set(all_codes)), (
            f"전체 item_codes에 중복: {sorted(all_codes)}"
        )

    def test_total_item_count_is_15(self, all_auditors):
        """전체 진단 항목은 15개여야 한다 (CE-01~05, AC-01~05, EM-01~05)."""
        total = sum(len(a.item_codes) for a in all_auditors)
        assert total == 15, f"총 진단 항목 수 = {total} (15여야 함)"

    def test_pillars_match_code_prefixes(self, all_auditors):
        """Auditor의 pillar와 item_codes 접두사가 일치해야 한다."""
        prefix_map = {
            Pillar.CONTEXT:    "CE",
            Pillar.CONSTRAINT: "AC",
            Pillar.ENTROPY:    "EM",
        }
        for auditor in all_auditors:
            expected_prefix = prefix_map[auditor.pillar]
            for code in auditor.item_codes:
                assert code.startswith(expected_prefix), (
                    f"{auditor.__class__.__name__}: "
                    f"코드 '{code}'의 접두사가 '{expected_prefix}'이어야 함"
                )
