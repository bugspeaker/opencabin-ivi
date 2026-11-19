"""Test Bench REST API로 차량 신호를 넣고 읽으면서 앱 화면이 따라오는지 확인합니다.

API 서버(ivi/bench_api.py)를 이 테스트 프로세스 안에 띄우고 HTTP로 부른다. adb 명령을 모르는 도구나 CI도
같은 방법으로 벤치 기기를 다룰 수 있다는 것을 보여 주려는 테스트다.
"""
import pytest

from ivi.bench_api import Bench, BenchDevice, call, serve_in_thread
from ivi.vehicle import CABIN_DEFAULTS, Signal
from ivi.waits import wait_until, wait_value


@pytest.fixture
def bench(app, device):
    api = Bench([BenchDevice(device.serial, device.kind, device.model, device.vehicle)])
    server, url = serve_in_thread(api)
    yield url, device.serial
    server.shutdown()


@pytest.mark.req("BENCH-01", "DRIVE-01")
@pytest.mark.sanity
def test_api_signals_drive_the_screen(app, bench):
    """REST API로 기어 D와 속도 50 km/h를 넣으면 화면 속도가 50이 되고 주행 제한 배지가 뜹니다.
    API로 다시 읽은 신호에도 주행 중으로 나옵니다.
    """
    url, serial = bench
    home = app.home()
    status, reply = call(url, "POST", f"/api/devices/{serial}/signals", {"gear": "D", "speed_kmh": 50})
    assert status == 200, reply
    home.wait_text("speed_value", "50")
    app.wait_visible("restriction_banner")
    status, reply = call(url, "GET", f"/api/devices/{serial}/signals")
    assert status == 200 and reply["signals"]["restricted"] is True

    assert call(url, "POST", f"/api/devices/{serial}/signals", {"gear": "P"})[0] == 200
    home.wait_text("speed_value", "0")
    app.wait_visible("restriction_banner", expected=False)


@pytest.mark.req("BENCH-01", "ENERGY-02")
@pytest.mark.regression
def test_api_low_range_shows_charger_card(app, bench):
    """REST API로 주행 가능 거리 25 km를 넣으면 '충전 필요'와 충전소 안내 카드가 뜹니다."""
    url, serial = bench
    cluster = app.cluster()
    status, reply = call(url, "POST", f"/api/devices/{serial}/signals", {"range_km": 25, "battery_pct": 8})
    assert status == 200, reply
    wait_value(lambda: cluster.range_km(), 25, what="주행 가능 거리(km)")
    wait_until(cluster.low_range_warning, what="충전 필요 표시")
    assert app.visible("low_range_card")


@pytest.mark.req("BENCH-01")
@pytest.mark.regression
def test_api_rejects_invalid_value_and_leaves_vehicle_alone(app, bench, car):
    """범위를 벗어난 값(풍량 9)은 400으로 거절하고, 차량의 풍량은 그대로 둡니다."""
    url, serial = bench
    status, reply = call(url, "POST", f"/api/devices/{serial}/signals", {"fan": 9})
    assert status == 400 and "fan 는 1~7" in reply["error"]
    assert car.signal(Signal.FAN) == CABIN_DEFAULTS[Signal.FAN]
