"""라디오의 켜기, 주파수 조정, 방송국 찾기, 대역 전환, 프리셋을 확인합니다."""
import pytest

from ivi.waits import wait_until


@pytest.mark.req("MEDIA-02")
@pytest.mark.sanity
def test_power_on_plays_default_station(app):
    """라디오를 켜면 기본 방송인 89.1 MHz 뉴스 FM이 나옵니다."""
    radio = app.radio()
    assert radio.state() == "꺼짐"
    radio.power()
    radio.wait_text("radio_state", "재생 중")
    assert radio.freq() == "89.1 MHz"
    assert radio.station() == "뉴스 FM"


@pytest.mark.req("MEDIA-02")
@pytest.mark.regression
def test_tune_and_seek(app):
    """미세 조정은 0.1 MHz씩 움직이고, 방송국 찾기는 방송이 있는 다음 주파수로 바로 넘어갑니다."""
    radio = app.radio()
    assert radio.step("tune_up") == "89.2 MHz"
    assert radio.station() == "방송 없음"
    assert radio.step("seek_up") == "91.9 MHz"
    assert radio.station() == "음악 FM"
    assert radio.step("seek_down") == "89.1 MHz"


@pytest.mark.req("MEDIA-02")
@pytest.mark.regression
def test_am_band_uses_khz_steps(app):
    """AM으로 바꾸면 주파수가 kHz 단위로 바뀌고 9 kHz씩 움직입니다."""
    radio = app.radio()
    radio.band("am")
    radio.wait_text("radio_freq", "711 kHz")
    assert radio.station() == "AM 뉴스"
    assert radio.step("tune_up") == "720 kHz"  # AM 은 9 kHz 단위


@pytest.mark.req("MEDIA-02")
@pytest.mark.regression
def test_preset_save_and_recall(app):
    """지금 주파수를 프리셋에 저장하고 다른 방송으로 옮긴 뒤 프리셋을 누르면, 저장한 주파수로 돌아옵니다."""
    radio = app.radio()
    radio.step("seek_up")
    assert radio.step("seek_up") == "95.9 MHz"
    radio.save_preset(0)
    radio.wait_text("radio_preset_0_freq", "95.9 MHz")

    radio.step("seek_up")
    radio.recall(0)
    radio.wait_text("radio_freq", "95.9 MHz")


@pytest.mark.req("SET-01")
@pytest.mark.regression
def test_preset_and_frequency_survive_app_restart(app, device):
    """앱을 완전히 껐다 켜도 프리셋과 마지막으로 듣던 주파수가 남아 있습니다."""
    radio = app.radio()
    radio.step("seek_up")
    radio.step("seek_up")  # 95.9
    radio.save_preset(5)

    device.stop_app()
    device.launch()
    radio = app.radio()
    radio.wait_text("radio_preset_5_freq", "95.9 MHz")
    assert radio.freq() == "95.9 MHz"


@pytest.mark.req("MEDIA-01")
@pytest.mark.regression
def test_radio_and_media_play_one_at_a_time(app):
    """음악을 듣다가 라디오를 켜면 음악이 일시 정지됩니다.
    소리는 한 번에 하나만 나옵니다.
    """
    media = app.media()
    media.select_track(1)
    media.wait_text("playback_state", "재생 중")

    radio = app.radio()
    radio.power()
    radio.wait_text("radio_state", "재생 중")

    media = app.media()
    media.wait_text("playback_state", "일시 정지")
    wait_until(lambda: app.radio().state() == "재생 중", what="라디오 계속 재생")
