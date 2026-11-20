"""대기 함수: 다시 볼 예외와 바로 올릴 예외, 대기 중첩, '유지' 확인. 기기 없이 돈다."""
import time

import pytest
from selenium.common.exceptions import InvalidSessionIdException, NoSuchElementException, WebDriverException

from ivi.screens import Screen
from ivi.waits import SessionLost, polling, session_lost, stays, wait_until, wait_value


def test_retries_element_not_found_then_returns_value():
    tries = iter([NoSuchElementException("없음"), NoSuchElementException("없음"), "찾음"])

    def check():
        value = next(tries)
        if isinstance(value, Exception):
            raise value
        return value

    assert wait_until(check, timeout=2, interval=0.01) == "찾음"


def test_code_error_is_raised_at_once_not_after_timeout():
    """오타 같은 코드 오류는 10초를 기다린 뒤 '조건이 맞지 않았다'로 바뀌지 않고, 원래 예외로 바로 올라온다."""
    started = time.monotonic()
    with pytest.raises(AttributeError):
        wait_until(lambda: None.text, timeout=10, interval=0.01)  # noqa - 일부러 낸 코드 오류
    assert time.monotonic() - started < 1


def test_parse_errors_are_treated_as_not_yet():
    """화면 글자가 아직 숫자가 아닐 때('--')는 다시 본다."""
    texts = iter(["--", "", "22.5"])
    assert wait_until(lambda: float(next(texts)), timeout=2, interval=0.01) == 22.5


def test_wait_value_reports_last_value_read():
    with pytest.raises(AssertionError, match=r"마지막으로 읽은 값: 22\.8"):
        wait_value(lambda: 22.8, 22.5, timeout=0.2, interval=0.05, what="차량 온도")


def test_stays_catches_late_change():
    values = iter([22.0, 22.0, 22.0, 21.5, 22.0])
    with pytest.raises(AssertionError, match="유지되지 않았다"):
        stays(lambda: next(values) == 22.0, duration=1, interval=0.01)
    assert stays(lambda: True, duration=0.05, interval=0.01)


class _Driver:
    """요소가 없는 화면. find_element 호출 횟수를 센다."""

    def __init__(self):
        self.calls = 0

    def find_element(self, *_):
        self.calls += 1
        raise NoSuchElementException("없음")


def test_find_inside_wait_does_not_start_its_own_wait():
    """wait_text 처럼 대기 안에서 find 를 부르면 한 번만 찾는다. 전에는 안쪽 find 가 10초를 따로 기다려 최대 약 20초가 됐다."""
    driver = _Driver()
    screen = Screen(driver)
    started = time.monotonic()
    with pytest.raises(AssertionError):
        screen.wait_text("title", "홈", timeout=0.5)
    assert time.monotonic() - started < 2
    assert driver.calls >= 2  # 바깥 대기가 여러 번 다시 봤다
    assert not polling()      # 대기가 끝나면 원래대로


def test_session_lost_is_raised_at_once_not_after_timeout():
    """UiAutomator2 계측 프로세스가 죽은 응답은 다시 봐도 살아나지 않는다. 제한 시간을 쓰지 않고 SessionLost 로 바로 올린다
    (2026-11-19 막 켠 에뮬레이터에서 이 응답이 대기마다 제한 시간을 다 쓰며 이어졌다)."""
    calls = []

    def check():
        calls.append(1)
        raise WebDriverException("'GET /source' cannot be proxied to UiAutomator2 server because the instrumentation "
                                 "process is not running (probably crashed)")

    started = time.monotonic()
    with pytest.raises(SessionLost, match="Appium 세션이 끊겨") as caught:
        wait_until(check, timeout=10, interval=0.01, what="화면 요소 'source_badge'")
    assert time.monotonic() - started < 1 and len(calls) == 1
    assert isinstance(caught.value.__cause__, WebDriverException)  # 원래 응답은 원인으로 남는다


@pytest.mark.parametrize("err, lost", [
    (InvalidSessionIdException("invalid session id"), True),
    (WebDriverException("A session is either terminated or not started"), True),
    (NoSuchElementException("없음"), False),
    (WebDriverException("An unknown server-side error occurred"), False),
    (RuntimeError("adb: device offline"), False),
], ids=["invalid_session", "terminated", "no_element", "other_server_error", "adb"])
def test_session_lost_classification(err, lost):
    assert session_lost(err) is lost


def test_wait_value_keeps_read_error_after_last_value():
    """값을 한 번 읽은 뒤 읽기가 실패하기 시작하면, 마지막 값과 함께 그 오류도 남긴다 ('22.0 에 머묾'으로 읽히지 않게)."""
    reads = iter([22.0])

    def read():
        try:
            return next(reads)
        except StopIteration:
            raise RuntimeError("adb: device offline") from None

    with pytest.raises(AssertionError, match=r"마지막으로 읽은 값: 22\.0, 그 뒤 읽기 오류: RuntimeError: adb: device offline") as caught:
        wait_value(read, 22.5, timeout=0.2, interval=0.02, what="차량 온도")
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_timeout_keeps_last_error_as_cause():
    with pytest.raises(AssertionError, match="마지막 오류: NoSuchElementException") as caught:
        wait_until(lambda: (_ for _ in ()).throw(NoSuchElementException("없음")), timeout=0.1, interval=0.02)
    assert isinstance(caught.value.__cause__, NoSuchElementException)


def test_wait_value_session_lost_after_a_value_was_read():
    """값을 한 번 읽은 뒤 세션이 끊기면, '마지막 값' 메시지로 바꾸지 않고 세션 끊김을 바로 올린다 (원인은 이어 둔다)."""
    reads = iter([22.0])

    def read():
        try:
            return next(reads)
        except StopIteration:
            raise WebDriverException("instrumentation process is not running (probably crashed)") from None

    started = time.monotonic()
    with pytest.raises(SessionLost) as caught:
        wait_value(read, 22.5, timeout=5, interval=0.01, what="화면 운전석 온도")
    assert time.monotonic() - started < 1
    assert isinstance(caught.value.__cause__, WebDriverException)
