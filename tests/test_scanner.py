"""Scanner 통합 테스트 — 실제 픽스처 디렉토리를 스캔한다."""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.scanner import Scanner

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_projects"


class TestScannerMinimal:
    """minimal/ 픽스처: 대부분의 항목 통과 기대."""

    @pytest.fixture
    def scan(self):
        target = FIXTURES_DIR / "minimal"
        return Scanner(target).scan()

    def test_has_agents_md(self, scan):
        assert scan.has_agents_md

    def test_agents_md_lines_positive(self, scan):
        assert scan.agents_md_lines > 0

    def test_has_session_bridge(self, scan):
        assert scan.has_session_bridge

    def test_has_feature_list(self, scan):
        assert scan.has_feature_list

    def test_has_docs_dir(self, scan):
        assert scan.has_docs_dir

    def test_has_architecture_md(self, scan):
        assert scan.has_architecture_md

    def test_has_conventions_md(self, scan):
        assert scan.has_conventions_md

    def test_has_adr_dir(self, scan):
        assert scan.has_adr_dir


class TestScannerNoHarness:
    """no_harness/ 픽스처: 대부분의 항목 실패 기대."""

    @pytest.fixture
    def scan(self):
        target = FIXTURES_DIR / "no_harness"
        return Scanner(target).scan()

    def test_no_agents_md(self, scan):
        assert not scan.has_agents_md

    def test_no_session_bridge(self, scan):
        assert not scan.has_session_bridge

    def test_no_feature_list(self, scan):
        assert not scan.has_feature_list


class TestScannerEdgeCases:
    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            Scanner(Path("/nonexistent/path"))

    def test_file_path_raises(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(NotADirectoryError):
            Scanner(f)
