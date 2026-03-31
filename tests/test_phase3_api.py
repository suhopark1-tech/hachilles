"""Phase 3 FastAPI 테스트 (최소 15개 테스트)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hachilles.api import create_app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient 생성."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_project_path(tmp_path: Path) -> Path:
    """간단한 샘플 프로젝트 생성."""
    # AGENTS.md 생성
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("# Sample Project\n\nTest AGENTS.md file")

    # .gitignore 생성
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")

    # Python 파일 생성
    py_file = tmp_path / "main.py"
    py_file.write_text("# Sample Python file\nprint('Hello')\n")

    return tmp_path


class TestScanEndpoint:
    """POST /api/v1/scan 테스트."""

    def test_scan_valid_path(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """유효한 프로젝트 경로 스캔."""
        response = client.post(
            "/api/v1/scan",
            json={"path": str(sample_project_path), "llm": False, "save_history": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert 0 <= data["total"] <= 100
        assert data["grade"] in ["S", "A", "B", "C", "D"]

    def test_scan_response_schema(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """응답 스키마 검증."""
        response = client.post(
            "/api/v1/scan",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()

        # 필수 필드 검증
        required_fields = [
            "hachilles_version",
            "total",
            "grade",
            "grade_label",
            "passed_rate",
            "context",
            "constraint",
            "entropy",
            "pattern_risks",
            "tech_stack",
            "scan_timestamp",
            "scan_errors",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_scan_invalid_path(self, client: TestClient) -> None:
        """존재하지 않는 경로 스캔."""
        response = client.post(
            "/api/v1/scan",
            json={"path": "/nonexistent/path/12345"},
        )
        assert response.status_code == 404

    def test_scan_non_directory_path(self, client: TestClient, tmp_path: Path) -> None:
        """파일 경로로 스캔 시도."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        response = client.post(
            "/api/v1/scan",
            json={"path": str(file_path)},
        )
        assert response.status_code == 400

    def test_scan_score_bounds(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """점수 범위 검증 (0-100)."""
        response = client.post(
            "/api/v1/scan",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["total"] <= 100
        assert data["passed_rate"] is not None

    def test_scan_with_history_flag(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """이력 저장 플래그 테스트."""
        response = client.post(
            "/api/v1/scan",
            json={
                "path": str(sample_project_path),
                "save_history": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "scan_errors" in data

    def test_scan_pillar_structure(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """Pillar 응답 구조 검증."""
        response = client.post(
            "/api/v1/scan",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()

        for pillar_key in ["context", "constraint", "entropy"]:
            pillar = data[pillar_key]
            assert "pillar" in pillar
            assert "score" in pillar
            assert "full_score" in pillar
            assert "passed_count" in pillar
            assert "items" in pillar
            assert isinstance(pillar["items"], list)

    def test_scan_audit_item_structure(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """AuditItem 응답 구조 검증."""
        response = client.post(
            "/api/v1/scan",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()

        items = data["context"]["items"]
        if items:
            item = items[0]
            assert "code" in item
            assert "name" in item
            assert "passed" in item
            assert isinstance(item["passed"], bool)
            assert "score" in item
            assert "full_score" in item


class TestHistoryEndpoint:
    """GET /api/v1/history 테스트."""

    def test_history_valid_path(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """유효한 프로젝트 경로로 이력 조회."""
        # 먼저 스캔을 실행하여 이력 저장
        client.post(
            "/api/v1/scan",
            json={
                "path": str(sample_project_path),
                "save_history": True,
            },
        )

        # 이력 조회
        response = client.get(
            f"/api/v1/history?path={sample_project_path}&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert "project_path" in data
        assert "records" in data
        assert "trend" in data

    def test_history_response_schema(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """이력 응답 스키마 검증."""
        client.post(
            "/api/v1/scan",
            json={
                "path": str(sample_project_path),
                "save_history": True,
            },
        )

        response = client.get(
            f"/api/v1/history?path={sample_project_path}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        if data["records"]:
            record = data["records"][0]
            assert "id" in record
            assert "timestamp" in record
            assert "total_score" in record
            assert "grade" in record


class TestHealthEndpoint:
    """GET /api/health 테스트."""

    def test_health_check(self, client: TestClient) -> None:
        """헬스 체크 엔드포인트."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "ok"


class TestGenerateAgentsEndpoint:
    """POST /api/v1/generate-agents 테스트."""

    def test_generate_agents_valid_path(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """유효한 프로젝트 경로로 AGENTS.md 생성."""
        response = client.post(
            "/api/v1/generate-agents",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "sections" in data
        assert "estimated_lines" in data
        assert len(data["content"]) > 0
        assert isinstance(data["sections"], list)

    def test_generate_agents_invalid_path(self, client: TestClient) -> None:
        """존재하지 않는 경로로 AGENTS.md 생성 시도."""
        response = client.post(
            "/api/v1/generate-agents",
            json={"path": "/nonexistent/path/12345"},
        )
        assert response.status_code == 404

    def test_generate_agents_response_structure(
        self, client: TestClient, sample_project_path: Path
    ) -> None:
        """AGENTS.md 생성 응답 구조 검증."""
        response = client.post(
            "/api/v1/generate-agents",
            json={"path": str(sample_project_path)},
        )
        assert response.status_code == 200
        data = response.json()

        # 필수 섹션 확인
        content = data["content"]
        assert "# " in content  # Markdown 헤더
        assert "프로젝트 개요" in content or "architecture" in content
