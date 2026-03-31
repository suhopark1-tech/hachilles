"""Auditor 계약 테스트 기반 클래스.

새 Auditor를 추가할 때는 이 클래스를 상속하고
auditor / empty_scan / full_scan fixture만 제공하면
모든 계약 검증 테스트가 자동으로 적용된다.

사용 예:
    class TestMyCustomAuditor(AuditorContractTest):
        @pytest.fixture
        def auditor(self):
            return MyCustomAuditor()

        @pytest.fixture
        def empty_scan(self, tmp_path):
            return ScanResult(target_path=tmp_path)

        @pytest.fixture
        def full_scan(self, tmp_path):
            scan = ScanResult(target_path=tmp_path)
            # ... 모든 항목 통과하는 값 설정
            return scan

        def test_pillar(self, auditor):
            assert auditor.pillar == Pillar.MY_PILLAR  # 기둥별 특수 검증
"""

from __future__ import annotations

from hachilles.auditors.base import BaseAuditor
from hachilles.models.scan_result import ScanResult


class AuditorContractTest:
    """BaseAuditor 계약 자동 검증 믹스인.

    모든 추상 프로퍼티 / audit() 반환값 불변식을 테스트한다.
    하위 테스트 클래스에서 아래 fixture를 반드시 제공해야 한다:
      - auditor  : BaseAuditor 구현체 인스턴스
      - empty_scan: 모든 필드가 기본값인 ScanResult (대부분 실패 예상)
      - full_scan : 모든 항목 통과하도록 설정된 ScanResult
    """

    # ── 인터페이스 프로퍼티 계약 ──────────────────────────────────────────────

    def test_pillar_is_pillar_enum(self, auditor: BaseAuditor):
        """pillar가 Pillar 열거형 값이어야 한다."""
        from hachilles.models.scan_result import Pillar
        assert isinstance(auditor.pillar, Pillar), (
            f"pillar은 Pillar 타입이어야 함: {type(auditor.pillar)}"
        )

    def test_full_score_is_positive_int(self, auditor: BaseAuditor):
        """full_score가 양수 정수여야 한다."""
        assert isinstance(auditor.full_score, int)
        assert auditor.full_score > 0, (
            f"full_score는 0보다 커야 함: {auditor.full_score}"
        )

    def test_item_codes_non_empty_list(self, auditor: BaseAuditor):
        """item_codes가 비어 있지 않은 리스트여야 한다."""
        codes = auditor.item_codes
        assert isinstance(codes, list)
        assert len(codes) > 0, "item_codes는 비어 있을 수 없음"

    def test_item_codes_unique(self, auditor: BaseAuditor):
        """item_codes에 중복이 없어야 한다."""
        codes = auditor.item_codes
        assert len(codes) == len(set(codes)), (
            f"item_codes에 중복 코드 있음: {codes}"
        )

    def test_item_codes_format(self, auditor: BaseAuditor):
        """item_codes가 'XX-NN' 형식이어야 한다 (예: CE-01, AC-05)."""
        import re
        pattern = re.compile(r"^[A-Z]{2}-\d{2}$")
        for code in auditor.item_codes:
            assert pattern.match(code), (
                f"코드 형식 불일치: '{code}' (기대 형식: XX-NN)"
            )

    def test_full_score_equals_item_scores_sum(
        self, auditor: BaseAuditor, full_scan: ScanResult
    ):
        """full_score가 각 AuditItem.full_score 합과 일치해야 한다."""
        result = auditor.audit(full_scan)
        assert result.full_score == auditor.full_score, (
            f"full_score 불일치: auditor={auditor.full_score}, "
            f"result.items 합={result.full_score}"
        )

    # ── audit() 반환값 계약 ───────────────────────────────────────────────────

    def test_audit_returns_correct_pillar(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """audit() 반환값의 pillar가 auditor.pillar와 일치해야 한다."""
        result = auditor.audit(empty_scan)
        assert result.pillar == auditor.pillar

    def test_audit_covers_all_item_codes(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """audit() 반환값의 items 코드 집합이 item_codes와 일치해야 한다."""
        result = auditor.audit(empty_scan)
        result_codes = {item.code for item in result.items}
        expected = set(auditor.item_codes)
        assert result_codes == expected, (
            f"코드 불일치:\n  result={sorted(result_codes)}\n  expected={sorted(expected)}"
        )

    def test_audit_score_in_range_empty(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """빈 프로젝트에서도 score가 [0, full_score] 범위 내여야 한다."""
        result = auditor.audit(empty_scan)
        assert 0 <= result.score <= result.full_score, (
            f"점수 범위 초과: score={result.score}, full_score={result.full_score}"
        )

    def test_audit_score_in_range_full(
        self, auditor: BaseAuditor, full_scan: ScanResult
    ):
        """완전한 프로젝트에서도 score가 [0, full_score] 범위 내여야 한다."""
        result = auditor.audit(full_scan)
        assert 0 <= result.score <= result.full_score

    def test_each_item_score_in_range(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """모든 AuditItem의 score가 [0, item.full_score] 범위 내여야 한다."""
        result = auditor.audit(empty_scan)
        for item in result.items:
            assert 0 <= item.score <= item.full_score, (
                f"{item.code}: score={item.score}, full_score={item.full_score}"
            )

    def test_passed_item_gets_full_score_or_partial(
        self, auditor: BaseAuditor, full_scan: ScanResult
    ):
        """passed=True인 항목은 score > 0이어야 한다."""
        result = auditor.audit(full_scan)
        for item in result.items:
            if item.passed:
                assert item.score > 0, (
                    f"{item.code}: passed=True인데 score=0"
                )

    def test_failed_item_score_less_than_full(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """passed=False인 항목은 score < full_score여야 한다."""
        result = auditor.audit(empty_scan)
        for item in result.items:
            if not item.passed:
                assert item.score < item.full_score, (
                    f"{item.code}: passed=False인데 score == full_score"
                )

    def test_verify_result_no_violations_full(
        self, auditor: BaseAuditor, full_scan: ScanResult
    ):
        """verify_result()가 완전한 프로젝트에서 위반 없음을 반환해야 한다."""
        result = auditor.audit(full_scan)
        violations = auditor.verify_result(result)
        assert not violations, (
            "계약 위반:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_verify_result_no_violations_empty(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """verify_result()가 빈 프로젝트에서도 위반 없음을 반환해야 한다."""
        result = auditor.audit(empty_scan)
        violations = auditor.verify_result(result)
        assert not violations, (
            "계약 위반:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_full_project_achieves_maximum_score(
        self, auditor: BaseAuditor, full_scan: ScanResult
    ):
        """완전한 프로젝트는 만점을 받아야 한다."""
        result = auditor.audit(full_scan)
        assert result.score == auditor.full_score, (
            f"만점 미달: score={result.score}, full_score={auditor.full_score}\n"
            + "\n".join(
                f"  실패: {item.code} — {item.detail}"
                for item in result.items if not item.passed
            )
        )

    def test_audit_is_deterministic(
        self, auditor: BaseAuditor, empty_scan: ScanResult
    ):
        """동일 ScanResult에 대해 audit()를 두 번 호출하면 동일 결과가 나와야 한다."""
        result1 = auditor.audit(empty_scan)
        result2 = auditor.audit(empty_scan)
        assert result1.score == result2.score
        assert result1.full_score == result2.full_score
        assert [i.code for i in result1.items] == [i.code for i in result2.items]
        assert [i.passed for i in result1.items] == [i.passed for i in result2.items]
