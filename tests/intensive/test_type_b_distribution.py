"""Type-B: Statistical Distribution Testing (점수 분포 통계 테스트)

1,000개 무작위 ScanResult를 생성하여 ScoreEngine의 점수 분포 특성을 검증한다.

검증 목표:
  DIST-01: 점수 범위 엄격 준수 — 모든 점수 ∈ [0, 100]
  DIST-02: 단조성 — 양성 변화가 누적될수록 점수는 비감소
  DIST-03: 분포 균형 — 점수가 한쪽 극단(0 또는 100)에만 몰리지 않음
  DIST-04: 독립성 — 기둥 간 점수 계산이 서로 간섭하지 않음
  DIST-05: 등급 일관성 — grade 문자열이 total 점수와 항상 일치
  DIST-06: 직렬화 안전성 — to_dict() 결과가 항상 JSON 직렬화 가능
  DIST-07: 결정론적 안정성 — 동일 입력 → 동일 결과 (반복 실행)
  DIST-08: 패턴 위험도 커버리지 — 5개 패턴 전부 항상 반환
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from hachilles.models.scan_result import RiskLevel, ScanResult
from hachilles.score import ScoreEngine

ENGINE = ScoreEngine()
RANDOM_SEED = 42
N_SAMPLES   = 1_000


# ── ScanResult 랜덤 생성기 ────────────────────────────────────────────────────

def _random_scan(tmp_path: Path, rng: random.Random) -> ScanResult:
    """완전 무작위 ScanResult 생성 (seed 제어 가능)."""
    scan = ScanResult(target_path=tmp_path)

    # CE
    scan.has_agents_md       = rng.choice([True, False])
    scan.agents_md_lines     = rng.randint(0, 3000)
    scan.has_docs_dir        = rng.choice([True, False])
    scan.has_architecture_md = rng.choice([True, False])
    scan.has_conventions_md  = rng.choice([True, False])
    scan.has_adr_dir         = rng.choice([True, False])
    n_docs = rng.randint(0, 5)
    scan.docs_files = [tmp_path / f"docs/doc{i}.md" for i in range(n_docs)]
    scan.has_session_bridge  = rng.choice([True, False])
    scan.has_feature_list    = rng.choice([True, False])

    # AC
    scan.has_linter_config      = rng.choice([True, False])
    scan.has_pre_commit         = rng.choice([True, False])
    scan.has_ci_gate            = rng.choice([True, False])
    scan.has_forbidden_patterns = rng.choice([True, False])
    scan.dependency_violations  = rng.randint(0, 20)

    # EM
    if rng.random() < 0.8:
        scan.agents_md_staleness_days = rng.randint(0, 200)
    else:
        scan.agents_md_staleness_days = None

    if rng.random() < 0.8:
        scan.docs_avg_staleness_days = rng.uniform(0, 200)
    else:
        scan.docs_avg_staleness_days = None

    n_invalid = rng.randint(0, 10)
    scan.invalid_agents_refs        = [f"ref_{i}" for i in range(n_invalid)]
    scan.has_gc_agent               = rng.choice([True, False])
    scan.bare_lint_suppression_ratio = rng.uniform(0.0, 1.0)

    return scan


def _generate_sample_set(tmp_path: Path, n: int = N_SAMPLES) -> list:
    """seed 고정 난수로 N개 (scan, score) 쌍을 생성."""
    rng = random.Random(RANDOM_SEED)
    results = []
    for _ in range(n):
        scan = _random_scan(tmp_path, rng)
        score = ENGINE.score(scan)
        results.append((scan, score))
    return results


# ── DIST-01: 점수 범위 ────────────────────────────────────────────────────────

class TestDistributionRange:

    def test_dist01_all_scores_in_0_100(self, tmp_path):
        """DIST-01: 1,000개 무작위 입력 → 모든 총점 [0, 100]."""
        samples = _generate_sample_set(tmp_path)
        violations = [
            (i, s.total)
            for i, (_, s) in enumerate(samples)
            if not (0 <= s.total <= 100)
        ]
        assert not violations, \
            f"범위 위반 {len(violations)}건: {violations[:5]}"

    def test_dist01_pillar_scores_within_bounds(self, tmp_path):
        """DIST-01b: 기둥별 점수도 각 만점 이내."""
        samples = _generate_sample_set(tmp_path)
        for i, (_, s) in enumerate(samples):
            assert 0 <= s.context_score    <= 40, f"[{i}] CE={s.context_score}"
            assert 0 <= s.constraint_score <= 35, f"[{i}] AC={s.constraint_score}"
            assert 0 <= s.entropy_score    <= 25, f"[{i}] EM={s.entropy_score}"

    def test_dist01_total_equals_pillar_sum(self, tmp_path):
        """DIST-01c: total == CE + AC + EM (항상 성립)."""
        samples = _generate_sample_set(tmp_path)
        violations = [
            (i, s.total, s.context_score + s.constraint_score + s.entropy_score)
            for i, (_, s) in enumerate(samples)
            if s.total != s.context_score + s.constraint_score + s.entropy_score
        ]
        assert not violations, \
            f"합산 불일치 {len(violations)}건: {violations[:3]}"


# ── DIST-02: 단조성 ──────────────────────────────────────────────────────────

class TestDistributionMonotonicity:

    def test_dist02_adding_positive_attribute_never_decreases(self, tmp_path):
        """DIST-02: 불리한 속성을 제거하면 점수가 감소하지 않는다.

        무작위 1,000쌍을 생성해 'better vs worse' 비교를 수행한다.
        """
        rng = random.Random(RANDOM_SEED + 1)
        violations = []

        for trial in range(200):  # 200회 비교
            # "worse" 기준 ScanResult
            worse = _random_scan(tmp_path, rng)
            from copy import deepcopy
            better = deepcopy(worse)

            # 무작위로 하나의 개선을 적용
            improvement = rng.choice([
                ("has_agents_md",            True),
                ("has_session_bridge",       True),
                ("has_feature_list",         True),
                ("has_linter_config",        True),
                ("has_pre_commit",           True),
                ("has_ci_gate",              True),
                ("has_gc_agent",             True),
                ("has_forbidden_patterns",   True),
            ])
            field_name, val = improvement
            setattr(better, field_name, val)

            score_worse  = ENGINE.score(worse).total
            score_better = ENGINE.score(better).total

            if score_better < score_worse:
                violations.append((trial, field_name, score_worse, score_better))

        assert not violations, \
            f"단조성 위반 {len(violations)}건 (200회 중): {violations[:3]}"

    def test_dist02_removing_dependency_violations_never_hurts(self, tmp_path):
        """DIST-02b: dependency_violations 감소 → 점수 비감소."""
        from copy import deepcopy
        rng = random.Random(RANDOM_SEED + 2)
        violations = []

        for _ in range(100):
            base = _random_scan(tmp_path, rng)
            if base.dependency_violations <= 0:
                continue
            improved = deepcopy(base)
            improved.dependency_violations = max(0, base.dependency_violations - 1)

            s_base     = ENGINE.score(base).total
            s_improved = ENGINE.score(improved).total
            if s_improved < s_base:
                violations.append((s_base, s_improved))

        assert not violations, \
            f"의존성 위반 감소 단조성 위반: {violations[:3]}"


# ── DIST-03: 분포 균형 ───────────────────────────────────────────────────────

class TestDistributionBalance:

    def test_dist03_score_distribution_not_all_zero(self, tmp_path):
        """DIST-03a: 1,000개 중 0점이 50% 이상이면 채점 편향 의심."""
        samples = _generate_sample_set(tmp_path)
        zero_count = sum(1 for _, s in samples if s.total == 0)
        assert zero_count < N_SAMPLES * 0.5, \
            f"0점 비율이 너무 높음: {zero_count}/{N_SAMPLES} ({100*zero_count/N_SAMPLES:.1f}%)"

    def test_dist03_score_distribution_not_all_100(self, tmp_path):
        """DIST-03b: 1,000개 중 100점이 50% 이상이면 채점 편향 의심."""
        samples = _generate_sample_set(tmp_path)
        perfect_count = sum(1 for _, s in samples if s.total == 100)
        assert perfect_count < N_SAMPLES * 0.5, \
            f"100점 비율이 너무 높음: {perfect_count}/{N_SAMPLES}"

    def test_dist03_mean_score_in_reasonable_range(self, tmp_path):
        """DIST-03c: 평균 점수가 20~80점 범위에 있어야 함 (중앙 분포)."""
        samples = _generate_sample_set(tmp_path)
        scores  = [s.total for _, s in samples]
        mean    = statistics.mean(scores)
        assert 20 <= mean <= 80, \
            f"평균 점수 {mean:.1f}점 — 채점 분포가 한쪽으로 치우침"

    def test_dist03_stddev_indicates_discrimination(self, tmp_path):
        """DIST-03d: 표준편차 ≥ 10 — 점수가 프로젝트를 실제로 변별한다."""
        samples = _generate_sample_set(tmp_path)
        scores  = [s.total for _, s in samples]
        stddev  = statistics.stdev(scores)
        assert stddev >= 10, \
            f"표준편차 {stddev:.1f}점 — 점수 변별력이 너무 낮음"

    def test_dist03_all_grades_achievable(self, tmp_path):
        """DIST-03e: 각 등급 경계 직상에서 대상 등급이 반환되어야 함.

        [설계 특성 문서]
        완전 무작위 입력에서는 bare_lint_suppression_ratio가 [0,1] 균등분포이므로
        평균 점수가 35점대에 머문다. 이것은 채점기가 '좋은 프로젝트에만 높은 점수'를
        주도록 설계됐기 때문이며 버그가 아니다.

        이 테스트는 점수 체계 자체가 S/A/B/C/D 등급 판정 능력을 갖추고 있음을 확인한다.
        """
        # 각 등급 경계를 직접 달성하는 ScanResult를 조합으로 생성
        grade_scenarios = {
            "S": (True,  True,  True,  True,   0,   5, 10.0, [],   True, 0.0),
            "A": (True,  True,  True,  False,  0,   5, 10.0, [],   True, 0.0),
            "B": (True,  True,  False, False,  0,  35, 10.0, [],   False, 0.2),
            "C": (True,  True,  False, False,  2,  35, 65.0, ["x"], False, 0.4),
            "D": (False, False, False, False, 10, 100, 150.0, ["x","y","z"], False, 0.9),
        }
        for expected_grade, (
            has_agents, has_ci, has_pre, has_session,
            dep_viol, staleness, docs_staleness, inv_refs, has_gc, suppress_ratio
        ) in grade_scenarios.items():
            scan = ScanResult(target_path=tmp_path)
            scan.has_agents_md              = has_agents
            scan.agents_md_lines            = 100
            scan.has_docs_dir               = True
            scan.has_architecture_md        = True
            scan.has_conventions_md         = True
            scan.has_adr_dir                = True
            scan.docs_files                 = [tmp_path / "docs" / "a.md"]
            scan.has_session_bridge         = has_session
            scan.has_feature_list           = has_session
            scan.has_linter_config          = True
            scan.has_pre_commit             = has_pre
            scan.has_ci_gate                = has_ci
            scan.has_forbidden_patterns     = True
            scan.dependency_violations      = dep_viol
            scan.agents_md_staleness_days   = staleness
            scan.docs_avg_staleness_days    = docs_staleness
            scan.invalid_agents_refs        = inv_refs
            scan.has_gc_agent               = has_gc
            scan.bare_lint_suppression_ratio = suppress_ratio
            result = ENGINE.score(scan)
            assert result.grade == expected_grade, \
                f"등급 {expected_grade} 달성 실패: 실제={result.grade}({result.total}점)"


# ── DIST-04: 기둥 독립성 ─────────────────────────────────────────────────────

class TestDistributionIndependence:

    def test_dist04_ce_score_independent_of_ac_inputs(self, tmp_path):
        """DIST-04: AC 전용 입력 변경 → CE 점수 불변."""
        from copy import deepcopy
        rng = random.Random(RANDOM_SEED + 3)

        for _ in range(50):
            base    = _random_scan(tmp_path, rng)
            mutated = deepcopy(base)
            mutated.has_linter_config      = not mutated.has_linter_config
            mutated.has_pre_commit         = not mutated.has_pre_commit
            mutated.dependency_violations  = rng.randint(0, 20)

            from hachilles.auditors.context_auditor import ContextAuditor
            ctx = ContextAuditor()
            assert ctx.audit(base).score == ctx.audit(mutated).score, \
                "AC 전용 입력이 CE 점수에 영향을 줌 — 기둥 독립성 위반"

    def test_dist04_em_score_independent_of_pure_ce_inputs(self, tmp_path):
        """DIST-04b: EM과 CE의 '설계된 공유 필드' 이해 검증.

        [설계 특성 문서]
        has_agents_md는 CE-01에도 쓰이고, EM-01(AGENTS.md 최신성)과
        EM-03(참조 유효성)에도 전제조건으로 사용된다. 이것은 의도된 결합이다.
        (AGENTS.md 없이는 최신성/참조를 측정할 수 없기 때문)

        이 테스트는 '순수 CE 전용' 필드(has_session_bridge, has_feature_list)는
        EM 점수에 영향을 주지 않음을 확인한다.
        """
        from copy import deepcopy

        from hachilles.auditors.entropy_auditor import EntropyAuditor
        ent = EntropyAuditor()
        rng = random.Random(RANDOM_SEED + 4)

        for _ in range(50):
            base    = _random_scan(tmp_path, rng)
            mutated = deepcopy(base)
            # 순수 CE 전용 필드만 변경 (EM과 공유 없음)
            mutated.has_session_bridge = not mutated.has_session_bridge
            mutated.has_feature_list   = not mutated.has_feature_list
            mutated.has_architecture_md = not mutated.has_architecture_md
            mutated.has_conventions_md  = not mutated.has_conventions_md

            assert ent.audit(base).score == ent.audit(mutated).score, \
                "순수 CE 전용 입력(session_bridge, feature_list, arch, conv)이 EM 점수에 영향을 줌"

    def test_dist04_em_em01_depends_on_has_agents_md_by_design(self, tmp_path):
        """DIST-04c: EM-01은 has_agents_md에 의존 — 의도된 설계임을 검증.

        AGENTS.md 없이는 최신성을 측정할 수 없으므로, has_agents_md=False이면
        EM-01이 0점 처리된다. 이 동작이 일관되게 유지되는지 확인한다.
        """
        from hachilles.auditors.entropy_auditor import EntropyAuditor
        ent = EntropyAuditor()

        scan_without = ScanResult(target_path=tmp_path)
        scan_without.has_agents_md            = False
        scan_without.agents_md_staleness_days = 5  # 최신이지만 파일이 없음

        scan_with = ScanResult(target_path=tmp_path)
        scan_with.has_agents_md            = True
        scan_with.agents_md_staleness_days = 5

        result_without = ent.audit(scan_without)
        result_with    = ent.audit(scan_with)

        em01_without = next(i for i in result_without.items if i.code == "EM-01")
        em01_with    = next(i for i in result_with.items if i.code == "EM-01")

        assert not em01_without.passed, \
            "AGENTS.md 없어도 EM-01이 통과됨 — 전제조건 로직 확인 필요"
        assert em01_with.passed, \
            "AGENTS.md 있고 최신인데 EM-01이 실패함"


# ── DIST-05: 등급 일관성 ─────────────────────────────────────────────────────

class TestDistributionGradeConsistency:

    _GRADE_BOUNDS = [
        (90, "S"),
        (75, "A"),
        (60, "B"),
        (40, "C"),
        (0,  "D"),
    ]

    def _expected_grade(self, total: int) -> str:
        for threshold, grade in self._GRADE_BOUNDS:
            if total >= threshold:
                return grade
        return "D"

    def test_dist05_grade_matches_total(self, tmp_path):
        """DIST-05: grade 문자열이 total 점수에 대한 등급 공식과 항상 일치."""
        samples = _generate_sample_set(tmp_path)
        violations = [
            (i, s.total, s.grade, self._expected_grade(s.total))
            for i, (_, s) in enumerate(samples)
            if s.grade != self._expected_grade(s.total)
        ]
        assert not violations, \
            f"등급 불일치 {len(violations)}건: {violations[:3]}"


# ── DIST-06: 직렬화 안전성 ───────────────────────────────────────────────────

class TestDistributionSerialization:

    def test_dist06_to_dict_always_json_serializable(self, tmp_path):
        """DIST-06: 1,000개 to_dict() 결과 전부 json.dumps 가능해야 함."""
        samples    = _generate_sample_set(tmp_path)
        violations = []
        for i, (_, s) in enumerate(samples):
            try:
                json.dumps(s.to_dict())
            except (TypeError, ValueError) as exc:
                violations.append((i, str(exc)))
        assert not violations, \
            f"직렬화 실패 {len(violations)}건: {violations[:3]}"

    def test_dist06_to_dict_keys_complete(self, tmp_path):
        """DIST-06b: to_dict() 결과에 필수 키가 항상 존재."""
        required_keys = {
            "total", "grade", "grade_label", "passed_rate",
            "context_score", "constraint_score", "entropy_score",
            "context_result", "constraint_result", "entropy_result",
            "pattern_risks",
        }
        rng = random.Random(RANDOM_SEED)
        for _ in range(100):
            scan = _random_scan(tmp_path, rng)
            d    = ENGINE.score(scan).to_dict()
            missing = required_keys - set(d.keys())
            assert not missing, f"to_dict()에 필수 키 누락: {missing}"


# ── DIST-07: 결정론적 안정성 ─────────────────────────────────────────────────

class TestDistributionDeterminism:

    def test_dist07_same_input_same_output(self, tmp_path):
        """DIST-07: 동일 ScanResult → 5회 반복 실행 후 항상 동일 HarnessScore."""
        rng = random.Random(RANDOM_SEED)
        for _ in range(50):
            scan    = _random_scan(tmp_path, rng)
            results = [ENGINE.score(scan) for _ in range(5)]
            totals  = [r.total for r in results]
            grades  = [r.grade for r in results]
            assert len(set(totals)) == 1, \
                f"비결정론적 총점: {totals}"
            assert len(set(grades)) == 1, \
                f"비결정론적 등급: {grades}"

    def test_dist07_different_engines_same_result(self, tmp_path):
        """DIST-07b: 두 독립 ScoreEngine 인스턴스 → 동일 결과."""
        engine2 = ScoreEngine()
        rng     = random.Random(RANDOM_SEED)
        for _ in range(30):
            scan = _random_scan(tmp_path, rng)
            r1   = ENGINE.score(scan)
            r2   = engine2.score(scan)
            assert r1.total == r2.total, \
                f"두 엔진의 결과 불일치: {r1.total} vs {r2.total}"


# ── DIST-08: 패턴 위험도 커버리지 ────────────────────────────────────────────

class TestDistributionPatternCoverage:

    _EXPECTED_PATTERNS = {
        "Context Drift",
        "AI Slop",
        "Entropy Explosion",
        "70-80% Wall",
        "Over-engineering",
    }

    def test_dist08_always_5_patterns(self, tmp_path):
        """DIST-08: 1,000개 입력 전부 정확히 5개 패턴 위험도 반환."""
        samples    = _generate_sample_set(tmp_path)
        violations = [
            (i, len(s.pattern_risks))
            for i, (_, s) in enumerate(samples)
            if len(s.pattern_risks) != 5
        ]
        assert not violations, \
            f"패턴 개수 불일치 {len(violations)}건: {violations[:3]}"

    def test_dist08_all_pattern_names_present(self, tmp_path):
        """DIST-08b: 5개 패턴 이름이 항상 정확히 일치."""
        rng = random.Random(RANDOM_SEED)
        for _ in range(100):
            scan     = _random_scan(tmp_path, rng)
            patterns = {pr.pattern for pr in ENGINE.score(scan).pattern_risks}
            missing  = self._EXPECTED_PATTERNS - patterns
            assert not missing, f"누락된 패턴: {missing}"

    def test_dist08_risk_level_values_valid(self, tmp_path):
        """DIST-08c: 모든 RiskLevel 값이 열거형 범위 내."""
        valid_levels = {lv.value for lv in RiskLevel}
        rng = random.Random(RANDOM_SEED)
        for _ in range(100):
            scan = _random_scan(tmp_path, rng)
            for pr in ENGINE.score(scan).pattern_risks:
                assert pr.risk.value in valid_levels, \
                    f"잘못된 RiskLevel 값: {pr.risk.value}"
