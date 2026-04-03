# 2. 핵심 진단 엔진 상세 명세 (Core Diagnostic Engine)

- **위치:** `hachilles/src/hachilles/`
- **개요:** 3대 기둥(3-Pillar Framework)을 기반으로 에이전트 품질을 정량적으로 진단하는 파이썬 코어 엔진.
- **분석 기둥(3 Pillars):**
    1. **CE (Context Engineering):** 시스템 프롬프트 품질, 컨텍스트 윈도우 관리 (40 pts)
    2. **AC (Architectural Constraints):** 도구 접근 제어, 루프 방지, 출력 검증 레이어 (35 pts)
    3. **EM (Entropy Management):** 의존성 제어, 에러 전파 격리, 관측 가능성 (25 pts)
- **핵심 로직:**
    - `Auditors`: 각 진단 항목별(15개) 스캔 수행.
    - `ScoreEngine`: 0~100점 합산 및 등급(S~D) 판정.
- **작성일:** 2026-04-02
- **작성자:** 박해달
