"""AAOS 에뮬레이터의 공조 값을 태블릿(Mock)과 같게 맞춘다: 운전석·조수석 22.0°C, 표시 단위 섭씨.

    python tools/emulator_defaults.py --persist     # 한 번: 재부팅해도 22.0°C · 섭씨로 시작하게 (권장)
    python tools/emulator_defaults.py [--serial emulator-5554] [--celsius 22.0] [--fahrenheit]   # 지금만 바꾸기

에뮬레이터 VHAL 은 켤 때마다 /vendor/etc/automotive/vhalconfig/DefaultProperties.json 의 기본값
(17.0°C, 화씨 표시 → 하단 시스템 바에 '63°')으로 돌아간다.

--persist: VHAL 의 초기값 덮어쓰기 기능을 쓴다 (ivi-app/privileged/vhaloverride/opencabin.json).
  - 덮어쓰기 파일 → /vendor/etc/automotive/vhaloverride/ (에뮬레이터를 -writable-system 으로 띄워야 쓸 수 있다)
  - 켜는 스위치 persist.vendor.vhal_init_value_override=true 는 /vendor/build.prop 에 넣는다.
    `setprop` 으로 넣으면 안 된다: persist 속성은 /data 가 올라온 뒤에 읽히는데 VHAL 은 그보다 먼저 떠서
    스위치가 꺼진 것으로 본다 (2026-11-16 확인: logcat 에 'loading properties from .../vhaloverride/' 가 없었다).
  - 재부팅한 뒤 실제 값을 읽어 확인한다.

테스트는 이 도구에 기대지 않는다 (app 픽스처가 테스트마다 22.0°C 로 맞추고, spike 테스트는 표시 단위를 읽어 기대 글자를 계산한다).
"""
import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

VHAL = "android.hardware.automotive.vehicle.IVehicle/default"
HVAC_TEMPERATURE_SET = 0x15600503
HVAC_TEMPERATURE_DISPLAY_UNITS = 0x1140050E
CELSIUS, FAHRENHEIT = 0x30, 0x31
SEATS = {"운전석": 0x1, "조수석": 0x4}

PRIVILEGED = Path(__file__).resolve().parents[2] / "ivi-app" / "privileged"
OVERRIDE_JSON = PRIVILEGED / "vhaloverride" / "opencabin.json"
OVERRIDE_DIR = "/vendor/etc/automotive/vhaloverride"
OVERRIDE_SWITCH = "persist.vendor.vhal_init_value_override=true"


def adb(serial, *args):
    done = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (done.stdout + done.stderr).replace("\r", "").strip()


def vhal_set(serial, prop, kind, value, area=0):
    out = adb(serial, "shell", "dumpsys", VHAL, "--set", hex(prop), kind, str(value), "-a", str(area))
    if "failed" in out.lower():
        raise SystemExit(f"VHAL --set {hex(prop)} 실패: {out[:200]} (adb root 가 필요하다)")


def vhal_get(serial, prop, area=0):
    out = adb(serial, "shell", "dumpsys", VHAL, "--get", hex(prop), "-a", str(area))
    found = re.search(r"(?:floatValues|int32Values): \[([^\]]+)\]", out)
    return float(found.group(1)) if found else None


def persist(serial):
    """덮어쓰기 파일과 스위치를 vendor 에 넣고 재부팅해 확인한다. remount·부팅 대기는 priv-app 설치 스크립트 것을 쓴다."""
    spec = importlib.util.spec_from_file_location("install_priv_app", PRIVILEGED / "install_priv_app.py")
    priv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(priv)

    print("1) root + vendor 쓰기 가능하게")
    priv.root_and_remount(serial)
    print(f"2) {OVERRIDE_JSON.name} → {OVERRIDE_DIR}/")
    adb(serial, "shell", "mkdir", "-p", OVERRIDE_DIR)
    out = adb(serial, "push", str(OVERRIDE_JSON), f"{OVERRIDE_DIR}/{OVERRIDE_JSON.name}")
    if "pushed" not in out:
        raise SystemExit(f"덮어쓰기 파일을 올리지 못했다: {out}")
    adb(serial, "shell", f"chmod 644 {OVERRIDE_DIR}/*.json && restorecon -R {OVERRIDE_DIR}")
    print("3) /vendor/build.prop 에 스위치")
    adb(serial, "shell", f"grep -q '^{OVERRIDE_SWITCH}' /vendor/build.prop || "
                         f"printf '\\n# OpenCabin: VHAL 초기값 덮어쓰기 ({OVERRIDE_DIR}/)\\n{OVERRIDE_SWITCH}\\n' >> /vendor/build.prop")
    print("4) 재부팅 후 확인")
    adb(serial, "reboot")
    priv.wait_boot(serial)
    adb(serial, "root")
    priv.wait_boot(serial)
    temps = {name: vhal_get(serial, HVAC_TEMPERATURE_SET, area) for name, area in SEATS.items()}
    unit = vhal_get(serial, HVAC_TEMPERATURE_DISPLAY_UNITS)
    print(f"  {', '.join(f'{n} {t}°C' for n, t in temps.items())}, 표시 단위 {'섭씨' if unit == CELSIUS else unit}")
    if unit != CELSIUS or any(t != 22.0 for t in temps.values()):
        raise SystemExit("재부팅 뒤 값이 덮어쓰기와 다르다. logcat 에서 'FakeVehicleHardware: loading properties from' 을 확인한다")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--persist", action="store_true", help="재부팅해도 유지되게 vendor 에 덮어쓰기를 넣는다 (재부팅함)")
    parser.add_argument("--celsius", type=float, default=22.0)
    parser.add_argument("--fahrenheit", action="store_true", help="표시 단위를 화씨로 (에뮬레이터 기본)")
    args = parser.parse_args()

    if args.persist:
        persist(args.serial)
        return

    adb(args.serial, "root")
    for name, area in SEATS.items():
        vhal_set(args.serial, HVAC_TEMPERATURE_SET, "-f", args.celsius, area)
        print(f"  {name} {args.celsius:.1f}°C")
    vhal_set(args.serial, HVAC_TEMPERATURE_DISPLAY_UNITS, "-i", FAHRENHEIT if args.fahrenheit else CELSIUS)
    print(f"  표시 단위 {'화씨' if args.fahrenheit else '섭씨'}")


if __name__ == "__main__":
    sys.exit(main())
