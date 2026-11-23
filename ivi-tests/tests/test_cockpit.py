"""화면 틀을 확인합니다. 아래 바 공조, 온도 동기화, 주행 정보, 분할 화면, 빠른 제어, 알림이 대상입니다."""

import pytest

from ivi.vehicle import Seat
from ivi.waits import stays, wait_until, wait_value


@pytest.mark.req("HVAC-01", "UI-01")
@pytest.mark.regression
@pytest.mark.parametrize("seat", list(Seat), ids=lambda s: s.tag)
def test_bottom_bar_temperature_drives_vehicle(app, car, seat):
    """아래 바의 온도 버튼은 어느 화면에서든 차량 온도를 바꿉니다.
    차량 쪽 값이 바뀌면 아래 바 숫자도 따라 바뀝니다.
    """
    app.media()
    bar = app.bar()
    bar.wait_temperature(seat, 22.0)
    bar.increase(seat)
    wait_value(lambda: car.temperature(seat), 22.5, what=f"차량 {seat.tag} 온도")

    car.set_temperature(seat, 18.0)
    bar.wait_temperature(seat, 18.0)


@pytest.mark.req("HVAC-06")
@pytest.mark.regression
def test_sync_mirrors_driver_temperature_to_passenger(app, car):
    """SYNC를 켜면 조수석 온도가 운전석과 같아지고, 그 뒤 운전석을 바꾸면 조수석 차량 값도 같이 바뀝니다."""
    car.set_temperature(Seat.DRIVER, 24.0)
    climate = app.climate()
    climate.wait_temperature(Seat.DRIVER, 24.0)
    climate.tap("climate_sync")
    wait_value(lambda: car.temperature(Seat.PASSENGER), 24.0, what="동기화: 차량 조수석 온도")

    climate.increase(Seat.DRIVER)
    wait_value(lambda: (car.temperature(Seat.DRIVER), car.temperature(Seat.PASSENGER)), (24.5, 24.5),
               what="차량 온도 (운전석, 조수석)")


@pytest.mark.req("HVAC-06")
@pytest.mark.regression
def test_passenger_change_releases_sync(app, car):
    """동기화 중에 조수석 온도를 직접 바꾸면 동기화가 풀립니다.
    그 뒤로는 운전석을 바꿔도 운전석만 바뀝니다.
    """
    climate = app.climate()
    climate.tap("climate_sync")
    climate.decrease(Seat.PASSENGER)
    wait_value(lambda: car.temperature(Seat.PASSENGER), 21.5, what="차량 조수석 온도")
    climate.increase(Seat.DRIVER)
    wait_value(lambda: car.temperature(Seat.DRIVER), 22.5, what="차량 운전석 온도")
    stays(lambda: car.temperature(Seat.PASSENGER) == 21.5, what="차량 조수석 온도 21.5 유지")


@pytest.mark.req("DRIVE-01")
@pytest.mark.regression
def test_trip_distance_follows_speed_signal(app, car):
    """현 주행 정보의 거리는 속도 신호에 따라 늘고, 차를 세우면 멈춥니다.
    120 km/h로 3초를 달리면 0.1 km쯤 늘어납니다.
    """
    cluster = app.cluster()
    assert cluster.trip_km() == 0.0
    car.drive(120.0)
    wait_until(lambda: cluster.trip_km() >= 0.1, timeout=15, what="주행 거리 0.1 km 이상")
    car.park()
    car.wait_restricted(False)
    parked = cluster.trip_km()
    stays(lambda: cluster.trip_km() == parked, duration=3, what=f"정차 중 주행 거리 {parked} km 유지")


@pytest.mark.req("DRIVE-01")
@pytest.mark.regression
def test_lane_assist_indicator_follows_speed(app, car):
    """운전자 보조 표시는 D 기어에서 30 km/h 이상이면 '작동', 그보다 느리면 '대기'가 됩니다.
    실제 ADAS 신호가 아니라 화면 연출입니다.
    """
    cluster = app.cluster()
    car.drive(50.0)
    cluster.wait_text("adas_state", "차로 유지 보조 작동")
    car.drive(20.0)
    cluster.wait_text("adas_state", "차로 유지 보조 대기")


@pytest.mark.req("UI-01")
@pytest.mark.regression
def test_utility_widget_pages(app):
    """주행 정보 위젯을 넘기면 현 주행 정보, 경로, 타이어 공기압 순서로 바뀌고 다시 처음으로 돌아옵니다."""
    cluster = app.cluster()
    assert cluster.widget_title() == "현 주행 정보"
    assert cluster.next_widget() == "경로"
    assert cluster.next_widget() == "타이어 공기압"
    assert cluster.next_widget() == "현 주행 정보"


@pytest.mark.req("UI-01")
@pytest.mark.regression
def test_split_screen_toggle(app):
    """홈 화면을 내비와 오디오가 같이 있는 분할 화면, 내비만 있는 화면으로 바꿀 수 있습니다.
    두 화면 모두에서 내비를 쓸 수 있습니다.
    """
    home = app.home()
    assert home.split()
    home.toggle_split()
    assert not home.split()
    home.find("nav_search")
    home.toggle_split()
    assert home.split()


@pytest.mark.req("DRIVE-03")
@pytest.mark.regression
def test_quick_control_mirror_locked_while_driving(app, car):
    """주행 중에는 빠른 제어의 사이드 미러 접기와 트렁크가 막히지만, 도어 잠금은 쓸 수 있습니다."""
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


@pytest.mark.req("DRIVE-03")
@pytest.mark.regression
def test_folded_mirror_can_be_unfolded_while_driving(app, car):
    """주행 중에 막는 것은 사이드 미러를 '접는' 것입니다.
    정차 중에 접어 둔 미러는 주행 중에도 펼 수 있고, 펴고 나면 다시 접을 수 없습니다.
    """
    qc = app.vehicle_controls()
    assert qc.toggle("mirror") == "접힘"

    car.drive(50.0)
    qc.wait_visible("qc_restricted_notice")
    assert qc.can_toggle("mirror"), "주행 중에 접힌 미러를 펼 수 없다"
    assert qc.toggle("mirror") == "펼침"
    qc.wait_enabled("qc_mirror", False)


@pytest.mark.req("UI-01")
@pytest.mark.regression
def test_notifications_record_guidance_and_restriction(app, car):
    """경로 안내 시작과 주행 제한이 알림 센터에 쌓이고, 알림 센터를 열면 배지가 사라집니다."""
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


@pytest.mark.req("UI-01")
@pytest.mark.regression
def test_clearing_notifications_leaves_empty_panel(app, car):
    """알림 센터에서 '모두 지우기'를 누르면 목록이 비고 '새 알림이 없습니다'가 보입니다.
    닫았다 다시 열어도 지운 알림이 돌아오지 않습니다.
    """
    car.drive(50.0)
    app.wait_visible("restriction_banner")
    app.wait_visible("notification_badge")
    panel = app.notifications()
    assert panel.titles(), "주행 제한 알림이 없다"

    panel.clear()
    assert panel.titles() == []
    panel.close()
    assert not app.visible("notification_badge")
    panel = app.notifications()
    panel.find("notification_empty")
    assert panel.titles() == []
    panel.close()


@pytest.mark.req("UI-01")
@pytest.mark.regression
def test_recent_app_slot(app):
    """앱 목록에서 라디오를 연 뒤 다른 앱으로 넘어가도 아래 바에 라디오가 남아 있어 바로 돌아갈 수 있습니다."""
    app.radio()
    app.media()
    app.tap("nav_recent")
    app.find("radio_freq")
