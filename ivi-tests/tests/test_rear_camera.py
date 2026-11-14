"""후방 카메라: 기어 신호가 R 이면 어떤 화면에서든 카메라가 뜨고, R 을 벗어나면 원래 화면으로 돌아온다."""
import pytest


@pytest.mark.sanity
def test_reverse_gear_shows_camera(app, car):
    assert not app.rear_camera()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)


@pytest.mark.regression
def test_camera_returns_to_previous_screen(app, car):
    radio = app.radio()
    car.reverse()
    app.wait_visible("rear_camera")
    car.park()
    app.wait_visible("rear_camera", expected=False)
    radio.wait_visible("radio_freq")


@pytest.mark.regression
def test_gear_value_shows_reverse(app, car):
    home = app.home()
    car.reverse()
    home.wait_text("gear_value", "R")
