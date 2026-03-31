"""Type-E: Architecture Layer Integrity Testing (아키텍처 레이어 무결성 테스트)

AST(추상 구문 트리) 기반으로 실제 소스 코드의 import 방향을 정적 분석하여
하네스 엔지니어링의 핵심 원칙인 '단방향 의존성'이 유지되는지 검증한다.

레이어 순서 (models → cli 방향으로만 import 허용):
  models → scanner → auditors → score → prescriptions → report → cli

검증 목표:
  ARCH-01: 단방향 의존성 — 역방향 import 완전 금지
  ARCH-02: 순환 의존성 없음 — 어떤 모듈도 자기 자신에게 돌아오지 않음
  ARCH-03: models 격리 — models는 다른 hachilles 모듈을 import하지 않음
  ARCH-04: Auditor → Score 격리 — auditors는 score/cli를 import하지 않음
  ARCH-05: CLI 최상위 — cli는 외부에서 import되지 않음 (다른 모듈이 cli를 쓰지 않음)
  ARCH-06: 외부 의존성 허용 범위 — 각 레이어의 허용 외부 패키지 준수
  ARCH-07: __init__.py 공개 API 일관성 — 각 패키지 __init__이 올바른 것만 노출
  ARCH-08: 파일 구조 고정 — 핵심 파일 목록이 변경되지 않음
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ── 상수 ─────────────────────────────────────────────────────────────────────

_SRC = Path(__file__).parent.parent.parent / "src" / "hachilles"

# 레이어 순서 (인덱스가 낮을수록 하위 레이어)
_LAYERS = ["models", "scanner", "auditors", "score", "prescriptions", "report", "cli"]
_LAYER_RANK = {layer: i for i, layer in enumerate(_LAYERS)}

# 외부 의존성 허용 목록 (레이어별)
_ALLOWED_EXTERNAL: dict[str, set[str]] = {
    "models":       set(),                                   # 순수 Python 표준 라이브러리만
    "scanner":      {"pathspec", "gitpython", "git"},        # 파일 파싱
    "auditors":     set(),                                   # 오직 내부 모듈
    "score":        set(),                                   # 오직 내부 모듈
    "prescriptions": set(),
    "report":       {"jinja2"},                              # HTML 템플릿
    "cli":          {"click", "rich", "uvicorn"},             # CLI 프레임워크 (Phase 3: serve 명령)
}

# 허용된 표준 라이브러리 (모든 레이어에서 사용 가능)
_STDLIB = {
    "ast", "abc", "collections", "copy", "dataclasses", "datetime",
    "enum", "functools", "io", "itertools", "json", "math", "os",
    "pathlib", "re", "statistics", "subprocess", "sys", "textwrap",
    "threading", "typing", "types", "warnings", "__future__", "concurrent",
}


# ── AST 파싱 유틸 ─────────────────────────────────────────────────────────────

def _get_hachilles_imports(filepath: Path) -> list[str]:
    """파일에서 hachilles 내부 모듈 import만 추출."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("hachilles."):
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("hachilles."):
                imports.append(node.module)
            elif node.level and node.level > 0:
                # 상대 import: 현재 파일의 레이어 추론
                pass
    return imports


def _get_all_imports(filepath: Path) -> list[str]:
    """파일에서 모든 top-level import 추출 (표준 라이브러리 포함)."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.append(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.append(top)
    return imports


def _get_layer(filepath: Path) -> str | None:
    """파일의 상대 경로에서 레이어 이름 추출."""
    try:
        rel = filepath.relative_to(_SRC)
        parts = rel.parts
        if parts:
            return parts[0]
        return "root"
    except ValueError:
        return None


def _all_python_files() -> list[Path]:
    """src/hachilles/ 하위 모든 Python 파일."""
    return [
        p for p in _SRC.rglob("*.py")
        if "__pycache__" not in p.parts
    ]


# ── ARCH-01: 단방향 의존성 ────────────────────────────────────────────────────

class TestArchUnidirectionalDependency:

    def test_arch01_no_reverse_imports(self):
        """ARCH-01: 모든 Python 파일이 상위 레이어를 import하지 않음.

        models(0) ← scanner(1) ← auditors(2) ← score(3) ← ... ← cli(6)
        낮은 인덱스 레이어가 높은 인덱스 레이어를 import하면 위반.
        """
        violations = []
        for filepath in _all_python_files():
            src_layer = _get_layer(filepath)
            if src_layer not in _LAYER_RANK:
                continue
            src_rank = _LAYER_RANK[src_layer]

            for imp in _get_hachilles_imports(filepath):
                # hachilles.{layer}.{module} 형태에서 레이어 추출
                parts = imp.split(".")
                if len(parts) < 2:
                    continue
                dst_layer = parts[1]
                if dst_layer not in _LAYER_RANK:
                    continue
                dst_rank = _LAYER_RANK[dst_layer]

                # 역방향 import: 낮은 레이어가 높은 레이어를 참조
                if dst_rank > src_rank:
                    violations.append(
                        f"{filepath.relative_to(_SRC.parent.parent)}: "
                        f"{src_layer}({src_rank}) → {dst_layer}({dst_rank})"
                    )

        assert not violations, (
            f"단방향 의존성 위반 {len(violations)}건:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ── ARCH-02: 순환 의존성 없음 ────────────────────────────────────────────────

class TestArchNoCyclicDependency:

    def _build_dep_graph(self) -> dict[str, set[str]]:
        """모듈 간 의존성 그래프 구축 (레이어 단위)."""
        graph: dict[str, set[str]] = {layer: set() for layer in _LAYERS}
        for filepath in _all_python_files():
            src_layer = _get_layer(filepath)
            if src_layer not in graph:
                continue
            for imp in _get_hachilles_imports(filepath):
                parts = imp.split(".")
                if len(parts) < 2:
                    continue
                dst_layer = parts[1]
                if dst_layer in graph and dst_layer != src_layer:
                    graph[src_layer].add(dst_layer)
        return graph

    def _has_cycle(self, graph: dict[str, set[str]]) -> list[str]:
        """DFS로 순환 탐지. 순환이 있으면 경로 반환."""
        visited: set[str] = set()
        stack:   set[str] = set()
        path:    list[str] = []

        def dfs(node: str) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            path.pop()
            stack.discard(node)
            return False

        for node in graph:
            if dfs(node):
                return path[:]
        return []

    def test_arch02_no_cyclic_imports(self):
        """ARCH-02: 레이어 간 순환 의존성 없음."""
        graph = self._build_dep_graph()
        cycle = self._has_cycle(graph)
        assert not cycle, f"순환 의존성 탐지: {' → '.join(cycle)}"


# ── ARCH-03: models 격리 ─────────────────────────────────────────────────────

class TestArchModelsIsolation:

    def test_arch03_models_imports_no_hachilles(self):
        """ARCH-03: models/ 는 hachilles 내부 다른 모듈을 import하지 않음."""
        models_dir = _SRC / "models"
        violations = []
        for filepath in models_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            for imp in _get_hachilles_imports(filepath):
                parts = imp.split(".")
                if len(parts) >= 2 and parts[1] != "models":
                    violations.append(f"{filepath.name}: {imp}")
        assert not violations, \
            f"models/ 에서 내부 모듈 import {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)

    def test_arch03_models_no_external_packages(self):
        """ARCH-03b: models/ 는 표준 라이브러리 외 외부 패키지를 사용하지 않음."""
        models_dir = _SRC / "models"
        violations = []
        for filepath in models_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            for imp in _get_all_imports(filepath):
                if imp.startswith("hachilles"):
                    continue
                if imp not in _STDLIB and imp not in {"", "_"}:
                    violations.append(f"{filepath.name}: import {imp}")
        assert not violations, \
            f"models/ 에서 외부 패키지 사용 {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)


# ── ARCH-04: Auditor → Score 격리 ────────────────────────────────────────────

class TestArchAuditorIsolation:

    def test_arch04_auditors_no_score_import(self):
        """ARCH-04: auditors/ 는 score/, cli/, report/, prescriptions/ 를 import하지 않음."""
        auditors_dir = _SRC / "auditors"
        forbidden_layers = {"score", "cli", "report", "prescriptions"}
        violations = []
        for filepath in auditors_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            for imp in _get_hachilles_imports(filepath):
                parts = imp.split(".")
                if len(parts) >= 2 and parts[1] in forbidden_layers:
                    violations.append(f"{filepath.name}: {imp}")
        assert not violations, \
            f"auditors/ 에서 상위 레이어 import {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)

    def test_arch04_auditors_only_use_base_and_models(self):
        """ARCH-04b: auditors/ 의 hachilles import는 models와 scanner와 auditors.base만 허용."""
        auditors_dir = _SRC / "auditors"
        violations = []
        for filepath in auditors_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            filename = filepath.name
            if filename == "base.py":
                continue  # base.py 자체는 models만 import
            for imp in _get_hachilles_imports(filepath):
                parts = imp.split(".")
                if len(parts) < 2:
                    continue
                layer = parts[1]
                if layer not in {"models", "scanner", "auditors"}:
                    violations.append(f"{filename}: {imp}")
        assert not violations, \
            "auditors/ 에서 허용 외 레이어 import:\n" + \
            "\n".join(f"  {v}" for v in violations)


# ── ARCH-05: CLI 최상위 보장 ─────────────────────────────────────────────────

class TestArchCliTopLevel:

    def test_arch05_no_module_imports_cli(self):
        """ARCH-05: 다른 어떤 모듈도 cli.py를 import하지 않음."""
        violations = []
        for filepath in _all_python_files():
            if filepath.name == "cli.py":
                continue
            for imp in _get_hachilles_imports(filepath):
                # 정확한 매칭: 모듈명이 정확히 "cli"인 경우만 (hachilles.llm.client 등 오탐 방지)
                if imp == "hachilles.cli" or imp.endswith(".cli") or ".cli." in imp:
                    violations.append(
                        f"{filepath.relative_to(_SRC)}: {imp}"
                    )
        assert not violations, \
            f"cli 모듈을 import하는 파일 {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)


# ── ARCH-06: 외부 의존성 허용 범위 ────────────────────────────────────────────

class TestArchExternalDependencies:

    def test_arch06_auditors_no_external_packages(self):
        """ARCH-06: auditors/ 는 표준 라이브러리만 사용."""
        auditors_dir = _SRC / "auditors"
        violations = []
        for filepath in auditors_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            for imp in _get_all_imports(filepath):
                if imp.startswith("hachilles"):
                    continue
                if imp not in _STDLIB | _ALLOWED_EXTERNAL.get("auditors", set()):
                    violations.append(f"{filepath.name}: import {imp}")
        assert not violations, \
            f"auditors/ 허용 외 외부 패키지 {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)

    def test_arch06_score_no_external_packages(self):
        """ARCH-06b: score/ 는 표준 라이브러리만 사용."""
        score_dir = _SRC / "score"
        violations = []
        for filepath in score_dir.rglob("*.py"):
            if "__pycache__" in filepath.parts:
                continue
            for imp in _get_all_imports(filepath):
                if imp.startswith("hachilles"):
                    continue
                if imp not in _STDLIB | _ALLOWED_EXTERNAL.get("score", set()):
                    violations.append(f"{filepath.name}: import {imp}")
        assert not violations, \
            f"score/ 허용 외 외부 패키지 {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)

    def test_arch06_cli_only_uses_allowed_packages(self):
        """ARCH-06c: cli.py는 click과 rich만 외부 패키지로 허용."""
        cli_file = _SRC / "cli.py"
        if not cli_file.exists():
            pytest.skip("cli.py 없음")
        violations = []
        for imp in _get_all_imports(cli_file):
            if imp.startswith("hachilles"):
                continue
            allowed = _STDLIB | _ALLOWED_EXTERNAL.get("cli", set())
            if imp not in allowed and imp != "":
                violations.append(f"cli.py: import {imp}")
        assert not violations, \
            f"cli.py 허용 외 패키지 {len(violations)}건:\n" + \
            "\n".join(f"  {v}" for v in violations)


# ── ARCH-07: 공개 API 일관성 ─────────────────────────────────────────────────

class TestArchPublicApi:

    def test_arch07_score_package_exports_engine(self):
        """ARCH-07: score/__init__.py가 ScoreEngine을 올바르게 export."""
        from hachilles.score import ScoreEngine
        assert ScoreEngine is not None
        engine = ScoreEngine()
        assert hasattr(engine, "score")

    def test_arch07_models_exports_required_classes(self):
        """ARCH-07b: models/scan_result.py에서 필수 클래스 export 확인."""
        from hachilles.models.scan_result import (
            AuditItem,
            AuditResult,
            ScanResult,
        )
        assert ScanResult.__dataclass_fields__  # dataclass인지 확인
        assert AuditResult.__dataclass_fields__
        assert AuditItem.__dataclass_fields__

    def test_arch07_all_auditors_are_importable(self):
        """ARCH-07c: 세 Auditor 모두 import 가능."""
        from hachilles.auditors.base import BaseAuditor
        from hachilles.auditors.constraint_auditor import ConstraintAuditor
        from hachilles.auditors.context_auditor import ContextAuditor
        from hachilles.auditors.entropy_auditor import EntropyAuditor

        for cls in [ContextAuditor, ConstraintAuditor, EntropyAuditor]:
            assert issubclass(cls, BaseAuditor)


# ── ARCH-08: 파일 구조 고정 ──────────────────────────────────────────────────

class TestArchFileStructure:

    _REQUIRED_FILES = [
        "models/scan_result.py",
        "scanner/scanner.py",
        "auditors/base.py",
        "auditors/context_auditor.py",
        "auditors/constraint_auditor.py",
        "auditors/entropy_auditor.py",
        "score/score_engine.py",
        "score/__init__.py",
        "cli.py",
    ]

    def test_arch08_required_files_exist(self):
        """ARCH-08: 핵심 파일 목록이 모두 존재."""
        missing = []
        for rel_path in self._REQUIRED_FILES:
            full = _SRC / rel_path
            if not full.exists():
                missing.append(rel_path)
        assert not missing, \
            f"필수 파일 {len(missing)}개 없음:\n" + \
            "\n".join(f"  src/hachilles/{p}" for p in missing)

    def test_arch08_no_python_files_in_src_root(self):
        """ARCH-08b: src/hachilles/ 루트에 직속 py 파일은 cli.py와 __init__.py만.

        하위 레이어들은 반드시 패키지 디렉토리 안에 있어야 한다.
        """
        root_py_files = [
            p for p in _SRC.glob("*.py")
            if "__pycache__" not in p.parts
        ]
        allowed_root = {"cli.py", "__init__.py"}
        unexpected = [p.name for p in root_py_files if p.name not in allowed_root]
        assert not unexpected, \
            f"src/hachilles/ 루트에 예상치 않은 파일: {unexpected}"

    def test_arch08_docs_decisions_directory_exists(self):
        """ARCH-08c: docs/decisions/ (ADR 디렉토리) 존재 — CE-05 항목 충족."""
        # src/ → hachilles/ → src/ → project_root
        proj_root = _SRC.parent.parent  # src/hachilles/../../  = project root
        adr_dir = proj_root / "docs" / "decisions"
        assert adr_dir.exists(), f"docs/decisions/ 없음 (경로: {adr_dir})"
        adr_files = list(adr_dir.glob("*.md"))
        assert len(adr_files) >= 1, "docs/decisions/ 에 ADR 파일이 없음"
