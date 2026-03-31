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

"""HAchilles Scanner — 대상 프로젝트의 원시 데이터 수집.

레이어 규칙: scanner는 models만 import한다. auditors/score/cli는 import 금지.

역할:
  - 대상 프로젝트의 파일 시스템을 탐색한다.
  - 진단에 필요한 원시 데이터를 ScanResult 객체로 수집한다.
  - Auditor는 이 ScanResult만 보고 진단한다. 직접 파일에 접근하지 않는다.

설계 원칙:
  - 스캔은 순수 관찰(read-only)이다. 파일을 쓰거나 변경하지 않는다.
  - 예외는 scan_errors에 기록되고 스캔을 중단하지 않는다.
  - 대형 파일은 _MAX_FILE_BYTES 이하만 읽는다 (메모리 안전).
  - 노이즈 디렉토리(.git, node_modules 등)는 재귀 탐색에서 제외한다.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

from hachilles.models.scan_result import ScanResult

# git 히스토리 접근은 선택적 (gitpython 없어도 동작)
try:
    import git as _git
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False


# ── 설정 상수 ────────────────────────────────────────────────────────────────

# 재귀 탐색 시 무시할 디렉토리명
_EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", ".pnpm-store",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    ".venv", "venv", ".env", "env",
    "dist", "build", ".next", ".nuxt",
    "coverage", ".coverage", "htmlcov",
    "vendor", "third_party",
})

# 단일 파일 읽기 상한 (메모리 안전 — 이 이상이면 잘라 읽음)
_MAX_FILE_BYTES = 512 * 1024  # 512 KB

# AGENTS.md 참조 검사 시 무시할 공통 식별자
# (언어 키워드, 내장 함수, 매우 흔한 라이브러리 이름)
_COMMON_IDENTIFIERS: frozenset[str] = frozenset({
    # Python 키워드
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else",
    "except", "finally", "for", "from", "global", "if", "import",
    "in", "is", "lambda", "nonlocal", "not", "or", "pass",
    "raise", "return", "try", "while", "with", "yield",
    # Python 내장
    "print", "len", "range", "list", "dict", "set", "tuple",
    "str", "int", "float", "bool", "bytes", "type",
    "open", "super", "self", "cls", "args", "kwargs",
    "Exception", "ValueError", "TypeError", "KeyError",
    "FileNotFoundError", "OSError", "IOError",
    "Path", "Optional", "Union", "Any", "List", "Dict",
    "Callable", "Generator", "Iterator", "Iterable",
    # 공통 타입/패턴
    "None", "init", "main", "run", "get", "set", "add",
    # JS/TS 키워드
    "const", "let", "var", "function", "return", "import",
    "export", "default", "class", "extends", "interface",
    "Promise", "async", "await", "undefined", "null",
})

# 탐지 파일/디렉토리 이름 목록
_AGENTS_NAMES       = {"AGENTS.md", "agents.md"}
_SESSION_BRIDGE_NAMES = {
    "claude-progress.txt", "agent-progress.txt",
    ".agent-state.txt", "session_bridge.md",
}
_FEATURE_LIST_NAMES = {"feature_list.json", "features.json", "todo.json"}
_LINTER_NAMES = {
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml",
    ".pylintrc", "pylintrc", "ruff.toml", ".ruff.toml", "pyproject.toml",
}
# GC 에이전트 파일명 판별: prefix 또는 suffix 기반 (substring 오탐 방지)
# 올바른 매칭: "gc_agent.py", "doc_gc.py", "garbage_collect.py"
# 오탐 방지:  "run_gc_test.py" 같은 단어 중간 패턴 제외
_GC_AGENT_PREFIXES = {"gc_", "gc-"}              # 파일명이 이것으로 시작
_GC_AGENT_SUFFIXES = {"_gc.py", "-gc.py", "_gc.ts", "-gc.js"}  # 파일명이 이것으로 끝
_GC_AGENT_KEYWORDS = {"garbage_collect", "doc_consistency", "docs_gc", "cleanup_agent"}

_STACK_INDICATORS = {
    "python":     ["*.py", "pyproject.toml", "setup.py", "requirements.txt"],
    "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
    "javascript": ["*.js", "*.jsx", "package.json"],
    "go":         ["*.go", "go.mod"],
    "java":       ["*.java", "pom.xml", "build.gradle"],
    "rust":       ["*.rs", "Cargo.toml"],
}

# EM-05: 이유 없는 lint suppress 탐지용 정규식 (모듈 레벨 — 반복 컴파일 방지)
_SUPPRESS_RE = re.compile(
    r"#\s*noqa"             # Python noqa
    r"|#\s*type:\s*ignore"  # mypy
    r"|//\s*eslint-disable"  # JS/TS eslint
)
_EXCEPTION_RE = re.compile(r"\[EXCEPTION\]", re.IGNORECASE)
# 문자열 리터럴 제거용 — 큰따옴표/작은따옴표 내부 텍스트를 빈 문자열로 치환
_STR_LITERAL_RE = re.compile(
    r'"[^"\\]*(?:\\.[^"\\]*)*"'   # "..." 큰따옴표 문자열
    r"|'[^'\\]*(?:\\.[^'\\]*)*'"  # '...' 작은따옴표 문자열
)


class Scanner:
    """대상 프로젝트 디렉토리를 스캔하여 ScanResult를 반환한다.

    사용 예:
        scanner = Scanner(Path("/path/to/project"))
        result = scanner.scan()
    """

    def __init__(self, target: Path) -> None:
        if not target.exists():
            raise FileNotFoundError(f"대상 경로를 찾을 수 없습니다: {target}")
        if not target.is_dir():
            raise NotADirectoryError(f"디렉토리가 아닙니다: {target}")
        self.target = target.resolve()

    def scan(self) -> ScanResult:
        """전체 스캔 실행. ScanResult 반환.

        각 서브 스캔은 독립적으로 오류를 처리한다.
        하나가 실패해도 나머지는 계속 실행된다.
        """
        import datetime
        result = ScanResult(target_path=self.target)
        result.scan_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self._scan_context(result)
        self._scan_constraint(result)
        self._scan_entropy(result)
        self._detect_tech_stack(result)
        self._scan_go_java(result)
        self._scan_typescript(result)

        return result

    # ── 유틸: 안전 파일 목록 조회 ────────────────────────────────────────────

    def _rglob_safe(self, pattern: str) -> list[Path]:
        """_EXCLUDE_DIRS를 건너뛰는 안전한 재귀 파일 탐색."""
        results: list[Path] = []
        for path in self.target.rglob(pattern):
            # 경로 구성 요소 중 하나라도 제외 대상이면 스킵
            if any(part in _EXCLUDE_DIRS for part in path.parts):
                continue
            results.append(path)
        return results

    def _read_safe(self, path: Path) -> str:
        """파일을 안전하게 읽는다. _MAX_FILE_BYTES 초과 시 잘라 읽음."""
        try:
            raw = path.read_bytes()
            if len(raw) > _MAX_FILE_BYTES:
                raw = raw[:_MAX_FILE_BYTES]
            return raw.decode("utf-8", errors="replace")
        except OSError:
            return ""

    # ── Private: 컨텍스트 스캔 ───────────────────────────────────────────────

    def _scan_context(self, result: ScanResult) -> None:
        # CE-01: AGENTS.md 존재 및 라인 수
        for name in _AGENTS_NAMES:
            p = self.target / name
            if p.exists():
                result.has_agents_md = True
                result.agents_md_path = p
                content = self._read_safe(p)
                result.agents_md_lines = len(content.splitlines())
                break

        # CE-02: docs/ 디렉토리 구조
        docs_dir = self.target / "docs"
        if docs_dir.exists() and docs_dir.is_dir():
            result.has_docs_dir = True
            # docs/ 하위 .md 파일 목록 (제외 디렉토리 건너뜀)
            result.docs_files = [
                f for f in docs_dir.rglob("*.md")
                if not any(part in _EXCLUDE_DIRS for part in f.parts)
            ]
            result.has_architecture_md = any(
                f.name.lower() in {"architecture.md", "arch.md"}
                for f in result.docs_files
            )
            result.has_conventions_md = any(
                f.name.lower() in {"conventions.md", "convention.md", "coding-standards.md"}
                for f in result.docs_files
            )
            adr_dirs = {"decisions", "adr", "adrs"}
            result.has_adr_dir = any(
                (docs_dir / d).exists() for d in adr_dirs
            )

        # CE-03: 세션 브릿지 파일
        for name in _SESSION_BRIDGE_NAMES:
            p = self.target / name
            if p.exists():
                result.has_session_bridge = True
                result.session_bridge_path = p
                break

        # CE-04: feature_list.json (완료 기준 구조화)
        for name in _FEATURE_LIST_NAMES:
            if (self.target / name).exists():
                result.has_feature_list = True
                break

    # ── Private: 제약 스캔 ───────────────────────────────────────────────────

    def _scan_constraint(self, result: ScanResult) -> None:
        # AC-01: 린터 설정 파일
        for name in _LINTER_NAMES:
            p = self.target / name
            if not p.exists():
                continue
            # pyproject.toml은 [tool.ruff/pylint/flake8/black] 섹션 있을 때만 인정
            if name == "pyproject.toml":
                content = self._read_safe(p)
                if not re.search(r"\[tool\.(ruff|pylint|flake8|black)\]", content):
                    continue
            result.has_linter_config = True
            result.linter_config_path = p
            break

        # AC-02: pre-commit 설정
        result.has_pre_commit = (self.target / ".pre-commit-config.yaml").exists()

        # AC-03: CI Gate (.github/workflows/ 에 lint/test job)
        workflows_dir = self.target / ".github" / "workflows"
        if workflows_dir.exists():
            for wf in list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml")):
                content = self._read_safe(wf).lower()
                if any(kw in content for kw in ["ruff", "pylint", "eslint", "lint", "test"]):
                    result.has_ci_gate = True
                    break

        # AC-04: 금지 패턴 목록
        # 1순위: docs/forbidden.md 파일
        # 2순위: AGENTS.md 내 "금지" / "forbidden" 섹션 존재
        forbidden_doc = self.target / "docs" / "forbidden.md"
        if forbidden_doc.exists():
            result.has_forbidden_patterns = True
        elif result.has_agents_md and result.agents_md_path:
            content = self._read_safe(result.agents_md_path)
            # AGENTS.md에 금지 패턴 섹션이 있으면 부분 인정
            if re.search(r"##\s*(금지|forbidden|prohibited|금지\s*패턴)", content, re.IGNORECASE):
                result.has_forbidden_patterns = True

        # AC-05: AST 기반 의존성 분석 (Phase 2)
        try:
            from hachilles.scanner.ast_analyzer import analyze as _ast_analyze
            src_root = self.target / "src"
            if not src_root.exists():
                src_root = self.target
            graph, cycles, violations = _ast_analyze(src_root)
            result.import_graph = graph
            result.dependency_cycles = cycles
            result.layer_violations = violations
            result.dependency_violations = len(violations) + len(cycles) * 2
        except Exception as e:  # [EXCEPTION] AST 분석 실패는 비치명적
            result.scan_errors.append(f"AST 분석 실패: {e}")
            result.dependency_violations = 0

    # ── Private: 엔트로피 스캔 ───────────────────────────────────────────────

    def _scan_entropy(self, result: ScanResult) -> None:
        # EM-01, EM-02: staleness (git 히스토리 필요)
        if _GIT_AVAILABLE:
            self._measure_staleness(result)

        # EM-03: AGENTS.md 참조 유효성 검사
        if result.has_agents_md and result.agents_md_path:
            result.invalid_agents_refs = self._check_agents_refs(
                result.agents_md_path
            )

        # EM-04: GC 에이전트 스크립트
        result.has_gc_agent = self._detect_gc_agent()

        # EM-05: 이유 없는 lint suppress 비율
        result.bare_lint_suppression_ratio = self._measure_bare_suppressions()

    def _measure_staleness(self, result: ScanResult) -> None:
        """git log로 AGENTS.md와 docs/ 파일들의 마지막 수정 날짜를 측정한다."""
        try:
            import datetime
            repo = _git.Repo(self.target, search_parent_directories=True)

            def days_since_last_commit(path: Path) -> int | None:
                try:
                    commits = list(repo.iter_commits(paths=str(path), max_count=1))
                    if not commits:
                        return None
                    last = commits[0].committed_datetime
                    delta = datetime.datetime.now(datetime.timezone.utc) - last
                    return delta.days
                except Exception:  # [EXCEPTION] git 오류는 개별 파일 단위로 무시
                    return None

            if result.agents_md_path:
                result.agents_md_staleness_days = days_since_last_commit(
                    result.agents_md_path
                )

            if result.docs_files:
                staleness_list = [
                    d for f in result.docs_files
                    if (d := days_since_last_commit(f)) is not None
                ]
                if staleness_list:
                    result.docs_avg_staleness_days = (
                        sum(staleness_list) / len(staleness_list)
                    )

        except Exception as e:  # [EXCEPTION] git 저장소 없거나 git 자체 오류
            result.scan_errors.append(f"staleness 측정 실패 (git 필요): {e}")

    def _check_agents_refs(self, agents_md_path: Path) -> list[str]:
        """AGENTS.md 내 `Identifier` 형태 참조가 코드베이스에 존재하는지 확인.

        알고리즘:
          1. AGENTS.md에서 backtick으로 감싼 식별자를 추출한다.
          2. 공통 키워드/내장 식별자를 제외한다.
          3. 소스 파일에서 class/def/function/const/interface 정의 패턴으로 검색한다.
          4. 미발견 식별자를 반환한다.

        한계 및 개선 예정:
          - [TODO] Sprint 4: AST 기반 분석으로 정확도 향상.
          - 현재는 텍스트 기반이므로 동적 클래스명 등은 탐지 불가.
          - 파일 크기 합계가 _MAX_FILE_BYTES × 50 초과 시 조기 종료.
        """
        content = self._read_safe(agents_md_path)
        # backtick 식별자 추출 (3글자 이상 PascalCase/snake_case 대상)
        raw_refs = re.findall(r"`([A-Za-z_][A-Za-z0-9_]{2,})`", content)

        # 공통 식별자 / 언어 키워드 제거
        refs = {
            ref for ref in raw_refs
            if ref not in _COMMON_IDENTIFIERS
        }

        if not refs:
            return []

        # 소스 파일 수집 — 총량 상한으로 메모리 안전 보장
        max_total_bytes = _MAX_FILE_BYTES * 50  # 25 MB 상한
        all_source = ""
        total_bytes = 0

        source_exts = ("*.py", "*.ts", "*.js")
        for ext in source_exts:
            for f in self._rglob_safe(ext):
                try:
                    raw = f.read_bytes()
                    chunk = raw[:_MAX_FILE_BYTES].decode("utf-8", errors="replace")
                    all_source += chunk
                    total_bytes += len(chunk)
                    if total_bytes >= max_total_bytes:
                        break
                except OSError:
                    continue
            if total_bytes >= max_total_bytes:
                break

        # 정의 패턴 검색
        invalid = []
        for ref in sorted(refs):
            define_pattern = (
                rf"\b(class|def|function|const|interface)\s+{re.escape(ref)}\b"
            )
            if not re.search(define_pattern, all_source):
                invalid.append(ref)

        return invalid

    def _detect_gc_agent(self) -> bool:
        """GC 에이전트 스크립트 또는 CI 스케줄 잡 존재 여부.

        판별 기준 (오탐 방지를 위해 prefix/suffix/keyword 분리):
          - prefix: "gc_" 또는 "gc-"로 시작하는 파일명 (예: gc_agent.py)
          - suffix: "_gc.py", "-gc.py" 등으로 끝나는 파일명 (예: doc_gc.py)
          - keyword: 파일명 전체에 특정 단어 포함 (예: garbage_collect.py)
          - Python / JS / TS 파일 모두 탐지
        """
        source_extensions = ("*.py", "*.js", "*.ts")
        for ext in source_extensions:
            for p in self._rglob_safe(ext):
                name = p.name.lower()
                if any(name.startswith(pref) for pref in _GC_AGENT_PREFIXES):
                    return True
                if any(name.endswith(suf) for suf in _GC_AGENT_SUFFIXES):
                    return True
                # 파일 기본명(확장자 제거)에 키워드 전체 포함 여부
                stem = p.stem.lower()
                if any(kw in stem for kw in _GC_AGENT_KEYWORDS):
                    return True

        # CI 워크플로우에서 스케줄 기반 GC 실행 여부 확인
        workflows_dir = self.target / ".github" / "workflows"
        if workflows_dir.exists():
            for wf in (
                list(workflows_dir.glob("*.yml"))
                + list(workflows_dir.glob("*.yaml"))
            ):
                content = self._read_safe(wf).lower()
                if "schedule" in content and any(
                    pat in content for pat in {"gc", "consistency", "cleanup"}
                ):
                    return True
        return False

    def _measure_bare_suppressions(self) -> float:
        """이유 없는 린터 억제 주석 비율을 반환한다.

        판단 기준:
          - 좋은 예: # [EXCEPTION] 마이그레이션 스크립트 # noqa: E501
          - 나쁜 예: # noqa    # type: ignore    // eslint-disable-next-line

        알고리즘:
          suppress_total: noqa / eslint-disable / type: ignore가 있는 라인 수
          bare_count: 같은 라인에 [EXCEPTION] 주석이 없는 suppress 라인 수
          반환값: bare_count / suppress_total  (suppress가 없으면 0.0)

        핵심 수정사항 (v1.2 버그 수정):
          - [EXCEPTION]은 suppress 키워드 앞에 올 수 있으므로, 라인 전체에서 검색.
          - Python 파일: tokenize 모듈로 실제 COMMENT 토큰만 검사 (docstring·문자열 오탐 완전 차단).
          - JS/TS 파일: 단일행 문자열 리터럴 제거 후 검사.
        """
        # 모듈 레벨 상수 사용: _SUPPRESS_RE, _EXCEPTION_RE, _STR_LITERAL_RE
        suppress_total = 0
        bare_count = 0

        # ── Python 파일: tokenize로 COMMENT 토큰만 검사 ──────────────────────
        for f in self._rglob_safe("*.py"):
            try:
                source = self._read_safe(f)
                tokens = tokenize.generate_tokens(io.StringIO(source).readline)
                for tok_type, tok_string, _, _, _ in tokens:
                    if tok_type == tokenize.COMMENT and _SUPPRESS_RE.search(tok_string):
                        suppress_total += 1
                        if not _EXCEPTION_RE.search(tok_string):
                            bare_count += 1
            except (OSError, tokenize.TokenError):
                continue

        # ── JS/TS 파일: 단일행 문자열 제거 후 라인 단위 검사 ──────────────────
        for ext in ("*.ts", "*.js"):
            for f in self._rglob_safe(ext):
                try:
                    lines = self._read_safe(f).splitlines()
                except OSError:
                    continue
                for line in lines:
                    stripped = _STR_LITERAL_RE.sub("''", line)
                    if _SUPPRESS_RE.search(stripped):
                        suppress_total += 1
                        if not _EXCEPTION_RE.search(stripped):
                            bare_count += 1

        return bare_count / suppress_total if suppress_total > 0 else 0.0

    # ── Private: 기술 스택 감지 ──────────────────────────────────────────────

    def _detect_tech_stack(self, result: ScanResult) -> None:
        """프로젝트에서 사용하는 기술 스택을 감지한다."""
        for stack, indicators in _STACK_INDICATORS.items():
            for pattern in indicators:
                if pattern.startswith("*."):
                    if self._rglob_safe(pattern):
                        result.tech_stack.append(stack)
                        break
                else:
                    if (self.target / pattern).exists():
                        result.tech_stack.append(stack)
                        break
        # 중복 제거, 순서 유지
        result.tech_stack = list(dict.fromkeys(result.tech_stack))

    # ── Phase 2: Go / Java 스캔 ─────────────────────────────────────────────

    def _scan_go_java(self, result: ScanResult) -> None:
        """Go 및 Java 프로젝트 메트릭 수집."""
        self._scan_go(result)
        self._scan_java(result)

    def _scan_go(self, result: ScanResult) -> None:
        """Go 프로젝트 메트릭 수집."""
        go_mod = self.target / "go.mod"
        if not go_mod.exists():
            return

        # go.mod에서 모듈명 추출
        try:
            content = self._read_safe(go_mod)
            m = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
            if m:
                result.go_module_name = m.group(1)
        except OSError:
            pass

        # *_test.go 파일 존재 여부
        result.go_has_tests = bool(self._rglob_safe("*_test.go"))

        # golangci-lint 설정 파일 또는 CI에서 go vet/golangci-lint 사용 여부
        go_lint_files = {
            ".golangci.yml", ".golangci.yaml", ".golangci.json", ".golangci.toml"
        }
        result.go_has_linter = any(
            (self.target / f).exists() for f in go_lint_files
        )
        if not result.go_has_linter:
            # CI 워크플로우에서 golangci-lint 또는 go vet 사용 확인
            workflows_dir = self.target / ".github" / "workflows"
            if workflows_dir.exists():
                for wf in list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml")):
                    content = self._read_safe(wf).lower()
                    if "golangci" in content or "go vet" in content or "go test" in content:
                        result.go_has_linter = True
                        break

    def _scan_java(self, result: ScanResult) -> None:
        """Java 프로젝트 메트릭 수집."""
        pom = self.target / "pom.xml"
        gradle = self.target / "build.gradle"
        gradle_kts = self.target / "build.gradle.kts"

        if pom.exists():
            result.java_build_tool = "maven"
        elif gradle.exists() or gradle_kts.exists():
            result.java_build_tool = "gradle"
        else:
            return

        # src/test/ 디렉토리 존재 여부
        result.java_has_tests = (self.target / "src" / "test").exists()

        # checkstyle / spotbugs / PMD 설정 또는 CI 확인
        java_lint_files = {"checkstyle.xml", "checkstyle-config.xml", "spotbugs-filter.xml"}
        result.java_has_linter = any(
            (self.target / f).exists() for f in java_lint_files
        )
        if not result.java_has_linter:
            # pom.xml에 checkstyle/spotbugs 플러그인 여부
            if pom.exists():
                content = self._read_safe(pom).lower()
                if "checkstyle" in content or "spotbugs" in content or "pmd" in content:
                    result.java_has_linter = True
            if not result.java_has_linter:
                # build.gradle에서 확인
                for bf in [gradle, gradle_kts]:
                    if bf.exists():
                        content = self._read_safe(bf).lower()
                        if "checkstyle" in content or "spotbugs" in content or "pmd" in content:
                            result.java_has_linter = True
                            break

    # ── Phase 3: TypeScript 심층 분석 ────────────────────────────────────────

    def _scan_typescript(self, result: ScanResult) -> None:
        """TypeScript 프로젝트 심층 메트릭 수집 (Phase 3).

        감지 항목:
          - ESLint 설정 파일 존재 및 extends 목록 파싱
          - tsconfig.json strict 모드, paths 별칭 설정
          - *.test.ts / *.spec.ts 파일 수
          - vitest / jest 설정 파일 존재 여부
        """
        # TypeScript 또는 JavaScript 프로젝트가 아니면 스킵
        if "typescript" not in result.tech_stack and "javascript" not in result.tech_stack:
            return

        self._scan_ts_eslint(result)
        self._scan_tsconfig(result)
        self._scan_ts_tests(result)

    def _scan_ts_eslint(self, result: ScanResult) -> None:
        """ESLint 설정 파싱 — 존재 여부 및 extends 목록 추출."""
        eslint_names = {
            ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.mjs",
            ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml",
            "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
            "eslint.config.ts",
        }
        for name in eslint_names:
            eslint_path = self.target / name
            if not eslint_path.exists():
                continue
            result.ts_has_eslint = True
            # extends 목록 추출 (JSON / JS 공통 패턴)
            try:
                content = self._read_safe(eslint_path)
                # "extends": ["a", "b"] 또는 extends: ["a", "b"] 패턴
                extends_matches = re.findall(
                    r'"extends"\s*:\s*\[([^\]]+)\]|extends\s*:\s*\[([^\]]+)\]',
                    content
                )
                for m1, m2 in extends_matches:
                    raw = m1 or m2
                    # 문자열 값만 추출
                    items = re.findall(r'["\']([^"\']+)["\']', raw)
                    result.ts_eslint_extends.extend(items)
                # 단일 문자열 extends: "value"
                if not result.ts_eslint_extends:
                    single = re.findall(
                        r'"extends"\s*:\s*["\']([^"\']+)["\']|extends\s*:\s*["\']([^"\']+)["\']',
                        content
                    )
                    for m1, m2 in single:
                        result.ts_eslint_extends.append(m1 or m2)
            except OSError:
                pass
            break

        # package.json의 eslintConfig 섹션도 확인
        if not result.ts_has_eslint:
            pkg_json = self.target / "package.json"
            if pkg_json.exists():
                content = self._read_safe(pkg_json)
                if '"eslintConfig"' in content:
                    result.ts_has_eslint = True

    def _scan_tsconfig(self, result: ScanResult) -> None:
        """tsconfig.json 파싱 — strict 모드, paths 별칭 설정 감지."""
        tsconfig_path = self.target / "tsconfig.json"
        if not tsconfig_path.exists():
            # tsconfig.base.json, tsconfig.app.json 등도 탐색
            for candidate in self.target.glob("tsconfig*.json"):
                if any(part in _EXCLUDE_DIRS for part in candidate.parts):
                    continue
                tsconfig_path = candidate
                break
            else:
                return

        try:
            import json
            content = self._read_safe(tsconfig_path)
            # JSON5 형식(주석 포함)을 허용하기 위해 주석 제거 후 파싱
            content_clean = re.sub(r"//[^\n]*", "", content)   # 단일행 주석 제거
            content_clean = re.sub(r"/\*.*?\*/", "", content_clean, flags=re.DOTALL)
            data = json.loads(content_clean)
        except (OSError, json.JSONDecodeError):
            return

        compiler_opts = data.get("compilerOptions", {})
        result.ts_has_strict = bool(compiler_opts.get("strict", False))
        result.ts_has_path_aliases = bool(compiler_opts.get("paths"))

    def _scan_ts_tests(self, result: ScanResult) -> None:
        """TypeScript 테스트 파일 수 및 테스트 프레임워크 감지."""
        # *.test.ts, *.spec.ts, *.test.tsx, *.spec.tsx
        test_files = []
        for pattern in ("*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx"):
            test_files.extend(self._rglob_safe(pattern))
        result.ts_test_files = len(test_files)

        # vitest / jest 설정 파일 감지
        test_config_names = {
            "vitest.config.ts", "vitest.config.js", "vitest.config.mts",
            "jest.config.ts", "jest.config.js", "jest.config.mjs",
            "jest.config.cjs",
        }
        result.ts_has_vitest_or_jest = any(
            (self.target / name).exists() for name in test_config_names
        )
        # package.json의 "jest" 또는 "vitest" 설정 섹션도 확인
        if not result.ts_has_vitest_or_jest:
            pkg_json = self.target / "package.json"
            if pkg_json.exists():
                content = self._read_safe(pkg_json)
                if '"jest"' in content or '"vitest"' in content:
                    result.ts_has_vitest_or_jest = True
