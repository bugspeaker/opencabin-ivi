"""차량 신호 어댑터. 테스트는 VehicleController 만 보고, 기기 종류에 따른 차이는 여기서 감춘다.

AaosVehicle (AAOS 에뮬레이터: CarService 와 에뮬레이터의 VHAL. 실차 VHAL 이 아니다)
  - set_property(): CarService 경로 (`cmd car_service set-property-value`). 앱의 CarPropertyManager 와 같다. 쓰기 가능 값만.
  - force():        VHAL 직접 (`dumpsys <VHAL> --set`, root). 속도·기어 같은 읽기 전용 센서 값을 '차가 보낸 것처럼' 바꾼다.
  - `inject-vhal-event` 는 저장 값이 안 바뀌어 판정에 못 써서 쓰지 않는다 (docs/phase1-spike.md).

8단계 신호 (Signal): 공조 A/C·AUTO·풍량·김서림·좌석 열선, 도어 잠금, 주행 가능 거리·배터리·외기 온도
  - 테스트는 car.set_signal(Signal.X, 값) / car.signal(Signal.X) 만 쓴다. 단위는 화면과 같다 (km, %, °C, 단계).
  - AAOS: VHAL 에 직접 넣고(force) CarService 로 읽는다. '전 좌석'·'전 도어' 신호는 모든 area 에 넣는다.
  - prepare() 가 테스트마다 기준 값(CABIN_DEFAULTS)으로 되돌린다 → 앞 테스트가 문을 열어 둬도 다음 테스트는 잠긴 채 시작한다.

MockVehicle (일반 Android, 앱 안의 가짜 차량)
  - `am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET/GET` (debug 빌드만 받는다)
  - 앱 프로세스가 떠 있어야 받는다. 그래서 prepare() 는 앱을 띄운 다음에 부른다.
"""
import re
import threading
import time
from abc import ABC, abstractmethod
from enum import Enum

from ivi.waits import wait_until

PACKAGE = "dev.opencabin.ivi"
VHAL = "android.hardware.automotive.vehicle.IVehicle/default"
DEFAULT_TEMP_C = 22.0


class Seat(Enum):
    DRIVER = ("driver", 0x1)       # ROW_1_LEFT
    PASSENGER = ("passenger", 0x4)  # ROW_1_RIGHT

    def __init__(self, tag, area):
        self.tag = tag
        self.area = area


class Prop:
    PERF_VEHICLE_SPEED = 0x11600207   # float m/s, 읽기 전용
    GEAR_SELECTION = 0x11400400       # int32, 읽기 전용
    HVAC_TEMPERATURE_SET = 0x15600503  # float °C, 좌석별 읽기/쓰기
    HVAC_TEMPERATURE_DISPLAY_UNITS = 0x1140050E  # int32 VehicleUnit: 0x30 섭씨, 0x31 화씨 (SystemUI 표시 단위)


    # 8단계
    HVAC_AC_ON = 0x15200505             # bool, 좌석별
    HVAC_AUTO_ON = 0x1520050A           # bool, 좌석별
    HVAC_MAX_AC_ON = 0x15200506         # bool, 좌석별
    HVAC_FAN_SPEED = 0x15400500         # int32 1~7, 좌석별
    HVAC_SEAT_TEMPERATURE = 0x1540050B  # int32 -2~2 (양수 = 열선), 좌석별
    HVAC_DEFROSTER = 0x13200504         # bool, 창(앞 0x1 / 뒤 0x2)
    DOOR_LOCK = 0x16200B02              # bool, 문별
    RANGE_REMAINING = 0x11600308        # float m
    EV_BATTERY_LEVEL = 0x11600309       # float Wh
    INFO_EV_BATTERY_CAPACITY = 0x11600106  # float Wh
    ENV_OUTSIDE_TEMPERATURE = 0x11600703  # float °C


PROP_NAMES = {value: name for name, value in vars(Prop).items() if name.isupper()}


class Signal:
    """8단계 차량 신호 이름. 두 어댑터가 같이 쓴다 (Mock 의 broadcast extra 이름과 같다)."""
    AC = "ac"
    AUTO = "auto"
    MAX_AC = "max_ac"   # 최대 냉방. 화면 버튼 이름은 FULL
    FAN = "fan"
    DEFROST_FRONT = "defrost_front"
    DEFROST_REAR = "defrost_rear"
    HEAT_DRIVER = "heat_driver"
    HEAT_PASSENGER = "heat_passenger"
    DOORS_LOCKED = "doors_locked"
    RANGE_KM = "range_km"
    BATTERY_PCT = "battery_pct"
    OUTSIDE_C = "outside_c"

    @staticmethod
    def heat(seat):
        return f"heat_{seat.tag}"


# 테스트 시작 기준 값 (값의 타입이 곧 신호의 타입이다: bool / int / float)
CABIN_DEFAULTS = {
    Signal.AC: True, Signal.AUTO: False, Signal.MAX_AC: False, Signal.FAN: 3,
    Signal.DEFROST_FRONT: False, Signal.DEFROST_REAR: False,
    Signal.HEAT_DRIVER: 0, Signal.HEAT_PASSENGER: 0,
    Signal.DOORS_LOCKED: True,
    Signal.RANGE_KM: 320.0, Signal.BATTERY_PCT: 80.0, Signal.OUTSIDE_C: 18.0,
}

# 에뮬레이터 HVAC area: 1열 좌·우, 2열 좌·우·가운데. 앱은 area 를 CarPropertyConfig 에서 읽지만 테스트는 일부러 고정한다:
# 앱과 같은 출처에서 기대값을 읽으면 config 가 틀렸을 때 둘이 같이 틀려 결함이 보이지 않는다.
# 다른 차종(다른 VHAL 설정)에서 돌릴 때는 `cmd car_service get-property-config` 로 읽은 area 와 이 목록을 먼저 맞춰 본다.
SEAT_AREAS = (0x1, 0x4, 0x10, 0x40, 0x20)
DOOR_AREAS = (0x1, 0x4, 0x10, 0x40)


class TempUnit:
    CELSIUS = 0x30
    FAHRENHEIT = 0x31


class Gear:
    REVERSE = 2
    PARK = 4
    DRIVE = 8


class Area:
    GLOBAL = 0x0
    DRIVER = Seat.DRIVER.area
    PASSENGER = Seat.PASSENGER.area


class DrivingState:
    UNKNOWN = -1
    PARKED = 0
    IDLING = 1
    MOVING = 2


class VehicleController(ABC):
    """테스트가 쓰는 차량 조작. 단위는 화면과 같이 km/h, °C."""

    kind = ""
    badge = ""  # 앱 상단 source_badge 에 보여야 하는 값

    def __init__(self, adb):
        self.adb = adb
        self.retried = []  # 신호 주입 도구의 일시 오류로 다시 시도한 기록 (conftest 가 테스트 결과에 옮긴다)
        self.observed = {}  # 테스트 중에 읽은 차량 값 (읽은 순서, 같은 property·area 는 마지막 값). AAOS 만 채운다

    def take_observed(self, limit=3):
        """마지막으로 읽은 차량 값 limit 개를 'HVAC_TEMPERATURE_SET[0x1]=22.5' 꼴로 돌려주고 비운다.
        wait_until 이 조건을 만족한 순간 읽은 값이 마지막에 남으므로, 판정에 쓴 값이다 (결과 페이지에 보여 준다)."""
        items = list(self.observed.items())[-limit:]
        self.observed.clear()
        return [f"{key}={value}" for key, value in items]

    def prepare(self):
        """테스트 시작 전: 정차 + 기본 온도 + 8단계 신호 기준 값."""
        self.park()
        for seat in Seat:
            self.set_temperature(seat, DEFAULT_TEMP_C)
        self.reset_cabin()

    def reset_cabin(self):
        """8단계 신호를 모두 기준 값(CABIN_DEFAULTS)으로."""
        self.set_signals(CABIN_DEFAULTS)

    def set_signal(self, name, value):
        """차량 쪽에서 신호를 바꾼다 (하위 → 상위 테스트의 입력)."""
        self.set_signals({name: value})

    @abstractmethod
    def set_signals(self, values):
        """신호 여러 개를 한 번에 (adb 왕복 한 번)."""

    @abstractmethod
    def signal(self, name):
        """지금 차량의 신호 값 (상위 → 하위 테스트의 판정). 타입은 CABIN_DEFAULTS 와 같다."""

    def signal_all(self, name):
        """'전 좌석'·'전 도어' 신호의 area 별 값. area 가 없는 기기(Mock)는 값 하나."""
        return [self.signal(name)]

    def cleanup(self):
        self.park()

    @abstractmethod
    def drive(self, kmh=50.0): ...

    @abstractmethod
    def park(self): ...

    @abstractmethod
    def reverse(self):
        """기어 R, 속도 0 (후진 준비). 후방 카메라가 떠야 한다."""

    @abstractmethod
    def set_temperature(self, seat, celsius): ...

    @abstractmethod
    def temperature(self, seat): ...

    @abstractmethod
    def inject_temperature(self, seat, celsius):
        """차량(ECU) 쪽에서 설정 온도가 바뀐 것처럼 넣는다. 앱의 쓰기 경로(CarService)가 거절하는 범위 밖 값이나
        0.5 단위가 아닌 값도 넣을 수 있다 (경계값 테스트의 입력)."""

    @abstractmethod
    def is_restricted(self): ...

    @abstractmethod
    def dump(self):
        """실패 자료용 현재 차량 상태 (사람이 읽는 문자열)."""

    def wait_restricted(self, expected, timeout=10.0):
        wait_until(lambda: self.is_restricted() == expected, timeout=timeout,
                   what=f"주행 중 제한 {'켜짐' if expected else '꺼짐'}")


class AaosVehicle(VehicleController):
    kind = "aaos"
    badge = "AAOS"

    # 테스트가 바꾸는 쓰기 가능 값. 시작할 때 저장했다가 끝나면 되돌린다
    _restored = [(Prop.HVAC_TEMPERATURE_SET, Area.DRIVER), (Prop.HVAC_TEMPERATURE_SET, Area.PASSENGER)]

    def ensure_root(self):
        if self.adb.shell("whoami").strip() != "root":
            self.adb.run("root")
            self.adb.run("wait-for-device", timeout=60)
            wait_until(lambda: self.adb.shell("whoami").strip() == "root", timeout=20, what="adb root")

    _saved = False

    def prepare(self):
        self.ensure_root()
        for prop, area in self._restored:
            self.save(prop, area)
        self._saved = True
        super().prepare()

    def cleanup(self):
        # 정리는 준비가 중간에 실패해도 돈다(conftest). 저장하기 전에 실패했으면 되돌릴 값이 없으니 정차만 한다.
        # 그대로 restore 하면 앞 테스트가 저장해 둔 값으로 되돌리게 된다
        saved, self._saved = self._saved, False
        self.park()
        if saved:
            for prop, area in self._restored:
                self.restore(prop, area)

    # ---- 저수준: property ----
    def get_property(self, prop, area=Area.GLOBAL):
        out = self.adb.shell("cmd", "car_service", "get-property-value", hex(prop), hex(area))
        floats = re.search(r"floatValues: \[([^\]]*)\]", out)
        ints = re.search(r"int32Values: \[([^\]]*)\]", out)
        if not floats or not ints:
            raise RuntimeError(f"property {hex(prop)} 값을 읽지 못했다: {out.strip()[:200]}")
        raw = (floats.group(1) or ints.group(1)).split(", ")[0]
        value = float(raw) if "." in raw else int(raw)
        if threading.current_thread() is threading.main_thread():  # CAN 게이트웨이 스레드가 읽은 값은 판정이 아니다
            key = PROP_NAMES.get(prop, hex(prop)) + (f"[{hex(area)}]" if area else "")
            self.observed.pop(key, None)
            self.observed[key] = value
        return value

    def set_property(self, prop, value, area=Area.GLOBAL):
        out = self.adb.shell("cmd", "car_service", "set-property-value", hex(prop), hex(area), str(value))
        if "successfully" not in out:
            raise RuntimeError(f"property {hex(prop)} 쓰기 실패: {out.strip()}")

    def force(self, prop, value, area=Area.GLOBAL, attempts=2):
        """VHAL 에 값을 직접 넣는다. 에뮬레이터 VHAL 이 드물게 'failed to set property' 를 돌려줘서
        (2026-11-13, 누적 200여 회 중 1회, 정차로 되돌리는 정리 단계) 한 번 더 시도한다. 두 번 다 실패하면 그대로 실패시킨다.
        테스트 대상(앱)이 아니라 신호를 넣는 도구 쪽 일시 오류라 여기서 흡수하고, 다시 시도한 사실은 retried 에 남긴다."""
        kind = "-f" if isinstance(value, float) else "-i"
        out = ""
        for attempt in range(1, attempts + 1):
            out = self.adb.shell("dumpsys", VHAL, "--set", str(prop), kind, str(value), "-a", str(area))
            if "Set property" in out:
                if attempt > 1:
                    self.retried.append(f"VHAL --set {hex(prop)}={value}: {attempt}번째에 성공")
                return
            time.sleep(0.3)
        raise RuntimeError(f"VHAL --set {hex(prop)} 실패 ({attempts}회): {out.strip()[:200]}")

    def save(self, prop, area=Area.GLOBAL):
        self.adb.shell("dumpsys", VHAL, "--save-prop", str(prop), "-a", str(area))

    def restore(self, prop, area=Area.GLOBAL):
        self.adb.shell("dumpsys", VHAL, "--restore-prop", str(prop), "-a", str(area))

    # ---- 8단계 신호 ----
    # 이름 → (property, 읽는 area, 쓰는 area 들)
    _SIGNALS = {
        Signal.AC: (Prop.HVAC_AC_ON, 0x1, SEAT_AREAS),
        Signal.AUTO: (Prop.HVAC_AUTO_ON, 0x1, SEAT_AREAS),
        Signal.MAX_AC: (Prop.HVAC_MAX_AC_ON, 0x1, SEAT_AREAS),
        Signal.FAN: (Prop.HVAC_FAN_SPEED, 0x1, SEAT_AREAS),
        Signal.DEFROST_FRONT: (Prop.HVAC_DEFROSTER, 0x1, (0x1,)),
        Signal.DEFROST_REAR: (Prop.HVAC_DEFROSTER, 0x2, (0x2,)),
        Signal.HEAT_DRIVER: (Prop.HVAC_SEAT_TEMPERATURE, 0x1, (0x1,)),
        Signal.HEAT_PASSENGER: (Prop.HVAC_SEAT_TEMPERATURE, 0x4, (0x4,)),
        Signal.DOORS_LOCKED: (Prop.DOOR_LOCK, 0x1, DOOR_AREAS),
        Signal.RANGE_KM: (Prop.RANGE_REMAINING, 0x0, (0x0,)),
        Signal.BATTERY_PCT: (Prop.EV_BATTERY_LEVEL, 0x0, (0x0,)),
        Signal.OUTSIDE_C: (Prop.ENV_OUTSIDE_TEMPERATURE, 0x0, (0x0,)),
    }
    _capacity_wh = None

    def battery_capacity_wh(self):
        if self._capacity_wh is None:
            self._capacity_wh = float(self.get_property(Prop.INFO_EV_BATTERY_CAPACITY))
        return self._capacity_wh

    def _to_vhal(self, name, value):
        """화면 단위 → VHAL 값: km → m, % → Wh, bool → 0/1."""
        if name == Signal.RANGE_KM:
            return float(value) * 1000.0
        if name == Signal.BATTERY_PCT:
            return self.battery_capacity_wh() * float(value) / 100.0
        return float(value) if isinstance(CABIN_DEFAULTS[name], float) else int(value)

    def _from_vhal(self, name, raw):
        if name == Signal.RANGE_KM:
            return raw / 1000.0
        if name == Signal.BATTERY_PCT:
            return round(raw / self.battery_capacity_wh() * 100.0, 1)
        return type(CABIN_DEFAULTS[name])(raw)

    def set_signals(self, values, attempts=2):
        """모든 값을 adb shell 한 번에 넣는다 (기준 값 12개 × area = 31번의 --set 을 왕복 한 번으로).
        force() 와 같이 VHAL 의 일시 오류는 한 번 더 시도하고 기록한다."""
        commands = []
        for name, value in values.items():
            prop, _, areas = self._SIGNALS[name]
            raw = self._to_vhal(name, value)
            kind = "-f" if isinstance(raw, float) else "-i"
            commands += [f"dumpsys {VHAL} --set {prop} {kind} {raw} -a {area}" for area in areas]
        out = ""
        for attempt in range(1, attempts + 1):
            out = self.adb.shell("; ".join(commands))
            if out.count("Set property") == len(commands):
                if attempt > 1:
                    self.retried.append(f"VHAL --set {', '.join(values)}: {attempt}번째에 성공")
                return
            time.sleep(0.3)
        raise RuntimeError(f"VHAL --set {list(values)} 실패 ({out.count('Set property')}/{len(commands)}): {out.strip()[-200:]}")

    def signal(self, name):
        prop, area, _ = self._SIGNALS[name]
        return self._from_vhal(name, self.get_property(prop, area))

    def signal_all(self, name):
        prop, _, areas = self._SIGNALS[name]
        return [self._from_vhal(name, self.get_property(prop, area)) for area in areas]

    def driving_state(self):
        out = self.adb.shell("dumpsys", "car_service", "--services", "CarDrivingStateService")
        found = re.search(r"Current Driving State: (-?\d+)", out)
        return int(found.group(1)) if found else DrivingState.UNKNOWN

    # ---- 공통 동작 ----
    def drive(self, kmh=50.0):
        self.force(Prop.GEAR_SELECTION, Gear.DRIVE)
        self.force(Prop.PERF_VEHICLE_SPEED, float(kmh) / 3.6)

    def park(self):
        self.force(Prop.PERF_VEHICLE_SPEED, 0.0)
        self.force(Prop.GEAR_SELECTION, Gear.PARK)

    def reverse(self):
        self.force(Prop.PERF_VEHICLE_SPEED, 0.0)
        self.force(Prop.GEAR_SELECTION, Gear.REVERSE)

    def set_temperature(self, seat, celsius):
        self.set_property(Prop.HVAC_TEMPERATURE_SET, float(celsius), seat.area)

    def temperature(self, seat):
        return self.get_property(Prop.HVAC_TEMPERATURE_SET, seat.area)

    def inject_temperature(self, seat, celsius):
        # CarService(set-property-value)는 범위 밖 값을 거절한다 (2026-11-18 확인: 15.5 → IllegalArgumentException).
        # 에뮬레이터 VHAL 의 --set 은 범위 검사 없이 받는다 → 차량 쪽에서 이상한 값이 올라온 상황을 만든다
        self.force(Prop.HVAC_TEMPERATURE_SET, float(celsius), seat.area)

    def is_restricted(self):
        return self.driving_state() == DrivingState.MOVING

    def dump(self):
        rows = [
            f"speed_mps={self.get_property(Prop.PERF_VEHICLE_SPEED)}",
            f"gear={self.get_property(Prop.GEAR_SELECTION)}",
            f"driving_state={self.driving_state()}",
        ] + [f"temp_{seat.tag}={self.temperature(seat)}" for seat in Seat]
        for name in CABIN_DEFAULTS:
            try:
                rows.append(f"{name}={self.signal_all(name)}")
            except RuntimeError as error:  # 실패 자료를 모으는 중이라 하나가 안 읽혀도 계속한다
                rows.append(f"{name}=<{error}>")
        return "\n".join(rows)


class MockVehicle(VehicleController):
    kind = "mock"
    badge = "Mock"

    def _broadcast(self, action, *extras):
        return self.adb.shell("am", "broadcast", "-p", PACKAGE, "-a", f"{PACKAGE}.mock.{action}", *extras)

    def _set(self, **values):
        extras = []
        for key, value in values.items():
            extras += ["--es", key, value] if isinstance(value, str) else ["--ef", key, str(float(value))]
        self._send_set(extras, values)

    def _send_set(self, extras, keys):
        """SET 브로드캐스트를 보내고, 앱이 돌려준 'applied=' 목록으로 값이 다 들어갔는지 그 자리에서 확인한다.
        화웨이는 꺼진 앱에 브로드캐스트를 전달하지 않는다. 확인하지 않으면 주입이 빠진 채 뒤의 대기에서 엉뚱하게 실패한다."""
        out = self._broadcast("SET", *extras)
        found = re.search(r'data="applied=([^"]*)"', out)
        missing = sorted(set(keys) - set(found.group(1).split(","))) if found else sorted(keys)
        if missing:
            raise RuntimeError(f"Mock 차량에 값이 들어가지 않았다 {missing} (앱이 떠 있는지 확인): {out.strip()[-200:]}")

    def state(self):
        out = self._broadcast("GET")
        found = re.search(r'data="([^"]*)"', out)
        if not found:
            raise RuntimeError(f"Mock 상태를 읽지 못했다 (앱이 떠 있는지 확인): {out.strip()[-200:]}")
        return dict(pair.split("=", 1) for pair in found.group(1).split(";"))

    def drive(self, kmh=50.0):
        self._set(gear="D", speed_kmh=kmh)

    def park(self):
        self._set(speed_kmh=0.0, gear="P")

    def reverse(self):
        self._set(speed_kmh=0.0, gear="R")

    def set_temperature(self, seat, celsius):
        self._set(**{f"temp_{seat.tag}": celsius})

    def temperature(self, seat):
        return float(self.state()[f"temp_{seat.tag}"])

    def inject_temperature(self, seat, celsius):
        # Mock 차량은 받은 값을 16.0~28.0 으로 자른다 (MockVehicleDataSource.applyExtras). 0.5 단위가 아닌 값은 그대로 둔다
        self._set(**{f"temp_{seat.tag}": celsius})

    def is_restricted(self):
        return self.state()["restricted"] == "true"

    def set_signals(self, values):
        """타입에 맞는 extra 로 보낸다: bool --ez, int --ei, float --ef."""
        extras = []
        for name, value in values.items():
            kind = type(CABIN_DEFAULTS[name])
            if kind is bool:
                extras += ["--ez", name, "true" if value else "false"]
            elif kind is int:
                extras += ["--ei", name, str(int(value))]
            else:
                extras += ["--ef", name, str(float(value))]
        self._send_set(extras, values)

    def signal(self, name):
        raw = self.state()[name]
        kind = type(CABIN_DEFAULTS[name])
        return raw == "true" if kind is bool else kind(raw)

    def dump(self):
        return "\n".join(f"{k}={v}" for k, v in self.state().items())
