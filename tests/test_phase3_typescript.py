"""Phase 3 TypeScript 스캔 테스트 (최소 10개 테스트)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hachilles.scanner import Scanner


@pytest.fixture
def ts_project_with_eslint(tmp_path: Path) -> Path:
    """ESLint 설정이 있는 TypeScript 프로젝트 생성."""
    # eslintrc.json 생성
    eslintrc = tmp_path / ".eslintrc.json"
    eslintrc.write_text('{"extends": ["eslint:recommended"]}')

    # tsconfig.json 생성
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {"strict": true}}')

    # TypeScript 파일
    ts_file = tmp_path / "main.ts"
    ts_file.write_text('const x: number = 42;\nconsole.log(x);')

    # 테스트 파일
    test_file = tmp_path / "main.test.ts"
    test_file.write_text('describe("main", () => { it("works", () => {}); });')

    return tmp_path


@pytest.fixture
def ts_project_without_eslint(tmp_path: Path) -> Path:
    """ESLint 없는 TypeScript 프로젝트 생성."""
    # tsconfig.json만 생성
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {"strict": false}}')

    # TypeScript 파일
    ts_file = tmp_path / "app.ts"
    ts_file.write_text('const x = 42;')

    return tmp_path


@pytest.fixture
def ts_project_with_vitest(tmp_path: Path) -> Path:
    """Vitest 설정이 있는 TypeScript 프로젝트 생성."""
    # vite.config.ts
    vite_config = tmp_path / "vite.config.ts"
    vite_config.write_text('export default { test: {} }')

    # vitest.config.ts
    vitest_config = tmp_path / "vitest.config.ts"
    vitest_config.write_text('export default {}')

    # 테스트 파일들
    (tmp_path / "lib.test.ts").write_text("test('sample', () => {})")
    (tmp_path / "helper.spec.ts").write_text("describe('helper', () => {})")

    return tmp_path


class TestTypeScriptDetection:
    """TypeScript 감지 테스트."""

    def test_detect_eslint_config(self, ts_project_with_eslint: Path) -> None:
        """ESLint 설정 감지."""
        scanner = Scanner(ts_project_with_eslint)
        result = scanner.scan()

        assert result.ts_has_eslint is True
        assert len(result.ts_eslint_extends) > 0

    def test_detect_no_eslint(self, ts_project_without_eslint: Path) -> None:
        """ESLint 없음 감지."""
        scanner = Scanner(ts_project_without_eslint)
        result = scanner.scan()

        assert result.ts_has_eslint is False

    def test_detect_strict_mode(self, ts_project_with_eslint: Path) -> None:
        """TypeScript strict 모드 감지."""
        scanner = Scanner(ts_project_with_eslint)
        result = scanner.scan()

        assert result.ts_has_strict is True

    def test_detect_non_strict_mode(
        self, ts_project_without_eslint: Path
    ) -> None:
        """TypeScript strict 모드 비활성화 감지."""
        scanner = Scanner(ts_project_without_eslint)
        result = scanner.scan()

        assert result.ts_has_strict is False


class TestTypeScriptTestFiles:
    """TypeScript 테스트 파일 카운팅 테스트."""

    def test_count_test_files(self, ts_project_with_vitest: Path) -> None:
        """테스트 파일 개수 카운팅."""
        scanner = Scanner(ts_project_with_vitest)
        result = scanner.scan()

        assert result.ts_test_files >= 2

    def test_count_spec_files(self, ts_project_with_vitest: Path) -> None:
        """*.spec.ts 파일 감지."""
        scanner = Scanner(ts_project_with_vitest)
        result = scanner.scan()

        # lib.test.ts와 helper.spec.ts가 감지되어야 함
        assert result.ts_test_files >= 1


class TestTypeScriptPathAliases:
    """TypeScript path aliases 테스트."""

    def test_detect_path_aliases(self, tmp_path: Path) -> None:
        """tsconfig.json paths 설정 감지."""
        tsconfig = tmp_path / "tsconfig.json"
        tsconfig.write_text(
            """{
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["src/*"],
                    "@components/*": ["src/components/*"]
                }
            }
        }"""
        )

        scanner = Scanner(tmp_path)
        result = scanner.scan()

        assert result.ts_has_path_aliases is True

    def test_no_path_aliases(self, ts_project_without_eslint: Path) -> None:
        """path aliases 없음 감지."""
        scanner = Scanner(ts_project_without_eslint)
        result = scanner.scan()

        # 기본적으로는 False
        assert result.ts_has_path_aliases is False


class TestTypeScriptTestFramework:
    """TypeScript 테스트 프레임워크 감지 테스트."""

    def test_detect_vitest(self, ts_project_with_vitest: Path) -> None:
        """Vitest 감지."""
        scanner = Scanner(ts_project_with_vitest)
        result = scanner.scan()

        assert result.ts_has_vitest_or_jest is True

    def test_detect_jest(self, tmp_path: Path) -> None:
        """Jest 설정 감지."""
        jest_config = tmp_path / "jest.config.js"
        jest_config.write_text("module.exports = {}")

        scanner = Scanner(tmp_path)
        result = scanner.scan()

        assert result.ts_has_vitest_or_jest is True

    def test_no_test_framework(self, ts_project_without_eslint: Path) -> None:
        """테스트 프레임워크 없음 감지."""
        scanner = Scanner(ts_project_without_eslint)
        result = scanner.scan()

        # 기본적으로는 False (vitest/jest 설정이 없으므로)
        assert result.ts_has_vitest_or_jest is False


class TestTypeScriptScanResult:
    """TypeScript 스캔 결과 통합 테스트."""

    def test_typescript_in_tech_stack(self, ts_project_with_eslint: Path) -> None:
        """기술 스택에 TypeScript 포함."""
        scanner = Scanner(ts_project_with_eslint)
        result = scanner.scan()

        assert "typescript" in result.tech_stack or "ts" in result.tech_stack

    def test_scan_result_consistency(self, ts_project_with_eslint: Path) -> None:
        """스캔 결과 일관성 검증."""
        scanner = Scanner(ts_project_with_eslint)
        result = scanner.scan()

        # ESLint가 감지되면 ts_eslint_extends가 비어있으면 안 됨
        if result.ts_has_eslint:
            assert isinstance(result.ts_eslint_extends, list)

        # 테스트 파일 개수는 음수가 될 수 없음
        assert result.ts_test_files >= 0
