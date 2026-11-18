"""가상 CAN 버스와 VHAL 을 잇는 게이트웨이 (모의 환경).

실제 차에서는 VCU, BMS, BCM 같은 ECU 가 CAN 으로 신호를 보내고, 차량 쪽 서비스가 그 값을 VHAL property 로 올려 준다.
이 프로젝트에는 ECU 도 CAN 장비도 없어서, PC 안에서 그 자리를 흉내 낸다.

  dbc/opencabin.dbc   프레임과 신호 정의 (DBC). cantools 로 인코딩, 디코딩한다
  가상 버스            python-can 의 virtual 인터페이스. 같은 프로세스 안에서 여러 노드가 같은 채널을 쓴다
  CanGateway          받는 쪽: VCU, BMS, BCM 프레임을 풀어 차량 어댑터(VHAL 또는 Mock)에 넣는다
                      보내는 쪽: 공조 상태를 읽어 IVI_HvacStatus 프레임을 1초마다, 바뀌면 바로 보낸다
  EcuNode             시험용 ECU. 실제 차처럼 같은 프레임을 주기적으로 보낸다

ECU 는 같은 값을 100~500 ms 마다 계속 보내므로, 게이트웨이는 값이 바뀐 프레임만 VHAL 에 넣는다 (adb 왕복을 줄이려는 것).
실제 ECU, CAN 트랜시버, 버스 부하와 타이밍은 다루지 않는다.
"""
import threading
import time
from pathlib import Path

import can
import cantools

from ivi.vehicle import Seat, Signal

DBC = Path(__file__).resolve().parent.parent / "dbc" / "opencabin.dbc"
CHANNEL = "opencabin"
GEAR_P, GEAR_R, GEAR_N, GEAR_D = 0, 1, 2, 3


def load_db(path=DBC):
    return cantools.database.load_file(str(path))


def virtual_bus(channel=CHANNEL):
    return can.Bus(interface="virtual", channel=channel)


class CanGateway:
    IGNORED = {"DriveCounter"}  # 롤링 카운터는 값 비교에서 뺀다

    def __init__(self, bus, vehicle, db=None, tx_period=1.0):
        self.bus, self.vehicle = bus, vehicle
        self.db = db or load_db()
        self.tx_period = tx_period
        self.last = {}       # 프레임 이름 → 마지막으로 넣은 값
        self.applied = []    # (프레임 이름, 값) 넣은 순서대로. 테스트와 진단용
        self.errors = []
        self.last_hvac = None
        self._lock = threading.Lock()  # 받기와 보내기가 차량 어댑터를 동시에 부르지 않게
        self._stop = threading.Event()
        self._threads = []

    # ---- 받기: CAN → VHAL ----
    def handle(self, msg):
        """프레임 하나를 처리한다. 차량에 넣은 값이 있으면 돌려주고, 무시했으면 None."""
        try:
            frame = self.db.get_message_by_frame_id(msg.arbitration_id)
        except KeyError:
            return None  # 이 DBC 에 없는 프레임
        if "IVI" in (frame.senders or []):
            return None  # 게이트웨이가 보낸 프레임
        values = {k: v for k, v in frame.decode(msg.data, decode_choices=False).items() if k not in self.IGNORED}
        if self.last.get(frame.name) == values:
            return None  # 주기적으로 오는 같은 값
        with self._lock:
            self._apply(frame.name, values)
        self.last[frame.name] = values
        self.applied.append((frame.name, values))
        return values

    def _apply(self, name, v):
        if name == "VCU_DriveStatus":
            gear = int(v["GearSelect"])
            if gear == GEAR_D:
                self.vehicle.drive(round(float(v["VehicleSpeed"]), 2))
            elif gear == GEAR_R:
                self.vehicle.reverse()
            elif gear == GEAR_P:
                self.vehicle.park()
            # N 은 이 앱이 쓰는 기어가 아니라 넣지 않는다
        elif name == "BMS_Status":
            self.vehicle.set_signals({Signal.BATTERY_PCT: round(float(v["BatterySoc"]), 1),
                                      Signal.RANGE_KM: round(float(v["RangeRemaining"]), 1)})
        elif name == "BCM_Status":
            self.vehicle.set_signals({Signal.DOORS_LOCKED: bool(v["DoorsLocked"]),
                                      Signal.OUTSIDE_C: round(float(v["OutsideTemp"]), 1)})

    # ---- 보내기: VHAL → CAN ----
    def hvac_values(self):
        with self._lock:
            return {
                "DriverTempSet": float(self.vehicle.temperature(Seat.DRIVER)),
                "PassengerTempSet": float(self.vehicle.temperature(Seat.PASSENGER)),
                "AcOn": int(bool(self.vehicle.signal(Signal.AC))),
                "MaxAcOn": int(bool(self.vehicle.signal(Signal.MAX_AC))),
                "AutoOn": int(bool(self.vehicle.signal(Signal.AUTO))),
                "FanSpeed": int(self.vehicle.signal(Signal.FAN)),
            }

    def hvac_frame(self, values):
        frame = self.db.get_message_by_name("IVI_HvacStatus")
        return can.Message(arbitration_id=frame.frame_id, data=frame.encode(values), is_extended_id=False)

    def publish_hvac(self):
        values = self.hvac_values()
        self.bus.send(self.hvac_frame(values))
        self.last_hvac = values
        return values

    # ---- 실행 ----
    def start(self):
        self._stop.clear()
        self._threads = [threading.Thread(target=self._rx_loop, name="can-rx", daemon=True),
                         threading.Thread(target=self._tx_loop, name="can-tx", daemon=True)]
        for thread in self._threads:
            thread.start()
        return self

    def stop(self):
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=5)

    def _rx_loop(self):
        while not self._stop.is_set():
            msg = self.bus.recv(timeout=0.1)
            if msg is None:
                continue
            try:
                self.handle(msg)
            except Exception as error:  # noqa: BLE001 - 프레임 하나가 잘못돼도 게이트웨이는 계속 돈다
                self.errors.append(f"rx {msg.arbitration_id:#x}: {error!r}")

    def _tx_loop(self):
        while not self._stop.wait(self.tx_period):
            try:
                self.publish_hvac()
            except Exception as error:  # noqa: BLE001
                self.errors.append(f"tx: {error!r}")


class EcuNode:
    """시험용 ECU. DBC 의 프레임 이름과 신호 값으로 주기 송신을 시작하거나 값을 바꾼다."""

    def __init__(self, bus, db=None):
        self.bus = bus
        self.db = db or load_db()
        self.tasks = {}

    def message(self, name, **signals):
        frame = self.db.get_message_by_name(name)
        values = {s.name: 0 for s in frame.signals}
        values.update(signals)
        return can.Message(arbitration_id=frame.frame_id, data=frame.encode(values), is_extended_id=False)

    def send(self, name, period=0.1, **signals):
        msg = self.message(name, **signals)
        if name in self.tasks:
            self.tasks[name].modify_data(msg)
        else:
            self.tasks[name] = self.bus.send_periodic(msg, period)

    def stop(self):
        for task in self.tasks.values():
            task.stop()
        self.tasks.clear()


def wait_for_frame(bus, db, name, check, timeout=10.0):
    """버스에서 name 프레임을 받아 check(값) 이 참이 될 때까지 기다린다. 마지막으로 받은 값을 돌려준다."""
    frame = db.get_message_by_name(name)
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg is None or msg.arbitration_id != frame.frame_id:
            continue
        last = frame.decode(msg.data, decode_choices=False)
        if check(last):
            return last
    raise AssertionError(f"{timeout:g}초 안에 조건에 맞는 {name} 프레임이 오지 않았다 (마지막 값: {last})")
