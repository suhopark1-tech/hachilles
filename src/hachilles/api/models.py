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

"""Pydantic models for HAchilles REST API (Phase 3)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """Request body for POST /api/v1/scan."""

    path: str = Field(..., description="진단할 프로젝트 경로")
    llm: bool = Field(False, description="LLM 기반 Over-engineering 분석 활성화")
    save_history: bool = Field(False, description="진단 결과를 SQLite 이력 DB에 저장")


class AuditItemResponse(BaseModel):
    """단일 진단 항목 응답."""

    code: str
    name: str
    passed: bool
    score: int
    full_score: int
    detail: str


class PillarResponse(BaseModel):
    """기둥(Context/Constraint/Entropy) 응답."""

    pillar: str
    score: int
    full_score: int
    passed_count: int
    items: list[AuditItemResponse]


class PatternRiskResponse(BaseModel):
    """패턴 위험도 응답."""

    pattern: str
    risk: str
    summary: str
    evidence: list[str]


class ScanResponse(BaseModel):
    """Complete scan result response."""

    hachilles_version: str
    total: int
    grade: str
    grade_label: str
    passed_rate: float
    context: PillarResponse
    constraint: PillarResponse
    entropy: PillarResponse
    pattern_risks: list[PatternRiskResponse]
    tech_stack: list[str]
    scan_timestamp: str
    scan_errors: list[str]
    # Phase 2
    dependency_cycles: list[Any]
    layer_violations: list[Any]
    llm_over_engineering_score: float
    go_module_name: str
    java_build_tool: str
    # Phase 3 TypeScript 심층 분석 (6개 필드 완전 노출)
    ts_has_eslint: bool
    ts_eslint_extends: list[str]        # ESLint extends 목록
    ts_has_strict: bool
    ts_has_path_aliases: bool           # tsconfig.json paths 별칭 여부
    ts_test_files: int
    ts_has_vitest_or_jest: bool         # vitest / jest 설정 존재 여부


class HistoryRecord(BaseModel):
    """단일 이력 레코드."""

    id: int
    timestamp: str
    total_score: int
    grade: str
    passed_items: int
    total_items: int
    tech_stack: list[str]


class HistoryResponse(BaseModel):
    """프로젝트 진단 이력 응답."""

    project_path: str
    records: list[HistoryRecord]
    trend: list[int]


class CompareItem(BaseModel):
    """팀 비교 항목."""

    project_path: str
    project_name: str
    total: int
    grade: str
    context_score: int
    constraint_score: int
    entropy_score: int
    tech_stack: list[str]
    last_scan: str


class CompareResponse(BaseModel):
    """여러 프로젝트 비교 응답."""

    projects: list[CompareItem]
    best_project: str
    worst_project: str


class GenerateAgentsRequest(BaseModel):
    """AGENTS.md 생성 요청."""

    path: str = Field(..., description="프로젝트 경로")
    project_name: str = Field("", description="프로젝트 이름 (비어 있으면 디렉토리명 사용)")
    include_sections: list[str] = Field(
        default_factory=lambda: [
            "overview",
            "architecture",
            "conventions",
            "forbidden",
            "session",
        ],
        description="포함할 섹션 목록",
    )


class GenerateAgentsResponse(BaseModel):
    """AGENTS.md 생성 응답."""

    content: str
    sections: list[str]
    estimated_lines: int
