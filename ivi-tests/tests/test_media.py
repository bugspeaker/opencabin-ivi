"""미디어 화면 회귀: 차량 신호와 무관한 기본 기능."""
import pytest

pytestmark = pytest.mark.regression


@pytest.mark.parametrize("index", [0, 2, 4])
def test_selecting_track_starts_it(app, index):
    media = app.media()
    title = media.select_track(index)
    media.wait_text("now_playing_title", title)
    media.wait_text("playback_state", "재생 중")


def test_play_pause_toggles(app):
    media = app.media()
    media.select_track(1)
    media.wait_text("playback_state", "재생 중")
    media.toggle_play()
    media.wait_text("playback_state", "일시 정지")
    media.toggle_play()
    media.wait_text("playback_state", "재생 중")


def test_media_stays_usable_while_driving(app, car):
    """주행 중에도 음악 선택은 된다 (메인 화면은 distractionOptimized). 영상만 막혀야 한다."""
    media = app.media()
    car.drive(50.0)
    app.wait_visible("restriction_banner")
    title = media.select_track(3)
    media.wait_text("now_playing_title", title)
