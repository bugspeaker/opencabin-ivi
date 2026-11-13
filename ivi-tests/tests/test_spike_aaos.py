"""1단계 기술 검증 (spike).

자체 IVI 앱을 만들기 전에, AAOS 기본 SystemUI 의 하단 HVAC 바로
'차량 신호 → UI', 'UI 조작 → 차량 신호', '속도·기어 → 주행 상태' 가 실제로 이어지는지 확인한다.
화면 표시는 화씨(°F)라서 정수로 딱 떨어지는 섭씨 값(25.0 → 77°, 20.0 → 68°)을 쓴다.
"""
import pytest
from appium.webdriver.common.appiumby import AppiumBy

from ivi.vehicle import Area, DrivingState, Prop
from ivi.waits import wait_until

pytestmark = pytest.mark.aaos

SYSTEMUI = "com.android.systemui:id"
SIDES = {"driver": Area.DRIVER, "passenger": Area.PASSENGER}
HOME_BUTTON = (AppiumBy.ID, f"{SYSTEMUI}/home")
STEP_C = 0.5  # HVAC_TEMPERATURE_SET config 의 단계 (config[2] = 5 → 0.5°C)


def hvac(side, name):
    return (AppiumBy.XPATH, f"//*[@resource-id='{SYSTEMUI}/{side}_hvac']//*[@resource-id='{SYSTEMUI}/{name}']")


def temp_label(driver, side="driver"):
    return driver.find_element(*hvac(side, "hvac_temperature_text")).text


def driver_temp_label(driver):
    return temp_label(driver, "driver")


@pytest.mark.spike
@pytest.mark.parametrize("celsius, label", [(25.0, "77°"), (20.0, "68°")])
def test_hvac_signal_is_shown_on_ui(driver, vehicle, celsius, label):
    """하위 → 상위: 운전석 설정 온도를 property 로 바꾸면 하단 HVAC 바 표시가 따라 바뀐다."""
    vehicle.set_property(Prop.HVAC_TEMPERATURE_SET, celsius, Area.DRIVER)
    wait_until(lambda: driver_temp_label(driver) == label, what=f"운전석 온도 표시 {label}")


@pytest.mark.spike
@pytest.mark.parametrize("side, button, delta", [
    ("driver", "hvac_decrease_button", -STEP_C),
    ("passenger", "hvac_increase_button", +STEP_C),
])
def test_hvac_ui_tap_changes_signal(driver, vehicle, side, button, delta):
    """상위 → 하위: 화면의 온도 ▲/▼ 를 한 번 누르면 실제 property 값이 한 단계(0.5°C) 바뀐다."""
    area = SIDES[side]
    vehicle.set_property(Prop.HVAC_TEMPERATURE_SET, 20.0, area)
    wait_until(lambda: temp_label(driver, side) == "68°", what=f"{side} 시작 온도 표시 68°")

    driver.find_element(*hvac(side, button)).click()

    expected = 20.0 + delta
    wait_until(lambda: vehicle.get_property(Prop.HVAC_TEMPERATURE_SET, area) == expected, what=f"{side} 설정 온도 {expected}°C")
    wait_until(lambda: temp_label(driver, side) != "68°", what=f"{side} 온도 표시 변경")


@pytest.mark.spike
@pytest.mark.xfail(strict=True, reason="알려진 결함: 1024x768 에서 운전석 온도 ▲ 가 홈 버튼에 가려 탭이 홈으로 간다 (docs/phase1-spike.md)")
def test_driver_temp_up_is_not_covered_by_home(driver):
    """버튼 영역이 겹치지 않는지 본다. 겹치면 사용자가 ▲ 를 눌러도 온도가 안 바뀐다 (1단계에서 발견)."""
    up = driver.find_element(*hvac("driver", "hvac_increase_button")).rect
    home = driver.find_element(*HOME_BUTTON).rect
    overlap_x = min(up["x"] + up["width"], home["x"] + home["width"]) - max(up["x"], home["x"])
    overlap_y = min(up["y"] + up["height"], home["y"] + home["height"]) - max(up["y"], home["y"])
    assert overlap_x <= 0 or overlap_y <= 0, f"운전석 ▲ {up} 와 홈 {home} 이 {overlap_x}x{overlap_y}px 겹친다"


@pytest.mark.spike
def test_speed_and_gear_change_driving_state(vehicle):
    """속도·기어를 VHAL 에 넣으면 CarService 의 주행 상태가 바뀐다 (주행 중 UX 제한의 입력)."""
    assert wait_until(lambda: vehicle.driving_state() == DrivingState.PARKED, what="정차 상태")

    vehicle.drive(50.0)  # km/h (VHAL 에는 13.9 m/s 로 들어간다)
    wait_until(lambda: vehicle.driving_state() == DrivingState.MOVING, what="주행 상태(MOVING)")

    vehicle.park()
    wait_until(lambda: vehicle.driving_state() == DrivingState.PARKED, what="다시 정차 상태")
