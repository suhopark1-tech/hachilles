"""ScoreEngine 기본 테스트 — STEP 2-4에서 tests/score/test_score_engine.py 로 이전됨.

이 파일은 하위 호환성을 위해 유지된다.
실제 포괄 테스트는 tests/score/test_score_engine.py 에 있다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.models.scan_result import RiskLevel, ScanResult
from hachilles.score import ScoreEngine


@pytest.fixture
def engine() -> ScoreEngine:
    return ScoreEngine()


@pytest.fixture
def empty_scan(tmp_path: Path) -> ScanResult:
    return ScanResult(target_path=tmp_path)


@pytest.fixture
def full_scan(tmp_path: Path) -> ScanResult:
    """모든 항목 통과하는 이상적인 ScanResult."""
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
    scan.has_linter_config = True
    scan.linter_config_path = tmp_path / "pyproject.toml"
    scan.has_pre_commit = True
    scan.has_ci_gate = True
    scan.has_forbidden_patterns = True
    scan.dependency_violations = 0
    scan.docs_files = [tmp_path / "docs" / "architecture.md"]
    scan.agents_md_staleness_days = None
    scan.docs_avg_staleness_days = None
    scan.invalid_agents_refs = []
    scan.has_gc_agent = True
    scan.bare_lint_suppression_ratio = 0.0
    return scan


class TestScoreEngine:
    def test_empty_project_low_score(self, engine, empty_scan):
        result = engine.score(empty_scan)
        assert result.total < 30

    def test_full_project_max_score(self, engine, full_scan):
        result = engine.score(full_scan)
        assert result.total == 100

    def test_grade_s_at_90(self, engine, full_scan):
        result = engine.score(full_scan)
        assert result.grade == "S"

    def test_grade_d_for_empty(self, engine, empty_scan):
        result = engine.score(empty_scan)
        assert result.grade in {"D", "C"}

    def test_total_is_clamped(self, engine, full_scan):
        result = engine.score(full_scan)
        assert 0 <= result.total <= 100

    def test_pattern_risks_count(self, engine, empty_scan):
        result = engine.score(empty_scan)
        assert len(result.pattern_risks) == 5

    def test_context_drift_high_for_empty(self, engine, empty_scan):
        result = engine.score(empty_scan)
        cd = next(pr for pr in result.pattern_risks if pr.pattern == "Context Drift")
        assert cd.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}

    def test_context_drift_ok_for_full(self, engine, full_scan):
        result = engine.score(full_scan)
        cd = next(pr for pr in result.pattern_risks if pr.pattern == "Context Drift")
        assert cd.risk == RiskLevel.OK
