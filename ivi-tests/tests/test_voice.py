"""음성 명령으로 알아들은 문장이 실제 기능으로 이어지는지 확인합니다. 온도 명령은 차량 신호까지 봅니다."""
import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_until


@pytest.mark.sanity
def test_voice_sets_driver_temperature_on_vehicle(app, car):
    """'운전석 온도 24도로 맞춰줘'라고 하면 차량의 운전석 온도가 24.0°C가 됩니다."""
    voice = app.voice()
    result = voice.say(0)  # "운전석 온도 24도로 맞춰줘"
    assert "24.0" in result
    wait_until(lambda: car.temperature(Seat.DRIVER) == 24.0, what="차량 운전석 온도 24.0")


@pytest.mark.sanity
def test_voice_turns_on_radio(app):
    """'라디오 켜줘'라고 하면 라디오가 켜집니다."""
    voice = app.voice()
    voice.say(1)  # "라디오 켜줘"
    app.wait_text("radio_state", "재생 중")


@pytest.mark.regression
def test_voice_starts_guidance_home(app):
    """'집으로 안내해줘'라고 하면 집까지 경로 안내가 시작됩니다."""
    voice = app.voice()
    voice.say(2)  # "집으로 안내해줘"
    app.wait_text("nav_dest_name", "집")
    app.find("nav_remaining")


@pytest.mark.regression
def test_voice_panel_closes_after_command(app):
    """명령을 처리하면 음성 패널이 닫혀 안내나 통화 화면을 가리지 않습니다.
    6단계 회귀 테스트에서 찾은 결함이 다시 생기지 않는지 봅니다.
    """
    voice = app.voice()
    voice.say(2)
    assert not app.visible("voice_panel")
    app.wait_text("nav_dest_name", "집")


@pytest.mark.regression
def test_voice_calls_contact(app):
    """'엄마에게 전화해줘'라고 하면 엄마에게 전화를 걸고, 끊으면 통화 화면이 닫힙니다."""
    voice = app.voice()
    voice.say(3)  # "엄마에게 전화해줘"
    app.wait_text("phone_call_name", "엄마")
    app.tap("phone_end")
    app.wait_visible("phone_call_screen", expected=False)
