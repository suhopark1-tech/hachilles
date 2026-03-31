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

"""LLM 기반 Over-engineering 패턴 평가기.

Over-engineering 탐지 항목:
  1. 불필요한 추상화 레이어 (Abstract Factory, Strategy 남발)
  2. 미사용 범용 인터페이스
  3. 과도한 설정 파일 계층
  4. 과잉 설계된 데이터 클래스
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from hachilles.llm.cache import LLMCache
from hachilles.llm.client import LLMClient

_OVER_ENG_PROMPT_TEMPLATE = """당신은 AI 에이전트 하네스 설계 품질 전문가입니다.
다음 코드베이스 요약을 분석하여 Over-engineering 패턴을 탐지하세요.

코드베이스 요약:
{code_summary}

다음 JSON 형식으로 응답하세요:
{{
  "over_engineering_score": 0.0 ~ 1.0,
  "evidence": ["근거1", "근거2", ...],
  "summary": "전체 평가 요약"
}}

판단 기준:
- 0.0: Over-engineering 없음
- 0.3: 경미한 수준 (일부 불필요한 추상화)
- 0.6: 중간 수준 (여러 미사용 인터페이스, 복잡한 팩토리 패턴)
- 1.0: 심각한 수준 (대부분의 코드가 실제 기능보다 구조를 위한 구조)
"""


class LLMEvaluator:
    """LLM을 사용하여 Over-engineering 패턴을 탐지한다."""

    def __init__(self, cache: LLMCache | None = None) -> None:
        self.client = LLMClient()
        self.cache = cache or LLMCache()

    def evaluate_over_engineering(
        self, target: Path, max_files: int = 20
    ) -> tuple[float, list[str]]:
        """Over-engineering 점수와 근거 목록을 반환한다.

        Returns:
            (score, evidence_list)
            score: 0.0~1.0 (0=없음, 1=매우 심함)
            evidence_list: 근거 목록
        """
        code_summary = self._build_code_summary(target, max_files)
        prompt = _OVER_ENG_PROMPT_TEMPLATE.format(code_summary=code_summary)

        # 캐시 조회
        cached = self.cache.get(self.client.provider, self.client.model, prompt)
        if cached:
            result = self._parse_response(cached)
            return result[0], result[1]

        # LLM 호출
        response = self.client.complete(prompt, max_tokens=512)
        self.cache.set(self.client.provider, self.client.model, prompt, response)

        return self._parse_response(response)

    def _build_code_summary(self, target: Path, max_files: int) -> str:
        """코드베이스 요약 문자열 생성 (프롬프트 삽입용)."""
        lines = [f"프로젝트 경로: {target.name}"]
        exclude = {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            "dist", "build", ".pytest_cache",
        }

        py_files = [
            f for f in target.rglob("*.py")
            if not any(part in exclude for part in f.parts)
        ][:max_files]

        for f in py_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                # 클래스/함수 정의만 추출 (최대 30줄)
                defs = [
                    line for line in content.splitlines()
                    if re.match(r"^\s*(class|def|async def)\s+", line)
                ][:30]
                if defs:
                    rel = f.relative_to(target)
                    lines.append(f"\n파일: {rel}")
                    lines.extend(defs)
            except OSError:
                continue

        return "\n".join(lines)[:4000]  # 프롬프트 크기 제한

    def _parse_response(self, response: str) -> tuple[float, list[str]]:
        """LLM 응답 JSON 파싱. 파싱 실패 시 기본값 반환."""
        try:
            # JSON 블록 추출 (마크다운 코드블록 내부일 수 있음)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("over_engineering_score", 0.0))
                score = max(0.0, min(1.0, score))  # 0~1 클리핑
                evidence = data.get("evidence", [])
                if not isinstance(evidence, list):
                    evidence = []
                return score, [str(e) for e in evidence]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return 0.0, ["LLM 응답 파싱 실패"]
