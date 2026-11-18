"""README 첫 화면용 데모 GIF: 화면 → 신호, 신호 → 화면을 터미널 출력과 나란히 보여 준다 (AAOS 에뮬레이터).

    python tools/record_demo.py                      # docs/images/demo-ui-vhal.gif
    python tools/record_demo.py --serial emulator-5554 --out ../docs/images/demo-ui-vhal.gif

테스트가 쓰는 화면 객체와 차량 어댑터를 그대로 쓴다. 장면은 넷이다.
  1. VHAL 의 운전석 설정 온도를 읽는다 (22.0)
  2. 화면의 + 를 누른다 → VHAL 값이 22.5 가 된다 (화면 → 신호)
  3. VHAL 에 25.0 을 넣는다 → 화면이 25.0 이 된다 (신호 → 화면)
  4. 원래 값으로 되돌린다
화면은 테스트의 끝 화면처럼 Appium 으로 찍는다. 영상(블랙박스) 화면은 넣지 않는다 (번호판).
"""
import argparse
import io
import os
import sys
import time
from pathlib import Path

from appium import webdriver
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ivi.device import Device  # noqa: E402
from ivi.screens import IviApp  # noqa: E402
from ivi.vehicle import Prop, Seat  # noqa: E402
from ivi.waits import wait_until  # noqa: E402

WIDTH = 800
SCREEN_H = 600            # 1024x768 → 800x600
TERM_H = 176
FONT_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
BG = (15, 16, 17)
INK = (247, 248, 248)
MUTED = (208, 214, 224)
SUBTLE = (138, 143, 152)
ACCENT = (130, 143, 255)
GREEN = (61, 214, 140)


def font(name, size):
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


MONO = font("consola.ttf", 17)
KO = font("malgun.ttf", 16)
KO_BOLD = font("malgunbd.ttf", 17)


def screencap(driver):
    # adb screencap 은 AAOS 에뮬레이터에 화면이 여러 개(클러스터)라 경고 글이 앞에 붙는다 → 테스트와 같이 Appium 으로 찍는다
    return Image.open(io.BytesIO(driver.get_screenshot_as_png())).convert("RGB")


def frame(shot, title, lines, boxes=()):
    """위: 기기 화면(강조 상자), 아래: 터미널. lines = [(글자, 색, 고정폭인가)]"""
    canvas = Image.new("RGB", (WIDTH, SCREEN_H + TERM_H), BG)
    scale = WIDTH / shot.width
    canvas.paste(shot.resize((WIDTH, round(shot.height * scale)), Image.LANCZOS), (0, 0))
    draw = ImageDraw.Draw(canvas)
    for x, y, w, h in boxes:
        draw.rounded_rectangle([x * scale - 4, y * scale - 4, (x + w) * scale + 4, (y + h) * scale + 4], radius=10, outline=ACCENT, width=3)
    top = SCREEN_H
    draw.rectangle([0, top, WIDTH, top + TERM_H], fill=BG)
    draw.line([0, top, WIDTH, top], fill=(52, 52, 58), width=1)
    draw.text((20, top + 12), title, font=KO_BOLD, fill=ACCENT)
    y = top + 44
    for text, color, mono in lines[-5:]:
        draw.text((20, y), text, font=MONO if mono else KO, fill=color)
        y += 25
    return canvas


def vhal_read(device, area):
    out = device.adb.shell("cmd", "car_service", "get-property-value", hex(Prop.HVAC_TEMPERATURE_SET), hex(area))
    start = out.find("floatValues")
    return out[start:out.find("]", start) + 1] if start >= 0 else out.strip()[:60]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--appium-url", default=os.environ.get("APPIUM_URL", "http://127.0.0.1:4723"))
    parser.add_argument("--out", default=str(ROOT.parent / "docs" / "images" / "demo-ui-vhal.gif"))
    args = parser.parse_args()

    device = Device.connect(args.serial)
    if not device.automotive:
        sys.exit("AAOS 에뮬레이터에서만 의미가 있습니다 (VHAL 값을 보여 준다)")
    driver = webdriver.Remote(args.appium_url, options=device.appium_options())
    driver.implicitly_wait(0)
    frames = []  # (이미지, 보여 줄 ms)
    try:
        app = IviApp(driver, tapper=device.tapper())
        device.launch(reset=True)
        app.find("source_badge")
        device.reset_app_state()
        device.vehicle.prepare()
        climate = app.climate()
        climate.wait_temperature(Seat.DRIVER, 22.0)
        value_box = climate.find("driver_temp_value").rect
        up_box = climate.find("driver_temp_up").rect
        boxes = [(r["x"], r["y"], r["width"], r["height"]) for r in (value_box, up_box)]
        get_cmd = "$ adb shell cmd car_service get-property-value 0x15600503 0x1"
        area = Seat.DRIVER.area

        # 1. 지금 값
        lines = [(get_cmd, MUTED, True), (f"  {vhal_read(device, area)}", GREEN, True)]
        frames.append((frame(screencap(driver), "화면 → 신호: + 를 누르면 VHAL 값이 바뀌는지", lines, boxes), 1800))

        # 2. + 누르기 → VHAL 22.5
        climate.increase(Seat.DRIVER)
        lines.append(("# 화면의 운전석 + 를 누름 (Appium)", SUBTLE, False))
        frames.append((frame(screencap(driver), "화면 → 신호: + 를 누르면 VHAL 값이 바뀌는지", lines, boxes[1:]), 900))
        wait_until(lambda: device.vehicle.temperature(Seat.DRIVER) == 22.5, what="VHAL 22.5")
        lines += [(get_cmd, MUTED, True), (f"  {vhal_read(device, area)}   <- 22.0 + 0.5", GREEN, True)]
        frames.append((frame(screencap(driver), "화면 → 신호: + 를 누르면 VHAL 값이 바뀌는지", lines, boxes[:1]), 2600))

        # 3. VHAL 에 25.0 → 화면 25.0
        set_cmd = "$ adb shell dumpsys <VHAL> --set 0x15600503 -f 25.0 -a 1"
        lines = [(set_cmd, MUTED, True), ("# <VHAL> = android.hardware.automotive.vehicle.IVehicle/default. 차량(ECU) 쪽 변화처럼 바로 넣음", SUBTLE, False)]
        before = screencap(driver)
        frames.append((frame(before, "신호 → 화면: VHAL 값을 바꾸면 화면이 따라오는지", lines, boxes[:1]), 1400))
        device.vehicle.inject_temperature(Seat.DRIVER, 25.0)
        climate.wait_temperature(Seat.DRIVER, 25.0)
        lines += [(get_cmd, MUTED, True), (f"  {vhal_read(device, area)}", GREEN, True),
                  ("# 화면의 운전석 온도와 아래 바가 25.0°C 로 바뀜", SUBTLE, False)]
        frames.append((frame(screencap(driver), "신호 → 화면: VHAL 값을 바꾸면 화면이 따라오는지", lines, boxes[:1]), 3200))
    finally:
        device.vehicle.prepare()  # 22.0 과 기준 값으로
        driver.quit()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    images = [img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for img, _ in frames]
    images[0].save(out, save_all=True, append_images=images[1:], duration=[ms for _, ms in frames], loop=0, optimize=True)
    print(f"{out}  {out.stat().st_size / 1024:.0f} KB, 장면 {len(frames)}개, {sum(ms for _, ms in frames) / 1000:.1f}초")


if __name__ == "__main__":
    main()
