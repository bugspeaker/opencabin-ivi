"""화면 객체 (Page Object). 태그 이름은 ivi-app 의 ui/IviScreens.kt, VideoActivity.kt 와 맞춘다.

Compose testTag 는 testTagsAsResourceId 로 resource-id 가 되는데, 패키지 접두사가 없다 (`nav_climate`).
UiAutomator2 의 By.ID 는 `dev.opencabin.ivi:id/` 를 붙여 찾아서 못 찾으므로 UiSelector().resourceId() 를 쓴다.
"""
from appium.webdriver.common.appiumby import AppiumBy

from ivi.vehicle import Seat
from ivi.waits import wait_until

TIMEOUT = 10.0


def by_tag(tag):
    return AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().resourceId("{tag}")'


def parse_celsius(text):
    """'25.0°C' → 25.0, '--' → None"""
    text = text.strip()
    return None if text in ("", "--") else float(text.removesuffix("°C"))


class Screen:
    """tapper: 요소를 누르는 방법. None 이면 Appium click. 화웨이처럼 UiAutomator 입력이 느린 기기는
    Device.tapper() 가 요소 중심 좌표를 adb input tap 으로 누르는 함수를 준다 (docs/phase3-framework.md)."""

    def __init__(self, driver, tapper=None):
        self.driver = driver
        self.tapper = tapper

    def _screen(self, cls):
        return cls(self.driver, self.tapper)

    def find(self, tag, timeout=TIMEOUT):
        return wait_until(lambda: self.driver.find_element(*by_tag(tag)), timeout=timeout, what=f"화면 요소 '{tag}'")

    def visible(self, tag):
        """지금 화면에 있는가 (기다리지 않는다)."""
        return len(self.driver.find_elements(*by_tag(tag))) > 0

    def wait_visible(self, tag, expected=True, timeout=TIMEOUT):
        wait_until(lambda: self.visible(tag) == expected, timeout=timeout,
                   what=f"'{tag}' {'표시' if expected else '사라짐'}")

    def text(self, tag):
        return self.find(tag).text

    def wait_text(self, tag, expected, timeout=TIMEOUT):
        wait_until(lambda: self.text(tag) == expected, timeout=timeout, what=f"'{tag}' = {expected!r}")

    def enabled(self, tag):
        return self.find(tag).get_attribute("enabled") == "true"

    def wait_enabled(self, tag, expected, timeout=TIMEOUT):
        wait_until(lambda: self.enabled(tag) == expected, timeout=timeout,
                   what=f"'{tag}' {'활성' if expected else '비활성'}")

    def tap(self, tag):
        element = self.find(tag)
        if self.tapper is None:
            element.click()
        else:
            self.tapper(element)


class IviApp(Screen):
    """메인 화면의 공통 영역 (탭, 상태 배지)."""

    TABS = ("nav_home", "nav_climate", "nav_media")

    def source_badge(self):
        return self.text("source_badge")

    def restriction_banner(self):
        return self.visible("restriction_banner")

    def home(self):
        self.tap("nav_home")
        return self._screen(Home).wait_loaded()

    def climate(self):
        self.tap("nav_climate")
        return self._screen(Climate).wait_loaded()

    def media(self):
        self.tap("nav_media")
        return self._screen(Media).wait_loaded()

    def video(self):
        """영상 화면 객체 (화면을 열지는 않는다. 직접 띄운 VideoActivity 를 볼 때 쓴다)."""
        return self._screen(Video)


class Home(Screen):
    def wait_loaded(self):
        self.find("speed_value")
        return self

    def speed(self):
        return self.text("speed_value")

    def gear(self):
        return self.text("gear_value")

    def summary_temperature(self, seat):
        """'운전석 25.0°C' → 25.0"""
        return parse_celsius(self.text(f"home_{seat.tag}_temp").split(" ", 1)[1])


class Climate(Screen):
    def wait_loaded(self):
        wait_until(lambda: self.visible("driver_temp_value") or self.visible("hvac_unavailable"), what="공조 화면")
        return self

    def unavailable(self):
        return self.visible("hvac_unavailable")

    def temperature(self, seat):
        return parse_celsius(self.text(f"{seat.tag}_temp_value"))

    def wait_temperature(self, seat, celsius, timeout=TIMEOUT):
        wait_until(lambda: self.temperature(seat) == celsius, timeout=timeout, what=f"{seat.tag} 온도 표시 {celsius}°C")

    def increase(self, seat):
        self.tap(f"{seat.tag}_temp_up")

    def decrease(self, seat):
        self.tap(f"{seat.tag}_temp_down")

    def can_increase(self, seat):
        return self.enabled(f"{seat.tag}_temp_up")

    def can_decrease(self, seat):
        return self.enabled(f"{seat.tag}_temp_down")


class Media(Screen):
    def wait_loaded(self):
        self.find("now_playing_title")
        return self

    def select_track(self, index):
        title = self.text(f"track_{index}")
        self.tap(f"track_{index}")
        return title

    def now_playing(self):
        return self.text("now_playing_title")

    def playback_state(self):
        return self.text("playback_state")

    def toggle_play(self):
        self.tap("play_pause")

    def video_button_enabled(self):
        return self.enabled("open_video")

    def restricted_notice(self):
        return self.visible("video_restricted_notice")

    def open_video(self):
        self.tap("open_video")
        return self._screen(Video)


class Video(Screen):
    def playing(self):
        return self.visible("video_player")

    def blocked(self):
        return self.visible("video_blocked")

    def elapsed(self):
        return self.text("video_elapsed")

    def close(self):
        self.tap("video_close")


__all__ = ["IviApp", "Home", "Climate", "Media", "Video", "Seat", "by_tag", "parse_celsius"]
