"""CAN 게이트웨이 (기기 없이). DBC 인코딩, 프레임을 차량 신호로 바꾸는 규칙, 가상 버스 위의 양방향 동작을 본다."""
import itertools
import time

import can
import pytest

from ivi.can_gateway import GEAR_D, GEAR_P, GEAR_R, CanGateway, EcuNode, load_db, virtual_bus, wait_for_frame
from ivi.vehicle import CABIN_DEFAULTS, Seat, Signal

_channels = itertools.count()


class FakeVehicle:
    def __init__(self):
        self.values = dict(CABIN_DEFAULTS)
        self.temps = {Seat.DRIVER: 22.0, Seat.PASSENGER: 22.0}
        self.calls = []

    def signal(self, name):
        return self.values[name]

    def set_signals(self, values):
        self.calls.append(("set_signals", dict(values)))
        self.values.update(values)

    def temperature(self, seat):
        return self.temps[seat]

    def drive(self, kmh=50.0):
        self.calls.append(("drive", kmh))

    def park(self):
        self.calls.append(("park",))

    def reverse(self):
        self.calls.append(("reverse",))


@pytest.fixture
def db():
    return load_db()


def test_dbc_encodes_signals_with_scale_and_offset(db):
    vcu = db.get_message_by_name("VCU_DriveStatus")
    data = vcu.encode({"VehicleSpeed": 50.0, "GearSelect": GEAR_D, "DriveCounter": 0})
    assert data[0] | data[1] << 8 == 5000  # 0.01 km/h 단위
    assert vcu.decode(data)["GearSelect"] == "D"

    hvac = db.get_message_by_name("IVI_HvacStatus")
    data = hvac.encode({"DriverTempSet": 22.5, "PassengerTempSet": 16.0, "AcOn": 1, "MaxAcOn": 0, "AutoOn": 0, "FanSpeed": 7})
    assert data[0] == 45 and data[1] == 32  # 0.5 °C 단위

    bcm = db.get_message_by_name("BCM_Status")
    assert bcm.decode(bcm.encode({"DoorsLocked": 0, "OutsideTemp": -3.5}))["OutsideTemp"] == -3.5  # 오프셋 -40


def test_drive_frames_reach_vehicle_once_per_change(db):
    car, ecu = FakeVehicle(), EcuNode(bus=None, db=db)
    gateway = CanGateway(bus=None, vehicle=car, db=db)
    frame = ecu.message("VCU_DriveStatus", VehicleSpeed=50.0, GearSelect=GEAR_D)
    assert gateway.handle(frame) is not None
    assert gateway.handle(frame) is None, "같은 값의 주기 프레임을 또 넣었다"
    gateway.handle(ecu.message("VCU_DriveStatus", VehicleSpeed=50.0, GearSelect=GEAR_D, DriveCounter=5))
    gateway.handle(ecu.message("VCU_DriveStatus", VehicleSpeed=0.0, GearSelect=GEAR_R))
    gateway.handle(ecu.message("VCU_DriveStatus", VehicleSpeed=0.0, GearSelect=GEAR_P))
    assert car.calls == [("drive", 50.0), ("reverse",), ("park",)]


def test_battery_and_body_frames_become_vehicle_signals(db):
    car, ecu = FakeVehicle(), EcuNode(bus=None, db=db)
    gateway = CanGateway(bus=None, vehicle=car, db=db)
    gateway.handle(ecu.message("BMS_Status", BatterySoc=8.0, RangeRemaining=25.0))
    gateway.handle(ecu.message("BCM_Status", DoorsLocked=0, OutsideTemp=-3.0))
    assert car.values[Signal.RANGE_KM] == 25.0 and car.values[Signal.BATTERY_PCT] == 8.0
    assert car.values[Signal.DOORS_LOCKED] is False and car.values[Signal.OUTSIDE_C] == -3.0


def test_unknown_and_own_frames_are_ignored(db):
    car = FakeVehicle()
    gateway = CanGateway(bus=None, vehicle=car, db=db)
    assert gateway.handle(can.Message(arbitration_id=0x7FF, data=bytes(8), is_extended_id=False)) is None
    assert gateway.handle(gateway.hvac_frame(gateway.hvac_values())) is None
    assert car.calls == []


def test_gateway_runs_both_directions_on_virtual_bus(db):
    channel = f"unit-{next(_channels)}"
    car = FakeVehicle()
    gateway = CanGateway(virtual_bus(channel), car, db, tx_period=0.1).start()
    ecu_bus, listener = virtual_bus(channel), virtual_bus(channel)
    ecu = EcuNode(ecu_bus, db)
    try:
        ecu.send("VCU_DriveStatus", period=0.01, VehicleSpeed=80.0, GearSelect=GEAR_D)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and ("drive", 80.0) not in car.calls:
            time.sleep(0.02)
        time.sleep(0.3)  # 그동안에도 같은 프레임이 30번쯤 더 온다
        assert car.calls.count(("drive", 80.0)) == 1

        car.temps[Seat.DRIVER] = 23.5
        values = wait_for_frame(listener, db, "IVI_HvacStatus", lambda v: v["DriverTempSet"] == 23.5, timeout=3)
        assert values["FanSpeed"] == 3 and values["AcOn"] == 1
        assert gateway.errors == []
    finally:
        ecu.stop()
        gateway.stop()
        for bus in (gateway.bus, ecu_bus, listener):
            bus.shutdown()
