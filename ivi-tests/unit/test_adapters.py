"""기기 없이 어댑터의 명령 조립·출력 해석을 검증한다 (CI 의 GitHub 호스트에서 돈다)."""
import pytest

from ivi.device import Device
from ivi.screens import parse_celsius
from ivi.vehicle import CABIN_DEFAULTS, AaosVehicle, MockVehicle, Prop, Seat, Signal


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


# ---------------- 8단계 신호 ----------------

def test_aaos_signals_are_set_in_one_shell_call_for_every_area():
    """A/C 는 좌석 5개 area 모두에 넣는다. adb 왕복은 한 번이다 (기준 값 초기화가 테스트마다 돌기 때문)."""
    adb = FakeAdb({"--set": "Set property: {}\n" * 5})
    AaosVehicle(adb).set_signal(Signal.AC, False)
    assert len(adb.calls) == 1
    command = adb.calls[0][0]
    assert command.count(f"--set {Prop.HVAC_AC_ON} -i 0") == 5
    assert [f"-a {area}" in command for area in (1, 4, 16, 64, 32)] == [True] * 5


def test_aaos_range_and_battery_are_converted_to_vhal_units():
    """화면 단위(km, %) → VHAL 단위(m, Wh). 배터리는 용량(INFO_EV_BATTERY_CAPACITY)에 대한 비율이다."""
    adb = FakeAdb({
        hex(Prop.INFO_EV_BATTERY_CAPACITY): "Property:0x11600106, zone: 0x0, floatValues: [150000.0], int32Values: []",
        "--set": "Set property: {}\nSet property: {}\n",
    })
    AaosVehicle(adb).set_signals({Signal.RANGE_KM: 22.0, Signal.BATTERY_PCT: 8.0})
    command = adb.calls[-1][0]
    assert f"--set {Prop.RANGE_REMAINING} -f 22000.0 -a 0" in command
    assert f"--set {Prop.EV_BATTERY_LEVEL} -f 12000.0 -a 0" in command


def test_aaos_signal_reads_back_in_screen_units():
    adb = FakeAdb({
        hex(Prop.INFO_EV_BATTERY_CAPACITY): "floatValues: [150000.0], int32Values: []",
        hex(Prop.EV_BATTERY_LEVEL): "floatValues: [63000.0], int32Values: []",
        hex(Prop.RANGE_REMAINING): "floatValues: [154000.0], int32Values: []",
        hex(Prop.DOOR_LOCK): "floatValues: [], int32Values: [1]",
        hex(Prop.HVAC_FAN_SPEED): "floatValues: [], int32Values: [4]",
    })
    car = AaosVehicle(adb)
    assert car.signal(Signal.BATTERY_PCT) == 42.0
    assert car.signal(Signal.RANGE_KM) == 154.0
    assert car.signal(Signal.DOORS_LOCKED) is True
    assert car.signal(Signal.FAN) == 4
    assert car.signal_all(Signal.DOORS_LOCKED) == [True, True, True, True]


def test_aaos_signal_batch_retries_once_then_fails(monkeypatch):
    """여러 개 중 하나라도 안 들어가면 통째로 다시 넣고, 그래도 안 되면 몇 개가 들어갔는지 알려 주며 실패한다."""
    monkeypatch.setattr("ivi.vehicle.time.sleep", lambda _: None)

    class Partial(FakeAdb):
        def __init__(self, good_after):
            super().__init__()
            self.good_after = good_after

        def shell(self, *args, **_):
            self.calls.append(args)
            wanted = args[0].count("--set")
            return "Set property: {}\n" * (wanted if len(self.calls) > self.good_after else wanted - 1)

    car = AaosVehicle(Partial(good_after=1))
    car.set_signal(Signal.FAN, 5)
    assert car.retried == ["VHAL --set fan: 2번째에 성공"]

    with pytest.raises(RuntimeError, match=r"실패 \(4/5\)"):
        AaosVehicle(Partial(good_after=9)).set_signal(Signal.FAN, 5)


def test_mock_signals_use_typed_extras():
    adb = FakeAdb()
    MockVehicle(adb).set_signals({Signal.AC: False, Signal.FAN: 5, Signal.RANGE_KM: 22})
    args = adb.calls[0]
    assert args[args.index("ac") - 1:args.index("ac") + 2] == ("--ez", "ac", "false")
    assert args[args.index("fan") - 1:args.index("fan") + 2] == ("--ei", "fan", "5")
    assert args[args.index("range_km") - 1:args.index("range_km") + 2] == ("--ef", "range_km", "22.0")


def test_mock_signal_is_parsed_by_type():
    adb = FakeAdb({"mock.GET": 'Broadcast completed: result=0, data="ac=true;fan=4;doors_locked=false;range_km=154.0;heat_driver=2"'})
    car = MockVehicle(adb)
    assert (car.signal(Signal.AC), car.signal(Signal.FAN), car.signal(Signal.DOORS_LOCKED)) == (True, 4, False)
    assert car.signal(Signal.RANGE_KM) == 154.0
    assert car.signal_all(Signal.heat(Seat.DRIVER)) == [2]


def test_reset_cabin_sets_every_signal_on_both_adapters():
    """기준 값 초기화는 신호 12개를 모두 넣는다 (하나라도 빠지면 테스트끼리 영향을 준다)."""
    mock = FakeAdb()
    MockVehicle(mock).reset_cabin()
    assert all(name in mock.calls[0] for name in CABIN_DEFAULTS)

    aaos = FakeAdb({hex(Prop.INFO_EV_BATTERY_CAPACITY): "floatValues: [150000.0], int32Values: []", "--set": "Set property: {}\n" * 31})
    AaosVehicle(aaos).reset_cabin()
    assert aaos.calls[-1][0].count("--set") == 31  # 좌석 5 × 4 + 김서림 2 + 열선 2 + 문 4 + 센서 3
