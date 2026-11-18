"""설정의 속도 단위, 볼륨, 저장 유지, 초기화, 시계 형식을 확인합니다."""
import pytest

from ivi.waits import wait_until


@pytest.mark.req("SET-01", "DRIVE-01")
@pytest.mark.sanity
def test_mph_setting_converts_vehicle_speed(app, car):
    """속도 단위를 mph로 바꾸면 차량 속도 50 km/h가 31 mph로 보입니다."""
    settings = app.settings()
    assert not settings.checked("unit_mph")
    settings.toggle("unit_mph")

    car.drive(50.0)
    wait_until(lambda: app.speed() == ("31", "mph"), what="31 mph")


@pytest.mark.req("SET-01")
@pytest.mark.regression
def test_volume_steps(app):
    """볼륨은 한 단계씩 오르내립니다.
    기본값 15에서 한 번 올리고 두 번 내리면 14가 됩니다.
    """
    settings = app.settings()
    assert settings.value("volume") == 15
    settings.up("volume")
    settings.down("volume")
    settings.down("volume")
    assert settings.value("volume") == 14


@pytest.mark.req("SET-01")
@pytest.mark.regression
def test_settings_survive_app_restart(app, device):
    """속도 단위, 무드등 색, 밝기를 바꾸고 앱을 껐다 켜도 바꾼 값이 그대로 남아 있습니다."""
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


@pytest.mark.req("SET-01")
@pytest.mark.regression
def test_reset_restores_defaults(app):
    """설정 초기화를 누르면 바꿔 둔 볼륨과 도어 자동 잠금이 기본값으로 돌아옵니다."""
    settings = app.settings()
    settings.toggle("autolock")
    settings.up("volume")
    settings.reset()
    wait_until(lambda: settings.value("volume") == 15, what="볼륨 기본값")
    assert settings.checked("autolock")


@pytest.mark.req("SET-01")
@pytest.mark.regression
def test_12_hour_clock_on_tablet(app, device):
    """태블릿에는 시스템 바가 없어서 앱이 시계를 직접 그립니다.
    24시간 시계를 끄면 오전, 오후가 붙은 12시간 형식으로 바뀝니다.
    """
    if device.automotive:
        pytest.skip("AAOS 는 시스템 바가 시계를 보여 준다 (앱 시계 없음)")
    settings = app.settings()
    settings.toggle("clock24")
    wait_until(lambda: any(word in app.text("status_clock") for word in ("오전", "오후")), what="12시간 형식")
