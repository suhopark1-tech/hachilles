"""
HAchilles Phase 1/2/3 전체 통합 테스트

=== 5가지 테스트 유형 ===
T1 - 엔드투엔드 파이프라인: Scanner → Score → Prescription → Report (전 파이프라인)
T2 - 크로스 Phase 데이터 흐름: Phase1 필드 → Phase2 AST → Phase3 TS → API 응답 일관성
T3 - 점수 결정론성: 동일 프로젝트를 CLI 경로와 API 경로로 반복 스캔 시 동일 점수
T4 - 경계값/적대적 입력: 빈 프로젝트, 완벽 프로젝트, 손상 입력 등 극단 케이스
T5 - 스코어링 무결성: 15개 항목 가중치 합=100, 단조성, 기둥 독립성 검증

등급 기준 (실제 _GRADE_BOUNDS):
  S: 90~100 / A: 75~89 / B: 60~74 / C: 40~59 / D: 0~39

실제 5대 패턴 이름:
  Context Drift / AI Slop / Entropy Explosion / 70-80% Wall / Over-engineering
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hachilles.api import create_app
from hachilles.models.scan_result import ScanResult
from hachilles.prescriptions import PrescriptionEngine
from hachilles.report import ReportGenerator
from hachilles.scanner import Scanner
from hachilles.score import ScoreEngine

# ─────────────────────────────────────────────────────────────────────────────
# 실제 Grade 경계 (score_engine._GRADE_BOUNDS 에서 확인)
# ─────────────────────────────────────────────────────────────────────────────
_GRADE_MAP = {
    "S": (90, 100),
    "A": (75, 89),
    "B": (60, 74),
    "C": (40, 59),
    "D": (0, 39),
}

# 실제 5대 패턴명 (score_engine._assess_pattern_risks 에서 확인)
_EXPECTED_PATTERNS = {
    "Context Drift",
    "AI Slop",
    "Entropy Explosion",
    "70-80% Wall",
    "Over-engineering",
}

# ─────────────────────────────────────────────────────────────────────────────
# 공통 픽스처
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def engine() -> ScoreEngine:
    return ScoreEngine()


# ─────────────────────────────────────────────────────────────────────────────
# 샘플 프로젝트 팩토리 (디렉토리를 직접 생성 후 파일 작성)
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_project(root: Path) -> Path:
    """최소 구성 프로젝트: AGENTS.md만 있음 (CE-01만 통과 기대)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Minimal\n- rule1\n- rule2\n")
    return root


def _make_partial_project(root: Path) -> Path:
    """중간 구성: AGENTS.md + ESLint + CI (CE-01, AC-01, AC-03 통과)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text(
        "# Partial Project\n\n## Rules\n- Always write tests\n- No bare suppresses\n"
    )
    (root / ".eslintrc.json").write_text('{"extends": ["eslint:recommended"]}')
    gh = root / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text(
        "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: npm test\n"
    )
    (root / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}')
    return root


def _make_full_project(root: Path) -> Path:
    """최고 점수 목표 프로젝트: 대부분 항목 충족."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text(
        "# Full Project\n\n"
        "## Architecture\n- Unidirectional deps only\n"
        "## Entropy\n- Update docs monthly\n"
        "## Conventions\n- snake_case for Python\n"
        "## Forbidden\n- No `any` type\n"
    )
    docs = root / "docs"
    docs.mkdir()
    (docs / "architecture.md").write_text("# Architecture\nLayer A → Layer B\n")
    (docs / "conventions.md").write_text("# Conventions\nUse snake_case.\n")
    (docs / "session_bridge.md").write_text("# Session Bridge\nContext.\n")
    (docs / "feature_list.json").write_text('{"features": ["auth", "search"]}')
    (root / ".eslintrc.json").write_text(
        '{"extends": ["eslint:recommended", "@typescript-eslint/recommended"]}'
    )
    (root / ".pre-commit-config.yaml").write_text(
        "repos:\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n"
        "    hooks:\n      - id: trailing-whitespace\n"
    )
    gh = root / ".github" / "workflows"
    gh.mkdir(parents=True)
    (gh / "ci.yml").write_text(
        "name: CI\non: [push]\njobs:\n  lint:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: eslint src/\n  test:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: jest\n"
    )
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "paths": {"@/*": ["src/*"]}}}'
    )
    (root / "vitest.config.ts").write_text(
        "import { defineConfig } from 'vitest/config'\nexport default defineConfig({})\n"
    )
    (root / "forbidden.md").write_text("# Forbidden\n- no-any\n- no-console\n")
    agents = root / ".github" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "gc_agent.yml").write_text("name: GC Agent\nschedule: weekly\n")
    src = root / "src"
    src.mkdir()
    (src / "index.ts").write_text("export const main = () => {}\n")
    (src / "index.test.ts").write_text("test('main', () => {})\n")
    return root


def _make_typescript_project(root: Path) -> Path:
    """TypeScript 심층 분석 대상 프로젝트 (Phase 3 TS 필드 검증용)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# TS Project\n- rule1\n")
    (root / ".eslintrc.json").write_text(
        '{"extends": ["eslint:recommended", "@typescript-eslint/recommended",'
        ' "plugin:react/recommended"]}'
    )
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true,'
        ' "paths": {"@src/*": ["src/*"], "@test/*": ["test/*"]}}}'
    )
    (root / "vitest.config.ts").write_text("export default {}\n")
    for i in range(5):
        (root / f"comp{i}.test.ts").write_text(f"test('comp{i}', () => {{}})\n")
    for i in range(3):
        (root / f"util{i}.spec.ts").write_text(f"test('util{i}', () => {{}})\n")
    return root


def _make_empty_project(root: Path) -> Path:
    """완전 빈 프로젝트."""
    root.mkdir(parents=True, exist_ok=True)
    return root


# ─────────────────────────────────────────────────────────────────────────────
# T1: 엔드투엔드 파이프라인 테스트
# ─────────────────────────────────────────────────────────────────────────────

class TestT1EndToEndPipeline:
    """T1: Scanner → Score → Prescription → Report 전 파이프라인 정합성."""

    def test_t1_01_full_pipeline_minimal_project(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """최소 프로젝트의 전 파이프라인 실행 — 오류 없이 완주."""
        root = _make_minimal_project(tmp_path / "minimal")
        scan = Scanner(root).scan()
        score = engine.score(scan)
        _presc = PrescriptionEngine().prescribe(score, scan)
        report_path = ReportGenerator().generate(score, scan, out=str(tmp_path / "report.html"))
        html = report_path.read_text()

        assert 0 <= score.total <= 100
        assert score.grade in ("S", "A", "B", "C", "D")
        ce_items = {i.code: i for i in score.context_result.items}
        assert ce_items["CE-01"].passed, "AGENTS.md 있으므로 CE-01 통과"
        assert len(html) > 100

    def test_t1_02_pillar_sum_equals_total(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """기둥별 점수 합계 = total (5개 프로젝트 유형 모두)."""
        for name, factory in [
            ("empty", _make_empty_project),
            ("minimal", _make_minimal_project),
            ("partial", _make_partial_project),
            ("full", _make_full_project),
            ("ts", _make_typescript_project),
        ]:
            root = factory(tmp_path / name)
            scan = Scanner(root).scan()
            score = engine.score(scan)
            assert score.context_score + score.constraint_score + score.entropy_score == score.total, (
                f"[{name}] 기둥 합 ≠ total"
            )

    def test_t1_03_prescription_count_equals_failed_items(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """실패한 모든 항목에 대해 처방이 생성."""
        root = _make_minimal_project(tmp_path / "presc")
        scan = Scanner(root).scan()
        score = engine.score(scan)
        presc = PrescriptionEngine().prescribe(score, scan)

        failed = [i for r in score.all_audit_results for i in r.items if not i.passed]
        assert len(presc.prescriptions) == len(failed), (
            f"실패 항목 {len(failed)}개 vs 처방 {len(presc.prescriptions)}개"
        )

    def test_t1_04_report_html_contains_score_and_pillars(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """HTML 리포트에 점수·등급·기둥명 포함."""
        root = _make_partial_project(tmp_path / "report")
        scan = Scanner(root).scan()
        score = engine.score(scan)
        _presc = PrescriptionEngine().prescribe(score, scan)
        report_path = ReportGenerator().generate(score, scan, out=str(tmp_path / "report2.html"))
        html = report_path.read_text()

        assert str(score.total) in html
        assert score.grade in html
        # 리포트 HTML은 한국어 기둥명 사용
        for keyword in ("컨텍스트", "아키텍처", "엔트로피"):
            assert keyword in html, f"{keyword} HTML에 없음"

    def test_t1_05_full_project_scores_b_or_above(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """완전 구성 프로젝트는 B등급(60점) 이상."""
        root = _make_full_project(tmp_path / "full")
        scan = Scanner(root).scan()
        score = engine.score(scan)
        assert score.total >= 60, f"완전 구성 프로젝트 점수 {score.total} < 60"

    def test_t1_06_scan_result_json_serializable(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """HarnessScore.to_dict() 결과가 JSON 왕복 가능."""
        root = _make_partial_project(tmp_path / "serial")
        scan = Scanner(root).scan()
        score = engine.score(scan)

        d = score.to_dict()
        s = json.dumps(d, ensure_ascii=False)
        r = json.loads(s)
        assert r["total"] == score.total
        assert r["grade"] == score.grade


# ─────────────────────────────────────────────────────────────────────────────
# T2: 크로스 Phase 데이터 흐름 정합성
# ─────────────────────────────────────────────────────────────────────────────

class TestT2CrossPhaseDataFlow:
    """T2: Phase 1 → Phase 2 → Phase 3 데이터 흐름 및 필드 일관성."""

    def test_t2_01_phase1_fields_all_present(self, tmp_path: Path) -> None:
        """Phase 1 기본 필드 전부 ScanResult에 존재."""
        root = _make_partial_project(tmp_path / "p1")
        scan = Scanner(root).scan()

        for field in [
            "has_agents_md", "has_docs_dir", "has_session_bridge", "has_feature_list",
            "has_linter_config", "has_pre_commit", "has_ci_gate", "has_forbidden_patterns",
            "dependency_violations",
            "agents_md_staleness_days", "docs_avg_staleness_days",
            "invalid_agents_refs", "has_gc_agent", "bare_lint_suppression_ratio",
        ]:
            assert hasattr(scan, field), f"Phase 1 필드 누락: {field}"

    def test_t2_02_phase2_fields_with_correct_types(self, tmp_path: Path) -> None:
        """Phase 2 필드가 올바른 타입으로 초기화."""
        root = _make_minimal_project(tmp_path / "p2")
        scan = Scanner(root).scan()

        assert isinstance(scan.import_graph, dict)
        assert isinstance(scan.dependency_cycles, list)
        assert isinstance(scan.layer_violations, (set, frozenset, list))
        assert isinstance(scan.llm_over_engineering_score, float)
        assert isinstance(scan.llm_over_engineering_evidence, list)
        assert isinstance(scan.llm_analysis_cached, bool)
        assert isinstance(scan.scan_timestamp, str)
        assert isinstance(scan.go_module_name, str)
        assert isinstance(scan.java_build_tool, str)

    def test_t2_03_phase3_ts_fields_all_six_correct_types(self, tmp_path: Path) -> None:
        """Phase 3 TypeScript 필드 6개 존재 및 타입 정확."""
        root = _make_typescript_project(tmp_path / "ts")
        scan = Scanner(root).scan()

        assert isinstance(scan.ts_has_eslint, bool)
        assert isinstance(scan.ts_eslint_extends, list)
        assert isinstance(scan.ts_has_strict, bool)
        assert isinstance(scan.ts_has_path_aliases, bool)
        assert isinstance(scan.ts_test_files, int)
        assert isinstance(scan.ts_has_vitest_or_jest, bool)

    def test_t2_04_ts_fields_correctly_detected_values(self, tmp_path: Path) -> None:
        """TypeScript 프로젝트에서 TS 필드 값이 올바르게 감지."""
        root = _make_typescript_project(tmp_path / "ts_val")
        scan = Scanner(root).scan()

        assert scan.ts_has_eslint is True
        assert len(scan.ts_eslint_extends) >= 1
        assert scan.ts_has_strict is True
        assert scan.ts_has_path_aliases is True
        assert scan.ts_test_files >= 8
        assert scan.ts_has_vitest_or_jest is True

    def test_t2_05_api_response_all_six_ts_fields(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """수정 후: API 응답에 TypeScript 필드 6개 모두 포함."""
        root = _make_typescript_project(tmp_path / "ts_api")
        resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        assert resp.status_code == 200
        data = resp.json()

        for field in [
            "ts_has_eslint", "ts_eslint_extends", "ts_has_strict",
            "ts_has_path_aliases", "ts_test_files", "ts_has_vitest_or_jest",
        ]:
            assert field in data, f"API 응답 TS 필드 누락: {field}"

        assert data["ts_has_eslint"] is True
        assert isinstance(data["ts_eslint_extends"], list)
        assert data["ts_has_strict"] is True
        assert data["ts_has_path_aliases"] is True
        assert data["ts_test_files"] >= 8
        assert data["ts_has_vitest_or_jest"] is True

    def test_t2_06_scan_timestamp_iso_format(self, tmp_path: Path) -> None:
        """scan_timestamp가 ISO 8601 형식 (Phase 2)."""
        root = _make_minimal_project(tmp_path / "ts_stamp")
        scan = Scanner(root).scan()

        assert scan.scan_timestamp != ""
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", scan.scan_timestamp), (
            f"ISO 형식 불일치: {scan.scan_timestamp}"
        )

    def test_t2_07_ast_violations_affect_ac05_score(self, tmp_path: Path) -> None:
        """Phase 2 AST 의존성 위반이 AC-05 점수에 반영."""
        engine = ScoreEngine()
        base = tmp_path / "ast"

        # 위반 없는 ScanResult (dependency_violations는 int 카운트)
        scan_ok = ScanResult(target_path=base)
        scan_ok.dependency_violations = 0
        score_ok = engine.score(scan_ok)

        scan_viol = ScanResult(target_path=base)
        scan_viol.dependency_violations = 5  # 위반 5건 주입
        score_viol = engine.score(scan_viol)

        ac_ok = {i.code: i for i in score_ok.constraint_result.items}
        ac_viol = {i.code: i for i in score_viol.constraint_result.items}

        assert ac_ok["AC-05"].passed, "위반 없으면 AC-05 통과"
        assert not ac_viol["AC-05"].passed, "위반 있으면 AC-05 실패"


# ─────────────────────────────────────────────────────────────────────────────
# T3: 점수 결정론성 (CLI ↔ API 동등성)
# ─────────────────────────────────────────────────────────────────────────────

class TestT3ScoreDeterminism:
    """T3: 동일 프로젝트 반복·다중 경로 스캔 시 동일 결과 보장."""

    def test_t3_01_same_project_repeated_three_times(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """같은 프로젝트 3회 스캔 → 동일 점수."""
        root = _make_partial_project(tmp_path / "det")
        scores = [engine.score(Scanner(root).scan()).total for _ in range(3)]
        assert len(set(scores)) == 1, f"점수 불일치: {scores}"

    def test_t3_02_cli_and_api_same_score(
        self, api_client: TestClient, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """CLI 경로(ScoreEngine 직접)와 API 경로의 점수 동일."""
        root = _make_partial_project(tmp_path / "eq")
        score_cli = engine.score(Scanner(root).scan()).total

        resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        assert resp.status_code == 200
        score_api = resp.json()["total"]

        assert score_cli == score_api, f"CLI={score_cli} vs API={score_api}"

    def test_t3_03_grade_thresholds_correct(self, engine: ScoreEngine) -> None:
        """등급 경계값이 실제 _GRADE_BOUNDS(S≥90, A≥75, B≥60, C≥40, D<40)와 일치."""
        cases = [
            (100, "S"), (90, "S"), (89, "A"), (75, "A"),
            (74, "B"), (60, "B"), (59, "C"), (40, "C"),
            (39, "D"), (0, "D"),
        ]
        for total, expected in cases:
            grade, _ = engine._determine_grade(total)  # type: ignore[attr-defined]  # [EXCEPTION] 내부 메서드 — mypy 스텁 미등록이나 테스트 목적상 직접 호출
            assert grade == expected, f"점수 {total}: 기대={expected}, 실제={grade}"

    def test_t3_04_pillar_scores_sum_to_total_five_projects(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """3개 기둥 합 = total (5개 유형 프로젝트)."""
        for name, factory in [
            ("empty", _make_empty_project), ("minimal", _make_minimal_project),
            ("partial", _make_partial_project), ("full", _make_full_project),
            ("ts", _make_typescript_project),
        ]:
            root = factory(tmp_path / name)
            score = engine.score(Scanner(root).scan())
            s = score.context_score + score.constraint_score + score.entropy_score
            assert s == score.total, f"[{name}] {s} ≠ {score.total}"

    def test_t3_05_api_grade_matches_total_boundary(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """API grade가 total에 대한 실제 등급 경계를 준수."""
        root = _make_full_project(tmp_path / "gc")
        resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        assert resp.status_code == 200
        data = resp.json()
        total, grade = data["total"], data["grade"]

        for g, (low, high) in _GRADE_MAP.items():
            if low <= total <= high:
                assert grade == g, f"total={total} → 기대={g}, 실제={grade}"
                break


# ─────────────────────────────────────────────────────────────────────────────
# T4: 경계값 / 적대적 입력
# ─────────────────────────────────────────────────────────────────────────────

class TestT4BoundaryAndAdversarial:
    """T4: 극단적·비정상 입력에서도 시스템 안정 동작."""

    def test_t4_01_empty_project_low_score(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """빈 프로젝트는 낮은 점수(D 등급 기준 40 미만)여야 한다."""
        root = _make_empty_project(tmp_path / "empty")
        score = engine.score(Scanner(root).scan())
        assert score.total < 40, f"빈 프로젝트 점수 {score.total} ≥ 40"
        failed = [i for r in score.all_audit_results for i in r.items if not i.passed]
        assert len(failed) >= 10

    def test_t4_02_api_404_for_nonexistent_path(self, api_client: TestClient) -> None:
        resp = api_client.post("/api/v1/scan", json={"path": "/nonexistent/xyz99999"})
        assert resp.status_code == 404

    def test_t4_03_api_400_for_file_path(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        f = tmp_path / "x.txt"
        f.write_text("data")
        assert api_client.post("/api/v1/scan", json={"path": str(f)}).status_code == 400

    def test_t4_04_deeply_nested_dirs_no_crash(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """깊게 중첩된 디렉토리 구조도 안정 스캔."""
        root = tmp_path / "nested"
        deep = root
        for i in range(10):
            deep = deep / f"L{i}"
        deep.mkdir(parents=True)
        (root / "AGENTS.md").write_text("# Nested\n")
        score = engine.score(Scanner(root).scan())
        assert 0 <= score.total <= 100

    def test_t4_05_malformed_tsconfig_no_crash(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """손상된 tsconfig.json도 크래시 없이 처리."""
        root = tmp_path / "malformed"
        root.mkdir()
        (root / "AGENTS.md").write_text("# Malformed\n")
        (root / "tsconfig.json").write_text("{ NOT VALID JSON }")
        score = engine.score(Scanner(root).scan())
        assert 0 <= score.total <= 100

    def test_t4_06_large_agents_md_handled(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """5000줄 AGENTS.md도 정상 처리."""
        root = tmp_path / "large"
        root.mkdir()
        (root / "AGENTS.md").write_text("# Large\n" + "\n".join(
            [f"- Rule {i}: constraint{i}" for i in range(5000)]
        ))
        scan = Scanner(root).scan()
        assert scan.has_agents_md is True
        assert 0 <= engine.score(scan).total <= 100

    def test_t4_07_two_projects_no_state_contamination(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """두 프로젝트 연속 스캔 시 결과 오염 없음."""
        root_a = _make_minimal_project(tmp_path / "A")
        root_b = _make_full_project(tmp_path / "B")
        scan_a = Scanner(root_a).scan()
        scan_b = Scanner(root_b).scan()
        score_a = engine.score(scan_a)
        score_b = engine.score(scan_b)
        assert score_b.total > score_a.total, "full > minimal 이어야 함"

    def test_t4_08_score_engine_contract_100pts(self) -> None:
        """ScoreEngine 배점 합이 항상 100점."""
        eng = ScoreEngine()
        if hasattr(eng, "_auditors"):
            total = sum(
                getattr(a, "full_score", 0) for a in eng._auditors  # type: ignore[attr-defined]  # [EXCEPTION] _auditors는 ScoreEngine 내부 속성 — 배점 계약 검증 목적
            )
            assert total == 100, f"배점 합 {total} ≠ 100"


# ─────────────────────────────────────────────────────────────────────────────
# T5: 스코어링 무결성
# ─────────────────────────────────────────────────────────────────────────────

class TestT5ScoringIntegrity:
    """T5: 단조성, 기둥 독립성, 처방-점수 정합성 검증."""

    def test_t5_01_monotone_score_increase(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """항목 충족이 많을수록 점수 비감소 (단조성)."""
        projects = [
            ("empty", _make_empty_project),
            ("minimal", _make_minimal_project),
            ("partial", _make_partial_project),
            ("full", _make_full_project),
        ]
        scores = []
        for name, factory in projects:
            root = factory(tmp_path / name)
            scores.append(engine.score(Scanner(root).scan()).total)

        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], (
                f"단조성 위반: [{projects[i][0]}]{scores[i]} > [{projects[i+1][0]}]{scores[i+1]}"
            )

    def test_t5_02_ce_pillar_independent_of_ac(self, tmp_path: Path) -> None:
        """CE 기둥 점수는 AC 항목 변경에 무관 (기둥 독립성)."""
        engine = ScoreEngine()
        root_ce = _make_minimal_project(tmp_path / "ce")
        root_ceac = _make_minimal_project(tmp_path / "ceac")
        (root_ceac / ".eslintrc.json").write_text('{}')

        score_ce = engine.score(Scanner(root_ce).scan())
        score_ceac = engine.score(Scanner(root_ceac).scan())

        assert score_ce.context_score == score_ceac.context_score, "CE 기둥이 AC 추가로 변해선 안 됨"
        assert score_ce.constraint_score < score_ceac.constraint_score, "AC는 린터 추가 시 증가해야 함"

    def test_t5_03_prescription_impact_equals_full_score(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """각 처방의 impact = 해당 실패 항목의 full_score."""
        root = _make_minimal_project(tmp_path / "impact")
        scan = Scanner(root).scan()
        score = engine.score(scan)
        presc = PrescriptionEngine().prescribe(score, scan)

        failed_map = {
            i.code: i.full_score
            for r in score.all_audit_results
            for i in r.items if not i.passed
        }
        for p in presc.prescriptions:
            assert p.impact == failed_map[p.code], (
                f"[{p.code}] impact={p.impact} vs full_score={failed_map[p.code]}"
            )

    def test_t5_04_five_patterns_always_evaluated(
        self, tmp_path: Path, engine: ScoreEngine
    ) -> None:
        """5대 패턴이 항상 평가 (실제 패턴명 기준)."""
        root = _make_empty_project(tmp_path / "pat")
        score = engine.score(Scanner(root).scan())
        names = {pr.pattern for pr in score.pattern_risks}
        assert names == _EXPECTED_PATTERNS, f"패턴 불일치: {names}"

    def test_t5_05_api_audit_items_exactly_15(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """API 응답 진단 항목 수 = 정확히 15개."""
        root = _make_partial_project(tmp_path / "15")
        resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        assert resp.status_code == 200
        data = resp.json()
        total = (
            len(data["context"]["items"])
            + len(data["constraint"]["items"])
            + len(data["entropy"]["items"])
        )
        assert total == 15, f"항목 수 {total} ≠ 15"

    def test_t5_06_api_pillar_full_scores_ce40_ac35_em25(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """API 응답 기둥 full_score: CE=40, AC=35, EM=25."""
        root = _make_minimal_project(tmp_path / "fs")
        resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["context"]["full_score"] == 40
        assert data["constraint"]["full_score"] == 35
        assert data["entropy"]["full_score"] == 25

    def test_t5_07_version_consistent_across_api_endpoints(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """scan 응답 hachilles_version = health 응답 version = __version__."""
        from hachilles import __version__
        root = _make_minimal_project(tmp_path / "ver")
        scan_resp = api_client.post("/api/v1/scan", json={"path": str(root)})
        health_resp = api_client.get("/api/health")
        assert scan_resp.status_code == 200
        assert scan_resp.json()["hachilles_version"] == __version__
        assert health_resp.json()["version"] == __version__

    def test_t5_08_generate_agents_returns_structured_content(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """AGENTS.md 생성 엔드포인트가 구조화된 콘텐츠 반환."""
        root = _make_partial_project(tmp_path / "agents")
        resp = api_client.post(
            "/api/v1/generate-agents",
            json={"path": str(root), "project_name": "TestProject"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data and "sections" in data and "estimated_lines" in data
        assert len(data["content"]) > 100
        assert data["estimated_lines"] > 0

    def test_t5_09_history_endpoint_valid_structure(
        self, api_client: TestClient, tmp_path: Path
    ) -> None:
        """이력 없는 프로젝트의 /history도 유효 구조 반환."""
        root = _make_minimal_project(tmp_path / "hist")
        resp = api_client.get("/api/v1/history", params={"path": str(root)})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["records"], list)
        assert isinstance(data["trend"], list)
        assert "project_path" in data
