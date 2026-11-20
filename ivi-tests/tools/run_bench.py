"""Test Bench 실행기: 연결된 기기마다 같은 테스트를 **동시에** 돌리고 결과를 한 묶음(run id)으로 모은다.

    python tools/run_bench.py                                   # 연결된 모든 기기, 전체
    python tools/run_bench.py -m "smoke or sanity" --reruns 1   # Nightly 게이트
    python tools/run_bench.py --devices emulator-5554 -m smoke  # 한 대만
    python tools/run_bench.py --repeat 5 --reruns 1             # 안정성 측정 (flaky 통계용)

- 기기마다 pytest 프로세스를 따로 띄운다. 같은 Appium 서버를 쓰므로 UiAutomator2 systemPort 를 기기마다 다르게 준다.
- 출력은 reports/logs/<run>-<serial>.log, 결과는 reports/runs/<run>-<serial>.json (conftest 의 Recorder).
- 모든 기기의 게이트가 통과해야 종료 코드 0.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
BASE_SYSTEM_PORT = 8200


def connected_devices():
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("\tdevice")]


def run_once(devices, run_id, pytest_args):
    (REPORTS / "logs").mkdir(parents=True, exist_ok=True)
    procs = []
    started = time.monotonic()
    for index, serial in enumerate(devices):
        log = REPORTS / "logs" / f"{run_id}-{serial}.log"
        cmd = [sys.executable, "-m", "pytest", "--serial", serial, "--system-port", str(BASE_SYSTEM_PORT + index * 10),
               "--run-id", run_id, "-q", *pytest_args]
        handle = log.open("w", encoding="utf-8")
        procs.append((serial, subprocess.Popen(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT), handle, log))
        print(f"  ▶ {serial}  (systemPort {BASE_SYSTEM_PORT + index * 10})  로그: {log.relative_to(ROOT)}")

    results = []
    for serial, proc, handle, log in procs:
        code = proc.wait()
        handle.close()
        run_file = REPORTS / "runs" / f"{run_id}-{serial}.json"
        summary = json.loads(run_file.read_text(encoding="utf-8"))["summary"] if run_file.exists() else None
        results.append((serial, code, summary, log))
    return time.monotonic() - started, results


def print_results(run_id, wall, results):
    print(f"\n  run {run_id}  (병렬 실행 {wall:.0f}s)")
    serial_total = 0.0
    ok = True
    for serial, code, summary, log in results:
        if summary is None:
            ok = False
            print(f"  ✗ {serial}: 결과 없음 (종료 코드 {code}). 로그 확인: {log}")
            continue
        serial_total += summary["duration"]
        counts = ", ".join(f"{k} {v}" for k, v in sorted(summary["counts"].items()))
        mark = "✓" if summary["gate"] == "pass" else "✗"
        ok = ok and summary["gate"] == "pass"
        print(f"  {mark} {summary['kind']:5} {serial:18} {summary['duration']:6.0f}s  {counts}  relaunch {summary['relaunches']}"
              f"  session_restart {summary.get('session_restarts', 0)}")
    if len(results) > 1 and wall:
        print(f"  기기별로 차례로 돌렸다면 약 {serial_total:.0f}s → 병렬 {wall:.0f}s ({serial_total / wall:.1f}배)")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--devices", help="쉼표로 구분. 비우면 연결된 모든 기기")
    parser.add_argument("--repeat", type=int, default=1)
    args, pytest_args = parser.parse_known_args()

    devices = args.devices.split(",") if args.devices else connected_devices()
    if not devices:
        sys.exit("연결된 기기가 없습니다")
    print(f"기기 {len(devices)}대: {', '.join(devices)}   pytest 인자: {' '.join(pytest_args) or '(없음)'}")

    all_ok = True
    for round_no in range(1, args.repeat + 1):
        run_id = time.strftime("%Y%m%d-%H%M%S") + (f"-r{round_no}" if args.repeat > 1 else "")
        print(f"\n[{round_no}/{args.repeat}] {run_id}")
        wall, results = run_once(devices, run_id, pytest_args)
        all_ok = print_results(run_id, wall, results) and all_ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
