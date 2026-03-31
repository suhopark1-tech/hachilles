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

"""HAchilles HTML 리포트 생성기 — Jinja2 템플릿 기반 (Phase 3).

레이어 규칙: report는 models, score, prescriptions만 import한다. cli는 import 금지.

템플릿 위치: src/hachilles/report/templates/report.html.j2
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from hachilles.models.scan_result import ScanResult
from hachilles.prescriptions import PrescriptionEngine
from hachilles.score import HarnessScore

# 템플릿 디렉토리 (패키지 내부)
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# 등급별 색상
_GRADE_COLORS = {
    "S": "#10b981", "A": "#22c55e", "B": "#f59e0b",
    "C": "#ef4444",  "D": "#dc2626",
}


class ReportGenerator:
    """HarnessScore + ScanResult → 자기완결형 HTML 파일.

    Jinja2 템플릿을 사용하여 Phase 2 데이터(AST, LLM, 타임스탬프 등)를 포함한
    풍부한 HTML 리포트를 생성한다.
    """

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )

    def generate(
        self,
        score: HarnessScore,
        scan: ScanResult,
        out: str | None = None,
    ) -> Path:
        """HTML 리포트를 생성하고 파일 경로를 반환한다."""
        rx_report = PrescriptionEngine().prescribe(score, scan)
        context = self._build_context(score, scan, rx_report)

        template = self._env.get_template("report.html.j2")
        html = template.render(**context)

        path = Path(out) if out else (scan.target_path / "hachilles-report.html")
        path.write_text(html, encoding="utf-8")
        return path

    # ── Private ──────────────────────────────────────────────────────────────

    def _build_context(
        self,
        score: HarnessScore,
        scan: ScanResult,
        rx_report,
    ) -> dict:
        """Jinja2 템플릿에 전달할 컨텍스트 딕셔너리 구성."""
        grade_color = _GRADE_COLORS.get(score.grade, "#6b7280")
        arc = int((1 - score.total / 100) * 283)  # SVG stroke-dashoffset (283=2πr, r=45)

        def _bar_color(pct: int) -> str:
            return "#10b981" if pct >= 80 else ("#f59e0b" if pct >= 60 else "#ef4444")

        # 기둥별 막대그래프 데이터
        pillars = []
        for result in score.all_audit_results:
            pillar_name = {
                "context":    "컨텍스트 엔지니어링",
                "constraint": "아키텍처 제약",
                "entropy":    "엔트로피 관리",
            }.get(result.pillar.value, result.pillar.value)
            pct = int(result.score / result.full_score * 100) if result.full_score else 0
            pillars.append({
                "name": pillar_name,
                "score": result.score,
                "full_score": result.full_score,
                "pct": pct,
                "color": _bar_color(pct),
            })

        # 진단 항목 목록
        audit_items = [
            {
                "code": item.code,
                "name": item.name,
                "passed": item.passed,
                "score": item.score,
                "full_score": item.full_score,
                "detail": item.detail,
            }
            for result in score.all_audit_results
            for item in result.items
        ]

        # 패턴 위험도
        pattern_risks = [
            {
                "pattern": pr.pattern,
                "risk": pr.risk.value,
                "summary": pr.summary,
                "evidence": pr.evidence,
            }
            for pr in score.pattern_risks
        ]

        # 처방
        prescriptions = []
        for p in rx_report.prescriptions:
            prescriptions.append({
                "code": p.code,
                "title": p.title,
                "impact": p.impact,
                "steps": p.steps,
                "snippet": getattr(p, "snippet", ""),
                "reference": getattr(p, "reference", ""),
            })

        from hachilles import __version__
        return {
            "version": __version__,
            "project_name": scan.target_path.name,
            "target_path": str(scan.target_path),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "scan_timestamp": scan.scan_timestamp,
            "grade_color": grade_color,
            "arc": arc,
            "total": score.total,
            "grade": score.grade,
            "grade_label": score.grade_label,
            "passed_rate": score.passed_rate,
            "total_recoverable": rx_report.total_recoverable,
            "tech_stack": scan.tech_stack,
            "pillars": pillars,
            "audit_items": audit_items,
            "pattern_risks": pattern_risks,
            "prescriptions": prescriptions,
            "scan_errors": scan.scan_errors,
            # Phase 2 필드
            "dependency_cycles": scan.dependency_cycles,
            "layer_violations": scan.layer_violations,
            "llm_score": scan.llm_over_engineering_score,
            "llm_evidence": scan.llm_over_engineering_evidence,
            "go_module_name": scan.go_module_name,
            "java_build_tool": scan.java_build_tool,
        }
