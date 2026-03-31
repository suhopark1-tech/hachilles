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

"""HAchilles 시계열 성장 추적기 (Phase 2).

SQLite를 사용하여 진단 이력을 저장하고 점수 추이를 분석한다.
"""
from hachilles.tracker.history import HistoryDB, ScanRecord

__all__ = ["HistoryDB", "ScanRecord"]
