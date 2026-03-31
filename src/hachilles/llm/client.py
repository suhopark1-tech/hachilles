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

"""Provider-agnostic LLM 클라이언트.

환경변수:
  HACHILLES_LLM_PROVIDER: "anthropic" | "openai" | "mock" (기본값: "mock")
  ANTHROPIC_API_KEY: Anthropic API 키
  OPENAI_API_KEY: OpenAI API 키
  HACHILLES_LLM_MODEL: 사용할 모델 이름 (기본값: provider별 기본값)
"""
from __future__ import annotations

import os

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "mock": "mock-model",
}


class LLMClient:
    """Provider-agnostic LLM 클라이언트."""

    def __init__(self) -> None:
        self.provider = os.environ.get("HACHILLES_LLM_PROVIDER", "mock").lower()
        self.model = os.environ.get(
            "HACHILLES_LLM_MODEL",
            DEFAULT_MODELS.get(self.provider, "mock-model"),
        )

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        """프롬프트에 대한 LLM 응답을 반환한다."""
        if self.provider == "anthropic":
            return self._complete_anthropic(prompt, max_tokens)
        elif self.provider == "openai":
            return self._complete_openai(prompt, max_tokens)
        else:
            return self._complete_mock(prompt)

    def _complete_anthropic(self, prompt: str, max_tokens: int) -> str:
        try:
            import anthropic  # type: ignore[import]  # [EXCEPTION] 선택적 의존성 — pip install hachilles[llm]
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except ImportError:
            return '{"over_engineering_score": 0.0, "evidence": [], "error": "anthropic 패키지가 없습니다. pip install hachilles[llm]"}'
        except Exception as e:
            return f'{{"over_engineering_score": 0.0, "evidence": [], "error": "{e}"}}'

    def _complete_openai(self, prompt: str, max_tokens: int) -> str:
        try:
            import openai  # type: ignore[import]  # [EXCEPTION] 선택적 의존성 — pip install hachilles[llm]
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except ImportError:
            return '{"over_engineering_score": 0.0, "evidence": [], "error": "openai 패키지가 없습니다"}'
        except Exception as e:
            return f'{{"over_engineering_score": 0.0, "evidence": [], "error": "{e}"}}'

    def _complete_mock(self, prompt: str) -> str:
        """테스트용 모의 응답."""
        return '{"over_engineering_score": 0.1, "evidence": ["모의 응답 — HACHILLES_LLM_PROVIDER를 설정하세요"], "summary": "mock"}'
