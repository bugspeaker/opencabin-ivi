"""대기 함수: 다시 볼 예외와 바로 올릴 예외, 대기 중첩, '유지' 확인. 기기 없이 돈다."""
import time

import pytest
from selenium.common.exceptions import NoSuchElementException

from ivi.screens import Screen
from ivi.waits import polling, stays, wait_until, wait_value


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
