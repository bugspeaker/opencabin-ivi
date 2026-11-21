"""OpenCabin 앱을 AAOS 에뮬레이터에 priv-app(시스템 앱)으로 설치한다.

왜: 공조 제어 권한 CONTROL_CAR_CLIMATE 는 signature|privileged 라서 일반 설치로는 받을 수 없다.
     실제 차량의 IVI 앱도 OEM 이 시스템 이미지에 넣는 priv-app 이다.

전제: 에뮬레이터를 -writable-system 으로 띄웠다 (그래야 /system 을 다시 마운트해 쓸 수 있다).
     userdebug 이미지라 adb root 가 된다.

사용:  python privileged/install_priv_app.py [apk 경로] [--serial emulator-5554]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

PACKAGE = "dev.opencabin.ivi"
HERE = Path(__file__).parent
DEFAULT_APK = HERE.parent / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
PERMISSIONS_XML = HERE / f"privapp-permissions-{PACKAGE}.xml"
TARGET_DIR = "/system/priv-app/OpenCabinIvi"
TARGET_XML = f"/system/etc/permissions/{PERMISSIONS_XML.name}"


def run_adb(serial, *args, timeout=120):
    """adb 를 돌려 (종료 코드, 출력) 을 돌려준다."""
    done = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return done.returncode, (done.stdout + done.stderr).replace("\r", "").strip()


def adb(serial, *args, check=True, timeout=120):
    code, out = run_adb(serial, *args, timeout=timeout)
    if check and code != 0:
        sys.exit(f"adb {' '.join(args)} 실패:\n{out}")
    return out


def wait_boot(serial, timeout=240):
    adb(serial, "wait-for-device", timeout=timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if adb(serial, "shell", "getprop", "sys.boot_completed", check=False) == "1":
            return
        time.sleep(3)
    sys.exit("부팅이 끝나지 않았다")


def adb_root(serial, tries=3, pause=5):
    """adb root 뒤 부팅 완료와 root 셸까지 기다린다.

    재부팅 직후에는 부팅 완료 신호가 와도 adbd 가 아직 다시 붙는 중이라
    'adb: unable to connect for root: closed' 로 끊길 때가 있다 (2026-11-21 GitHub 호스트 러너, PR #33).
    그때는 잠깐 기다렸다가 다시 한다. tries 번 모두 실패하면 멈춘다.
    """
    out = ""
    for attempt in range(1, tries + 1):
        code, out = run_adb(serial, "root")
        if code == 0:
            wait_boot(serial)
            if adb(serial, "shell", "whoami", check=False) == "root":
                return
            out = f"root 셸이 아니다: {out}"
        if attempt < tries:
            print(f"   adb root 다시 시도 ({attempt}/{tries}): {out}")
            time.sleep(pause)
            adb(serial, "wait-for-device", timeout=120)
    sys.exit(f"adb root 실패 ({tries}번 시도):\n{out}")


def root_and_remount(serial):
    adb_root(serial)
    out = adb(serial, "remount", check=False)
    if "reboot" in out.lower():  # 처음 한 번은 overlayfs 를 켜려고 재부팅이 필요하다
        print("remount 를 위해 재부팅합니다")
        adb(serial, "reboot")
        wait_boot(serial)
        adb_root(serial)
        out = adb(serial, "remount", check=False)
    if "remount succeeded" not in out.lower():
        sys.exit(f"/system 을 쓰기 가능하게 만들지 못했다. 에뮬레이터를 -writable-system 으로 띄웠는지 확인:\n{out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", nargs="?", default=str(DEFAULT_APK))
    parser.add_argument("--serial", default="emulator-5554")
    args = parser.parse_args()
    apk = Path(args.apk)
    if not apk.exists():
        sys.exit(f"APK 가 없다: {apk} (먼저 ./gradlew assembleDebug)")

    s = args.serial
    # CI 로그에서 단계 안내가 오류보다 늦게 찍히지 않게 (파이프로 나갈 때는 출력이 모였다가 끝에 나온다)
    sys.stdout.reconfigure(line_buffering=True)
    print("1) root + /system 쓰기 가능하게")
    root_and_remount(s)

    print("2) 일반 설치본 제거 (있으면). 남아 있으면 시스템 앱 대신 이것이 쓰인다")
    adb(s, "uninstall", PACKAGE, check=False)

    print("3) priv-app 과 권한 허용 목록 복사")
    adb(s, "shell", "mkdir", "-p", TARGET_DIR)
    adb(s, "push", str(apk), f"{TARGET_DIR}/OpenCabinIvi.apk")
    adb(s, "push", str(PERMISSIONS_XML), TARGET_XML)
    adb(s, "shell", "chmod", "644", f"{TARGET_DIR}/OpenCabinIvi.apk", TARGET_XML)

    print("4) 재부팅 (시스템 앱은 부팅 때 스캔된다)")
    adb(s, "reboot")
    wait_boot(s)
    adb_root(s)

    print("5) 확인")
    dump = adb(s, "shell", "dumpsys", "package", PACKAGE)
    privileged = "PRIVILEGED" in dump
    climate = "android.car.permission.CONTROL_CAR_CLIMATE: granted=true" in dump
    user = adb(s, "shell", "am", "get-current-user")
    for permission in ("CAR_SPEED", "CAR_ENERGY"):  # dangerous 권한: 권한 창이 뜨지 않게 미리 준다
        adb(s, "shell", "pm", "grant", "--user", user, PACKAGE, f"android.car.permission.{permission}", check=False)
    print(f"   priv-app: {privileged}, CONTROL_CAR_CLIMATE: {climate}, 운전자 사용자: {user}")
    if not (privileged and climate):
        sys.exit("priv-app 설치 또는 권한 부여가 확인되지 않았다")
    print("완료. 이후 코드 변경은 `adb install -r` 로 덮어써도 같은 서명이면 priv-app 권한이 유지된다.")


if __name__ == "__main__":
    main()
