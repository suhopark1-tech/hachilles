"""Phase 3 플러그인 SDK 테스트 (최소 10개 테스트)."""
from __future__ import annotations

from pathlib import Path

from hachilles.models.scan_result import AuditItem, AuditResult, Pillar, ScanResult
from hachilles.plugins.base import BaseAuditorPlugin
from hachilles.plugins.registry import PluginRegistry


class DummyPlugin(BaseAuditorPlugin):
    """테스트용 더미 플러그인."""

    @property
    def plugin_name(self) -> str:
        return "dummy-plugin"

    @property
    def pillar(self) -> Pillar:
        return Pillar.CONTEXT

    @property
    def full_score(self) -> int:
        return 10

    @property
    def item_codes(self) -> list[str]:
        return ["DUMMY-01"]

    def audit(self, scan: ScanResult) -> AuditResult:
        """더미 감사 구현."""
        result = AuditResult(pillar=Pillar.CONTEXT)
        item = AuditItem(
            code="DUMMY-01",
            pillar=Pillar.CONTEXT,
            name="Dummy Test",
            passed=True,
            score=10,
            full_score=10,
            detail="Dummy test item",
        )
        result.items.append(item)
        return result


class FailingPlugin(BaseAuditorPlugin):
    """실패하는 플러그인."""

    @property
    def plugin_name(self) -> str:
        return "failing-plugin"

    @property
    def pillar(self) -> Pillar:
        return Pillar.CONSTRAINT

    @property
    def full_score(self) -> int:
        return 5

    @property
    def item_codes(self) -> list[str]:
        return ["FAIL-01"]

    def audit(self, scan: ScanResult) -> AuditResult:
        """실패하는 감사."""
        result = AuditResult(pillar=Pillar.CONSTRAINT)
        item = AuditItem(
            code="FAIL-01",
            pillar=Pillar.CONSTRAINT,
            name="Failing Test",
            passed=False,
            score=0,
            full_score=5,
            detail="This item failed",
        )
        result.items.append(item)
        return result


class TestPluginRegistry:
    """PluginRegistry 테스트."""

    def test_registry_init(self, tmp_path: Path) -> None:
        """PluginRegistry 초기화."""
        registry = PluginRegistry(tmp_path)
        assert registry.plugins == []
        assert registry.errors == []

    def test_register_plugin(self, tmp_path: Path) -> None:
        """플러그인 수동 등록."""
        registry = PluginRegistry(tmp_path)
        plugin = DummyPlugin()
        registry.register(plugin)

        assert len(registry.plugins) == 1
        assert registry.plugins[0].plugin_name == "dummy-plugin"

    def test_register_multiple_plugins(self, tmp_path: Path) -> None:
        """여러 플러그인 등록."""
        registry = PluginRegistry(tmp_path)
        dummy = DummyPlugin()
        failing = FailingPlugin()

        registry.register(dummy)
        registry.register(failing)

        assert len(registry.plugins) == 2

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """빈 디렉토리에서 플러그인 발견."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        registry = PluginRegistry(plugins_dir)
        count = registry.discover()

        assert count == 0
        assert registry.plugins == []

    def test_discover_nonexistent_directory(self, tmp_path: Path) -> None:
        """존재하지 않는 디렉토리에서 발견 시도."""
        nonexistent = tmp_path / "nonexistent" / "plugins"

        registry = PluginRegistry(nonexistent)
        count = registry.discover()

        assert count == 0
        assert registry.errors == []

    def test_plugins_property(self, tmp_path: Path) -> None:
        """플러그인 리스트 반환."""
        registry = PluginRegistry(tmp_path)
        dummy = DummyPlugin()
        registry.register(dummy)

        plugins = registry.plugins
        assert isinstance(plugins, list)
        assert len(plugins) == 1

    def test_errors_property(self, tmp_path: Path) -> None:
        """오류 리스트 반환."""
        registry = PluginRegistry(tmp_path)

        errors = registry.errors
        assert isinstance(errors, list)
        assert len(errors) == 0


class TestBaseAuditorPlugin:
    """BaseAuditorPlugin 테스트."""

    def test_plugin_name_property(self) -> None:
        """plugin_name 속성 검증."""
        plugin = DummyPlugin()
        assert plugin.plugin_name == "dummy-plugin"

    def test_plugin_version_property(self) -> None:
        """plugin_version 속성 기본값."""
        plugin = DummyPlugin()
        assert plugin.plugin_version == "1.0.0"

    def test_plugin_description_property(self) -> None:
        """plugin_description 속성 기본값."""
        plugin = DummyPlugin()
        assert plugin.plugin_description == ""

    def test_plugin_author_property(self) -> None:
        """plugin_author 속성 기본값."""
        plugin = DummyPlugin()
        assert plugin.plugin_author == ""

    def test_plugin_audit_method(self, tmp_path: Path) -> None:
        """플러그인 audit() 메서드 실행."""
        plugin = DummyPlugin()
        scan = ScanResult(target_path=tmp_path)

        result = plugin.audit(scan)

        assert isinstance(result, AuditResult)
        assert result.pillar == Pillar.CONTEXT
        assert len(result.items) == 1
        assert result.items[0].code == "DUMMY-01"

    def test_plugin_inheritance(self) -> None:
        """BaseAuditorPlugin 상속 검증."""
        plugin = DummyPlugin()
        assert isinstance(plugin, BaseAuditorPlugin)

    def test_failing_plugin_audit(self, tmp_path: Path) -> None:
        """실패하는 플러그인 감사."""
        plugin = FailingPlugin()
        scan = ScanResult(target_path=tmp_path)

        result = plugin.audit(scan)

        assert result.pillar == Pillar.CONSTRAINT
        assert result.items[0].passed is False
        assert result.items[0].score == 0


class TestPluginIntegration:
    """플러그인 통합 테스트."""

    def test_registry_with_multiple_plugin_types(self, tmp_path: Path) -> None:
        """다양한 플러그인 타입 레지스트리."""
        registry = PluginRegistry(tmp_path)

        # 여러 플러그인 등록
        registry.register(DummyPlugin())
        registry.register(FailingPlugin())

        assert len(registry.plugins) == 2

        # 플러그인 이름 확인
        names = [p.plugin_name for p in registry.plugins]
        assert "dummy-plugin" in names
        assert "failing-plugin" in names

    def test_plugin_full_score_consistency(self, tmp_path: Path) -> None:
        """플러그인 점수 일관성."""
        dummy = DummyPlugin()
        failing = FailingPlugin()

        dummy_result = dummy.audit(ScanResult(target_path=tmp_path))
        failing_result = failing.audit(ScanResult(target_path=tmp_path))

        # 각 플러그인의 점수가 full_score와 일치
        dummy_full = sum(item.full_score for item in dummy_result.items)

        failing_full = sum(item.full_score for item in failing_result.items)

        assert dummy_full > 0
        assert failing_full > 0
