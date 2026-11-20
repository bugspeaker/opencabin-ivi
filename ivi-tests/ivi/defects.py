"""알려진 결함 테스트가 '그 결함의 증상'으로 실패했다는 표시.

알려진 결함은 xfail(strict=True) 로 건다. 그런데 raises 를 주지 않으면 어떤 예외든 xfailed 가 된다. 버튼을 못 찾은
NoSuchElementException, Appium 세션 끊김, 테스트 코드의 오타까지 '알려진 결함'으로 삼켜져 게이트를 통과한다.

그래서 테스트는 결함의 증상을 직접 확인한 자리에서만 DefectReproduced 를 내고, xfail 에는 raises=DefectReproduced 를 준다.
    - 증상이 그대로     → DefectReproduced → xfailed (알려진 결함)
    - 다른 이유로 실패  → 그 예외 그대로   → failed (게이트가 막음)
    - 결함이 고쳐짐     → 통과             → strict 라 failed (목록과 xfail 을 지울 때)
unit/test_release_gate.py 가 tests/ 의 모든 xfail(strict=True) 에 raises 가 있는지 확인한다.
"""


class DefectReproduced(AssertionError):
    """알려진 결함(known_defects.txt)의 증상이 재현됐다."""
