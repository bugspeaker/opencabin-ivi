"""경로 안내가 차량 속도에 맞춰 진행되는지, 주행 중에 검색 입력이 막히는지 확인합니다."""
import time

import pytest

from ivi.waits import wait_until


@pytest.mark.sanity
def test_guidance_counts_down_with_vehicle_speed(app, car):
    """경로 안내의 남은 거리가 차량 속도 신호만큼 줄어듭니다.
    120 km/h로 3초를 달리면 0.1 km쯤 줄어듭니다.
    """
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
    """차가 서 있으면 남은 거리가 줄지 않습니다.
    안내가 시간이 아니라 속도 신호를 따라 진행된다는 것을 확인합니다.
    """
    nav = app.navigation()
    nav.pick(1)  # 회사 8.7 km
    nav.start()
    assert nav.remaining_km() == pytest.approx(8.7)
    time.sleep(3)  # 일부러 기다린다: 정차 중에는 시간이 지나도 줄면 안 된다 (조건 대기로 바꿀 수 없는 '변하지 않음' 확인)
    assert nav.remaining_km() == pytest.approx(8.7)


@pytest.mark.sanity
def test_search_locked_while_driving_but_favorites_work(app, car):
    """주행 중에는 검색 입력이 막히지만, 즐겨찾기로는 목적지를 고를 수 있습니다."""
    nav = app.navigation()
    assert nav.search_enabled()

    car.drive(50.0)
    nav.wait_enabled("nav_search", False)
    assert nav.visible("nav_search_locked")

    nav.favorite("home")
    assert nav.destination() == "집"


@pytest.mark.sanity
def test_search_filters_destinations(app):
    """'역'으로 검색하면 판교역과 서울역만 남습니다."""
    nav = app.navigation()
    nav.search("역")
    wait_until(lambda: nav.results() == ["판교역", "서울역"], what="'역' 검색 결과")


@pytest.mark.regression
def test_arrival(app, car):
    """0.1 km 떨어진 편의점으로 안내를 시작하고 120 km/h로 달리면 도착 화면이 뜹니다."""
    nav = app.navigation()
    nav.search("편의점")
    wait_until(lambda: nav.results() == ["편의점"], what="'편의점' 검색 결과")
    nav.pick(5)  # 0.1 km
    nav.start()
    car.drive(120.0)
    nav.wait_visible("nav_arrived", timeout=20)


@pytest.mark.regression
def test_stop_guidance_returns_to_search_and_clears_cluster_route(app):
    """안내 중인 경로는 왼쪽 주행 정보에 보이고, 다른 앱을 보고 있어도 남아 있습니다.
    안내를 끝내면 검색 화면으로 돌아가고 경로 표시도 사라집니다.
    """
    nav = app.navigation()
    nav.pick(1)
    nav.start()
    app.media()
    wait_until(lambda: (app.cluster().route() or "").startswith("회사까지"), what="주행 정보에 경로 표시")

    nav = app.navigation()
    nav.stop()
    nav.wait_visible("nav_search")
    app.wait_visible("cluster_route", expected=False)
