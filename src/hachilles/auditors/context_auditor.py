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

"""HAchilles ContextAuditor — 컨텍스트 엔지니어링 기둥 진단 (CE-01~05).

레이어 규칙: auditors는 models와 scanner만 import한다. score/cli는 import 금지.

진단 항목:
  CE-01: AGENTS.md 존재 여부 및 라인 수 (10점)
  CE-02: docs/ 구조 충실도 (10점)
  CE-03: 세션 브릿지 파일 존재 (8점)
  CE-04: feature_list.json 존재 (6점)
  CE-05: docs/에 architecture.md + conventions.md 존재 여부 (6점)

  총 40점
"""

from __future__ import annotations

from hachilles.auditors.base import BaseAuditor
from hachilles.models.scan_result import AuditItem, AuditResult, Pillar, ScanResult

# ── 배점 상수 ────────────────────────────────────────────────────────────────

_AGENTS_MD_FULL    = 10
_DOCS_STRUCT_FULL  = 10
_SESSION_FULL      = 8
_FEATURE_LIST_FULL = 6
_ARCH_CONV_FULL    = 6

# AGENTS.md 라인 수 권장 범위
_AGENTS_LINES_WARN = 600   # 이 이상이면 "분리 권장" 경고
_AGENTS_LINES_CRIT = 1200  # 이 이상이면 점수 차감


class ContextAuditor(BaseAuditor):
    """컨텍스트 엔지니어링 기둥 진단 (CE-01~05).

    총 40점 만점. 각 항목의 passed/score는 아래 기준으로 결정된다:
      - passed=True  → full_score 부여
      - passed=False → 0점

    예외: CE-01은 존재하더라도 라인 수가 과도하면 점수를 감점한다.
    """

    @property
    def pillar(self) -> Pillar:
        return Pillar.CONTEXT

    @property
    def full_score(self) -> int:
        """Context 기둥 만점 = 40점."""
        return (
            _AGENTS_MD_FULL
            + _DOCS_STRUCT_FULL
            + _SESSION_FULL
            + _FEATURE_LIST_FULL
            + _ARCH_CONV_FULL
        )

    @property
    def item_codes(self) -> list[str]:
        """CE-01~CE-05."""
        return ["CE-01", "CE-02", "CE-03", "CE-04", "CE-05"]

    def audit(self, scan: ScanResult) -> AuditResult:
        result = AuditResult(pillar=self.pillar)
        result.items.append(self._audit_ce01(scan))
        result.items.append(self._audit_ce02(scan))
        result.items.append(self._audit_ce03(scan))
        result.items.append(self._audit_ce04(scan))
        result.items.append(self._audit_ce05(scan))
        return result

    # ── CE-01: AGENTS.md 존재 및 라인 수 ────────────────────────────────────

    def _audit_ce01(self, scan: ScanResult) -> AuditItem:
        if not scan.has_agents_md:
            return AuditItem(
                code="CE-01",
                pillar=self.pillar,
                name="AGENTS.md 존재 여부",
                passed=False,
                score=0,
                full_score=_AGENTS_MD_FULL,
                detail="AGENTS.md 없음 — AI 에이전트에게 컨텍스트 지도가 없는 상태",
            )

        lines = scan.agents_md_lines

        if lines >= _AGENTS_LINES_CRIT:
            # 매우 긴 경우: 절반 점수
            score = _AGENTS_MD_FULL // 2
            detail = (
                f"AGENTS.md {lines:,}줄 — 심각한 분리 필요. "
                f"기능별로 여러 파일로 분리하고 메인 AGENTS.md에서 include 권장."
            )
            passed = False
        elif lines >= _AGENTS_LINES_WARN:
            # 경고 범위: 통과하지만 경고
            score = _AGENTS_MD_FULL
            detail = (
                f"AGENTS.md {lines:,}줄 — 분리 권장. "
                f"섹션별 파일 분리 후 메인 AGENTS.md에서 참조하는 구조 고려."
            )
            passed = True
        elif lines == 0:
            score = _AGENTS_MD_FULL // 2
            detail = "AGENTS.md 존재하나 내용이 비어 있음"
            passed = False
        else:
            score = _AGENTS_MD_FULL
            detail = f"AGENTS.md {lines:,}줄 — 적절한 분량"
            passed = True

        return AuditItem(
            code="CE-01",
            pillar=self.pillar,
            name="AGENTS.md 존재 여부",
            passed=passed,
            score=score,
            full_score=_AGENTS_MD_FULL,
            detail=detail,
        )

    # ── CE-02: docs/ 구조 충실도 ─────────────────────────────────────────────

    def _audit_ce02(self, scan: ScanResult) -> AuditItem:
        if not scan.has_docs_dir:
            return AuditItem(
                code="CE-02",
                pillar=self.pillar,
                name="docs/ 구조 충실도",
                passed=False,
                score=0,
                full_score=_DOCS_STRUCT_FULL,
                detail="docs/ 디렉토리 없음",
            )

        # 세부 항목: architecture.md, conventions.md, ADR 디렉토리
        checks = {
            "architecture.md": scan.has_architecture_md,
            "conventions.md":  scan.has_conventions_md,
            "ADR 디렉토리":     scan.has_adr_dir,
        }
        passed_checks = [k for k, v in checks.items() if v]
        missing_checks = [k for k, v in checks.items() if not v]

        # 3개 모두 있으면 만점, 2개면 7점, 1개면 4점, 0개면 2점 (docs/ 존재 크레딧)
        score_map = {3: _DOCS_STRUCT_FULL, 2: 7, 1: 4, 0: 2}
        count = len(passed_checks)
        score = score_map[count]
        passed = count == 3

        if passed:
            detail = "architecture.md + conventions.md + ADR 디렉토리 모두 존재"
        else:
            missing_str = ", ".join(missing_checks)
            detail = f"docs/ 있음 ({count}/3 충족) — 미비: {missing_str}"

        return AuditItem(
            code="CE-02",
            pillar=self.pillar,
            name="docs/ 구조 충실도",
            passed=passed,
            score=score,
            full_score=_DOCS_STRUCT_FULL,
            detail=detail,
        )

    # ── CE-03: 세션 브릿지 파일 ──────────────────────────────────────────────

    def _audit_ce03(self, scan: ScanResult) -> AuditItem:
        if scan.has_session_bridge:
            fname = scan.session_bridge_path.name if scan.session_bridge_path else "존재"
            return AuditItem(
                code="CE-03",
                pillar=self.pillar,
                name="세션 브릿지 파일",
                passed=True,
                score=_SESSION_FULL,
                full_score=_SESSION_FULL,
                detail=f"세션 브릿지 발견: {fname}",
            )
        return AuditItem(
            code="CE-03",
            pillar=self.pillar,
            name="세션 브릿지 파일",
            passed=False,
            score=0,
            full_score=_SESSION_FULL,
            detail="세션 브릿지 없음 (claude-progress.txt 또는 유사 파일) — 세션 간 컨텍스트 단절 위험",
        )

    # ── CE-04: feature_list.json ─────────────────────────────────────────────

    def _audit_ce04(self, scan: ScanResult) -> AuditItem:
        if scan.has_feature_list:
            return AuditItem(
                code="CE-04",
                pillar=self.pillar,
                name="완료 기준 구조화 (feature_list)",
                passed=True,
                score=_FEATURE_LIST_FULL,
                full_score=_FEATURE_LIST_FULL,
                detail="feature_list.json 또는 유사 파일 발견 — 완료 기준 명시됨",
            )
        return AuditItem(
            code="CE-04",
            pillar=self.pillar,
            name="완료 기준 구조화 (feature_list)",
            passed=False,
            score=0,
            full_score=_FEATURE_LIST_FULL,
            detail="feature_list.json 없음 — AI가 완료 기준을 추론해야 하는 상황",
        )

    # ── CE-05: architecture.md + conventions.md 파일 존재 ────────────────────

    def _audit_ce05(self, scan: ScanResult) -> AuditItem:
        """docs/에 architecture.md + conventions.md 두 파일이 모두 있으면 통과.

        AGENTS.md 존재 전제 조건: AGENTS.md 없으면 N/A(0점) 처리.
        """
        has_both = scan.has_architecture_md and scan.has_conventions_md

        if not scan.has_agents_md:
            return AuditItem(
                code="CE-05",
                pillar=self.pillar,
                name="아키텍처·컨벤션 문서 연결",
                passed=False,
                score=0,
                full_score=_ARCH_CONV_FULL,
                detail="AGENTS.md 없어 CE-05 측정 불가",
            )

        if has_both:
            return AuditItem(
                code="CE-05",
                pillar=self.pillar,
                name="아키텍처·컨벤션 문서 연결",
                passed=True,
                score=_ARCH_CONV_FULL,
                full_score=_ARCH_CONV_FULL,
                detail="architecture.md + conventions.md 모두 존재 — AGENTS.md 보조 문서 체계 충족",
            )

        missing = []
        if not scan.has_architecture_md:
            missing.append("architecture.md")
        if not scan.has_conventions_md:
            missing.append("conventions.md")
        return AuditItem(
            code="CE-05",
            pillar=self.pillar,
            name="아키텍처·컨벤션 문서 연결",
            passed=False,
            score=0,
            full_score=_ARCH_CONV_FULL,
            detail=f"미비 문서: {', '.join(missing)} — AI가 코딩 규칙을 추론해야 하는 상황",
        )
