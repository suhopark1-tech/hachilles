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

"""HAchilles 처방 엔진 — 실패 항목별 맥락 특화 처방 생성."""
from __future__ import annotations

from dataclasses import dataclass, field

from hachilles.models.scan_result import AuditItem, ScanResult
from hachilles.score import HarnessScore


@dataclass
class Prescription:
    code: str
    name: str
    priority: int
    impact: int
    title: str
    steps: list[str]
    snippet: str = ""
    reference: str = ""

@dataclass
class PrescriptionReport:
    prescriptions: list[Prescription] = field(default_factory=list)
    total_recoverable: int = 0
    @property
    def top_priority(self) -> list[Prescription]:
        return self.prescriptions[:3]

class PrescriptionEngine:
    def prescribe(self, score: HarnessScore, scan: ScanResult) -> PrescriptionReport:
        rxs = []
        for i, item in enumerate(score.critical_items):
            rx = self._generate(item, scan)
            if rx:
                rx.priority = i
                rxs.append(rx)
        return PrescriptionReport(prescriptions=rxs, total_recoverable=sum(r.impact for r in rxs))

    def _generate(self, item: AuditItem, scan: ScanResult) -> Prescription | None:
        h = getattr(self, f"_rx_{item.code.lower().replace('-','_')}", None)
        return h(item, scan) if h else self._rx_default(item, scan)

    def _rx_ce_01(self, item, scan):
        return Prescription("CE-01", item.name, 0, item.full_score,
            "AGENTS.md 파일 생성 — AI에게 프로젝트 지도 제공",
            ["프로젝트 루트에 AGENTS.md를 생성합니다.",
             "아키텍처 개요, 핵심 컨벤션, 금지 패턴, 진행 상황을 기술합니다.",
             "100~400줄로 유지합니다 (너무 길면 AI가 전체를 읽지 않습니다).",
             "세션 시작 지시에 'AGENTS.md를 먼저 읽어라'를 포함합니다."],
            _S["agents_md"], "하네스 엔지니어링 2장 — Context Engineering 기초")

    def _rx_ce_02(self, item, scan):
        missing = ([m for m, f in [("docs/architecture.md", scan.has_architecture_md),
                                    ("docs/conventions.md", scan.has_conventions_md),
                                    ("docs/decisions/", scan.has_adr_dir)] if not f])
        return Prescription("CE-02", item.name, 0, item.full_score,
            "docs/ 구조 보완 — AI가 참조할 문서 체계 구축",
            [f"누락된 문서 생성: {', '.join(missing) if missing else '없음'}",
             "architecture.md: 시스템 구성, 레이어, 데이터 흐름을 기술합니다.",
             "conventions.md: 네이밍, 파일 구조, PR 규칙을 열거합니다.",
             "docs/decisions/: 설계 결정을 ADR 형식으로 기록합니다."],
            _S["adr"], "ADR 형식: https://adr.github.io")

    def _rx_ce_03(self, item, scan):
        return Prescription("CE-03", item.name, 0, item.full_score,
            "세션 브릿지 파일 생성 — 세션 간 컨텍스트 단절 방지",
            ["프로젝트 루트에 claude-progress.txt를 생성합니다.",
             "현재 스프린트, 완료 항목, 다음 세션 진입 정보를 기록합니다.",
             "매 세션 종료 시 이 파일을 갱신하는 규칙을 정합니다.",
             "AGENTS.md에 '세션 시작 전 claude-progress.txt 확인'을 명시합니다."],
            _S["session_bridge"], "하네스 엔지니어링 3장 — 세션 브릿지 패턴")

    def _rx_ce_04(self, item, scan):
        return Prescription("CE-04", item.name, 0, item.full_score,
            "feature_list.json 생성 — 완료 기준 명시화",
            ["프로젝트 루트에 feature_list.json을 생성합니다.",
             "기능 목록과 각 상태(planned/in-progress/implemented)를 정의합니다.",
             "done_definition 필드에 완료 기준을 구체적으로 명시합니다.",
             "AI에게 작업 전 feature_list.json으로 범위를 파악하도록 지시합니다."],
            _S["feature_list"])

    def _rx_ce_05(self, item, scan):
        return Prescription("CE-05", item.name, 0, item.full_score,
            "AGENTS.md와 architecture/conventions 문서 연결",
            ["AGENTS.md 상단에 보조 문서 참조 링크를 추가합니다.",
             "architecture.md와 conventions.md 존재 여부를 확인합니다.",
             "AGENTS.md에서 각 문서로의 명시적 참조 섹션을 추가합니다."],
            "## 문서 구조\n- [아키텍처](docs/architecture.md)\n- [컨벤션](docs/conventions.md)")

    def _rx_ac_01(self, item, scan):
        is_py = "python" in (getattr(scan, "tech_stack", []) or [])
        return Prescription("AC-01", item.name, 0, item.full_score,
            "린터 설정 추가 — AI 생성 코드 품질 게이트",
            ["Python: pyproject.toml에 [tool.ruff] 섹션을 추가합니다." if is_py
             else "JS/TS: .eslintrc.json을 생성합니다.",
             "lint 명령이 통과하는지 확인합니다: ruff check . 또는 eslint .",
             "AGENTS.md에 '코드 제출 전 린터를 실행하라'고 명시합니다."],
            _S["ruff"] if is_py else "", "Ruff: https://docs.astral.sh/ruff/")

    def _rx_ac_02(self, item, scan):
        return Prescription("AC-02", item.name, 0, item.full_score,
            "pre-commit 훅 설정 — 커밋 전 자동 품질 검사",
            ["pip install pre-commit 으로 설치합니다.",
             ".pre-commit-config.yaml을 생성합니다.",
             "pre-commit install 로 훅을 활성화합니다."],
            _S["pre_commit"], "pre-commit: https://pre-commit.com")

    def _rx_ac_03(self, item, scan):
        return Prescription("AC-03", item.name, 0, item.full_score,
            "CI 게이트 추가 — PR마다 자동 lint/test 실행",
            [".github/workflows/ci.yml을 생성합니다.",
             "push/PR 트리거에 lint + test 잡을 포함합니다.",
             "메인 브랜치 병합 조건으로 CI 통과를 설정합니다."],
            _S["ci"])

    def _rx_ac_04(self, item, scan):
        return Prescription("AC-04", item.name, 0, item.full_score,
            "docs/forbidden.md 생성 — AI에게 금지 패턴 명시",
            ["docs/forbidden.md 파일을 생성합니다.",
             "의존성 방향 위반, 비결정론 코드, 전역 상태 수정 패턴을 목록화합니다.",
             "AGENTS.md에서 이 파일을 참조합니다.",
             "코드 리뷰 시 체크리스트로 활용합니다."],
            _S["forbidden"])

    def _rx_ac_05(self, item, scan):
        v = getattr(scan, "dependency_violations", 0) or 0
        return Prescription("AC-05", item.name, 0, item.full_score,
            f"의존성 방향 위반 {v}건 수정",
            [f"역방향 의존성 {v}건을 확인합니다.",
             "상위 레이어(cli)가 하위 레이어(models)를 import하는 구조를 점검합니다.",
             "역방향 import를 인터페이스 추출 또는 의존성 주입으로 해결합니다."])

    def _rx_em_01(self, item, scan):
        d = getattr(scan, "agents_md_staleness_days", None)
        return Prescription("EM-01", item.name, 0, item.full_score,
            f"AGENTS.md 갱신 필요 — {d}일 경과" if d else "AGENTS.md 갱신 필요",
            ["AGENTS.md의 마지막 갱신 날짜와 현재 상태를 비교합니다.",
             "완료된 기능, 변경된 아키텍처, 새 컨벤션을 반영합니다.",
             "스프린트 완료 시 갱신을 의무화합니다."])

    def _rx_em_02(self, item, scan):
        d = getattr(scan, "docs_avg_staleness_days", None)
        return Prescription("EM-02", item.name, 0, item.full_score,
            "docs/ 문서 일괄 갱신",
            [f"docs/ 평균 staleness: {d}일." if d else "docs/ staleness 측정 불가.",
             "architecture.md, conventions.md, ADR을 현재 상태로 갱신합니다.",
             "정기 갱신을 CI/스프린트 프로세스에 포함합니다."])

    def _rx_em_03(self, item, scan):
        refs = getattr(scan, "invalid_agents_refs", []) or []
        return Prescription("EM-03", item.name, 0, item.full_score,
            f"AGENTS.md 참조 유효성 수정 ({len(refs)}건)",
            [f"유효하지 않은 참조 {len(refs)}건을 수정합니다.",
             *[f"  · {r}" for r in refs[:5]],
             "존재하지 않는 파일/함수 참조를 제거하거나 올바른 경로로 수정합니다."])

    def _rx_em_04(self, item, scan):
        return Prescription("EM-04", item.name, 0, item.full_score,
            "GC 에이전트 추가 — 자동 컨텍스트 정리",
            ["gc_agent.py를 프로젝트 루트에 생성합니다.",
             "오래된 캐시·임시 파일을 정리하는 로직을 구현합니다.",
             "CI 또는 cron에 주 1회 실행을 등록합니다."],
            _S["gc_agent"])

    def _rx_em_05(self, item, scan):
        r = getattr(scan, "bare_lint_suppression_ratio", 0.0) or 0.0
        return Prescription("EM-05", item.name, 0, item.full_score,
            f"이유 없는 lint suppress 제거 ({r:.0%})",
            [f"현재 이유 없는 suppress 비율: {r:.0%}.",
             "# noqa, # type: ignore 주석 없는 suppress를 전수 검색합니다.",
             "각 suppress에 이유를 추가하거나 suppress 자체를 제거합니다.",
             "ruff check --select=RUF100 으로 불필요한 suppress를 감지합니다."])

    def _rx_default(self, item, scan):
        return Prescription(item.code, item.name, 0, item.full_score,
            f"{item.name} 개선", [item.detail or "해당 항목을 검토하고 개선합니다."])


_S = {
    "agents_md": "# AGENTS.md\n## 역할\n[프로젝트 설명]\n## 아키텍처\n[구조 설명]\n## 금지 패턴\n→ docs/forbidden.md",
    "adr": "# docs/decisions/001-[제목].md\n## 상태: 승인됨\n## 컨텍스트\n[배경]\n## 결정\n[내용]\n## 결과\n[영향]",
    "session_bridge": "# claude-progress.txt\n## Sprint: X\n## 완료: [항목]\n## 다음 단계: [내용]",
    "feature_list": '{"features": [{"id": "f1", "name": "기능명", "status": "planned"}], "done_definition": ["테스트 통과"]}',
    "ruff": "[tool.ruff]\nline-length = 100\n\n[tool.ruff.lint]\nselect = [\"E\", \"W\", \"F\", \"I\"]",
    "pre_commit": "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.4.0\n    hooks:\n      - id: ruff",
    "ci": "name: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pip install -e \".[dev]\"\n      - run: ruff check .\n      - run: pytest -q",
    "forbidden": "# docs/forbidden.md\n## 의존성 방향 위반\n- 하위 레이어가 상위 레이어를 import\n## 비결정론\n- random, datetime.now()를 채점에 사용",
    "gc_agent": "from pathlib import Path\nfrom datetime import datetime, timedelta\n\ndef gc_cache(d=Path('.cache'), days=30):\n    c = datetime.now() - timedelta(days=days)\n    [f.unlink() for f in d.glob('*.json') if datetime.fromtimestamp(f.stat().st_mtime) < c]",
}
