"""Test Bench 실행기: 연결된 기기마다 같은 테스트를 **동시에** 돌리고 결과를 한 묶음(run id)으로 모은다.

    python tools/run_bench.py                                   # 연결된 모든 기기, 전체
    python tools/run_bench.py -m "smoke or sanity" --reruns 1   # Nightly 게이트
    python tools/run_bench.py --devices emulator-5554 -m smoke  # 한 대만
    python tools/run_bench.py --repeat 5 --reruns 1             # 안정성 측정 (flaky 통계용)

- 기기마다 pytest 프로세스를 따로 띄운다. 같은 Appium 서버를 쓰므로 UiAutomator2 systemPort 를 기기마다 다르게 준다.
- 출력은 reports/logs/<run>-<serial>.log, 결과는 reports/runs/<run>-<serial>.json (conftest 의 Recorder).
- 모든 기기에서 pytest 가 종료 코드 0 으로 끝나고, 결과 파일의 게이트가 pass 여야 종료 코드 0.
  결과 파일만 믿지 않는다: 중간에 멈춘 실행(종료 코드 2)도 그때까지 돈 테스트가 모두 통과면 결과 파일은 깨끗해 보인다.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ivi.results import EXIT_CODES  # noqa: E402

REPORTS = ROOT / "reports"
BASE_SYSTEM_PORT = 8200


def judge(code, summary, run_id=None, serial=None):
    """기기 하나의 실행이 통과인가: (통과 여부, 실패 이유 목록). 종료 코드와 결과 파일을 둘 다 보고,
    결과 파일이 이번 실행·이 기기의 것인지도 본다 (run_id, serial 을 주면)."""
    reasons = []
    failed_tests = summary is not None and summary.get("gate") != "pass"
    if summary is None:
        reasons.append("결과 파일 없음 (pytest 가 끝나기 전에 죽었거나 시간 제한에 걸림)")
    else:
        for key, expected in (("run_id", run_id), ("serial", serial)):
            if expected is not None and summary.get(key) != expected:
                reasons.append(f"결과 파일의 {key} {summary.get(key)!r} 가 이번 실행의 {expected!r} 와 다르다")
    if summary is not None and failed_tests:
        reasons += summary.get("problems") or ["결과 파일의 게이트 실패 (failed·error)"]
    # 종료 코드 1 은 '실패한 테스트 있음'이라 결과 파일의 실패와 겹친다. 그 밖의 0 이 아닌 코드는 따로 알린다
    if code != 0 and not (code == 1 and failed_tests) and not any("종료 코드" in reason for reason in reasons):
        reasons.append(f"pytest 종료 코드 {code} ({EXIT_CODES.get(code, '알 수 없음')})")
    return not reasons, reasons


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
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # 로그 파일과 같은 utf-8 로 쓰게 (Python 3.12 Windows 기본은 cp949)
        procs.append((serial, subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT), handle, log))
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
        passed, reasons = judge(code, summary, run_id, serial)
        ok = ok and passed
        if summary is None:
            print(f"  ✗ {serial}: {'; '.join(reasons)}. 로그 확인: {log}")
            continue
        serial_total += summary["duration"]
        counts = ", ".join(f"{k} {v}" for k, v in sorted(summary["counts"].items()))
        mark = "✓" if passed else "✗"
        print(f"  {mark} {summary['kind']:5} {serial:18} {summary['duration']:6.0f}s  {counts}  relaunch {summary['relaunches']}"
              f"  session_restart {summary.get('session_restarts', 0)}")
        for reason in reasons:
            print(f"      ✗ {reason}")
    if len(results) > 1 and wall:
        print(f"  기기별로 차례로 돌렸다면 약 {serial_total:.0f}s → 병렬 {wall:.0f}s ({serial_total / wall:.1f}배)")
    return ok


def positive_int(text):
    """--repeat 는 1 이상. 0 이면 아무것도 돌리지 않고 종료 코드 0 으로 끝나 '통과'처럼 보였다 (2026-11-20 검토)."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"1 이상이어야 한다: {text}")
    return value


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--devices", help="쉼표로 구분. 비우면 연결된 모든 기기")
    parser.add_argument("--repeat", type=positive_int, default=1)
    return parser.parse_known_args(argv)


def main():
    args, pytest_args = parse_args()
    # 결과 파일에 '어떤 명령으로 돌렸는지' 남기려고 pytest 에 넘긴다 (conftest 의 launcher)
    os.environ["IVI_LAUNCHER"] = " ".join(["run_bench.py", *sys.argv[1:]])

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
