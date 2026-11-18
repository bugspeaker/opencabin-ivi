"""빌드가 나오면 가장 먼저 돌리는 최소 확인입니다. 여기서 실패하면 나머지 테스트는 돌려도 의미가 없습니다."""
import pytest

pytestmark = pytest.mark.smoke


@pytest.mark.req("SYS-01")
def test_app_starts_with_vehicle_source_for_device(app, device):
    """앱이 뜨고 기기에 맞는 차량 데이터에 연결됩니다.
    AAOS에서는 CarService, 태블릿에서는 Mock입니다.
    """
    assert app.source_badge() == device.vehicle.badge
    assert not app.visible("vehicle_disconnected"), "차량 연결 안 됨 표시가 떠 있다"
    assert not app.visible("vehicle_error"), f"차량 오류 표시: {app.text('vehicle_error')}"


@pytest.mark.req("SYS-01", "DRIVE-01")
def test_parked_on_start(app):
    """정차 상태로 시작하면 속도는 0, 기어는 P이고 주행 제한 배지가 없습니다."""
    home = app.home()
    home.wait_text("speed_value", "0")
    assert home.gear() == "P"
    assert not app.restriction_banner()


@pytest.mark.req("UI-01")
@pytest.mark.parametrize("tab", ["home", "navigation", "radio", "media", "phone", "climate", "settings",
                                 "assistant", "vehicle_controls", "apps"])
def test_each_tab_opens(app, tab):
    """탭마다 화면이 열리는지 봅니다.
    화면마다 핵심 요소가 나타날 때까지 기다립니다.
    """
    getattr(app, tab)()


@pytest.mark.req("SYS-01", "HVAC-01")
def test_hvac_is_controllable(app):
    """공조를 제어할 수 있는지 봅니다.
    AAOS에서 실패하면 priv-app 설치와 공조 권한부터 확인합니다.
    """
    climate = app.climate()
    assert not climate.unavailable(), "공조 제어 불가 화면. AAOS 면 ivi-app/privileged/install_priv_app.py 로 설치했는지 확인"
