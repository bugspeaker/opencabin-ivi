"""주행 상태 E2E: 속도·기어 신호 → 화면 표시, 주행 중 UX 제한(영상 차단).

영상 차단 판정은 기기마다 다르다 (Device.video_blocked):
  AAOS  : OS 가 ActivityBlockingActivity 로 막는다 (VideoActivity 는 distractionOptimized 가 아님)
  Mock  : 시스템 차단이 없어 앱이 video_blocked 화면을 보여 준다
"""
import pytest

from ivi.device import VIDEO
from ivi.waits import wait_until


@pytest.mark.sanity
def test_driving_signals_are_shown(app, car):
    home = app.home()

    car.drive(50.0)
    home.wait_text("speed_value", "50")
    home.wait_text("gear_value", "D")
    app.wait_visible("restriction_banner")

    car.park()
    home.wait_text("speed_value", "0")
    home.wait_text("gear_value", "P")
    app.wait_visible("restriction_banner", expected=False)


@pytest.mark.sanity
def test_video_button_locked_while_driving(app, car):
    media = app.media()
    assert media.video_button_enabled()

    car.drive(50.0)
    media.wait_enabled("open_video", False)
    assert media.restricted_notice()

    car.park()
    media.wait_enabled("open_video", True)
    assert not media.restricted_notice()


@pytest.mark.sanity
def test_video_is_blocked_while_driving(app, car, device, driver):
    """버튼을 거치지 않고 영상 화면을 직접 열어도(다른 앱·알림에서 들어오는 경우) 주행 중에는 막힌다."""
    car.drive(50.0)
    car.wait_restricted(True)

    device.launch(VIDEO)
    video = app.video()
    wait_until(lambda: device.video_blocked(video), what="주행 중 영상 차단")
    assert not video.playing(), "주행 중인데 영상 재생 화면이 보인다"


@pytest.mark.sanity
def test_video_plays_when_parked(app, car, device, driver):
    device.launch(VIDEO)
    video = app.video()
    video.wait_visible("video_player")
    first = video.elapsed()
    wait_until(lambda: video.elapsed() != first, timeout=5, what="재생 시간 증가")
    video.close()


@pytest.mark.regression
def test_video_blocked_screen_follows_parking(app, car, device, driver):
    """주행 중 차단된 영상은 정차하면 다시 쓸 수 있어야 한다 (차단 화면이 그대로 남으면 결함)."""
    car.drive(50.0)
    car.wait_restricted(True)
    device.launch(VIDEO)
    video = app.video()
    wait_until(lambda: device.video_blocked(video), what="주행 중 영상 차단")

    car.park()
    car.wait_restricted(False)
    # AAOS: ActivityBlockingActivity 가 닫히고 막혔던 VideoActivity 가 다시 앞으로 온다 (2026-11-13 에뮬레이터 확인)
    # Mock: 같은 화면이 재생 화면으로 바뀐다
    wait_until(lambda: not device.video_blocked(video), what="정차 후 차단 해제")
    video.wait_visible("video_player")
