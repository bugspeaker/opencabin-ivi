"""Test Bench REST API.

벤치에 붙은 기기를 HTTP 로 다룬다. 다른 팀의 도구나 CI 가 adb 명령을 직접 몰라도 기기 상태를 보고, 차량 신호를 넣고,
전원을 껐다 켜고, 테스트를 돌리고, 결과를 가져갈 수 있게 하려는 것이다. 표준 라이브러리(http.server)만 쓴다.

    GET  /api                              경로 목록
    GET  /api/health
    GET  /api/devices                      기기 목록
    GET  /api/devices/{serial}/signals     차량 신호 (CABIN_DEFAULTS 12종, 좌석 온도, 주행 중 제한)
    POST /api/devices/{serial}/signals     신호 넣기 {"gear": "D", "speed_kmh": 50, "range_km": 25, "temp_driver": 22.5, ...}
    GET  /api/devices/{serial}/power       전원 상태
    POST /api/devices/{serial}/power       {"action": "off" | "on" | "cycle"}. cycle 은 부팅에 걸린 초를 돌려준다
    GET  /api/runs?limit=5                 최근 실행 요약 (reports/runs/*.json)
    GET  /api/runs/{name}                  실행 하나 전체 (name = <run_id>-<serial>)
    POST /api/jobs                         테스트 실행 시작 {"serial": "...", "markers": "smoke"} → 202
    GET  /api/jobs/{id}                    실행 상태 (running, passed, failed)

실행: python tools/bench_api.py  (기본 127.0.0.1:8770, 벤치 PC 밖으로 열지 않는다)
"""
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ivi.power import NotSupported, PowerError
from ivi.vehicle import CABIN_DEFAULTS, Seat

# 넣을 수 있는 값의 범위. 앱과 에뮬레이터 VHAL config 에 맞춘다
LIMITS = {
    "speed_kmh": (0.0, 250.0), "temp_driver": (16.0, 28.0), "temp_passenger": (16.0, 28.0),
    "fan": (1, 7), "heat_driver": (0, 2), "heat_passenger": (0, 2),
    "range_km": (0.0, 1000.0), "battery_pct": (0.0, 100.0), "outside_c": (-40.0, 60.0),
}
GEARS = ("P", "R", "D")
MARKERS = re.compile(r"^[\w\s()]{1,80}$")  # "smoke or sanity" 같은 마커 식만 받는다


class ApiError(Exception):
    def __init__(self, status, message, **extra):
        super().__init__(message)
        self.status = status
        self.body = {"error": message, **extra}


class BenchDevice:
    """API 가 다루는 기기 하나. vehicle 은 ivi.vehicle.VehicleController, power 는 ivi.power.PowerController (없어도 된다)."""

    def __init__(self, serial, kind, model, vehicle, power=None):
        self.serial, self.kind, self.model, self.vehicle, self.power = serial, kind, model, vehicle, power
        self.lock = threading.Lock()  # 한 기기에 요청이 겹치지 않게

    def describe(self):
        return {"serial": self.serial, "kind": self.kind, "model": self.model,
                "power": self.power.name if self.power else None}


def validate_signals(body):
    """요청 본문을 검사하고 (차량 신호, 기어, 속도, 좌석 온도) 로 나눈다. 틀리면 400."""
    if not isinstance(body, dict) or not body:
        raise ApiError(HTTPStatus.BAD_REQUEST, "신호를 JSON 객체로 보낸다. 예: {\"gear\": \"D\", \"speed_kmh\": 50}")
    known = set(CABIN_DEFAULTS) | {"gear", "speed_kmh", "temp_driver", "temp_passenger"}
    unknown = sorted(set(body) - known)
    if unknown:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"모르는 신호: {', '.join(unknown)}", known=sorted(known))
    errors = []
    for name, value in body.items():
        if name == "gear":
            if value not in GEARS:
                errors.append(f"gear 는 {'/'.join(GEARS)} 중 하나")
            continue
        expected = type(CABIN_DEFAULTS[name]) if name in CABIN_DEFAULTS else float
        if expected is bool:
            if not isinstance(value, bool):
                errors.append(f"{name} 는 true/false")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{name} 는 숫자")
            continue
        if expected is int and value != int(value):
            errors.append(f"{name} 는 정수")
            continue
        low, high = LIMITS.get(name, (None, None))
        if low is not None and not low <= value <= high:
            errors.append(f"{name} 는 {low:g}~{high:g}")
    if "speed_kmh" in body and body.get("gear") != "D":
        errors.append("speed_kmh 는 gear 가 D 일 때만 넣는다")
    for seat in ("temp_driver", "temp_passenger"):
        if seat in body and isinstance(body[seat], (int, float)) and (body[seat] * 2) != int(body[seat] * 2):
            errors.append(f"{seat} 는 0.5 단위")
    if errors:
        raise ApiError(HTTPStatus.BAD_REQUEST, "; ".join(errors))
    cabin = {name: (type(CABIN_DEFAULTS[name])(value)) for name, value in body.items() if name in CABIN_DEFAULTS}
    temps = {Seat.DRIVER: body.get("temp_driver"), Seat.PASSENGER: body.get("temp_passenger")}
    return cabin, body.get("gear"), float(body.get("speed_kmh", 0.0)), {s: float(t) for s, t in temps.items() if t is not None}


class Bench:
    """REST 경로가 하는 일. HTTP 와 떼어 두어 단위 테스트에서 바로 부를 수 있다."""

    def __init__(self, devices, runs_dir=None, pytest_cmd=None, cwd=None):
        self.devices = {d.serial: d for d in devices}
        self.runs_dir = Path(runs_dir) if runs_dir else None
        self.pytest_cmd = pytest_cmd or [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        self.cwd = cwd
        self.jobs = {}

    def device(self, serial):
        if serial not in self.devices:
            raise ApiError(HTTPStatus.NOT_FOUND, f"없는 기기: {serial}", devices=sorted(self.devices))
        return self.devices[serial]

    # ---- 기기 · 신호 ----
    def list_devices(self):
        return {"devices": [d.describe() for d in self.devices.values()]}

    def read_signals(self, serial):
        d = self.device(serial)
        with d.lock:
            values = {name: d.vehicle.signal(name) for name in CABIN_DEFAULTS}
            values["temp_driver"] = d.vehicle.temperature(Seat.DRIVER)
            values["temp_passenger"] = d.vehicle.temperature(Seat.PASSENGER)
            values["restricted"] = d.vehicle.is_restricted()
        return {"serial": serial, "signals": values}

    def write_signals(self, serial, body):
        d = self.device(serial)
        cabin, gear, speed, temps = validate_signals(body)
        with d.lock:
            for seat, celsius in temps.items():
                d.vehicle.set_temperature(seat, celsius)
            if cabin:
                d.vehicle.set_signals(cabin)
            if gear == "P":
                d.vehicle.park()
            elif gear == "R":
                d.vehicle.reverse()
            elif gear == "D":
                d.vehicle.drive(speed)
        return {"serial": serial, "applied": body}

    # ---- 전원 ----
    def power_state(self, serial):
        d = self.device(serial)
        if not d.power:
            return {"serial": serial, "supported": False}
        return {"serial": serial, "supported": True, "controller": d.power.name, "on": d.power.is_on()}

    def power_action(self, serial, body):
        d = self.device(serial)
        action = body.get("action") if isinstance(body, dict) else None
        if action not in ("off", "on", "cycle"):
            raise ApiError(HTTPStatus.BAD_REQUEST, "action 은 off, on, cycle 중 하나")
        if not d.power:
            raise ApiError(HTTPStatus.NOT_IMPLEMENTED, f"{serial} 에는 전원 제어가 없다")
        with d.lock:
            try:
                if action == "cycle":
                    return {"serial": serial, "action": action, "boot_seconds": round(d.power.cycle(), 1)}
                getattr(d.power, action)()
            except NotSupported as error:
                raise ApiError(HTTPStatus.NOT_IMPLEMENTED, str(error)) from error
            except PowerError as error:
                raise ApiError(HTTPStatus.BAD_GATEWAY, str(error)) from error
        return {"serial": serial, "action": action}

    # ---- 실행 기록 ----
    def _run_files(self):
        if not self.runs_dir or not self.runs_dir.exists():
            return []
        return sorted(self.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    def list_runs(self, limit=10):
        rows = []
        for path in self._run_files()[:limit]:
            summary = json.loads(path.read_text(encoding="utf-8"))["summary"]
            rows.append({"name": path.stem, **{k: summary.get(k) for k in ("run_id", "serial", "kind", "counts", "gate", "duration")}})
        return {"runs": rows}

    def get_run(self, name):
        for path in self._run_files():
            if path.stem == name:
                return json.loads(path.read_text(encoding="utf-8"))
        raise ApiError(HTTPStatus.NOT_FOUND, f"없는 실행: {name}")

    # ---- 원격 실행 ----
    def start_job(self, body):
        if not isinstance(body, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "본문은 JSON 객체")
        serial = body.get("serial")
        self.device(serial)
        markers = body.get("markers")
        if markers is not None and not (isinstance(markers, str) and MARKERS.match(markers)):
            raise ApiError(HTTPStatus.BAD_REQUEST, "markers 는 'smoke or sanity' 같은 마커 식")
        if any(j["serial"] == serial and j["status"] == "running" for j in self.jobs.values()):
            raise ApiError(HTTPStatus.CONFLICT, f"{serial} 에서 이미 실행 중이다")
        command = [*self.pytest_cmd, "--serial", serial, *(["-m", markers] if markers else [])]
        job = {"id": uuid.uuid4().hex[:12], "serial": serial, "markers": markers, "status": "running",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "returncode": None, "output_tail": ""}
        self.jobs[job["id"]] = job
        threading.Thread(target=self._run_job, args=(job, command), daemon=True).start()
        return job

    def _run_job(self, job, command):
        done = subprocess.run(command, cwd=self.cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        job["returncode"] = done.returncode
        job["output_tail"] = (done.stdout + done.stderr).strip()[-2000:]
        job["status"] = "passed" if done.returncode == 0 else "failed"

    def job(self, job_id):
        if job_id not in self.jobs:
            raise ApiError(HTTPStatus.NOT_FOUND, f"없는 실행 작업: {job_id}")
        return self.jobs[job_id]


# ---------------- HTTP ----------------

ROUTES = [
    ("GET", r"/api", "routes", "경로 목록"),
    ("GET", r"/api/health", "health", "상태 확인"),
    ("GET", r"/api/devices", "list_devices", "기기 목록"),
    ("GET", r"/api/devices/(?P<serial>[\w.:-]+)/signals", "read_signals", "차량 신호 읽기"),
    ("POST", r"/api/devices/(?P<serial>[\w.:-]+)/signals", "write_signals", "차량 신호 넣기"),
    ("GET", r"/api/devices/(?P<serial>[\w.:-]+)/power", "power_state", "전원 상태"),
    ("POST", r"/api/devices/(?P<serial>[\w.:-]+)/power", "power_action", "전원 끄기, 켜기, 껐다 켜기"),
    ("GET", r"/api/runs", "list_runs", "최근 실행 요약"),
    ("GET", r"/api/runs/(?P<name>[\w.-]+)", "get_run", "실행 하나 전체"),
    ("POST", r"/api/jobs", "start_job", "테스트 실행 시작"),
    ("GET", r"/api/jobs/(?P<job_id>\w+)", "job", "실행 상태"),
]


def _handler(bench):
    class Handler(BaseHTTPRequestHandler):
        server_version = "OpenCabinBench/1.0"

        def log_message(self, *args):  # 요청마다 stderr 에 찍지 않는다
            pass

        def _send(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ApiError(HTTPStatus.BAD_REQUEST, f"JSON 이 아니다: {error}") from error

        def _dispatch(self, method):
            url = urlsplit(self.path)
            path = url.path.rstrip("/") or "/"
            allowed = []
            try:
                for route_method, pattern, name, _ in ROUTES:
                    found = re.fullmatch(pattern, path)
                    if not found:
                        continue
                    if route_method != method:
                        allowed.append(route_method)
                        continue
                    status, body = HTTPStatus.OK, None
                    if name == "routes":
                        body = {"routes": [{"method": m, "path": p, "description": d} for m, p, _, d in ROUTES]}
                    elif name == "health":
                        body = {"ok": True, "devices": len(bench.devices)}
                    elif name == "list_runs":
                        limit = int(parse_qs(url.query).get("limit", ["10"])[0])
                        body = bench.list_runs(limit=max(1, min(limit, 100)))
                    elif method == "POST":
                        args = {**found.groupdict(), "body": self._body()}
                        body = getattr(bench, name)(**args)
                        status = HTTPStatus.ACCEPTED if name == "start_job" else HTTPStatus.OK
                    else:
                        body = getattr(bench, name)(**found.groupdict())
                    return self._send(status, body)
                if allowed:
                    return self._send(HTTPStatus.METHOD_NOT_ALLOWED, {"error": f"{method} 는 안 된다", "allowed": allowed})
                return self._send(HTTPStatus.NOT_FOUND, {"error": f"없는 경로: {path}"})
            except ApiError as error:
                return self._send(error.status, error.body)
            except ValueError as error:
                return self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except Exception as error:  # noqa: BLE001 - 기기 쪽 오류(adb 등)는 502 로 알린다
                return self._send(HTTPStatus.BAD_GATEWAY, {"error": f"{type(error).__name__}: {error}"})

        def do_GET(self):  # noqa: N802
            self._dispatch("GET")

        def do_POST(self):  # noqa: N802
            self._dispatch("POST")

    return Handler


def make_server(bench, host="127.0.0.1", port=8770):
    return ThreadingHTTPServer((host, port), _handler(bench))


def serve_in_thread(bench, host="127.0.0.1", port=0):
    """테스트용: 빈 포트에 띄우고 (server, base_url) 를 돌려준다. 끝나면 server.shutdown()."""
    server = make_server(bench, host, port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{host}:{server.server_address[1]}"


def call(base_url, method, path, body=None, timeout=300):
    """간단한 클라이언트. (상태 코드, JSON) 을 돌려준다."""
    import urllib.error
    import urllib.request
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 벤치 내부 주소
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8") or "{}")
