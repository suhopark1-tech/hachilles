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

"""POST /api/v1/generate-agents — AGENTS.md 템플릿 자동 생성."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from hachilles.api.models import GenerateAgentsRequest, GenerateAgentsResponse
from hachilles.scanner import Scanner

router = APIRouter(prefix="/generate-agents", tags=["AGENTS.md 생성"])


@router.post(
    "",
    response_model=GenerateAgentsResponse,
    summary="AGENTS.md 템플릿 자동 생성",
)
def generate_agents_md(req: GenerateAgentsRequest) -> GenerateAgentsResponse:
    """프로젝트를 스캔하여 맥락에 맞는 AGENTS.md 템플릿을 생성한다.

    진단 결과(실패 항목, 기술 스택, 의존성 구조)를 반영하여
    프로젝트 특화 AGENTS.md 초안을 반환한다.
    """
    target = Path(req.path).resolve()
    if not target.exists():
        raise HTTPException(
            status_code=404, detail=f"경로를 찾을 수 없습니다: {target}"
        )

    # 스캔으로 컨텍스트 수집
    try:
        scan_result = Scanner(target).scan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스캔 실패: {e}") from e

    project_name = req.project_name or target.name
    sections = req.include_sections
    content = _build_agents_md(project_name, scan_result, sections)

    return GenerateAgentsResponse(
        content=content,
        sections=sections,
        estimated_lines=len(content.splitlines()),
    )


def _build_agents_md(project_name: str, scan: object, sections: list[str]) -> str:
    """진단 결과를 기반으로 AGENTS.md 템플릿 문자열을 생성한다."""
    s = scan  # type: ignore[assignment]  # [EXCEPTION] scan은 object 타입 주석으로 순환 import 방지 — 런타임엔 ScanResult
    stack_str = ", ".join(s.tech_stack) if s.tech_stack else "미감지"

    parts: list[str] = [
        f"# {project_name} — AI 에이전트 가이드",
        "",
        "> 이 파일은 HAchilles가 자동 생성한 AGENTS.md 템플릿입니다.",
        "> 프로젝트 실정에 맞게 내용을 보완하여 사용하세요.",
        "",
    ]

    if "overview" in sections:
        parts += [
            "## 프로젝트 개요",
            "",
            f"- **기술 스택**: {stack_str}",
        ]
        if s.go_module_name:
            parts.append(f"- **Go 모듈**: {s.go_module_name}")
        if s.java_build_tool:
            parts.append(f"- **Java 빌드**: {s.java_build_tool}")
        parts += [
            "- **목적**: [프로젝트 목적을 여기에 기술하세요]",
            "- **주요 기능**: [핵심 기능 목록]",
            "",
        ]

    if "architecture" in sections:
        violation_note = (
            f"⚠️ 현재 {len(s.layer_violations)}개의 레이어 위반이 감지되었습니다."
            " 수정이 필요합니다."
            if s.layer_violations
            else "✓ 레이어 의존성 위반 없음"
        )
        parts += [
            "## 아키텍처 제약",
            "",
            "### 레이어 구조",
            "",
            "```",
            "하위 레이어 ← 상위 레이어 (방향: 항상 위에서 아래로 import)",
            "models ← scanner ← auditors ← score ← cli",
            "```",
            "",
            f"**의존성 상태**: {violation_note}",
            "",
            "### 핵심 설계 원칙",
            "",
            "- 레이어 경계를 절대 역방향으로 import하지 마세요",
            "- 순환 의존성을 도입하지 마세요",
            "- 새 기능은 기존 레이어를 확장하거나 독립 레이어로 추가하세요",
            "",
        ]

    if "conventions" in sections:
        ts_strict = "TypeScript: strict 모드 필수" if s.ts_has_strict else ""
        eslint_note = ""
        if s.ts_has_eslint and s.ts_eslint_extends:
            eslint_note = f"ESLint 사용 중 (extends: {', '.join(s.ts_eslint_extends[:3])})"
        elif s.ts_has_eslint:
            eslint_note = "ESLint 설정 확인"

        parts += [
            "## 코딩 컨벤션",
            "",
            "### 코드 스타일",
            "",
            "- 린터를 통과하지 않는 코드를 커밋하지 마세요",
            "- `# noqa` / `// eslint-disable` 사용 시 반드시 `[EXCEPTION]` 주석을 달아"
            " 이유를 기술하세요",
        ]
        if ts_strict:
            parts.append(f"- {ts_strict}")
        else:
            parts.append("- 타입 안전성을 최우선으로 유지하세요")
        if eslint_note:
            parts.append(f"- {eslint_note}")
        else:
            parts.append("- 린터 설정 파일을 반드시 유지하세요")

        parts += [
            "",
            "### 테스트",
            "",
        ]
        if s.ts_test_files > 0:
            parts.append(f"- TypeScript 테스트 파일 {s.ts_test_files}개 유지 중")
        parts += [
            "- 새 기능에는 반드시 테스트를 추가하세요",
            "- 테스트 없는 PR은 병합하지 마세요",
            "",
        ]

    if "forbidden" in sections:
        parts += [
            "## 금지 패턴",
            "",
            "AI가 생성한 코드에서 다음 패턴은 절대 허용하지 않습니다:",
            "",
            "- [ ] 이유 없는 lint suppress (`# noqa`, `// eslint-disable`)",
            "- [ ] 레이어 간 역방향 import",
            "- [ ] 하드코딩된 경로/시크릿",
            "- [ ] `print()` 디버그 출력을 프로덕션 코드에 남기기",
            "- [ ] 테스트 없는 신규 public API",
            "",
        ]

    if "session" in sections:
        parts += [
            "## 세션 관리",
            "",
            "### 작업 시작 시",
            "",
            "1. 이 AGENTS.md를 읽고 현재 컨텍스트를 파악하세요",
            "2. `claude-progress.txt` (또는 세션 브릿지 파일)를 확인하세요",
            "3. 현재 작업 중인 feature branch를 확인하세요",
            "",
            "### 작업 종료 시",
            "",
            "1. `claude-progress.txt`에 완료한 작업과 다음 작업을 기록하세요",
            "2. `hachilles scan . --save-history`로 하네스 점수를 기록하세요",
            "3. 미완성 항목을 `feature_list.json`에 업데이트하세요",
            "",
            "### 주요 파일",
            "",
            "| 파일 | 역할 |",
            "|------|------|",
            "| `AGENTS.md` | AI 에이전트 가이드 (이 파일) |",
            "| `claude-progress.txt` | 세션 간 진행 상황 브릿지 |",
            "| `feature_list.json` | 완료 기준 구조화 목록 |",
            "| `docs/architecture.md` | 아키텍처 상세 문서 |",
            "",
        ]

    return "\n".join(line for line in parts if line is not None)
