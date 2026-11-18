"""기어가 R이 되면 어느 화면에서든 후방 카메라가 뜨고, R에서 벗어나면 보던 화면으로 돌아오는지 확인합니다."""
import time

import pytest

from ivi.waits import wait_until


@pytest.mark.req("CAM-01")
@pytest.mark.sanity
def test_reverse_gear_shows_camera(app, car):
    """기어가 R이 되면 후방 카메라 화면이 뜨고, P로 바꾸면 사라집니다."""
    assert not app.rear_camera()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)


@pytest.mark.req("CAM-01")
@pytest.mark.regression
def test_camera_returns_to_previous_screen(app, car):
    """라디오를 보다가 후진하면 카메라가 뜨고, 기어를 바꾸면 보던 라디오 화면으로 돌아옵니다."""
    radio = app.radio()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)
    radio.wait_visible("radio_freq")


@pytest.mark.req("CAM-01", "DRIVE-01")
@pytest.mark.regression
def test_gear_value_shows_reverse(app, car):
    """후진 기어 신호가 들어오면 주행 정보의 기어 표시가 R로 바뀝니다."""
    home = app.home()
    car.reverse()
    home.wait_text("gear_value", "R")


CAMERA_LIMIT = 2.0  # FMVSS 111: 후진을 시작하고 2.0초 안에 후방 영상을 보여야 한다


@pytest.mark.req("CAM-02")
@pytest.mark.regression
def test_rear_camera_appears_within_two_seconds(app, car, request):
    """기어를 R로 바꾼 뒤 2.0초 안에 후방 카메라 화면이 떠야 합니다(FMVSS 111).
    다섯 번 재서 가장 느린 값으로 판정하고, 신호를 넣는 adb 시간까지 포함해 잽니다.
    """
    times = []
    for _ in range(5):
        car.park()
        app.wait_visible("rear_camera", expected=False)
        started = time.monotonic()
        car.reverse()
        wait_until(app.rear_camera, timeout=5, interval=0.05, what="후방 카메라")
        times.append(time.monotonic() - started)
    request.node.user_properties.append(("camera_seconds", ", ".join(f"{t:.2f}" for t in times)))
    assert max(times) <= CAMERA_LIMIT, f"후방 카메라가 {max(times):.2f}초 만에 떴다 (측정값 {times})"
