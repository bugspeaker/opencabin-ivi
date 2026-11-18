"""Test Bench REST API 와 전원 제어 (기기 없이). 가짜 차량과 가짜 전원을 붙여 실제 HTTP 로 부른다."""
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ivi.bench_api import Bench, BenchDevice, call, serve_in_thread
from ivi.power import AdbRebootPower, HttpRelayPower, NotSupported, PowerController
from ivi.vehicle import CABIN_DEFAULTS, Seat


class FakeVehicle:
    def __init__(self):
        self.values = dict(CABIN_DEFAULTS)
        self.temps = {Seat.DRIVER: 22.0, Seat.PASSENGER: 22.0}
        self.gear, self.speed = "P", 0.0

    def signal(self, name):
        return self.values[name]

    def set_signals(self, values):
        self.values.update(values)

    def temperature(self, seat):
        return self.temps[seat]

    def set_temperature(self, seat, celsius):
        self.temps[seat] = celsius

    def drive(self, kmh=50.0):
        self.gear, self.speed = "D", kmh

    def park(self):
        self.gear, self.speed = "P", 0.0

    def reverse(self):
        self.gear, self.speed = "R", 0.0

    def is_restricted(self):
        return self.gear == "D" and self.speed > 0


class FakePower(PowerController):
    name = "가짜 전원"
    off_seconds = 0.0

    def __init__(self):
        self.powered, self.log = True, []

    def off(self):
        self.powered = False
        self.log.append("off")

    def on(self):
        self.powered = True
        self.log.append("on")

    def is_on(self):
        return self.powered


@pytest.fixture
def bench(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "20261118-100000-emulator-5554.json").write_text(json.dumps({
        "summary": {"run_id": "20261118-100000", "serial": "emulator-5554", "kind": "aaos",
                    "counts": {"passed": 3}, "gate": "pass", "duration": 12.5},
        "tests": [{"nodeid": "tests/test_smoke.py::test_parked_on_start", "outcome": "passed"}],
    }), encoding="utf-8")
    car, power = FakeVehicle(), FakePower()
    bench = Bench(
        [BenchDevice("emulator-5554", "aaos", "Car on x86_64", car, power), BenchDevice("tablet", "mock", "DBY-W09", FakeVehicle())],
        runs_dir=runs, pytest_cmd=[sys.executable, "-c", "import sys; print('args', sys.argv[1:])"],
    )
    server, url = serve_in_thread(bench)
    yield {"url": url, "car": car, "power": power, "bench": bench}
    server.shutdown()


def test_lists_devices_and_routes(bench):
    status, body = call(bench["url"], "GET", "/api/devices")
    assert status == 200
    assert [d["serial"] for d in body["devices"]] == ["emulator-5554", "tablet"]
    assert body["devices"][0]["power"] == "가짜 전원" and body["devices"][1]["power"] is None
    status, body = call(bench["url"], "GET", "/api")
    assert status == 200 and {"POST", "GET"} <= {r["method"] for r in body["routes"]}


def test_signals_written_by_api_reach_vehicle_and_read_back(bench):
    url, car = bench["url"], bench["car"]
    status, _ = call(url, "POST", "/api/devices/emulator-5554/signals",
                     {"gear": "D", "speed_kmh": 50, "range_km": 25, "doors_locked": False, "fan": 5, "temp_driver": 23.5})
    assert status == 200
    assert (car.gear, car.speed) == ("D", 50.0)
    assert car.values["range_km"] == 25.0 and isinstance(car.values["range_km"], float)
    assert car.values["fan"] == 5 and isinstance(car.values["fan"], int)

    status, body = call(url, "GET", "/api/devices/emulator-5554/signals")
    signals = body["signals"]
    assert status == 200
    assert signals["doors_locked"] is False and signals["temp_driver"] == 23.5 and signals["restricted"] is True


@pytest.mark.parametrize("body, message", [
    ({}, "JSON 객체"),
    ({"speed": 50}, "모르는 신호: speed"),
    ({"fan": 9}, "fan 는 1~7"),
    ({"fan": 2.5}, "fan 는 정수"),
    ({"doors_locked": "no"}, "true/false"),
    ({"range_km": "25"}, "range_km 는 숫자"),
    ({"speed_kmh": 50}, "gear 가 D 일 때만"),
    ({"gear": "N"}, "gear 는 P/R/D"),
    ({"temp_driver": 22.3}, "0.5 단위"),
    ({"temp_passenger": 35.0}, "16~28"),
])
def test_rejects_invalid_signals_with_400(bench, body, message):
    status, reply = call(bench["url"], "POST", "/api/devices/emulator-5554/signals", body)
    assert status == 400
    assert message in reply["error"]
    assert bench["car"].values == CABIN_DEFAULTS, "검사에 걸린 요청이 차량 값을 바꿨다"


def test_errors_for_bad_json_unknown_device_path_and_method(bench):
    url = bench["url"]
    request = urllib.request.Request(url + "/api/devices/emulator-5554/signals", data=b"{not json", method="POST")
    try:
        urllib.request.urlopen(request, timeout=5)
        raise AssertionError("400 이어야 한다")
    except urllib.error.HTTPError as error:
        assert error.code == 400 and "JSON" in json.loads(error.read())["error"]
    assert call(url, "GET", "/api/devices/nope/signals")[0] == 404
    assert call(url, "GET", "/api/nope")[0] == 404
    status, body = call(url, "GET", "/api/jobs")
    assert status == 405 and body["allowed"] == ["POST"]


def test_power_cycle_and_unsupported_device(bench):
    url, power = bench["url"], bench["power"]
    assert call(url, "GET", "/api/devices/emulator-5554/power")[1]["on"] is True
    status, body = call(url, "POST", "/api/devices/emulator-5554/power", {"action": "cycle"})
    assert status == 200 and body["boot_seconds"] >= 0
    assert power.log == ["off", "on"]
    assert call(url, "POST", "/api/devices/emulator-5554/power", {"action": "explode"})[0] == 400
    assert call(url, "GET", "/api/devices/tablet/power")[1] == {"serial": "tablet", "supported": False}
    assert call(url, "POST", "/api/devices/tablet/power", {"action": "off"})[0] == 501


def test_runs_are_listed_and_readable(bench):
    status, body = call(bench["url"], "GET", "/api/runs?limit=5")
    assert status == 200 and body["runs"][0]["name"] == "20261118-100000-emulator-5554"
    assert body["runs"][0]["counts"] == {"passed": 3}
    status, body = call(bench["url"], "GET", "/api/runs/20261118-100000-emulator-5554")
    assert status == 200 and body["tests"][0]["outcome"] == "passed"
    assert call(bench["url"], "GET", "/api/runs/none")[0] == 404


def test_job_runs_pytest_command_for_device(bench):
    url = bench["url"]
    status, job = call(url, "POST", "/api/jobs", {"serial": "tablet", "markers": "smoke or sanity"})
    assert status == 202 and job["status"] == "running"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and job["status"] == "running":
        time.sleep(0.1)
        job = call(url, "GET", f"/api/jobs/{job['id']}")[1]
    assert job["status"] == "passed"
    assert "'--serial', 'tablet', '-m', 'smoke or sanity'" in job["output_tail"]
    assert call(url, "POST", "/api/jobs", {"serial": "tablet", "markers": "smoke; rm -rf /"})[0] == 400
    assert call(url, "POST", "/api/jobs", {"serial": "nope"})[0] == 404


def test_http_relay_power_speaks_tasmota_commands():
    state = {"power": "ON"}

    class Relay(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):  # noqa: N802
            command = urllib.parse.unquote(self.path.split("cmnd=", 1)[1])
            if command in ("Power On", "Power Off"):
                state["power"] = command.split()[1].upper()
            data = json.dumps({"POWER": state["power"]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Relay)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        relay = HttpRelayPower(f"http://127.0.0.1:{server.server_address[1]}")
        relay.off()
        assert state["power"] == "OFF" and relay.is_on() is False
        relay.on()
        assert relay.is_on() is True
    finally:
        server.shutdown()


def test_adb_reboot_power_cannot_switch_device_on():
    calls = []
    power = AdbRebootPower("tablet", run=lambda serial, *args, **kw: calls.append(args) or (0, "device"))
    power.off()
    assert calls == [("reboot", "-p")]
    with pytest.raises(NotSupported):
        power.on()
