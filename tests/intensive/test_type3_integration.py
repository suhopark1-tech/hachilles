"""Type-3: Integration / E2E Testing

실제 파일시스템을 대상으로 Scanner → Auditor → ScoreEngine 전 파이프라인을
통합 테스트한다. Scanner API: Scanner(target_path).scan() → ScanResult.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hachilles.models.scan_result import ScanResult
from hachilles.scanner.scanner import Scanner
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()

_PROJ_ROOT = Path(__file__).parent.parent.parent
_FIXTURES_DIR = _PROJ_ROOT / "tests" / "fixtures" / "sample_projects"


class TestIntegrationFullPipeline:

    def test_int01_scanner_detects_real_files(self):
        """INT-01: hachilles 자신 스캔 시 ScanResult가 실제 파일시스템을 반영한다."""
        scan = Scanner(_PROJ_ROOT).scan()
        assert scan.target_path == _PROJ_ROOT
        assert isinstance(scan.has_agents_md, bool)
        assert isinstance(scan.docs_files, list)
        assert isinstance(scan.scan_errors, list)
        assert "python" in scan.tech_stack

    def test_int02_hachilles_self_scan_b_grade_or_above(self):
        """INT-02: hachilles 자신 스캔 → B등급(60점) 이상."""
        scan = Scanner(_PROJ_ROOT).scan()
        result = ENGINE.score(scan)
        assert result.total >= 60, (
            f"hachilles 자가 진단 {result.total}pts ({result.grade}) B등급 미달\n"
            f"  CE={result.context_score}/40, AC={result.constraint_score}/35, "
            f"EM={result.entropy_score}/25\n"
            f"  실패: {[i.code for i in result.critical_items]}"
        )
        assert result.grade in {"S", "A", "B"}

    def test_int03_minimal_project_ce_score_positive(self):
        """INT-03: minimal 샘플 → CE 점수 > 0."""
        minimal_path = _FIXTURES_DIR / "minimal"
        if not minimal_path.exists():
            pytest.skip("minimal 픽스처 없음")
        scan = Scanner(minimal_path).scan()
        result = ENGINE.score(scan)
        assert result.context_score > 0

    def test_int04_no_harness_project_very_low_score(self):
        """INT-04: no_harness 샘플 → 낮은 점수."""
        no_harness_path = _FIXTURES_DIR / "no_harness"
        if not no_harness_path.exists():
            pytest.skip("no_harness 픽스처 없음")
        scan = Scanner(no_harness_path).scan()
        result = ENGINE.score(scan)
        assert result.total < 30, f"no_harness 점수 {result.total}pts (30 미만 기대)"

    def test_int05_empty_dir_no_exception(self, tmp_path):
        """INT-05: 빈 디렉토리도 파이프라인이 오류 없이 완주."""
        result = ENGINE.score(Scanner(tmp_path).scan())
        assert 0 <= result.total <= 100

    def test_int06_scan_errors_do_not_break_scoring(self, tmp_path):
        """INT-06: scan_errors가 있어도 ScoreEngine 정상 동작."""
        scan = ScanResult(target_path=tmp_path)
        scan.scan_errors = ["테스트용 스캔 오류"]
        result = ENGINE.score(scan)
        assert 0 <= result.total <= 100

    def test_int07_synthetic_a_grade_project(self, tmp_path):
        """INT-07: A등급 요건을 갖춘 합성 프로젝트 → 75점 이상."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Architecture")
        (docs / "conventions.md").write_text("# Conventions")
        (docs / "forbidden.md").write_text("# Forbidden")
        (docs / "decisions").mkdir()
        (docs / "decisions" / "001.md").write_text("# ADR-001")
        (tmp_path / "AGENTS.md").write_text("# Agent Guide\n" * 50)
        (tmp_path / "claude-progress.txt").write_text("progress")
        (tmp_path / "feature_list.json").write_text('{"features": ["scan"]}')
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length=88")
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
        ci = tmp_path / ".github" / "workflows"
        ci.mkdir(parents=True)
        (ci / "ci.yml").write_text("on: push\njobs:\n  test:\n    runs-on: ubuntu-latest")

        scan = Scanner(tmp_path).scan()
        result = ENGINE.score(scan)

        assert result.total >= 75, (
            f"합성 프로젝트 {result.total}pts A등급 미달\n"
            f"  CE={result.context_score}/40, AC={result.constraint_score}/35, "
            f"EM={result.entropy_score}/25\n"
            f"  실패: {[(i.code, i.detail[:50]) for i in result.critical_items]}"
        )

    def test_int08_manual_full_scan_100pts(self, tmp_path):
        """INT-08: 수동 perfect ScanResult → 100점."""
        scan = ScanResult(target_path=tmp_path)
        scan.has_agents_md = True
        scan.agents_md_lines = 300
        scan.has_docs_dir = True
        scan.has_architecture_md = True
        scan.has_conventions_md = True
        scan.has_adr_dir = True
        scan.has_session_bridge = True
        scan.has_feature_list = True
        scan.has_linter_config = True
        scan.has_pre_commit = True
        scan.has_ci_gate = True
        scan.has_forbidden_patterns = True
        scan.dependency_violations = 0
        scan.docs_files = [tmp_path / "docs" / "arch.md"]
        scan.agents_md_staleness_days = None
        scan.docs_avg_staleness_days = None
        scan.invalid_agents_refs = []
        scan.has_gc_agent = True
        scan.bare_lint_suppression_ratio = 0.0
        assert ENGINE.score(scan).total == 100

    def test_int09_pipeline_output_json_serializable(self):
        """INT-09: 파이프라인 전체 결과가 JSON 직렬화 가능해야 한다."""
        scan = Scanner(_PROJ_ROOT).scan()
        result = ENGINE.score(scan)
        payload = json.dumps(result.to_dict(), ensure_ascii=False)
        data = json.loads(payload)
        assert data["total"] == result.total
        assert data["grade"] == result.grade
        assert len(data["pattern_risks"]) == 5
