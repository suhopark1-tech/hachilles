"""Phase 2: AC-05 AST 의존성 분석기 테스트."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from hachilles.scanner.ast_analyzer import (
    LAYER_ORDER,
    analyze,
    build_import_graph,
    find_cycles,
    find_layer_violations,
)

# ── 픽스처 ─────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_src(tmp_path: Path) -> Path:
    """hachilles 패키지 형식의 임시 src 디렉터리."""
    src = tmp_path / "src"
    src.mkdir()
    return src


def _make_module(src: Path, rel_path: str, content: str) -> Path:
    """src 아래에 Python 모듈 파일을 생성한다."""
    target = src / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content), encoding="utf-8")
    return target


# ── build_import_graph 테스트 ─────────────────────────────────────────────────

class TestBuildImportGraph:

    def test_simple_absolute_import(self, tmp_src: Path) -> None:
        """절대 import를 올바르게 추출한다."""
        _make_module(tmp_src, "hachilles/scanner/scanner.py", """
            from hachilles.models.scan_result import ScanResult
        """)
        graph = build_import_graph(tmp_src)
        assert "hachilles.scanner.scanner" in graph
        assert "hachilles.models.scan_result" in graph["hachilles.scanner.scanner"]

    def test_multiple_imports(self, tmp_src: Path) -> None:
        """여러 개의 import를 모두 추출한다."""
        _make_module(tmp_src, "hachilles/score/score_engine.py", """
            from hachilles.models.scan_result import ScanResult, AuditItem
            from hachilles.auditors.base import BaseAuditor
        """)
        graph = build_import_graph(tmp_src)
        node = "hachilles.score.score_engine"
        assert node in graph
        assert "hachilles.models.scan_result" in graph[node]
        assert "hachilles.auditors.base" in graph[node]

    def test_non_hachilles_imports_excluded(self, tmp_src: Path) -> None:
        """표준 라이브러리·외부 패키지 import는 그래프에 포함되지 않는다."""
        _make_module(tmp_src, "hachilles/scanner/scanner.py", """
            import os
            import re
            from pathlib import Path
            import click
            from hachilles.models.scan_result import ScanResult
        """)
        graph = build_import_graph(tmp_src)
        imports = graph.get("hachilles.scanner.scanner", [])
        # 표준 라이브러리/외부는 포함되지 않아야 한다
        assert "os" not in imports
        assert "click" not in imports
        # hachilles 모듈만 포함
        assert "hachilles.models.scan_result" in imports

    def test_init_file_resolves_to_package(self, tmp_src: Path) -> None:
        """__init__.py는 패키지명으로 해석된다."""
        _make_module(tmp_src, "hachilles/models/__init__.py", """
            from hachilles.models.scan_result import ScanResult
        """)
        graph = build_import_graph(tmp_src)
        assert "hachilles.models" in graph

    def test_syntax_error_file_skipped(self, tmp_src: Path) -> None:
        """구문 오류가 있는 파일은 건너뛴다."""
        _make_module(tmp_src, "hachilles/broken.py", """
            this is not valid python !!!
        """)
        # 오류 없이 실행돼야 한다
        graph = build_import_graph(tmp_src)
        assert "hachilles.broken" not in graph

    def test_empty_project_returns_empty_graph(self, tmp_src: Path) -> None:
        """Python 파일이 없으면 빈 그래프를 반환한다."""
        graph = build_import_graph(tmp_src)
        assert graph == {}


# ── find_cycles 테스트 ────────────────────────────────────────────────────────

class TestFindCycles:

    def test_no_cycles_in_dag(self) -> None:
        """DAG(방향성 비순환 그래프)에서는 사이클이 없다."""
        graph = {
            "hachilles.models": [],
            "hachilles.scanner": ["hachilles.models"],
            "hachilles.auditors": ["hachilles.scanner", "hachilles.models"],
        }
        cycles = find_cycles(graph)
        assert cycles == []

    def test_direct_cycle_detected(self) -> None:
        """A→B→A 직접 순환을 탐지한다."""
        graph = {
            "hachilles.scanner": ["hachilles.auditors"],
            "hachilles.auditors": ["hachilles.scanner"],
        }
        cycles = find_cycles(graph)
        assert len(cycles) >= 1

    def test_indirect_cycle_detected(self) -> None:
        """A→B→C→A 간접 순환을 탐지한다."""
        graph = {
            "hachilles.a": ["hachilles.b"],
            "hachilles.b": ["hachilles.c"],
            "hachilles.c": ["hachilles.a"],
        }
        cycles = find_cycles(graph)
        assert len(cycles) >= 1

    def test_empty_graph_no_cycles(self) -> None:
        """빈 그래프에서는 사이클이 없다."""
        assert find_cycles({}) == []

    def test_self_loop_detected(self) -> None:
        """자기 자신을 import하는 순환을 탐지한다."""
        graph = {"hachilles.models": ["hachilles.models"]}
        cycles = find_cycles(graph)
        assert len(cycles) >= 1


# ── find_layer_violations 테스트 ─────────────────────────────────────────────

class TestFindLayerViolations:

    def test_correct_direction_no_violation(self) -> None:
        """올바른 방향(상위→하위)은 위반이 아니다."""
        graph = {
            "hachilles.scanner.scanner": ["hachilles.models.scan_result"],
            "hachilles.auditors.base": ["hachilles.models.scan_result", "hachilles.scanner.scanner"],
        }
        violations = find_layer_violations(graph)
        assert violations == []

    def test_reverse_direction_is_violation(self) -> None:
        """models가 scanner를 import하면 위반이다."""
        graph = {
            "hachilles.models.scan_result": ["hachilles.scanner.scanner"],  # 위반!
        }
        violations = find_layer_violations(graph)
        assert len(violations) >= 1
        assert ("hachilles.models.scan_result", "hachilles.scanner.scanner") in violations

    def test_auditors_importing_cli_is_violation(self) -> None:
        """auditors가 cli를 import하면 위반이다."""
        graph = {
            "hachilles.auditors.base": ["hachilles.cli"],  # 위반!
        }
        violations = find_layer_violations(graph)
        assert len(violations) >= 1

    def test_cli_importing_everything_is_ok(self) -> None:
        """cli(최상위)가 모든 하위를 import하면 위반이 아니다."""
        graph = {
            "hachilles.cli": [
                "hachilles.models.scan_result",
                "hachilles.scanner.scanner",
                "hachilles.auditors.base",
                "hachilles.score.score_engine",
                "hachilles.prescriptions",
                "hachilles.report",
            ],
        }
        violations = find_layer_violations(graph)
        assert violations == []

    def test_non_hachilles_imports_ignored(self) -> None:
        """hachilles 레이어가 아닌 모듈은 위반 검사에서 제외된다."""
        graph = {
            "hachilles.models.scan_result": ["os", "re", "pathlib", "click"],
        }
        violations = find_layer_violations(graph)
        assert violations == []


# ── analyze 통합 테스트 ──────────────────────────────────────────────────────

class TestAnalyze:

    def test_real_hachilles_src_no_violations(self) -> None:
        """HAchilles 자체 소스는 순환·레이어 위반이 없어야 한다."""
        src_root = Path(__file__).parent.parent / "src"
        graph, cycles, violations = analyze(src_root)

        assert len(graph) > 0, "import 그래프가 비어 있다"
        assert cycles == [], f"순환 의존성 발견: {cycles}"
        assert violations == [], f"레이어 위반 발견: {violations}"

    def test_layer_order_completeness(self) -> None:
        """LAYER_ORDER가 7개 레이어를 모두 포함한다."""
        expected = {"models", "scanner", "auditors", "score", "prescriptions", "report", "cli"}
        assert set(LAYER_ORDER) == expected

    def test_analyze_returns_tuple(self, tmp_src: Path) -> None:
        """analyze()는 (graph, cycles, violations) 튜플을 반환한다."""
        result = analyze(tmp_src)
        assert isinstance(result, tuple)
        assert len(result) == 3
        graph, cycles, violations = result
        assert isinstance(graph, dict)
        assert isinstance(cycles, list)
        assert isinstance(violations, list)
