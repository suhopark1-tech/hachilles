"""Phase 2: Scanner Go/Java 지원 + AST 통합 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.scanner.scanner import Scanner


@pytest.fixture()
def make_project(tmp_path: Path):
    """프로젝트 파일 생성 헬퍼 팩토리."""
    def _make(files: dict[str, str]) -> Path:
        for rel_path, content in files.items():
            target = tmp_path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return tmp_path
    return _make


# ── Go 스캔 테스트 ───────────────────────────────────────────────────────────

class TestGoScan:

    def test_go_module_name_extracted(self, make_project) -> None:
        """go.mod에서 모듈명을 추출한다."""
        project = make_project({
            "go.mod": "module github.com/example/myapp\n\ngo 1.21\n",
        })
        result = Scanner(project).scan()
        assert result.go_module_name == "github.com/example/myapp"

    def test_go_has_tests_detected(self, make_project) -> None:
        """*_test.go 파일이 있으면 go_has_tests가 True다."""
        project = make_project({
            "go.mod": "module example.com/app\n",
            "main_test.go": "package main\n\nimport \"testing\"\n",
        })
        result = Scanner(project).scan()
        assert result.go_has_tests is True

    def test_go_no_tests_when_none(self, make_project) -> None:
        """*_test.go 파일이 없으면 go_has_tests가 False다."""
        project = make_project({
            "go.mod": "module example.com/app\n",
            "main.go": "package main\n",
        })
        result = Scanner(project).scan()
        assert result.go_has_tests is False

    def test_go_linter_detected_via_config(self, make_project) -> None:
        """golangci-lint 설정 파일이 있으면 go_has_linter가 True다."""
        project = make_project({
            "go.mod": "module example.com/app\n",
            ".golangci.yml": "linters:\n  enable:\n    - errcheck\n",
        })
        result = Scanner(project).scan()
        assert result.go_has_linter is True

    def test_go_linter_detected_via_ci(self, make_project) -> None:
        """CI 워크플로우에서 golangci-lint 사용 시 go_has_linter가 True다."""
        project = make_project({
            "go.mod": "module example.com/app\n",
            ".github/workflows/ci.yml": (
                "name: CI\non: push\njobs:\n  lint:\n    steps:\n"
                "      - uses: golangci/golangci-lint-action@v3\n"
            ),
        })
        result = Scanner(project).scan()
        assert result.go_has_linter is True

    def test_no_go_mod_go_fields_empty(self, make_project) -> None:
        """go.mod가 없으면 Go 관련 필드가 기본값이다."""
        project = make_project({"README.md": "# Test\n"})
        result = Scanner(project).scan()
        assert result.go_module_name == ""
        assert result.go_has_tests is False
        assert result.go_has_linter is False


# ── Java 스캔 테스트 ─────────────────────────────────────────────────────────

class TestJavaScan:

    def test_maven_build_tool_detected(self, make_project) -> None:
        """pom.xml이 있으면 java_build_tool이 'maven'이다."""
        project = make_project({
            "pom.xml": "<project><modelVersion>4.0.0</modelVersion></project>",
        })
        result = Scanner(project).scan()
        assert result.java_build_tool == "maven"

    def test_gradle_build_tool_detected(self, make_project) -> None:
        """build.gradle이 있으면 java_build_tool이 'gradle'이다."""
        project = make_project({
            "build.gradle": "plugins {\n  id 'java'\n}\n",
        })
        result = Scanner(project).scan()
        assert result.java_build_tool == "gradle"

    def test_gradle_kts_build_tool_detected(self, make_project) -> None:
        """build.gradle.kts도 gradle로 인식한다."""
        project = make_project({
            "build.gradle.kts": "plugins {\n  java\n}\n",
        })
        result = Scanner(project).scan()
        assert result.java_build_tool == "gradle"

    def test_java_has_tests_detected(self, make_project) -> None:
        """src/test/ 디렉토리가 있으면 java_has_tests가 True다."""
        project = make_project({
            "pom.xml": "<project/>",
            "src/test/java/AppTest.java": "public class AppTest {}",
        })
        result = Scanner(project).scan()
        assert result.java_has_tests is True

    def test_java_no_tests_when_none(self, make_project) -> None:
        """src/test/가 없으면 java_has_tests가 False다."""
        project = make_project({
            "pom.xml": "<project/>",
            "src/main/java/App.java": "public class App {}",
        })
        result = Scanner(project).scan()
        assert result.java_has_tests is False

    def test_java_linter_via_checkstyle_file(self, make_project) -> None:
        """checkstyle.xml이 있으면 java_has_linter가 True다."""
        project = make_project({
            "pom.xml": "<project/>",
            "checkstyle.xml": "<?xml version='1.0'?><module name='Checker'/>",
        })
        result = Scanner(project).scan()
        assert result.java_has_linter is True

    def test_java_linter_via_pom_plugin(self, make_project) -> None:
        """pom.xml에 checkstyle 플러그인이 있으면 java_has_linter가 True다."""
        project = make_project({
            "pom.xml": (
                "<project><build><plugins><plugin>"
                "<artifactId>maven-checkstyle-plugin</artifactId>"
                "</plugin></plugins></build></project>"
            ),
        })
        result = Scanner(project).scan()
        assert result.java_has_linter is True

    def test_no_java_build_file_java_fields_empty(self, make_project) -> None:
        """빌드 파일이 없으면 Java 관련 필드가 기본값이다."""
        project = make_project({"README.md": "# Test\n"})
        result = Scanner(project).scan()
        assert result.java_build_tool == ""
        assert result.java_has_tests is False
        assert result.java_has_linter is False


# ── 스캔 타임스탬프 테스트 ────────────────────────────────────────────────────

class TestScanTimestamp:

    def test_scan_timestamp_is_set(self, make_project) -> None:
        """scan() 후 scan_timestamp가 ISO 8601 형식으로 설정된다."""
        project = make_project({"README.md": ""})
        result = Scanner(project).scan()
        ts = result.scan_timestamp
        assert ts != ""
        # ISO 8601 형식 확인 (최소한 날짜 부분 포함)
        assert "T" in ts or len(ts) >= 10

    def test_scan_timestamp_contains_timezone(self, make_project) -> None:
        """scan_timestamp에 UTC 타임존(+00:00 또는 Z)이 포함된다."""
        project = make_project({"README.md": ""})
        result = Scanner(project).scan()
        # Python의 isoformat()은 +00:00 형태로 UTC를 표현
        assert "+00:00" in result.scan_timestamp or result.scan_timestamp.endswith("Z")


# ── AST 통합: 자기 자신 진단 ─────────────────────────────────────────────────

class TestASTIntegration:

    def test_hachilles_self_scan_no_violations(self) -> None:
        """HAchilles 자체 코드는 AST 분석에서 위반이 없어야 한다."""
        src_path = Path(__file__).parent.parent / "src" / "hachilles"
        result = Scanner(src_path.parent.parent).scan()
        # 레이어 위반과 순환 의존성이 없어야 함
        assert result.dependency_violations == 0
        assert result.dependency_cycles == []
        assert result.layer_violations == []
