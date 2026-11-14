"""라디오: 켜기 · 미세 조정 · 방송국 찾기 · 대역 · 프리셋(저장 유지) · 오디오 소스 하나만 재생."""
import pytest

from ivi.waits import wait_until


@pytest.mark.sanity
def test_power_on_plays_default_station(app):
    radio = app.radio()
    assert radio.state() == "꺼짐"
    radio.power()
    radio.wait_text("radio_state", "재생 중")
    assert radio.freq() == "89.1 MHz"
    assert radio.station() == "뉴스 FM"


@pytest.mark.sanity
def test_tune_and_seek(app):
    radio = app.radio()
    assert radio.step("tune_up") == "89.2 MHz"
    assert radio.station() == "방송 없음"
    assert radio.step("seek_up") == "91.9 MHz"
    assert radio.station() == "음악 FM"
    assert radio.step("seek_down") == "89.1 MHz"


@pytest.mark.sanity
def test_am_band_uses_khz_steps(app):
    radio = app.radio()
    radio.band("am")
    radio.wait_text("radio_freq", "711 kHz")
    assert radio.station() == "AM 뉴스"
    assert radio.step("tune_up") == "720 kHz"  # AM 은 9 kHz 단위


@pytest.mark.regression
def test_preset_save_and_recall(app):
    radio = app.radio()
    radio.step("seek_up")
    assert radio.step("seek_up") == "95.9 MHz"
    radio.save_preset(0)
    radio.wait_text("radio_preset_0_freq", "95.9 MHz")

    radio.step("seek_up")
    radio.recall(0)
    radio.wait_text("radio_freq", "95.9 MHz")


@pytest.mark.regression
def test_preset_and_frequency_survive_app_restart(app, device):
    """저장 설정: 앱 프로세스를 끝내고 다시 켜도 프리셋과 마지막 주파수가 남는다."""
    radio = app.radio()
    radio.step("seek_up")
    radio.step("seek_up")  # 95.9
    radio.save_preset(5)

    device.stop_app()
    device.launch()
    radio = app.radio()
    radio.wait_text("radio_preset_5_freq", "95.9 MHz")
    assert radio.freq() == "95.9 MHz"


@pytest.mark.regression
def test_radio_and_media_play_one_at_a_time(app):
    """오디오 소스는 하나: 음악 재생 중 라디오를 켜면 음악이 일시 정지된다."""
    media = app.media()
    media.select_track(1)
    media.wait_text("playback_state", "재생 중")

    radio = app.radio()
    radio.power()
    radio.wait_text("radio_state", "재생 중")

    media = app.media()
    media.wait_text("playback_state", "일시 정지")
    wait_until(lambda: app.radio().state() == "재생 중", what="라디오 계속 재생")
