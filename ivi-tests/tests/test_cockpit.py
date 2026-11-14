"""화면 틀 E2E (7단계, Pleos Connect 구조): 아래 바 공조 · 동기화 · 주행 정보 · 분할 화면 · 빠른 제어 · 알림."""
import time

import pytest

from ivi.vehicle import Seat
from ivi.waits import wait_until


@pytest.mark.sanity
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_bottom_bar_temperature_drives_vehicle(app, car, seat):
    """아래 바 ‹ › 는 어느 화면에서든 차량 온도를 바꾼다 (상위 → 하위), 차량 값이 바뀌면 아래 바도 따라간다 (하위 → 상위)."""
    app.media()
    bar = app.bar()
    bar.wait_temperature(seat, 22.0)
    bar.increase(seat)
    wait_until(lambda: car.temperature(seat) == 22.5, what=f"차량 {seat.tag} 22.5")

    car.set_temperature(seat, 18.0)
    bar.wait_temperature(seat, 18.0)


@pytest.mark.sanity
def test_sync_mirrors_driver_temperature_to_passenger(app, car):
    """SYNC: 켜면 조수석이 운전석 값으로 맞춰지고, 운전석을 바꾸면 조수석 차량 값도 같이 바뀐다."""
    car.set_temperature(Seat.DRIVER, 24.0)
    climate = app.climate()
    climate.wait_temperature(Seat.DRIVER, 24.0)
    climate.tap("climate_sync")
    wait_until(lambda: car.temperature(Seat.PASSENGER) == 24.0, what="동기화: 조수석 24.0")

    climate.increase(Seat.DRIVER)
    wait_until(lambda: car.temperature(Seat.DRIVER) == 24.5 and car.temperature(Seat.PASSENGER) == 24.5, what="두 좌석 24.5")


@pytest.mark.regression
def test_passenger_change_releases_sync(app, car):
    """동기화 중 조수석을 직접 바꾸면 동기화가 풀린다 (이후 운전석만 바뀐다)."""
    climate = app.climate()
    climate.tap("climate_sync")
    climate.decrease(Seat.PASSENGER)
    wait_until(lambda: car.temperature(Seat.PASSENGER) == 21.5, what="조수석 21.5")
    climate.increase(Seat.DRIVER)
    wait_until(lambda: car.temperature(Seat.DRIVER) == 22.5, what="운전석 22.5")
    assert car.temperature(Seat.PASSENGER) == 21.5


@pytest.mark.sanity
def test_trip_distance_follows_speed_signal(app, car):
    """현 주행 정보: 거리는 속도 신호로 늘고, 정차하면 멈춘다 (120 km/h ≈ 3초에 0.1 km)."""
    cluster = app.cluster()
    assert cluster.trip_km() == 0.0
    car.drive(120.0)
    wait_until(lambda: cluster.trip_km() >= 0.1, timeout=15, what="주행 거리 0.1 km 이상")
    car.park()
    car.wait_restricted(False)
    parked = cluster.trip_km()
    time.sleep(3)  # '변하지 않음' 확인이라 조건 대기로 바꿀 수 없다
    assert cluster.trip_km() == parked


@pytest.mark.regression
def test_lane_assist_indicator_follows_speed(app, car):
    """운전자 보조 표시(화면 연출): D 에서 30 km/h 이상이면 작동, 그 아래면 대기."""
    cluster = app.cluster()
    car.drive(50.0)
    cluster.wait_text("adas_state", "차로 유지 보조 작동")
    car.drive(20.0)
    cluster.wait_text("adas_state", "차로 유지 보조 대기")


@pytest.mark.regression
def test_utility_widget_pages(app):
    cluster = app.cluster()
    assert cluster.widget_title() == "현 주행 정보"
    assert cluster.next_widget() == "경로"
    assert cluster.next_widget() == "타이어 공기압"
    assert cluster.next_widget() == "현 주행 정보"


@pytest.mark.regression
def test_split_screen_toggle(app):
    """홈: 분할(내비 + 오디오) ↔ 단일(내비만). 내비는 두 모드 모두에서 쓸 수 있다."""
    home = app.home()
    assert home.split()
    home.toggle_split()
    assert not home.split()
    home.find("nav_search")
    home.toggle_split()
    assert home.split()


@pytest.mark.sanity
def test_quick_control_mirror_locked_while_driving(app, car):
    """빠른 제어: 주행 중에는 사이드 미러 접기 · 트렁크가 막히고, 도어 잠금은 된다."""
    qc = app.vehicle_controls()
    assert qc.can_toggle("mirror") and qc.can_toggle("trunk")

    car.drive(50.0)
    qc.wait_enabled("qc_mirror", False)
    assert not qc.can_toggle("trunk")
    assert qc.visible("qc_restricted_notice")
    assert qc.toggle("door_lock") == "열림"

    car.park()
    qc.wait_enabled("qc_mirror", True)
    assert qc.toggle("mirror") == "접힘"


@pytest.mark.regression
def test_notifications_record_guidance_and_restriction(app, car):
    """알림 센터: 경로 안내 시작 · 주행 제한이 쌓이고, 열면 배지가 사라진다."""
    nav = app.navigation()
    nav.favorite("work")
    nav.start()
    car.drive(50.0)
    app.wait_visible("restriction_banner")
    app.wait_visible("notification_badge")

    panel = app.notifications()
    titles = panel.titles()
    assert titles[:2] == ["주행 중 제한", "경로 안내 시작"], titles
    assert not app.visible("notification_badge")
    panel.close()


@pytest.mark.regression
def test_recent_app_slot(app):
    """아래 바 '이전 실행 앱': 앱 목록에서 연 라디오가 다른 앱으로 가면 아래 바에 남아 바로 돌아갈 수 있다."""
    app.radio()
    app.media()
    app.tap("nav_recent")
    app.find("radio_freq")
