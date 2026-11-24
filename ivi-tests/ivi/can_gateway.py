"""가상 CAN 버스와 VHAL 을 잇는 게이트웨이 (모의 환경).

실제 차에서는 VCU, BMS, BCM 같은 ECU 가 CAN 으로 신호를 보내고, 차량 쪽 서비스가 그 값을 VHAL property 로 올려 준다.
이 프로젝트에는 ECU 도 CAN 장비도 없어서, PC 안에서 그 자리를 흉내 낸다.

  dbc/opencabin.dbc   프레임과 신호 정의 (DBC). cantools 로 인코딩, 디코딩한다
  가상 버스            python-can 의 virtual 인터페이스. 같은 프로세스 안에서 여러 노드가 같은 채널을 쓴다
  CanGateway          받는 쪽: VCU, BMS, BCM 프레임을 풀어 차량 어댑터(VHAL 또는 Mock)에 넣는다
                      보내는 쪽: 공조 상태를 읽어 IVI_HvacStatus 프레임을 1초마다, 바뀌면 바로 보낸다
  EcuNode             시험용 ECU. 실제 차처럼 같은 프레임을 주기적으로 보낸다

ECU 는 같은 값을 100~500 ms 마다 계속 보내므로, 게이트웨이는 값이 바뀐 프레임만 VHAL 에 넣는다 (adb 왕복을 줄이려는 것).

받기와 넣기는 스레드를 나눈다. 받는 스레드는 버스를 비우는 일만 하고, 넣는 스레드가 차량 어댑터를 부른다.
차량 쪽(adb 왕복)이 CAN 보다 느리면 오래된 값을 차례로 쌓아 두지 않고 프레임마다 최신 값으로 합친다
(속도, 배터리처럼 지금 값만 의미 있는 상태 신호). 기어, 도어처럼 바뀐 사실 자체가 사건인 신호는 합치지 않고 순서대로 넣는다
(R 을 건너뛰면 후방 카메라가 뜨지 않는다). 대기는 queue_limit 개까지이고, 넘으면 가장 오래된 것부터 버리고 센다.
합친 수, 버린 수, 받은 때부터 차량에 다 넣을 때까지의 지연은 diagnostics() 로 본다.

실제 ECU, CAN 트랜시버, 버스 부하와 타이밍은 다루지 않는다.
"""
import collections
import threading
import time
from pathlib import Path

import can
import cantools

from ivi.vehicle import Seat, Signal

DBC = Path(__file__).resolve().parent.parent / "dbc" / "opencabin.dbc"
CHANNEL = "opencabin"
GEAR_P, GEAR_R, GEAR_N, GEAR_D = 0, 1, 2, 3
KEEP = 500  # applied, errors 에 남기는 최근 개수. 오래 돌려도 메모리가 늘지 않게


def load_db(path=DBC):
    return cantools.database.load_file(str(path))


def virtual_bus(channel=CHANNEL):
    return can.Bus(interface="virtual", channel=channel)


class GatewayStopTimeout(RuntimeError):
    """stop() 이 정한 시간 안에 스레드를 멈추지 못했다. 차량 어댑터 호출이 끝나지 않은 것이다."""


class PendingFrames:
    """받았지만 아직 차량에 넣지 않은 프레임. [이름, 값, 받은 시각] 을 차례로 둔다.

    같은 프레임의 마지막 대기 항목과 사건 신호(events)가 같으면 새 항목을 만들지 않고 그 항목의 값을 최신으로 바꾼다.
    """

    def __init__(self, events, limit=64):
        self.events, self.limit = events, limit
        self._items = collections.deque()
        self._cond = threading.Condition()
        self.merged = self.dropped = self.peak = 0

    def put(self, name, values, received):
        with self._cond:
            for item in reversed(self._items):
                if item[0] != name:
                    continue
                if all(item[1].get(key) == values.get(key) for key in self.events.get(name, ())):
                    item[1], item[2] = values, received
                    self.merged += 1
                    return
                break
            if len(self._items) >= self.limit:
                self._items.popleft()
                self.dropped += 1
            self._items.append([name, values, received])
            self.peak = max(self.peak, len(self._items))
            self._cond.notify()

    def get(self, timeout):
        with self._cond:
            if not self._items:
                self._cond.wait(timeout)
            return tuple(self._items.popleft()) if self._items else None

    def clear(self):
        with self._cond:
            self._items.clear()
            self._cond.notify_all()

    def __len__(self):
        with self._cond:
            return len(self._items)


class CanGateway:
    IGNORED = {"DriveCounter"}  # 롤링 카운터는 값 비교에서 뺀다
    EVENTS = {"VCU_DriveStatus": ("GearSelect",), "BCM_Status": ("DoorsLocked",)}  # 합치지 않고 순서대로 넣는 신호

    def __init__(self, bus, vehicle, db=None, tx_period=1.0, queue_limit=64):
        self.bus, self.vehicle = bus, vehicle
        self.db = db or load_db()
        self.tx_period = tx_period
        self.last = {}       # 프레임 이름 → 마지막으로 넣은 값
        self.applied = []    # (프레임 이름, 값) 넣은 순서대로. 테스트와 진단용 (최근 KEEP 개)
        self.errors = []     # 최근 KEEP 개. 모두 몇 번이었는지는 diagnostics()["errors"]
        self.last_hvac = None
        self._lock = threading.Lock()  # 넣기와 보내기가 차량 어댑터를 동시에 부르지 않게
        self._stop = threading.Event()
        self._threads = []
        self._pending = PendingFrames(self.EVENTS, queue_limit)
        self._stats = {"received": 0, "applied": 0, "unchanged": 0, "errors": 0, "last_lag_ms": None, "max_lag_ms": 0.0}

    # ---- 받기: CAN → VHAL ----
    def decode(self, msg):
        """프레임을 (이름, 값) 으로 푼다. 이 DBC 에 없거나 게이트웨이가 보낸 프레임이면 None."""
        try:
            frame = self.db.get_message_by_frame_id(msg.arbitration_id)
        except KeyError:
            return None  # 이 DBC 에 없는 프레임
        if "IVI" in (frame.senders or []):
            return None  # 게이트웨이가 보낸 프레임
        values = {k: v for k, v in frame.decode(msg.data, decode_choices=False).items() if k not in self.IGNORED}
        return frame.name, values

    def handle(self, msg):
        """프레임 하나를 바로 처리한다 (스레드 없이 쓸 때). 차량에 넣은 값이 있으면 돌려주고, 무시했으면 None."""
        decoded = self.decode(msg)
        return self._apply_if_changed(*decoded) if decoded else None

    def _apply_if_changed(self, name, values, received=None):
        if self.last.get(name) == values:
            self._stats["unchanged"] += 1
            return None  # 주기적으로 오는 같은 값
        with self._lock:
            if self._stop.is_set():
                return None  # 멈춘 게이트웨이는 차량을 바꾸지 않는다 (다음 테스트의 차량 상태를 건드리지 않게)
            self._apply(name, values)
        self.last[name] = values
        self._remember(self.applied, (name, values))
        self._stats["applied"] += 1
        if received is not None:
            lag = (time.monotonic() - received) * 1000
            self._stats["last_lag_ms"] = round(lag, 1)
            self._stats["max_lag_ms"] = round(max(self._stats["max_lag_ms"], lag), 1)
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
        # 값마다 잠금을 따로 잡는다. 여섯 번을 한 번에 잡으면 그동안(adb 왕복 여섯 번) 넣는 스레드가 기다린다
        reads = {
            "DriverTempSet": lambda: float(self.vehicle.temperature(Seat.DRIVER)),
            "PassengerTempSet": lambda: float(self.vehicle.temperature(Seat.PASSENGER)),
            "AcOn": lambda: int(bool(self.vehicle.signal(Signal.AC))),
            "MaxAcOn": lambda: int(bool(self.vehicle.signal(Signal.MAX_AC))),
            "AutoOn": lambda: int(bool(self.vehicle.signal(Signal.AUTO))),
            "FanSpeed": lambda: int(self.vehicle.signal(Signal.FAN)),
        }
        values = {}
        for name, read in reads.items():
            with self._lock:
                values[name] = read()
        return values

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
        if any(thread.is_alive() for thread in self._threads):
            raise RuntimeError("게이트웨이 스레드가 아직 돈다 (이미 시작했거나, 앞의 stop() 에서 멈추지 않은 스레드가 있다)")
        self._stop.clear()
        self.last.clear()  # 멈춘 사이 차량이나 앱이 초기화됐을 수 있다. 다시 시작하면 처음 받는 프레임은 다시 넣는다
        self._pending.clear()
        self.last_hvac = None
        self._threads = [threading.Thread(target=self._rx_loop, name="can-rx", daemon=True),
                         threading.Thread(target=self._apply_loop, name="can-apply", daemon=True),
                         threading.Thread(target=self._tx_loop, name="can-tx", daemon=True)]
        for thread in self._threads:
            thread.start()
        return self

    def stop(self, timeout=5.0):
        """스레드를 멈추고 모두 멈췄는지 확인한다. timeout 안에 못 멈추면 GatewayStopTimeout.

        멈추라고 한 뒤로는 대기 중인 프레임을 버리고 차량에 새로 넣지 않는다. 이미 들어간 어댑터 호출 하나는 끝날 때까지 기다린다.
        """
        self._stop.set()
        self._pending.clear()
        deadline = time.monotonic() + timeout
        for thread in self._threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        alive = [thread.name for thread in self._threads if thread.is_alive()]
        if alive:
            raise GatewayStopTimeout(f"{timeout:g}초 안에 멈추지 않았다: {', '.join(alive)} (차량 어댑터 호출이 끝나지 않았다)")
        self._threads = []

    def diagnostics(self):
        """받은 수, 넣은 수, 같은 값이라 넘긴 수, 합친 수, 버린 수, 대기 수(지금, 최대), 지연(ms), 오류 수."""
        return {**self._stats, "merged": self._pending.merged, "dropped": self._pending.dropped,
                "queued": len(self._pending), "queued_peak": self._pending.peak}

    def _rx_loop(self):
        while not self._stop.is_set():
            try:
                msg = self.bus.recv(timeout=0.1)
            except Exception as error:  # noqa: BLE001 - 버스가 닫혔거나 장치 오류. 조용히 죽지 않고 남긴다
                if self._stop.is_set():
                    break
                self._error(f"rx recv: {error!r}")
                self._stop.wait(0.1)
                continue
            if msg is None:
                continue
            self._stats["received"] += 1
            try:
                decoded = self.decode(msg)
            except Exception as error:  # noqa: BLE001 - 프레임 하나가 잘못돼도 게이트웨이는 계속 돈다
                self._error(f"rx {msg.arbitration_id:#x}: {error!r}")
                continue
            if decoded:
                self._pending.put(*decoded, received=time.monotonic())

    def _apply_loop(self):
        while not self._stop.is_set():
            item = self._pending.get(timeout=0.1)
            if item is None:
                continue
            name, values, received = item
            try:
                self._apply_if_changed(name, values, received)
            except Exception as error:  # noqa: BLE001 - adb 오류 등. 다음 주기 프레임에서 다시 넣는다
                self._error(f"apply {name}: {error!r}")

    def _tx_loop(self):
        while not self._stop.wait(self.tx_period):
            try:
                values = self.hvac_values()
                if self._stop.is_set():
                    break  # 읽는 사이 멈췄으면 보내지 않는다 (버스가 이미 닫혔을 수 있다)
                self.bus.send(self.hvac_frame(values))
                self.last_hvac = values
            except Exception as error:  # noqa: BLE001
                self._error(f"tx: {error!r}")

    def _error(self, text):
        self._stats["errors"] += 1
        self._remember(self.errors, text)

    @staticmethod
    def _remember(items, item):
        items.append(item)
        if len(items) > 2 * KEEP:
            del items[:-KEEP]


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
