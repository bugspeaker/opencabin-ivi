"""기기 E2E 공통 설정 (tests/ 아래에만 적용. unit/ 은 기기 없이 돈다).

기기 선택: --serial (또는 IVI_SERIAL). 비우면 연결된 기기가 1대일 때 그 기기를 쓴다.
기기 종류는 자동으로 판별한다 (android.hardware.type.automotive → AAOS, 아니면 Mock).

픽스처
  device   세션 하나에 기기 하나 (ivi.device.Device). 세션 시작 때 앱을 한 번 종료해 깨끗하게 시작
  driver   Appium 세션 (AAOS 전용 설정, 병렬 실행용 --system-port). 실행 전체에서 하나를 쓰고, 끊기면 다음 테스트 시작 때 다시 붙인다
  app      테스트마다 저장 설정을 기본값으로(테스트 훅), 화면을 초기화(--activity-clear-task), 차량을 정차·기본 온도로. 끝나면 정차·값 복원
           (정리는 준비보다 먼저 등록한다. 준비가 중간에 실패해도 차량을 되돌린다)
  car      app 과 함께 쓰는 차량 어댑터 (device.vehicle)
  vehicle  앱 없이 차량만 쓰는 테스트(1단계 spike)용

운영
  재시도   --reruns N (pytest-rerunfailures). 재시도에서 통과하면 'flaky' 로 기록
  세션     Appium 세션이 끊겨 있으면 테스트 시작 전에 다시 붙이고 'session_restart' 로 기록 (ivi/session.py)
  격리     quarantine.txt 에 있는 테스트는 xfail(strict=False) → 돌리되 게이트를 막지 않음
  기기전용 aaos 마커는 태블릿(Mock)에서, tablet 마커는 AAOS 에서 건너뜀. Release 게이트는 이 두 경우 말고 건너뛴 테스트를 막는다
  크래시   테스트 도중 앱이 죽었거나 ANR 이 나면(logcat crash·system 버퍼, ivi/crashes.py) 화면 판정이 통과해도 그 테스트를 실패로 한다.
           다음 테스트의 am start 가 앱을 다시 띄우므로 화면만 봐서는 알 수 없다
  세션끊김 테스트 도중 세션이 끊기면 대기가 제한 시간을 쓰지 않고 바로 실패시킨다(ivi.waits.SessionLost). 그 실패는 그대로
           남고, 다음 시도(재시도 포함)를 시작할 때 위 '세션' 이 다시 붙인다. 실패 자료에 세션 끊김이라고 적는다
  기록     reports/history/results.jsonl (누적), reports/runs/<run>-<serial>.json (이번 실행: 커밋, 종료 코드, 수집 수 포함), JUnit
  실패자료 reports/artifacts/<테스트>[__재시도 n]/ 화면·UI 계층·차량 상태·액티비티·logcat·앱 크래시(app_crash.txt, 있을 때) (정리 전에 남김)
  결과화면 --shots 를 주면 통과한 테스트도 끝 화면을 reports/shots/<run>-<serial>/ 에 남긴다 (tools/publish_results.py 가 사이트로 옮긴다)
"""
import os
import re
import subprocess
import time
from pathlib import Path

import pytest
from appium import webdriver

from ivi import quarantine
from ivi.adb import AdbError
from ivi.crashes import AppCrashed, crash_message, find_app_crashes
from ivi.device import Device
from ivi.vehicle import PACKAGE
from ivi.results import QUARANTINE_KEYWORD, Recorder, code_version, junit_name
from ivi.screens import IviApp
from ivi.session import SessionHolder
from ivi.waits import session_lost

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
    group.addoption("--shots", action="store_true", default=os.environ.get("IVI_SHOTS") == "1",
                    help="테스트마다 끝 화면 스크린샷을 남긴다 (결과 페이지용)")


def _connected_serials():
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("\tdevice")]  # run_bench 와 같은 기준


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
    # 어느 코드와 어느 빌드로, 어떤 명령으로 돈 결과인지 남긴다. Release 게이트가 회차·기기마다 같은 커밋, 같은 APK 인지 본다
    config.ivi_recorder = Recorder(run_id, {"serial": serial, "kind": device.kind, "model": device.model},
                                   code={**code_version(ROOT), "app": device.adb.app_identity(PACKAGE),
                                         "command": " ".join(["pytest", *config.invocation_params.args]),
                                         "launcher": os.environ.get("IVI_LAUNCHER", "")})
    config.pluginmanager.register(config.ivi_recorder, "ivi_recorder")  # pytest_runtest_logreport 를 받는다
    if not config.option.xmlpath:
        config.option.xmlpath = str(REPORT_DIR / junit_name(run_id, device.kind, serial))


def pytest_report_header(config):
    device = getattr(config, "ivi_device", None)
    if device:
        return f"ivi device: {device.serial} ({device.label}, user {device.user}, tap {device.tap_mode})"


def pytest_collection_modifyitems(config, items):
    # 전원을 껐다 켜는 테스트는 Appium 세션을 끊으므로 맨 끝에 돌린다
    items.sort(key=lambda item: "power" in item.keywords)
    entries = quarantine.load(QUARANTINE_FILE)
    device = getattr(config, "ivi_device", None)
    for item in items:
        if device is not None and "aaos" in item.keywords and not device.automotive:
            item.add_marker(pytest.mark.skip(reason=f"AAOS 전용 (현재 기기: {device.label})"))
        if device is not None and "tablet" in item.keywords and device.automotive:
            item.add_marker(pytest.mark.skip(reason=f"태블릿(Mock) 전용 (현재 기기: {device.label})"))
        entry = quarantine.find(entries, item.nodeid)
        if entry:
            item.add_marker(getattr(pytest.mark, QUARANTINE_KEYWORD))
            item.add_marker(pytest.mark.xfail(strict=False, reason=f"격리({entry.since}): {entry.reason}"))


def pytest_runtest_setup(item):
    device = getattr(item.config, "ivi_device", None)
    if device:
        # 실패 때 이 테스트의 로그만 남도록 시작 시각을 찍어 둔다. 버퍼를 지우지(logcat -c) 않는다:
        # 같은 기기를 쓰는 다른 도구나 사람의 로그까지 지우기 때문 (재시도하면 그 시도의 시작 시각으로 바뀐다)
        item.ivi_log_since = device.adb.log_mark()


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    """테스트 본문을 감싼다. 앞: 준비 단계에서 읽은 차량 값을 지운다. 뒤: 앱이 테스트 도중 죽었는지 logcat 으로 본다.
    크래시가 있으면 테스트가 통과했어도 AppCrashed 로 실패시키고, 다른 이유로 실패했으면 원래 실패를 원인으로 이어 붙인다.
    세션 끊김 실패는 그대로 둔다(다음 시도가 세션을 다시 붙이는 표시를 지우지 않게). 크래시 기록은 어느 경우든 실패 자료에 남긴다."""
    device = getattr(item.config, "ivi_device", None)
    if device is None:
        return (yield)
    device.vehicle.observed.clear()  # 준비 단계에서 읽은 값은 판정이 아니다
    item.ivi_app_crashes = []  # 재시도하면 같은 item 이 다시 돈다. 앞 시도의 기록이 이번 실패 자료에 섞이지 않게
    try:
        result = yield
    except Exception as err:  # 테스트 실패. skip·xfail 호출(OutcomeException)과 중단은 Exception 이 아니라 여기 오지 않는다
        crashes = _app_crashes(item, device)
        if crashes and not session_lost(err):
            raise AppCrashed(crash_message(crashes)) from err
        raise
    crashes = _app_crashes(item, device)
    if crashes:
        raise AppCrashed(crash_message(crashes))
    return result


def _app_crashes(item, device):
    """이 테스트를 시작한 뒤 이 앱의 크래시·ANR (ivi/crashes.py). 로그를 읽지 못하면 판정하지 못했다고 결과에 남기고 넘어간다."""
    try:
        crashes = find_app_crashes(device.adb.crash_log(getattr(item, "ivi_log_since", None)), PACKAGE)
    except (AdbError, OSError, subprocess.SubprocessError) as err:
        item.user_properties.append(("crash_check", f"logcat 을 읽지 못해 크래시를 판정하지 못함: {err}"))
        return []
    item.ivi_app_crashes = crashes
    return crashes


def pytest_sessionfinish(session, exitstatus):
    recorder = getattr(session.config, "ivi_recorder", None)
    if recorder:
        # 테스트가 하나도 돌지 않았어도(수집 오류, 0개 선택) 파일을 남긴다. 파일이 없으면 '왜 없는지'를 알 수 없다
        summary, run_file = recorder.write(REPORT_DIR, exitstatus=int(exitstatus), collected=session.testscollected)
        session.config.ivi_summary = (summary, run_file)


def pytest_terminal_summary(terminalreporter, config):
    result = getattr(config, "ivi_summary", None)
    if result:
        summary, run_file = result
        counts = ", ".join(f"{key} {value}" for key, value in sorted(summary["counts"].items()))
        terminalreporter.write_sep("-", "ivi run")
        terminalreporter.write_line(f"{summary['kind']}:{summary['serial']}  gate={summary['gate']}  {counts}  "
                                    f"relaunch {summary['relaunches']}  vhal_retry {summary.get('infra_retries', 0)}  "
                                    f"session_restart {summary.get('session_restarts', 0)}  ({summary['duration']}s)")
        for problem in summary.get("problems", []):
            terminalreporter.write_line(f"  게이트 실패 이유: {problem}")
        terminalreporter.write_line(f"기록: {run_file}")


# ---------------- 픽스처 ----------------

@pytest.fixture(scope="session")
def device(pytestconfig):
    device = pytestconfig.ivi_device
    device.stop_app()  # 세션마다 한 번만 프로세스를 새로 시작한다
    return device


@pytest.fixture(scope="session")
def driver(device, pytestconfig):
    """Appium 세션 자리(SessionHolder). 테스트는 webdriver 처럼 쓰고, 끊긴 세션은 _appium_session_alive 가 다시 붙인다."""
    holder = SessionHolder(lambda: _new_session(device, pytestconfig))
    yield holder
    holder.quit_session()  # 전원 테스트가 기기를 껐다 켜면 이 세션은 이미 끊겨 있다 (오류 없이 넘어간다)


def _new_session(device, pytestconfig):
    options = device.appium_options()
    port = pytestconfig.getoption("--system-port")
    if port:
        options.set_capability("appium:systemPort", port)
    session = webdriver.Remote(pytestconfig.getoption("--appium-url"), options=options)
    try:
        session.implicitly_wait(0)  # 기다림은 화면 객체가 명시적으로 한다
        if device.automotive:
            session.update_settings({"enableMultiWindows": True})  # SystemUI(하단 HVAC 바)도 보이게
    except Exception:
        # 설정 중에 실패하면 Appium 세션이 남아 다음 실행이 막히지 않게 여기서 닫는다
        session.quit()
        raise
    return session


@pytest.fixture(autouse=True)
def _appium_session_alive(request):
    """드라이버를 쓰는 테스트마다 시작 전에 Appium 세션을 확인하고, 끊겼으면 다시 붙인다.
    2026-11-19: 막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽자 세션 하나에 묶인 뒤의 테스트가 모두 error 였다.
    다시 붙인 일은 숨기지 않고 JUnit property(session_restart)와 결과 기록에 남긴다."""
    if "driver" not in request.fixturenames:
        return
    reason = request.getfixturevalue("driver").ensure_alive()
    if reason:
        request.node.user_properties.append(("session_restart", reason))


@pytest.fixture
def app(device, driver, request):
    screen = IviApp(driver, tapper=device.tapper())
    # 차량 정리를 준비보다 **먼저** 등록한다. yield 뒤에 두면 준비가 중간에 실패했을 때(예: 정차는 했는데 신호 기준값
    # 쓰기 실패) 정리가 돌지 않아, 다음 테스트가 앞 테스트의 차량 상태로 시작한다. finalizer 는 teardown 에 돌므로
    # 실패 자료(pytest_runtest_makereport)는 정리 전 상태 그대로 남는다
    request.addfinalizer(lambda: _cleanup_vehicle(device, request))
    _start_app(device, screen, request)
    # 저장 설정을 기본값으로 (테스트끼리 영향 없게). 앱을 띄운 **뒤에** 부른다:
    # 화웨이는 꺼져 있는 앱에는 브로드캐스트를 전달하지 않는다 (logcat 'targets O+, restricted', 6단계에서 발견)
    device.reset_app_state()
    device.vehicle.prepare()
    return screen


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
    request.addfinalizer(lambda: _cleanup_vehicle(device, request))  # app 과 같은 이유로 준비보다 먼저
    device.vehicle.prepare()
    return device.vehicle


def _cleanup_vehicle(device, request):
    """정차·값 복원. 실패하면 teardown 오류로 남지만(결과 기록은 준비 단계의 원래 오류를 지우지 않는다), 재시도 기록은 옮긴다.
    정리가 실패한 뒤에도 실행은 이어 간다. 다음 테스트의 준비(prepare)가 정차, 온도, 신호 12종을 모두 기준값으로 다시 쓰기 때문이다.
    그 준비마저 실패하면 그 테스트가 준비 단계 오류가 되고, 어느 쪽이든 Release 게이트는 막는다 (unit/test_fixtures.py)."""
    try:
        device.vehicle.cleanup()
    finally:
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
    # 테스트 중 마지막으로 읽은 차량 값 (AAOS 의 CarService 로 읽은 VHAL 값, 최대 3개). assert 의 증거 전체는 아니다. 결과 페이지에서 화면 옆에 보여 준다
    if report.when == "call":
        device = getattr(item.config, "ivi_device", None)
        if device is not None:
            report.user_properties.extend(("vhal", value) for value in device.vehicle.take_observed())
    # 정리(teardown) 전에 남겨야 실패 순간의 화면·차량 상태가 보인다. 재시도로 사라질 실패도 남긴다 (flaky 원인 분석용)
    # 정리 단계 실패(예: 정차로 되돌리는 VHAL 쓰기 실패)도 남긴다 — 5단계에서 이 경우 자료가 없어 원인 추적이 늦었다
    if report.failed:
        folder = _save_artifacts(item, suffix="" if report.when == "call" else f"__{report.when}")
        if folder:
            report.sections.append(("ivi artifacts", str(folder)))
        # 세션이 끊긴 실패는 실패 자료 폴더에 표시해 둔다. 다음 시도를 시작할 때 _appium_session_alive 가 세션을 다시 붙인다.
        # 실행을 멈추지는 않는다: 다시 붙인 뒤의 테스트는 정상으로 돌 수 있고(2026-11-20 확인), 끊긴 시도는 failed·flaky 로
        # 남아 Release 게이트가 막는다
        if folder and call.excinfo is not None and session_lost(call.excinfo.value):
            (folder / "session_lost.txt").write_text(f"{type(call.excinfo.value).__name__}: {call.excinfo.value}", encoding="utf-8")
    # 결과 페이지용 끝 화면: 판정이 난 직후, 정리 전에 찍는다 (정리가 화면을 처음 상태로 돌리기 전)
    if report.when == "call" and item.config.getoption("--shots", default=False):
        shot = _save_result_shot(item)
        if shot:
            report.user_properties.append(("shot", str(shot)))


def _save_result_shot(item):
    """끝 화면 한 장. 재시도가 있으면 마지막 시도의 화면으로 덮어쓴다. 실패해도 테스트 결과에는 영향을 주지 않는다."""
    driver = item.funcargs.get("driver")
    recorder = getattr(item.config, "ivi_recorder", None)
    if driver is None or recorder is None:
        return None
    folder = REPORT_DIR / "shots" / f"{recorder.run_id}-{recorder.device['serial']}"
    path = folder / (re.sub(r"[^\w.\-\[\]]+", "_", item.nodeid)[:150] + ".png")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_bytes(driver.get_screenshot_as_png())
        return path
    except Exception:  # noqa: BLE001 - 스크린샷 실패가 테스트 판정을 바꾸지 않게
        return None


def _save_artifacts(item, suffix=""):
    device = getattr(item.config, "ivi_device", None)
    if device is None:
        return None
    name = re.sub(r"[^\w.\-\[\]]+", "_", item.nodeid)[:150]
    attempt = getattr(item, "execution_count", 1)  # pytest-rerunfailures 가 붙이는 시도 번호
    # 실행 · 기기별 폴더: 두 기기를 병렬로 돌리면 같은 테스트의 실패 자료가 서로 덮어쓰던 문제 (2026-11-18 발견)
    recorder = getattr(item.config, "ivi_recorder", None)
    run = f"{recorder.run_id}-{device.serial}" if recorder else device.serial
    folder = REPORT_DIR / "artifacts" / run / ((name if attempt == 1 else f"{name}__try{attempt}") + suffix)
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
    save("logcat.txt", lambda: device.adb.logcat_dump(since=getattr(item, "ivi_log_since", None)))
    crashes = getattr(item, "ivi_app_crashes", None)
    if crashes:
        save("app_crash.txt", lambda: "\n\n".join(crashes))
    return folder
