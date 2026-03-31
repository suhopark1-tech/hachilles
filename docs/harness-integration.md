# Harness × HAchilles 통합 가이드

> **"Harness로 만들고, HAchilles로 측정한다."**
>
> 이 문서는 [revfactory/harness](https://github.com/revfactory) 플러그인 또는
> [harness-100](https://github.com/revfactory/harness-100)으로 에이전트 팀을 구성한 후,
> HAchilles로 품질을 측정하는 전체 워크플로우를 설명합니다.

---

## 두 도구의 역할 분리

| 구분 | Harness 플러그인 | HAchilles |
|------|-----------------|-----------|
| **핵심 질문** | "어떻게 에이전트 팀을 만들까?" | "만들어진 팀이 얼마나 잘 작동하나?" |
| **입력** | 자연어 요청 ("하네스 구성해줘") | 코드베이스 경로 |
| **출력** | `.claude/agents/*.md`, `.claude/skills/*.md` | CE·AC·EM 0~100점, 5대 실패 패턴 평가 |
| **아키텍처 패턴** | 파이프라인/팬아웃/감독자 등 6종 | 패턴 자동 인식 후 맞춤 진단 |
| **측정 기능** | 없음 | 있음 (본 도구의 존재 이유) |

두 도구는 **파이프라인의 인접 단계**를 담당합니다. 경쟁 관계가 아닙니다.

---

## 통합 4단계 워크플로우

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                    │
│   STEP 1              STEP 2               STEP 3              STEP 4             │
│                                                                                    │
│  [ Harness로 ]  →→  [ HAchilles ]  →→  [ 항목별  ]  →→  [ Harness로  ]          │
│  [ 팀 생성   ]       [ 품질 진단 ]       [ 처방 실행 ]      [ 재구성   ]          │
│                                                                                    │
│   "하네스          hachilles scan .    CE-03 낮으면         파이프라인 패턴 →     │
│    구성해줘"         → 72점 B등급       claude-progress.txt  감독자 패턴으로        │
│                                        생성               변경 재설계              │
│                                                                                    │
│                  ◄────────────────────────────────────────────────────────────   │
│                                반복 (목표 등급 달성까지)                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

### STEP 1 — Harness로 에이전트 팀 생성

Claude Code에서 Harness 플러그인을 활성화한 후 에이전트 팀을 구성합니다.

```bash
# Claude Code 실행 환경 설정 (필요 시)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

**자연어 프롬프트 예시 — 코드 리뷰 팀:**

```
하네스 구성해줘. 코드 리뷰 팀이 필요해.
아키텍처, 보안, 성능, 스타일을 병렬로 감사하고
결과를 하나의 리포트로 통합하는 팀.
```

Harness 플러그인이 선택하는 패턴: **팬아웃/팬인(Fan-out/Fan-in)**

```
.claude/
├── AGENTS.md                  # 팀 전체 메타 컨텍스트 (필수!)
├── agents/
│   ├── orchestrator.md        # 팀 조율자 (팬아웃 제어)
│   ├── architect-auditor.md   # 아키텍처 감사
│   ├── security-auditor.md    # 보안 감사
│   ├── performance-auditor.md # 성능 감사
│   └── style-auditor.md       # 코드 스타일 감사
├── skills/
│   └── code-review.md         # 통합 리뷰 스킬
└── docs/
    ├── architecture.md        # 에이전트 아키텍처 설계 문서
    └── conventions.md         # 코드·커뮤니케이션 규약
```

> **팁**: Harness가 생성한 직후, 아직 아무것도 변경하기 전에 HAchilles 진단을 먼저 실행하세요.
> 베이스라인 점수를 기록해두면 개선 효과를 정량으로 추적할 수 있습니다.

---

### STEP 2 — HAchilles로 품질 점수 확인

```bash
# 설치 (처음 한 번)
pip install hachilles

# 기본 진단
hachilles scan .

# 상세 JSON 출력 (CI/CD 파이프라인 통합용)
hachilles scan . --json | tee harness-quality.json

# HTML 리포트 생성 (브라우저에서 열기)
hachilles scan . --html --out harness-quality.html

# 이력 저장 (트렌드 추적용)
hachilles scan . --save-history
```

**실제 출력 예시 — 코드 리뷰 팀 최초 진단:**

```
╭────────────────────────────────────────────────────────────────╮
│                     HAchilles Score Report                      │
│                                                                  │
│   72점 / 100점         등급: B                                  │
│   "기본 하네스, 일부 개선 필요"                                  │
│                                                                  │
│   CE (컨텍스트)    ████████████████████░░░░   28/40점  (70%)    │
│   AC (아키텍처)    ████████████████████████░   26/35점  (74%)    │
│   EM (엔트로피)    ██████████████████░░░░░░░   18/25점  (72%)    │
│                                                                  │
│   패턴 감지: 팬아웃/팬인 (Fan-out/Fan-in) ✓                     │
│   5대 실패 패턴: 컨텍스트 단절 위험 ⚠                           │
╰────────────────────────────────────────────────────────────────╯

개선 권고 (높은 우선순위부터):
  ⚠  CE-03 [ 8점 ]  세션 브릿지 파일 없음
                    → claude-progress.txt 또는 session-bridge.md 추가 필요
  ⚠  AC-04 [ 6점 ]  docs/forbidden.md 없음
                    → 팬아웃 패턴에서 금지 패턴 명시 필수 (에이전트 간 직접 위임 방지)
  ⚠  EM-04 [ 5점 ]  GC 에이전트 없음
                    → gc_agent.py 추가 또는 CI 스케줄로 컨텍스트 가비지 컬렉션 자동화 필요
  ✓  CE-01 [10점]   AGENTS.md 충실 (156줄 ✓)
  ✓  AC-05 [ 6점]   의존성 방향 위반 0건 ✓
  ✓  EM-01 [ 6점]   AGENTS.md 최신성 양호 (3일 이내 갱신) ✓

통과: 12/15항목    실패: 3/15항목    처방 적용 시 예상 점수: 91점 (S등급)
```

**JSON 출력 구조 (CI/CD 파싱용):**

```json
{
  "total": 72,
  "total_score": 72,
  "grade": "B",
  "grade_label": "기본 하네스, 일부 개선 필요",
  "pillars": {
    "context": {
      "score": 28,
      "full_score": 40,
      "items": ["..."]
    },
    "constraint": {
      "score": 26,
      "full_score": 35,
      "items": ["..."]
    },
    "entropy": {
      "score": 18,
      "full_score": 25,
      "items": ["..."]
    }
  },
  "pattern_risks": [
    { "pattern": "Context Drift", "risk": "medium", "summary": "세션 브릿지 없음", "evidence": ["CE-03 미통과"] },
    { "pattern": "GC Neglect",    "risk": "low",    "summary": "GC 에이전트 없음", "evidence": ["EM-04 미통과"] }
  ],
  "tech_stack": ["python", "markdown"],
  "scan_errors": []
}
```

---

### STEP 3 — 낮은 항목 처방 실행

HAchilles 진단 결과의 **개선 권고** 를 항목별로 처방합니다.
우선순위는 `배점이 높은 항목 → 구현 난이도가 낮은 항목` 순으로 처리합니다.

#### CE-03 처방 — 세션 브릿지 파일 생성 (8점 즉시 획득)

```markdown
<!-- 신규 생성: claude-progress.txt -->

# 코드 리뷰 하네스 — 세션 브릿지

## 현재 하네스 상태
- 버전: v1.0 (2026-03-29 Harness 플러그인으로 생성)
- 패턴: 팬아웃/팬인 (Fan-out/Fan-in)
- 에이전트 구성: orchestrator → [architect, security, performance, style]

## 활성 컨텍스트
- 진단 대상: PR #143 (feat/user-auth-refactor)
- 지난 세션에서 architect-auditor가 순환 의존성 3건 발견
- security-auditor는 JWT 검증 로직 재확인 요청 중

## 에이전트 역할 요약
| 에이전트 | 역할 | 책임 범위 |
|---------|------|---------|
| orchestrator | 리뷰 조율 + 결과 통합 | PR 전체 |
| architect-auditor | 아키텍처·의존성 | src/ 레이어 구조 |
| security-auditor | 보안 취약점 | 인증·인가·입력값 |
| performance-auditor | 성능 이슈 | 쿼리·캐싱·I/O |
| style-auditor | 코드 스타일 | 린터·네이밍·포맷 |

## 출력 형식 (orchestrator 최종 리포트)
```json
{
  "pr": "#143",
  "verdict": "REQUEST_CHANGES | APPROVE",
  "issues": [
    {"severity": "high|medium|low", "agent": "...", "message": "..."}
  ]
}
```

## 금지 사항
- 감사 에이전트 간 직접 통신 금지 (모든 정보는 orchestrator 경유)
- orchestrator 없이 다른 에이전트에게 태스크 위임 금지
```

#### AC-04 처방 — 금지 패턴 문서화 (6점 즉시 획득)

```markdown
<!-- 신규 생성: docs/forbidden.md -->

# 코드 리뷰 하네스 — 금지 패턴 목록

## 에이전트 간 통신 금지 패턴

### [FORBIDDEN-01] 감사 에이전트 간 직접 결과 공유
- **금지**: architect-auditor가 security-auditor의 결과를 직접 참조
- **이유**: 팬아웃 구조에서 독립성 보장 필수 — 편향된 감사 방지
- **허용**: orchestrator가 각 에이전트 결과를 수집 후 통합

### [FORBIDDEN-02] 단일 에이전트의 전체 리뷰 수행
- **금지**: orchestrator가 직접 코드를 감사
- **이유**: orchestrator는 조율자, 감사자가 아님
- **허용**: orchestrator는 태스크 분배 및 결과 통합만 수행

### [FORBIDDEN-03] 감사 완료 전 verdict 선언
- **금지**: 4개 에이전트 중 하나라도 미완료 시 최종 리포트 발행
- **이유**: 불완전한 리뷰는 APPROVE보다 위험
- **허용**: 모든 에이전트 완료 후 통합 리포트 생성

### [FORBIDDEN-04] AGENTS.md 외부에 역할 정의
- **금지**: 개별 에이전트 파일에 다른 에이전트의 역할 재정의
- **이유**: AGENTS.md가 단일 진실의 원천(SSOT)
```

#### EM-04 처방 — GC 에이전트 추가 (5점 획득)

```python
# 신규 생성: gc_agent.py
"""
Garbage Collection Agent — 코드 리뷰 하네스 컨텍스트 정리

역할:
  1. 완료된 PR 리뷰 컨텍스트를 아카이브로 이동
  2. 30일 초과 이력 정리
  3. AGENTS.md 참조 유효성 점검 (EM-03)
  4. docs/ 파일 최신성 점검 (EM-02)
"""
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def gc_run():
    # 1. 오래된 세션 브릿지 아카이브
    progress = Path("claude-progress.txt")
    archive_dir = Path(".claude/archive")
    archive_dir.mkdir(exist_ok=True)

    if progress.exists():
        mtime = datetime.fromtimestamp(progress.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=30):
            archive_path = archive_dir / f"progress-{mtime:%Y%m%d}.txt"
            progress.rename(archive_path)
            print(f"[GC] 세션 브릿지 아카이브 완료: {archive_path}")

    # 2. AGENTS.md 참조 유효성 검사
    agents_md = Path("AGENTS.md")
    if agents_md.exists():
        for line in agents_md.read_text().splitlines():
            if line.startswith("- [") or "](." in line:
                import re
                links = re.findall(r'\]\(([^)]+)\)', line)
                for link in links:
                    if not link.startswith("http") and not Path(link).exists():
                        print(f"[GC] ⚠ 무효 참조 발견: {link}")

    print(f"[GC] 완료: {datetime.now():%Y-%m-%d %H:%M}")

if __name__ == "__main__":
    gc_run()
```

또는 CI 스케줄로 대체 가능:

```yaml
# .github/workflows/hachilles-gc.yml
name: HAchilles GC

on:
  schedule:
    - cron: '0 3 * * 0'  # 매주 일요일 새벽 3시
  workflow_dispatch:

jobs:
  gc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run GC Agent
        run: python gc_agent.py
      - name: Re-scan after GC
        run: |
          pip install hachilles
          hachilles scan . --json > post-gc-result.json
          echo "Post-GC Score: $(jq '.total' post-gc-result.json)"
```

---

### STEP 4 — 재스캔 및 목표 등급 달성 확인

```bash
# 처방 적용 후 재진단
hachilles scan .

# 이전 점수와 비교
hachilles history .

# 트렌드 확인 (ASCII 차트)
hachilles history . --chart
```

**재진단 출력 예시 (처방 3개 적용 후):**

```
╭────────────────────────────────────────────────────────────────╮
│                     HAchilles Score Report                      │
│                                                                  │
│   91점 / 100점         등급: S  ★                              │
│   "모범적인 하네스 — 표준 채택 권장"                            │
│                                                                  │
│   CE (컨텍스트)    ████████████████████████████████   36/40점  │
│   AC (아키텍처)    ████████████████████████████████   32/35점  │
│   EM (엔트로피)    ████████████████████████████████   23/25점  │
│                                                                  │
│   이전 점수: 72점 (B)  →  현재: 91점 (S)  (+19점, +1등급↑↑)  │
╰────────────────────────────────────────────────────────────────╯
```

**이력 트렌드 차트:**

```
점수
100 │
 90 │                              ●  (S등급)
 80 │
 70 │   ●  (B등급 시작)
 60 │
    └──────────────────────────────────
      2026-03-29               2026-04-05
```

**목표 등급 달성 기준:**

| 목표 등급 | 최소 점수 | 핵심 통과 항목 | 예상 소요 시간 |
|-----------|----------|---------------|--------------|
| **S (모범)**  | 90점 | CE·AC·EM 15개 중 13개 이상 | 1~2일 |
| **A (견고)**  | 75점 | CE·AC 전 항목 + EM 3/5 이상 | 반나절 |
| **B (기본)**  | 60점 | CE·AC 주요 항목 (CE-01·CE-02·AC-01·AC-03) | 2~3시간 |
| **C (주의)**  | 40점 | CE-01 통과 + α | 즉시 측정만 해도 달성 |

> STEP 2→3→4를 **B→A→S** 순으로 목표를 높여가며 반복하는 것을 권장합니다.
> 한 번에 S등급을 목표로 하면 개선 항목이 많아 방향을 잃을 수 있습니다.

---

## Harness 6가지 패턴별 취약점 상세

Harness 플러그인의 6가지 아키텍처 패턴은 구조적으로 서로 다른 취약점을 내포합니다.
HAchilles는 `.claude/agents/` 파일 수·참조 구조를 분석하여 패턴을 자동 감지하고,
패턴별 맞춤 진단 가중치를 적용합니다.

---

### 패턴 1: 파이프라인 (Pipeline)

**구조**: A → B → C → D (순차적 단계 처리)

**예시**: 데이터 수집 → 정제 → 분석 → 리포트 생성

```
.claude/agents/
├── AGENTS.md
├── collector.md    # 1단계: 원본 데이터 수집
├── cleaner.md      # 2단계: 데이터 정제
├── analyzer.md     # 3단계: 분석 수행
└── reporter.md     # 4단계: 결과 리포트
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **CE-03** (세션 브릿지) | 단계 간 컨텍스트 단절 | collector가 수집한 메타데이터를 cleaner가 알 수 없음. 다음 에이전트가 이전 단계 상태를 모른 채 시작 |
| **AC-05** (의존성 위반) | 역방향 참조 | analyzer가 collector를 직접 호출하려 시도 (파이프라인 역방향 위반) |
| **CE-05** (아키텍처 문서) | 파이프라인 흐름 미문서화 | 각 단계의 입출력 계약(input/output contract)이 docs/architecture.md에 없음 |

**처방 포인트:**
- `claude-progress.txt`에 "현재 파이프라인 단계: 2단계(cleaner) 진행 중, 입력: s3://bucket/raw/*.csv" 형식으로 단계 상태 기록
- `docs/architecture.md`에 각 에이전트의 Input Type / Output Type 명시
- `docs/forbidden.md`에 "역방향 호출 금지 (analyzer → collector 금지)" 추가

---

### 패턴 2: 팬아웃/팬인 (Fan-out / Fan-in)

**구조**: orchestrator → [A, B, C, D] → orchestrator (병렬 처리 후 통합)

**예시**: 코드 리뷰, 멀티 플랫폼 콘텐츠 생성, 다중 소스 조사

```
.claude/agents/
├── AGENTS.md
├── orchestrator.md      # 분배 + 통합
├── worker-a.md          # 병렬 작업자 A
├── worker-b.md          # 병렬 작업자 B
├── worker-c.md          # 병렬 작업자 C
└── worker-d.md          # 병렬 작업자 D
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **AC-05** (의존성 위반) | 순환 의존성 | worker-a와 worker-b가 서로의 결과를 참조하려 시도 → 교착 상태 위험 |
| **EM-04** (GC 에이전트) | 병렬 컨텍스트 누적 | 각 worker의 중간 컨텍스트가 축적되어 토큰 한도 초과 위험 |
| **AC-04** (금지 패턴) | 에이전트 간 직접 통신 | worker-b가 worker-c에게 직접 재확인 요청 (orchestrator 바이패스) |
| **CE-03** (세션 브릿지) | 병렬 상태 비동기화 | orchestrator가 어느 worker가 어디까지 완료했는지 세션 간 추적 불가 |

**처방 포인트:**
- `docs/forbidden.md`에 "worker 간 직접 통신 절대 금지" 최상위 항목으로 명시
- `gc_agent.py`에서 각 worker의 완료된 중간 컨텍스트 주기적 정리
- `claude-progress.txt`에 worker 완료 상태 체크리스트 유지

---

### 패턴 3: 전문가 풀 (Expert Pool)

**구조**: 요청이 들어오면 적합한 전문가 에이전트를 동적으로 선택

**예시**: 질의응답 시스템, 도메인별 상담 봇

```
.claude/agents/
├── AGENTS.md
├── router.md            # 요청 분류 및 전문가 선택
├── domain-expert-a.md   # 도메인 A 전문가
├── domain-expert-b.md   # 도메인 B 전문가
├── domain-expert-c.md   # 도메인 C 전문가
└── generalist.md        # 복합 도메인 대응
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **CE-01** (AGENTS.md 분량) | 전문가 역할 미정의 | AGENTS.md가 50줄 미만 — 전문가 풀의 선택 기준, 각 전문가 도메인 경계가 명시되지 않아 router가 잘못 분류 |
| **CE-05** (아키텍처 문서) | 전문가 경계 문서화 미비 | 어느 도메인이 어느 전문가 담당인지 docs/architecture.md에 없음 → 도메인 중복·누락 발생 |
| **CE-02** (docs/ 구조) | 전문가별 지식 문서 부재 | 전문가 에이전트가 참조할 도메인 지식 문서가 docs/에 없음 |
| **AC-04** (금지 패턴) | 전문가 오버스텝 | domain-expert-a가 자신의 도메인 밖 질문에 답변 시도 |

**처방 포인트:**
- AGENTS.md에 각 전문가의 "담당 도메인 키워드 목록" 50줄 이상으로 명시
- `docs/routing-criteria.md` (또는 architecture.md 내) 라우팅 결정 트리 문서화
- `docs/forbidden.md`에 "전문가는 자신의 도메인 외 질문에 답하지 않는다" 명시

---

### 패턴 4: 생성-검증 (Generate-Validate)

**구조**: Generator → Validator → (실패 시) Generator 재시도

**예시**: 코드 생성 + 테스트, 콘텐츠 초안 + 팩트체크, SQL 생성 + 실행 검증

```
.claude/agents/
├── AGENTS.md
├── generator.md    # 결과물 초안 생성
├── validator.md    # 품질·정합성 검증
└── refiner.md      # 검증 실패 시 정제 (선택)
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **EM-01** (AGENTS.md 최신성) | 검증 기준 드리프트 | Generator가 업데이트되었는데 AGENTS.md의 "생성 형식" 정의가 구버전 — Validator가 새 형식을 모르고 계속 실패 처리 |
| **EM-03** (참조 유효성) | 검증 스키마 파일 무효화 | `validator.md`가 참조하는 `docs/output-schema.json`이 삭제되거나 이동됨 |
| **CE-03** (세션 브릿지) | 재시도 횟수 소실 | 세션 재시작 시 "현재 3번째 재시도 중"이라는 컨텍스트가 소실되어 무한 루프 위험 |
| **AC-02** (pre-commit) | 검증 결과 코드 미검사 | Generator가 만든 코드가 lint 검사 없이 커밋됨 |

**처방 포인트:**
- AGENTS.md에 "현재 생성 형식 버전 v2.1" 명시, 변경 시 즉시 갱신 (EM-01)
- `claude-progress.txt`에 "재시도 횟수: 2/3, 실패 원인: 타입 오류" 기록 (CE-03)
- `docs/output-schema.json` 참조 파일 존재 여부 주기적 확인 (EM-03)

---

### 패턴 5: 감독자 (Supervisor)

**구조**: Supervisor가 여러 Worker를 감시·지시·중단

**예시**: 장기 작업 모니터링, 복잡한 멀티스텝 태스크 실행

```
.claude/agents/
├── AGENTS.md
├── supervisor.md    # 전체 감독 및 의사결정
├── worker-1.md      # 실행 에이전트 1
├── worker-2.md      # 실행 에이전트 2
└── monitor.md       # 상태 모니터링 (선택)
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **AC-01** (린터 설정) | Worker 코드 품질 무관리 | Supervisor가 수행 결과를 판단하는 기준이 없어 저품질 결과물도 통과 |
| **AC-03** (CI Gate) | 감독 결과 검증 없음 | Supervisor의 최종 승인이 CI 검증 없이 바로 배포로 연결 |
| **CE-01** (AGENTS.md 분량) | 감독 권한 범위 미정의 | Supervisor가 어디까지 결정할 수 있는지 AGENTS.md에 미명시 → 과잉 개입 또는 방치 |
| **EM-02** (docs/ 최신성) | 감독 기준 노후화 | Supervisor가 참고하는 기준 문서가 30일 이상 갱신되지 않아 구버전 기준으로 판단 |

**처방 포인트:**
- AGENTS.md에 "Supervisor 개입 조건 (예: 에러율 > 20%, 재시도 3회 초과)" 명시
- CI 파이프라인에 `hachilles scan . --json` 품질 게이트 추가 (AC-03)
- `docs/supervision-criteria.md`에 판단 기준 문서화 후 30일마다 갱신 (EM-02)

---

### 패턴 6: 계층적 위임 (Hierarchical Delegation)

**구조**: Top → Mid → Bottom 3단계 이상의 위임 구조

**예시**: 전사 → 팀 → 개인 태스크 분해, 복잡한 프로젝트 관리

```
.claude/agents/
├── AGENTS.md
├── ceo-agent.md        # 최상위: 전략 결정
├── manager-a.md        # 중간: 팀 A 관리
├── manager-b.md        # 중간: 팀 B 관리
├── worker-a1.md        # 실행: 팀 A 작업 1
├── worker-a2.md        # 실행: 팀 A 작업 2
└── worker-b1.md        # 실행: 팀 B 작업 1
```

**HAchilles 주요 취약 항목:**

| 항목 | 취약 유형 | 구체적 증상 |
|------|---------|-----------|
| **AC-04** (금지 패턴) | 계층 월권 | ceo-agent가 worker에게 직접 지시 (manager 바이패스) → 중간 관리자 무력화 |
| **EM-05** (bare suppress) | 기술 부채 누적 | 계층이 깊을수록 각 레이어에서 린트 suppress가 누적됨, [EXCEPTION] 주석 없이 suppressed |
| **CE-04** (feature_list.json) | 기능 범위 불명확 | 계층별 위임 범위가 feature_list.json으로 명시되지 않아 중복 작업·충돌 발생 |
| **AC-05** (의존성 위반) | 계층 역전 | worker-a1이 manager-b에게 직접 보고 시도 (같은 레이어 간 의존성 추가) |

**처방 포인트:**
- `docs/forbidden.md` 최우선 항목: "계층 월권 금지 — ceo는 manager를 통해서만 worker와 소통"
- `feature_list.json`에 각 에이전트의 권한 범위 명시 (`"scope": "team-a"`, `"escalate_to": "manager-a"`)
- lint suppress 사용 시 반드시 `# [EXCEPTION] 이유: ...` 주석 추가 (EM-05)

---

## CI/CD 통합 코드 예시

### GitHub Actions — PR 품질 게이트

```yaml
# .github/workflows/hachilles-quality.yml
name: Harness Quality Gate

on:
  pull_request:
    branches: [main, develop]
    paths:
      - '.claude/**'
      - 'AGENTS.md'
      - 'docs/**'
      - 'pyproject.toml'

jobs:
  hachilles-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install HAchilles
        run: pip install hachilles

      - name: Run HAchilles Scan
        id: scan
        run: |
          hachilles scan . --json > hachilles-result.json
          echo "score=$(jq -r '.total' hachilles-result.json)" >> $GITHUB_OUTPUT
          echo "grade=$(jq -r '.grade' hachilles-result.json)" >> $GITHUB_OUTPUT
          echo "ce=$(jq -r '.pillars.context.score' hachilles-result.json)" >> $GITHUB_OUTPUT
          echo "ac=$(jq -r '.pillars.constraint.score' hachilles-result.json)" >> $GITHUB_OUTPUT
          echo "em=$(jq -r '.pillars.entropy.score' hachilles-result.json)" >> $GITHUB_OUTPUT

      - name: Comment PR with Results
        uses: actions/github-script@v7
        with:
          script: |
            const score = '${{ steps.scan.outputs.score }}';
            const grade = '${{ steps.scan.outputs.grade }}';
            const ce = '${{ steps.scan.outputs.ce }}';
            const ac = '${{ steps.scan.outputs.ac }}';
            const em = '${{ steps.scan.outputs.em }}';
            const gradeEmoji = {S:'🏆',A:'✅',B:'🔵',C:'⚠️',D:'❌'}[grade] || '❓';

            const body = [
              `## HAchilles Harness Quality Report ${gradeEmoji}`,
              ``,
              `| 지표 | 점수 | 만점 |`,
              `|------|------|------|`,
              `| **총점** | **${score}점** | 100점 |`,
              `| CE (컨텍스트) | ${ce}점 | 40점 |`,
              `| AC (아키텍처) | ${ac}점 | 35점 |`,
              `| EM (엔트로피) | ${em}점 | 25점 |`,
              ``,
              `등급: **${grade}등급** ${gradeEmoji}`,
              ``,
              `> 상세 결과: \`cat hachilles-result.json\` 또는 \`hachilles scan . --html\``,
            ].join('\n');

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body
            });

      - name: Quality Gate Check
        run: |
          SCORE="${{ steps.scan.outputs.score }}"
          GRADE="${{ steps.scan.outputs.grade }}"
          MIN_SCORE=75

          echo "HAchilles Score: ${SCORE}점 (${GRADE}등급)"
          echo "최소 기준: ${MIN_SCORE}점 (A등급)"

          if [ "$SCORE" -lt "$MIN_SCORE" ]; then
            echo "❌ 하네스 품질 기준 미달 — ${MIN_SCORE}점 이상 필요"
            echo ""
            echo "개선 방법:"
            jq -r '.pillars | to_entries[] | select(.value.score < .value.full_score) |
              "  ⚠ \(.key): \(.value.score)/\(.value.full_score)점 — 처방 항목 확인 필요"' \
              hachilles-result.json
            exit 1
          fi

          echo "✅ 품질 게이트 통과 (${SCORE}점 ≥ ${MIN_SCORE}점)"
```

---

### GitHub Actions — 공식 Action 사용 (예정)

```yaml
# 간결한 버전 — hachilles-action@v1 출시 후 사용 가능
- name: HAchilles Quality Gate
  uses: suhopark1/hachilles-action@v1
  with:
    min-score: 75           # A등급 이상 요구
    fail-on-grade: C        # C등급 이하 시 PR 차단
    comment-pr: true        # PR에 자동 코멘트
    save-history: true      # 점수 이력 저장
```

---

### GitLab CI — 동일한 품질 게이트

```yaml
# .gitlab-ci.yml
hachilles-quality:
  stage: test
  image: python:3.11
  only:
    - merge_requests
    - main

  script:
    - pip install hachilles
    - hachilles scan . --json > hachilles-result.json

    - |
      SCORE=$(python3 -c "import json; d=json.load(open('hachilles-result.json')); print(d['total'])")
      GRADE=$(python3 -c "import json; d=json.load(open('hachilles-result.json')); print(d['grade'])")
      echo "HAchilles Score: ${SCORE}점 (${GRADE}등급)"

      if [ "$SCORE" -lt 75 ]; then
        echo "❌ 품질 게이트 미달 (75점 이상 필요)"
        python3 -c "
      import json
      d = json.load(open('hachilles-result.json'))
      for pillar, data in d['pillars'].items():
          if data['score'] < data['full_score']:
              print(f'  ⚠ {pillar}: {data[\"score\"]}/{data[\"full_score\"]}점')
        "
        exit 1
      fi
      echo "✅ 품질 게이트 통과"

  artifacts:
    paths:
      - hachilles-result.json
    expire_in: 30 days
    reports:
      dotenv: hachilles-result.json
```

---

### Pre-commit Hook — 커밋 전 로컬 검사

```yaml
# .pre-commit-config.yaml 에 추가
repos:
  - repo: local
    hooks:
      - id: hachilles-check
        name: HAchilles Harness Quality Check
        entry: bash -c '
          hachilles scan . --json > /tmp/hachilles-pre-commit.json 2>/dev/null &&
          SCORE=$(jq .total /tmp/hachilles-pre-commit.json) &&
          GRADE=$(jq -r .grade /tmp/hachilles-pre-commit.json) &&
          echo "HAchilles: ${SCORE}점 (${GRADE}등급)" &&
          [ "$SCORE" -ge 60 ] || (echo "❌ 60점 미만 — 커밋 차단" && exit 1)
        '
        language: system
        pass_filenames: false
        files: '^(AGENTS\.md|\.claude/|docs/).*'
        stages: [commit]
```

---

### Python 스크립트 — 배포 파이프라인 통합

```python
# scripts/hachilles_gate.py
"""HAchilles 품질 게이트 — 배포 파이프라인 통합 스크립트"""

import json
import subprocess
import sys
from pathlib import Path


def run_hachilles_gate(
    project_path: str = ".",
    min_score: int = 75,
    fail_on_grade: str = "C",
) -> dict:
    """
    HAchilles 품질 게이트를 실행하고 결과를 반환합니다.

    Args:
        project_path: 진단할 프로젝트 경로
        min_score: 최소 통과 점수 (기본: 75점, A등급)
        fail_on_grade: 이 등급 이하 시 실패 처리 (기본: C등급)

    Returns:
        {"passed": bool, "score": int, "grade": str, "details": dict}
    """
    result = subprocess.run(
        ["hachilles", "scan", project_path, "--json"],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)

    score = data["total"]
    grade = data["grade"]
    grade_order = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

    passed = (
        score >= min_score
        and grade_order.get(grade, 0) > grade_order.get(fail_on_grade, 0)
    )

    print(f"HAchilles Score: {score}점 ({grade}등급) — {'✅ PASS' if passed else '❌ FAIL'}")

    if not passed:
        print("\n개선 필요 항목:")
        for pillar, pillar_data in data["pillars"].items():
            gap = pillar_data["full_score"] - pillar_data["score"]
            if gap > 0:
                print(f"  {pillar}: {pillar_data['score']}/{pillar_data['full_score']}점 ({gap}점 부족)")

    return {"passed": passed, "score": score, "grade": grade, "details": data}


if __name__ == "__main__":
    result = run_hachilles_gate(min_score=75)
    sys.exit(0 if result["passed"] else 1)
```

---

## 자주 묻는 질문

**Q: Harness 없이 HAchilles만 써도 되나요?**
네. HAchilles는 Harness 플러그인 없이도 모든 AI 에이전트 코드베이스를 진단합니다.
Harness로 생성된 팀에 특화된 패턴 감지 기능은 추가적인 가치를 제공하지만, 필수 요건은 아닙니다.

**Q: harness-100의 팀을 HAchilles로 진단할 수 있나요?**
네. `git clone https://github.com/revfactory/harness-100 && hachilles scan harness-100/`
으로 즉시 진단 가능합니다. 100개 팀 전체 벤치마크 결과는 [블로그 포스트](../blog/harness-100-benchmark.md)를 참조하세요.

**Q: Harness가 생성한 팀에서 HAchilles가 낮은 점수를 주는 경우가 있나요?**
Harness 플러그인은 에이전트 파일 구조를 잘 생성하지만, CE-03(세션 브릿지)·AC-04(금지 패턴)·EM-04(GC 에이전트)는 자동 생성하지 않습니다. 이 세 항목(합계 19점)이 초기 점수를 낮추는 주요 원인입니다. STEP 3 처방을 따르면 빠르게 개선할 수 있습니다.

**Q: CI/CD 게이트에서 최소 기준을 얼마로 설정해야 하나요?**
팀의 성숙도에 따라 단계적으로 높여가는 방식을 권장합니다.
- 초기 도입: 60점 (B등급) — 너무 엄격하면 개발자 저항
- 안정화 후: 75점 (A등급) — 대부분의 팀이 달성 가능
- 고품질 목표: 90점 (S등급) — 표준 채택 프로젝트 기준

**Q: 패턴 자동 감지는 어떻게 작동하나요?**
HAchilles가 `.claude/agents/` 아래의 파일명과 파일 내 참조 관계를 분석합니다.
- `orchestrator.md` 존재 + 다수의 `worker*.md` → 팬아웃/팬인 패턴
- `supervisor.md` 존재 → 감독자 패턴
- 파일명에 단계 번호 포함 (`step1`, `stage2` 등) → 파이프라인 패턴
- `generator.md` + `validator.md` 쌍 존재 → 생성-검증 패턴

---

*이 문서는 HAchilles v3.0.0 기준으로 작성되었습니다.*
*최신 정보는 [CHANGELOG.md](../CHANGELOG.md)를 참조하세요.*
*HAchilles Standards: [STANDARDS.md](../STANDARDS.md)*
