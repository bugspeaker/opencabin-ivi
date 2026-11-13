"""공조 E2E: 차량 신호 ↔ 앱 화면을 양방향으로 본다. 같은 테스트가 AAOS(VHAL)와 Mock 기기에서 돈다."""
import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_until

STEP = 0.5
MIN_C, MAX_C = 16.0, 28.0


@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_signal_is_shown_on_climate_and_home(app, car, seat):
    """하위 → 상위: 차량의 설정 온도가 바뀌면 공조 화면과 홈 요약이 같은 값을 보여 준다."""
    climate = app.climate()
    car.set_temperature(seat, 25.0)
    climate.wait_temperature(seat, 25.0)

    home = app.home()
    wait_until(lambda: home.summary_temperature(seat) == 25.0, what=f"홈 {seat.tag} 온도 25.0")


@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
@pytest.mark.parametrize("direction", ["up", "down"])
def test_button_changes_signal_by_one_step(app, car, seat, direction):
    """상위 → 하위: 화면의 +/- 를 한 번 누르면 차량 값이 0.5°C 바뀌고 화면도 따라간다."""
    climate = app.climate()
    climate.wait_temperature(seat, 22.0)

    (climate.increase if direction == "up" else climate.decrease)(seat)

    expected = 22.0 + (STEP if direction == "up" else -STEP)
    wait_until(lambda: car.temperature(seat) == expected, what=f"차량 {seat.tag} 온도 {expected}")
    climate.wait_temperature(seat, expected)


@pytest.mark.regression
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_buttons_disabled_at_limits(app, car, seat):
    """경계 값: 최저(16.0)에서 -, 최고(28.0)에서 + 가 비활성이고 반대쪽은 활성이다."""
    climate = app.climate()

    car.set_temperature(seat, MIN_C)
    climate.wait_temperature(seat, MIN_C)
    climate.wait_enabled(f"{seat.tag}_temp_down", False)
    assert climate.can_increase(seat)

    car.set_temperature(seat, MAX_C)
    climate.wait_temperature(seat, MAX_C)
    climate.wait_enabled(f"{seat.tag}_temp_up", False)
    assert climate.can_decrease(seat)


@pytest.mark.regression
def test_seats_are_independent(app, car):
    """한쪽 좌석을 바꿔도 다른 좌석 값은 그대로다 (area 혼동 방지)."""
    climate = app.climate()
    climate.increase(Seat.DRIVER)
    wait_until(lambda: car.temperature(Seat.DRIVER) == 22.5, what="운전석 22.5")
    climate.wait_temperature(Seat.DRIVER, 22.5)
    assert car.temperature(Seat.PASSENGER) == 22.0
    assert climate.temperature(Seat.PASSENGER) == 22.0
