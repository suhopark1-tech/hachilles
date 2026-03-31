# revfactory 협업 제안 — Harness × HAchilles 공식 통합

> **발신**: 박성훈 (suhopark1@gmail.com) · HAchilles 개발자 · 「실전 하네스 엔지니어링」 저자
> **수신**: revfactory (github.com/revfactory) · Harness 플러그인 개발자
> **날짜**: 2026-03-29
> **제목**: Harness × HAchilles 공식 통합 협업 제안 — 3가지 구체적 방안

---

## 제안 배경

안녕하세요, revfactory님.

오늘 Harness 플러그인과 harness-100 공개 소식을 접했습니다.
1,808개 파일, 100개 프로덕션 레디 에이전트 팀 — 정말 인상적인 작업입니다.

저는 [HAchilles](https://github.com/suhopark1/hachilles)를 개발했습니다.
AI 에이전트 하네스의 품질을 CE·AC·EM 세 기둥 기준으로 0~100점 정량 측정하는 도구입니다.
오늘 바로 harness-100 전체 100개 팀을 HAchilles로 진단해봤습니다.
(결과: 평균 71.4점 B등급, [전체 벤치마크 포스트](./harness-100-benchmark.md))

두 도구가 다루는 영역이 인접하면서도 완전히 다릅니다.

- **Harness**: 에이전트 팀을 **설계·생성**합니다
- **HAchilles**: 만들어진 팀의 **품질을 측정**합니다

이 관계를 공식화하면 양쪽 사용자 모두에게 명확한 가치가 생긴다고 생각합니다.
아래 3가지 구체적 협업 방안을 제안드립니다.

---

## 협업 방안 1 — 상호 README 링크 교환

### 목적

두 프로젝트의 README에 상대방 도구를 자연스럽게 소개하여, 사용자가
"Harness로 만들고 → HAchilles로 측정한다"는 워크플로우를 처음 접하는 순간부터 인지하게 합니다.

### Harness README에 추가를 요청하는 섹션

아래 내용을 Harness README의 **"다음 단계"** 또는 **"에코시스템"** 섹션에 추가해주시면 감사합니다.

```markdown
## 품질 측정 — HAchilles로 하네스를 진단하세요

Harness로 에이전트 팀을 만들었다면, **HAchilles**로 품질 점수를 확인하세요.
CE(컨텍스트)·AC(아키텍처)·EM(엔트로피) 3개 기둥으로 0~100점 정량 평가합니다.

```bash
pip install hachilles
hachilles scan .
```

harness-100 100개 팀을 진단한 결과, **평균 71.4점(B등급)** —
`claude-progress.txt` + `docs/forbidden.md` 두 파일 추가만으로 **B→A 등급 진입**이 가능합니다.

→ [HAchilles GitHub](https://github.com/suhopark1/hachilles)
→ [harness-100 전체 벤치마크 결과](./harness-100-benchmark.md)

> **"Harness로 만들고, HAchilles로 측정한다."**
```

### HAchilles README의 Harness 링크 (현재 상태)

HAchilles README에는 이미 Harness 링크가 포함되어 있습니다:

```markdown
## Harness 플러그인 사용자라면 — HAchilles가 다음 단계입니다

[revfactory/harness](https://github.com/revfactory)로 에이전트 팀을 생성한 후,
HAchilles로 품질을 측정하는 전체 워크플로우 → [통합 가이드](../docs/harness-integration.md)
```

### 기대 효과

| 항목 | Harness | HAchilles |
|------|---------|-----------|
| 유입 경로 | HAchilles 사용자 중 "에이전트 팀 생성 도구" 필요 그룹 | Harness 사용자 중 "품질 측정" 니즈 그룹 |
| GitHub Star 상관관계 | Harness Star 증가 시 HAchilles에 자동 유입 | HAchilles Star 증가 시 Harness에 자동 유입 |
| 검색 노출 | "harness hachilles" 키워드 양방향 SEO 강화 | |
| 커뮤니티 | 하네스 생태계를 "생성 + 측정" 이중 구조로 포지셔닝 | |

**구현 비용**: 양쪽 각 README에 10~15줄 추가. **즉시 가능**.

---

## 협업 방안 2 — harness-100 공식 벤치마크 연계

### 목적

HAchilles로 harness-100 전체를 진단한 결과를 **양쪽 공식 문서에 연결**하여,
harness-100이 단순한 "예제 모음"이 아니라 "측정 가능한 품질 기준"으로 자리잡게 합니다.

### 제안 내용

**① harness-100 README에 벤치마크 배지 및 링크 추가**

```markdown
## HAchilles 품질 진단 결과

[![HAchilles Score](https://img.shields.io/badge/HAchilles-Avg%2071.4%20B%EA%B8%89-blue)](https://github.com/suhopark1/hachilles)

100개 팀 전체를 HAchilles v3.0.0으로 진단한 결과:

| 등급 | 팀 수 | 비율 |
|------|------|------|
| A등급 (75~89점) | 28개 | 28% |
| B등급 (60~74점) | 51개 | 51% |
| C등급 (40~59점) | 21개 | 21% |

→ [전체 벤치마크 결과 보기](https://github.com/suhopark1/hachilles/blob/main/blog/harness-100-benchmark.md)
→ 내 하네스 점수 확인: `pip install hachilles && hachilles scan .`
```

**② 도메인별 README에 HAchilles 점수 배지 추가**

각 도메인 폴더(예: `software-dev/README.md`)에 도메인 평균 점수 배지 추가:

```markdown
[![HAchilles](https://img.shields.io/badge/HAchilles-82.1점_A등급-green)](https://github.com/suhopark1/hachilles)
```

**③ 갱신 주기 협의**

harness-100이 업데이트되면 HAchilles 진단 결과도 갱신합니다.
권장 갱신 주기: **major release마다 1회** (또는 분기 1회).

자동화 스크립트 제공 가능:

```python
# harness-100 전체 재진단 스크립트 (HAchilles 제공)
# python scripts/benchmark_harness100.py --output results.json

import subprocess, json
from pathlib import Path

def benchmark_all(harness100_path: str, output_path: str = "benchmark-results.json"):
    """harness-100 전체 팀을 HAchilles로 진단하고 결과를 저장합니다."""
    results = []
    root = Path(harness100_path)

    for domain_dir in sorted(root.iterdir()):
        if not domain_dir.is_dir():
            continue
        for team_dir in sorted(domain_dir.iterdir()):
            if not team_dir.is_dir():
                continue
            try:
                out = subprocess.run(
                    ["hachilles", "scan", str(team_dir), "--json"],
                    capture_output=True, text=True, timeout=30
                )
                data = json.loads(out.stdout)
                data["team"] = f"{domain_dir.name}/{team_dir.name}"
                results.append(data)
                print(f"  {data['team']}: {data['total']}점 ({data['grade']})")
            except Exception as e:
                print(f"  {domain_dir.name}/{team_dir.name}: 오류 — {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    scores = [r["total"] for r in results]
    print(f"\n전체 {len(results)}개 팀 완료 | 평균: {sum(scores)/len(scores):.1f}점")
    return results
```

### harness-100의 이점

harness-100이 단순한 코드 모음을 넘어 **측정 가능한 하네스 품질 기준**으로 인식되면:
- "harness-100 A등급 달성"이 개발자 커뮤니티에서 하나의 품질 목표가 됩니다
- harness-100 자체의 개선 방향이 HAchilles 점수로 정량화됩니다
- 외부 기여자가 자신의 PR이 점수에 어떤 영향을 미치는지 즉시 확인 가능합니다

---

## 협업 방안 3 — Harness 패턴 자동 인식 기능 공동 개발

### 목적

HAchilles가 `.claude/agents/` 구조를 분석해 Harness의 6가지 패턴을 **자동 감지**하고,
**패턴별 맞춤 진단 + 처방**을 제공하는 기능을 개발합니다.
이는 두 도구의 통합 가치를 가장 직접적으로 높이는 기술 협업입니다.

### 기능 사양 (HAchilles 구현 예정)

**패턴 감지 알고리즘 (현재 구현 초안)**

```python
# src/hachilles/scanner/harness_pattern_detector.py

from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re


class HarnessPattern(Enum):
    PIPELINE        = "파이프라인"
    FAN_OUT_FAN_IN  = "팬아웃/팬인"
    EXPERT_POOL     = "전문가 풀"
    GENERATE_VALIDATE = "생성-검증"
    SUPERVISOR      = "감독자"
    HIERARCHICAL    = "계층적 위임"
    UNKNOWN         = "알 수 없음"


@dataclass
class PatternDetectionResult:
    pattern: HarnessPattern
    confidence: float          # 0.0 ~ 1.0
    evidence: list[str]        # 감지 근거 목록
    agent_count: int
    key_files: list[str]       # 패턴을 나타내는 주요 파일명
    vulnerability_focus: list[str]  # 이 패턴의 주요 취약 항목 코드


class HarnessPatternDetector:
    """
    .claude/agents/ 구조를 분석하여 Harness 패턴을 자동 감지합니다.
    revfactory/harness-100 기준으로 검증된 휴리스틱을 사용합니다.
    """

    # 패턴별 취약 항목 (HAchilles 항목 코드)
    PATTERN_VULNERABILITIES = {
        HarnessPattern.PIPELINE:        ["CE-03", "AC-05", "CE-05"],
        HarnessPattern.FAN_OUT_FAN_IN:  ["AC-05", "EM-04", "AC-04", "CE-03"],
        HarnessPattern.EXPERT_POOL:     ["CE-01", "CE-05", "CE-02", "AC-04"],
        HarnessPattern.GENERATE_VALIDATE: ["EM-01", "EM-03", "CE-03", "AC-02"],
        HarnessPattern.SUPERVISOR:      ["AC-01", "AC-03", "CE-01", "EM-02"],
        HarnessPattern.HIERARCHICAL:    ["AC-04", "EM-05", "CE-04", "AC-05"],
    }

    def detect(self, project_root: Path) -> PatternDetectionResult:
        agents_dir = project_root / ".claude" / "agents"
        if not agents_dir.exists():
            return PatternDetectionResult(
                pattern=HarnessPattern.UNKNOWN,
                confidence=0.0,
                evidence=["agents/ 디렉토리 없음"],
                agent_count=0,
                key_files=[],
                vulnerability_focus=[]
            )

        agent_files = [f.name for f in agents_dir.glob("*.md")]
        agent_count = len(agent_files)
        evidence = []
        scores = {p: 0.0 for p in HarnessPattern if p != HarnessPattern.UNKNOWN}

        # 규칙 1: orchestrator + worker* → 팬아웃/팬인
        has_orchestrator = any("orchestrator" in f for f in agent_files)
        worker_count = sum(1 for f in agent_files if "worker" in f or "auditor" in f)
        if has_orchestrator and worker_count >= 2:
            scores[HarnessPattern.FAN_OUT_FAN_IN] += 0.8
            evidence.append(f"orchestrator.md + {worker_count}개 worker/auditor 파일 감지")

        # 규칙 2: supervisor.md 존재 → 감독자 패턴
        if any("supervisor" in f for f in agent_files):
            scores[HarnessPattern.SUPERVISOR] += 0.85
            evidence.append("supervisor.md 감지")

        # 규칙 3: 단계 번호 포함 파일명 → 파이프라인
        stage_files = [f for f in agent_files
                       if re.search(r'(step|stage|phase)\d|^\d+[-_]', f)]
        if len(stage_files) >= 2:
            scores[HarnessPattern.PIPELINE] += 0.8
            evidence.append(f"단계 순서 파일 {len(stage_files)}개 감지: {stage_files[:3]}")

        # 규칙 4: generator + validator 쌍 → 생성-검증
        has_generator = any("generat" in f for f in agent_files)
        has_validator = any("validat" in f or "verif" in f for f in agent_files)
        if has_generator and has_validator:
            scores[HarnessPattern.GENERATE_VALIDATE] += 0.9
            evidence.append("generator + validator 쌍 감지")

        # 규칙 5: expert/specialist/domain 다수 → 전문가 풀
        expert_files = [f for f in agent_files
                        if any(k in f for k in ["expert", "specialist", "domain", "advisor"])]
        if len(expert_files) >= 3:
            scores[HarnessPattern.EXPERT_POOL] += 0.75
            evidence.append(f"전문가 파일 {len(expert_files)}개 감지: {expert_files[:3]}")

        # 규칙 6: manager + worker 다층 → 계층적 위임
        has_manager = any("manager" in f or "lead" in f for f in agent_files)
        if has_manager and worker_count >= 2 and not has_orchestrator:
            scores[HarnessPattern.HIERARCHICAL] += 0.7
            evidence.append("manager + worker 계층 구조 감지")

        # 최고 점수 패턴 선택
        best_pattern = max(scores, key=lambda p: scores[p])
        confidence = scores[best_pattern]

        if confidence < 0.3:
            best_pattern = HarnessPattern.UNKNOWN
            confidence = 0.0

        return PatternDetectionResult(
            pattern=best_pattern,
            confidence=confidence,
            evidence=evidence,
            agent_count=agent_count,
            key_files=agent_files,
            vulnerability_focus=self.PATTERN_VULNERABILITIES.get(best_pattern, [])
        )
```

**HAchilles CLI 출력에 패턴 정보 포함 (예정)**

```
╭────────────────────────────────────────────────────────────────╮
│                     HAchilles Score Report                      │
│                                                                  │
│   84점 / 100점         등급: A                                  │
│                                                                  │
│   ◆ Harness 패턴 감지: 팬아웃/팬인 (신뢰도: 92%)               │
│     감지 근거: orchestrator.md + 4개 auditor 파일 확인됨        │
│                                                                  │
│   ⚠ 이 패턴의 주요 취약 항목:                                  │
│     AC-05 (순환 의존성) · EM-04 (GC 에이전트) · AC-04 (금지)   │
│                                                                  │
│   맞춤 처방 →  docs/harness-integration.md#팬아웃팬인          │
╰────────────────────────────────────────────────────────────────╯
```

### revfactory에 요청하는 협업 내용

패턴 자동 감지의 정확도를 높이려면 **공식 패턴 정의 데이터**가 필요합니다.
아래 3가지 중 하나라도 공유해주시면 감사합니다:

**요청 1 — 패턴 메타데이터 파일 (harness-100에 추가)**

각 팀 폴더에 `harness-pattern.json` 추가:

```json
{
  "pattern": "fan-out-fan-in",
  "version": "1.0",
  "orchestrator": "orchestrator.md",
  "workers": ["architect-auditor.md", "security-auditor.md"],
  "fan_in": "orchestrator.md"
}
```

**요청 2 — 패턴 인식 규칙 문서화**

Harness 플러그인이 패턴을 선택하는 기준(파일명 규칙, 구조 조건)을 간단한 문서로 공유.
HAchilles 패턴 감지 알고리즘에 공식 기준으로 반영합니다.

**요청 3 — 정기 공동 검증 (선택사항)**

HAchilles가 harness-100의 패턴을 올바르게 감지하는지
분기 1회 공동 검증. 오탐/누락 케이스를 함께 개선합니다.

### 구현 로드맵

| 단계 | 작업 | 담당 | 예상 완료 |
|------|------|------|---------|
| 1단계 | 패턴 감지 알고리즘 초안 구현 | HAchilles | 2026-04-07 |
| 2단계 | harness-100으로 정확도 검증 | HAchilles | 2026-04-14 |
| 3단계 | 패턴 메타데이터 형식 협의 | 공동 | 협의 후 |
| 4단계 | harness-100에 패턴 메타데이터 추가 | Harness | 협의 후 |
| 5단계 | HAchilles v3.1.0 패턴 인식 공식 출시 | HAchilles | 2026-05 |

---

## 기대 효과 종합

| 항목 | Harness에 대한 가치 | HAchilles에 대한 가치 |
|------|-------------------|---------------------|
| **트래픽** | HAchilles 사용자(품질 관심층) → Harness 자연 유입 | Harness 사용자(에이전트 팀 구성자) → HAchilles 필수 도구화 |
| **완성도** | "만든 팀의 품질 확인" 워크플로우 공식 완성 | "Harness 팀에 특화된 패턴별 진단" 차별화 |
| **커뮤니티** | harness-100이 측정 가능한 품질 기준으로 격상 | HAchilles가 Harness 생태계의 공식 측정 도구로 인정 |
| **검색 노출** | "harness quality", "harness benchmark" 키워드 선점 | "hachilles harness", "harness score" 키워드 강화 |
| **생태계** | 하네스 엔지니어링 = 생성(Harness) + 측정(HAchilles) 표준 정립 | |

---

## 요청 우선순위 및 최소 협업

세 방안 중 가장 부담 없이 시작할 수 있는 것부터 제안합니다:

**🟢 즉시 가능 (1시간 이내)**
- Harness README에 HAchilles 섹션 10~15줄 추가
- harness-100 README에 벤치마크 결과 링크 추가

**🟡 단기 (1~2주)**
- harness-100 폴더별 HAchilles 점수 배지 추가
- 패턴 메타데이터 형식 협의

**🔵 중기 (1~2개월)**
- 패턴 자동 인식 공동 개발
- 공동 통합 가이드 문서 작성

최소한 **README 링크 교환**만으로도 양쪽 사용자에게 즉각적인 가치를 제공할 수 있습니다.

---

## 다음 단계

관심이 있으시다면:

1. **GitHub Issue** — [suhopark1/hachilles](https://github.com/suhopark1/hachilles/issues)에 이슈 오픈
2. **이메일** — suhopark1@gmail.com으로 연락
3. **이 저장소의 PR** — harness README에 직접 PR로 섹션 추가 제안

어떤 형태의 협업이든 환영합니다.
두 프로젝트가 함께 하네스 엔지니어링 생태계의 **생성 + 측정** 표준을 만들어가기를 기대합니다.

감사합니다.
박성훈 드림

---

*HAchilles v3.0.0 · https://github.com/suhopark1/hachilles*
*「실전 하네스 엔지니어링」 저자*
*[harness-100 전체 벤치마크](./harness-100-benchmark.md) · [통합 가이드](../docs/harness-integration.md)*
