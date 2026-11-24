"""CAN 게이트웨이 (기기 없이). DBC 인코딩, 프레임을 차량 신호로 바꾸는 규칙, 가상 버스 위의 양방향 동작을 본다."""
import itertools
import threading
import time

import can
import pytest

from ivi.can_gateway import (
    GEAR_D, GEAR_P, GEAR_R, KEEP, CanGateway, EcuNode, GatewayStopTimeout, load_db, virtual_bus, wait_for_frame,
)
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


# ---- 예외 경로: 느린 차량, 멈추지 않는 호출, 다시 시작, 버스 오류 (2026-11-24 외부 검토 IVI-REV-05, 06, 07) ----

class SlowVehicle(FakeVehicle):
    """drive() 한 번에 delay 초가 걸리는 차량 (adb 왕복이 느린 경우)."""

    def __init__(self, delay):
        super().__init__()
        self.delay = delay

    def drive(self, kmh=50.0):
        time.sleep(self.delay)
        super().drive(kmh)


class BlockingVehicle(FakeVehicle):
    """drive() 가 release 될 때까지 돌아오지 않는 차량 (adb 가 멈춘 경우)."""

    def __init__(self):
        super().__init__()
        self.entered, self.release = threading.Event(), threading.Event()

    def drive(self, kmh=50.0):
        self.entered.set()
        self.release.wait(10)
        super().drive(kmh)


@pytest.fixture
def net(db):
    """가상 버스 위의 게이트웨이와 ECU 쪽 버스. 보내기 스레드는 이 테스트들과 상관없어 주기를 길게 둔다."""
    made = []

    def make(car, **kwargs):
        channel = f"unit-{next(_channels)}"
        gateway = CanGateway(virtual_bus(channel), car, db, tx_period=30, **kwargs).start()
        ecu_bus = virtual_bus(channel)
        made.append((gateway, ecu_bus, car))
        return gateway, ecu_bus, EcuNode(ecu_bus, db)

    yield make
    for gateway, ecu_bus, car in made:
        if isinstance(car, BlockingVehicle):
            car.release.set()
        try:
            gateway.stop()
        finally:
            gateway.bus.shutdown()
            ecu_bus.shutdown()


def wait_for(check, timeout=5.0, what="조건"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.01)
    raise AssertionError(f"{timeout:g}초 안에 {what}이 되지 않았다")


def test_slow_vehicle_gets_latest_speed_without_backlog(net):
    """차량 쓰기가 40 ms 걸리는데 속도가 매번 다른 프레임이 5 ms 마다 50개 온다. 예전에는 하나씩 차례로 넣어 마지막 값까지
    2초 가까이 걸렸고 프레임이 40개 넘게 쌓였다. 지금은 최신 값으로 합쳐 마지막 프레임 뒤 곧 50 km/h 가 들어가고,
    합친 수와 지연이 진단 기록에 남는다."""
    car = SlowVehicle(0.04)
    gateway, ecu_bus, ecu = net(car)
    for kmh in range(1, 51):
        ecu_bus.send(ecu.message("VCU_DriveStatus", VehicleSpeed=float(kmh), GearSelect=GEAR_D))
        time.sleep(0.005)
    sent = time.monotonic()
    wait_for(lambda: car.calls[-1:] == [("drive", 50.0)], timeout=5, what="마지막 속도 50 km/h")
    assert time.monotonic() - sent < 0.5, "최신 값이 늦게 들어갔다 (오래된 프레임을 차례로 넣고 있다)"

    speeds = [kmh for _, kmh in car.calls]
    assert len(speeds) < 25 and speeds == sorted(speeds), f"늦게 온 값이 먼저 들어가면 안 된다: {speeds}"
    stats = gateway.diagnostics()
    assert stats["merged"] > 0 and stats["dropped"] == 0 and stats["queued_peak"] <= 3, stats
    assert stats["received"] == 50 and stats["last_lag_ms"] is not None and stats["max_lag_ms"] < 500, stats


def test_gear_changes_are_not_merged_away(net):
    """느린 차량에서 프레임을 합쳐도 기어가 바뀐 프레임은 합치지 않는다. D → R → P → D 를 빠르게 보내면 차량도 그 순서를 다 받는다
    (R 을 건너뛰면 후방 카메라가 뜨지 않는다)."""
    car = SlowVehicle(0.04)
    _, ecu_bus, ecu = net(car)
    for gear, kmh in [(GEAR_D, 10.0), (GEAR_D, 20.0), (GEAR_R, 0.0), (GEAR_P, 0.0), (GEAR_D, 30.0), (GEAR_D, 40.0)]:
        ecu_bus.send(ecu.message("VCU_DriveStatus", VehicleSpeed=kmh, GearSelect=gear))
        time.sleep(0.005)
    wait_for(lambda: car.calls[-1:] == [("drive", 40.0)], what="마지막 D 40 km/h")
    gears = [call[0] for call in car.calls]
    assert [g for i, g in enumerate(gears) if i == 0 or g != gears[i - 1]] == ["drive", "reverse", "park", "drive"], car.calls


def test_stop_reports_thread_stuck_in_vehicle_call(net):
    """차량 호출이 끝나지 않으면 stop() 이 '멈췄다'고 돌아오지 않고 GatewayStopTimeout 을 낸다. 그 사이 다시 시작하지 못한다.
    멈추라고 한 뒤에 받은 프레임은 차량에 넣지 않고, 걸려 있던 호출이 끝나면 스레드가 끝나 다시 시작할 수 있다."""
    car = BlockingVehicle()
    gateway, ecu_bus, ecu = net(car)
    ecu_bus.send(ecu.message("VCU_DriveStatus", VehicleSpeed=50.0, GearSelect=GEAR_D))
    assert car.entered.wait(3), "차량 호출에 들어가지 않았다"
    ecu_bus.send(ecu.message("BMS_Status", BatterySoc=8.0, RangeRemaining=25.0))
    wait_for(lambda: gateway.diagnostics()["queued"] == 1, what="BMS 프레임 대기")

    with pytest.raises(GatewayStopTimeout, match="can-apply"):
        gateway.stop(timeout=0.3)
    with pytest.raises(RuntimeError, match="아직 돈다"):
        gateway.start()

    car.release.set()
    wait_for(lambda: not any(thread.is_alive() for thread in gateway._threads), what="스레드 종료")
    assert car.calls == [("drive", 50.0)], f"멈추라고 한 뒤에 차량을 바꿨다: {car.calls}"
    gateway.stop()
    gateway.start()


def test_restart_applies_first_frame_again(net):
    """같은 게이트웨이를 멈췄다 다시 켜면, 멈춘 사이 차량이 초기화됐을 수 있으므로 처음 받는 프레임은 같은 값이어도 다시 넣는다.
    켜져 있는 동안 같은 값을 거르는 것은 그대로다."""
    car = FakeVehicle()
    gateway, ecu_bus, ecu = net(car)
    frame = ecu.message("VCU_DriveStatus", VehicleSpeed=50.0, GearSelect=GEAR_D)
    ecu_bus.send(frame)
    wait_for(lambda: car.calls == [("drive", 50.0)], what="첫 프레임")
    ecu_bus.send(frame)
    wait_for(lambda: gateway.diagnostics()["unchanged"] == 1, what="같은 값 거르기")
    assert car.calls == [("drive", 50.0)]

    gateway.stop()
    car.calls.clear()  # 멈춘 사이 차량(또는 앱)이 초기화됐다
    gateway.start()
    ecu_bus.send(frame)
    wait_for(lambda: car.calls == [("drive", 50.0)], what="다시 시작한 뒤 첫 프레임")


def test_bus_receive_error_is_recorded_and_receiving_continues(db):
    """버스 읽기가 예외를 내면 예전에는 받는 스레드가 조용히 죽었다. 오류를 남기고 계속 돈다."""
    class BrokenBus:
        def recv(self, timeout=None):
            raise can.CanOperationError("버스가 끊겼다")

    gateway = CanGateway(BrokenBus(), FakeVehicle(), db, tx_period=30).start()
    try:
        wait_for(lambda: len(gateway.errors) >= 2, what="오류 기록")
        assert "버스가 끊겼다" in gateway.errors[0] and gateway._threads[0].is_alive()
    finally:
        gateway.stop()


def test_error_and_applied_history_stay_bounded(db):
    """잘못된 프레임이 계속 와도 오류 기록이 끝없이 늘지 않는다. 모두 몇 번이었는지는 진단 기록에 남는다."""
    gateway = CanGateway(bus=None, vehicle=FakeVehicle(), db=db)
    for index in range(5000):
        gateway._error(f"rx 0x100: 잘못된 길이 {index}")
    assert len(gateway.errors) <= 2 * KEEP and gateway.errors[-1].endswith("4999")
    assert gateway.diagnostics()["errors"] == 5000
