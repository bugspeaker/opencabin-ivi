"""1단계 기술 검증입니다. 앱을 만들기 전에 AAOS 기본 SystemUI로 신호와 화면이 이어지는지 먼저 확인했습니다.

자체 IVI 앱을 만들기 전에, AAOS 기본 SystemUI 의 하단 HVAC 바로
'차량 신호 → UI', 'UI 조작 → 차량 신호', '속도·기어 → 주행 상태' 가 실제로 이어지는지 확인한다.
SystemUI 표시 단위는 VHAL 의 HVAC_TEMPERATURE_DISPLAY_UNITS 를 따른다. 에뮬레이터 기본은 화씨(25.0 → 77°)이고,
7단계에서 태블릿과 같게 섭씨(25.0 → 25.0°)로 바꿔 쓰기도 해서, 기대 글자는 지금 표시 단위로 계산한다.
화씨에서도 정수로 딱 떨어지는 섭씨 값(25.0, 20.0)을 쓴다.
"""
import pytest
from appium.webdriver.common.appiumby import AppiumBy

from ivi.defects import DefectReproduced
from ivi.vehicle import Area, DrivingState, Prop, TempUnit
from ivi.waits import wait_until, wait_value

pytestmark = pytest.mark.aaos

SYSTEMUI = "com.android.systemui:id"
SIDES = {"driver": Area.DRIVER, "passenger": Area.PASSENGER}
HOME_BUTTON = (AppiumBy.ID, f"{SYSTEMUI}/home")
STEP_C = 0.5  # HVAC_TEMPERATURE_SET config 의 단계 (config[2] = 5 → 0.5°C)
KEYCODE_HOME = 3


@pytest.fixture(autouse=True)
def system_bar_shown(driver):
    """OpenCabin 이 앞에 있으면 아래 시스템 바가 숨겨져 있다 (앱이 자체 하단 줄을 쓰므로, SystemBars.kt).
    spike 는 기본 SystemUI 바를 대상으로 하므로 홈(런처)으로 나가 바를 다시 띄운다."""
    driver.press_keycode(KEYCODE_HOME)
    wait_until(lambda: driver.find_elements(*hvac("driver", "hvac_temperature_text")), what="하단 시스템 바 표시")


def hvac(side, name):
    return (AppiumBy.XPATH, f"//*[@resource-id='{SYSTEMUI}/{side}_hvac']//*[@resource-id='{SYSTEMUI}/{name}']")


def temp_label(driver, side="driver"):
    return driver.find_element(*hvac(side, "hvac_temperature_text")).text


def driver_temp_label(driver):
    return temp_label(driver, "driver")


def expected_label(vehicle, celsius):
    """SystemUI 가 보여 줄 글자: 섭씨면 '25.0°', 화씨면 '77°'."""
    if vehicle.get_property(Prop.HVAC_TEMPERATURE_DISPLAY_UNITS) == TempUnit.CELSIUS:
        return f"{celsius:.1f}°"
    return f"{round(celsius * 9 / 5 + 32)}°"


@pytest.mark.req("SPIKE-01")
@pytest.mark.spike
@pytest.mark.parametrize("celsius", [25.0, 20.0])
def test_hvac_signal_is_shown_on_ui(driver, vehicle, celsius):
    """운전석 설정 온도 property를 바꾸면 AAOS 기본 하단 공조 바의 숫자가 따라 바뀝니다."""
    label = expected_label(vehicle, celsius)
    vehicle.set_property(Prop.HVAC_TEMPERATURE_SET, celsius, Area.DRIVER)
    wait_value(lambda: driver_temp_label(driver), label, what="운전석 온도 표시")


@pytest.mark.req("SPIKE-01")
@pytest.mark.spike
@pytest.mark.parametrize("side, button, delta", [
    ("driver", "hvac_decrease_button", -STEP_C),
    ("passenger", "hvac_increase_button", +STEP_C),
])
def test_hvac_ui_tap_changes_signal(driver, vehicle, side, button, delta):
    """하단 공조 바의 온도 ▲ 또는 ▼를 한 번 누르면 property 값이 0.5°C 바뀝니다."""
    area = SIDES[side]
    start = expected_label(vehicle, 20.0)
    vehicle.set_property(Prop.HVAC_TEMPERATURE_SET, 20.0, area)
    wait_value(lambda: temp_label(driver, side), start, what=f"{side} 시작 온도 표시")

    driver.find_element(*hvac(side, button)).click()

    expected = 20.0 + delta
    wait_value(lambda: vehicle.get_property(Prop.HVAC_TEMPERATURE_SET, area), expected, what=f"{side} 설정 온도(°C)")
    wait_until(lambda: temp_label(driver, side) != start, what=f"{side} 온도 표시 변경")


@pytest.mark.req("SPIKE-01")
@pytest.mark.spike
# raises=DefectReproduced: 이 결함의 증상(두 버튼이 겹침)일 때만 xfailed 로 본다. 버튼을 못 찾거나 Appium 세션이 끊기는 등
# 다른 이유의 실패는 그대로 failed 가 되어 게이트를 막는다. raises 가 없으면 어떤 예외든 '알려진 결함'으로 삼켜진다
@pytest.mark.xfail(strict=True, raises=DefectReproduced,
                   reason="알려진 결함 3 (이슈 #21): 1024x768 에서 운전석 온도 ▲ 가 홈 버튼에 가려 탭이 홈으로 간다 (docs/phase1-spike.md)")
def test_driver_temp_up_is_not_covered_by_home(driver):
    """운전석 온도 ▲ 버튼이 홈 버튼에 가려지지 않는지 봅니다.
    1단계에서 찾은 SystemUI 결함이라 알려진 결함으로 남겨 두었습니다.
    """
    up = driver.find_element(*hvac("driver", "hvac_increase_button")).rect
    home = driver.find_element(*HOME_BUTTON).rect
    overlap_x = min(up["x"] + up["width"], home["x"] + home["width"]) - max(up["x"], home["x"])
    overlap_y = min(up["y"] + up["height"], home["y"] + home["height"]) - max(up["y"], home["y"])
    if overlap_x > 0 and overlap_y > 0:
        raise DefectReproduced(f"운전석 ▲ {up} 와 홈 {home} 이 {overlap_x}x{overlap_y}px 겹친다")


@pytest.mark.req("SPIKE-01")
@pytest.mark.spike
def test_speed_and_gear_change_driving_state(vehicle):
    """속도와 기어를 VHAL에 넣으면 CarService의 주행 상태가 바뀝니다.
    주행 중 화면 제한은 이 값을 보고 동작합니다.
    """
    wait_value(lambda: vehicle.driving_state(), DrivingState.PARKED, what="주행 상태 (정차)")

    vehicle.drive(50.0)  # km/h (VHAL 에는 13.9 m/s 로 들어간다)
    wait_value(lambda: vehicle.driving_state(), DrivingState.MOVING, what="주행 상태 (MOVING)")

    vehicle.park()
    wait_value(lambda: vehicle.driving_state(), DrivingState.PARKED, what="주행 상태 (다시 정차)")
