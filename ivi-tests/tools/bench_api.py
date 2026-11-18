"""Test Bench REST API 서버를 띄운다 (ivi/bench_api.py).

    python tools/bench_api.py                       # 연결된 기기 전부, 127.0.0.1:8770
    python tools/bench_api.py --port 8770 --relay W3VB...=http://192.168.0.50   # 그 기기는 HTTP 릴레이로 전원 제어

    curl http://127.0.0.1:8770/api/devices
    curl -X POST http://127.0.0.1:8770/api/devices/emulator-5554/signals -d "{\"gear\": \"D\", \"speed_kmh\": 50}"
    curl -X POST http://127.0.0.1:8770/api/devices/emulator-5554/power -d "{\"action\": \"cycle\"}"

전원 제어: 에뮬레이터는 EmulatorPower(끄고 다시 켜기), 실기기는 AdbRebootPower(재부팅만), --relay 를 준 기기는 HttpRelayPower.
벤치 PC 안에서만 쓰도록 기본 주소는 127.0.0.1 이다. 인증이 없으므로 밖으로 열지 않는다.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ivi.bench_api import Bench, BenchDevice, make_server  # noqa: E402
from ivi.device import Device  # noqa: E402
from ivi.power import AdbRebootPower, EmulatorPower, HttpRelayPower  # noqa: E402


def connected_serials():
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("device")]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--relay", action="append", default=[], metavar="SERIAL=URL", help="HTTP 릴레이로 전원을 제어할 기기")
    args = parser.parse_args()

    relays = dict(item.split("=", 1) for item in args.relay)
    devices = []
    for serial in connected_serials():
        device = Device.connect(serial)
        if hasattr(device.vehicle, "ensure_root"):
            device.vehicle.ensure_root()  # AAOS: 읽기 전용 센서 값을 넣으려면 root
        if serial in relays:
            power = HttpRelayPower(relays[serial])
        elif serial.startswith("emulator-"):
            power = EmulatorPower(serial, log_dir=ROOT / "reports" / "logs")
        else:
            power = AdbRebootPower(serial)
        devices.append(BenchDevice(serial, device.kind, device.model, device.vehicle, power))
        print(f"  {serial}  {device.label}  전원: {power.name}")

    bench = Bench(devices, runs_dir=ROOT / "reports" / "runs", cwd=ROOT)
    server = make_server(bench, args.host, args.port)
    print(f"Test Bench API: http://{args.host}:{args.port}/api  (Ctrl+C 로 끝냄)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
