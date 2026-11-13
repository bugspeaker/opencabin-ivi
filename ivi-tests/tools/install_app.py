"""테스트 대상 앱을 기기에 올린다. 이미 같은 APK 가 있으면 건너뛴다.

    python tools/install_app.py ../ivi-app/app/build/outputs/apk/debug/app-debug.apk [--devices a,b]

왜 '같으면 건너뛰기' 인가
  - 화웨이는 adb 설치마다 기기 화면 승인이 필요하다. 무인 실행(CI)에서 매번 설치하면 멈춘다.
  - AAOS 에뮬레이터는 priv-app 으로 넣어 두었다 (공조 권한). 서명이 같으면 `adb install -r` 로 덮어써도 권한이 유지된다.
    처음 한 번은 ivi-app/privileged/install_priv_app.py 로 넣는다. 서명이 다르면(다른 PC 의 debug 키) 설치가 거부된다.
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

PACKAGE = "dev.opencabin.ivi"


def adb(serial, *args, timeout=60):
    done = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return done.returncode, (done.stdout + done.stderr).replace("\r", "").strip()


def installed_hash(serial):
    code, out = adb(serial, "shell", "pm", "path", PACKAGE)
    if code != 0 or not out.startswith("package:"):
        return None
    path = out.splitlines()[0].removeprefix("package:")
    code, out = adb(serial, "shell", "sha256sum", path)
    return out.split()[0] if code == 0 and out else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk")
    parser.add_argument("--devices")
    parser.add_argument("--timeout", type=int, default=180, help="기기 승인 대기 포함 설치 제한 시간(초)")
    args = parser.parse_args()

    apk = Path(args.apk)
    if not apk.exists():
        sys.exit(f"APK 가 없다: {apk}")
    local = hashlib.sha256(apk.read_bytes()).hexdigest()
    if args.devices:
        devices = args.devices.split(",")
    else:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        devices = [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("\tdevice")]

    failed = False
    for serial in devices:
        if installed_hash(serial) == local:
            print(f"  = {serial}: 같은 APK 가 이미 있음 (건너뜀)")
            continue
        brand = adb(serial, "shell", "getprop", "ro.product.brand")[1].upper()
        if brand in ("HUAWEI", "HONOR"):
            print(f"  ! {serial}: 화웨이 기기 — 기기 화면에서 설치 승인을 눌러야 합니다 ({args.timeout}초 대기)")
        code, out = adb(serial, "install", "-r", str(apk), timeout=args.timeout)
        ok = code == 0 and "Success" in out
        failed |= not ok
        print(f"  {'✓' if ok else '✗'} {serial}: {out.splitlines()[-1] if out else code}")
        if not ok and "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in out:
            print("    서명이 다릅니다. 같은 서명 키로 빌드했는지 확인 (AAOS priv-app 은 install_priv_app.py 로 다시 넣기)")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
