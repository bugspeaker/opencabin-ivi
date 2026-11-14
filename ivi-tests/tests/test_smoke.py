"""Smoke: 빌드가 나오면 가장 먼저 도는 최소 확인. 실패하면 나머지 검증을 돌릴 의미가 없다."""
import pytest

pytestmark = pytest.mark.smoke


def test_app_starts_with_vehicle_source_for_device(app, device):
    """앱이 뜨고, 기기에 맞는 차량 데이터 소스에 연결된다 (AAOS → CarService, 그 외 → Mock)."""
    assert app.source_badge() == device.vehicle.badge
    assert not app.visible("vehicle_disconnected"), "차량 연결 안 됨 표시가 떠 있다"
    assert not app.visible("vehicle_error"), f"차량 오류 표시: {app.text('vehicle_error')}"


def test_parked_on_start(app):
    """정차 상태로 시작하면 주행 제한 배지가 없고 속도 0, 기어 P 다."""
    home = app.home()
    home.wait_text("speed_value", "0")
    assert home.gear() == "P"
    assert not app.restriction_banner()


@pytest.mark.parametrize("tab", ["home", "navigation", "radio", "media", "phone", "climate", "settings"])
def test_each_tab_opens(app, tab):
    """탭마다 화면이 열린다 (화면 객체의 wait_loaded 가 핵심 요소를 기다린다)."""
    getattr(app, tab)()


def test_hvac_is_controllable(app):
    """공조를 제어할 수 있다. AAOS 에서 실패하면 priv-app 설치(CONTROL_CAR_CLIMATE)부터 의심한다."""
    climate = app.climate()
    assert not climate.unavailable(), "공조 제어 불가 화면. AAOS 면 ivi-app/privileged/install_priv_app.py 로 설치했는지 확인"
