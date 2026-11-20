"""공조 온도를 차량 신호와 앱 화면 양쪽에서 확인합니다. 같은 테스트를 AAOS(VHAL)와 태블릿(Mock)에서 돌립니다."""
import pytest

from ivi.vehicle import Seat
from ivi.waits import stays, wait_value

STEP = 0.5
MIN_C, MAX_C = 16.0, 28.0


@pytest.mark.req("HVAC-01")
@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_signal_is_shown_on_climate_and_home(app, car, seat):
    """차량의 설정 온도가 바뀌면 공조 화면과 홈 화면이 같은 값을 보여 줍니다."""
    climate = app.climate()
    car.set_temperature(seat, 25.0)
    climate.wait_temperature(seat, 25.0)

    home = app.home()
    wait_value(lambda: home.summary_temperature(seat), 25.0, what=f"홈 {seat.tag} 온도")


@pytest.mark.req("HVAC-01", "HVAC-02")
@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
@pytest.mark.parametrize("direction", ["up", "down"])
def test_button_changes_signal_by_one_step(app, car, seat, direction):
    """화면의 + 또는 -를 한 번 누르면 차량 온도가 0.5°C 바뀌고, 화면 숫자도 같이 바뀝니다."""
    climate = app.climate()
    climate.wait_temperature(seat, 22.0)

    (climate.increase if direction == "up" else climate.decrease)(seat)

    expected = 22.0 + (STEP if direction == "up" else -STEP)
    wait_value(lambda: car.temperature(seat), expected, what=f"차량 {seat.tag} 온도")
    climate.wait_temperature(seat, expected)


@pytest.mark.req("HVAC-02")
@pytest.mark.regression
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_buttons_disabled_at_limits(app, car, seat):
    """최저 온도 16.0°C에서는 - 버튼이, 최고 온도 28.0°C에서는 + 버튼이 꺼지고 반대쪽 버튼은 그대로 눌립니다."""
    climate = app.climate()

    car.set_temperature(seat, MIN_C)
    climate.wait_temperature(seat, MIN_C)
    climate.wait_enabled(f"{seat.tag}_temp_down", False)
    assert climate.can_increase(seat)

    car.set_temperature(seat, MAX_C)
    climate.wait_temperature(seat, MAX_C)
    climate.wait_enabled(f"{seat.tag}_temp_up", False)
    assert climate.can_decrease(seat)


@pytest.mark.req("HVAC-02")
@pytest.mark.regression
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_step_reaches_limit_and_disables(app, car, seat):
    """16.5°C에서 -를 한 번 누르면 차량 온도가 16.0°C가 되고 - 버튼이 꺼집니다. 27.5°C에서 +도 같습니다. 끝에 닿은 뒤 꺼진 버튼을 눌러도 차량 온도는 범위를 넘지 않습니다."""
    climate = app.climate()
    for start, limit, tag, press in ((MIN_C + STEP, MIN_C, "down", climate.decrease),
                                     (MAX_C - STEP, MAX_C, "up", climate.increase)):
        car.set_temperature(seat, start)
        climate.wait_temperature(seat, start)
        climate.wait_enabled(f"{seat.tag}_temp_{tag}", True)

        press(seat)
        wait_value(lambda: car.temperature(seat), limit, what=f"차량 {seat.tag} 온도")
        climate.wait_temperature(seat, limit)
        climate.wait_enabled(f"{seat.tag}_temp_{tag}", False)

        press(seat)  # 꺼진 버튼
        stays(lambda: car.temperature(seat) == limit, what=f"차량 {seat.tag} 온도 {limit} 유지")


@pytest.mark.req("HVAC-02")
@pytest.mark.regression
@pytest.mark.parametrize("value, away, back, expected", [
    # 기기별 (주입한 뒤 차량·화면 값, 반대 버튼을 한 번 누른 뒤 차량·화면 값). 버튼 값은 앱의 HvacSpec.stepUp/stepDown 과 같다
    (MIN_C - STEP, "down", "up", {"aaos": (15.5, 16.0), "mock": (16.0, 16.5)}),
    (MAX_C + STEP, "up", "down", {"aaos": (28.5, 28.0), "mock": (28.0, 27.5)}),
], ids=["below_min", "above_max"])
def test_out_of_range_signal_is_shown_safely(app, car, device, value, away, back, expected):
    """차량 쪽에서 범위 밖 온도(15.5°C, 28.5°C)가 와도 앱은 멈추지 않고, 범위 밖으로 더 가는 버튼은 꺼집니다. 기기마다 기대값이 하나입니다.
    AAOS는 VHAL에 값을 바로 넣어 화면이 15.5°C를 그대로 보여 주고, ▲를 한 번 누르면 차량 온도가 끝값 16.0°C가 됩니다(28.5°C는 ▼로 28.0°C).
    태블릿의 Mock 차량은 받은 값을 끝값 16.0°C로 잘라 두므로, ▲를 누르면 한 칸 안쪽 16.5°C가 됩니다(28.5°C는 28.0°C로 잘린 뒤 ▼로 27.5°C)."""
    seat = Seat.DRIVER
    shown, after = expected[device.kind]
    climate = app.climate()
    car.inject_temperature(seat, value)
    wait_value(lambda: car.temperature(seat), shown, what=f"주입한 뒤 차량 {seat.tag} 온도")
    climate.wait_temperature(seat, shown)
    climate.wait_enabled(f"{seat.tag}_temp_{away}", False)

    (climate.increase if back == "up" else climate.decrease)(seat)
    wait_value(lambda: car.temperature(seat), after, what=f"버튼을 누른 뒤 차량 {seat.tag} 온도")
    climate.wait_temperature(seat, after)


@pytest.mark.req("HVAC-02")
@pytest.mark.regression
@pytest.mark.parametrize("direction, expected", [("up", 22.5), ("down", 22.0)])
def test_off_grid_signal_steps_back_to_grid(app, car, direction, expected):
    """차량 쪽에서 0.5°C 단위가 아닌 온도(22.3°C)가 와도, 버튼을 한 번 누르면 차량 온도가 0.5°C 단위(+는 22.5°C, -는 22.0°C)로 맞춰집니다."""
    seat = Seat.DRIVER
    climate = app.climate()
    car.inject_temperature(seat, 22.3)
    climate.wait_temperature(seat, 22.3)

    (climate.increase if direction == "up" else climate.decrease)(seat)
    wait_value(lambda: car.temperature(seat), expected, what=f"차량 {seat.tag} 온도")
    climate.wait_temperature(seat, expected)


@pytest.mark.req("HVAC-01")
@pytest.mark.regression
def test_seats_are_independent(app, car):
    """한쪽 좌석 온도를 바꿔도 다른 좌석 값은 그대로여야 합니다.
    좌석 area를 헷갈리는 결함을 잡는 테스트입니다.
    """
    climate = app.climate()
    climate.increase(Seat.DRIVER)
    wait_value(lambda: car.temperature(Seat.DRIVER), 22.5, what="차량 운전석 온도")
    climate.wait_temperature(Seat.DRIVER, 22.5)
    # 한 번만 보면 늦게 도착하는 잘못된 쓰기(조수석 area 에 쓰기)를 놓친다 → 1.5초 동안 계속 본다
    stays(lambda: car.temperature(Seat.PASSENGER) == 22.0 and climate.temperature(Seat.PASSENGER) == 22.0,
          what="조수석 신호와 화면 22.0°C")
