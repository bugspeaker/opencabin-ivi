"""앱 크래시·ANR 판정(ivi/crashes.py)과, 그 판정으로 테스트를 실패시키는 conftest 의 pytest_runtest_call 을 기기 없이 확인한다.

판정 함수는 logcat 출력 예시로 본다. 훅은 test_fixtures.py 처럼 pytest 를 따로 띄워, 진짜 tests/conftest.py 의 훅에
가짜 기기(logcat 출력만 정해 둔 adb)를 붙여 돌린다. 결과(passed/failed/xfailed)는 pytest 가 정하므로 흉내로는 확인할 수 없다."""
import json
import os
import subprocess
import sys
from pathlib import Path

from ivi.crashes import crash_message, find_app_crashes
from ivi.vehicle import PACKAGE

ROOT = Path(__file__).resolve().parent.parent

# 앱(dev.opencabin.ivi)의 FATAL EXCEPTION. 같은 시각에 다른 프로세스(1820)의 줄이 끼어 있다
APP_FATAL = """\
11-21 14:02:10.101  8123  8123 E AndroidRuntime: FATAL EXCEPTION: main
11-21 14:02:10.101  1820  1850 I ActivityManager: Process dev.opencabin.ivi (pid 8123) has died
11-21 14:02:10.102  8123  8123 E AndroidRuntime: Process: dev.opencabin.ivi, PID: 8123
11-21 14:02:10.102  8123  8123 E AndroidRuntime: java.lang.IllegalStateException: fan level 9
11-21 14:02:10.102  8123  8123 E AndroidRuntime: \tat dev.opencabin.ivi.hvac.HvacSpec.clamp(HvacSpec.kt:42)
"""

# 2026-11-19 태블릿 crash 버퍼에 실제로 남아 있던 Appium 서버의 크래시 (앱이 아니므로 보지 않는다)
APPIUM_FATAL = """\
11-19 09:55:03.956  6475  6499 E AndroidRuntime: FATAL EXCEPTION: Instr: androidx.test.runner.AndroidJUnitRunner
11-19 09:55:03.956  6475  6499 E AndroidRuntime: Process: io.appium.uiautomator2.server, PID: 6475
11-19 09:55:03.956  6475  6499 E AndroidRuntime: java.lang.RuntimeException: Error while disconnecting UiAutomation@ba514bb[id=-1, flags=0]
"""

APP_ANR = "11-21 14:03:00.500  1820  1851 E ActivityManager: ANR in dev.opencabin.ivi (dev.opencabin.ivi/.MainActivity)\n"
OTHER_ANR = "11-21 14:03:00.500  1820  1851 E ActivityManager: ANR in dev.opencabin.ivi.demo (dev.opencabin.ivi.demo/.Main)\n"
APP_SIGNAL = ("11-21 14:04:00.000  8200  8230 F libc    : Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), "
              "fault addr 0x0 in tid 8230 (RenderThread), pid 8200 (dev.opencabin.ivi)\n")
SYSTEMUI_SIGNAL = ("11-21 14:04:00.000  900  930 F libc    : Fatal signal 6 (SIGABRT), code -1 (SI_QUEUE) in tid 930 "
                   "(HwBinder), pid 900 (com.android.systemui)\n")


def test_finds_app_fatal_exception_with_its_own_lines_only():
    crashes = find_app_crashes(APP_FATAL, PACKAGE)
    assert len(crashes) == 1
    assert "Process: dev.opencabin.ivi, PID: 8123" in crashes[0]
    assert "HvacSpec.clamp" in crashes[0]
    assert "has died" not in crashes[0]   # 끼어든 다른 프로세스의 줄은 덩어리에 넣지 않는다


def test_ignores_other_processes_and_empty_log():
    assert find_app_crashes(APPIUM_FATAL, PACKAGE) == []
    assert find_app_crashes(OTHER_ANR + SYSTEMUI_SIGNAL, PACKAGE) == []
    assert find_app_crashes("", PACKAGE) == []
    assert find_app_crashes("--------- beginning of crash\n", PACKAGE) == []


def test_finds_anr_native_crash_and_sub_process():
    sub = APP_FATAL.replace("Process: dev.opencabin.ivi,", "Process: dev.opencabin.ivi:remote,")
    found = find_app_crashes(APPIUM_FATAL + APP_ANR + APP_SIGNAL + sub, PACKAGE)
    assert len(found) == 3
    assert "ANR in dev.opencabin.ivi" in found[0] and "Fatal signal 11" in found[1] and ":remote" in found[2]


def test_message_counts_and_points_to_artifact():
    message = crash_message(find_app_crashes(APP_FATAL + APP_ANR, PACKAGE))
    assert "logcat 2건" in message and "app_crash.txt" in message and "FATAL EXCEPTION: main" in message


CONFTEST = '''
import importlib.util, json, os
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("ivi_e2e_conftest", os.environ["IVI_REAL_CONFTEST"])
real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real)
pytest_runtest_setup = real.pytest_runtest_setup   # 테스트 시작 시각을 찍는다
pytest_runtest_call = real.pytest_runtest_call     # 진짜 판정 훅

REPORTS = []


class FakeAdb:
    log, fail, asked = "", False, []

    def log_mark(self):
        return "1700000000.000"

    def crash_log(self, since):
        self.asked.append(since)
        if self.fail:
            raise real.AdbError("adb logcat 실패 (기기 연결 끊김)")
        return self.log


class FakeDevice:
    def __init__(self):
        self.adb = FakeAdb()
        self.vehicle = type("V", (), {"observed": {}})()


def pytest_configure(config):
    config.ivi_device = FakeDevice()


@pytest.fixture(autouse=True)
def _log(request, pytestconfig):
    adb = pytestconfig.ivi_device.adb
    marker = request.node.get_closest_marker("log")
    adb.log = os.environ[marker.args[0]] if marker else ""
    adb.fail = request.node.get_closest_marker("adb_fails") is not None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        error = call.excinfo.value if call.excinfo else None
        REPORTS.append({"test": item.name, "outcome": report.outcome, "xfailed": hasattr(report, "wasxfail"),
                        "error": type(error).__name__ if error else "",
                        "cause": type(error.__cause__).__name__ if error is not None and error.__cause__ else "",
                        "message": str(error) if error else "", "props": [list(p) for p in report.user_properties],
                        "crashes": len(getattr(item, "ivi_app_crashes", []) or []),
                        "since": item.config.ivi_device.adb.asked[-1] if item.config.ivi_device.adb.asked else None})


def pytest_sessionfinish(session):
    Path(os.environ["IVI_FLOW_OUT"]).write_text(json.dumps(REPORTS), encoding="utf-8")
'''

TESTS = '''
import pytest
from ivi.defects import DefectReproduced
from ivi.waits import SessionLost


@pytest.mark.log("APP_LOG")
def test_passes_but_app_crashed():
    pass


@pytest.mark.log("APPIUM_LOG")
def test_passes_and_only_appium_crashed():
    pass


@pytest.mark.log("APP_LOG")
def test_fails_and_app_crashed():
    assert False, "버튼을 찾지 못함"


@pytest.mark.log("APP_LOG")
def test_session_lost_and_app_crashed():
    raise SessionLost("instrumentation process is not running")


@pytest.mark.log("APP_LOG")
@pytest.mark.xfail(strict=True, raises=DefectReproduced, reason="알려진 결함")
def test_known_defect_with_crash():
    raise DefectReproduced("22.3 에서 22.8 을 씀")


@pytest.mark.xfail(strict=True, raises=DefectReproduced, reason="알려진 결함")
def test_known_defect_without_crash():
    raise DefectReproduced("22.3 에서 22.8 을 씀")


@pytest.mark.log("APP_LOG")
def test_skipped_inside_test():
    pytest.skip("에뮬레이터에서만")


@pytest.mark.adb_fails
def test_log_cannot_be_read():
    pass
'''


def run_flow(tmp_path):
    (tmp_path / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp_path / "test_flow.py").write_text(TESTS, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    log(name)\n    adb_fails\n", encoding="utf-8")
    out = tmp_path / "flow.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT), "IVI_REAL_CONFTEST": str(ROOT / "tests" / "conftest.py"),
           "IVI_FLOW_OUT": str(out), "APP_LOG": APPIUM_FATAL + APP_FATAL, "APPIUM_LOG": APPIUM_FATAL,
           "PYTHONIOENCODING": "utf-8"}  # 자식 출력을 utf-8 로 읽는다. Python 3.12 Windows 는 기본이 cp949
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
                          cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8")
    assert out.exists(), proc.stdout + proc.stderr
    return {r["test"]: r for r in json.loads(out.read_text(encoding="utf-8"))}


def test_crash_fails_a_passing_test_and_is_read_from_test_start(tmp_path):
    flow = run_flow(tmp_path)
    crashed = flow["test_passes_but_app_crashed"]
    assert crashed["outcome"] == "failed" and crashed["error"] == "AppCrashed"
    assert "FATAL EXCEPTION: main" in crashed["message"] and crashed["crashes"] == 1
    assert crashed["since"] == "1700000000.000"   # 이 테스트를 시작한 시각부터 읽는다
    assert flow["test_passes_and_only_appium_crashed"]["outcome"] == "passed"   # 다른 앱의 크래시는 보지 않는다


def test_crash_keeps_original_failure_as_cause_but_not_session_loss(tmp_path):
    flow = run_flow(tmp_path)
    failed = flow["test_fails_and_app_crashed"]
    assert failed["error"] == "AppCrashed" and failed["cause"] == "AssertionError"
    # 세션 끊김은 그대로 둔다: 실패 자료의 session_lost 표시와 다음 시도의 세션 복구가 이 예외를 보고 움직인다
    lost = flow["test_session_lost_and_app_crashed"]
    assert lost["outcome"] == "failed" and lost["error"] == "SessionLost" and lost["crashes"] == 1


def test_crash_is_not_swallowed_as_known_defect(tmp_path):
    flow = run_flow(tmp_path)
    # 알려진 결함 증상이 재현됐어도 앱이 죽었다면 xfail 로 받지 않는다 (raises=DefectReproduced 에 맞지 않음)
    assert flow["test_known_defect_with_crash"]["outcome"] == "failed"
    assert not flow["test_known_defect_with_crash"]["xfailed"]
    assert flow["test_known_defect_without_crash"]["xfailed"]


def test_skip_and_unreadable_log_are_left_as_they_are(tmp_path):
    flow = run_flow(tmp_path)
    assert flow["test_skipped_inside_test"]["outcome"] == "skipped"
    unread = flow["test_log_cannot_be_read"]
    assert unread["outcome"] == "passed"
    assert any(p[0] == "crash_check" and "판정하지 못함" in p[1] for p in unread["props"])
