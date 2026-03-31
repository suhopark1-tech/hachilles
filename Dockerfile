# ─────────────────────────────────────────────────────────────────────────────
# HAchilles v3.0.0 — 멀티스테이지 Docker 이미지
#
# Stage 1 (node-builder) : React + TypeScript Vite 빌드
# Stage 2 (py-builder)   : Python 패키지 빌드 (wheel)
# Stage 3 (runtime)      : 최소 런타임 이미지
#
# 빌드:  docker build -t hachilles:3.0.0 .
# 실행:  docker run -p 8000:8000 hachilles:3.0.0
# CLI:   docker run --rm -v /project:/workspace hachilles:3.0.0 hachilles scan /workspace
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: React 빌드 ───────────────────────────────────────────────────────
FROM node:20-alpine AS node-builder

WORKDIR /app/web

# 의존성 캐시 최적화 (package.json 변경 시만 npm ci 재실행)
COPY src/hachilles/web/package*.json ./
RUN npm ci --prefer-offline 2>/dev/null || npm install

# 소스 복사 및 프로덕션 빌드
COPY src/hachilles/web/ ./
RUN npm run build

# ── Stage 2: Python 패키지 빌드 ───────────────────────────────────────────────
FROM python:3.11-slim AS py-builder

WORKDIR /build

# 빌드 도구 설치
RUN pip install --no-cache-dir build==1.2.1

# 소스 전체 복사 (React dist 포함)
COPY pyproject.toml README.md CHANGELOG.md ./
COPY src/ ./src/

# React 빌드 결과물 주입
COPY --from=node-builder /app/web/dist ./src/hachilles/web/dist/

# wheel 빌드
RUN python -m build --wheel --outdir /dist

# ── Stage 3: 런타임 이미지 ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="박성훈 <suhopark1@gmail.com>"
LABEL version="3.0.0"
LABEL description="HAchilles — AI 에이전트 하네스 진단 플랫폼"

# 보안: 비 root 사용자 생성
RUN groupadd -r hachilles && useradd -r -g hachilles hachilles

WORKDIR /app

# 빌드된 wheel 복사 및 설치 (web 의존성 포함)
COPY --from=py-builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/hachilles-*.whl[web] \
    && rm /tmp/hachilles-*.whl

# 비 root로 전환
USER hachilles

# 포트 노출
EXPOSE 8000

# 헬스 체크 (10초 간격, 3초 타임아웃, 3회 재시도)
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
    || exit 1

# 기본 커맨드: 웹 서버 실행
CMD ["hachilles", "serve", "--host", "0.0.0.0", "--port", "8000"]
