# Copyright 2026 Park Sung Hoon (박성훈) <suhopark1@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HAchilles AST 의존성 분석기 (Phase 2: AC-05 강화).

Python 소스를 AST로 파싱하여 import 그래프를 재구성하고
순환 의존성 및 레이어 경계 위반을 탐지한다.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

# HAchilles 레이어 순서 (낮은 인덱스 = 하위 레이어)
# 하위 레이어가 상위 레이어를 import하면 위반
LAYER_ORDER = [
    "models",        # 0 - 최하위
    "scanner",       # 1
    "auditors",      # 2
    "score",         # 3
    "prescriptions", # 4
    "report",        # 5
    "cli",           # 6 - 최상위
]


def build_import_graph(src_root: Path) -> dict[str, list[str]]:
    """src/ 아래의 모든 Python 파일을 AST로 파싱하여 import 그래프를 반환한다.

    반환값: {모듈경로: [import하는 hachilles 모듈명 목록]}
    예: {"hachilles.scanner.scanner": ["hachilles.models.scan_result"]}
    """
    graph: dict[str, list[str]] = defaultdict(list)

    py_files = list(src_root.rglob("*.py"))

    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, OSError):
            continue

        # 모듈 경로 계산 (src/ 기준 상대 경로 → 점 표기)
        try:
            rel = py_file.relative_to(src_root)
            module_parts = list(rel.with_suffix("").parts)
            if module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]
            module_name = ".".join(module_parts)
        except ValueError:
            continue

        if not module_name.startswith("hachilles"):
            continue

        # import 구문 추출
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("hachilles"):
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("hachilles"):
                    imports.append(node.module)
                elif node.level > 0:
                    # 상대 import: 현재 패키지 기준으로 절대 경로로 변환
                    parts = module_name.split(".")
                    base_parts = parts[:-node.level] if node.level <= len(parts) else parts[:1]
                    if node.module:
                        abs_module = ".".join(base_parts) + "." + node.module
                    else:
                        abs_module = ".".join(base_parts)
                    if abs_module.startswith("hachilles"):
                        imports.append(abs_module)

        graph[module_name] = list(set(imports))

    return dict(graph)


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DFS 기반 순환 의존성 탐지. 발견된 사이클 목록 반환."""
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in graph and neighbor not in visited:
                continue
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # 사이클 발견: path에서 neighbor 위치부터 추출
                cycle_start = path.index(neighbor) if neighbor in path else 0
                cycle = path[cycle_start:] + [neighbor]
                # 최소 표현으로 정규화 (알파벳 첫 원소 기준)
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in cycles:
                    cycles.append(normalized)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def find_layer_violations(
    graph: dict[str, list[str]]
) -> list[tuple[str, str]]:
    """레이어 경계 위반 탐지.

    반환값: [(위반자_모듈, 피위반자_모듈), ...]
    예: [("hachilles.models.scan_result", "hachilles.scanner.scanner")]
    하위 레이어(models)가 상위 레이어(scanner)를 import하는 경우.
    """
    violations: list[tuple[str, str]] = []

    def get_layer_index(module: str) -> int:
        for i, layer in enumerate(LAYER_ORDER):
            if f"hachilles.{layer}" in module or module == f"hachilles.{layer}":
                return i
        return -1  # hachilles 레이어가 아닌 경우 (표준 라이브러리 등)

    for module, imports in graph.items():
        src_layer = get_layer_index(module)
        if src_layer < 0:
            continue
        for imp in imports:
            dst_layer = get_layer_index(imp)
            if dst_layer < 0:
                continue
            # 하위 레이어(src)가 상위 레이어(dst)를 import: 위반
            if src_layer < dst_layer:
                violations.append((module, imp))

    return violations


def analyze(src_root: Path) -> tuple[
    dict[str, list[str]],   # import_graph
    list[list[str]],         # cycles
    list[tuple[str, str]],   # layer_violations
]:
    """전체 AST 분석 실행. (graph, cycles, violations) 반환."""
    graph = build_import_graph(src_root)
    cycles = find_cycles(graph)
    violations = find_layer_violations(graph)
    return graph, cycles, violations
