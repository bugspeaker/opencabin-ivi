"""AI 어시스턴트에 한 말이 실제 차량 신호까지 이어지는지 확인합니다.

음성 인식 대신 추천 명령(칩)을 누르거나 글자로 입력한다. 문장 → 동작 규칙 자체는
ivi-app 의 JVM 단위 테스트(CabinAssistantTest)가 보고, 여기서는 화면 · 차량 신호 · 주행 제한과 이어지는지를 본다.

칩 번호 (ivi-app ui/Assistant.kt AssistantSuggestions):
  0 "22도로 맞춰줘"  1 "나 더워"  2 "에어컨 켜고 음악 틀어줘"  3 "판교 가자"  4 "엄마에게 전화해줘"  5 "사이드 미러 접어줘"
"""
import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_value


@pytest.mark.req("VOICE-01", "HVAC-01")
@pytest.mark.regression
def test_zone_applies_command_to_speaking_seat(app, car):
    """조수석에서 '나 더워'라고 하면 조수석 온도만 1°C 내려가야 합니다.
    차량 신호로 확인합니다.
    """
    assistant = app.assistant()
    assistant.zone(Seat.PASSENGER)
    reply = assistant.chip(1)
    assert "조수석" in reply
    wait_value(lambda: car.temperature(Seat.PASSENGER), 21.0, what="차량 조수석 온도")
    assert car.temperature(Seat.DRIVER) == 22.0
    app.bar().wait_temperature(Seat.PASSENGER, 21.0)


@pytest.mark.req("VOICE-01", "HVAC-01")
@pytest.mark.sanity
def test_typed_command_sets_vehicle_temperature(app, car):
    """'운전석 25.5도로 맞춰줘'를 글자로 입력하면 차량의 운전석 온도가 25.5°C가 됩니다."""
    assistant = app.assistant()
    reply = assistant.say("운전석 25.5도로 맞춰줘")
    assert "25.5" in reply
    wait_value(lambda: car.temperature(Seat.DRIVER), 25.5, what="차량 운전석 온도")


@pytest.mark.req("VOICE-01")
@pytest.mark.regression
def test_multiple_commands_in_one_sentence(app):
    """'에어컨 켜고 음악 틀어줘'처럼 한 문장에 명령이 두 개 들어 있으면 둘 다 실행합니다."""
    assistant = app.assistant()
    reply = assistant.chip(2)
    assert "에어컨" in reply and "음악" in reply
    app.media().wait_text("playback_state", "재생 중")


@pytest.mark.req("VOICE-01", "NAV-01")
@pytest.mark.regression
def test_ambiguous_destination_offers_candidates(app):
    """'판교 가자'처럼 목적지 후보가 여럿이면 세 곳을 보여 주고 고르게 합니다.
    판교역을 고르면 안내가 시작됩니다.
    """
    assistant = app.assistant()
    reply = assistant.chip(3)
    assert "3곳" in reply
    assistant.choose(2)  # 가까운 순: 충전소 1.8, 주차장 2.0, 판교역 5.2
    app.wait_text("nav_dest_name", "판교역")
    app.find("nav_remaining")


@pytest.mark.req("DRIVE-03")
@pytest.mark.regression
def test_driving_locks_typing_and_refuses_mirror_fold(app, car):
    """주행 중에는 글자 입력이 막히고 추천 명령만 쓸 수 있습니다.
    사이드 미러를 접어 달라는 명령은 거절합니다.
    """
    assistant = app.assistant()
    assert assistant.typing_enabled()

    car.drive(50.0)
    assistant.wait_enabled("assistant_input", False)
    assert assistant.visible("assistant_input_locked")
    reply = assistant.chip(5)
    assert "주행 중" in reply
    assert app.vehicle_controls().value("mirror") == "펼침"

    car.park()
    assistant = app.assistant()
    assistant.wait_enabled("assistant_input", True)
    assistant.chip(5)
    assert app.vehicle_controls().value("mirror") == "접힘"


@pytest.mark.req("VOICE-01")
@pytest.mark.regression
def test_voice_popup_and_assistant_share_history(app):
    """음성 팝업에서 한 말이 AI 어시스턴트 대화 내역에도 남습니다."""
    voice = app.voice()
    voice.say(1)  # "라디오 켜줘"
    assistant = app.assistant()
    assert assistant.reply() == "라디오를 켤게요."
