"""기기 E2E 공통 설정 (tests/ 아래에만 적용. unit/ 은 기기 없이 돈다).

기기 선택: --serial (또는 IVI_SERIAL). 비우면 연결된 기기가 1대일 때 그 기기를 쓴다.
기기 종류는 자동으로 판별한다 (android.hardware.type.automotive → AAOS, 아니면 Mock).

픽스처
  device   세션 하나에 기기 하나 (ivi.device.Device). 세션 시작 때 앱을 한 번 종료해 깨끗하게 시작
  driver   Appium 세션 (AAOS 전용 설정, 병렬 실행용 --system-port)
  app      테스트마다 저장 설정을 기본값으로(테스트 훅), 화면을 초기화(--activity-clear-task), 차량을 정차·기본 온도로. 끝나면 정차·값 복원
  car      app 과 함께 쓰는 차량 어댑터 (device.vehicle)
  vehicle  앱 없이 차량만 쓰는 테스트(1단계 spike)용

운영
  재시도   --reruns N (pytest-rerunfailures). 재시도에서 통과하면 'flaky' 로 기록
  격리     quarantine.txt 에 있는 테스트는 xfail(strict=False) → 돌리되 게이트를 막지 않음
  기록     reports/history/results.jsonl (누적), reports/runs/<run>-<serial>.json (이번 실행), JUnit
  실패자료 reports/artifacts/<테스트>[__재시도 n]/ 화면·UI 계층·차량 상태·액티비티·logcat (정리 전에 남김)
"""
import os
import re
import subprocess
import time
from pathlib import Path

import pytest
from appium import webdriver

from ivi import quarantine
from ivi.device import Device
from ivi.results import QUARANTINE_KEYWORD, Recorder
from ivi.screens import IviApp

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"
QUARANTINE_FILE = ROOT / "quarantine.txt"


def pytest_addoption(parser):
    group = parser.getgroup("ivi")
    group.addoption("--serial", default=os.environ.get("IVI_SERIAL"), help="대상 기기 (adb serial)")
    group.addoption("--appium-url", default=os.environ.get("APPIUM_URL", "http://127.0.0.1:4723"))
    group.addoption("--system-port", type=int, default=None,
                    help="UiAutomator2 systemPort. 같은 Appium 서버로 여러 기기를 동시에 돌릴 때 기기마다 달라야 한다")
    group.addoption("--run-id", default=os.environ.get("IVI_RUN_ID"), help="여러 기기 실행을 한 묶음으로 기록할 때")


def _connected_serials():
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("device")]


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.option.help or config.option.collectonly:
        return
    serial = config.getoption("--serial")
    if not serial:
        serials = _connected_serials()
        if len(serials) != 1:
            raise pytest.UsageError(f"연결된 기기가 {len(serials)}대입니다. --serial 로 고르세요: {serials}")
        serial = serials[0]
    device = Device.connect(serial)
    config.ivi_device = device
    run_id = config.getoption("--run-id") or time.strftime("%Y%m%d-%H%M%S")
    config.ivi_recorder = Recorder(run_id, {"serial": serial, "kind": device.kind, "model": device.model})
    config.pluginmanager.register(config.ivi_recorder, "ivi_recorder")  # pytest_runtest_logreport 를 받는다
    if not config.option.xmlpath:
        config.option.xmlpath = str(REPORT_DIR / f"junit-{device.kind}-{serial}.xml")


def pytest_report_header(config):
    device = getattr(config, "ivi_device", None)
    if device:
        return f"ivi device: {device.serial} ({device.label}, user {device.user}, tap {device.tap_mode})"


def pytest_collection_modifyitems(config, items):
    entries = quarantine.load(QUARANTINE_FILE)
    device = getattr(config, "ivi_device", None)
    for item in items:
        if device is not None and "aaos" in item.keywords and not device.automotive:
            item.add_marker(pytest.mark.skip(reason=f"AAOS 전용 (현재 기기: {device.label})"))
        entry = quarantine.find(entries, item.nodeid)
        if entry:
            item.add_marker(getattr(pytest.mark, QUARANTINE_KEYWORD))
            item.add_marker(pytest.mark.xfail(strict=False, reason=f"격리({entry.since}): {entry.reason}"))


def pytest_runtest_setup(item):
    device = getattr(item.config, "ivi_device", None)
    if device:
        device.adb.logcat_clear()  # 실패 때 이 테스트의 로그만 남도록


def pytest_sessionfinish(session, exitstatus):
    recorder = getattr(session.config, "ivi_recorder", None)
    if recorder and recorder.records:
        summary, run_file = recorder.write(REPORT_DIR)
        session.config.ivi_summary = (summary, run_file)


def pytest_terminal_summary(terminalreporter, config):
    result = getattr(config, "ivi_summary", None)
    if result:
        summary, run_file = result
        counts = ", ".join(f"{key} {value}" for key, value in sorted(summary["counts"].items()))
        terminalreporter.write_sep("-", "ivi run")
        terminalreporter.write_line(f"{summary['kind']}:{summary['serial']}  gate={summary['gate']}  {counts}  "
                                    f"relaunch {summary['relaunches']}  vhal_retry {summary.get('infra_retries', 0)}  ({summary['duration']}s)")
        terminalreporter.write_line(f"기록: {run_file}")


# ---------------- 픽스처 ----------------

@pytest.fixture(scope="session")
def device(pytestconfig):
    device = pytestconfig.ivi_device
    device.stop_app()  # 세션마다 한 번만 프로세스를 새로 시작한다
    return device


@pytest.fixture(scope="session")
def driver(device, pytestconfig):
    options = device.appium_options()
    port = pytestconfig.getoption("--system-port")
    if port:
        options.set_capability("appium:systemPort", port)
    session = webdriver.Remote(pytestconfig.getoption("--appium-url"), options=options)
    session.implicitly_wait(0)  # 기다림은 화면 객체가 명시적으로 한다
    if device.automotive:
        session.update_settings({"enableMultiWindows": True})  # SystemUI(하단 HVAC 바)도 보이게
    yield session
    session.quit()


@pytest.fixture
def app(device, driver, request):
    screen = IviApp(driver, tapper=device.tapper())
    _start_app(device, screen, request)
    # 저장 설정을 기본값으로 (테스트끼리 영향 없게). 앱을 띄운 **뒤에** 부른다:
    # 화웨이는 꺼져 있는 앱에는 브로드캐스트를 전달하지 않는다 (logcat 'targets O+, restricted', 6단계에서 발견)
    device.reset_app_state()
    device.vehicle.prepare()
    yield screen
    device.vehicle.cleanup()
    _record_retries(device, request)


def _start_app(device, screen, request, attempts=2):
    """화면을 초기화해서 띄운다. 프로세스는 죽이지 않는다 (3단계: 화웨이 iAware 가 종료·실행 반복을 '반복 크래시'로 보고
    앱을 강제 종료했다 → 테스트마다 -S 를 쓰던 방식을 세션 시작 1회로 바꿈).
    그래도 앱이 화면에 없으면 프로세스까지 새로 띄우고, 그 사실을 JUnit property(app_relaunch)로 남긴다."""
    for attempt in range(1, attempts + 1):
        device.launch(reset=True, fresh=attempt > 1)
        try:
            screen.find("source_badge")
            return
        except AssertionError:
            if attempt == attempts:
                raise
            top = ", ".join(device.adb.resumed_activities()) or "-"
            request.node.user_properties.append(("app_relaunch", f"{attempt}회차에 앱이 화면에 없음 (맨 위: {top})"))


@pytest.fixture
def car(app, device):
    return device.vehicle


@pytest.fixture
def vehicle(device, request):
    device.vehicle.prepare()
    yield device.vehicle
    device.vehicle.cleanup()
    _record_retries(device, request)


def _record_retries(device, request):
    """신호 주입 도구(VHAL)를 다시 시도한 일이 있으면 JUnit property(vhal_retry)로 남긴다. 숨기지 않고 통계로 본다."""
    for note in device.vehicle.retried:
        request.node.user_properties.append(("vhal_retry", note))
    device.vehicle.retried.clear()


# ---------------- 실패 자료 ----------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    # 정리(teardown) 전에 남겨야 실패 순간의 화면·차량 상태가 보인다. 재시도로 사라질 실패도 남긴다 (flaky 원인 분석용)
    # 정리 단계 실패(예: 정차로 되돌리는 VHAL 쓰기 실패)도 남긴다 — 5단계에서 이 경우 자료가 없어 원인 추적이 늦었다
    if report.failed:
        folder = _save_artifacts(item, suffix="__teardown" if report.when == "teardown" else "")
        if folder:
            report.sections.append(("ivi artifacts", str(folder)))


def _save_artifacts(item, suffix=""):
    device = getattr(item.config, "ivi_device", None)
    if device is None:
        return None
    name = re.sub(r"[^\w.\-\[\]]+", "_", item.nodeid)[:150]
    attempt = getattr(item, "execution_count", 1)  # pytest-rerunfailures 가 붙이는 시도 번호
    folder = REPORT_DIR / "artifacts" / ((name if attempt == 1 else f"{name}__try{attempt}") + suffix)
    folder.mkdir(parents=True, exist_ok=True)
    driver = item.funcargs.get("driver")

    def save(file_name, produce):
        try:
            content = produce()
            path = folder / file_name
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        except Exception as err:  # noqa: BLE001 - 자료 수집 실패가 원래 실패를 가리지 않게
            (folder / f"{file_name}.error.txt").write_text(f"{type(err).__name__}: {err}", encoding="utf-8")

    if driver is not None:
        save("screen.png", driver.get_screenshot_as_png)
        save("page_source.xml", lambda: driver.page_source)
    save("vehicle.txt", device.vehicle.dump)
    save("activities.txt", lambda: "\n".join(device.adb.resumed_activities()))
    save("logcat.txt", device.adb.logcat_dump)
    return folder
