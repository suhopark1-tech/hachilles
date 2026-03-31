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

"""HAchilles CLI — 메인 커맨드라인 진입점.

레이어 규칙: cli는 모든 내부 모듈을 import할 수 있다. (최상위 레이어)

사용법:
    hachilles scan [PATH]          # 기본 진단 (터미널 출력)
    hachilles scan PATH --json     # JSON 출력
    hachilles scan PATH --html     # HTML 리포트 생성
    hachilles --version            # 버전 출력
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hachilles import __version__
from hachilles.models.scan_result import RiskLevel, ScanResult
from hachilles.scanner import Scanner
from hachilles.score import HarnessScore, ScoreEngine

console = Console()

# ── 색상 매핑 ────────────────────────────────────────────────────────────────

_GRADE_COLORS = {
    "S": "bold green",
    "A": "green",
    "B": "yellow",
    "C": "bold red",
    "D": "bold red on white",
}

_RISK_COLORS = {
    RiskLevel.OK:       "green",
    RiskLevel.LOW:      "yellow",
    RiskLevel.MEDIUM:   "yellow",
    RiskLevel.HIGH:     "bold red",
    RiskLevel.CRITICAL: "bold red on white",
}

_PASSED_ICON = "✓"
_FAILED_ICON = "✗"


# ── CLI 정의 ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version=__version__, prog_name="hachilles")
def main() -> None:
    """HAchilles — AI 에이전트 하네스 진단 및 최적화 플랫폼."""


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--limit", default=10, help="표시할 최근 진단 수")
def history(path: str, limit: int) -> None:
    """프로젝트의 진단 이력을 조회한다 (Phase 2).

    PATH: 조회할 프로젝트 디렉토리 (기본값: 현재 디렉토리)
    """
    target = Path(path).resolve()

    try:
        from hachilles.tracker import HistoryDB
        db = HistoryDB()
        records = db.get_history(str(target), limit=limit)

        if not records:
            console.print(f"[dim]'{target.name}'의 진단 이력이 없습니다[/]")
            return

        # 이력 테이블
        console.print(f"\n[bold]진단 이력 — {target.name}[/]")
        history_table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        history_table.add_column("날짜", min_width=10)
        history_table.add_column("점수", justify="right", min_width=8)
        history_table.add_column("등급", justify="center", min_width=6)
        history_table.add_column("통과/전체", justify="center", min_width=12)
        history_table.add_column("기술 스택", min_width=20)

        for record in records:
            grade_color = _GRADE_COLORS.get(record.grade, "white")
            tech_stack_str = ", ".join(record.tech_stack) or "-"
            history_table.add_row(
                record.timestamp[:10],
                str(record.total_score),
                f"[{grade_color}]{record.grade}[/]",
                f"{record.passed_items}/{record.total_items}",
                tech_stack_str,
            )

        console.print(history_table)

        # ASCII 차트
        console.print()
        chart = db.ascii_chart(str(target), limit=limit)
        console.print(chart)

    except Exception as e:
        console.print(f"[bold red]오류:[/] {e}")
        sys.exit(1)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--json", "output_json", is_flag=True, help="JSON 형식으로 출력")
@click.option("--html", "output_html", is_flag=True, help="HTML 리포트 파일 생성")
@click.option("--out", "-o", default=None, help="출력 파일 경로 (--html 사용 시)")
@click.option("--llm", is_flag=True, help="LLM 기반 Over-engineering 분석 활성화 (Phase 2)")
@click.option("--save-history", is_flag=True, help="진단 결과를 SQLite 이력 DB에 저장 (Phase 2)")
def scan(
    path: str,
    output_json: bool,
    output_html: bool,
    out: str | None,
    llm: bool,
    save_history: bool,
) -> None:
    """대상 프로젝트의 하네스 진단을 실행한다.

    PATH: 진단할 프로젝트 디렉토리 (기본값: 현재 디렉토리)
    """
    target = Path(path).resolve()

    # 스캔
    with console.status(f"[bold cyan]스캔 중: {target}[/]"):
        try:
            scanner = Scanner(target)
            scan_result = scanner.scan()
        except (FileNotFoundError, NotADirectoryError) as e:
            console.print(f"[bold red]오류:[/] {e}")
            sys.exit(1)

    # Phase 2: LLM 기반 Over-engineering 분석
    if llm:
        with console.status("[bold cyan]LLM 분석 중...[/]"):
            try:
                from hachilles.llm import LLMEvaluator
                evaluator = LLMEvaluator()
                hits_before = evaluator.cache.stats()["hits"]
                score, evidence = evaluator.evaluate_over_engineering(target)
                scan_result.llm_over_engineering_score = score
                scan_result.llm_over_engineering_evidence = evidence
                scan_result.llm_analysis_cached = (
                    evaluator.cache.stats()["hits"] > hits_before
                )
            except Exception as e:  # [EXCEPTION] LLM 분석 실패는 비치명적
                scan_result.scan_errors.append(f"LLM 분석 실패: {e}")

    # 점수 계산
    with console.status("[bold cyan]진단 중...[/]"):
        engine = ScoreEngine()
        harness_score = engine.score(scan_result)

    if output_json:
        _output_json(harness_score, scan_result)
    elif output_html:
        _output_html(harness_score, scan_result, out)
    else:
        _output_terminal(harness_score, scan_result, target)

    # Phase 2: 이력 저장
    if save_history:
        try:
            from hachilles.tracker import HistoryDB
            db = HistoryDB()
            total_items = sum(
                len(r.items) for r in harness_score.all_audit_results
            )
            passed_items = sum(
                r.passed_count for r in harness_score.all_audit_results
            )
            db.save(
                project_path=str(target),
                timestamp=scan_result.scan_timestamp or "",
                total_score=harness_score.total,
                ce_score=harness_score.context_score,
                ac_score=harness_score.constraint_score,
                em_score=harness_score.entropy_score,
                grade=harness_score.grade,
                passed_items=passed_items,
                total_items=total_items,
                tech_stack=scan_result.tech_stack,
            )
            console.print("[green]진단 이력 저장 완료[/]")
        except Exception as e:  # [EXCEPTION] 이력 저장 실패는 비치명적
            console.print(f"[yellow]이력 저장 실패: {e}[/]")

    # 등급이 C 이하면 종료 코드 1 반환 (CI 통합용)
    if harness_score.total < 60:
        sys.exit(1)


# ── 터미널 출력 ───────────────────────────────────────────────────────────────

def _output_terminal(score: HarnessScore, scan: ScanResult, target: Path) -> None:
    """Rich를 사용한 컬러 터미널 출력."""

    # 헤더
    console.print()
    console.print(Panel(
        f"[bold]HAchilles 진단 리포트[/]\n[dim]{target}[/]",
        style="bold blue",
        expand=False,
    ))

    # 종합 점수
    grade_color = _GRADE_COLORS.get(score.grade, "white")
    score_panel = Panel(
        f"[{grade_color}]{score.total}점 / 100점   등급: {score.grade}[/]\n"
        f"[dim]{score.grade_label}[/]",
        title="[bold]HAchilles Score[/]",
        expand=False,
    )
    console.print(score_panel)

    # 기둥별 점수 요약
    summary_table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    summary_table.add_column("기둥", style="bold", min_width=18)
    summary_table.add_column("점수", justify="right", min_width=8)
    summary_table.add_column("만점", justify="right", min_width=8)
    summary_table.add_column("통과/전체", justify="center", min_width=10)

    for audit_result in score.all_audit_results:
        pillar_name = {
            "context":    "컨텍스트 엔지니어링",
            "constraint": "아키텍처 제약",
            "entropy":    "엔트로피 관리",
        }.get(audit_result.pillar.value, audit_result.pillar.value)

        total_items = len(audit_result.items)
        passed = audit_result.passed_count
        ratio_color = "green" if passed == total_items else ("yellow" if passed >= total_items // 2 else "red")

        summary_table.add_row(
            pillar_name,
            str(audit_result.score),
            str(audit_result.full_score),
            f"[{ratio_color}]{passed}/{total_items}[/]",
        )

    console.print(summary_table)

    # 세부 진단 항목
    console.print("\n[bold]세부 진단 항목[/]")
    detail_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    detail_table.add_column("코드", min_width=7)
    detail_table.add_column("항목", min_width=22)
    detail_table.add_column("결과", min_width=6, justify="center")
    detail_table.add_column("점수", min_width=8, justify="right")
    detail_table.add_column("상세", min_width=50)

    for audit_result in score.all_audit_results:
        for item in audit_result.items:
            icon = f"[green]{_PASSED_ICON}[/]" if item.passed else f"[red]{_FAILED_ICON}[/]"
            score_str = f"{item.score}/{item.full_score}"
            detail_table.add_row(
                item.code,
                item.name,
                icon,
                score_str,
                item.detail,
            )

    console.print(detail_table)

    # 5대 실패 패턴 위험도
    console.print("\n[bold]5대 실패 패턴 위험도[/]")
    pattern_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    pattern_table.add_column("패턴", min_width=20)
    pattern_table.add_column("위험도", min_width=10, justify="center")
    pattern_table.add_column("요약", min_width=40)

    for pr in score.pattern_risks:
        risk_color = _RISK_COLORS.get(pr.risk, "white")
        pattern_table.add_row(
            pr.pattern,
            f"[{risk_color}]{pr.risk.value.upper()}[/]",
            pr.summary,
        )

    console.print(pattern_table)

    # 스캔 오류 (있을 경우만)
    if scan.scan_errors:
        console.print("\n[bold yellow]스캔 경고:[/]")
        for err in scan.scan_errors:
            console.print(f"  [dim yellow]· {err}[/]")

    console.print()


# ── JSON 출력 ─────────────────────────────────────────────────────────────────

def _output_json(score: HarnessScore, scan: ScanResult) -> None:
    output = {
        "hachilles_version": __version__,
        "total": score.total,
        "total_score": score.total,   # CI yml 호환 별칭 (hachilles-self-audit 잡)
        "grade": score.grade,
        "grade_label": score.grade_label,
        "pillars": {
            "context": {
                "score": score.context_score,
                "full_score": score.context_result.full_score,
                "items": [_audit_item_to_dict(i) for i in score.context_result.items],
            },
            "constraint": {
                "score": score.constraint_score,
                "full_score": score.constraint_result.full_score,
                "items": [_audit_item_to_dict(i) for i in score.constraint_result.items],
            },
            "entropy": {
                "score": score.entropy_score,
                "full_score": score.entropy_result.full_score,
                "items": [_audit_item_to_dict(i) for i in score.entropy_result.items],
            },
        },
        "pattern_risks": [
            {
                "pattern": pr.pattern,
                "risk": pr.risk.value,
                "summary": pr.summary,
                "evidence": pr.evidence,
            }
            for pr in score.pattern_risks
        ],
        "tech_stack": scan.tech_stack,
        "scan_errors": scan.scan_errors,
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))


def _audit_item_to_dict(item) -> dict:
    return {
        "code": item.code,
        "name": item.name,
        "passed": item.passed,
        "score": item.score,
        "full_score": item.full_score,
        "detail": item.detail,
    }


# ── HTML 출력 ─────────────────────────────────────────────────────────────────

def _output_html(score: HarnessScore, scan: ScanResult, out: str | None) -> None:
    """HTML 리포트 생성. [TODO] Sprint 4에서 Jinja2 템플릿으로 고도화 예정."""
    try:
        from hachilles.report import ReportGenerator
        generator = ReportGenerator()
        html_path = generator.generate(score, scan, out)
        console.print(f"[green]HTML 리포트 생성됨:[/] {html_path}")
    except ImportError:
        # report 모듈 미구현 시 간단한 HTML 출력
        console.print("[yellow]report 모듈 준비 중. --json 으로 출력합니다.[/]")
        _output_json(score, scan)


@main.command()
@click.option("--host", default="0.0.0.0", help="바인딩 호스트")
@click.option("--port", default=8000, help="포트 번호")
@click.option("--reload", is_flag=True, help="개발 모드 (자동 재로딩)")
def serve(host: str, port: int, reload: bool) -> None:
    """HAchilles REST API 서버를 시작한다 (Phase 3).

    웹 대시보드: http://localhost:8000/
    API 문서:   http://localhost:8000/api/docs
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[bold red]오류:[/] uvicorn이 설치되지 않았습니다.")
        console.print("  pip install hachilles[web]")
        sys.exit(1)

    display_host = host if host != "0.0.0.0" else "localhost"
    console.print("[bold green]HAchilles API 서버 시작[/]")
    console.print(f"  URL:      http://{display_host}:{port}/")
    console.print(f"  API Docs: http://{display_host}:{port}/api/docs")

    uvicorn.run(
        "hachilles.api:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@main.command("generate-agents")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--out", "-o", default=None, help="출력 파일 경로 (기본: AGENTS.md)")
@click.option("--project-name", default="", help="프로젝트 이름")
def generate_agents(path: str, out: str | None, project_name: str) -> None:
    """AGENTS.md 템플릿을 자동 생성한다 (Phase 3).

    PATH: 대상 프로젝트 디렉토리 (기본값: 현재 디렉토리)
    """
    from hachilles.api.routes.agents import _build_agents_md

    target = Path(path).resolve()

    with console.status(f"[bold cyan]스캔 중: {target}[/]"):
        try:
            scanner = Scanner(target)
            scan_result = scanner.scan()
        except (FileNotFoundError, NotADirectoryError) as e:
            console.print(f"[bold red]오류:[/] {e}")
            sys.exit(1)

    proj_name = project_name or target.name
    content = _build_agents_md(
        proj_name,
        scan_result,
        ["overview", "architecture", "conventions", "forbidden", "session"],
    )

    out_path = Path(out) if out else (target / "AGENTS.md")

    if out_path.exists():
        console.print(
            f"[yellow]경고:[/] {out_path} 파일이 이미 존재합니다. 덮어씁니다."
        )

    out_path.write_text(content, encoding="utf-8")
    lines = len(content.splitlines())
    console.print(f"[green]AGENTS.md 생성 완료:[/] {out_path} ({lines}줄)")


if __name__ == "__main__":
    main()
