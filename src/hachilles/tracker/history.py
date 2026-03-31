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

"""SQLite 기반 진단 이력 저장소.

저장 위치: ~/.hachilles/history.db
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScanRecord:
    """단일 진단 기록."""
    id: int
    project_path: str
    timestamp: str         # ISO 8601
    total_score: int
    ce_score: int
    ac_score: int
    em_score: int
    grade: str             # S/A/B/C/D
    passed_items: int
    total_items: int
    tech_stack: list[str]


class HistoryDB:
    """진단 이력을 SQLite에 저장하고 조회한다."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".hachilles" / "history.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """테이블 생성 (없으면)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_score INTEGER NOT NULL,
                    ce_score INTEGER NOT NULL,
                    ac_score INTEGER NOT NULL,
                    em_score INTEGER NOT NULL,
                    grade TEXT NOT NULL,
                    passed_items INTEGER NOT NULL,
                    total_items INTEGER NOT NULL,
                    tech_stack TEXT NOT NULL DEFAULT '[]'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_project ON scan_history(project_path, timestamp)"
            )
            conn.commit()

    def save(
        self,
        project_path: str,
        timestamp: str,
        total_score: int,
        ce_score: int,
        ac_score: int,
        em_score: int,
        grade: str,
        passed_items: int,
        total_items: int,
        tech_stack: list[str],
    ) -> int:
        """진단 결과를 저장하고 생성된 ID를 반환한다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO scan_history
                   (project_path, timestamp, total_score, ce_score, ac_score,
                    em_score, grade, passed_items, total_items, tech_stack)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_path, timestamp, total_score,
                    ce_score, ac_score, em_score,
                    grade, passed_items, total_items,
                    json.dumps(tech_stack, ensure_ascii=False),
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_history(
        self, project_path: str, limit: int = 20
    ) -> list[ScanRecord]:
        """프로젝트의 최근 진단 이력을 반환한다."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, project_path, timestamp, total_score,
                          ce_score, ac_score, em_score, grade,
                          passed_items, total_items, tech_stack
                   FROM scan_history
                   WHERE project_path = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (project_path, limit),
            ).fetchall()

        records = []
        for row in rows:
            try:
                tech_stack = json.loads(row[10]) if row[10] else []
            except json.JSONDecodeError:
                tech_stack = []
            records.append(ScanRecord(
                id=row[0],
                project_path=row[1],
                timestamp=row[2],
                total_score=row[3],
                ce_score=row[4],
                ac_score=row[5],
                em_score=row[6],
                grade=row[7],
                passed_items=row[8],
                total_items=row[9],
                tech_stack=tech_stack,
            ))
        return records

    def get_all_projects(self) -> list[str]:
        """이력이 있는 모든 프로젝트 경로를 반환한다."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT project_path FROM scan_history ORDER BY project_path"
            ).fetchall()
        return [row[0] for row in rows]

    def trend(self, project_path: str, limit: int = 10) -> list[tuple[str, int]]:
        """점수 추이 (timestamp, score) 목록을 오래된 순으로 반환한다."""
        records = self.get_history(project_path, limit)
        return [(r.timestamp[:10], r.total_score) for r in reversed(records)]

    def ascii_chart(self, project_path: str, limit: int = 10) -> str:
        """점수 추이를 ASCII 차트로 렌더링한다."""
        trend = self.trend(project_path, limit)
        if not trend:
            return "이력 없음"

        scores = [s for _, s in trend]
        dates = [d for d, _ in trend]
        max_score = max(scores) if scores else 100
        min_score = min(scores) if scores else 0
        height = 10
        width = len(scores)

        lines = []
        lines.append(f"  점수 추이 — {project_path}")
        lines.append(f"  최고: {max_score}점  최저: {min_score}점  최신: {scores[-1]}점")
        lines.append("")

        for row in range(height, 0, -1):
            threshold = min_score + (max_score - min_score) * row / height
            line = f"{threshold:4.0f} │"
            for score in scores:
                if score >= threshold:
                    line += "█"
                else:
                    line += " "
            lines.append(line)

        lines.append("     └" + "─" * width)
        date_row = "      "
        for i, d in enumerate(dates):
            if i == 0 or i == len(dates) - 1:
                date_row += d[-5:]  # MM-DD
            else:
                date_row += " " * 5
        lines.append(date_row)

        return "\n".join(lines)
