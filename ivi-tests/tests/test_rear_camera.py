"""기어가 R이 되면 어느 화면에서든 후방 카메라가 뜨고, R에서 벗어나면 보던 화면으로 돌아오는지 확인합니다."""
import pytest


@pytest.mark.sanity
def test_reverse_gear_shows_camera(app, car):
    """기어가 R이 되면 후방 카메라 화면이 뜨고, P로 바꾸면 사라집니다."""
    assert not app.rear_camera()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)


@pytest.mark.regression
def test_camera_returns_to_previous_screen(app, car):
    """라디오를 보다가 후진하면 카메라가 뜨고, 기어를 바꾸면 보던 라디오 화면으로 돌아옵니다."""
    radio = app.radio()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)
    radio.wait_visible("radio_freq")


@pytest.mark.regression
def test_gear_value_shows_reverse(app, car):
    """후진 기어 신호가 들어오면 주행 정보의 기어 표시가 R로 바뀝니다."""
    home = app.home()
    car.reverse()
    home.wait_text("gear_value", "R")
