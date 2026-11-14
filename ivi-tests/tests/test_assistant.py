"""AI 어시스턴트 E2E (7단계): 말 → 실제 차량 신호까지 본다.

음성 인식 대신 추천 명령(칩)을 누르거나 글자로 입력한다. 문장 → 동작 규칙 자체는
ivi-app 의 JVM 단위 테스트(CabinAssistantTest)가 보고, 여기서는 화면 · 차량 신호 · 주행 제한과 이어지는지를 본다.

칩 번호 (ivi-app ui/Assistant.kt AssistantSuggestions):
  0 "22도로 맞춰줘"  1 "나 더워"  2 "에어컨 켜고 음악 틀어줘"  3 "판교 가자"  4 "엄마에게 전화해줘"  5 "사이드 미러 접어줘"
"""
import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_until


@pytest.mark.sanity
def test_zone_applies_command_to_speaking_seat(app, car):
    """좌석 인식: 조수석에서 '나 더워' → 조수석만 1°C 내려간다 (차량 신호 확인)."""
    assistant = app.assistant()
    assistant.zone(Seat.PASSENGER)
    reply = assistant.chip(1)
    assert "조수석" in reply
    wait_until(lambda: car.temperature(Seat.PASSENGER) == 21.0, what="차량 조수석 21.0")
    assert car.temperature(Seat.DRIVER) == 22.0
    app.bar().wait_temperature(Seat.PASSENGER, 21.0)


@pytest.mark.sanity
def test_typed_command_sets_vehicle_temperature(app, car):
    """글자로 말하기: '운전석 25.5도로 맞춰줘' → 차량 운전석 25.5 (상위 → 하위)."""
    assistant = app.assistant()
    reply = assistant.say("운전석 25.5도로 맞춰줘")
    assert "25.5" in reply
    wait_until(lambda: car.temperature(Seat.DRIVER) == 25.5, what="차량 운전석 25.5")


@pytest.mark.regression
def test_multiple_commands_in_one_sentence(app):
    """한 문장에 두 명령: 에어컨 켜고 음악 틀어줘 → 두 동작 모두."""
    assistant = app.assistant()
    reply = assistant.chip(2)
    assert "에어컨" in reply and "음악" in reply
    app.media().wait_text("playback_state", "재생 중")


@pytest.mark.regression
def test_ambiguous_destination_offers_candidates(app):
    """후보가 여럿이면 고르게 한다: '판교 가자' → 3곳 → 판교역을 고르면 안내가 시작된다."""
    assistant = app.assistant()
    reply = assistant.chip(3)
    assert "3곳" in reply
    assistant.choose(2)  # 가까운 순: 충전소 1.8, 주차장 2.0, 판교역 5.2
    app.wait_text("nav_dest_name", "판교역")
    app.find("nav_remaining")


@pytest.mark.sanity
def test_driving_locks_typing_and_refuses_mirror_fold(app, car):
    """주행 중: 글자 입력은 막히고(칩은 된다), 사이드 미러 접기는 거절한다."""
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


@pytest.mark.regression
def test_voice_popup_and_assistant_share_history(app):
    """음성 팝업에서 한 말이 AI 어시스턴트 대화 내역에도 남는다."""
    voice = app.voice()
    voice.say(1)  # "라디오 켜줘"
    assistant = app.assistant()
    assert assistant.reply() == "라디오를 켤게요."
