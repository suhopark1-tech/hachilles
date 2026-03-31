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

"""GET /api/v1/history — 진단 이력 조회."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

from hachilles.api.models import HistoryRecord, HistoryResponse

router = APIRouter(prefix="/history", tags=["이력"])


@router.get(
    "",
    response_model=HistoryResponse,
    summary="프로젝트 진단 이력 조회",
)
def get_history(
    path: str = Query(..., description="프로젝트 경로"),
    limit: int = Query(20, ge=1, le=100, description="최근 N회"),
) -> HistoryResponse:
    """프로젝트 경로의 진단 이력과 점수 추이를 반환한다."""
    from hachilles.tracker import HistoryDB

    target = Path(path).resolve()
    db = HistoryDB()
    records = db.get_history(str(target), limit=limit)
    trend_data = db.trend(str(target), limit=limit)

    # trend()는 (date, score) 튜플 리스트를 반환하므로 점수만 추출
    trend = [score for _, score in trend_data]

    return HistoryResponse(
        project_path=str(target),
        records=[
            HistoryRecord(
                id=r.id or 0,
                timestamp=r.timestamp,
                total_score=r.total_score,
                grade=r.grade,
                passed_items=r.passed_items,
                total_items=r.total_items,
                tech_stack=r.tech_stack,
            )
            for r in records
        ],
        trend=trend,
    )
