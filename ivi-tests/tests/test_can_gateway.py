"""가상 CAN 버스의 ECU 프레임이 게이트웨이와 VHAL을 거쳐 화면까지 오는지, 화면에서 바꾼 공조 값이 CAN으로 나가는지 확인합니다.

모의 환경이다. ECU 와 CAN 버스는 PC 안의 python-can virtual 버스이고, 프레임 정의는 dbc/opencabin.dbc 다.
게이트웨이(ivi/can_gateway.py)가 실제 차에서 CAN 신호를 VHAL 로 올려 주는 자리를 맡는다.
"""
from types import SimpleNamespace

import pytest

from ivi.can_gateway import GEAR_D, GEAR_P, CanGateway, EcuNode, virtual_bus, wait_for_frame
from ivi.vehicle import Seat
from ivi.waits import wait_until, wait_value


@pytest.fixture
def can_net(app, device):
    channel = f"e2e-{device.serial}"
    gateway = CanGateway(virtual_bus(channel), device.vehicle, tx_period=1.0)
    ecu_bus, listener = virtual_bus(channel), virtual_bus(channel)
    gateway.start()
    net = SimpleNamespace(gateway=gateway, ecu=EcuNode(ecu_bus, gateway.db), listener=listener, db=gateway.db)
    yield net
    net.ecu.stop()
    gateway.stop()
    for bus in (gateway.bus, ecu_bus, listener):
        bus.shutdown()


@pytest.mark.req("NET-01", "DRIVE-01")
@pytest.mark.sanity
def test_can_drive_frames_reach_screen(app, can_net):
    """VCU가 CAN으로 기어 D, 속도 50 km/h를 100 ms마다 보내면 화면 속도가 50이 되고 주행 제한 배지가 뜹니다.
    P로 바꿔 보내면 0으로 돌아옵니다. 같은 값이 계속 와도 VHAL에는 한 번만 넣습니다.
    """
    home = app.home()
    can_net.ecu.send("VCU_DriveStatus", period=0.1, VehicleSpeed=50.0, GearSelect=GEAR_D)
    home.wait_text("speed_value", "50")
    app.wait_visible("restriction_banner")

    can_net.ecu.send("VCU_DriveStatus", period=0.1, VehicleSpeed=0.0, GearSelect=GEAR_P)
    home.wait_text("speed_value", "0")
    app.wait_visible("restriction_banner", expected=False)
    drives = [values for name, values in can_net.gateway.applied if name == "VCU_DriveStatus"]
    assert len(drives) == 2, f"같은 프레임을 여러 번 넣었다: {drives}"
    assert can_net.gateway.errors == []


@pytest.mark.req("NET-01", "ENERGY-02", "BODY-01")
@pytest.mark.regression
def test_can_battery_and_door_frames_reach_screen(app, can_net):
    """BMS가 주행 가능 거리 25 km를 보내면 '충전 필요'가 뜨고, BCM이 문 열림을 보내면 빠른 제어의 도어 표시가 '열림'이 됩니다."""
    can_net.ecu.send("BMS_Status", period=0.5, BatterySoc=8.0, RangeRemaining=25.0)
    cluster = app.cluster()
    wait_value(lambda: cluster.range_km(), 25, what="주행 가능 거리(km)")
    wait_until(cluster.low_range_warning, what="충전 필요 표시")

    can_net.ecu.send("BCM_Status", period=0.5, DoorsLocked=0, OutsideTemp=-3.0)
    controls = app.vehicle_controls()
    controls.wait_text("qc_door_lock_value", "열림")
    assert can_net.gateway.errors == []


@pytest.mark.req("NET-02", "HVAC-01")
@pytest.mark.sanity
def test_climate_button_goes_out_on_can(app, can_net):
    """화면에서 운전석 온도를 한 칸 올리면 게이트웨이가 보내는 IVI_HvacStatus 프레임의 운전석 온도가 22.5°C가 됩니다."""
    climate = app.climate()
    climate.wait_temperature(Seat.DRIVER, 22.0)
    climate.increase(Seat.DRIVER)
    values = wait_for_frame(can_net.listener, can_net.db, "IVI_HvacStatus", lambda v: v["DriverTempSet"] == 22.5, timeout=15)
    assert values["PassengerTempSet"] == 22.0
    assert can_net.gateway.errors == []
