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

"""LLM 응답 디스크 캐시.

캐시 키: SHA-256(provider + model + prompt) → JSON 파일로 저장.
캐시 위치: ~/.hachilles/llm_cache/
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class LLMCache:
    """LLM 응답을 디스크에 캐싱하여 반복 호출을 방지한다."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path.home() / ".hachilles" / "llm_cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

    def _key(self, provider: str, model: str, prompt: str) -> str:
        """캐시 키 생성 (SHA-256 해시)."""
        raw = f"{provider}::{model}::{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, provider: str, model: str, prompt: str) -> str | None:
        """캐시에서 응답을 조회한다. 없으면 None 반환."""
        key = self._key(provider, model, prompt)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                self._hits += 1
                return data.get("response")
            except (json.JSONDecodeError, OSError):
                pass
        self._misses += 1
        return None

    def set(self, provider: str, model: str, prompt: str, response: str) -> None:
        """캐시에 응답을 저장한다."""
        key = self._key(provider, model, prompt)
        cache_file = self.cache_dir / f"{key}.json"
        data = {"provider": provider, "model": model, "response": response}
        try:
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @property
    def hit_rate(self) -> float:
        """캐시 적중률 (0.0~1.0)."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, int | float]:
        """캐시 통계 반환."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "cache_files": len(list(self.cache_dir.glob("*.json"))),
        }
