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

"""POST /api/v1/scan — 프로젝트 진단 실행."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from hachilles import __version__
from hachilles.api.models import (
    AuditItemResponse,
    PatternRiskResponse,
    PillarResponse,
    ScanRequest,
    ScanResponse,
)
from hachilles.scanner import Scanner
from hachilles.score import ScoreEngine

router = APIRouter(prefix="/scan", tags=["진단"])


@router.post("", response_model=ScanResponse, summary="프로젝트 하네스 진단 실행")
def run_scan(req: ScanRequest) -> ScanResponse:
    """대상 프로젝트를 스캔하여 HAchilles Score를 반환한다.

    - **path**: 진단할 프로젝트 경로 (절대 또는 상대)
    - **llm**: LLM 기반 Over-engineering 분석 활성화 (HACHILLES_LLM_PROVIDER 환경변수 필요)
    - **save_history**: 결과를 SQLite 이력 DB에 저장
    """
    target = Path(req.path).resolve()
    if not target.exists():
        raise HTTPException(
            status_code=404, detail=f"경로를 찾을 수 없습니다: {target}"
        )
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"디렉토리가 아닙니다: {target}")

    try:
        scanner = Scanner(target)
        scan_result = scanner.scan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스캔 실패: {e}") from e

    # LLM 분석 (선택)
    if req.llm:
        try:
            from hachilles.llm import LLMEvaluator

            evaluator = LLMEvaluator()
            hits_before = evaluator.cache.stats()["hits"]
            llm_score, llm_evidence = evaluator.evaluate_over_engineering(target)
            scan_result.llm_over_engineering_score = llm_score
            scan_result.llm_over_engineering_evidence = llm_evidence
            scan_result.llm_analysis_cached = (
                evaluator.cache.stats()["hits"] > hits_before
            )
        except Exception as e:  # [EXCEPTION] LLM 분석 실패는 비치명적
            scan_result.scan_errors.append(f"LLM 분석 실패: {e}")

    engine = ScoreEngine()
    harness_score = engine.score(scan_result)

    # 이력 저장 (선택)
    if req.save_history:
        try:
            from hachilles.tracker import HistoryDB

            db = HistoryDB()
            total_items = sum(len(r.items) for r in harness_score.all_audit_results)
            passed_items = sum(r.passed_count for r in harness_score.all_audit_results)
            db.save(
                project_path=str(target),
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
        except Exception as e:  # [EXCEPTION] 이력 저장 실패는 비치명적
            scan_result.scan_errors.append(f"이력 저장 실패: {e}")

    def _pillar(result: object) -> PillarResponse:
        r = result  # type: ignore[assignment]  # [EXCEPTION] result는 object 주석으로 레이어 의존 방지 — 런타임엔 AuditResult
        return PillarResponse(
            pillar=r.pillar.value,
            score=r.score,
            full_score=r.full_score,
            passed_count=r.passed_count,
            items=[
                AuditItemResponse(
                    code=item.code,
                    name=item.name,
                    passed=item.passed,
                    score=item.score,
                    full_score=item.full_score,
                    detail=item.detail,
                )
                for item in r.items
            ],
        )

    return ScanResponse(
        hachilles_version=__version__,
        total=harness_score.total,
        grade=harness_score.grade,
        grade_label=harness_score.grade_label,
        passed_rate=round(harness_score.passed_rate, 3),
        context=_pillar(harness_score.context_result),
        constraint=_pillar(harness_score.constraint_result),
        entropy=_pillar(harness_score.entropy_result),
        pattern_risks=[
            PatternRiskResponse(
                pattern=pr.pattern,
                risk=pr.risk.value,
                summary=pr.summary,
                evidence=pr.evidence,
            )
            for pr in harness_score.pattern_risks
        ],
        tech_stack=scan_result.tech_stack,
        scan_timestamp=scan_result.scan_timestamp,
        scan_errors=scan_result.scan_errors,
        dependency_cycles=scan_result.dependency_cycles,
        layer_violations=list(scan_result.layer_violations),
        llm_over_engineering_score=scan_result.llm_over_engineering_score,
        go_module_name=scan_result.go_module_name,
        java_build_tool=scan_result.java_build_tool,
        ts_has_eslint=scan_result.ts_has_eslint,
        ts_eslint_extends=scan_result.ts_eslint_extends,
        ts_has_strict=scan_result.ts_has_strict,
        ts_has_path_aliases=scan_result.ts_has_path_aliases,
        ts_test_files=scan_result.ts_test_files,
        ts_has_vitest_or_jest=scan_result.ts_has_vitest_or_jest,
    )
