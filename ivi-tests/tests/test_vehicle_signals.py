"""8단계에서 연결한 차량 신호를 확인합니다. 공조 부가 기능, 좌석 열선, 도어 잠금, 주행 가능 거리, 배터리, 외기 온도입니다.

모든 테스트가 화면과 차량 신호(AAOS: CarProperty/VHAL, 태블릿: Mock)를 **양쪽에서** 본다.
  상위 → 하위: 화면을 누르면 차량 신호가 바뀐다        (car.signal 로 판정)
  하위 → 상위: 차량 신호를 넣으면 화면이 따라 바뀐다    (car.set_signal 이 입력)
시작 상태는 app 픽스처가 기준 값으로 맞춘다 (ivi.vehicle.CABIN_DEFAULTS: A/C 켜짐, 풍량 3, 문 잠김, 320 km, 80 %, 18 °C).

AAOS 에서 실패하면 권한부터 본다: 공조 = CONTROL_CAR_CLIMATE, 도어 = CONTROL_CAR_DOORS (둘 다 priv-app),
주행 가능 거리·배터리 = CAR_ENERGY (pm grant). ivi-app/privileged/install_priv_app.py 가 모두 처리한다.
"""
import pytest

from ivi.vehicle import Seat, Signal
from ivi.waits import wait_until


def wait_signal(car, name, expected, what=None):
    wait_until(lambda: car.signal(name) == expected, what=what or f"차량 신호 {name} = {expected!r}")


# ---------------- 공조: A/C · AUTO · 풍량 · 김서림 ----------------

@pytest.mark.req("HVAC-03")
@pytest.mark.sanity
def test_ac_toggle_reaches_every_seat(app, car):
    """화면에서 A/C를 끄면 운전석만이 아니라 모든 좌석의 HVAC_AC_ON이 꺼져야 합니다."""
    climate = app.climate()
    climate.wait_checked("ac", True)

    climate.toggle("ac")
    wait_until(lambda: not any(car.signal_all(Signal.AC)), what="전 좌석 A/C 꺼짐")
    climate.wait_checked("ac", False)


@pytest.mark.req("HVAC-03")
@pytest.mark.sanity
def test_ac_signal_is_shown_on_climate_and_bottom_bar(app, car):
    """차량 쪽에서 A/C를 끄면 공조 화면의 토글도 꺼지고, 다시 켜면 켜집니다."""
    climate = app.climate()
    car.set_signal(Signal.AC, False)
    climate.wait_checked("ac", False)
    car.set_signal(Signal.AC, True)
    climate.wait_checked("ac", True)


@pytest.mark.req("HVAC-03")
@pytest.mark.sanity
@pytest.mark.parametrize("direction, expected", [("up", 4), ("down", 2)])
def test_fan_button_changes_signal_by_one(app, car, direction, expected):
    """풍량 + 또는 -를 한 번 누르면 HVAC_FAN_SPEED가 한 단계 바뀌고 화면 숫자도 같이 바뀝니다."""
    climate = app.climate()
    assert climate.fan() == 3
    (climate.fan_up if direction == "up" else climate.fan_down)()
    wait_signal(car, Signal.FAN, expected)
    wait_until(lambda: climate.fan() == expected, what=f"풍량 표시 {expected}")


@pytest.mark.req("HVAC-03")
@pytest.mark.regression
@pytest.mark.parametrize("level, blocked", [(1, "climate_fan_down"), (7, "climate_fan_up")])
def test_fan_buttons_disabled_at_limits(app, car, level, blocked):
    """풍량이 최저 1이면 -가, 최고 7이면 +가 눌리지 않고 신호도 범위를 벗어나지 않습니다."""
    climate = app.climate()
    car.set_signal(Signal.FAN, level)
    wait_until(lambda: climate.fan() == level, what=f"풍량 표시 {level}")
    climate.wait_enabled(blocked, False)
    climate.tap(blocked)
    assert car.signal(Signal.FAN) == level


@pytest.mark.req("HVAC-04")
@pytest.mark.sanity
def test_max_ac_sets_signal_and_coldest_settings(app, car):
    """FULL(최대 냉방)을 켜면 모든 좌석의 HVAC_MAX_AC_ON이 켜지고, 온도는 최저, 풍량은 최대가 되며 AUTO는 꺼집니다."""
    climate = app.climate()
    climate.toggle("auto")
    wait_signal(car, Signal.AUTO, True)

    climate.toggle("max_ac")
    wait_until(lambda: all(car.signal_all(Signal.MAX_AC)), what="전 좌석 최대 냉방 켜짐")
    wait_signal(car, Signal.FAN, 7)
    wait_signal(car, Signal.AUTO, False)
    wait_signal(car, Signal.AC, True)
    for seat in Seat:
        wait_until(lambda: car.temperature(seat) == 16.0, what=f"{seat.tag} 온도 최저")
    climate.wait_checked("max_ac", True)
    wait_until(lambda: climate.fan() == 7, what="풍량 표시 7")


@pytest.mark.req("HVAC-04")
@pytest.mark.sanity
def test_max_ac_off_restores_previous_settings(app, car):
    """FULL을 버튼으로 끄면 켜기 전 값인 22.0°C, 풍량 3으로 돌아갑니다."""
    climate = app.climate()
    climate.toggle("max_ac")
    wait_signal(car, Signal.FAN, 7)

    climate.toggle("max_ac")
    wait_until(lambda: not any(car.signal_all(Signal.MAX_AC)), what="전 좌석 최대 냉방 꺼짐")
    wait_signal(car, Signal.FAN, 3)
    for seat in Seat:
        wait_until(lambda: car.temperature(seat) == 22.0, what=f"{seat.tag} 온도 복원")
    climate.wait_checked("max_ac", False)


@pytest.mark.req("HVAC-04")
@pytest.mark.sanity
def test_max_ac_signal_is_shown_on_toggle(app, car):
    """차량 쪽에서 최대 냉방을 켜고 끄면 화면의 FULL 토글도 따라 바뀝니다."""
    climate = app.climate()
    car.set_signal(Signal.MAX_AC, True)
    climate.wait_checked("max_ac", True)
    car.set_signal(Signal.MAX_AC, False)
    climate.wait_checked("max_ac", False)


@pytest.mark.req("HVAC-04")
@pytest.mark.regression
def test_manual_fan_releases_max_ac(app, car):
    """FULL 중에 풍량을 직접 내리면 최대 냉방이 풀립니다.
    온도는 되돌리지 않고 방금 바꾼 값을 따릅니다.
    """
    climate = app.climate()
    climate.toggle("max_ac")
    wait_signal(car, Signal.FAN, 7)

    climate.fan_down()
    wait_signal(car, Signal.MAX_AC, False)
    wait_signal(car, Signal.FAN, 6)
    climate.wait_checked("max_ac", False)
    assert car.temperature(Seat.DRIVER) == 16.0


@pytest.mark.req("HVAC-04")
@pytest.mark.regression
def test_turning_ac_off_releases_max_ac(app, car):
    """FULL 중에 A/C를 끄면 최대 냉방도 같이 꺼집니다.
    A/C 없이 최대 냉방만 켜져 있을 수는 없습니다.
    """
    climate = app.climate()
    climate.toggle("max_ac")
    climate.wait_checked("max_ac", True)

    climate.toggle("ac")
    wait_signal(car, Signal.AC, False)
    wait_signal(car, Signal.MAX_AC, False)
    climate.wait_checked("max_ac", False)


@pytest.mark.req("HVAC-03")
@pytest.mark.regression
def test_manual_fan_releases_auto(app, car):
    """AUTO 중에 풍량을 직접 바꾸면 AUTO가 풀리고 HVAC_AUTO_ON이 꺼집니다."""
    climate = app.climate()
    climate.toggle("auto")
    wait_signal(car, Signal.AUTO, True)
    climate.wait_checked("auto", True)

    climate.fan_up()
    wait_signal(car, Signal.FAN, 4)
    wait_signal(car, Signal.AUTO, False)
    climate.wait_checked("auto", False)


@pytest.mark.req("HVAC-05")
@pytest.mark.sanity
@pytest.mark.parametrize("where, signal, other", [
    ("defrost_front", Signal.DEFROST_FRONT, Signal.DEFROST_REAR),
    ("defrost_rear", Signal.DEFROST_REAR, Signal.DEFROST_FRONT),
])
def test_defrost_changes_only_its_window(app, car, where, signal, other):
    """앞 유리 김서림 제거를 누르면 앞 유리 신호만, 뒤를 누르면 뒤 유리 신호만 켜집니다."""
    climate = app.climate()
    climate.toggle(where)
    wait_signal(car, signal, True)
    assert car.signal(other) is False
    climate.wait_checked(where, True)

    car.set_signal(signal, False)  # 하위 → 상위: 차량이 끄면 화면도 꺼진다
    climate.wait_checked(where, False)


# ---------------- 좌석 열선 ----------------

@pytest.mark.req("HVAC-05")
@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_seat_heat_cycles_levels_on_vehicle(app, car, seat):
    """열선 버튼을 누를 때마다 꺼짐, 2단, 1단, 꺼짐 순서로 바뀝니다.
    다른 좌석의 열선은 그대로입니다.
    """
    other = Seat.PASSENGER if seat == Seat.DRIVER else Seat.DRIVER
    climate = app.climate()
    assert climate.seat_heat(seat) == 0

    for expected in (2, 1, 0):
        climate.tap_seat_heat(seat)
        wait_signal(car, Signal.heat(seat), expected)
        wait_until(lambda: climate.seat_heat(seat) == expected, what=f"{seat.tag} 열선 표시 {expected}단")
    assert car.signal(Signal.heat(other)) == 0


@pytest.mark.req("HVAC-05")
@pytest.mark.sanity
def test_seat_heat_signal_is_shown_everywhere(app, car):
    """차량의 열선 단계가 공조 화면, 아래 바, 빠른 제어 세 곳에 같은 값으로 보입니다."""
    climate = app.climate()
    car.set_signal(Signal.HEAT_DRIVER, 1)
    wait_until(lambda: climate.seat_heat(Seat.DRIVER) == 1, what="공조 화면 운전석 열선 1단")
    wait_until(lambda: app.bar().seat_heat(Seat.DRIVER) == 1, what="아래 바 운전석 열선 1")
    assert app.bar().seat_heat(Seat.PASSENGER) == 0
    app.vehicle_controls().wait_text("qc_seat_heat_value", "1단")


@pytest.mark.req("HVAC-05", "UI-01")
@pytest.mark.regression
def test_bottom_bar_seat_heat_works_from_any_screen(app, car):
    """아래 바의 열선 버튼은 다른 앱을 보고 있을 때 눌러도 차량 신호를 바꿉니다."""
    app.media()
    bar = app.bar()
    bar.tap_seat_heat(Seat.PASSENGER)
    wait_signal(car, Signal.HEAT_PASSENGER, 2)
    wait_until(lambda: bar.seat_heat(Seat.PASSENGER) == 2, what="아래 바 조수석 열선 2")
    assert car.signal(Signal.HEAT_DRIVER) == 0


@pytest.mark.req("VOICE-01", "HVAC-05")
@pytest.mark.regression
def test_assistant_seat_heat_follows_speaker_zone(app, car):
    """조수석에서 AI 어시스턴트에 '열선 켜줘'라고 하면 조수석 열선 신호만 올라갑니다."""
    assistant = app.assistant()
    assistant.zone(Seat.PASSENGER)
    reply = assistant.say("열선 켜줘")
    assert "조수석" in reply
    wait_signal(car, Signal.HEAT_PASSENGER, 2)
    assert car.signal(Signal.HEAT_DRIVER) == 0


# ---------------- 도어 잠금 ----------------

@pytest.mark.req("BODY-01")
@pytest.mark.sanity
def test_door_lock_button_drives_every_door(app, car):
    """빠른 제어의 도어 버튼을 누르면 네 문의 DOOR_LOCK이 함께 바뀝니다."""
    qc = app.vehicle_controls()
    assert qc.value("door_lock") == "잠김"

    assert qc.toggle("door_lock") == "열림"
    wait_until(lambda: not any(car.signal_all(Signal.DOORS_LOCKED)), what="전 도어 잠금 해제")

    assert qc.toggle("door_lock") == "잠김"
    wait_until(lambda: all(car.signal_all(Signal.DOORS_LOCKED)), what="전 도어 잠김")


@pytest.mark.req("BODY-01")
@pytest.mark.sanity
def test_door_lock_signal_is_shown(app, car):
    """키나 도어 스위치로 차량 쪽에서 문이 열리면 화면의 도어 표시도 바뀝니다."""
    qc = app.vehicle_controls()
    car.set_signal(Signal.DOORS_LOCKED, False)
    qc.wait_text("qc_door_lock_value", "열림")
    car.set_signal(Signal.DOORS_LOCKED, True)
    qc.wait_text("qc_door_lock_value", "잠김")


# ---------------- 주행 가능 거리 · 배터리 · 외기 온도 ----------------

@pytest.mark.req("ENERGY-01")
@pytest.mark.sanity
def test_energy_signals_are_shown_on_cluster(app, car):
    """주행 가능 거리, 배터리, 외기 온도 신호가 주행 정보에 보입니다.
    미터는 km로, Wh는 %로 바꿔 보여 줍니다.
    """
    cluster = app.cluster()
    wait_until(lambda: (cluster.range_km(), cluster.battery_percent()) == (320, 80), what="기준 값 320 km · 80 %")
    wait_until(lambda: cluster.outside_temperature() == 18.0, what="외기 온도 18.0°C")
    assert not cluster.low_range_warning()

    car.set_signals({Signal.RANGE_KM: 154.0, Signal.BATTERY_PCT: 42.0, Signal.OUTSIDE_C: -3.5})
    wait_until(lambda: (cluster.range_km(), cluster.battery_percent()) == (154, 42), what="154 km · 42 %")
    wait_until(lambda: cluster.outside_temperature() == -3.5, what="외기 온도 -3.5°C")


@pytest.mark.req("ENERGY-02")
@pytest.mark.sanity
@pytest.mark.parametrize("range_km, low", [(31.0, False), (30.0, True), (29.0, True)])
def test_low_range_threshold(app, car, range_km, low):
    """주행 가능 거리가 30 km 이하로 떨어지면 '충전 필요'와 충전소 안내 카드가 뜹니다.
    31 km에서는 뜨지 않습니다.
    """
    cluster = app.cluster()
    car.set_signal(Signal.RANGE_KM, range_km)
    wait_until(lambda: cluster.range_km() == int(range_km), what=f"주행 가능 거리 {range_km:g} km")
    wait_until(lambda: cluster.low_range_warning() == low, what=f"충전 필요 표시 {low}")
    assert app.visible("low_range_card") == low


@pytest.mark.req("ENERGY-02", "NAV-01")
@pytest.mark.sanity
def test_low_range_card_starts_guidance_to_nearest_charger(app, car):
    """주행 가능 거리가 부족해지면 충전소 카드가 뜨고, 누르면 가장 가까운 충전소로 안내를 시작합니다.
    글자 검색이 막힌 주행 중에도 카드는 한 번에 누를 수 있어야 합니다.
    """
    car.drive(50.0)
    app.wait_visible("restriction_banner")
    car.set_signal(Signal.RANGE_KM, 22.0)
    app.wait_visible("low_range_card")
    assert app.text("low_range_text") == "주행 가능 거리 22 km"
    assert app.text("low_range_charger").startswith("판교 급속 충전소")

    app.tap("low_range_navigate")
    app.wait_text("nav_dest_name", "판교 급속 충전소")
    app.find("nav_remaining")
    app.wait_visible("low_range_card", expected=False)  # 안내 중에는 다시 권하지 않는다


@pytest.mark.req("ENERGY-02")
@pytest.mark.regression
def test_low_range_is_recorded_in_notifications(app, car):
    """주행 가능 거리 부족은 알림 센터에도 남습니다.
    그때 화면을 보지 못했어도 나중에 확인할 수 있습니다.
    """
    car.set_signal(Signal.RANGE_KM, 12.0)
    app.wait_visible("notification_badge")
    panel = app.notifications()
    assert panel.titles()[0] == "주행 가능 거리 부족"
    panel.close()


@pytest.mark.req("ENERGY-02")
@pytest.mark.regression
def test_range_recovers_after_charging(app, car):
    """충전해서 주행 가능 거리가 늘어나면 경고와 카드가 사라져야 합니다."""
    cluster = app.cluster()
    car.set_signal(Signal.RANGE_KM, 10.0)
    app.wait_visible("low_range_card")

    car.set_signals({Signal.RANGE_KM: 300.0, Signal.BATTERY_PCT: 75.0})
    app.wait_visible("low_range_card", expected=False)
    wait_until(lambda: not cluster.low_range_warning(), what="충전 필요 표시 사라짐")
    # 거리와 배터리는 서로 다른 신호라 따로 도착한다 → 바로 assert 하지 않고 기다린다 (8단계 회귀에서 한 번 실패)
    wait_until(lambda: cluster.battery_percent() == 75, what="배터리 75 %")


@pytest.mark.req("ENERGY-01", "SET-01")
@pytest.mark.regression
def test_range_follows_speed_unit_setting(app, car):
    """속도 단위를 mph로 바꾸면 주행 가능 거리도 마일로 보입니다.
    320 km는 199 mi입니다.
    """
    settings = app.settings()
    settings.toggle("unit_mph")
    cluster = app.cluster()
    wait_until(lambda: (cluster.range_km(), cluster.range_unit()) == (199, "mi"), what="199 mi")
