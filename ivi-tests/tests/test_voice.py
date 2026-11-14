"""음성 명령: 인식된 문장이 실제 기능으로 이어지는지 본다. 온도 명령은 차량 신호까지 확인한다 (E2E)."""
import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_until


@pytest.mark.sanity
def test_voice_sets_driver_temperature_on_vehicle(app, car):
    voice = app.voice()
    result = voice.say(0)  # "운전석 온도 24도로 맞춰줘"
    assert "24.0" in result
    wait_until(lambda: car.temperature(Seat.DRIVER) == 24.0, what="차량 운전석 온도 24.0")


@pytest.mark.sanity
def test_voice_turns_on_radio(app):
    voice = app.voice()
    voice.say(1)  # "라디오 켜줘"
    app.wait_text("radio_state", "재생 중")


@pytest.mark.regression
def test_voice_starts_guidance_home(app):
    voice = app.voice()
    voice.say(2)  # "집으로 안내해줘"
    app.wait_text("nav_dest_name", "집")
    app.find("nav_remaining")


@pytest.mark.regression
def test_voice_panel_closes_after_command(app):
    """명령을 처리하면 패널이 닫혀 안내·통화 화면을 가리지 않는다 (6단계 회귀에서 찾은 결함의 회귀 테스트)."""
    voice = app.voice()
    voice.say(2)
    assert not app.visible("voice_panel")
    app.wait_text("nav_dest_name", "집")


@pytest.mark.regression
def test_voice_calls_contact(app):
    voice = app.voice()
    voice.say(3)  # "엄마에게 전화해줘"
    app.wait_text("phone_call_name", "엄마")
    app.tap("phone_end")
    app.wait_visible("phone_call_screen", expected=False)
