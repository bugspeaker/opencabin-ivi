import subprocess
import threading
import time

from selenium.common.exceptions import InvalidSessionIdException, NoSuchDriverException, WebDriverException

# 대기 중에 '아직 아님'으로 보고 다시 볼 예외. 여기에 없는 예외(AttributeError, TypeError, NameError, KeyError 같은
# 코드 오류)는 기다리지 않고 바로 올린다. 오타가 10초 뒤 "조건이 맞지 않았다"로 바뀌어 원인 분석이 늦어지지 않게 한다.
RETRY_ERRORS = (
    WebDriverException,           # 요소가 아직 없음, 화면이 바뀌어 요소가 낡음 (NoSuchElement, StaleElementReference 포함)
    RuntimeError,                 # adb 실패(AdbError), 차량 값을 아직 못 읽음 (vehicle.py)
    ValueError, IndexError,       # 화면 글자를 숫자로 바꾸는 중간 상태 ('--', 빈 글자, 'mm:ss' 가 아직 아님)
    AssertionError,               # check 안에서 부른 다른 대기가 시간을 넘김
    OSError, subprocess.SubprocessError,  # 전원을 껐다 켜는 동안의 adb, HTTP 연결 실패
)

# Appium 세션이나 UiAutomator2 서버가 죽었다는 응답. WebDriverException 이라 위 목록에 걸리지만, 다시 봐도 살아나지 않는다.
# 2026-11-19 막 켠 에뮬레이터에서 계측 프로세스가 죽자('instrumentation process is not running') 그 뒤 테스트가 대기마다
# 제한 시간을 다 쓰고 준비 단계 오류로 끝났다. 이런 응답은 기다리지 않고 SessionLost 로 바로 올린다.
SESSION_LOST_TYPES = (InvalidSessionIdException, NoSuchDriverException)
SESSION_LOST_MESSAGES = (
    "instrumentation process is not running",           # UiAutomator2 서버(계측 프로세스)가 죽음
    "session is either terminated or not started",      # Appium 이 세션을 이미 지움
    "cannot be proxied to uiautomator2 server",         # 위와 같은 원인으로 명령을 넘기지 못함
)


class SessionLost(Exception):
    """Appium 세션이 끊겼다. RETRY_ERRORS 에 들지 않으므로 대기가 다시 보지 않는다.
    conftest 는 이 실패가 나면 남은 테스트를 돌리지 않고 실행을 멈춘다(모두 같은 이유로 오류가 되므로)."""


def session_lost(err):
    """err 가 '세션이 끊겨 다시 봐도 소용없는' 오류인가. 대기와 conftest 가 같은 기준을 쓴다."""
    if isinstance(err, (SessionLost, *SESSION_LOST_TYPES)):
        return True
    if isinstance(err, WebDriverException):
        text = str(err).lower()
        return any(marker in text for marker in SESSION_LOST_MESSAGES)
    return False


class WaitTimeout(AssertionError):
    """대기가 제한 시간을 넘김. last 는 마지막으로 check 가 돌려준 값, error 는 마지막으로 다시 본 예외."""

    def __init__(self, message, last=None, error=None):
        super().__init__(message)
        self.last = last
        self.error = error


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
            if session_lost(err):
                raise SessionLost(f"Appium 세션이 끊겨 {what}을(를) 더 기다리지 않는다: {_first_line(err)}") from err
            error = err
        finally:
            _state.depth -= 1
        time.sleep(interval)
    detail = f"마지막 값: {last!r}" if error is None else f"마지막 오류: {_describe(error)}"
    # 마지막 오류를 원인으로 이어 둔다: 실패 자료의 traceback 에서 어느 줄에서 났는지 바로 보인다
    raise WaitTimeout(f"{timeout:g}초 안에 {what}이(가) 맞지 않았다 ({detail})", last, error) from error


def _first_line(err):
    return (str(err).strip().splitlines() or [type(err).__name__])[0][:200]


def _describe(err):
    return f"{type(err).__name__}: {_first_line(err)}"


def wait_value(read, expected, timeout=10.0, interval=0.25, what="값"):
    """read() 가 expected 가 될 때까지 기다린다. 실패 메시지에 마지막으로 읽은 값을 남긴다
    (`wait_until(lambda: read() == expected)` 는 '마지막 값: False' 만 남아 실제 값을 실패 자료에서 찾아야 했다)."""
    seen = []

    def check():
        seen[:] = [read()]
        return seen[0] == expected

    try:
        return wait_until(check, timeout=timeout, interval=interval, what=f"{what} {expected!r}")
    except WaitTimeout as err:
        if not seen:
            raise
        # 값을 한 번 읽은 뒤 읽기 자체가 실패하기 시작했으면(adb 끊김 등) 그 오류도 함께 남긴다.
        # 값만 남기면 '22.0 에 머물렀다'로 읽혀, 실제 원인인 읽기 실패를 놓친다
        detail = f"마지막으로 읽은 값: {seen[0]!r}"
        if err.error is not None:
            detail += f", 그 뒤 읽기 오류: {_describe(err.error)}"
        raise WaitTimeout(f"{timeout:g}초 안에 {what}이(가) {expected!r}이(가) 되지 않았다 ({detail})",
                          seen[0], err.error) from err.error


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
