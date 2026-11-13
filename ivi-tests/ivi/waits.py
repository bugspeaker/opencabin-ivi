import time


def wait_until(check, timeout=10.0, interval=0.25, what="조건"):
    """check() 가 참 값을 돌려줄 때까지 기다린다.

    고정 sleep 은 느린 기기에서는 flaky, 빠른 기기에서는 시간 낭비라 쓰지 않는다.
    check 안에서 난 예외(요소가 아직 없음 등)는 '아직 아님'으로 보고 다시 본다.
    """
    deadline = time.monotonic() + timeout
    last, error = None, None
    while time.monotonic() < deadline:
        try:
            last = check()
            error = None
            if last:
                return last
        except Exception as err:  # noqa: BLE001 - 대기 중 일시적 실패는 다시 시도
            error = err
        time.sleep(interval)
    detail = f"마지막 값: {last!r}" if error is None else f"마지막 오류: {type(error).__name__}: {error}"
    raise AssertionError(f"{timeout:g}초 안에 {what}이(가) 맞지 않았다 ({detail})")
