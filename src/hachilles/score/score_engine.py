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

"""HAchilles ScoreEngine — 기둥별 AuditResult를 종합하여 HAchilles Score를 산출.

레이어 규칙: score는 models와 auditors만 import한다. prescriptions/report/cli는 import 금지.

점수 체계:
  Context     (CE-01~05): 40점 만점
  Constraint  (AC-01~05): 35점 만점
  Entropy     (EM-01~05): 25점 만점
  ─────────────────────────────────
  합계                  : 100점 만점

등급 기준:
  90-100: S — 하네스 엔지니어링 모범 사례
  75-89 : A — 견고한 하네스 구조
  60-74 : B — 기본 하네스 갖춤, 일부 개선 필요
  40-59 : C — 위험 수준. 즉각적 조치 필요
  0-39  : D — 위기 수준. 전면 재설계 검토
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hachilles.auditors.constraint_auditor import ConstraintAuditor
from hachilles.auditors.context_auditor import ContextAuditor
from hachilles.auditors.entropy_auditor import EntropyAuditor
from hachilles.models.scan_result import (
    AuditItem,
    AuditResult,
    PatternRisk,
    Pillar,
    RiskLevel,
    ScanResult,
)

# ── 등급 경계값 ───────────────────────────────────────────────────────────────

_GRADE_BOUNDS = [
    (90, "S", "하네스 엔지니어링 모범 사례"),
    (75, "A", "견고한 하네스 구조"),
    (60, "B", "기본 하네스 갖춤, 일부 개선 필요"),
    (40, "C", "위험 수준 — 즉각 조치 필요"),
    (0,  "D", "위기 수준 — 전면 재설계 검토"),
]


@dataclass
class HarnessScore:
    """HAchilles 최종 점수 및 진단 요약.

    ScoreEngine.score()가 반환하는 불변 결과 객체다.
    모든 AuditResult와 패턴 위험도를 집계하며,
    CLI의 터미널/JSON 출력 모두 이 객체를 소비한다.
    """

    total: int                              # 0~100
    grade: str                              # S/A/B/C/D
    grade_label: str                        # 등급 설명

    context_result:    AuditResult
    constraint_result: AuditResult
    entropy_result:    AuditResult

    pattern_risks: list[PatternRisk] = field(default_factory=list)

    # ── 개별 기둥 점수 ────────────────────────────────────────────────────────

    @property
    def context_score(self) -> int:
        """Context Engineering 기둥 점수 (0~40)."""
        return self.context_result.score

    @property
    def constraint_score(self) -> int:
        """Architectural Constraint 기둥 점수 (0~35)."""
        return self.constraint_result.score

    @property
    def entropy_score(self) -> int:
        """Entropy Management 기둥 점수 (0~25)."""
        return self.entropy_result.score

    # ── 집계 뷰 ──────────────────────────────────────────────────────────────

    @property
    def all_audit_results(self) -> list[AuditResult]:
        """세 기둥 AuditResult 목록 (순서 고정: CE, AC, EM)."""
        return [self.context_result, self.constraint_result, self.entropy_result]

    @property
    def failed_items_by_pillar(self) -> dict[Pillar, list[AuditItem]]:
        """실패 항목을 기둥별로 분류한 dict.

        통과 항목이 없는 기둥은 키 자체가 없다.
        """
        return {
            r.pillar: r.failed_items
            for r in self.all_audit_results
            if r.failed_items
        }

    @property
    def passed_rate(self) -> float:
        """전체 15개 항목 중 통과 비율 (0.0 ~ 1.0).

        warn 케이스(passed=True, 반감점)도 통과로 계산된다.
        """
        all_items = [item for r in self.all_audit_results for item in r.items]
        if not all_items:
            return 0.0
        return sum(1 for item in all_items if item.passed) / len(all_items)

    @property
    def critical_items(self) -> list[AuditItem]:
        """실패한 항목을 배점 높은 순으로 정렬한 목록.

        처방 엔진 및 터미널 출력에서 '우선 개선 항목' 표시에 활용한다.
        """
        failed = [
            item
            for r in self.all_audit_results
            for item in r.items
            if not item.passed
        ]
        return sorted(failed, key=lambda x: x.full_score, reverse=True)

    # ── 직렬화 ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """JSON 직렬화를 위한 dict 변환.

        CLI의 --json 출력 및 테스트 스냅샷에 사용된다.
        Path/Enum 등 비직렬화 타입은 str/value로 변환한다.
        """

        def _item(item: AuditItem) -> dict:
            return {
                "code":       item.code,
                "pillar":     item.pillar.value,
                "name":       item.name,
                "passed":     item.passed,
                "score":      item.score,
                "full_score": item.full_score,
                "detail":     item.detail,
            }

        def _result(result: AuditResult) -> dict:
            return {
                "pillar":       result.pillar.value,
                "score":        result.score,
                "full_score":   result.full_score,
                "passed_count": result.passed_count,
                "items":        [_item(i) for i in result.items],
            }

        def _risk(pr: PatternRisk) -> dict:
            return {
                "pattern":  pr.pattern,
                "risk":     pr.risk.value,
                "evidence": pr.evidence,
                "summary":  pr.summary,
            }

        return {
            "total":             self.total,
            "grade":             self.grade,
            "grade_label":       self.grade_label,
            "passed_rate":       round(self.passed_rate, 3),
            "context_score":     self.context_score,
            "constraint_score":  self.constraint_score,
            "entropy_score":     self.entropy_score,
            "context_result":    _result(self.context_result),
            "constraint_result": _result(self.constraint_result),
            "entropy_result":    _result(self.entropy_result),
            "pattern_risks":     [_risk(pr) for pr in self.pattern_risks],
        }


class ScoreEngine:
    """세 Auditor를 실행하고 HAchilles Score를 계산한다.

    초기화 시 Auditor 계약을 자동 검증한다:
      - 세 Auditor의 full_score 합 == 100
      - 각 Auditor의 pillar가 고유

    사용 예:
        engine = ScoreEngine()
        harness_score = engine.score(scan_result)
    """

    _EXPECTED_TOTAL_FULL_SCORE = 100

    def __init__(self) -> None:
        self._auditors = [
            ContextAuditor(),
            ConstraintAuditor(),
            EntropyAuditor(),
        ]
        self._validate_auditor_contract()

    def _validate_auditor_contract(self) -> None:
        """Auditor 등록 계약을 검증한다.

        위반 시 프로그래밍 오류이므로 AssertionError를 발생시킨다.
        """
        total_full = sum(a.full_score for a in self._auditors)
        assert total_full == self._EXPECTED_TOTAL_FULL_SCORE, (
            f"Auditor full_score 합 = {total_full} "
            f"(반드시 {self._EXPECTED_TOTAL_FULL_SCORE}이어야 함)\n"
            + "\n".join(
                f"  {a.__class__.__name__}: {a.full_score}"
                for a in self._auditors
            )
        )

        pillars = [a.pillar for a in self._auditors]
        assert len(pillars) == len(set(pillars)), (
            f"Auditor pillar 중복: {pillars}"
        )

    def score(self, scan: ScanResult) -> HarnessScore:
        """ScanResult를 받아 HarnessScore를 반환한다.

        동일 ScanResult → 항상 동일 HarnessScore (결정론적).
        """
        context_result    = self._auditors[0].audit(scan)
        constraint_result = self._auditors[1].audit(scan)
        entropy_result    = self._auditors[2].audit(scan)

        total = (
            context_result.score
            + constraint_result.score
            + entropy_result.score
        )
        # 안전 클램핑 (배점 버그 방지)
        total = max(0, min(100, total))

        grade, grade_label = self._determine_grade(total)
        pattern_risks = self._assess_pattern_risks(
            scan, context_result, constraint_result, entropy_result
        )

        return HarnessScore(
            total=total,
            grade=grade,
            grade_label=grade_label,
            context_result=context_result,
            constraint_result=constraint_result,
            entropy_result=entropy_result,
            pattern_risks=pattern_risks,
        )

    # ── Private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _determine_grade(total: int) -> tuple[str, str]:
        """총점을 S/A/B/C/D 등급으로 변환한다.

        _GRADE_BOUNDS는 (최소점수, 등급, 설명) 튜플의 내림차순 리스트다.
        """
        for threshold, grade, label in _GRADE_BOUNDS:
            if total >= threshold:
                return grade, label
        # 방어: threshold=0이 있으므로 실제로는 도달 불가
        return "D", "위기 수준 — 전면 재설계 검토"  # pragma: no cover

    @staticmethod
    def _assess_pattern_risks(
        scan: ScanResult,
        ctx: AuditResult,
        con: AuditResult,
        ent: AuditResult,
    ) -> list[PatternRisk]:
        """5대 실패 패턴 위험도를 평가한다.

        각 패턴의 위험 근거는 AuditItem 결과에서 추출한다.
        모든 패턴에 대해 항상 5개의 PatternRisk를 반환한다.
        """
        risks: list[PatternRisk] = []

        # ── 1. Context Drift ─────────────────────────────────────────────────
        # CE와 EM의 점수 비율이 낮을수록 컨텍스트 드리프트 위험이 높다.
        ctx_ratio = ctx.score / ctx.full_score if ctx.full_score else 1.0
        ent_ratio = ent.score / ent.full_score if ent.full_score else 1.0
        cd_evidence = (
            [item.detail for item in ctx.failed_items]
            + [
                item.detail for item in ent.failed_items
                if item.code in {"EM-01", "EM-02", "EM-03"}
            ]
        )
        if ctx_ratio < 0.4 or ent_ratio < 0.4:
            cd_risk = RiskLevel.CRITICAL
        elif ctx_ratio < 0.6 or ent_ratio < 0.6:
            cd_risk = RiskLevel.HIGH
        elif ctx_ratio < 0.8:
            cd_risk = RiskLevel.MEDIUM
        else:
            cd_risk = RiskLevel.OK
        risks.append(PatternRisk(
            pattern="Context Drift",
            risk=cd_risk,
            evidence=cd_evidence,
            summary=_risk_summary("Context Drift", cd_risk),
        ))

        # ── 2. AI Slop ───────────────────────────────────────────────────────
        # AC 게이트(린터·pre-commit·CI) 누락 + 이유 없는 lint suppress가 많을수록 위험.
        slop_evidence = (
            [item.detail for item in con.failed_items
             if item.code in {"AC-01", "AC-02", "AC-03"}]
            + [item.detail for item in ent.failed_items
               if item.code == "EM-05"]
        )
        slop_fail_count = sum(
            1 for item in con.failed_items + ent.failed_items
            if item.code in {"AC-01", "AC-02", "AC-03", "EM-05"}
        )
        if slop_fail_count >= 3:
            slop_risk = RiskLevel.HIGH
        elif slop_fail_count >= 2:
            slop_risk = RiskLevel.MEDIUM
        elif slop_fail_count >= 1:
            slop_risk = RiskLevel.LOW
        else:
            slop_risk = RiskLevel.OK
        risks.append(PatternRisk(
            pattern="AI Slop",
            risk=slop_risk,
            evidence=slop_evidence,
            summary=_risk_summary("AI Slop", slop_risk),
        ))

        # ── 3. Entropy Explosion ─────────────────────────────────────────────
        # EM 실패 항목 수로 엔트로피 폭발 위험을 측정한다.
        ee_fail_count = len(ent.failed_items)
        ee_evidence = [item.detail for item in ent.failed_items]
        if ee_fail_count >= 4:
            ee_risk = RiskLevel.CRITICAL
        elif ee_fail_count >= 3:
            ee_risk = RiskLevel.HIGH
        elif ee_fail_count >= 2:
            ee_risk = RiskLevel.MEDIUM
        elif ee_fail_count >= 1:
            ee_risk = RiskLevel.LOW
        else:
            ee_risk = RiskLevel.OK
        risks.append(PatternRisk(
            pattern="Entropy Explosion",
            risk=ee_risk,
            evidence=ee_evidence,
            summary=_risk_summary("Entropy Explosion", ee_risk),
        ))

        # ── 4. 70-80% Wall ───────────────────────────────────────────────────
        # 세션 브릿지·피처 목록 없이 70~85점 구간에 정체할 때 발생.
        # '거의 다 됐다'는 착각으로 마지막 20%를 완성하지 못하는 패턴이다.
        total = ctx.score + con.score + ent.score
        if 70 <= total <= 85 and (
            not scan.has_session_bridge or not scan.has_feature_list
        ):
            wall_risk = RiskLevel.MEDIUM
            wall_evidence = [f"총점 {total}점 — 70-85 구간 정체 중"]
            if not scan.has_session_bridge:
                wall_evidence.append("세션 브릿지 없음 — 세션 간 컨텍스트 단절")
            if not scan.has_feature_list:
                wall_evidence.append("feature_list 없음 — 완료 기준 불명확")
        else:
            wall_risk = RiskLevel.OK
            wall_evidence = []
        risks.append(PatternRisk(
            pattern="70-80% Wall",
            risk=wall_risk,
            evidence=wall_evidence,
            summary=_risk_summary("70-80% Wall", wall_risk),
        ))

        # ── 5. Over-engineering ──────────────────────────────────────────────
        # Phase 3: llm_over_engineering_score (0.0~1.0) 기반 위험도 산출.
        # LLM 분석이 실행되지 않은 경우(score==0.0, evidence==[])는 측정 보류로 표시.
        oe_score = scan.llm_over_engineering_score
        oe_evidence = list(scan.llm_over_engineering_evidence)
        if not oe_evidence and oe_score == 0.0:
            # LLM 분석 미실행 — 측정 보류
            oe_risk = RiskLevel.OK
            oe_evidence = ["LLM 분석 미실행 (hachilles scan --llm 으로 활성화)"]
        elif oe_score >= 0.8:
            oe_risk = RiskLevel.CRITICAL
        elif oe_score >= 0.6:
            oe_risk = RiskLevel.HIGH
        elif oe_score >= 0.4:
            oe_risk = RiskLevel.MEDIUM
        elif oe_score >= 0.2:
            oe_risk = RiskLevel.LOW
        else:
            oe_risk = RiskLevel.OK
        risks.append(PatternRisk(
            pattern="Over-engineering",
            risk=oe_risk,
            evidence=oe_evidence,
            summary=_risk_summary("Over-engineering", oe_risk),
        ))

        return risks


# ── 요약 문구 사전 ────────────────────────────────────────────────────────────

def _risk_summary(pattern: str, risk: RiskLevel) -> str:
    """패턴·위험도 조합으로 요약 문구를 반환한다."""
    summaries: dict[tuple[str, RiskLevel], str] = {
        ("Context Drift", RiskLevel.OK):       "컨텍스트 드리프트 위험 없음",
        ("Context Drift", RiskLevel.LOW):      "컨텍스트 드리프트 초기 징후 — 모니터링 권장",
        ("Context Drift", RiskLevel.MEDIUM):   "컨텍스트 드리프트 진행 중 — 문서 갱신 필요",
        ("Context Drift", RiskLevel.HIGH):     "컨텍스트 드리프트 심각 — AI가 잘못된 지도로 작업 중",
        ("Context Drift", RiskLevel.CRITICAL): "컨텍스트 드리프트 위기 — 즉각적 문서 재건 필요",
        ("AI Slop", RiskLevel.OK):             "AI 슬롭 위험 없음",
        ("AI Slop", RiskLevel.LOW):            "AI 슬롭 초기 징후 — 린터 설정 점검 권장",
        ("AI Slop", RiskLevel.MEDIUM):         "AI 슬롭 누적 중 — pre-commit + CI Gate 강화 필요",
        ("AI Slop", RiskLevel.HIGH):           "AI 슬롭 심각 — 코드 품질 대규모 저하 중",
        ("AI Slop", RiskLevel.CRITICAL):       "AI 슬롭 위기 — 전면 코드 감사 필요",
        ("Entropy Explosion", RiskLevel.OK):   "엔트로피 폭발 위험 없음",
        ("Entropy Explosion", RiskLevel.LOW):  "엔트로피 증가 초기 — GC 에이전트 도입 권장",
        ("Entropy Explosion", RiskLevel.MEDIUM): "엔트로피 누적 중 — 주기적 정리 작업 필요",
        ("Entropy Explosion", RiskLevel.HIGH): "엔트로피 폭발 임박 — 긴급 정리 작업 필요",
        ("Entropy Explosion", RiskLevel.CRITICAL): "엔트로피 폭발 — 시스템 전면 재정비 필요",
        ("70-80% Wall", RiskLevel.OK):         "70-80% 벽 위험 없음",
        ("70-80% Wall", RiskLevel.MEDIUM):     "70-80% 벽 징후 — 세션 브릿지·완료 기준 보강으로 돌파 가능",
        ("Over-engineering", RiskLevel.OK):      "Over-engineering 위험 없음 (또는 LLM 분석 미실행)",
        ("Over-engineering", RiskLevel.LOW):     "경미한 Over-engineering — 일부 불필요한 추상화 감지",
        ("Over-engineering", RiskLevel.MEDIUM):  "Over-engineering 진행 중 — 미사용 인터페이스·복잡한 팩토리 패턴",
        ("Over-engineering", RiskLevel.HIGH):    "Over-engineering 심각 — 구조를 위한 구조가 다수 감지됨",
        ("Over-engineering", RiskLevel.CRITICAL): "Over-engineering 위기 — 대부분의 코드가 실제 기능보다 구조 중심",
    }
    return summaries.get((pattern, risk), f"{pattern}: {risk.value}")
