"""주행 상태 E2E: 속도·기어 신호 → 화면 표시, 주행 중 UX 제한(영상 차단).

영상 차단 판정은 기기마다 다르다 (Device.video_blocked):
  AAOS  : OS 가 ActivityBlockingActivity 로 막는다 (VideoActivity 는 distractionOptimized 가 아님)
  Mock  : 시스템 차단이 없어 앱이 video_blocked 화면을 보여 준다
"""
import time

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


def _real_clips_or_skip(video):
    video.wait_visible("video_player")
    if not video.has_clips():
        pytest.skip("기기에 주행 영상이 없다 (tools/push_drive_videos.py 로 올린다)")


@pytest.mark.regression
def test_video_resumes_where_it_stopped(app, car, device, driver):
    """주행으로 막혔다가 정차하면 처음부터가 아니라 멈춘 자리에서 이어서 재생한다. 막힌 동안에는 재생이 흐르지 않는다."""
    device.launch(VIDEO)
    video = app.video()
    _real_clips_or_skip(video)
    wait_until(lambda: video.elapsed_seconds() >= 3, timeout=10, what="3초 이상 재생")

    # 막힌 화면에서는 재생 시간을 읽을 수 없다 → 주행 직전 재생 시간과 실제로 흐른 시간을 비교한다
    before, t0 = video.elapsed_seconds(), time.monotonic()
    car.drive(50.0)
    car.wait_restricted(True)
    wait_until(lambda: device.video_blocked(video), what="주행 중 영상 차단")
    time.sleep(5)  # 막힌 채로 둔다

    car.park()
    car.wait_restricted(False)
    wait_until(lambda: not device.video_blocked(video), what="정차 후 차단 해제")
    video.wait_visible("video_player")
    resumed, wall = video.elapsed_seconds(), time.monotonic() - t0
    assert resumed >= before, f"정차 후 처음부터 다시 재생된다 (주행 전 {before}초 → {resumed}초)"
    # 막힌 동안에도 재생이 흘렀다면 resumed - before ≈ wall. 멈췄다면 차단까지 걸린 1~2초만 더해진다
    assert resumed - before <= wall - 4, f"막힌 동안에도 재생이 흘렀다 ({before}초 → {resumed}초, 실제 {wall:.1f}초)"
    first = video.elapsed()
    wait_until(lambda: video.elapsed() != first, timeout=5, what="정차 후 재생 재개")


@pytest.mark.regression
def test_video_next_clip(app, car, device, driver):
    device.launch(VIDEO)
    video = app.video()
    _real_clips_or_skip(video)
    if video.clip_index().endswith("/ 1"):
        pytest.skip("영상이 하나뿐이다")
    assert video.clip_index().startswith("1 /")
    video.next_clip()
    video.wait_text("video_index", f"2 / {video.clip_index().split('/')[1].strip()}")
    video.close()
