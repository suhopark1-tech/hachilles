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

"""HAchilles FastAPI 애플리케이션 팩토리."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from hachilles import __version__


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 라우터를 등록한다."""
    app = FastAPI(
        title="HAchilles API",
        description=(
            "AI 에이전트 하네스 진단 및 최적화 플랫폼 REST API\n\n"
            "## 주요 엔드포인트\n"
            "- `POST /api/v1/scan` — 프로젝트 하네스 진단\n"
            "- `GET /api/v1/history` — 진단 이력 조회\n"
            "- `GET /api/v1/compare` — 팀 단위 점수 비교\n"
            "- `POST /api/v1/generate-agents` — AGENTS.md 템플릿 생성\n"
        ),
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — 개발 환경에서 React (localhost:5173) 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 라우터 등록
    from hachilles.api.routes.agents import router as agents_router
    from hachilles.api.routes.compare import router as compare_router
    from hachilles.api.routes.history import router as history_router
    from hachilles.api.routes.scan import router as scan_router

    api_prefix = "/api/v1"
    app.include_router(scan_router, prefix=api_prefix)
    app.include_router(history_router, prefix=api_prefix)
    app.include_router(compare_router, prefix=api_prefix)
    app.include_router(agents_router, prefix=api_prefix)

    # health check는 static mount 전에 반드시 등록 (라우트 우선순위)
    @app.get("/api/health", tags=["시스템"])
    def health_check() -> dict:
        """서버 상태 확인."""
        return {"status": "ok", "version": __version__}

    # React 빌드 정적 파일 서빙 (빌드 결과물이 있을 경우 — 반드시 마지막에 mount)
    web_dist = Path(__file__).parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(web_dist), html=True),
            name="static",
        )

    return app
