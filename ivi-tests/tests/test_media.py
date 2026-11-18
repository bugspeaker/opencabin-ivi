"""미디어 화면의 기본 기능을 확인합니다. 차량 신호와는 관계없는 회귀 테스트입니다."""
import pytest

pytestmark = pytest.mark.regression


@pytest.mark.req("MEDIA-02")
@pytest.mark.parametrize("index", [0, 2, 4])
def test_selecting_track_starts_it(app, index):
    """재생 목록에서 곡을 고르면 그 곡이 재생됩니다."""
    media = app.media()
    title = media.select_track(index)
    media.wait_text("now_playing_title", title)
    media.wait_text("playback_state", "재생 중")


@pytest.mark.req("MEDIA-02")
def test_play_pause_toggles(app):
    """재생 버튼을 누를 때마다 재생과 일시 정지가 번갈아 바뀝니다."""
    media = app.media()
    media.select_track(1)
    media.wait_text("playback_state", "재생 중")
    media.toggle_play()
    media.wait_text("playback_state", "일시 정지")
    media.toggle_play()
    media.wait_text("playback_state", "재생 중")


@pytest.mark.req("DRIVE-02", "MEDIA-02")
def test_media_stays_usable_while_driving(app, car):
    """주행 중에도 음악은 고를 수 있습니다.
    막혀야 하는 것은 영상뿐입니다.
    """
    media = app.media()
    car.drive(50.0)
    app.wait_visible("restriction_banner")
    title = media.select_track(3)
    media.wait_text("now_playing_title", title)
