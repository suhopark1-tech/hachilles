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

"""HAchilles EntropyAuditor — 엔트로피 관리 기둥 진단 (EM-01~05).

레이어 규칙: auditors는 models와 scanner만 import한다. score/cli는 import 금지.

진단 항목:
  EM-01: AGENTS.md 최신성 (docs staleness) (6점)
  EM-02: docs/ 평균 최신성 (4점)
  EM-03: AGENTS.md 참조 유효성 (5점)
  EM-04: GC 에이전트 존재 (5점)
  EM-05: 이유 없는 lint suppress 비율 (5점)

  총 25점
"""

from __future__ import annotations

from hachilles.auditors.base import BaseAuditor
from hachilles.models.scan_result import AuditItem, AuditResult, Pillar, ScanResult

# ── 배점 상수 ────────────────────────────────────────────────────────────────

_AGENTS_FRESH_FULL = 6
_DOCS_FRESH_FULL   = 4
_AGENTS_REFS_FULL  = 5
_GC_AGENT_FULL     = 5
_SUPPRESS_FULL     = 5

# 최신성 임계값 (일 단위)
_AGENTS_STALE_WARN = 14   # 14일 이상: 경고
_AGENTS_STALE_FAIL = 30   # 30일 이상: 실패
_DOCS_STALE_WARN   = 30   # 30일 이상: 경고
_DOCS_STALE_FAIL   = 60   # 60일 이상: 실패

# AGENTS.md 참조 허용 무효 개수
_INVALID_REFS_WARN = 1
_INVALID_REFS_FAIL = 3

# lint suppress 허용 비율
_SUPPRESS_RATIO_WARN = 0.1   # 10% 이상: 경고
_SUPPRESS_RATIO_FAIL = 0.3   # 30% 이상: 실패


class EntropyAuditor(BaseAuditor):
    """엔트로피 관리 기둥 진단 (EM-01~05).

    총 25점 만점.
    git 히스토리 없으면 EM-01, EM-02는 N/A (만점 처리 + 경고 메모).
    """

    @property
    def pillar(self) -> Pillar:
        return Pillar.ENTROPY

    @property
    def full_score(self) -> int:
        """Entropy 기둥 만점 = 25점."""
        return (
            _AGENTS_FRESH_FULL
            + _DOCS_FRESH_FULL
            + _AGENTS_REFS_FULL
            + _GC_AGENT_FULL
            + _SUPPRESS_FULL
        )

    @property
    def item_codes(self) -> list[str]:
        """EM-01~EM-05."""
        return ["EM-01", "EM-02", "EM-03", "EM-04", "EM-05"]

    def audit(self, scan: ScanResult) -> AuditResult:
        result = AuditResult(pillar=self.pillar)
        result.items.append(self._audit_em01(scan))
        result.items.append(self._audit_em02(scan))
        result.items.append(self._audit_em03(scan))
        result.items.append(self._audit_em04(scan))
        result.items.append(self._audit_em05(scan))
        return result

    # ── EM-01: AGENTS.md 최신성 ─────────────────────────────────────────────

    def _audit_em01(self, scan: ScanResult) -> AuditItem:
        days = scan.agents_md_staleness_days

        if not scan.has_agents_md:
            return AuditItem(
                code="EM-01",
                pillar=self.pillar,
                name="AGENTS.md 최신성",
                passed=False,
                score=0,
                full_score=_AGENTS_FRESH_FULL,
                detail="AGENTS.md 없어 EM-01 측정 불가",
            )

        if days is None:
            # git 히스토리 없음 → N/A, 만점 + 경고
            return AuditItem(
                code="EM-01",
                pillar=self.pillar,
                name="AGENTS.md 최신성",
                passed=True,
                score=_AGENTS_FRESH_FULL,
                full_score=_AGENTS_FRESH_FULL,
                detail="git 히스토리 없음 — 최신성 측정 불가 (N/A 처리)",
            )

        if days < _AGENTS_STALE_WARN:
            return AuditItem(
                code="EM-01",
                pillar=self.pillar,
                name="AGENTS.md 최신성",
                passed=True,
                score=_AGENTS_FRESH_FULL,
                full_score=_AGENTS_FRESH_FULL,
                detail=f"AGENTS.md 마지막 수정 {days}일 전 — 최신 상태",
            )
        elif days < _AGENTS_STALE_FAIL:
            return AuditItem(
                code="EM-01",
                pillar=self.pillar,
                name="AGENTS.md 최신성",
                passed=True,
                score=_AGENTS_FRESH_FULL // 2,
                full_score=_AGENTS_FRESH_FULL,
                detail=f"AGENTS.md 마지막 수정 {days}일 전 — 코드베이스와 괴리 시작 가능성",
            )
        else:
            return AuditItem(
                code="EM-01",
                pillar=self.pillar,
                name="AGENTS.md 최신성",
                passed=False,
                score=0,
                full_score=_AGENTS_FRESH_FULL,
                detail=f"AGENTS.md 마지막 수정 {days}일 전 — Context Drift 위험. 즉시 갱신 필요",
            )

    # ── EM-02: docs/ 평균 최신성 ─────────────────────────────────────────────

    def _audit_em02(self, scan: ScanResult) -> AuditItem:
        avg = scan.docs_avg_staleness_days

        if not scan.has_docs_dir or not scan.docs_files:
            return AuditItem(
                code="EM-02",
                pillar=self.pillar,
                name="docs/ 평균 최신성",
                passed=False,
                score=0,
                full_score=_DOCS_FRESH_FULL,
                detail="docs/ 없거나 마크다운 파일 없음 — EM-02 측정 불가",
            )

        if avg is None:
            return AuditItem(
                code="EM-02",
                pillar=self.pillar,
                name="docs/ 평균 최신성",
                passed=True,
                score=_DOCS_FRESH_FULL,
                full_score=_DOCS_FRESH_FULL,
                detail="git 히스토리 없음 — 최신성 측정 불가 (N/A 처리)",
            )

        avg_days = int(avg)
        if avg_days < _DOCS_STALE_WARN:
            return AuditItem(
                code="EM-02",
                pillar=self.pillar,
                name="docs/ 평균 최신성",
                passed=True,
                score=_DOCS_FRESH_FULL,
                full_score=_DOCS_FRESH_FULL,
                detail=f"docs/ 평균 {avg_days}일 전 수정 — 양호",
            )
        elif avg_days < _DOCS_STALE_FAIL:
            return AuditItem(
                code="EM-02",
                pillar=self.pillar,
                name="docs/ 평균 최신성",
                passed=True,
                score=_DOCS_FRESH_FULL // 2,
                full_score=_DOCS_FRESH_FULL,
                detail=f"docs/ 평균 {avg_days}일 전 수정 — 일부 문서 갱신 권장",
            )
        else:
            return AuditItem(
                code="EM-02",
                pillar=self.pillar,
                name="docs/ 평균 최신성",
                passed=False,
                score=0,
                full_score=_DOCS_FRESH_FULL,
                detail=f"docs/ 평균 {avg_days}일 전 수정 — 문서 부패 수준. 대규모 갱신 필요",
            )

    # ── EM-03: AGENTS.md 참조 유효성 ────────────────────────────────────────

    def _audit_em03(self, scan: ScanResult) -> AuditItem:
        if not scan.has_agents_md:
            return AuditItem(
                code="EM-03",
                pillar=self.pillar,
                name="AGENTS.md 참조 유효성",
                passed=False,
                score=0,
                full_score=_AGENTS_REFS_FULL,
                detail="AGENTS.md 없어 EM-03 측정 불가",
            )

        invalid = scan.invalid_agents_refs
        count = len(invalid)

        if count == 0:
            return AuditItem(
                code="EM-03",
                pillar=self.pillar,
                name="AGENTS.md 참조 유효성",
                passed=True,
                score=_AGENTS_REFS_FULL,
                full_score=_AGENTS_REFS_FULL,
                detail="AGENTS.md 내 모든 코드 참조 유효",
            )
        elif count < _INVALID_REFS_FAIL:
            refs_str = ", ".join(f"`{r}`" for r in invalid[:5])
            return AuditItem(
                code="EM-03",
                pillar=self.pillar,
                name="AGENTS.md 참조 유효성",
                passed=False,
                score=_AGENTS_REFS_FULL // 2,
                full_score=_AGENTS_REFS_FULL,
                detail=f"무효 참조 {count}건: {refs_str}",
            )
        else:
            refs_str = ", ".join(f"`{r}`" for r in invalid[:5])
            if len(invalid) > 5:
                refs_str += f" 외 {len(invalid) - 5}건"
            return AuditItem(
                code="EM-03",
                pillar=self.pillar,
                name="AGENTS.md 참조 유효성",
                passed=False,
                score=0,
                full_score=_AGENTS_REFS_FULL,
                detail=f"무효 참조 {count}건: {refs_str} — AGENTS.md가 코드와 심각하게 괴리됨",
            )

    # ── EM-04: GC 에이전트 ───────────────────────────────────────────────────

    def _audit_em04(self, scan: ScanResult) -> AuditItem:
        if scan.has_gc_agent:
            return AuditItem(
                code="EM-04",
                pillar=self.pillar,
                name="GC 에이전트 존재",
                passed=True,
                score=_GC_AGENT_FULL,
                full_score=_GC_AGENT_FULL,
                detail="GC 에이전트 스크립트 또는 CI 스케줄 발견 — 문서 일관성 자동화 활성",
            )
        return AuditItem(
            code="EM-04",
            pillar=self.pillar,
            name="GC 에이전트 존재",
            passed=False,
            score=0,
            full_score=_GC_AGENT_FULL,
            detail=(
                "GC 에이전트 없음 — 문서·코드 일관성 수동 관리 의존 상태. "
                "gc_agent.py 또는 CI 스케줄 작업 추가 권장"
            ),
        )

    # ── EM-05: 이유 없는 lint suppress 비율 ─────────────────────────────────

    def _audit_em05(self, scan: ScanResult) -> AuditItem:
        ratio = scan.bare_lint_suppression_ratio
        pct = round(ratio * 100, 1)

        if ratio < _SUPPRESS_RATIO_WARN:
            return AuditItem(
                code="EM-05",
                pillar=self.pillar,
                name="이유 없는 lint suppress 비율",
                passed=True,
                score=_SUPPRESS_FULL,
                full_score=_SUPPRESS_FULL,
                detail=f"이유 없는 lint-suppress {pct}% — 양호",
            )
        elif ratio < _SUPPRESS_RATIO_FAIL:
            return AuditItem(
                code="EM-05",
                pillar=self.pillar,
                name="이유 없는 lint suppress 비율",
                passed=False,
                score=_SUPPRESS_FULL // 2,
                full_score=_SUPPRESS_FULL,
                detail=(
                    f"이유 없는 lint-suppress {pct}% — AI 슬롭 증가 징후. "
                    "# [EXCEPTION] 주석 없는 noqa/eslint-disable 검토 필요"
                ),
            )
        else:
            return AuditItem(
                code="EM-05",
                pillar=self.pillar,
                name="이유 없는 lint suppress 비율",
                passed=False,
                score=0,
                full_score=_SUPPRESS_FULL,
                detail=(
                    f"이유 없는 lint-suppress {pct}% — 심각한 AI 슬롭 패턴. "
                    "전수 조사 후 이유 명시 또는 코드 수정 필요"
                ),
            )
