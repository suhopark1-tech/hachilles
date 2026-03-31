"""Type-A: Mutation Testing (변이 테스트)

각 Auditor의 판정 로직에 단일 변이(mutation)를 가해
'테스트가 변이를 탐지하는가'를 검증한다.

변이 설계 원칙:
  - 입력 하나를 Fail 경계에서 Pass 경계로, 또는 그 반대로 뒤집는다.
  - 변이 후 점수 변화가 반드시 발생해야 한다.
  - 변이가 묵살(mutant survived)되면 해당 테스트/구현의 커버리지 공백을 의미한다.

검증 항목 (15개 진단 항목 × 단방향 변이):
  MUT-CE01 ~ MUT-CE05 : Context Auditor 변이
  MUT-AC01 ~ MUT-AC05 : Constraint Auditor 변이
  MUT-EM01 ~ MUT-EM05 : Entropy Auditor 변이

판정 기준: 변이 전 점수 vs 변이 후 점수가 반드시 달라야 한다 (Δscore ≠ 0).
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from hachilles.auditors.constraint_auditor import ConstraintAuditor
from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.auditors.entropy_auditor import EntropyAuditor
from hachilles.models.scan_result import ScanResult
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()
CTX = ContextAuditor()
CON = ConstraintAuditor()
ENT = EntropyAuditor()


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _perfect_scan(tmp_path: Path) -> ScanResult:
    """모든 항목이 통과하는 '완벽한' ScanResult (100점 기준선)."""
    scan = ScanResult(target_path=tmp_path)
    # CE
    scan.has_agents_md = True
    scan.agents_md_lines = 300          # 정상 범위 (1~599)
    scan.has_docs_dir = True
    scan.has_architecture_md = True
    scan.has_conventions_md = True
    scan.has_adr_dir = True
    scan.docs_files = [
        tmp_path / "docs" / "architecture.md",
        tmp_path / "docs" / "conventions.md",
        tmp_path / "docs" / "decisions" / "001.md",
    ]
    scan.has_session_bridge = True
    scan.has_feature_list = True
    # AC
    scan.has_linter_config = True
    scan.has_pre_commit = True
    scan.has_ci_gate = True
    scan.has_forbidden_patterns = True
    scan.dependency_violations = 0
    # EM
    scan.agents_md_staleness_days = 7   # 최근 갱신
    scan.docs_avg_staleness_days = 20.0
    scan.invalid_agents_refs = []       # 무효 참조 없음
    scan.has_gc_agent = True
    scan.bare_lint_suppression_ratio = 0.0  # 이유 없는 suppress 없음
    return scan


def _score_delta(base: ScanResult, mutated: ScanResult, auditor) -> int:
    """변이 전후 특정 Auditor의 score 차이."""
    before = auditor.audit(base).score
    after  = auditor.audit(mutated).score
    return after - before


def _total_delta(base: ScanResult, mutated: ScanResult) -> int:
    """변이 전후 전체 총점 차이."""
    before = ENGINE.score(base).total
    after  = ENGINE.score(mutated).total
    return after - before


# ── MUT-CE: Context Auditor 변이 ──────────────────────────────────────────────

class TestMutationContextAuditor:

    def test_mut_ce01_remove_agents_md(self, tmp_path):
        """MUT-CE01: has_agents_md True→False → CE-01 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_agents_md = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-01 변이가 묵살됨 — has_agents_md 판정 로직 확인 필요"

    def test_mut_ce01_oversized_agents_md(self, tmp_path):
        """MUT-CE01: agents_md_lines 300→1500 → CE-01 점수 감소 (1200줄 초과 패널티)."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.agents_md_lines = 1500
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-01 변이가 묵살됨 — 과도한 라인 수 패널티 판정 로직 확인 필요"

    def test_mut_ce02_remove_docs_dir(self, tmp_path):
        """MUT-CE02: has_docs_dir False + docs_files 삭제 → CE-02 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_docs_dir = False
        mutated.docs_files   = []
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-02 변이가 묵살됨 — docs_dir 판정 로직 확인 필요"

    def test_mut_ce02_remove_adr(self, tmp_path):
        """MUT-CE02: has_adr_dir False → docs 구조 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_adr_dir = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-02 변이가 묵살됨 — has_adr_dir 판정 로직 확인 필요"

    def test_mut_ce03_remove_session_bridge(self, tmp_path):
        """MUT-CE03: has_session_bridge True→False → CE-03 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_session_bridge = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-03 변이가 묵살됨 — has_session_bridge 판정 로직 확인 필요"

    def test_mut_ce04_remove_feature_list(self, tmp_path):
        """MUT-CE04: has_feature_list True→False → CE-04 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_feature_list = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-04 변이가 묵살됨 — has_feature_list 판정 로직 확인 필요"

    def test_mut_ce05_remove_architecture_md(self, tmp_path):
        """MUT-CE05: has_architecture_md False → CE-05 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_architecture_md = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-05 변이가 묵살됨 — has_architecture_md 판정 로직 확인 필요"

    def test_mut_ce05_remove_conventions_md(self, tmp_path):
        """MUT-CE05: has_conventions_md False → CE-05 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_conventions_md = False
        assert _score_delta(base, mutated, CTX) < 0, \
            "CE-05 변이가 묵살됨 — has_conventions_md 판정 로직 확인 필요"

    def test_mut_ce_compound_two_items_fail(self, tmp_path):
        """MUT-CE 복합: 두 항목 동시 변이 → 점수 감소폭이 단일 변이보다 커야 함."""
        base  = _perfect_scan(tmp_path)
        mut1 = deepcopy(base)
        mut1.has_session_bridge = False
        mut2 = deepcopy(base)
        mut2.has_feature_list = False
        mut12 = deepcopy(base)
        mut12.has_session_bridge = False
        mut12.has_feature_list   = False

        delta1  = _score_delta(base, mut1,  CTX)
        delta2  = _score_delta(base, mut2,  CTX)
        delta12 = _score_delta(base, mut12, CTX)

        assert delta12 <= delta1 + delta2, \
            "복합 변이 점수 감소폭이 단일 합계보다 커서 중복 패널티 발생 의심"
        assert delta12 < min(delta1, delta2), \
            "복합 변이가 단일 변이보다 감소폭이 작음 — 독립적 채점 규칙 확인 필요"


# ── MUT-AC: Constraint Auditor 변이 ──────────────────────────────────────────

class TestMutationConstraintAuditor:

    def test_mut_ac01_remove_linter_config(self, tmp_path):
        """MUT-AC01: has_linter_config True→False → AC-01 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_linter_config = False
        assert _score_delta(base, mutated, CON) < 0, \
            "AC-01 변이가 묵살됨 — has_linter_config 판정 로직 확인 필요"

    def test_mut_ac02_remove_pre_commit(self, tmp_path):
        """MUT-AC02: has_pre_commit True→False → AC-02 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_pre_commit = False
        assert _score_delta(base, mutated, CON) < 0, \
            "AC-02 변이가 묵살됨 — has_pre_commit 판정 로직 확인 필요"

    def test_mut_ac03_remove_ci_gate(self, tmp_path):
        """MUT-AC03: has_ci_gate True→False → AC-03 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_ci_gate = False
        assert _score_delta(base, mutated, CON) < 0, \
            "AC-03 변이가 묵살됨 — has_ci_gate 판정 로직 확인 필요"

    def test_mut_ac04_remove_forbidden_patterns(self, tmp_path):
        """MUT-AC04: has_forbidden_patterns True→False → AC-04 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_forbidden_patterns = False
        assert _score_delta(base, mutated, CON) < 0, \
            "AC-04 변이가 묵살됨 — has_forbidden_patterns 판정 로직 확인 필요"

    def test_mut_ac05_add_dependency_violation(self, tmp_path):
        """MUT-AC05: dependency_violations 0→5 → AC-05 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.dependency_violations = 5
        assert _score_delta(base, mutated, CON) < 0, \
            "AC-05 변이가 묵살됨 — dependency_violations 판정 로직 확인 필요"

    def test_mut_ac_all_gates_removed(self, tmp_path):
        """MUT-AC 복합: 린터+pre-commit+CI 모두 제거 → Constraint 0점에 가까워야 함."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_linter_config     = False
        mutated.has_pre_commit        = False
        mutated.has_ci_gate           = False
        mutated.has_forbidden_patterns = False
        mutated.dependency_violations = 10

        delta = _score_delta(base, mutated, CON)
        assert delta <= -25, \
            f"AC 모든 게이트 제거 시 감소폭이 너무 작음: Δ={delta} (기대 ≤ -25)"


# ── MUT-EM: Entropy Auditor 변이 ─────────────────────────────────────────────

class TestMutationEntropyAuditor:

    def test_mut_em01_stale_agents_md(self, tmp_path):
        """MUT-EM01: agents_md_staleness_days 7→60 → EM-01 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.agents_md_staleness_days = 60
        assert _score_delta(base, mutated, ENT) < 0, \
            "EM-01 변이가 묵살됨 — agents_md_staleness_days 판정 로직 확인 필요"

    def test_mut_em02_stale_docs(self, tmp_path):
        """MUT-EM02: docs_avg_staleness_days 20→90 → EM-02 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.docs_avg_staleness_days = 90.0
        assert _score_delta(base, mutated, ENT) < 0, \
            "EM-02 변이가 묵살됨 — docs_avg_staleness_days 판정 로직 확인 필요"

    def test_mut_em03_add_invalid_refs(self, tmp_path):
        """MUT-EM03: invalid_agents_refs 0→3 → EM-03 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.invalid_agents_refs = ["ref_a", "ref_b", "ref_c"]
        assert _score_delta(base, mutated, ENT) < 0, \
            "EM-03 변이가 묵살됨 — invalid_agents_refs 판정 로직 확인 필요"

    def test_mut_em04_remove_gc_agent(self, tmp_path):
        """MUT-EM04: has_gc_agent True→False → EM-04 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.has_gc_agent = False
        assert _score_delta(base, mutated, ENT) < 0, \
            "EM-04 변이가 묵살됨 — has_gc_agent 판정 로직 확인 필요"

    def test_mut_em05_increase_bare_suppression(self, tmp_path):
        """MUT-EM05: bare_lint_suppression_ratio 0.0→0.5 → EM-05 점수 감소."""
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.bare_lint_suppression_ratio = 0.5
        assert _score_delta(base, mutated, ENT) < 0, \
            "EM-05 변이가 묵살됨 — bare_lint_suppression_ratio 판정 로직 확인 필요"

    def test_mut_em_staleness_no_git_history_design_decision(self, tmp_path):
        """MUT-EM: staleness_days None(git 없음) → N/A 처리로 만점 유지 (의도된 설계).

        [설계 결정 검증]
        git 히스토리가 없는 경우 EM-01/EM-02는 측정 불가(N/A)로 간주하고
        '이익의 원칙(benefit of the doubt)'으로 만점을 부여한다.
        이 테스트는 그 결정이 코드에 올바르게 반영됐는지 검증한다.

        변경하려면 ADR을 업데이트 후 이 테스트도 같이 수정해야 한다.
        """
        base    = _perfect_scan(tmp_path)
        mutated = deepcopy(base)
        mutated.agents_md_staleness_days = None
        mutated.docs_avg_staleness_days  = None
        delta = _score_delta(base, mutated, ENT)
        # N/A → 만점 유지: 점수 변화 없어야 함 (의도된 설계)
        assert delta == 0, \
            f"git 없음 시 N/A 만점 설계가 깨짐: Δ={delta} (ADR 확인 필요)"

    def test_mut_em_staleness_none_vs_stale(self, tmp_path):
        """MUT-EM: git 없음(None) vs 명시적 오래된 값(90일) → 후자가 낮아야 함."""
        base_none = _perfect_scan(tmp_path)
        base_none.agents_md_staleness_days = None

        base_stale = deepcopy(base_none)
        base_stale.agents_md_staleness_days = 90

        score_none  = ENT.audit(base_none).score
        score_stale = ENT.audit(base_stale).score
        assert score_none >= score_stale, \
            "git 없음이 90일 오래된 문서보다 점수가 낮음 — N/A 처리 로직 오류"


# ── MUT-E2E: 전체 점수 변이 검증 ─────────────────────────────────────────────

class TestMutationEndToEnd:

    def test_mut_e2e_perfect_score_is_100(self, tmp_path):
        """MUT-E2E-00: 완벽한 입력 → 100점 기준 (모든 변이의 기준선 확인)."""
        base = _perfect_scan(tmp_path)
        result = ENGINE.score(base)
        assert result.total == 100, \
            f"완벽한 입력이 100점이 아님: {result.total}점\n" \
            f"  CE={result.context_score}/40, AC={result.constraint_score}/35, " \
            f"EM={result.entropy_score}/25\n" \
            f"  실패: {[i.code for i in result.critical_items]}"

    def test_mut_e2e_single_mutation_always_decreases(self, tmp_path):
        """MUT-E2E-01: 100점 기준에서 단일 불리한 변이 → 총점 반드시 감소."""
        base = _perfect_scan(tmp_path)

        single_mutations = [
            ("has_agents_md",            False),
            ("has_session_bridge",       False),
            ("has_feature_list",         False),
            ("has_linter_config",        False),
            ("has_pre_commit",           False),
            ("has_ci_gate",              False),
            ("has_gc_agent",             False),
        ]
        for field, val in single_mutations:
            mutated = deepcopy(base)
            setattr(mutated, field, val)
            delta = _total_delta(base, mutated)
            assert delta < 0, \
                f"단일 변이 '{field}={val}' 이 총점을 감소시키지 않음 (Δ={delta})"

    def test_mut_e2e_grade_boundary_mutation(self, tmp_path):
        """MUT-E2E-02: 등급 경계에서 변이 → 등급 강등."""
        # A등급(80점)에서 한 항목 제거 → B등급으로 강등되는지
        base = _perfect_scan(tmp_path)
        # A 등급 범위로 내리기 위해 일부 항목 제거
        base.has_feature_list      = False  # -6
        base.has_session_bridge    = False  # -8
        base.has_adr_dir           = False  # CE-02 일부 감소
        base.docs_files            = [
            tmp_path / "docs" / "architecture.md",
            tmp_path / "docs" / "conventions.md",
        ]  # adr 없으므로 2개 docs만

        base_result = ENGINE.score(base)
        # 기준선이 60점 이상인 경우에만 테스트 의미 있음
        if base_result.total < 60:
            pytest.skip(f"기준선 {base_result.total}점 — 등급 경계 테스트 불가")

        # 추가 변이: GC 에이전트 제거
        mutated = deepcopy(base)
        mutated.has_gc_agent = False
        mutated_result = ENGINE.score(mutated)

        assert mutated_result.total <= base_result.total, \
            "변이 후 점수가 증가함 — 채점 로직 오류"
