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

"""HAchilles 핵심 데이터 모델.

레이어 규칙: models는 다른 hachilles 모듈을 import하지 않는다.
모든 Auditor, Scanner, Score 엔진은 이 모델을 공통 데이터 계약으로 사용한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ── 열거형 ─────────────────────────────────────────────────────

class Pillar(str, Enum):
    """하네스 3대 기둥."""
    CONTEXT    = "context"      # 컨텍스트 엔지니어링
    CONSTRAINT = "constraint"   # 아키텍처 제약 설계
    ENTROPY    = "entropy"      # 엔트로피 관리


class RiskLevel(str, Enum):
    """5대 실패 패턴의 위험도."""
    CRITICAL = "critical"   # 즉시 대응 필요
    HIGH     = "high"       # 1주 내 대응
    MEDIUM   = "medium"     # 1개월 내 대응
    LOW      = "low"        # 장기적 개선
    OK       = "ok"         # 문제 없음


# ── 진단 항목 결과 ──────────────────────────────────────────────

@dataclass
class AuditItem:
    """단일 진단 항목(예: CE-01)의 결과.

    항목 코드 명명 규칙:
      CE-01~05: Context Engineering
      AC-01~05: Architecture Constraint
      EM-01~05: Entropy Management
    """
    code: str           # 예: "CE-01"
    pillar: Pillar
    name: str           # 예: "AGENTS.md 존재 여부"
    passed: bool        # True = 통과, False = 실패
    score: int          # 이 항목이 기여하는 점수 (0 또는 full_score)
    full_score: int     # 이 항목의 만점
    detail: str = ""    # 측정 결과 설명 (예: "AGENTS.md 없음", "1,240줄 — 분리 권장")
    prescription: str = ""  # 맥락 특화 처방 (처방 엔진이 채운다)


@dataclass
class AuditResult:
    """기둥 하나의 전체 진단 결과."""
    pillar: Pillar
    items: list[AuditItem] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(item.score for item in self.items)

    @property
    def full_score(self) -> int:
        return sum(item.full_score for item in self.items)

    @property
    def passed_count(self) -> int:
        return sum(1 for item in self.items if item.passed)

    @property
    def failed_items(self) -> list[AuditItem]:
        return [item for item in self.items if not item.passed]


@dataclass
class PatternRisk:
    """5대 실패 패턴 위험도 평가 결과."""
    pattern: str        # 예: "Context Drift"
    risk: RiskLevel
    evidence: list[str] = field(default_factory=list)  # 위험 근거 목록
    summary: str = ""


# ── 스캐너 원시 데이터 ──────────────────────────────────────────

@dataclass
class ScanResult:
    """Scanner가 수집한 대상 프로젝트의 원시 데이터.

    이 객체가 모든 Auditor의 유일한 입력이다.
    Auditor는 대상 프로젝트 파일에 직접 접근하지 않는다.
    """
    target_path: Path

    # ── 컨텍스트 관련 ───────────────────────────────────────────
    has_agents_md: bool = False
    agents_md_path: Path | None = None
    agents_md_lines: int = 0
    has_docs_dir: bool = False
    docs_files: list[Path] = field(default_factory=list)
    has_session_bridge: bool = False   # claude-progress.txt 또는 유사 파일
    session_bridge_path: Path | None = None
    has_feature_list: bool = False     # feature_list.json 또는 유사 파일
    has_architecture_md: bool = False
    has_conventions_md: bool = False
    has_adr_dir: bool = False          # docs/decisions/ 또는 adr/

    # ── 제약 관련 ────────────────────────────────────────────────
    has_linter_config: bool = False
    linter_config_path: Path | None = None
    has_pre_commit: bool = False
    has_ci_gate: bool = False          # .github/workflows/ 에 lint/test job 존재
    dependency_violations: int = 0    # 실제 측정된 의존성 방향 위반 건수
    has_forbidden_patterns: bool = False  # docs/forbidden.md 또는 규칙 내 금지 목록

    # ── 엔트로피 관련 ────────────────────────────────────────────
    agents_md_staleness_days: int | None = None   # None = git 히스토리 없음
    docs_avg_staleness_days: float | None = None
    invalid_agents_refs: list[str] = field(default_factory=list)  # 코드에 없는 참조
    has_gc_agent: bool = False         # GC 에이전트 스크립트 존재 여부
    bare_lint_suppression_ratio: float = 0.0   # 이유 없는 lint-disable 비율

    # ── 메타 ─────────────────────────────────────────────────────
    tech_stack: list[str] = field(default_factory=list)  # ["python", "typescript"] 등
    scan_errors: list[str] = field(default_factory=list) # 스캔 중 발생한 비치명적 오류

    # ── Phase 2: AST 의존성 분석 ─────────────────────────────────
    import_graph: dict[str, list[str]] = field(default_factory=dict)
    # 모듈명 → import하는 모듈명 목록 (AST 분석 결과)
    dependency_cycles: list[list[str]] = field(default_factory=list)
    # 탐지된 순환 의존성 사이클 목록
    layer_violations: list[tuple[str, str]] = field(default_factory=list)
    # (위반자, 피위반자) 튜플 목록 — 하위 레이어가 상위 레이어를 참조한 경우

    # ── Phase 2: Go/Java 스택 ────────────────────────────────────────
    go_module_name: str = ""           # go.mod의 module 이름
    go_has_linter: bool = False        # golangci-lint 또는 go vet CI 설정
    go_has_tests: bool = False         # *_test.go 파일 존재 여부
    java_build_tool: str = ""         # "maven" | "gradle" | ""
    java_has_linter: bool = False      # checkstyle/spotbugs 설정
    java_has_tests: bool = False       # src/test/ 디렉토리 존재 여부

    # ── Phase 2: LLM 분석 결과 ───────────────────────────────────────
    llm_over_engineering_score: float = 0.0  # 0.0~1.0 (0=없음, 1=매우 심함)
    llm_over_engineering_evidence: list[str] = field(default_factory=list)
    llm_analysis_cached: bool = False  # 캐시에서 가져온 결과인지 여부

    # ── Phase 2: 시계열 추적 ────────────────────────────────────────
    scan_timestamp: str = ""  # ISO 8601 형식 스캔 시각

    # ── Phase 3: TypeScript 심층 분석 ────────────────────────────────
    ts_has_eslint: bool = False          # .eslintrc.* 또는 eslint.config.* 존재
    ts_eslint_extends: list[str] = field(default_factory=list)  # ESLint extends 목록
    ts_has_strict: bool = False          # tsconfig.json "strict": true 여부
    ts_has_path_aliases: bool = False    # tsconfig.json paths 설정 여부
    ts_test_files: int = 0              # *.test.ts / *.spec.ts 파일 수
    ts_has_vitest_or_jest: bool = False  # vitest/jest 설정 파일 존재 여부
