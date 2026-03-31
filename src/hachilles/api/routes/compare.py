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

"""GET /api/v1/compare — 여러 프로젝트 점수 비교."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from hachilles.api.models import CompareItem, CompareResponse
from hachilles.tracker import HistoryDB

router = APIRouter(prefix="/compare", tags=["팀 비교"])


@router.get("", response_model=CompareResponse, summary="여러 프로젝트 점수 비교")
def compare_projects(
    paths: list[str] = Query(..., description="비교할 프로젝트 경로 목록 (반복 파라미터)"),
) -> CompareResponse:
    """여러 프로젝트의 최신 진단 결과를 비교한다.

    이력 DB에 저장된 데이터를 사용한다.
    """
    if len(paths) < 2:
        raise HTTPException(
            status_code=400,
            detail="비교에는 2개 이상의 프로젝트 경로가 필요합니다",
        )

    db = HistoryDB()
    items: list[CompareItem] = []

    for path in paths:
        target = Path(path).resolve()
        records = db.get_history(str(target), limit=1)
        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"이력이 없습니다: {path}. 먼저 hachilles scan --save-history 를 실행하세요.",
            )
        r = records[0]
        items.append(
            CompareItem(
                project_path=str(target),
                project_name=target.name,
                total=r.total_score,
                grade=r.grade,
                context_score=r.ce_score,
                constraint_score=r.ac_score,
                entropy_score=r.em_score,
                tech_stack=r.tech_stack,
                last_scan=r.timestamp[:10],
            )
        )

    best = max(items, key=lambda x: x.total)
    worst = min(items, key=lambda x: x.total)

    return CompareResponse(
        projects=sorted(items, key=lambda x: x.total, reverse=True),
        best_project=best.project_name,
        worst_project=worst.project_name,
    )
