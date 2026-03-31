"""Phase 1 + Phase 2 통합 테스트 — 5가지 유형.

유형 1: 레이어 아키텍처 불변식 테스트
         Phase 1/2 전체 소스에 걸쳐 단방향 레이어 의존성이 항상 성립함을 검증.

유형 2: 점수 연속성 테스트
         Phase 1 기준점(0점·만점) 시나리오를 Phase 2 환경에서도 재현.
         AST 의존성 위반이 AC-05 배점에 정확히 반영되는지 포함.

유형 3: Go/Java 엔드투엔드 파이프라인 테스트
         Go·Java 프로젝트 전체를 스캔→진단→점수화하는 전체 파이프라인 검증.
         언어별 필드가 Auditor 결과에 일관되게 반영되는지 확인.

유형 4: LLM + 시계열 이력 저장 파이프라인 테스트
         Mock LLM → ScanResult 업데이트 → HistoryDB 저장 → 조회·ASCII 차트까지
         전체 데이터 흐름의 무결성 검증.

유형 5: 자가 진단 회귀 테스트
         hachilles 자체 코드를 스캔·진단·점수화하여 S등급(≥90점)이 유지됨을 확인.
         Phase 2 추가 이후에도 품질 기준 퇴행이 없음을 보장.
"""
from __future__ import annotations

import ast
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture()
def project_root() -> Path:
    """hachilles 프로젝트 루트 경로."""
    return Path(__file__).parent.parent


@pytest.fixture()
def src_root(project_root: Path) -> Path:
    """hachilles src 경로."""
    return project_root / "src"


@pytest.fixture()
def make_project(tmp_path: Path):
    """프로젝트 파일 생성 헬퍼."""
    def _make(files: dict[str, str]) -> Path:
        for rel_path, content in files.items():
            target = tmp_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return tmp_path
    return _make


# ══════════════════════════════════════════════════════════════════════════════
# 유형 1: 레이어 아키텍처 불변식 테스트
# ══════════════════════════════════════════════════════════════════════════════

class TestLayerArchitectureInvariant:
    """레이어 단방향 의존성 불변식을 Phase 1/2 전체 소스에 대해 검증한다."""

    # 레이어 순서: 낮은 인덱스 = 더 아래(더 구체적) 레이어
    LAYER_ORDER = [
        "models", "scanner", "auditors", "score",
        "prescriptions", "report", "cli", "llm", "tracker",
    ]
    LAYER_IDX = {layer: i for i, layer in enumerate(LAYER_ORDER)}

    def _collect_violations(self, src: Path) -> list[str]:
        """src 아래의 모든 .py 파일에서 레이어 위반을 수집한다."""
        hachilles_src = src / "hachilles"
        violations = []

        for pyfile in sorted(hachilles_src.rglob("*.py")):
            parts = pyfile.relative_to(hachilles_src).parts
            if len(parts) < 2:
                continue
            module_layer = parts[0]
            if module_layer not in self.LAYER_IDX:
                continue

            try:
                tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module
                    if not mod.startswith("hachilles."):
                        continue
                    parts2 = mod.split(".")
                    if len(parts2) < 2:
                        continue
                    imported_layer = parts2[1]
                    if imported_layer not in self.LAYER_IDX:
                        continue
                    if module_layer == imported_layer:
                        continue

                    src_idx = self.LAYER_IDX[module_layer]
                    dst_idx = self.LAYER_IDX[imported_layer]

                    # 규칙: 레이어는 자신보다 아래(더 낮은 인덱스) 레이어만 import 가능
                    if dst_idx >= src_idx:
                        violations.append(
                            f"{pyfile.relative_to(hachilles_src)}: "
                            f"{module_layer}(idx={src_idx}) → {imported_layer}(idx={dst_idx})"
                        )
        return violations

    def test_no_layer_violations_in_entire_codebase(self, src_root: Path) -> None:
        """Phase 1/2 전체 소스에서 레이어 위반이 0건이어야 한다."""
        violations = self._collect_violations(src_root)
        assert violations == [], (
            f"레이어 위반 {len(violations)}건 발견:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_models_imports_nothing_external_to_layer(self, src_root: Path) -> None:
        """models 레이어는 다른 hachilles 레이어(models 제외)를 import하지 않는다."""
        models_dir = src_root / "hachilles" / "models"
        for pyfile in models_dir.rglob("*.py"):
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("hachilles."):
                        parts = node.module.split(".")
                        # 같은 레이어(hachilles.models.*) 내 import는 허용
                        if len(parts) >= 2 and parts[1] != "models":
                            raise AssertionError(
                                f"models 레이어가 다른 레이어 {node.module}을 import함 — 위반!"
                            )

    def test_cli_can_import_all_layers(self, src_root: Path) -> None:
        """cli 레이어는 모든 내부 레이어를 import할 수 있다 (최상위)."""
        cli_py = src_root / "hachilles" / "cli.py"
        tree = ast.parse(cli_py.read_text(encoding="utf-8"))
        imported_layers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("hachilles."):
                    parts = node.module.split(".")
                    if len(parts) >= 2:
                        imported_layers.add(parts[1])
        # cli는 models, scanner, score, llm, tracker를 모두 import한다
        essential_layers = {"models", "scanner", "score"}
        assert essential_layers.issubset(imported_layers), (
            f"cli가 필수 레이어를 import하지 않음: {essential_layers - imported_layers}"
        )

    def test_auditors_do_not_import_score(self, src_root: Path) -> None:
        """auditors 레이어는 score 레이어를 import하지 않는다."""
        auditors_dir = src_root / "hachilles" / "auditors"
        for pyfile in auditors_dir.rglob("*.py"):
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "hachilles.score" not in node.module, (
                        f"{pyfile.name}이 score 레이어를 import함 — 위반!"
                    )

    def test_llm_tracker_independent_from_auditors(self, src_root: Path) -> None:
        """llm/tracker 레이어는 auditors/score를 import하지 않는다."""
        forbidden_layers = {"hachilles.auditors", "hachilles.score"}
        for layer_dir in ["llm", "tracker"]:
            layer_path = src_root / "hachilles" / layer_dir
            for pyfile in layer_path.rglob("*.py"):
                tree = ast.parse(pyfile.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        for forbidden in forbidden_layers:
                            assert not node.module.startswith(forbidden), (
                                f"{layer_dir}/{pyfile.name}이 {node.module}을 import — 위반!"
                            )


# ══════════════════════════════════════════════════════════════════════════════
# 유형 2: 점수 연속성 테스트
# ══════════════════════════════════════════════════════════════════════════════

class TestScoringContinuity:
    """Phase 1 기준 점수 시나리오가 Phase 2 환경에서도 동일하게 계산됨을 검증."""

    def _make_full_scan(self, tmp_path: Path) -> object:
        """100점 요건을 갖춘 프로젝트를 스캔하여 ScanResult 반환."""
        from hachilles.scanner.scanner import Scanner

        # AGENTS.md (충분히 긴 내용)
        agents_content = "# Agent Guide\n\n" + "content\n" * 50
        (tmp_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

        # docs/ 구조
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        (docs / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
        (docs / "forbidden.md").write_text("# Forbidden Patterns\n", encoding="utf-8")
        decisions = docs / "decisions"
        decisions.mkdir()
        (decisions / "ADR-001.md").write_text("# ADR-001\n", encoding="utf-8")

        # 세션 브릿지
        (tmp_path / "claude-progress.txt").write_text("progress\n", encoding="utf-8")

        # feature_list.json
        (tmp_path / "feature_list.json").write_text("{}\n", encoding="utf-8")

        # 린터 설정 (pyproject.toml with ruff)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )

        # pre-commit
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")

        # CI gate
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: push\njobs:\n  test:\n    steps:\n      - run: pytest\n",
            encoding="utf-8",
        )

        # GC 에이전트
        (tmp_path / "gc_agent.py").write_text("# GC\n", encoding="utf-8")

        return Scanner(tmp_path).scan()

    def test_full_score_scenario_reaches_100(self, tmp_path: Path) -> None:
        """모든 항목 충족 시 100점이어야 한다."""
        from hachilles.score.score_engine import ScoreEngine

        scan = self._make_full_scan(tmp_path)
        score = ScoreEngine().score(scan)
        assert score.total == 100, (
            f"100점 기대, 실제 {score.total}점\n"
            + "\n".join(
                f"  {item.code}: {item.score}/{item.full_score} — {item.detail}"
                for r in score.all_audit_results
                for item in r.items
                if not item.passed
            )
        )

    def test_empty_project_score_under_20(self, tmp_path: Path) -> None:
        """완전히 빈 프로젝트는 20점 미만이어야 한다."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        scan = Scanner(tmp_path).scan()
        score = ScoreEngine().score(scan)
        assert score.total < 20, f"빈 프로젝트가 {score.total}점 — 너무 높음"
        assert score.grade == "D"

    def test_ast_layer_violations_reduce_ac05_score(self, tmp_path: Path) -> None:
        """AST 레이어 위반 시 AC-05 배점이 감소한다."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        # Python 파일들을 포함한 프로젝트
        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")

        # 레이어 위반 없는 정상 케이스
        scan_ok = Scanner(tmp_path).scan()
        scan_ok.dependency_violations = 0
        scan_ok.layer_violations = []
        scan_ok.dependency_cycles = []
        score_ok = ScoreEngine().score(scan_ok)

        # 레이어 위반 있는 케이스
        scan_bad = Scanner(tmp_path).scan()
        scan_bad.dependency_violations = 2
        scan_bad.layer_violations = [("models.foo", "scanner.bar"), ("models.x", "auditors.y")]
        scan_bad.dependency_cycles = []
        score_bad = ScoreEngine().score(scan_bad)

        # AC-05 감점 확인
        ac05_ok = next(
            item for r in score_ok.all_audit_results for item in r.items if item.code == "AC-05"
        )
        ac05_bad = next(
            item for r in score_bad.all_audit_results for item in r.items if item.code == "AC-05"
        )
        assert ac05_ok.score > ac05_bad.score, (
            f"위반 없을 때 AC-05={ac05_ok.score}, 위반 있을 때 AC-05={ac05_bad.score} — 감점이 없음!"
        )

    def test_grade_thresholds_are_sharp(self, tmp_path: Path) -> None:
        """경계값 점수에서 등급이 정확히 전환된다."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        scan = Scanner(tmp_path).scan()
        engine = ScoreEngine()

        boundary_cases = [
            (100, "S"), (90, "S"), (89, "A"), (75, "A"),
            (74, "B"), (60, "B"), (59, "C"), (40, "C"),
            (39, "D"), (0, "D"),
        ]

        for total_score, expected_grade in boundary_cases:
            scan.dependency_violations = 0
            # ScoreEngine._determine_grade를 직접 검증
            grade, _ = engine._determine_grade(total_score)
            assert grade == expected_grade, (
                f"점수={total_score}: 기대={expected_grade}, 실제={grade}"
            )

    def test_pattern_risks_reflect_phase2_audit_results(self, tmp_path: Path) -> None:
        """패턴 위험도 평가가 Phase 2 항목(AC-05)을 포함한 전체 진단 결과를 반영한다."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        scan = Scanner(tmp_path).scan()
        # 의존성 위반 + 린터 없음 + pre-commit 없음 → AI Slop 위험
        scan.has_linter_config = False
        scan.has_pre_commit = False
        scan.dependency_violations = 0

        score = ScoreEngine().score(scan)

        # 5개 패턴 모두 존재해야 함
        assert len(score.pattern_risks) == 5
        patterns = {pr.pattern for pr in score.pattern_risks}
        assert patterns == {
            "Context Drift", "AI Slop", "Entropy Explosion", "70-80% Wall", "Over-engineering"
        }


# ══════════════════════════════════════════════════════════════════════════════
# 유형 3: Go/Java 엔드투엔드 파이프라인 테스트
# ══════════════════════════════════════════════════════════════════════════════

class TestGoJavaEndToEndPipeline:
    """Go·Java 프로젝트의 스캔→진단→점수화 전체 파이프라인 강도 테스트."""

    def test_go_project_full_pipeline(self, make_project) -> None:
        """Go 프로젝트 전체 파이프라인: 스캔 → 기술스택 감지 → 점수화."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        project = make_project({
            "go.mod": "module github.com/example/myapp\n\ngo 1.21\n",
            "main.go": "package main\nfunc main() {}\n",
            "main_test.go": "package main\nimport \"testing\"\nfunc TestFoo(t *testing.T) {}\n",
            ".golangci.yml": "linters:\n  enable:\n    - errcheck\n",
            "AGENTS.md": "# Agent\n" + "x\n" * 50,
            ".github/workflows/ci.yml": (
                "name: CI\non: push\njobs:\n  test:\n    steps:\n      - run: go test\n"
            ),
        })

        result = Scanner(project).scan()

        # 스캔 필드 검증
        assert result.go_module_name == "github.com/example/myapp"
        assert result.go_has_tests is True
        assert result.go_has_linter is True
        assert "go" in result.tech_stack
        assert result.scan_timestamp != ""

        # 점수화 실행 (오류 없이 완료되어야 함)
        score = ScoreEngine().score(result)
        assert score.total >= 0
        assert score.grade in {"S", "A", "B", "C", "D"}

    def test_java_maven_project_full_pipeline(self, make_project) -> None:
        """Java Maven 프로젝트 전체 파이프라인."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        project = make_project({
            "pom.xml": (
                "<project><build><plugins><plugin>"
                "<artifactId>maven-checkstyle-plugin</artifactId>"
                "</plugin></plugins></build></project>"
            ),
            "src/main/java/App.java": "public class App { public static void main(String[] args) {} }",
            "src/test/java/AppTest.java": "public class AppTest { @Test void test() {} }",
            ".github/workflows/ci.yml": (
                "name: CI\non: push\njobs:\n  build:\n    steps:\n      - run: mvn test\n"
            ),
        })

        result = Scanner(project).scan()

        assert result.java_build_tool == "maven"
        assert result.java_has_tests is True
        assert result.java_has_linter is True
        assert "java" in result.tech_stack

        score = ScoreEngine().score(result)
        assert score.total >= 0

    def test_go_java_polyglot_project(self, make_project) -> None:
        """Go + Java 혼합 프로젝트가 두 기술 스택을 모두 감지한다."""
        from hachilles.scanner.scanner import Scanner

        project = make_project({
            "go.mod": "module example.com/app\n",
            "main.go": "package main\n",
            "pom.xml": "<project><modelVersion>4.0.0</modelVersion></project>",
            "src/main/java/App.java": "public class App {}",
        })

        result = Scanner(project).scan()

        assert result.go_module_name == "example.com/app"
        assert result.java_build_tool == "maven"
        assert "go" in result.tech_stack
        assert "java" in result.tech_stack

    def test_go_no_tests_no_linter_reduces_score(self, make_project) -> None:
        """Go 프로젝트에서 테스트·린터 없으면 AC/EM 항목 점수가 낮다."""
        from hachilles.scanner.scanner import Scanner

        # 테스트·린터 있는 프로젝트
        project_good = make_project({
            "go.mod": "module example.com/app\n",
            "main_test.go": "package main\nimport \"testing\"\n",
            ".golangci.yml": "linters:\n  enable:\n    - errcheck\n",
        })
        result_good = Scanner(project_good).scan()

        # 새로운 tmp 디렉토리로 빈 프로젝트
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
            (p / "main.go").write_text("package main\n", encoding="utf-8")
            result_bare = Scanner(p).scan()

        assert result_good.go_has_tests is True
        assert result_good.go_has_linter is True
        assert result_bare.go_has_tests is False
        assert result_bare.go_has_linter is False

    def test_scan_timestamp_iso8601_utc(self, make_project) -> None:
        """스캔 타임스탬프가 ISO 8601 UTC 형식이다."""
        import datetime

        from hachilles.scanner.scanner import Scanner

        project = make_project({"dummy.txt": "x"})
        result = Scanner(project).scan()

        ts = result.scan_timestamp
        assert ts != ""
        # ISO 8601 파싱 가능해야 함
        dt = datetime.datetime.fromisoformat(ts)
        assert dt.tzinfo is not None, "타임존 정보 없음"
        # UTC여야 함
        assert str(dt.tzinfo) in {"+00:00", "UTC"} or dt.utcoffset().total_seconds() == 0


# ══════════════════════════════════════════════════════════════════════════════
# 유형 4: LLM + 시계열 이력 저장 파이프라인 테스트
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMHistoryPipeline:
    """LLM 평가 → ScanResult 업데이트 → HistoryDB 저장 → 조회까지 전체 파이프라인."""

    @pytest.fixture()
    def mock_evaluator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Mock LLM을 사용하는 LLMEvaluator."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "mock")
        from hachilles.llm.cache import LLMCache
        from hachilles.llm.evaluator import LLMEvaluator
        cache = LLMCache(cache_dir=tmp_path / "cache")
        return LLMEvaluator(cache=cache)

    @pytest.fixture()
    def history_db(self, tmp_path: Path):
        """임시 HistoryDB."""
        from hachilles.tracker.history import HistoryDB
        return HistoryDB(db_path=tmp_path / "test.db")

    def test_llm_result_populates_scan_result(
        self, mock_evaluator, tmp_path: Path
    ) -> None:
        """LLM 평가 결과가 ScanResult 필드를 올바르게 채운다."""
        from hachilles.models.scan_result import ScanResult

        scan_result = ScanResult(target_path=tmp_path)
        assert scan_result.llm_over_engineering_score == 0.0
        assert scan_result.llm_over_engineering_evidence == []

        score, evidence = mock_evaluator.evaluate_over_engineering(tmp_path)
        scan_result.llm_over_engineering_score = score
        scan_result.llm_over_engineering_evidence = evidence

        assert 0.0 <= scan_result.llm_over_engineering_score <= 1.0
        assert isinstance(scan_result.llm_over_engineering_evidence, list)

    def test_full_llm_to_history_pipeline(
        self, mock_evaluator, history_db, tmp_path: Path
    ) -> None:
        """LLM 평가 → 점수화 → HistoryDB 저장 → 조회까지 전체 파이프라인."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        # 1. 스캔
        scan_result = Scanner(tmp_path).scan()
        assert scan_result.scan_timestamp != ""

        # 2. LLM 평가
        llm_score, llm_evidence = mock_evaluator.evaluate_over_engineering(tmp_path)
        scan_result.llm_over_engineering_score = llm_score
        scan_result.llm_over_engineering_evidence = llm_evidence

        # 3. 점수화
        engine = ScoreEngine()
        harness_score = engine.score(scan_result)
        assert harness_score.total >= 0

        # 4. 이력 저장
        total_items = sum(len(r.items) for r in harness_score.all_audit_results)
        passed_items = sum(r.passed_count for r in harness_score.all_audit_results)
        history_db.save(
            project_path=str(tmp_path),
            timestamp=scan_result.scan_timestamp,
            total_score=harness_score.total,
            ce_score=harness_score.context_score,
            ac_score=harness_score.constraint_score,
            em_score=harness_score.entropy_score,
            grade=harness_score.grade,
            passed_items=passed_items,
            total_items=total_items,
            tech_stack=scan_result.tech_stack,
        )

        # 5. 조회 검증
        records = history_db.get_history(str(tmp_path))
        assert len(records) == 1
        record = records[0]
        assert record.total_score == harness_score.total
        assert record.grade == harness_score.grade

    def test_multiple_scans_trend_analysis(
        self, history_db, tmp_path: Path
    ) -> None:
        """여러 번 저장된 이력의 추이 분석이 올바르다."""
        # 상승 추이 시뮬레이션
        scores = [40, 55, 70, 85, 100]
        for i, total in enumerate(scores):
            history_db.save(
                project_path=str(tmp_path),
                timestamp=f"2026-03-{i+1:02d}T09:00:00+00:00",
                total_score=total,
                ce_score=total * 40 // 100,
                ac_score=total * 35 // 100,
                em_score=total * 25 // 100,
                grade="D" if total < 40 else ("C" if total < 60 else "B"),
                passed_items=total // 10,
                total_items=15,
                tech_stack=["python"],
            )

        records = history_db.get_history(str(tmp_path))
        assert len(records) == 5

        # 점수 범위 확인
        assert max(r.total_score for r in records) == 100
        assert min(r.total_score for r in records) == 40

        # ASCII 차트 생성 확인
        chart = history_db.ascii_chart(str(tmp_path))
        assert chart != ""
        assert "100" in chart or "40" in chart

    def test_llm_cache_prevents_redundant_calls(
        self, mock_evaluator, tmp_path: Path
    ) -> None:
        """동일 경로 두 번 호출 시 두 번째는 캐시를 사용한다."""
        # 첫 번째 호출 (캐시 미스)
        mock_evaluator.evaluate_over_engineering(tmp_path)
        misses_after_first = mock_evaluator.cache.stats()["misses"]

        # 두 번째 호출 (캐시 히트)
        mock_evaluator.evaluate_over_engineering(tmp_path)
        hits_after_second = mock_evaluator.cache.stats()["hits"]

        assert hits_after_second >= 1, "두 번째 호출이 캐시를 사용하지 않았음"
        assert misses_after_first == 1, f"첫 번째 호출 미스 횟수 이상: {misses_after_first}"

    def test_history_db_sqlite_schema_integrity(self, tmp_path: Path) -> None:
        """SQLite DB 스키마가 예상된 컬럼을 갖는다."""
        from hachilles.tracker.history import HistoryDB

        db = HistoryDB(db_path=tmp_path / "schema_test.db")
        db.save(
            project_path="/test",
            timestamp="2026-01-01T00:00:00+00:00",
            total_score=80,
            ce_score=35, ac_score=28, em_score=17,
            grade="A",
            passed_items=12, total_items=15,
            tech_stack=["python"],
        )

        conn = sqlite3.connect(str(tmp_path / "schema_test.db"))
        cursor = conn.execute("PRAGMA table_info(scan_history)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected_cols = {
            "id", "project_path", "timestamp", "total_score",
            "ce_score", "ac_score", "em_score", "grade",
            "passed_items", "total_items", "tech_stack",
        }
        assert expected_cols.issubset(columns), (
            f"누락된 컬럼: {expected_cols - columns}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 유형 5: 자가 진단 회귀 테스트
# ══════════════════════════════════════════════════════════════════════════════

class TestSelfAuditRegression:
    """HAchilles가 자기 자신을 진단할 때 S등급 품질을 유지함을 검증한다.

    Phase 2 추가 이후에도 모든 품질 기준이 유지되어야 한다.
    """

    @pytest.fixture()
    def self_scan(self):
        """HAchilles 자체 스캔 결과."""
        from hachilles.scanner.scanner import Scanner
        from hachilles.score.score_engine import ScoreEngine

        project_root = Path(__file__).parent.parent
        scan_result = Scanner(project_root).scan()
        harness_score = ScoreEngine().score(scan_result)
        return scan_result, harness_score

    def test_self_audit_score_is_s_grade(self, self_scan) -> None:
        """자가 진단 점수가 S등급(90점 이상)이어야 한다."""
        _, score = self_scan
        assert score.total >= 90, (
            f"자가 진단 점수 {score.total}점 — S등급 기준 미달\n"
            + "\n".join(
                f"  {item.code}: {item.score}/{item.full_score} — {item.detail}"
                for r in score.all_audit_results
                for item in r.items
                if not item.passed
            )
        )
        assert score.grade == "S"

    def test_no_ast_cycles_or_violations(self, self_scan) -> None:
        """HAchilles 자체 코드에 순환 의존성·레이어 위반이 없어야 한다."""
        scan_result, _ = self_scan
        assert scan_result.dependency_cycles == [], (
            f"순환 의존성 발견: {scan_result.dependency_cycles}"
        )
        assert scan_result.layer_violations == [], (
            f"레이어 위반 발견: {scan_result.layer_violations}"
        )
        assert scan_result.dependency_violations == 0

    def test_all_15_items_defined(self, self_scan) -> None:
        """15개 진단 항목이 모두 정의되어 있어야 한다."""
        _, score = self_scan
        all_items = [item for r in score.all_audit_results for item in r.items]
        assert len(all_items) == 15, f"진단 항목 수 이상: {len(all_items)}"

        codes = {item.code for item in all_items}
        expected = {f"CE-0{i}" for i in range(1, 6)} | {f"AC-0{i}" for i in range(1, 6)} | {f"EM-0{i}" for i in range(1, 6)}
        assert codes == expected, f"항목 코드 불일치: {codes ^ expected}"

    def test_total_score_adds_up_correctly(self, self_scan) -> None:
        """기둥별 점수 합산이 총점과 일치한다."""
        _, score = self_scan
        pillar_sum = score.context_score + score.constraint_score + score.entropy_score
        assert pillar_sum == score.total, (
            f"기둥 합계({pillar_sum}) ≠ 총점({score.total})"
        )

    def test_json_schema_has_required_keys(self, self_scan) -> None:
        """JSON 출력 스키마에 필수 키가 모두 있어야 한다."""
        import unittest.mock as mock

        from hachilles.cli import _output_json

        scan_result, score = self_scan

        with mock.patch("click.echo") as mock_echo:
            _output_json(score, scan_result)
            call_args = mock_echo.call_args[0][0]

        data = json.loads(call_args)

        required_keys = {
            "hachilles_version", "total", "total_score",
            "grade", "grade_label", "pillars",
            "pattern_risks", "tech_stack", "scan_errors",
        }
        missing = required_keys - set(data.keys())
        assert missing == set(), f"JSON 키 누락: {missing}"

        # total_score == total (CI yml 호환)
        assert data["total_score"] == data["total"]

        # 버전 확인
        assert data["hachilles_version"] in ("2.0.0", "3.0.0")  # Phase 3 업그레이드 허용

    def test_phase2_import_graph_non_empty(self, self_scan) -> None:
        """Phase 2 AST 분석으로 생성된 import_graph가 비어 있지 않아야 한다."""
        scan_result, _ = self_scan
        assert len(scan_result.import_graph) > 0, "import_graph가 비어 있음"
        assert "hachilles.cli" in scan_result.import_graph, (
            "cli 모듈이 import_graph에 없음"
        )

    def test_scan_timestamp_present_after_scan(self, self_scan) -> None:
        """스캔 후 scan_timestamp가 설정되어야 한다."""
        scan_result, _ = self_scan
        assert scan_result.scan_timestamp != ""
        assert "T" in scan_result.scan_timestamp  # ISO 8601 T 구분자

    def test_python_stack_detected(self, self_scan) -> None:
        """HAchilles 자체 스캔에서 python 기술 스택이 감지된다."""
        scan_result, _ = self_scan
        assert "python" in scan_result.tech_stack
