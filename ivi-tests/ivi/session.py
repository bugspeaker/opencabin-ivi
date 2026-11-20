"""Appium 세션이 끊기면 다음 테스트를 시작할 때 다시 붙인다.

세션은 실행 전체에서 하나를 쓴다(만드는 데 기기당 5~15초). 그런데 그 세션이 중간에 끊기면 그 뒤 테스트가 모두
준비 단계 오류가 된다. 2026-11-19 막 켠 AAOS 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽어
('UiAutomation returned null' → 'instrumentation process is not running') 129개가 모두 error 였다.

SessionHolder 는 테스트가 쓰는 드라이버 자리에 들어가서 모든 호출을 지금 세션으로 넘긴다.
테스트를 시작할 때 ensure_alive() 가 UiAutomator2 서버까지 가는 가벼운 요청(창 크기)으로 세션을 확인하고,
끊겨 있으면 닫고 새로 만든 뒤 그 이유를 돌려준다. conftest 는 이 이유를 결과에 session_restart 로 남긴다.
다시 붙인 일을 숨기지 않고 세는 것은 앱 재실행(app_relaunch), 신호 재시도(vhal_retry)와 같은 원칙이다.

새 세션을 만들다 실패하면 몇 초 간격으로 몇 번 더 해 본다(Appium 서버가 다시 뜨는 중일 수 있다).
그래도 안 되면(서버가 꺼져 있는 등) 마지막 오류가 그대로 올라가 그 테스트가 error 가 된다.
테스트 도중에 끊기면 그 시도는 실패하고, 재시도(--reruns)를 시작할 때 다시 붙는다. 재시도에서 통과하면 flaky 로 남는다.
"""
import time

from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import HTTPError as Urllib3Error

# 세션이 끊긴 것으로 보는 오류: Appium 이 돌려준 오류(세션 없음, 계측 프로세스 없음 등)와 Appium 서버에 닿지 못한 경우
DEAD_SESSION_ERRORS = (WebDriverException, OSError, Urllib3Error)


def _first_line(err):
    text = getattr(err, "msg", None) or str(err) or type(err).__name__
    return text.strip().splitlines()[0][:200] if text.strip() else type(err).__name__


class SessionHolder:
    """드라이버처럼 쓰는 세션 자리. factory() 는 새 Appium 세션을 만들어 돌려준다."""

    def __init__(self, factory, attempts=3, delay=3.0):
        self._factory = factory
        self._attempts, self._delay = attempts, delay
        self._session = factory()
        self.restarts = []  # 다시 붙인 이유 (실행 전체)

    @property
    def session(self):
        """지금 쓰고 있는 Appium 세션 (webdriver.Remote)."""
        return self._session

    def __getattr__(self, name):
        # 여기에 없는 속성(find_element, page_source, get_screenshot_as_png …)은 모두 지금 세션으로 넘긴다
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._session, name)

    def ensure_alive(self):
        """세션이 살아 있으면 None. 끊겨 있었으면 새로 만들고 그 이유를 돌려준다."""
        try:
            self._session.get_window_rect()  # UiAutomator2 서버를 거치는 가벼운 요청 (계측 프로세스가 죽으면 실패)
            return None
        except DEAD_SESSION_ERRORS as err:
            reason = f"{type(err).__name__}: {_first_line(err)}"
        self.quit_session()
        self._session = self._reconnect()
        self.restarts.append(reason)
        return reason

    def _reconnect(self):
        for attempt in range(1, self._attempts + 1):
            try:
                return self._factory()
            except DEAD_SESSION_ERRORS:
                if attempt == self._attempts:
                    raise
                time.sleep(self._delay)

    def quit_session(self):
        """지금 세션을 닫는다. 이미 끊겨 있어도 오류를 내지 않는다."""
        try:
            self._session.quit()
        except Exception:  # noqa: BLE001 - 끊긴 세션은 닫다가도 실패한다
            pass
