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

"""HAchilles 플러그인 레지스트리 — 자동 발견 및 로딩."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from hachilles.plugins.base import BaseAuditorPlugin

# 기본 플러그인 디렉토리
_DEFAULT_PLUGIN_DIR = Path.home() / ".hachilles" / "plugins"


class PluginRegistry:
    """플러그인을 발견하고 관리하는 레지스트리.

    사용 예:
        registry = PluginRegistry()
        registry.discover()
        plugins = registry.plugins
        for plugin in plugins:
            result = plugin.audit(scan_result)
    """

    def __init__(self, plugin_dir: Path | None = None) -> None:
        self._plugin_dir = plugin_dir or _DEFAULT_PLUGIN_DIR
        self._plugins: list[BaseAuditorPlugin] = []
        self._errors: list[str] = []

    @property
    def plugins(self) -> list[BaseAuditorPlugin]:
        """로딩된 플러그인 목록."""
        return list(self._plugins)

    @property
    def errors(self) -> list[str]:
        """플러그인 로딩 중 발생한 오류 목록."""
        return list(self._errors)

    def discover(self) -> int:
        """플러그인 디렉토리에서 플러그인을 자동 발견하여 로딩한다.

        플러그인 규칙:
          - ~/.hachilles/plugins/{name}/plugin.py 파일이 있어야 한다.
          - plugin.py는 BaseAuditorPlugin 서브클래스를 export해야 한다.
          - 클래스명이 'Plugin'으로 끝나는 클래스를 자동 감지한다.

        Returns:
            로딩 성공한 플러그인 수
        """
        self._plugins.clear()
        self._errors.clear()

        if not self._plugin_dir.exists():
            return 0

        loaded = 0
        for plugin_path in sorted(self._plugin_dir.glob("*/plugin.py")):
            plugin_name = plugin_path.parent.name
            try:
                plugin_instance = self._load_plugin(plugin_name, plugin_path)
                if plugin_instance:
                    self._plugins.append(plugin_instance)
                    loaded += 1
            except Exception as e:  # [EXCEPTION] 개별 플러그인 실패는 비치명적
                self._errors.append(f"플러그인 '{plugin_name}' 로딩 실패: {e}")

        return loaded

    def register(self, plugin: BaseAuditorPlugin) -> None:
        """플러그인 인스턴스를 직접 등록한다 (테스트·프로그래매틱 등록용)."""
        self._plugins.append(plugin)

    def _load_plugin(self, name: str, path: Path) -> BaseAuditorPlugin | None:
        """단일 플러그인 파일에서 BaseAuditorPlugin 서브클래스를 로딩한다."""
        module_name = f"hachilles_plugin_{name}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]  # [EXCEPTION] spec.loader는 위 조건 분기에서 not None 보장됨

        # Plugin으로 끝나는 BaseAuditorPlugin 서브클래스 찾기
        for attr_name in dir(module):
            if not attr_name.endswith("Plugin"):
                continue
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseAuditorPlugin)
                and attr is not BaseAuditorPlugin
            ):
                return attr()

        return None
