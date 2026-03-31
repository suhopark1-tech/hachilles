"""Phase 2: LLM 평가 모듈 테스트."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hachilles.llm.cache import LLMCache
from hachilles.llm.client import DEFAULT_MODELS, LLMClient
from hachilles.llm.evaluator import LLMEvaluator

# ── LLMCache 테스트 ──────────────────────────────────────────────────────────

class TestLLMCache:

    @pytest.fixture()
    def cache(self, tmp_path: Path) -> LLMCache:
        return LLMCache(cache_dir=tmp_path / "cache")

    def test_get_miss_returns_none(self, cache: LLMCache) -> None:
        """캐시에 없는 항목은 None을 반환한다."""
        result = cache.get("anthropic", "claude-haiku", "test prompt")
        assert result is None

    def test_set_and_get_roundtrip(self, cache: LLMCache) -> None:
        """저장한 응답을 정확히 불러온다."""
        cache.set("mock", "mock-model", "hello", "world response")
        result = cache.get("mock", "mock-model", "hello")
        assert result == "world response"

    def test_different_keys_no_collision(self, cache: LLMCache) -> None:
        """다른 키는 서로 간섭하지 않는다."""
        cache.set("mock", "model-a", "prompt", "response-a")
        cache.set("mock", "model-b", "prompt", "response-b")
        assert cache.get("mock", "model-a", "prompt") == "response-a"
        assert cache.get("mock", "model-b", "prompt") == "response-b"

    def test_hit_rate_zero_on_all_miss(self, cache: LLMCache) -> None:
        """캐시 미스만 있으면 적중률은 0.0이다."""
        cache.get("x", "y", "z")
        assert cache.hit_rate == 0.0

    def test_hit_rate_one_on_all_hit(self, cache: LLMCache) -> None:
        """캐시 히트만 있으면 적중률은 1.0이다."""
        cache.set("x", "y", "z", "resp")
        cache.get("x", "y", "z")
        assert cache.hit_rate == 1.0

    def test_hit_rate_partial(self, cache: LLMCache) -> None:
        """히트 1회 + 미스 1회 → 0.5 적중률."""
        cache.set("x", "y", "z", "resp")
        cache.get("x", "y", "z")   # hit
        cache.get("x", "y", "zz")  # miss
        assert cache.hit_rate == 0.5

    def test_stats_returns_dict(self, cache: LLMCache) -> None:
        """stats()는 올바른 키를 가진 dict를 반환한다."""
        stats = cache.stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "cache_files" in stats

    def test_cache_files_count(self, cache: LLMCache) -> None:
        """저장된 파일 수가 stats에 반영된다."""
        cache.set("p", "m", "prompt1", "r1")
        cache.set("p", "m", "prompt2", "r2")
        stats = cache.stats()
        assert stats["cache_files"] == 2

    def test_unicode_content_preserved(self, cache: LLMCache) -> None:
        """한국어 등 유니코드 응답이 손실 없이 저장된다."""
        response = '{"over_engineering_score": 0.3, "evidence": ["불필요한 추상화 레이어"], "summary": "경미"}'
        cache.set("mock", "m", "p", response)
        assert cache.get("mock", "m", "p") == response


# ── LLMClient 테스트 ─────────────────────────────────────────────────────────

class TestLLMClient:

    def test_default_provider_is_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """환경변수가 없으면 기본 provider는 mock이다."""
        monkeypatch.delenv("HACHILLES_LLM_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "mock"

    def test_provider_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """환경변수로 provider를 선택할 수 있다."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "openai")
        client = LLMClient()
        assert client.provider == "openai"

    def test_model_from_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """HACHILLES_LLM_MODEL로 모델을 재정의할 수 있다."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("HACHILLES_LLM_MODEL", "claude-opus-4-6")
        client = LLMClient()
        assert client.model == "claude-opus-4-6"

    def test_mock_complete_returns_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """mock provider는 올바른 JSON 형식으로 응답한다."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "mock")
        monkeypatch.delenv("HACHILLES_LLM_MODEL", raising=False)
        client = LLMClient()
        response = client.complete("test prompt")
        data = json.loads(response)
        assert "over_engineering_score" in data
        assert "evidence" in data

    def test_default_models_defined(self) -> None:
        """각 provider에 기본 모델이 정의돼 있다."""
        assert "anthropic" in DEFAULT_MODELS
        assert "openai" in DEFAULT_MODELS
        assert "mock" in DEFAULT_MODELS

    def test_provider_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """provider명은 대소문자 무관하다."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "MOCK")
        client = LLMClient()
        assert client.provider == "mock"


# ── LLMEvaluator 테스트 ──────────────────────────────────────────────────────

class TestLLMEvaluator:

    @pytest.fixture()
    def evaluator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LLMEvaluator:
        """mock provider + 임시 캐시 경로를 사용하는 evaluator."""
        monkeypatch.setenv("HACHILLES_LLM_PROVIDER", "mock")
        cache = LLMCache(cache_dir=tmp_path / "cache")
        return LLMEvaluator(cache=cache)

    def test_evaluate_returns_score_and_evidence(
        self, evaluator: LLMEvaluator, tmp_path: Path
    ) -> None:
        """evaluate_over_engineering()는 (float, list) 튜플을 반환한다."""
        score, evidence = evaluator.evaluate_over_engineering(tmp_path)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(evidence, list)

    def test_score_clamped_to_0_1(
        self, evaluator: LLMEvaluator, tmp_path: Path
    ) -> None:
        """점수가 0~1 범위를 벗어나지 않는다."""
        # 극단값을 반환하는 mock 클라이언트
        evaluator.client.complete = lambda p, **kw: '{"over_engineering_score": 99.9, "evidence": []}'  # type: ignore[method-assign]  # [EXCEPTION] 테스트용 monkey-patch
        score, _ = evaluator.evaluate_over_engineering(tmp_path)
        assert score <= 1.0

    def test_second_call_uses_cache(
        self, evaluator: LLMEvaluator, tmp_path: Path
    ) -> None:
        """동일 프로젝트의 두 번째 호출은 캐시를 사용한다."""
        evaluator.evaluate_over_engineering(tmp_path)
        evaluator.evaluate_over_engineering(tmp_path)
        # 두 번째 호출은 캐시 히트
        assert evaluator.cache.hit_rate > 0

    def test_invalid_json_response_returns_defaults(
        self, evaluator: LLMEvaluator, tmp_path: Path
    ) -> None:
        """LLM이 유효하지 않은 JSON을 반환하면 기본값을 반환한다."""
        evaluator.client.complete = lambda p, **kw: "이것은 JSON이 아닙니다"  # type: ignore[method-assign]  # [EXCEPTION] 테스트용 monkey-patch
        score, evidence = evaluator.evaluate_over_engineering(tmp_path)
        assert score == 0.0
        assert isinstance(evidence, list)

    def test_parse_response_valid_json(self, evaluator: LLMEvaluator) -> None:
        """올바른 JSON 응답을 파싱한다."""
        response = '{"over_engineering_score": 0.4, "evidence": ["불필요한 추상화"], "summary": "경미"}'
        score, evidence = evaluator._parse_response(response)
        assert score == pytest.approx(0.4)
        assert "불필요한 추상화" in evidence

    def test_parse_response_markdown_codeblock(self, evaluator: LLMEvaluator) -> None:
        """마크다운 코드블록 내부 JSON도 파싱한다."""
        response = '```json\n{"over_engineering_score": 0.2, "evidence": []}\n```'
        score, evidence = evaluator._parse_response(response)
        assert score == pytest.approx(0.2)
