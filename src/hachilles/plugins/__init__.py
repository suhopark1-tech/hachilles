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

"""HAchilles 플러그인 SDK (Phase 3).

레이어 규칙: plugins는 models, auditors만 import 가능.
cli/api에서만 로딩 가능.

사용 예:
    from hachilles.plugins import PluginRegistry
    registry = PluginRegistry()
    registry.discover()  # ~/.hachilles/plugins/ 에서 자동 발견
"""
from hachilles.plugins.base import BaseAuditorPlugin
from hachilles.plugins.registry import PluginRegistry

__all__ = ["BaseAuditorPlugin", "PluginRegistry"]
