"""Type-1: Property-based Testing (Hypothesis)

임의 생성된 ScanResult 입력에 대해 ScoreEngine의 불변 속성(invariant)이
항상 성립하는지 검증한다.

검증 대상 불변 속성:
  INV-01: 0 ≤ total ≤ 100
  INV-02: grade ∈ {S, A, B, C, D}
  INV-03: pattern_risks 는 정확히 5개
  INV-04: context_score + constraint_score + entropy_score == total
  INV-05: 각 AuditItem의 score ≤ full_score
  INV-06: 동일 입력 → 동일 출력 (결정론적)
  INV-07: passed_rate ∈ [0.0, 1.0]
  INV-08: to_dict()는 json.dumps()로 직렬화 가능
"""

from __future__ import annotations

import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hachilles.models.scan_result import ScanResult
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()


def _make_scan(
    tmp_path,
    has_agents_md, agents_md_lines, has_docs_dir,
    has_architecture_md, has_conventions_md, has_adr_dir,
    has_session_bridge, has_feature_list,
    has_linter_config, has_pre_commit, has_ci_gate,
    has_forbidden_patterns, dependency_violations,
    agents_md_staleness_days, docs_avg_staleness_days,
    n_invalid_refs, has_gc_agent, bare_lint_suppression_ratio,
    n_docs_files,
) -> ScanResult:
    scan = ScanResult(target_path=tmp_path)
    scan.has_agents_md = has_agents_md
    scan.agents_md_lines = agents_md_lines
    scan.has_docs_dir = has_docs_dir
    scan.has_architecture_md = has_architecture_md
    scan.has_conventions_md = has_conventions_md
    scan.has_adr_dir = has_adr_dir
    scan.has_session_bridge = has_session_bridge
    scan.has_feature_list = has_feature_list
    scan.has_linter_config = has_linter_config
    scan.has_pre_commit = has_pre_commit
    scan.has_ci_gate = has_ci_gate
    scan.has_forbidden_patterns = has_forbidden_patterns
    scan.dependency_violations = dependency_violations
    scan.agents_md_staleness_days = agents_md_staleness_days
    scan.docs_avg_staleness_days = docs_avg_staleness_days
    scan.invalid_agents_refs = [f"ref_{i}" for i in range(n_invalid_refs)]
    scan.has_gc_agent = has_gc_agent
    scan.bare_lint_suppression_ratio = bare_lint_suppression_ratio
    scan.docs_files = [tmp_path / f"doc_{i}.md" for i in range(n_docs_files)]
    return scan


@given(
    has_agents_md               = st.booleans(),
    agents_md_lines             = st.integers(min_value=0, max_value=5000),
    has_docs_dir                = st.booleans(),
    has_architecture_md         = st.booleans(),
    has_conventions_md          = st.booleans(),
    has_adr_dir                 = st.booleans(),
    has_session_bridge          = st.booleans(),
    has_feature_list            = st.booleans(),
    has_linter_config           = st.booleans(),
    has_pre_commit              = st.booleans(),
    has_ci_gate                 = st.booleans(),
    has_forbidden_patterns      = st.booleans(),
    dependency_violations       = st.integers(min_value=0, max_value=20),
    agents_md_staleness_days    = st.one_of(st.none(), st.integers(min_value=0, max_value=365)),
    docs_avg_staleness_days     = st.one_of(st.none(), st.floats(min_value=0.0, max_value=365.0,
                                                                  allow_nan=False, allow_infinity=False)),
    n_invalid_refs              = st.integers(min_value=0, max_value=10),
    has_gc_agent                = st.booleans(),
    bare_lint_suppression_ratio = st.floats(min_value=0.0, max_value=1.0,
                                            allow_nan=False, allow_infinity=False),
    n_docs_files                = st.integers(min_value=0, max_value=10),
)
@settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_invariants_hold_for_any_input(
    tmp_path,
    has_agents_md, agents_md_lines, has_docs_dir,
    has_architecture_md, has_conventions_md, has_adr_dir,
    has_session_bridge, has_feature_list,
    has_linter_config, has_pre_commit, has_ci_gate,
    has_forbidden_patterns, dependency_violations,
    agents_md_staleness_days, docs_avg_staleness_days,
    n_invalid_refs, has_gc_agent, bare_lint_suppression_ratio,
    n_docs_files,
):
    scan = _make_scan(
        tmp_path,
        has_agents_md, agents_md_lines, has_docs_dir,
        has_architecture_md, has_conventions_md, has_adr_dir,
        has_session_bridge, has_feature_list,
        has_linter_config, has_pre_commit, has_ci_gate,
        has_forbidden_patterns, dependency_violations,
        agents_md_staleness_days, docs_avg_staleness_days,
        n_invalid_refs, has_gc_agent, bare_lint_suppression_ratio,
        n_docs_files,
    )

    result = ENGINE.score(scan)

    # INV-01: 총점 범위
    assert 0 <= result.total <= 100, f"INV-01 위반: total={result.total}"

    # INV-02: 등급 유효성
    assert result.grade in {"S", "A", "B", "C", "D"}, f"INV-02 위반: grade={result.grade}"

    # INV-03: 패턴 리스크 5개
    assert len(result.pattern_risks) == 5, f"INV-03 위반: {len(result.pattern_risks)}개"

    # INV-04: 기둥 점수 합 == 총점
    pillar_sum = result.context_score + result.constraint_score + result.entropy_score
    assert pillar_sum == result.total, f"INV-04 위반: {pillar_sum} ≠ {result.total}"

    # INV-05: 항목 score ≤ full_score
    for audit_result in result.all_audit_results:
        for item in audit_result.items:
            assert item.score <= item.full_score, (
                f"INV-05 위반: {item.code} score={item.score} > full_score={item.full_score}"
            )

    # INV-06: 결정론적
    result2 = ENGINE.score(scan)
    assert result.total == result2.total, "INV-06 위반: 비결정론적 동작"

    # INV-07: passed_rate 범위
    assert 0.0 <= result.passed_rate <= 1.0, f"INV-07 위반: passed_rate={result.passed_rate}"

    # INV-08: JSON 직렬화 가능
    try:
        json.dumps(result.to_dict())
    except (TypeError, ValueError) as e:
        raise AssertionError(f"INV-08 위반: to_dict() JSON 직렬화 실패 — {e}")
