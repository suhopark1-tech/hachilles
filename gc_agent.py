"""HAchilles GC Agent — 컨텍스트 엔트로피 정리 에이전트.

EM-04: GC 에이전트 존재 (5점)

역할:
  - 오래된 스캔 캐시 파일(.hachilles_cache/) 자동 정리
  - 임시 리포트 파일 만료 기준 초과 시 삭제
  - 실행 로그를 표준 출력으로 기록 (사이드이펙트 최소화)

설계 원칙:
  - 정리(clean-up)만 수행한다. 생성이나 수정은 하지 않는다.
  - 삭제 전 항목을 출력하여 가시성을 확보한다.
  - dry_run=True이면 삭제하지 않고 목록만 출력한다.

사용 예:
    python -m hachilles.gc_agent
    python -m hachilles.gc_agent --dry-run
    python -m hachilles.gc_agent --max-age-days 7
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── 기본 설정 ────────────────────────────────────────────────────────────────

_DEFAULT_CACHE_DIR   = Path(".hachilles_cache")
_DEFAULT_REPORT_DIR  = Path(".hachilles_reports")
_DEFAULT_MAX_AGE_DAYS = 30


# ── 핵심 함수 ────────────────────────────────────────────────────────────────

def gc_scan_cache(
    cache_dir: Path = _DEFAULT_CACHE_DIR,
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
    dry_run: bool = False,
) -> list[Path]:
    """오래된 스캔 캐시 파일(.json)을 정리한다.

    Args:
        cache_dir:    캐시 디렉토리 경로 (기본: .hachilles_cache/)
        max_age_days: 이 일수를 초과하면 삭제 대상 (기본: 30일)
        dry_run:      True이면 목록만 반환하고 실제 삭제하지 않음

    Returns:
        삭제(또는 삭제 예정) 파일 경로 목록
    """
    if not cache_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed: list[Path] = []

    for f in sorted(cache_dir.glob("*.json")):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            removed.append(f)
            if not dry_run:
                f.unlink()

    return removed


def gc_reports(
    report_dir: Path = _DEFAULT_REPORT_DIR,
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
    dry_run: bool = False,
) -> list[Path]:
    """오래된 임시 리포트 파일(.html, .json)을 정리한다."""
    if not report_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed: list[Path] = []

    for f in sorted(report_dir.glob("*.html")) + sorted(report_dir.glob("*.json")):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            removed.append(f)
            if not dry_run:
                f.unlink()

    return removed


def run_gc(
    max_age_days: int = _DEFAULT_MAX_AGE_DAYS,
    dry_run: bool = False,
) -> dict[str, list[Path]]:
    """전체 GC 작업을 실행하고 정리 결과를 반환한다.

    Returns:
        {"cache": [...], "reports": [...]}
    """
    cache_removed   = gc_scan_cache(max_age_days=max_age_days, dry_run=dry_run)
    reports_removed = gc_reports(max_age_days=max_age_days, dry_run=dry_run)

    prefix = "[DRY-RUN] " if dry_run else ""
    total = len(cache_removed) + len(reports_removed)

    if total == 0:
        print(f"{prefix}GC 완료: 정리할 파일 없음 (기준: {max_age_days}일)")
    else:
        print(f"{prefix}GC 완료: {total}개 파일 정리")
        for p in cache_removed:
            print(f"  캐시: {p}")
        for p in reports_removed:
            print(f"  리포트: {p}")

    return {"cache": cache_removed, "reports": reports_removed}


# ── CLI 진입점 ──────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hachilles-gc",
        description="HAchilles GC Agent — 오래된 캐시·리포트 정리",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=_DEFAULT_MAX_AGE_DAYS,
        metavar="N",
        help=f"N일 초과 파일 삭제 (기본: {_DEFAULT_MAX_AGE_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 삭제 없이 대상 파일 목록만 출력",
    )
    return parser


def main() -> None:
    """CLI 진입점."""
    parser = _build_parser()
    args = parser.parse_args()
    run_gc(max_age_days=args.max_age_days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
