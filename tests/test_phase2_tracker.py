"""Phase 2: 시계열 성장 추적기 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.tracker.history import HistoryDB, ScanRecord


@pytest.fixture()
def db(tmp_path: Path) -> HistoryDB:
    """임시 경로의 HistoryDB."""
    return HistoryDB(db_path=tmp_path / "test_history.db")


def _save(db: HistoryDB, path: str, score: int, ts: str, grade: str = "S") -> int:
    """테스트용 간편 저장 헬퍼."""
    ce = score * 40 // 100
    ac = score * 35 // 100
    em = score - ce - ac
    return db.save(path, ts, score, ce, ac, em, grade, 15, 15, ["python"])


class TestHistoryDB:

    def test_save_and_retrieve(self, db: HistoryDB) -> None:
        """저장한 레코드를 다시 불러온다."""
        _save(db, "/test/project", 100, "2026-03-28T00:00:00Z")
        records = db.get_history("/test/project")
        assert len(records) == 1
        assert records[0].total_score == 100
        assert records[0].project_path == "/test/project"

    def test_returns_scan_record_type(self, db: HistoryDB) -> None:
        """반환 타입이 ScanRecord 리스트다."""
        _save(db, "/p", 95, "2026-03-01T00:00:00Z")
        records = db.get_history("/p")
        assert all(isinstance(r, ScanRecord) for r in records)

    def test_multiple_records_ordered_by_desc(self, db: HistoryDB) -> None:
        """여러 레코드가 최신순으로 정렬된다."""
        _save(db, "/p", 70, "2026-01-01T00:00:00Z", "B")
        _save(db, "/p", 89, "2026-02-01T00:00:00Z", "A")
        _save(db, "/p", 100, "2026-03-01T00:00:00Z", "S")
        records = db.get_history("/p")
        assert records[0].total_score == 100
        assert records[1].total_score == 89
        assert records[2].total_score == 70

    def test_limit_respected(self, db: HistoryDB) -> None:
        """limit 파라미터가 결과 건수를 제한한다."""
        for i in range(10):
            _save(db, "/p", 80 + i, f"2026-01-{i+1:02d}T00:00:00Z")
        records = db.get_history("/p", limit=3)
        assert len(records) == 3

    def test_different_projects_isolated(self, db: HistoryDB) -> None:
        """다른 프로젝트의 이력은 서로 간섭하지 않는다."""
        _save(db, "/project-a", 100, "2026-03-01T00:00:00Z")
        _save(db, "/project-b", 70, "2026-03-01T00:00:00Z")
        assert db.get_history("/project-a")[0].total_score == 100
        assert db.get_history("/project-b")[0].total_score == 70

    def test_empty_history_returns_empty_list(self, db: HistoryDB) -> None:
        """이력이 없는 프로젝트는 빈 리스트를 반환한다."""
        records = db.get_history("/nonexistent/project")
        assert records == []

    def test_get_all_projects(self, db: HistoryDB) -> None:
        """get_all_projects()는 이력이 있는 모든 프로젝트를 반환한다."""
        _save(db, "/alpha", 90, "2026-03-01T00:00:00Z")
        _save(db, "/beta", 80, "2026-03-02T00:00:00Z")
        _save(db, "/alpha", 95, "2026-03-03T00:00:00Z")
        projects = db.get_all_projects()
        assert "/alpha" in projects
        assert "/beta" in projects
        assert len(projects) == 2

    def test_trend_order_is_ascending(self, db: HistoryDB) -> None:
        """trend()는 오래된 순(오름차순)으로 반환한다."""
        _save(db, "/p", 70, "2026-01-01T00:00:00Z")
        _save(db, "/p", 100, "2026-03-01T00:00:00Z")
        trend = db.trend("/p")
        scores = [s for _, s in trend]
        assert scores[0] == 70
        assert scores[-1] == 100

    def test_trend_empty_for_unknown_project(self, db: HistoryDB) -> None:
        """이력이 없는 프로젝트의 trend는 빈 리스트다."""
        assert db.trend("/unknown") == []

    def test_tech_stack_json_roundtrip(self, db: HistoryDB) -> None:
        """tech_stack 리스트가 JSON 직렬화 후 복원된다."""
        db.save("/p", "2026-03-01T00:00:00Z", 95, 40, 35, 20, "S", 14, 15,
                ["python", "typescript", "go"])
        record = db.get_history("/p")[0]
        assert record.tech_stack == ["python", "typescript", "go"]


class TestAsciiChart:

    def test_no_history_returns_message(self, db: HistoryDB) -> None:
        """이력이 없으면 안내 메시지를 반환한다."""
        chart = db.ascii_chart("/unknown")
        assert "이력" in chart

    def test_chart_contains_score(self, db: HistoryDB) -> None:
        """차트에 최고·최저·최신 점수가 포함된다."""
        _save(db, "/p", 70, "2026-01-01T00:00:00Z")
        _save(db, "/p", 100, "2026-03-01T00:00:00Z")
        chart = db.ascii_chart("/p")
        assert "70" in chart
        assert "100" in chart

    def test_chart_is_string(self, db: HistoryDB) -> None:
        """chart()는 항상 문자열을 반환한다."""
        chart = db.ascii_chart("/any")
        assert isinstance(chart, str)

    def test_chart_with_single_record(self, db: HistoryDB) -> None:
        """레코드 1개로도 차트가 렌더링된다."""
        _save(db, "/p", 85, "2026-03-01T00:00:00Z")
        chart = db.ascii_chart("/p")
        assert "85" in chart
