# 3. API 및 CLI 명세 (API & CLI)

- **개요:** 사용자 및 CI/CD 파이프라인 연동을 위한 인터페이스 명세.
- **CLI (Command Line Interface):**
    - `hachilles scan .`: Rich 출력(터미널)을 통한 품질 스캔.
    - `hachilles scan . --html --out report.html`: 독립 실행형 HTML 리포트 생성.
    - `hachilles scan . --json`: CI 파이프라인 연동을 위한 JSON 출력.
- **API (REST API):**
    - 프레임워크: FastAPI
    - 주요 엔드포인트:
        - `GET /api/health`: 시스템 상태 점검.
        - `POST /api/v1/scan`: 프로젝트 분석 스캔 실행.
        - `GET /api/v1/history`: SQLite 기반 분석 히스토리 조회.
- **작성일:** 2026-04-02
- **작성자:** 박해달
