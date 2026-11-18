"""블루투스 핸즈프리 전화(가상)의 통화 화면, 최근 통화, 키패드, 주행 중 제한을 확인합니다."""
import pytest

from ivi.waits import wait_until


@pytest.mark.req("MEDIA-02")
@pytest.mark.sanity
def test_call_contact_shows_call_screen_and_recent(app):
    """연락처에서 전화를 걸면 통화 화면에 이름과 통화 시간이 보이고, 끊고 나면 최근 통화 맨 위에 남습니다."""
    phone = app.phone()
    phone.tab("contacts")
    name = phone.call_contact(2)
    assert phone.call_name() == name
    first = phone.call_seconds()
    wait_until(lambda: phone.call_seconds() > first, timeout=5, what="통화 시간 증가")

    phone.end()
    phone.tab("recent")
    phone.wait_text("phone_recent_0_name", name)


@pytest.mark.req("MEDIA-02")
@pytest.mark.sanity
def test_keypad_dial(app):
    """키패드로 번호를 눌러 전화를 걸면 통화 화면에 그 번호가 보입니다."""
    phone = app.phone()
    phone.tab("keypad")
    phone.dial("0101234")
    phone.call()
    assert phone.call_name() == "0101234"
    phone.end()


@pytest.mark.req("DRIVE-03")
@pytest.mark.sanity
def test_driving_locks_keypad_and_limits_contacts(app, car):
    """주행 중에는 키패드가 막히고 연락처는 5개까지만 보입니다."""
    phone = app.phone()
    phone.tab("contacts")
    wait_until(lambda: len(phone.contact_names()) > 5, what="정차 중 연락처 전체")

    car.drive(50.0)
    phone.wait_visible("phone_list_limited")
    wait_until(lambda: len(phone.contact_names()) == 5, what="주행 중 연락처 5개")

    phone.tab("keypad")
    phone.wait_visible("phone_keypad_locked")
    phone.wait_enabled("phone_key_1", False)


@pytest.mark.req("MEDIA-01")
@pytest.mark.regression
def test_call_pauses_radio_then_resumes(app):
    """라디오를 듣다가 전화를 걸면 라디오가 멈추고, 통화를 끝내면 다시 나옵니다."""
    radio = app.radio()
    radio.power()
    radio.wait_text("radio_state", "재생 중")

    phone = app.phone()
    phone.tab("contacts")
    phone.call_contact(0)
    radio = app.radio()
    radio.wait_text("radio_state", "통화 중")

    phone = app.phone()
    phone.end()
    radio = app.radio()
    radio.wait_text("radio_state", "재생 중")
