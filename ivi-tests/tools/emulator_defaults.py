"""AAOS 에뮬레이터의 공조 값을 태블릿(Mock)과 같게 맞춘다: 운전석·조수석 22.0°C, 표시 단위 섭씨.

    python tools/emulator_defaults.py [--serial emulator-5554] [--celsius 22.0] [--fahrenheit]

에뮬레이터 VHAL 은 켤 때마다 기본값(화씨 표시, 좌석마다 다른 온도)으로 돌아간다. 데모·스크린샷 전에 한 번 돌린다.
테스트는 이 도구에 기대지 않는다 (app 픽스처가 테스트마다 22.0°C 로 맞추고, spike 테스트는 표시 단위를 읽어 기대 글자를 계산한다).
"""
import argparse
import subprocess
import sys

VHAL = "android.hardware.automotive.vehicle.IVehicle/default"
HVAC_TEMPERATURE_SET = 0x15600503
HVAC_TEMPERATURE_DISPLAY_UNITS = 0x1140050E
CELSIUS, FAHRENHEIT = 0x30, 0x31
SEATS = {"운전석": 0x1, "조수석": 0x4}


def vhal_set(serial, prop, kind, value, area=0):
    out = subprocess.run(["adb", "-s", serial, "shell", "dumpsys", VHAL, "--set", hex(prop), kind, str(value), "-a", str(area)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    if "failed" in out.lower():
        raise SystemExit(f"VHAL --set {hex(prop)} 실패: {out.strip()[:200]} (adb root 가 필요하다)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--celsius", type=float, default=22.0)
    parser.add_argument("--fahrenheit", action="store_true", help="표시 단위를 화씨로 (에뮬레이터 기본)")
    args = parser.parse_args()

    subprocess.run(["adb", "-s", args.serial, "root"], capture_output=True)
    for name, area in SEATS.items():
        vhal_set(args.serial, HVAC_TEMPERATURE_SET, "-f", args.celsius, area)
        print(f"  {name} {args.celsius:.1f}°C")
    vhal_set(args.serial, HVAC_TEMPERATURE_DISPLAY_UNITS, "-i", FAHRENHEIT if args.fahrenheit else CELSIUS)
    print(f"  표시 단위 {'화씨' if args.fahrenheit else '섭씨'}")


if __name__ == "__main__":
    sys.exit(main())
