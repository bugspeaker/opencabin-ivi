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

    TABS = ("nav_home", "nav_navi", "nav_radio", "nav_media", "nav_phone", "nav_climate", "nav_settings")

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

    def navigation(self):
        self.tap("nav_navi")
        return self._screen(Navigation).wait_loaded()

    def radio(self):
        self.tap("nav_radio")
        return self._screen(Radio).wait_loaded()

    def phone(self):
        self.tap("nav_phone")
        return self._screen(Phone).wait_loaded()

    def settings(self):
        self.tap("nav_settings")
        return self._screen(Settings).wait_loaded()

    def voice(self):
        self.tap("voice_button")
        voice = self._screen(Voice)
        voice.find("voice_panel")
        return voice

    def speed(self):
        return self.text("speed_value"), self.text("speed_unit")

    def rear_camera(self):
        return self.visible("rear_camera")


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
        # 목록 한 줄(track_N)은 제목·가수를 담는 줄이라 자기 글자가 없다. 제목은 track_N_title 에서 읽는다 (5단계 디자인 개편)
        title = self.text(f"track_{index}_title")
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


def tags_matching(driver, pattern):
    """resource-id 가 정규식에 맞는 요소들 (예: 'nav_dest_[0-9]+_title')."""
    return driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().resourceIdMatches("{pattern}")')


class Navigation(Screen):
    def wait_loaded(self):
        wait_until(lambda: any(self.visible(t) for t in ("nav_search", "nav_dest_name", "nav_arrived")), what="내비 화면")
        return self

    def search_enabled(self):
        return self.enabled("nav_search")

    def search(self, text):
        field = self.find("nav_search")
        field.clear()
        field.send_keys(text)

    def results(self):
        return [element.text for element in tags_matching(self.driver, "nav_dest_[0-9]+_title")]

    def pick(self, index):
        self.tap(f"nav_dest_{index}")
        self.find("nav_start")

    def favorite(self, which):
        self.tap(f"nav_fav_{which}")
        self.find("nav_start")

    def start(self):
        self.tap("nav_start")
        self.find("nav_remaining")

    def destination(self):
        return self.text("nav_dest_name")

    def remaining_km(self):
        return float(self.text("nav_remaining").split()[0])

    def maneuver(self):
        return self.text("nav_maneuver")

    def stop(self):
        self.tap("nav_stop")


class Radio(Screen):
    def wait_loaded(self):
        self.find("radio_freq")
        return self

    def freq(self):
        return self.text("radio_freq")

    def station(self):
        return self.text("radio_station")

    def state(self):
        return self.text("radio_state")

    def power(self):
        self.tap("radio_power")

    def band(self, name):
        self.tap(f"radio_band_{name}")

    def step(self, action):
        """action: tune_up / tune_down / seek_up / seek_down"""
        before = self.freq()
        self.tap(f"radio_{action}")
        wait_until(lambda: self.freq() != before, what=f"라디오 {action}")
        return self.freq()

    def save_preset(self, slot):
        self.tap("radio_save")
        self.find("radio_save_hint")
        self.tap(f"radio_preset_{slot}")
        self.wait_visible("radio_save_hint", expected=False)

    def recall(self, slot):
        self.tap(f"radio_preset_{slot}")

    def preset_freq(self, slot):
        return self.text(f"radio_preset_{slot}_freq")


class Phone(Screen):
    def wait_loaded(self):
        # 통화 중에는 통화 화면이 위를 덮어 머리글(phone_device)이 안 보인다 → 둘 중 하나면 열린 것
        wait_until(lambda: self.visible("phone_device") or self.visible("phone_call_screen"), what="전화 화면")
        return self

    def tab(self, name):
        """recent / contacts / keypad"""
        self.tap(f"phone_tab_{name}")

    def contact_names(self):
        return [element.text for element in tags_matching(self.driver, "phone_contact_[0-9]+_name")]

    def call_contact(self, index):
        name = self.text(f"phone_contact_{index}_name")
        self.tap(f"phone_contact_{index}")
        self.find("phone_call_screen")
        return name

    def dial(self, digits):
        for digit in digits:
            self.tap(f"phone_key_{digit}")
        self.wait_text("phone_dial_number", digits)

    def call(self):
        self.tap("phone_call")
        self.find("phone_call_screen")

    def call_name(self):
        return self.text("phone_call_name")

    def call_seconds(self):
        minutes, seconds = self.text("phone_call_timer").split()[-1].split(":")
        return int(minutes) * 60 + int(seconds)

    def end(self):
        self.tap("phone_end")
        self.wait_visible("phone_call_screen", expected=False)

    def recent_name(self, index=0):
        return self.text(f"phone_recent_{index}_name")


class Settings(Screen):
    def wait_loaded(self):
        self.find("settings_volume_value")
        return self

    def value(self, name):
        return int(self.text(f"settings_{name}_value"))

    def up(self, name):
        before = self.value(name)
        self.tap(f"settings_{name}_up")
        wait_until(lambda: self.value(name) == before + 1, what=f"{name} +1")

    def down(self, name):
        before = self.value(name)
        self.tap(f"settings_{name}_down")
        wait_until(lambda: self.value(name) == before - 1, what=f"{name} -1")

    def checked(self, name):
        return self.find(f"settings_{name}").get_attribute("checked") == "true"

    def toggle(self, name):
        before = self.checked(name)
        self.tap(f"settings_{name}")
        wait_until(lambda: self.checked(name) != before, what=f"{name} 전환")

    def ambient(self, index):
        self.tap(f"settings_ambient_{index}")

    def ambient_name(self):
        return self.text("settings_ambient_value")

    def reset(self):
        self.tap("settings_reset")


class Voice(Screen):
    def say(self, index):
        """음성 명령 index 번 (인식된 문장을 누르는 것으로 대신한다)."""
        self.tap(f"voice_cmd_{index}")
        self.wait_visible("voice_panel", expected=False)  # 명령을 처리하면 패널이 닫힌다
        return self.text("voice_result").removeprefix("🎙").strip()  # 결과는 상태 줄 알림으로

    def close(self):
        """명령을 실행하면 패널은 저절로 닫힌다. 명령 없이 닫을 때만 쓴다."""
        if self.visible("voice_panel"):
            self.tap("voice_close")
        self.wait_visible("voice_panel", expected=False)


__all__ = ["IviApp", "Home", "Climate", "Media", "Video", "Navigation", "Radio", "Phone", "Settings", "Voice",
           "Seat", "by_tag", "parse_celsius", "tags_matching"]
