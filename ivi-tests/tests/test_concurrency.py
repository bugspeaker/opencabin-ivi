"""한 기능을 쓰는 동안 다른 기능을 조작해도 서로의 상태가 바뀌지 않는지 확인합니다 (동시 조작).

차 안에서는 음악을 틀어 둔 채 공조를 바꾸고, 경로 안내를 받으며 달리고, 통화 중에 온도를 만집니다. 기능마다의 테스트는
그 기능만 보므로, 여기서는 뒤에서 도는 기능(음악, 안내, 통화)의 상태가 다른 조작 뒤에도 그대로인지 봅니다.
화면 조작과 차량 쪽 변경이 겹칠 때와 버튼을 빠르게 누를 때 화면과 차량 신호가 같은 값으로 끝나는지도 봅니다.
"""
import threading

import pytest

from ivi.vehicle import Seat, Signal
from ivi.waits import stays, wait_until, wait_value

pytestmark = pytest.mark.regression


def wait_signal(car, name, expected):
    wait_value(lambda: car.signal(name), expected, what=f"차량 신호 {name}")


def route_km(cluster):
    """'회사까지 8.6 km' → 8.6"""
    return float(cluster.route().split()[-2])


@pytest.mark.req("SYS-02", "MEDIA-02", "HVAC-01")
def test_music_keeps_playing_while_climate_is_operated(app, car):
    """음악을 틀어 둔 채 공조 화면에서 두 좌석 온도, 풍량, A/C를 바꿉니다. 값은 모두 차량에 들어가고,
    음악은 같은 곡으로 계속 재생 중입니다. 음악 화면을 보는 동안 차량 쪽에서 온도가 바뀌어도 재생은 그대로입니다."""
    media = app.media()
    title = media.select_track(2)
    media.wait_text("playback_state", "재생 중")

    climate = app.climate()
    climate.increase(Seat.DRIVER)
    climate.decrease(Seat.PASSENGER)
    climate.fan_up()
    climate.toggle("ac")
    wait_value(lambda: car.temperature(Seat.DRIVER), 22.5, what="차량 운전석 온도")
    wait_value(lambda: car.temperature(Seat.PASSENGER), 21.5, what="차량 조수석 온도")
    wait_signal(car, Signal.FAN, 4)
    wait_signal(car, Signal.AC, False)

    media = app.media()
    media.wait_text("now_playing_title", title)
    media.wait_text("playback_state", "재생 중")

    car.set_temperature(Seat.DRIVER, 24.0)  # 음악 화면을 보는 동안 차량 쪽(다른 좌석의 조작 등)에서 바뀐다
    app.bar().wait_temperature(Seat.DRIVER, 24.0)
    stays(lambda: media.playback_state() == "재생 중" and media.now_playing() == title, what=f"'{title}' 재생 중")


@pytest.mark.req("SYS-02", "NAV-01", "MEDIA-02", "HVAC-01")
def test_guidance_and_music_continue_while_temperature_changes_on_the_move(app, car):
    """경로 안내를 받고 음악을 들으며 120 km/h로 달리는 중에 아래 바로 두 좌석 온도를 바꿉니다.
    온도는 차량에 들어가고, 안내는 같은 목적지로 계속 줄고, 음악은 같은 곡으로 재생 중입니다."""
    nav = app.navigation()
    nav.pick(1)  # 회사 8.7 km
    nav.start()
    media = app.media()
    title = media.select_track(4)
    media.wait_text("playback_state", "재생 중")

    car.drive(120.0)
    app.wait_visible("restriction_banner")
    bar = app.bar()
    bar.increase(Seat.DRIVER)
    bar.decrease(Seat.PASSENGER)
    wait_value(lambda: car.temperature(Seat.DRIVER), 22.5, what="차량 운전석 온도")
    wait_value(lambda: car.temperature(Seat.PASSENGER), 21.5, what="차량 조수석 온도")

    cluster = app.cluster()
    assert cluster.route().startswith("회사")
    wait_until(lambda: route_km(cluster) <= 8.5, timeout=20, what="안내 남은 거리 8.5 km 이하")
    media.wait_text("now_playing_title", title)
    media.wait_text("playback_state", "재생 중")

    nav = app.navigation()
    assert nav.destination() == "회사" and nav.remaining_km() < 8.7


@pytest.mark.req("SYS-02", "MEDIA-01", "HVAC-01")
def test_climate_works_during_call_and_music_resumes_after(app, car):
    """음악을 듣다가 전화를 겁니다. 통화하는 동안 공조 화면에서 온도와 풍량을 바꾸면 차량에 들어가고, 통화는 이어지고,
    음악은 '통화 중'으로 멈춰 있습니다. 통화를 끝내면 같은 곡이 다시 나오고 바꾼 공조 값은 그대로입니다."""
    media = app.media()
    title = media.select_track(1)
    media.wait_text("playback_state", "재생 중")
    phone = app.phone()
    phone.tab("contacts")
    name = phone.call_contact(0)

    climate = app.climate()
    climate.increase(Seat.DRIVER)
    climate.fan_up()
    wait_value(lambda: car.temperature(Seat.DRIVER), 22.5, what="차량 운전석 온도")
    wait_signal(car, Signal.FAN, 4)

    media = app.media()
    media.wait_text("playback_state", "통화 중")
    assert media.now_playing() == title
    phone = app.phone()
    assert phone.call_name() == name
    seconds = phone.call_seconds()
    wait_until(lambda: phone.call_seconds() > seconds, timeout=5, what="통화 시간이 계속 흐름")
    phone.end()

    media = app.media()
    media.wait_text("playback_state", "재생 중")
    assert media.now_playing() == title
    assert car.temperature(Seat.DRIVER) == 22.5 and car.signal(Signal.FAN) == 4


@pytest.mark.req("SYS-02", "HVAC-01")
def test_screen_and_vehicle_changes_at_once_end_in_same_value(app, car):
    """화면에서 운전석 +를 세 번 누르는 동안 차량 쪽에서도 운전석 온도를 세 번 바꿉니다(다른 스레드).
    어느 쪽이 마지막이든 화면과 차량 신호는 같은 값으로 끝나야 하고, 조수석은 그대로여야 합니다.
    둘이 다른 값에 머물면 화면이 차량과 어긋난 것입니다."""
    climate = app.climate()
    climate.wait_temperature(Seat.DRIVER, 22.0)
    errors = []

    def vehicle_side():
        try:
            for celsius in (25.0, 24.0, 26.0):
                car.set_temperature(Seat.DRIVER, celsius)
        except Exception as error:  # noqa: BLE001 - 주 스레드에서 다시 올린다
            errors.append(error)

    writer = threading.Thread(target=vehicle_side, name="vehicle-side")
    writer.start()
    for _ in range(3):
        climate.increase(Seat.DRIVER)
    writer.join(60)
    assert not writer.is_alive() and not errors, errors

    wait_until(lambda: climate.temperature(Seat.DRIVER) == car.temperature(Seat.DRIVER), what="화면과 차량 운전석 온도 일치")
    final = car.temperature(Seat.DRIVER)
    stays(lambda: climate.temperature(Seat.DRIVER) == car.temperature(Seat.DRIVER) == final, what=f"화면과 차량 {final}°C 유지")
    assert 16.0 <= final <= 28.0 and final * 2 == int(final * 2), f"범위 밖이거나 0.5°C 단위가 아니다: {final}"
    assert car.temperature(Seat.PASSENGER) == 22.0 and climate.temperature(Seat.PASSENGER) == 22.0


def quick_taps(screen, device, tag, count, gap=0.1):
    """버튼 가운데를 count 번 빠르게 누른다. 사람이 빠르게 누르는 간격(초당 8~10번)에 맞춰 누름 사이를 gap 초로 둔다.
    adb 셸 한 번에 input tap 과 sleep 을 이어 보낸다. 누름 하나는 에뮬레이터 15~20 ms, 태블릿 약 100 ms 다.
    Appium W3C 동작은 쓰지 않는다: AAOS 에뮬레이터에서 UiAutomator2 가 만드는 MOVE 이벤트 주입이 실패해
    동작 전체가 'Unable to perform W3C actions' 로 끝났다 (2026-11-24)."""
    rect = screen.find(tag).rect
    x, y = rect["x"] + rect["width"] // 2, rect["y"] + rect["height"] // 2
    device.adb.shell(f"; sleep {gap}; ".join([f"input tap {x} {y}"] * count))


@pytest.mark.req("SYS-02", "HVAC-02")
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_quick_taps_are_all_applied(app, car, device, seat):
    """+를 빠르게 네 번 누르면 네 번 모두 차량에 들어가 24.0°C가 되고 화면도 24.0°C입니다.
    앱이 차량에서 값이 돌아오기 전의 옛 값으로 다음 값을 계산하면 누른 것이 사라집니다."""
    climate = app.climate()
    climate.wait_temperature(seat, 22.0)
    quick_taps(climate, device, f"{seat.tag}_temp_up", 4)
    wait_value(lambda: car.temperature(seat), 24.0, what=f"차량 {seat.tag} 온도 (네 번 누름)")
    climate.wait_temperature(seat, 24.0)
    stays(lambda: car.temperature(seat) == 24.0, what=f"차량 {seat.tag} 24.0°C 유지")
