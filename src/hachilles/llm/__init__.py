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

"""HAchilles LLM 평가 모듈 (Phase 2).

Provider-agnostic LLM 클라이언트로 코드베이스의 Over-engineering 패턴을 탐지한다.
환경변수 HACHILLES_LLM_PROVIDER로 제공자를 선택한다.
"""
from hachilles.llm.cache import LLMCache
from hachilles.llm.evaluator import LLMEvaluator

__all__ = ["LLMEvaluator", "LLMCache"]
