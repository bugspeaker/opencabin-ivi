"""내비게이션 E2E: 경로 안내가 차량 속도 신호로 진행되고, 주행 중에는 글자 입력(검색)이 막힌다."""
import time

import pytest

from ivi.waits import wait_until


@pytest.mark.sanity
def test_guidance_counts_down_with_vehicle_speed(app, car):
    """하위 → 상위: 차량 속도 신호만큼 남은 거리가 줄어든다 (120 km/h ≈ 3초에 0.1 km)."""
    nav = app.navigation()
    nav.pick(0)  # 집 12.4 km
    nav.start()
    start = nav.remaining_km()
    assert start == pytest.approx(12.4)
    assert "앞" in nav.maneuver()

    car.drive(120.0)
    wait_until(lambda: nav.remaining_km() <= start - 0.2, timeout=20, what="남은 거리 0.2 km 이상 감소")


@pytest.mark.sanity
def test_parked_vehicle_does_not_advance_route(app, car):
    """정차 중에는 남은 거리가 그대로다 (시간이 아니라 속도 신호로 진행)."""
    nav = app.navigation()
    nav.pick(1)  # 회사 8.7 km
    nav.start()
    assert nav.remaining_km() == pytest.approx(8.7)
    time.sleep(3)  # 일부러 기다린다: 정차 중에는 시간이 지나도 줄면 안 된다 (조건 대기로 바꿀 수 없는 '변하지 않음' 확인)
    assert nav.remaining_km() == pytest.approx(8.7)


@pytest.mark.sanity
def test_search_locked_while_driving_but_favorites_work(app, car):
    """주행 중 UX 제한: 검색 입력은 막히고, 즐겨찾기로는 목적지를 고를 수 있다."""
    nav = app.navigation()
    assert nav.search_enabled()

    car.drive(50.0)
    nav.wait_enabled("nav_search", False)
    assert nav.visible("nav_search_locked")

    nav.favorite("home")
    assert nav.destination() == "집"


@pytest.mark.sanity
def test_search_filters_destinations(app):
    nav = app.navigation()
    nav.search("역")
    wait_until(lambda: nav.results() == ["판교역", "서울역"], what="'역' 검색 결과")


@pytest.mark.regression
def test_arrival(app, car):
    nav = app.navigation()
    nav.search("편의점")
    wait_until(lambda: nav.results() == ["편의점"], what="'편의점' 검색 결과")
    nav.pick(5)  # 0.1 km
    nav.start()
    car.drive(120.0)
    nav.wait_visible("nav_arrived", timeout=20)


@pytest.mark.regression
def test_stop_guidance_returns_to_search_and_clears_cluster_route(app):
    """7단계: 홈 위젯 대신 주행 정보(왼쪽)에 경로를 보여 준다. 다른 앱을 보고 있어도 보이고, 안내를 끝내면 사라진다."""
    nav = app.navigation()
    nav.pick(1)
    nav.start()
    app.media()
    wait_until(lambda: (app.cluster().route() or "").startswith("회사까지"), what="주행 정보에 경로 표시")

    nav = app.navigation()
    nav.stop()
    nav.wait_visible("nav_search")
    app.wait_visible("cluster_route", expected=False)
