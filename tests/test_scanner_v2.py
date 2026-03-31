"""Scanner v2 강화 테스트 — 버그 수정·새 기능 검증.

테스트 범위:
  - _EXCLUDE_DIRS: 노이즈 디렉토리 제외 동작
  - _read_safe: 파일 크기 상한 처리
  - _check_agents_refs: 공통 식별자 필터, 메모리 안전
  - _measure_bare_suppressions: [EXCEPTION] 위치 무관 처리
  - _scan_constraint: AC-04 AGENTS.md 섹션 탐지
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.scanner.scanner import _MAX_FILE_BYTES, Scanner

# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_scanner(tmp_path: Path) -> Scanner:
    return Scanner(tmp_path)


# ── _EXCLUDE_DIRS 검증 ───────────────────────────────────────────────────────

class TestExcludeDirs:
    def test_node_modules_excluded(self, tmp_path):
        """node_modules 하위 파일은 rglob 결과에 포함되지 않아야 한다."""
        node_m = tmp_path / "node_modules" / "some_lib"
        node_m.mkdir(parents=True)
        (node_m / "index.py").write_text("class FakeClass: pass")

        # 실제 소스 파일
        (tmp_path / "main.py").write_text("class RealClass: pass")

        scanner = make_scanner(tmp_path)
        results = scanner._rglob_safe("*.py")

        names = [f.name for f in results]
        assert "index.py" not in names
        assert "main.py" in names

    def test_pycache_excluded(self, tmp_path):
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module.cpython-311.pyc").write_bytes(b"bytecode")
        (tmp_path / "module.py").write_text("x = 1")

        scanner = make_scanner(tmp_path)
        results = scanner._rglob_safe("*.py")
        assert not any("__pycache__" in str(f) for f in results)

    def test_git_dir_excluded(self, tmp_path):
        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True)
        (git_hooks / "pre-commit").write_text("#!/bin/bash")
        (tmp_path / "app.py").write_text("pass")

        scanner = make_scanner(tmp_path)
        results = scanner._rglob_safe("*.py")
        assert all(".git" not in str(f) for f in results)

    def test_venv_excluded(self, tmp_path):
        venv_lib = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        venv_lib.mkdir(parents=True)
        (venv_lib / "requests.py").write_text("def get(): pass")
        (tmp_path / "app.py").write_text("from requests import get")

        scanner = make_scanner(tmp_path)
        results = scanner._rglob_safe("*.py")
        assert all(".venv" not in str(f) for f in results)
        assert any(f.name == "app.py" for f in results)


# ── _read_safe 검증 ───────────────────────────────────────────────────────────

class TestReadSafe:
    def test_normal_file_reads_fully(self, tmp_path):
        f = tmp_path / "small.py"
        f.write_text("x = 1\ny = 2\n")
        scanner = make_scanner(tmp_path)
        content = scanner._read_safe(f)
        assert "x = 1" in content
        assert "y = 2" in content

    def test_oversized_file_truncated(self, tmp_path):
        f = tmp_path / "huge.py"
        # _MAX_FILE_BYTES + 1KB 크기 파일 생성
        f.write_bytes(b"x" * (_MAX_FILE_BYTES + 1024))
        scanner = make_scanner(tmp_path)
        content = scanner._read_safe(f)
        # 읽힌 내용 길이가 상한을 초과하지 않아야 함
        assert len(content.encode("utf-8")) <= _MAX_FILE_BYTES

    def test_missing_file_returns_empty(self, tmp_path):
        scanner = make_scanner(tmp_path)
        content = scanner._read_safe(tmp_path / "nonexistent.py")
        assert content == ""


# ── _measure_bare_suppressions 검증 ──────────────────────────────────────────

class TestBareSuppression:
    def _run(self, tmp_path: Path, code: str, filename: str = "app.py") -> float:
        (tmp_path / filename).write_text(code)
        return make_scanner(tmp_path)._measure_bare_suppressions()

    def test_no_suppression_returns_zero(self, tmp_path):
        ratio = self._run(tmp_path, "x = 1\ny = 2\n")
        assert ratio == 0.0

    def test_bare_noqa_counted(self, tmp_path):
        code = "import os  # noqa\n"
        ratio = self._run(tmp_path, code)
        assert ratio == 1.0  # 1 bare / 1 total

    def test_exception_before_noqa_not_counted(self, tmp_path):
        """[EXCEPTION]이 noqa 앞에 있어도 bare로 집계되지 않아야 한다 (버그 수정 검증)."""
        code = "import os  # [EXCEPTION] 마이그레이션용 # noqa: E501\n"
        ratio = self._run(tmp_path, code)
        assert ratio == 0.0  # exception 있으므로 bare 아님

    def test_exception_after_noqa_not_counted(self, tmp_path):
        """[EXCEPTION]이 noqa 뒤에 있어도 bare로 집계되지 않아야 한다."""
        code = "import os  # noqa: E501 [EXCEPTION] 이유\n"
        ratio = self._run(tmp_path, code)
        assert ratio == 0.0

    def test_mixed_bare_and_valid(self, tmp_path):
        code = (
            "import os  # noqa\n"                    # bare → 집계
            "import sys  # [EXCEPTION] reason # noqa: E501\n"  # 이유 있음 → not bare
            "x = 1\n"                                # suppress 없음
        )
        ratio = self._run(tmp_path, code)
        # 1 bare / 2 total = 0.5
        assert ratio == pytest.approx(0.5)

    def test_type_ignore_bare(self, tmp_path):
        code = "x: int = 'hello'  # type: ignore\n"
        ratio = self._run(tmp_path, code)
        assert ratio == 1.0

    def test_type_ignore_with_exception(self, tmp_path):
        code = "x: int = 'hello'  # [EXCEPTION] 외부 API 반환값 # type: ignore\n"
        ratio = self._run(tmp_path, code)
        assert ratio == 0.0

    def test_node_modules_excluded_from_count(self, tmp_path):
        """node_modules 내 파일은 suppress 집계에 포함되지 않아야 한다."""
        nm = tmp_path / "node_modules" / "lib"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("var x = 1  // eslint-disable-next-line\n")
        (tmp_path / "app.py").write_text("x = 1\n")  # suppress 없음
        ratio = make_scanner(tmp_path)._measure_bare_suppressions()
        assert ratio == 0.0


# ── _check_agents_refs 검증 ───────────────────────────────────────────────────

class TestAgentsRefs:
    def test_valid_ref_not_flagged(self, tmp_path):
        """코드베이스에 실제로 정의된 클래스는 invalid로 나오지 않아야 한다."""
        (tmp_path / "AGENTS.md").write_text("Use `MyScanner` for scanning.\n")
        (tmp_path / "scanner.py").write_text("class MyScanner:\n    pass\n")
        scanner = make_scanner(tmp_path)
        invalid = scanner._check_agents_refs(tmp_path / "AGENTS.md")
        assert "MyScanner" not in invalid

    def test_missing_ref_flagged(self, tmp_path):
        """코드베이스에 없는 식별자는 invalid에 포함돼야 한다."""
        (tmp_path / "AGENTS.md").write_text("Use `GhostClass` for something.\n")
        (tmp_path / "app.py").write_text("class RealClass: pass\n")
        scanner = make_scanner(tmp_path)
        invalid = scanner._check_agents_refs(tmp_path / "AGENTS.md")
        assert "GhostClass" in invalid

    def test_common_identifiers_filtered(self, tmp_path):
        """Path, list, None 등 공통 식별자는 오탐되지 않아야 한다."""
        (tmp_path / "AGENTS.md").write_text(
            "Use `Path` and `list` and `dict` for data handling.\n"
            "Return `None` when not found.\n"
        )
        (tmp_path / "app.py").write_text("x = 1\n")
        scanner = make_scanner(tmp_path)
        invalid = scanner._check_agents_refs(tmp_path / "AGENTS.md")
        # Path, list, dict, None은 공통 식별자이므로 invalid에 포함되면 안 됨
        assert "Path" not in invalid
        assert "list" not in invalid
        assert "None" not in invalid

    def test_empty_agents_md_returns_empty(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n모든 규칙을 따르세요.\n")
        scanner = make_scanner(tmp_path)
        invalid = scanner._check_agents_refs(tmp_path / "AGENTS.md")
        assert invalid == []


# ── AC-04 AGENTS.md 섹션 탐지 검증 ────────────────────────────────────────────

class TestAC04Detection:
    def test_forbidden_md_detected(self, tmp_path):
        """docs/forbidden.md가 있으면 has_forbidden_patterns=True."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "forbidden.md").write_text("# 금지 패턴\n- bare noqa\n")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_forbidden_patterns

    def test_agents_md_forbidden_section_detected(self, tmp_path):
        """docs/forbidden.md 없어도 AGENTS.md에 ## 금지 섹션이 있으면 True."""
        (tmp_path / "AGENTS.md").write_text(
            "# AGENTS\n\n## 금지 패턴\n- bare except\n- any()\n"
        )
        scan = make_scanner(tmp_path).scan()
        assert scan.has_forbidden_patterns

    def test_no_forbidden_anywhere_false(self, tmp_path):
        """금지 패턴 관련 파일/섹션이 전혀 없으면 False."""
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n## 레이어 구조\n...")
        scan = make_scanner(tmp_path).scan()
        assert not scan.has_forbidden_patterns


# ── GC Agent 탐지 (버그 수정 검증) ────────────────────────────────────────────

class TestGCAgentDetection:
    """BUG-1 수정 검증: substring 오탐 방지 및 JS/TS 탐지 추가."""

    def test_prefix_gc_detected(self, tmp_path):
        """'gc_'로 시작하는 파일은 GC 에이전트로 탐지돼야 한다."""
        (tmp_path / "gc_agent.py").write_text("def run(): pass")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_gc_agent

    def test_suffix_gc_detected(self, tmp_path):
        """'_gc.py'로 끝나는 파일은 GC 에이전트로 탐지돼야 한다."""
        (tmp_path / "doc_gc.py").write_text("def run(): pass")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_gc_agent

    def test_keyword_garbage_collect_detected(self, tmp_path):
        """'garbage_collect' 키워드 포함 파일은 GC 에이전트로 탐지돼야 한다."""
        (tmp_path / "garbage_collect_docs.py").write_text("def run(): pass")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_gc_agent

    def test_false_positive_run_gc_not_detected(self, tmp_path):
        """BUG-1: 'run_gc.py'는 GC 에이전트가 아니어야 한다 (중간 substring)."""
        # 'gc_' prefix가 아니고, '_gc.py' suffix도 아닌 파일
        (tmp_path / "run_gc_test.py").write_text("def test(): pass")
        scan = make_scanner(tmp_path).scan()
        assert not scan.has_gc_agent, (
            "run_gc_test.py를 GC 에이전트로 오탐하면 안 됨 (BUG-1 재발)"
        )

    def test_js_gc_agent_detected(self, tmp_path):
        """JS 프로젝트의 GC 에이전트도 탐지돼야 한다."""
        (tmp_path / "gc_cleanup.js").write_text("function run() {}")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_gc_agent

    def test_ts_gc_agent_detected(self, tmp_path):
        """TypeScript GC 에이전트도 탐지돼야 한다."""
        (tmp_path / "doc_gc.ts").write_text("export function run() {}")
        scan = make_scanner(tmp_path).scan()
        assert scan.has_gc_agent

    def test_no_gc_agent_returns_false(self, tmp_path):
        """GC 에이전트 관련 파일이 없으면 False여야 한다."""
        (tmp_path / "main.py").write_text("def main(): pass")
        scan = make_scanner(tmp_path).scan()
        assert not scan.has_gc_agent
