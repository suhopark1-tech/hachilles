"""ContextAuditor 단위 테스트.

각 CE 항목의 passed=True / False 케이스를 모두 검증한다.
ScanResult를 직접 구성하여 파일시스템 의존성 없이 테스트.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.models.scan_result import Pillar, ScanResult


@pytest.fixture
def auditor() -> ContextAuditor:
    return ContextAuditor()


@pytest.fixture
def base_scan(tmp_path: Path) -> ScanResult:
    """모든 CE 항목이 기본값(False)인 ScanResult."""
    return ScanResult(target_path=tmp_path)


# ── CE-01 ────────────────────────────────────────────────────────────────────

class TestCE01:
    def test_no_agents_md_fails(self, auditor, base_scan):
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-01")
        assert not item.passed
        assert item.score == 0

    def test_agents_md_normal_passes(self, auditor, base_scan, tmp_path):
        base_scan.has_agents_md = True
        base_scan.agents_md_path = tmp_path / "AGENTS.md"
        base_scan.agents_md_lines = 200
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-01")
        assert item.passed
        assert item.score == item.full_score

    def test_agents_md_too_long_partial_score(self, auditor, base_scan, tmp_path):
        base_scan.has_agents_md = True
        base_scan.agents_md_path = tmp_path / "AGENTS.md"
        base_scan.agents_md_lines = 1500  # 1200 이상 → 절반 점수
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-01")
        assert not item.passed
        assert item.score == item.full_score // 2

    def test_agents_md_empty_partial_score(self, auditor, base_scan, tmp_path):
        base_scan.has_agents_md = True
        base_scan.agents_md_path = tmp_path / "AGENTS.md"
        base_scan.agents_md_lines = 0
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-01")
        assert not item.passed


# ── CE-02 ────────────────────────────────────────────────────────────────────

class TestCE02:
    def test_no_docs_dir_fails(self, auditor, base_scan):
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-02")
        assert not item.passed
        assert item.score == 0

    def test_docs_full_passes(self, auditor, base_scan):
        base_scan.has_docs_dir = True
        base_scan.has_architecture_md = True
        base_scan.has_conventions_md = True
        base_scan.has_adr_dir = True
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-02")
        assert item.passed
        assert item.score == item.full_score

    def test_docs_partial_lower_score(self, auditor, base_scan):
        base_scan.has_docs_dir = True
        base_scan.has_architecture_md = True
        base_scan.has_conventions_md = False
        base_scan.has_adr_dir = False
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-02")
        assert not item.passed
        assert 0 < item.score < item.full_score


# ── CE-03 ────────────────────────────────────────────────────────────────────

class TestCE03:
    def test_no_session_bridge_fails(self, auditor, base_scan):
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-03")
        assert not item.passed

    def test_session_bridge_passes(self, auditor, base_scan, tmp_path):
        base_scan.has_session_bridge = True
        base_scan.session_bridge_path = tmp_path / "claude-progress.txt"
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-03")
        assert item.passed
        assert item.score == item.full_score


# ── CE-04 ────────────────────────────────────────────────────────────────────

class TestCE04:
    def test_no_feature_list_fails(self, auditor, base_scan):
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-04")
        assert not item.passed

    def test_feature_list_passes(self, auditor, base_scan):
        base_scan.has_feature_list = True
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-04")
        assert item.passed


# ── CE-05 ────────────────────────────────────────────────────────────────────

class TestCE05:
    def test_no_agents_md_fails(self, auditor, base_scan):
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-05")
        assert not item.passed

    def test_both_docs_passes(self, auditor, base_scan):
        base_scan.has_agents_md = True
        base_scan.has_architecture_md = True
        base_scan.has_conventions_md = True
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-05")
        assert item.passed

    def test_missing_one_doc_fails(self, auditor, base_scan):
        base_scan.has_agents_md = True
        base_scan.has_architecture_md = True
        base_scan.has_conventions_md = False
        result = auditor.audit(base_scan)
        item = next(i for i in result.items if i.code == "CE-05")
        assert not item.passed


# ── 기둥 메타 ────────────────────────────────────────────────────────────────

class TestContextAuditorMeta:
    def test_pillar_is_context(self, auditor):
        assert auditor.pillar == Pillar.CONTEXT

    def test_full_score_is_40(self, auditor, base_scan):
        """Context 기둥 만점 = 40."""
        result = auditor.audit(base_scan)
        assert result.full_score == 40

    def test_perfect_score(self, auditor, tmp_path):
        """모든 항목 통과 시 40점."""
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
        result = auditor.audit(scan)
        assert result.score == 40
