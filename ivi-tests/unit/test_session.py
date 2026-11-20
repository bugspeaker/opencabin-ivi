"""Appium 세션 다시 붙이기(ivi/session.py)와 그 기록을 기기 없이 검증한다."""
import json

import pytest
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from urllib3.exceptions import MaxRetryError

from ivi.results import Recorder
from ivi.session import SessionHolder
from tools import flaky_report

from test_operations import _rows, run  # unit/ 는 패키지가 아니라 pytest 가 이 폴더를 경로에 넣는다

CRASHED = WebDriverException("'GET /session/abc/window/rect' cannot be proxied to UiAutomator2 server because the "
                             "instrumentation process is not running (probably crashed). Check the server log")


class FakeSession:
    """Appium 세션 흉내: error 가 있으면 UiAutomator2 를 거치는 요청이 그 오류로 실패한다."""

    def __init__(self, name, error=None, quit_error=None):
        self.name, self.error, self.quit_error = name, error, quit_error
        self.quit_called = False

    def get_window_rect(self):
        if self.error:
            raise self.error
        return {"x": 0, "y": 0, "width": 1024, "height": 768}

    def find_element(self, by, value):
        return f"{self.name}:{value}"

    def quit(self):
        self.quit_called = True
        if self.quit_error:
            raise self.quit_error


class Factory:
    def __init__(self, *sessions):
        self.sessions = list(sessions)
        self.made = []

    def __call__(self):
        session = self.sessions.pop(0)
        if isinstance(session, Exception):
            raise session
        self.made.append(session)
        return session


def test_calls_go_to_the_current_session():
    holder = SessionHolder(Factory(FakeSession("s1")))
    assert holder.find_element("id", "source_badge") == "s1:source_badge"
    assert holder.session.name == "s1"


def test_alive_session_is_kept():
    factory = Factory(FakeSession("s1"), FakeSession("s2"))
    holder = SessionHolder(factory)
    assert holder.ensure_alive() is None
    assert [s.name for s in factory.made] == ["s1"] and holder.restarts == []


@pytest.mark.parametrize("error, kind", [
    (CRASHED, "WebDriverException"),                                        # UiAutomator2 계측 프로세스가 죽음 (2026-11-19)
    (InvalidSessionIdException("A session is either terminated or not started"), "InvalidSessionIdException"),  # Appium 서버가 다시 뜸
    (MaxRetryError(None, "/session/abc/window/rect", "Connection refused"), "MaxRetryError"),                  # 잠깐 닿지 않음
], ids=["instrumentation_crashed", "session_gone", "server_unreachable"])
def test_dead_session_is_replaced_and_reason_returned(error, kind):
    dead = FakeSession("s1", error=error, quit_error=error)  # 끊긴 세션은 닫다가도 실패한다
    holder = SessionHolder(Factory(dead, FakeSession("s2")))

    reason = holder.ensure_alive()

    assert reason.startswith(f"{kind}: ")
    assert dead.quit_called
    assert holder.find_element("id", "x") == "s2:x"  # 이후 호출은 새 세션으로
    assert holder.restarts == [reason]
    assert holder.ensure_alive() is None  # 새 세션이 살아 있으면 다시 만들지 않는다


def test_crash_reason_keeps_the_first_line_of_the_appium_message():
    holder = SessionHolder(Factory(FakeSession("s1", error=CRASHED), FakeSession("s2")))
    assert "instrumentation process is not running" in holder.ensure_alive()


def test_reconnect_waits_for_a_restarting_server(monkeypatch):
    """Appium 서버가 다시 뜨는 중이면 몇 번 더 해 본다."""
    waits = []
    monkeypatch.setattr("ivi.session.time.sleep", waits.append)
    refused = MaxRetryError(None, "/session", "Connection refused")
    factory = Factory(FakeSession("s1", error=refused), refused, FakeSession("s2"))
    holder = SessionHolder(factory, attempts=3, delay=3.0)
    assert holder.ensure_alive().startswith("MaxRetryError")
    assert holder.session.name == "s2" and waits == [3.0]


def test_failure_to_make_a_new_session_is_raised(monkeypatch):
    """끝내 다시 붙이지 못하면(Appium 서버가 꺼짐) 숨기지 않고 그 테스트를 error 로 만든다."""
    monkeypatch.setattr("ivi.session.time.sleep", lambda _: None)
    gone = WebDriverException("Could not start a new session")
    holder = SessionHolder(Factory(FakeSession("s1", error=CRASHED), gone, gone, gone), attempts=3)
    with pytest.raises(WebDriverException, match="Could not start a new session"):
        holder.ensure_alive()


def test_code_errors_are_not_treated_as_a_dead_session():
    holder = SessionHolder(Factory(FakeSession("s1", error=TypeError("코드 오류")), FakeSession("s2")))
    with pytest.raises(TypeError):
        holder.ensure_alive()


def test_private_names_are_not_forwarded():
    holder = SessionHolder(Factory(FakeSession("s1")))
    with pytest.raises(AttributeError):
        holder._not_there  # noqa: B018 - 속성 접근 자체를 시험한다


def test_recorder_counts_session_restart():
    recorder = Recorder("run1", {"serial": "s1", "kind": "aaos", "model": "m"})
    props = [("session_restart", "WebDriverException: instrumentation process is not running")]
    run(recorder, "t::a", ("setup", "passed", {"props": props}), ("call", "passed", {"props": props}),
        ("teardown", "passed", {"props": props}))
    run(recorder, "t::b", ("setup", "passed", {}), ("call", "passed", {}), ("teardown", "passed", {}))
    rec = recorder.records["t::a"]
    assert rec["session_restarts"] == 1 and "instrumentation" in rec["session_restart_reason"]
    assert recorder.records["t::b"]["session_restarts"] == 0
    summary = recorder.summary()
    assert summary["session_restarts"] == 1 and summary["gate"] == "pass"  # 다시 붙여서 통과했으면 게이트는 막지 않는다


def test_flaky_report_shows_session_restarts(tmp_path):
    rows = _rows("aaos", "t::a", ["passed", "passed"])
    rows[1]["session_restarts"] = 1
    history = tmp_path / "results.jsonl"
    history.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    out = tmp_path / "report.md"
    flaky_report.main(["--history", str(history), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "| aaos | 2 | 2/2 (100%) | 2 | 0 | 0 | 1 |" in text  # 실행 요약의 세션 재연결 열
    assert "| aaos | `t::a` | 2 | 0 | 0 | 0% | 0 | 0 | 1 |" in text  # 불안정 테스트 표에도 올라온다
