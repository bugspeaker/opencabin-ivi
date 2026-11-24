"""기기 없이 어댑터의 명령 조립·출력 해석을 검증한다 (CI 의 GitHub 호스트에서 돈다)."""
import pytest

from ivi.device import Device
from ivi.screens import parse_celsius
from ivi.vehicle import CABIN_DEFAULTS, AaosVehicle, DrivingState, MockVehicle, Prop, Seat, Signal, Ux
from ivi.waits import WaitTimeout


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


class MockAppAdb(FakeAdb):
    """앱의 Mock 수신기처럼 SET 에 받은 extra 이름을 돌려준다 (data="applied=...")."""

    def shell(self, *args, **_):
        self.calls.append(args)
        if any(str(a).endswith("mock.SET") for a in args):
            keys = [args[i + 1] for i, a in enumerate(args) if a in ("--es", "--ef", "--ei", "--ez")]
            return f'Broadcast completed: result=0, data="applied={",".join(sorted(keys))}"'
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


DRIVING_DUMP = """*CarDrivingStateService*
Driving state change log:
Current Driving State: {state}
Current Gear: 8
"""


def test_aaos_driving_state_is_read_from_car_service():
    car = AaosVehicle(FakeAdb({"CarDrivingStateService": DRIVING_DUMP.format(state=2)}))
    assert car.driving_state() == DrivingState.MOVING
    assert car.is_restricted() is True


@pytest.mark.parametrize("out", ["", "Can't find service: CarDrivingStateService", "Current Driving State: moving"])
def test_aaos_unreadable_driving_state_fails_loudly(out):
    """상태 줄을 못 읽으면 '제한 없음'(False)이 아니라 오류다. 예전에는 UNKNOWN 을 돌려줘 is_restricted() 가 False 였다."""
    car = AaosVehicle(FakeAdb({"CarDrivingStateService": out}))
    with pytest.raises(RuntimeError, match="주행 상태를 읽지 못했다"):
        car.driving_state()
    with pytest.raises(RuntimeError, match="주행 상태를 읽지 못했다"):
        car.is_restricted()


def test_wait_restricted_false_does_not_pass_when_state_is_unreadable():
    """정차를 기다리는 동기화 지점(wait_restricted(False))이 못 읽은 상태를 '제한 없음'으로 보고 바로 지나가지 않는다."""
    car = AaosVehicle(FakeAdb({"CarDrivingStateService": "Can't find service"}))
    with pytest.raises(WaitTimeout, match="주행 중 제한 꺼짐") as caught:
        car.wait_restricted(False, timeout=0.3)
    assert "주행 상태를 읽지 못했다" in str(caught.value.error)


def test_aaos_dump_keeps_going_when_driving_state_is_unreadable():
    """실패 자료(dump)는 하나가 안 읽혀도 나머지를 모은다."""
    dump = AaosVehicle(FakeAdb({})).dump()
    assert "driving_state=<주행 상태를 읽지 못했다" in dump
    assert dump.splitlines()[0].startswith("speed_mps=")


def test_mock_state_is_parsed_from_broadcast_result():
    adb = FakeAdb({"mock.GET": 'Broadcasting: Intent { ... }\nBroadcast completed: result=0, '
                               'data="speed_kmh=50.0;gear=D;temp_driver=25.0;temp_passenger=22.0;restricted=true;moving=true;ux=255"'})
    car = MockVehicle(adb)
    assert car.is_restricted() is True
    assert car.ux_restrictions() == Ux.MOVING
    assert car.temperature(Seat.DRIVER) == 25.0


def test_mock_idling_is_restricted_for_video_but_not_moving():
    """D 기어로 멈춰 있으면 영상 제한(0x10)은 걸려 있지만 '주행 중'은 아니다 (is_restricted 는 주행 중만 뜻한다)."""
    adb = FakeAdb({"mock.GET": 'Broadcast completed: result=0, data="speed_kmh=0.0;gear=D;restricted=true;moving=false;ux=16"'})
    car = MockVehicle(adb)
    assert car.is_restricted() is False
    assert car.ux_restrictions() == Ux.NO_VIDEO


UXR_DUMP = """*CarUxRestrictionsManagerService*
UX Restrictions Clients:
Display id: 0 UXR: DO: {do} UxR: {ux} time: 10994804941
Display id: 3 UXR: DO: true UxR: 511 time: 12298537493
State:idling num restrictions:1
Restrictions: 0x10
"""


@pytest.mark.parametrize("do, ux, expected", [("true", 16, 0x10), ("true", 255, 0xff), ("false", 0, 0), ("false", 16, 0)])
def test_aaos_ux_restrictions_reads_main_display(do, ux, expected):
    """주 화면(display 0)의 줄만 읽는다. 클러스터(display 3)는 늘 전부 제한(511)이라 섞이면 안 된다. DO 가 false 면 0 이다."""
    adb = FakeAdb({"CarUxRestrictionsManagerService": UXR_DUMP.format(do=do, ux=ux)})
    assert AaosVehicle(adb).ux_restrictions() == expected


def test_aaos_ux_restrictions_fails_loudly_when_dump_changes():
    adb = FakeAdb({"CarUxRestrictionsManagerService": "*CarUxRestrictionsManagerService*\n(형식이 바뀜)"})
    with pytest.raises(RuntimeError, match="UX 제한을 읽지 못했다"):
        AaosVehicle(adb).ux_restrictions()


@pytest.mark.parametrize("gear, vhal", [("D", "8"), ("N", "1"), ("R", "2")])
def test_aaos_drive_sets_requested_gear(gear, vhal):
    adb = FakeAdb({"--set": "Set property: VehiclePropValue{...}"})
    AaosVehicle(adb).drive(0.0, gear=gear)
    call = [c for c in adb.calls if str(Prop.GEAR_SELECTION) in c][0]
    assert call[call.index("-i") + 1] == vhal


def test_mock_drive_passes_gear_label():
    adb = MockAppAdb()
    MockVehicle(adb).drive(0, gear="N")
    args = adb.calls[0]
    assert args[args.index("gear") + 1] == "N" and args[args.index("speed_kmh") + 1] == "0.0"


def test_mock_state_error_explains_app_must_run():
    adb = FakeAdb({"mock.GET": "Broadcast completed: result=0"})
    with pytest.raises(RuntimeError, match="앱이 떠 있는지"):
        MockVehicle(adb).state()


def test_mock_set_uses_string_for_gear_and_float_for_numbers():
    adb = MockAppAdb()
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
    adb = MockAppAdb()
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
    mock = MockAppAdb()
    MockVehicle(mock).reset_cabin()
    assert all(name in mock.calls[0] for name in CABIN_DEFAULTS)

    aaos = FakeAdb({hex(Prop.INFO_EV_BATTERY_CAPACITY): "floatValues: [150000.0], int32Values: []", "--set": "Set property: {}\n" * 31})
    AaosVehicle(aaos).reset_cabin()
    assert aaos.calls[-1][0].count("--set") == 31  # 좌석 5 × 4 + 김서림 2 + 열선 2 + 문 4 + 센서 3


def test_mock_set_fails_on_the_spot_when_app_did_not_take_the_values():
    """앱이 꺼져 있어 브로드캐스트가 전달되지 않으면(화웨이) 그 자리에서 실패한다. 뒤의 대기에서 엉뚱하게 실패하지 않게."""
    with pytest.raises(RuntimeError, match="들어가지 않았다"):
        MockVehicle(FakeAdb({"mock.SET": "Broadcast completed: result=0"})).set_temperature(Seat.DRIVER, 25.0)
    partial = FakeAdb({"mock.SET": 'Broadcast completed: result=0, data="applied=gear"'})
    with pytest.raises(RuntimeError, match="speed_kmh"):
        MockVehicle(partial).drive(50)


def test_aaos_inject_temperature_goes_straight_to_vhal():
    """범위 밖 값은 CarService 가 거절하므로, 차량 쪽 값은 VHAL --set 으로 넣는다."""
    adb = FakeAdb({"--set": "Set property: {}"})
    AaosVehicle(adb).inject_temperature(Seat.DRIVER, 15.5)
    call = adb.calls[0]
    assert call[:3] == ("dumpsys", "android.hardware.automotive.vehicle.IVehicle/default", "--set")
    assert call[call.index("-f") + 1] == "15.5" and call[call.index("-a") + 1] == "1"


def test_aaos_keeps_last_read_values_for_the_result_page():
    """마지막으로 읽은 VHAL 값(최대 3개)을 남긴다. 같은 property·area 는 마지막 값만, 다른 스레드(CAN 게이트웨이)가 읽은 값은 뺀다."""
    import threading
    adb = FakeAdb({
        "0x15600503 0x1": "floatValues: [22.5], int32Values: []",
        "0x15600503 0x4": "floatValues: [22.0], int32Values: []",
        "0x11400400": "floatValues: [], int32Values: [4]",
        "0x15200505": "floatValues: [], int32Values: [1]",
    })
    car = AaosVehicle(adb)
    car.temperature(Seat.DRIVER)
    car.get_property(Prop.GEAR_SELECTION)
    car.temperature(Seat.PASSENGER)
    car.temperature(Seat.DRIVER)
    worker = threading.Thread(target=lambda: car.get_property(Prop.HVAC_AC_ON, 0x1))
    worker.start()
    worker.join()
    assert car.take_observed() == ["GEAR_SELECTION=4", "HVAC_TEMPERATURE_SET[0x4]=22.0", "HVAC_TEMPERATURE_SET[0x1]=22.5"]
    assert car.take_observed() == []  # 꺼내면 비운다


def test_logcat_is_collected_from_test_start_without_clearing(monkeypatch):
    """실패 자료의 logcat 은 테스트 시작 시각(-T)부터 모으고, 버퍼를 지우지(-c) 않는다 (같은 기기를 쓰는 다른 도구의 로그 보존)."""
    from types import SimpleNamespace

    from ivi.adb import Adb

    calls = []

    def fake_run(cmd, **_):
        calls.append(cmd)
        out = "1763540703\n" if cmd[3:5] == ["shell", "date"] else "".join(f"line {i}\n" for i in range(5))
        return SimpleNamespace(returncode=0, stdout=out, stderr="")

    monkeypatch.setattr("ivi.adb.subprocess.run", fake_run)
    adb = Adb("emulator-5554")
    since = adb.log_mark()
    assert since == "1763540703.000"  # 점이 없으면 logcat 은 시각이 아니라 줄 수로 읽는다
    assert adb.logcat_dump(since=since, lines=3) == "line 2\nline 3\nline 4\n"
    assert calls[-1] == ["adb", "-s", "emulator-5554", "logcat", "-d", "-v", "threadtime", "-T", "1763540703.000"]
    assert not any("-c" in cmd for cmd in calls)


def test_aaos_cleanup_restores_only_what_this_test_saved():
    """정리는 준비가 중간에 실패해도 돈다. 저장 전에 실패했으면 정차만 하고, 앞 테스트가 저장한 값으로 되돌리지 않는다."""
    adb = FakeAdb({"whoami": "root", "--set": "Set property"})
    vehicle = AaosVehicle(adb)
    vehicle.cleanup()  # 준비 없이 정리 (준비 맨 앞에서 실패한 경우)
    assert not any("--restore-prop" in call for call in adb.calls)
    assert any("--set" in call for call in adb.calls)  # 정차는 한다

    adb.calls.clear()
    vehicle._saved = True  # 준비가 저장까지 한 경우
    vehicle.cleanup()
    assert sum("--restore-prop" in call for call in adb.calls) == 2
    adb.calls.clear()
    vehicle.cleanup()  # 같은 저장 값으로 두 번 되돌리지 않는다
    assert not any("--restore-prop" in call for call in adb.calls)


def test_app_identity_reads_apk_hash_and_version(monkeypatch):
    """결과 파일에 남기는 빌드 식별값: 기기에 있는 APK 의 sha256 과 versionName (versionCode). 못 읽으면 빈 값."""
    from ivi.adb import Adb, AdbError

    outputs = {"pm path": "package:/data/app/dev.opencabin.ivi/base.apk\n",
               "sha256sum": "ab" * 32 + "  /data/app/dev.opencabin.ivi/base.apk\n",
               "dumpsys package": "    versionCode=7 minSdk=31\n    versionName=0.9.0\n"}
    adb = Adb("s1")
    monkeypatch.setattr(adb, "shell", lambda *args, **_: next(v for k, v in outputs.items() if k in " ".join(args)))
    assert adb.app_identity("dev.opencabin.ivi") == {"version": "0.9.0 (7)", "apk_sha256": "ab" * 32}

    def broken(*_args, **_kw):
        raise AdbError("device offline")
    monkeypatch.setattr(adb, "shell", broken)
    assert adb.app_identity("dev.opencabin.ivi") == {"version": "", "apk_sha256": ""}
