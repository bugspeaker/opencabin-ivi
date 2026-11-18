import subprocess
import threading
import time

from selenium.common.exceptions import WebDriverException

# 대기 중에 '아직 아님'으로 보고 다시 볼 예외. 여기에 없는 예외(AttributeError, TypeError, NameError, KeyError 같은
# 코드 오류)는 기다리지 않고 바로 올린다. 오타가 10초 뒤 "조건이 맞지 않았다"로 바뀌어 원인 분석이 늦어지지 않게 한다.
RETRY_ERRORS = (
    WebDriverException,           # 요소가 아직 없음, 화면이 바뀌어 요소가 낡음 (NoSuchElement, StaleElementReference 포함)
    RuntimeError,                 # adb 실패(AdbError), 차량 값을 아직 못 읽음 (vehicle.py)
    ValueError, IndexError,       # 화면 글자를 숫자로 바꾸는 중간 상태 ('--', 빈 글자, 'mm:ss' 가 아직 아님)
    AssertionError,               # check 안에서 부른 다른 대기가 시간을 넘김
    OSError, subprocess.SubprocessError,  # 전원을 껐다 켜는 동안의 adb, HTTP 연결 실패
)

_state = threading.local()


def polling():
    """지금 wait_until 의 check 안에서 불렸는가. 화면 객체는 이때 기다리지 않고 한 번만 찾는다 (대기 중첩 방지)."""
    return getattr(_state, "depth", 0) > 0


def wait_until(check, timeout=10.0, interval=0.25, what="조건", ignore=RETRY_ERRORS):
    """check() 가 참 값을 돌려줄 때까지 기다린다.

    고정 sleep 은 느린 기기에서는 flaky, 빠른 기기에서는 시간 낭비라 쓰지 않는다.
    check 안에서 난 예외 가운데 ignore 에 든 것(요소가 아직 없음 등)만 '아직 아님'으로 보고 다시 본다.
    """
    deadline = time.monotonic() + timeout
    last, error = None, None
    while time.monotonic() < deadline:
        _state.depth = getattr(_state, "depth", 0) + 1
        try:
            last = check()
            error = None
            if last:
                return last
        except ignore as err:
            error = err
        finally:
            _state.depth -= 1
        time.sleep(interval)
    detail = f"마지막 값: {last!r}" if error is None else f"마지막 오류: {type(error).__name__}: {error}"
    raise AssertionError(f"{timeout:g}초 안에 {what}이(가) 맞지 않았다 ({detail})")


def wait_value(read, expected, timeout=10.0, interval=0.25, what="값"):
    """read() 가 expected 가 될 때까지 기다린다. 실패 메시지에 마지막으로 읽은 값을 남긴다
    (`wait_until(lambda: read() == expected)` 는 '마지막 값: False' 만 남아 실제 값을 실패 자료에서 찾아야 했다)."""
    seen = []

    def check():
        seen[:] = [read()]
        return seen[0] == expected

    try:
        return wait_until(check, timeout=timeout, interval=interval, what=f"{what} {expected!r}")
    except AssertionError:
        if not seen:
            raise
        raise AssertionError(f"{timeout:g}초 안에 {what}이(가) {expected!r}이(가) 되지 않았다 (마지막으로 읽은 값: {seen[0]!r})") from None


def stays(check, duration=1.5, interval=0.25, what="조건"):
    """check() 가 duration 동안 계속 참인지 본다. '바뀌지 않아야 한다'를 한 번만 보면 늦게 도착하는 잘못된 쓰기를 놓친다."""
    deadline = time.monotonic() + duration
    while True:
        value = check()
        if not value:
            raise AssertionError(f"{duration:g}초 동안 {what}이(가) 유지되지 않았다 (값: {value!r})")
        if time.monotonic() >= deadline:
            return value
        time.sleep(interval)
