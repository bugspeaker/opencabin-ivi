"""Test Bench REST API 와 전원 제어 (기기 없이). 가짜 차량과 가짜 전원을 붙여 실제 HTTP 로 부른다."""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ivi.bench_api import ApiError, Bench, BenchDevice, call, serve_in_thread
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


def test_emulator_power_restarts_without_window():
    """다시 켤 때 창 없이 켠다. 화면이 꺼진 무인 벤치에서 창 모드 재시작이 멈췄다 (2026-11-21, ivi/power.py)."""
    from ivi.power import EmulatorPower

    power = EmulatorPower("emulator-5554", sdk_root="C:/android")
    power.avd = "OpenCabin_AAOS_34"
    command = power.command()
    assert command[1:5] == ["-avd", "OpenCabin_AAOS_34", "-port", "5554"]
    assert {"-writable-system", "-no-snapshot", "-no-window"} <= set(command)


# ---- 예외 경로: 동시 요청, 실행 중 조작, 실행 실패, 잘못된 입력 (2026-11-24 외부 검토 IVI-REV-03, 04) ----

def make_bench(**kwargs):
    car, power = FakeVehicle(), FakePower()
    devices = [BenchDevice("emulator-5554", "aaos", "Car", car, power), BenchDevice("tablet", "mock", "Tab", FakeVehicle())]
    return Bench(devices, **kwargs), car, power


def sleeping(seconds):
    return [sys.executable, "-c", f"import time; time.sleep({seconds})"]


def wait_job_done(bench, job_id, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = bench.job(job_id)
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError(f"{timeout}초 안에 끝나지 않았다: {bench.job(job_id)}")


def test_same_device_accepts_only_one_of_simultaneous_jobs(monkeypatch):
    """같은 기기에 동시에 온 실행 요청 8개 가운데 하나만 받고 나머지는 409다. 다른 기기는 그대로 같이 돈다.
    '실행 중인지 보기'와 '등록' 사이를 일부러 늘려(uuid 를 느리게) 예전 코드라면 8개가 모두 통과하는 조건을 만든다."""
    import ivi.bench_api as bench_api

    real_uuid4 = bench_api.uuid.uuid4
    monkeypatch.setattr(bench_api.uuid, "uuid4", lambda: (time.sleep(0.05), real_uuid4())[1])
    bench, _, _ = make_bench(pytest_cmd=sleeping(1))
    barrier, results = threading.Barrier(8), []

    def request():
        barrier.wait()
        try:
            results.append(bench.start_job({"serial": "emulator-5554"})["id"])
        except ApiError as error:
            results.append(int(error.status))

    threads = [threading.Thread(target=request) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    accepted = [r for r in results if isinstance(r, str)]
    assert len(accepted) == 1 and results.count(409) == 7, results

    other = bench.start_job({"serial": "tablet"})
    assert bench.devices["tablet"].job == other["id"], "다른 기기는 동시에 돌 수 있어야 한다"
    assert {wait_job_done(bench, job_id)["status"] for job_id in (accepted[0], other["id"])} == {"passed"}


def test_vehicle_and_power_changes_are_refused_while_job_runs():
    """테스트가 도는 기기에는 신호 넣기와 전원 조작이 409 로 거절되고 차량·전원은 그대로다. 읽기와 다른 기기는 된다.
    실행이 끝나면 바로 다시 넣을 수 있다."""
    bench, car, power = make_bench(pytest_cmd=sleeping(1.5))
    server, url = serve_in_thread(bench)
    try:
        status, job = call(url, "POST", "/api/jobs", {"serial": "emulator-5554"})
        assert status == 202
        status, body = call(url, "POST", "/api/devices/emulator-5554/signals", {"gear": "D", "speed_kmh": 50})
        assert status == 409 and body["job"] == job["id"]
        assert call(url, "POST", "/api/devices/emulator-5554/power", {"action": "off"})[0] == 409
        assert (car.gear, car.speed) == ("P", 0.0) and power.log == [] and power.powered

        assert call(url, "GET", "/api/devices/emulator-5554/signals")[0] == 200
        assert call(url, "GET", "/api/devices/emulator-5554/power")[0] == 200
        assert call(url, "POST", "/api/devices/tablet/signals", {"gear": "R"})[0] == 200
        assert [d["job"] for d in call(url, "GET", "/api/devices")[1]["devices"]] == [job["id"], None]

        assert wait_job_done(bench, job["id"])["status"] == "passed"
        assert call(url, "POST", "/api/devices/emulator-5554/signals", {"gear": "D", "speed_kmh": 50})[0] == 200
        assert (car.gear, car.speed) == ("D", 50.0)
    finally:
        server.shutdown()


def test_job_request_waits_for_power_cycle_in_progress():
    """전원을 껐다 켜는 중에 온 실행 요청은 거절하지 않고, 껐다 켜기가 끝난 뒤에 시작한다."""
    released = threading.Event()

    class SlowPower(FakePower):
        def off(self):
            super().off()
            released.wait(10)

    bench = Bench([BenchDevice("emulator-5554", "aaos", "Car", FakeVehicle(), SlowPower())], pytest_cmd=sleeping(0))
    power = bench.devices["emulator-5554"].power
    cycle = threading.Thread(target=bench.power_action, args=("emulator-5554", {"action": "cycle"}))
    cycle.start()
    while not power.log:
        time.sleep(0.01)
    started = []
    request = threading.Thread(target=lambda: started.append(bench.start_job({"serial": "emulator-5554"})))
    request.start()
    request.join(0.3)
    assert not started, "껐다 켜는 도중에 테스트가 시작됐다"
    released.set()
    cycle.join(10)
    request.join(10)
    assert power.log == ["off", "on"] and len(started) == 1
    assert wait_job_done(bench, started[0]["id"])["status"] == "passed"


@pytest.mark.parametrize("problem", ["no_program", "no_workdir"])
def test_job_that_cannot_start_ends_as_error_and_frees_device(tmp_path, problem):
    """실행 파일이나 작업 폴더가 없으면 작업이 running 에 남지 않고 error 로 끝난다. 같은 기기에 바로 다시 실행할 수 있다."""
    if problem == "no_program":
        bench, _, _ = make_bench(pytest_cmd=[str(tmp_path / "no-such-program.exe")])
    else:
        bench, _, _ = make_bench(pytest_cmd=sleeping(0), cwd=tmp_path / "missing")
    job = wait_job_done(bench, bench.start_job({"serial": "emulator-5554"})["id"])
    assert job["status"] == "error" and "시작하지 못했다" in job["error"] and job["finished"]
    assert bench.devices["emulator-5554"].job is None
    again = bench.start_job({"serial": "emulator-5554"})  # 예전에는 409 '이미 실행 중'
    wait_job_done(bench, again["id"])


def test_job_over_time_limit_is_stopped_and_frees_device():
    """시간 제한을 넘은 실행은 프로세스를 멈추고 timeout 으로 남긴다. 멈추기 전까지의 출력(한글 포함)은 남는다."""
    script = "import time; print('테스트 시작', flush=True); time.sleep(60)"
    bench, _, _ = make_bench(pytest_cmd=[sys.executable, "-c", script], job_timeout=3)
    started = time.monotonic()
    job = wait_job_done(bench, bench.start_job({"serial": "emulator-5554"})["id"], timeout=30)
    assert job["status"] == "timeout" and job["returncode"] is not None and "3초" in job["error"]
    assert time.monotonic() - started < 20
    assert "테스트 시작" in job["output_tail"]
    assert bench.devices["emulator-5554"].job is None


def test_unexpected_error_in_job_thread_is_recorded(monkeypatch):
    """실행 스레드에서 예상하지 못한 예외가 나도 작업은 error 로 끝나고 기기는 풀린다."""
    bench, _, _ = make_bench()
    monkeypatch.setattr(bench, "_execute", lambda command: 1 / 0)
    job = wait_job_done(bench, bench.start_job({"serial": "tablet"})["id"])
    assert job["status"] == "error" and "ZeroDivisionError" in job["error"]
    assert bench.devices["tablet"].job is None


def test_job_output_keeps_korean_text():
    """테스트 출력의 한글이 깨지지 않는다. Python 3.12 Windows 에서는 자식이 cp949 로 써서 utf-8 로 읽으면 깨졌다."""
    bench, _, _ = make_bench(pytest_cmd=[sys.executable, "-c", "print('통과 3개, 실패 0개')"])
    job = wait_job_done(bench, bench.start_job({"serial": "tablet"})["id"])
    assert "통과 3개, 실패 0개" in job["output_tail"]


def test_malformed_requests_get_4xx_instead_of_502(bench):
    """서버 쪽 오류(502)가 아니라 요청 잘못(4xx)으로 답한다. 예전에는 아래 셋이 502 였다."""
    url = bench["url"]
    status, body = call(url, "POST", "/api/jobs", {"serial": ["tablet"]})  # 목록은 dict 키가 될 수 없어 TypeError
    assert status == 400 and "serial" in body["error"]
    for raw in (b'{"fan": Infinity}', b'{"temp_driver": NaN}'):  # 파이썬 json 은 기본으로 받아 준다
        request = urllib.request.Request(url + "/api/devices/emulator-5554/signals", data=raw, method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=5)
        assert error.value.code == 400
    with pytest.raises(ApiError) as error:  # HTTP 를 거치지 않고 부를 때도
        bench["bench"].write_signals("emulator-5554", {"fan": float("inf")})
    assert error.value.status == 400 and "유한한 숫자" in error.value.body["error"]
    assert bench["car"].values == CABIN_DEFAULTS


@pytest.mark.parametrize("length, expected", [("-1", 400), (str(64 * 1024 + 1), 413), ("abc", 400)])
def test_bad_content_length_is_answered_without_waiting(bench, length, expected):
    """Content-Length 가 음수면 예전에는 연결이 닫힐 때까지 본문을 기다렸다(요청 스레드가 묶인다). 너무 큰 본문은 읽지 않는다."""
    import http.client

    host, port = bench["url"].removeprefix("http://").split(":")
    connection = http.client.HTTPConnection(host, int(port), timeout=5)
    try:
        connection.putrequest("POST", "/api/devices/emulator-5554/signals")
        connection.putheader("Content-Length", length)
        connection.endheaders()
        assert connection.getresponse().status == expected
    finally:
        connection.close()


def test_unreadable_run_file_does_not_break_run_list(bench):
    """실행이 아직 쓰는 중인 결과 파일이 있어도 목록은 나온다. 그 줄만 오류로 표시하고, 그 파일을 직접 달라면 503."""
    url = bench["url"]
    (bench["bench"].runs_dir / "20261118-110000-tablet.json").write_text('{"summary": {"run_id": "2026', encoding="utf-8")
    status, body = call(url, "GET", "/api/runs")
    rows = {row["name"]: row for row in body["runs"]}
    assert status == 200 and "error" in rows["20261118-110000-tablet"]
    assert rows["20261118-100000-emulator-5554"]["counts"] == {"passed": 3}
    assert call(url, "GET", "/api/runs/20261118-110000-tablet")[0] == 503
