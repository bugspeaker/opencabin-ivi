"""원격 전원 제어로 에뮬레이터를 껐다 켠 뒤 부팅, 앱, 공조 기본값이 돌아오는지 확인합니다.

실제 벤치라면 전원 공급기나 릴레이로 헤드 유닛 전원을 끊는 자리다. 여기서는 EmulatorPower(ivi/power.py)가
에뮬레이터 프로세스를 끄고 같은 설정으로 다시 켠다. Appium 세션이 끊기므로 conftest 가 이 테스트를 맨 끝으로 보낸다.
"""
import pytest
from appium import webdriver

from ivi.power import EmulatorPower
from ivi.screens import IviApp
from ivi.vehicle import Seat
from ivi.waits import wait_value

BOOT_LIMIT = 180.0


@pytest.mark.req("BENCH-02")
@pytest.mark.timeout(600)  # 부팅과 새 Appium 세션까지 기다린다
@pytest.mark.aaos
@pytest.mark.power
@pytest.mark.regression
def test_power_cycle_brings_back_app_and_cabin_defaults(device, pytestconfig, request):
    """전원을 껐다 켜면 3분 안에 부팅이 끝나고, 앱이 다시 CarService에 붙으며, 공조는 기본값 22.0°C로 시작합니다.
    부팅에 걸린 시간은 결과에 남깁니다.
    """
    if not device.serial.startswith("emulator-"):
        pytest.skip("원격 전원은 에뮬레이터에서만 돌린다 (실기기는 재부팅만 된다)")
    power = EmulatorPower(device.serial, log_dir=pytestconfig.rootpath / "reports" / "logs")
    boot = power.cycle(timeout=BOOT_LIMIT + 60)
    request.node.user_properties.append(("boot_seconds", f"{boot:.1f}"))
    assert boot <= BOOT_LIMIT, f"부팅이 {boot:.0f}초 걸렸다"

    wait_value(lambda: device.adb.shell("am", "get-current-user").strip(), str(device.user), timeout=90,
               what="현재 사용자 (운전자 사용자 준비)")
    vehicle = device.vehicle
    vehicle.ensure_root()
    wait_value(lambda: (vehicle.temperature(Seat.DRIVER), vehicle.temperature(Seat.PASSENGER)), (22.0, 22.0),
               timeout=60, what="공조 기본값 (운전석, 조수석. VHAL 초기값)")

    # 이전 Appium 세션은 에뮬레이터와 함께 끊겼다. 새로 만들고, 결과 화면(--shots)도 이 세션으로 찍게 한다
    options = device.appium_options()
    port = pytestconfig.getoption("--system-port")
    if port:
        options.set_capability("appium:systemPort", port)
    session = webdriver.Remote(pytestconfig.getoption("--appium-url"), options=options)
    session.implicitly_wait(0)
    request.addfinalizer(session.quit)
    request.node.funcargs["driver"] = session

    screen = IviApp(session, tapper=device.tapper())
    device.launch(reset=True)
    wait_value(lambda: screen.text("source_badge"), "AAOS", timeout=90, what="데이터 소스 표시 (CarService 연결)")
    home = screen.home()
    wait_value(lambda: home.summary_temperature(Seat.DRIVER), 22.0, timeout=30, what="화면 운전석 온도")
