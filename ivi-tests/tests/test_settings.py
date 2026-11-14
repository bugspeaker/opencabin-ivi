"""설정: 속도 단위(차량 신호 표시에 반영) · 볼륨 · 저장 유지 · 초기화 · 시계 형식."""
import pytest

from ivi.waits import wait_until


@pytest.mark.sanity
def test_mph_setting_converts_vehicle_speed(app, car):
    """설정 → 주행 정보: mph 로 바꾸면 차량 속도 50 km/h 가 31 mph 로 보인다."""
    settings = app.settings()
    assert not settings.checked("unit_mph")
    settings.toggle("unit_mph")

    car.drive(50.0)
    wait_until(lambda: app.speed() == ("31", "mph"), what="31 mph")


@pytest.mark.sanity
def test_volume_steps(app):
    settings = app.settings()
    assert settings.value("volume") == 15
    settings.up("volume")
    settings.down("volume")
    settings.down("volume")
    assert settings.value("volume") == 14


@pytest.mark.regression
def test_settings_survive_app_restart(app, device):
    settings = app.settings()
    settings.toggle("unit_mph")
    settings.ambient(3)
    settings.wait_text("settings_ambient_value", "퍼플")
    settings.up("brightness")

    device.stop_app()
    device.launch()
    settings = app.settings()
    assert settings.checked("unit_mph")
    assert settings.ambient_name() == "퍼플"
    assert settings.value("brightness") == 17


@pytest.mark.regression
def test_reset_restores_defaults(app):
    settings = app.settings()
    settings.toggle("autolock")
    settings.up("volume")
    settings.reset()
    wait_until(lambda: settings.value("volume") == 15, what="볼륨 기본값")
    assert settings.checked("autolock")


@pytest.mark.regression
def test_12_hour_clock_on_tablet(app, device):
    """시계는 시스템 바가 없는 태블릿(Mock)에서만 앱이 그린다."""
    if device.automotive:
        pytest.skip("AAOS 는 시스템 바가 시계를 보여 준다 (앱 시계 없음)")
    settings = app.settings()
    settings.toggle("clock24")
    wait_until(lambda: any(word in app.text("status_clock") for word in ("오전", "오후")), what="12시간 형식")
