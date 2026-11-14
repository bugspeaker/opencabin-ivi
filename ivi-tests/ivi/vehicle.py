"""차량 신호 어댑터. 테스트는 VehicleController 만 보고, 기기 종류에 따른 차이는 여기서 감춘다.

AaosVehicle (AAOS 에뮬레이터, 실제 CarService·VHAL)
  - set_property(): CarService 경로 (`cmd car_service set-property-value`). 앱의 CarPropertyManager 와 같다. 쓰기 가능 값만.
  - force():        VHAL 직접 (`dumpsys <VHAL> --set`, root). 속도·기어 같은 읽기 전용 센서 값을 '차가 보낸 것처럼' 바꾼다.
  - `inject-vhal-event` 는 저장 값이 안 바뀌어 판정에 못 써서 쓰지 않는다 (docs/phase1-spike.md).

MockVehicle (일반 Android, 앱 안의 가짜 차량)
  - `am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET/GET` (debug 빌드만 받는다)
  - 앱 프로세스가 떠 있어야 받는다. 그래서 prepare() 는 앱을 띄운 다음에 부른다.
"""
import re
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

    def prepare(self):
        """테스트 시작 전: 정차 + 기본 온도."""
        self.park()
        for seat in Seat:
            self.set_temperature(seat, DEFAULT_TEMP_C)

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

    def prepare(self):
        self.ensure_root()
        for prop, area in self._restored:
            self.save(prop, area)
        super().prepare()

    def cleanup(self):
        self.park()
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
        return float(raw) if "." in raw else int(raw)

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

    def is_restricted(self):
        return self.driving_state() == DrivingState.MOVING

    def dump(self):
        rows = [
            f"speed_mps={self.get_property(Prop.PERF_VEHICLE_SPEED)}",
            f"gear={self.get_property(Prop.GEAR_SELECTION)}",
            f"driving_state={self.driving_state()}",
        ] + [f"temp_{seat.tag}={self.temperature(seat)}" for seat in Seat]
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
        self._broadcast("SET", *extras)

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

    def is_restricted(self):
        return self.state()["restricted"] == "true"

    def dump(self):
        return "\n".join(f"{k}={v}" for k, v in self.state().items())
