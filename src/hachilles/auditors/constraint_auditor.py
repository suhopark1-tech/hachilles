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

"""HAchilles ConstraintAuditor — 아키텍처 제약 기둥 진단 (AC-01~05).

레이어 규칙: auditors는 models와 scanner만 import한다. score/cli는 import 금지.

진단 항목:
  AC-01: 린터 설정 파일 존재 (8점)
  AC-02: pre-commit 훅 설정 (7점)
  AC-03: CI Gate (lint/test job) (8점)
  AC-04: 금지 패턴 목록 (6점)
  AC-05: 의존성 방향 위반 건수 (6점)

  총 35점
"""

from __future__ import annotations

from hachilles.auditors.base import BaseAuditor
from hachilles.models.scan_result import AuditItem, AuditResult, Pillar, ScanResult

# ── 배점 상수 ────────────────────────────────────────────────────────────────

_LINTER_FULL    = 8
_PRECOMMIT_FULL = 7
_CI_GATE_FULL   = 8
_FORBIDDEN_FULL = 6
_DEP_FULL       = 6

# 의존성 위반 허용 임계값
_DEP_VIOLATIONS_WARN = 1   # 1건 이상이면 경고
_DEP_VIOLATIONS_FAIL = 5   # 5건 이상이면 실패


class ConstraintAuditor(BaseAuditor):
    """아키텍처 제약 기둥 진단 (AC-01~05).

    총 35점 만점.
    AC-05 (의존성 방향 위반)는 Sprint 3에서 AST 기반으로 고도화 예정.
    현재는 Scanner가 수집한 dependency_violations 값(기본 0)을 사용한다.
    """

    @property
    def pillar(self) -> Pillar:
        return Pillar.CONSTRAINT

    @property
    def full_score(self) -> int:
        """Constraint 기둥 만점 = 35점."""
        return (
            _LINTER_FULL
            + _PRECOMMIT_FULL
            + _CI_GATE_FULL
            + _FORBIDDEN_FULL
            + _DEP_FULL
        )

    @property
    def item_codes(self) -> list[str]:
        """AC-01~AC-05."""
        return ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05"]

    def audit(self, scan: ScanResult) -> AuditResult:
        result = AuditResult(pillar=self.pillar)
        result.items.append(self._audit_ac01(scan))
        result.items.append(self._audit_ac02(scan))
        result.items.append(self._audit_ac03(scan))
        result.items.append(self._audit_ac04(scan))
        result.items.append(self._audit_ac05(scan))
        return result

    # ── AC-01: 린터 설정 ─────────────────────────────────────────────────────

    def _audit_ac01(self, scan: ScanResult) -> AuditItem:
        if scan.has_linter_config:
            fname = scan.linter_config_path.name if scan.linter_config_path else "발견"
            return AuditItem(
                code="AC-01",
                pillar=self.pillar,
                name="린터 설정 파일",
                passed=True,
                score=_LINTER_FULL,
                full_score=_LINTER_FULL,
                detail=f"린터 설정 발견: {fname}",
            )
        return AuditItem(
            code="AC-01",
            pillar=self.pillar,
            name="린터 설정 파일",
            passed=False,
            score=0,
            full_score=_LINTER_FULL,
            detail=(
                "린터 설정 없음 (.eslintrc, .pylintrc, ruff.toml 등) — "
                "AI 생성 코드의 스타일 일관성 보장 불가"
            ),
        )

    # ── AC-02: pre-commit 훅 ─────────────────────────────────────────────────

    def _audit_ac02(self, scan: ScanResult) -> AuditItem:
        if scan.has_pre_commit:
            return AuditItem(
                code="AC-02",
                pillar=self.pillar,
                name="pre-commit 훅 설정",
                passed=True,
                score=_PRECOMMIT_FULL,
                full_score=_PRECOMMIT_FULL,
                detail=".pre-commit-config.yaml 존재 — 커밋 전 자동 검증 활성화",
            )
        return AuditItem(
            code="AC-02",
            pillar=self.pillar,
            name="pre-commit 훅 설정",
            passed=False,
            score=0,
            full_score=_PRECOMMIT_FULL,
            detail=(
                "pre-commit 설정 없음 — AI 슬롭이 린팅 없이 커밋될 수 있는 상태"
            ),
        )

    # ── AC-03: CI Gate ───────────────────────────────────────────────────────

    def _audit_ac03(self, scan: ScanResult) -> AuditItem:
        if scan.has_ci_gate:
            return AuditItem(
                code="AC-03",
                pillar=self.pillar,
                name="CI Gate (lint/test)",
                passed=True,
                score=_CI_GATE_FULL,
                full_score=_CI_GATE_FULL,
                detail=".github/workflows/ 에 lint/test job 확인",
            )
        return AuditItem(
            code="AC-03",
            pillar=self.pillar,
            name="CI Gate (lint/test)",
            passed=False,
            score=0,
            full_score=_CI_GATE_FULL,
            detail=(
                "CI Gate 없음 — PR 병합 전 자동 품질 검증이 없는 상태. "
                ".github/workflows/ 에 lint/test 잡 추가 권장"
            ),
        )

    # ── AC-04: 금지 패턴 목록 ────────────────────────────────────────────────

    def _audit_ac04(self, scan: ScanResult) -> AuditItem:
        if scan.has_forbidden_patterns:
            return AuditItem(
                code="AC-04",
                pillar=self.pillar,
                name="금지 패턴 목록",
                passed=True,
                score=_FORBIDDEN_FULL,
                full_score=_FORBIDDEN_FULL,
                detail="docs/forbidden.md 존재 — AI에게 금지 패턴 명시됨",
            )
        return AuditItem(
            code="AC-04",
            pillar=self.pillar,
            name="금지 패턴 목록",
            passed=False,
            score=0,
            full_score=_FORBIDDEN_FULL,
            detail=(
                "docs/forbidden.md 없음 — AI가 금지 패턴을 AGENTS.md에서 추론해야 함. "
                "명시적 목록으로 분리 권장"
            ),
        )

    # ── AC-05: 의존성 방향 위반 ──────────────────────────────────────────────

    def _audit_ac05(self, scan: ScanResult) -> AuditItem:
        """AST 기반 의존성 분석으로 레이어 위반 및 순환 의존성을 탐지한다 (Phase 2)."""
        violations_count = len(scan.layer_violations)
        cycles_count = len(scan.dependency_cycles)
        v = scan.dependency_violations  # 위반 건수 + 순환 * 2

        # 상세 메시지 구성
        detail_parts = []

        if violations_count > 0:
            detail_parts.append(f"레이어 위반: {violations_count}건")
            if scan.layer_violations:
                first_violation = scan.layer_violations[0]
                detail_parts.append(f"  예: {first_violation[0]} → {first_violation[1]}")

        if cycles_count > 0:
            detail_parts.append(f"순환 의존성: {cycles_count}개 사이클")
            if scan.dependency_cycles:
                first_cycle = scan.dependency_cycles[0]
                cycle_str = " → ".join(first_cycle[:3]) + ("..." if len(first_cycle) > 3 else "")
                detail_parts.append(f"  예: {cycle_str}")

        if not detail_parts:
            detail_parts.append("AST 분석 기반: 의존성 방향 위반 0건")

        detail = "\n".join(detail_parts)

        if v == 0:
            return AuditItem(
                code="AC-05",
                pillar=self.pillar,
                name="의존성 방향 위반",
                passed=True,
                score=_DEP_FULL,
                full_score=_DEP_FULL,
                detail=detail,
            )
        elif v < _DEP_VIOLATIONS_FAIL:
            return AuditItem(
                code="AC-05",
                pillar=self.pillar,
                name="의존성 방향 위반",
                passed=False,
                score=_DEP_FULL // 2,
                full_score=_DEP_FULL,
                detail=detail + " — 즉시 수정 권장",
            )
        else:
            return AuditItem(
                code="AC-05",
                pillar=self.pillar,
                name="의존성 방향 위반",
                passed=False,
                score=0,
                full_score=_DEP_FULL,
                detail=detail + " — 레이어 아키텍처 붕괴 수준. 즉시 리팩터링 필요",
            )
