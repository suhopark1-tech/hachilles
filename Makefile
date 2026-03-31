# HAchilles v3.0.0 — 개발 편의 Makefile
# 사용법: make <target>

.PHONY: help install dev web-install web-build lint test test-phase3 \
        serve clean build check

# ── 기본 ──────────────────────────────────────────────────────────────────
help:
	@echo "HAchilles v3.0.0 개발 커맨드"
	@echo ""
	@echo "  make install      - 기본 패키지 설치 (pip install -e .)"
	@echo "  make dev          - 개발 의존성 포함 설치 (dev + web)"
	@echo "  make web-install  - React 의존성 설치 (npm install)"
	@echo "  make web-build    - React 프로덕션 빌드"
	@echo "  make lint         - ruff 린트 실행"
	@echo "  make test         - 전체 테스트 실행"
	@echo "  make test-phase3  - Phase 3 테스트만 실행"
	@echo "  make serve        - 웹 서버 실행 (http://localhost:8000)"
	@echo "  make build        - PyPI 패키지 빌드 (웹 포함)"
	@echo "  make clean        - 빌드 아티팩트 정리"

# ── 설치 ──────────────────────────────────────────────────────────────────
install:
	pip install -e .

dev:
	pip install -e ".[dev,web]"

web-install:
	cd src/hachilles/web && npm install

web-build: web-install
	cd src/hachilles/web && npm run build
	@echo "React 빌드 완료: src/hachilles/web/dist/"

# ── 린트 ──────────────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

lint-fix:
	ruff check src/ tests/ --fix
	ruff format src/ tests/

# ── 테스트 ────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-phase3:
	pytest tests/test_phase3_api.py tests/test_phase3_plugins.py \
	       tests/test_phase3_typescript.py -v --tb=short

test-unit:
	pytest tests/score/ tests/test_scanner.py tests/test_scanner_v2.py \
	       tests/test_phase2_ast.py tests/test_phase2_llm.py -v --tb=short

# ── 서버 ──────────────────────────────────────────────────────────────────
serve:
	hachilles serve --port 8000

serve-dev:
	@echo "백엔드: http://localhost:8000"
	@echo "프론트엔드 개발서버: http://localhost:5173"
	hachilles serve &
	cd src/hachilles/web && npm run dev

# ── 빌드 & 배포 ───────────────────────────────────────────────────────────
build: web-build
	pip install build
	python -m build
	@echo "패키지 빌드 완료: dist/"

check:
	pip install twine
	twine check dist/*

# ── 정리 ──────────────────────────────────────────────────────────────────
clean:
	rm -rf dist/ build/ *.egg-info
	rm -rf src/hachilles/web/dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "정리 완료"
