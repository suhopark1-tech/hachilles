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

"""HAchilles 플러그인 베이스 클래스."""
from __future__ import annotations

from abc import abstractmethod

from hachilles.auditors.base import BaseAuditor


class BaseAuditorPlugin(BaseAuditor):
    """외부 플러그인이 구현해야 하는 Auditor 기반 클래스.

    플러그인은 이 클래스를 상속하여 custom 진단 항목을 추가할 수 있다.

    주의: 플러그인의 full_score는 전체 100점 배점에 영향을 주지 않는다.
    플러그인 점수는 별도 집계되어 보고서에 'plugin_score' 항목으로 표시된다.

    사용 예:
        class MyPlugin(BaseAuditorPlugin):
            @property
            def plugin_name(self) -> str:
                return "my-custom-audit"

            @property
            def pillar(self) -> Pillar:
                return Pillar.CONSTRAINT

            @property
            def full_score(self) -> int:
                return 10

            @property
            def item_codes(self) -> list[str]:
                return ["MY-01"]

            def audit(self, scan):
                # 커스텀 진단 로직
                ...
    """

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """플러그인 고유 이름 (예: 'security-audit', 'docker-check')."""

    @property
    def plugin_version(self) -> str:
        """플러그인 버전 (기본값: '1.0.0')."""
        return "1.0.0"

    @property
    def plugin_description(self) -> str:
        """플러그인 설명."""
        return ""

    @property
    def plugin_author(self) -> str:
        """플러그인 작성자."""
        return ""
