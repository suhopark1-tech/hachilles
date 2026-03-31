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

"""HAchilles BaseAuditor — 모든 Auditor의 추상 기반 클래스.

레이어 규칙: auditors는 models와 scanner만 import한다. score/cli는 import 금지.

## Auditor 계약 (Contract)

모든 Auditor 구현체는 다음 계약을 충족해야 한다:

  1. pillar    : 이 Auditor가 담당하는 기둥 (Pillar 열거형)
  2. full_score: 실행 없이 쿼리 가능한 만점 (int)
  3. item_codes: 이 Auditor가 평가하는 진단 코드 목록 (list[str])
  4. audit()   : ScanResult → AuditResult 변환의 순수 함수

## 계약 불변식 (Invariant)

audit()가 반환하는 AuditResult는 다음을 항상 만족해야 한다:
  - result.pillar == self.pillar
  - result.full_score == self.full_score
  - {item.code for item in result.items} == set(self.item_codes)
  - 0 <= result.score <= result.full_score
  - 각 item.score <= item.full_score

verify_result()를 호출하면 이 불변식들을 런타임에 검증할 수 있다.

## 새 Auditor 추가 방법

1. BaseAuditor를 상속하고 pillar, full_score, item_codes, audit()를 구현한다.
2. AGENTS.md의 진단 항목 목록에 새 코드를 등록한다.
3. docs/architecture.md의 배점 테이블을 업데이트한다.
4. AuditorContractTest를 상속한 단위 테스트를 작성한다.
   (tests/auditors/contract.py 참고)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hachilles.models.scan_result import AuditResult, Pillar, ScanResult


class BaseAuditor(ABC):
    """Auditor 공통 추상 인터페이스.

    구현 규칙:
      - audit() 메서드만 public API다.
      - 내부 헬퍼는 _으로 시작한다.
      - ScanResult 외 파일에 직접 접근하지 않는다.
      - Auditor 인스턴스는 상태(state)를 보유하지 않는다 (무상태 설계).
    """

    # ── 추상 프로퍼티: 실행 전에 쿼리 가능 ──────────────────────────────────

    @property
    @abstractmethod
    def pillar(self) -> Pillar:
        """이 Auditor가 담당하는 기둥.

        예: Pillar.CONTEXT
        """

    @property
    @abstractmethod
    def full_score(self) -> int:
        """이 Auditor의 만점 (배점 합계).

        audit() 실행 없이 쿼리 가능해야 한다.
        ScoreEngine이 세 Auditor의 full_score 합이 100인지 검증하는 데 사용한다.

        예: ContextAuditor → 40, ConstraintAuditor → 35, EntropyAuditor → 25
        """

    @property
    @abstractmethod
    def item_codes(self) -> list[str]:
        """이 Auditor가 평가하는 진단 항목 코드 목록.

        audit() 실행 없이 쿼리 가능해야 한다.
        AuditResult의 items와 코드 집합이 일치해야 한다.

        예: ["CE-01", "CE-02", "CE-03", "CE-04", "CE-05"]
        """

    # ── 추상 메서드: 핵심 진단 로직 ─────────────────────────────────────────

    @abstractmethod
    def audit(self, scan: ScanResult) -> AuditResult:
        """ScanResult를 진단하여 AuditResult를 반환한다.

        Args:
            scan: Scanner가 수집한 원시 데이터.

        Returns:
            이 기둥의 전체 진단 결과.

        계약:
            - result.pillar == self.pillar
            - result.full_score == self.full_score
            - result.items의 코드 집합 == set(self.item_codes)
            - 0 <= result.score <= result.full_score
        """

    # ── 구체 메서드: 계약 검증 ───────────────────────────────────────────────

    def verify_result(self, result: AuditResult) -> list[str]:
        """audit()가 반환한 AuditResult가 계약을 충족하는지 검증한다.

        테스트 및 CI에서 호출할 수 있다.
        위반 항목을 문자열 목록으로 반환한다. 빈 목록이면 계약 충족.

        사용 예:
            result = auditor.audit(scan)
            violations = auditor.verify_result(result)
            assert not violations, violations
        """
        violations: list[str] = []

        # 1. pillar 일치
        if result.pillar != self.pillar:
            violations.append(
                f"pillar 불일치: result.pillar={result.pillar!r}, "
                f"self.pillar={self.pillar!r}"
            )

        # 2. full_score 일치
        if result.full_score != self.full_score:
            violations.append(
                f"full_score 불일치: result.full_score={result.full_score}, "
                f"self.full_score={self.full_score}"
            )

        # 3. item_codes 집합 일치
        result_codes = {item.code for item in result.items}
        expected_codes = set(self.item_codes)
        if result_codes != expected_codes:
            extra   = result_codes - expected_codes
            missing = expected_codes - result_codes
            if extra:
                violations.append(f"예상치 않은 진단 코드: {sorted(extra)}")
            if missing:
                violations.append(f"누락된 진단 코드: {sorted(missing)}")

        # 4. 점수 범위 검증
        if not (0 <= result.score <= result.full_score):
            violations.append(
                f"점수 범위 초과: score={result.score}, "
                f"full_score={result.full_score}"
            )

        # 5. 각 AuditItem 점수 범위
        for item in result.items:
            if not (0 <= item.score <= item.full_score):
                violations.append(
                    f"{item.code}: item.score={item.score} > "
                    f"item.full_score={item.full_score}"
                )

        return violations
