"""기기 없이 어댑터의 명령 조립·출력 해석을 검증한다 (CI 의 GitHub 호스트에서 돈다)."""
import pytest

from ivi.device import Device
from ivi.screens import parse_celsius
from ivi.vehicle import AaosVehicle, MockVehicle, Prop, Seat


class FakeAdb:
    """명령을 기록하고, 미리 정한 출력을 돌려준다."""

    def __init__(self, outputs=None):
        self.calls = []
        self.outputs = outputs or {}

    def shell(self, *args, **_):
        self.calls.append(args)
        for key, out in self.outputs.items():
            if key in " ".join(args):
                return out
        return ""


@pytest.mark.parametrize("text, expected", [("25.0°C", 25.0), ("16.5°C", 16.5), ("--", None), (" 22.0°C ", 22.0), ("23.5°", 23.5)])
def test_parse_celsius(text, expected):
    assert parse_celsius(text) == expected


def test_aaos_reads_float_and_int_properties():
    adb = FakeAdb({
        "0x15600503": "Property:0x15600503, status: 0, timestamp: 1, zone: 0x1, floatValues: [22.5], int32Values: [], int64Values: []",
        "0x11400400": "Property:0x11400400, status: 0, timestamp: 1, zone: 0x0, floatValues: [], int32Values: [8], int64Values: []",
    })
    car = AaosVehicle(adb)
    assert car.temperature(Seat.DRIVER) == 22.5
    assert car.get_property(Prop.GEAR_SELECTION) == 8


def test_aaos_drive_converts_kmh_to_mps_and_uses_vhal_set():
    adb = FakeAdb({"--set": "Set property: VehiclePropValue{...}"})
    AaosVehicle(adb).drive(36.0)
    speed = [call for call in adb.calls if str(Prop.PERF_VEHICLE_SPEED) in call][0]
    assert speed[speed.index("-f") + 1] == "10.0"  # 36 km/h = 10 m/s
    gear = [call for call in adb.calls if str(Prop.GEAR_SELECTION) in call][0]
    assert gear[gear.index("-i") + 1] == "8"


def test_aaos_set_temperature_fails_loudly_when_car_service_refuses():
    adb = FakeAdb({"set-property-value": "Failed to set property: SecurityException"})
    with pytest.raises(RuntimeError, match="쓰기 실패"):
        AaosVehicle(adb).set_temperature(Seat.PASSENGER, 25.0)


def test_mock_state_is_parsed_from_broadcast_result():
    adb = FakeAdb({"mock.GET": 'Broadcasting: Intent { ... }\nBroadcast completed: result=0, '
                               'data="speed_kmh=50.0;gear=D;temp_driver=25.0;temp_passenger=22.0;restricted=true"'})
    car = MockVehicle(adb)
    assert car.is_restricted() is True
    assert car.temperature(Seat.DRIVER) == 25.0


def test_mock_state_error_explains_app_must_run():
    adb = FakeAdb({"mock.GET": "Broadcast completed: result=0"})
    with pytest.raises(RuntimeError, match="앱이 떠 있는지"):
        MockVehicle(adb).state()


def test_mock_set_uses_string_for_gear_and_float_for_numbers():
    adb = FakeAdb()
    MockVehicle(adb).drive(50)
    args = adb.calls[0]
    assert args[args.index("gear") - 1] == "--es" and args[args.index("gear") + 1] == "D"
    assert args[args.index("speed_kmh") - 1] == "--ef" and args[args.index("speed_kmh") + 1] == "50.0"


@pytest.mark.parametrize("brand, forced, expected", [
    ("HUAWEI", None, "adb"), ("HONOR", None, "adb"), ("google", None, "appium"),
    ("HUAWEI", "appium", "appium"), ("samsung", "adb", "adb"),
])
def test_tap_mode_by_brand_and_override(monkeypatch, brand, forced, expected):
    if forced:
        monkeypatch.setenv("IVI_TAP", forced)
    else:
        monkeypatch.delenv("IVI_TAP", raising=False)
    device = Device("serial", FakeAdb(), False, 0, "model", brand, MockVehicle(FakeAdb()))
    assert device.tap_mode == expected


class FlakyAdb(FakeAdb):
    """VHAL --set 이 처음 n 번은 실패하는 adb."""

    def __init__(self, failures):
        super().__init__()
        self.failures = failures

    def shell(self, *args, **_):
        self.calls.append(args)
        if "--set" in args and self.failures > 0:
            self.failures -= 1
            return "failed to set property: VehiclePropValue{...}"
        return "Set property: VehiclePropValue{...}"


def test_vhal_set_retries_once_and_records_it(monkeypatch):
    monkeypatch.setattr("ivi.vehicle.time.sleep", lambda _: None)
    car = AaosVehicle(FlakyAdb(failures=1))
    car.park()
    assert len(car.retried) == 1 and "2번째에 성공" in car.retried[0]


def test_vhal_set_fails_after_two_attempts(monkeypatch):
    monkeypatch.setattr("ivi.vehicle.time.sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="2회"):
        AaosVehicle(FlakyAdb(failures=2)).park()
