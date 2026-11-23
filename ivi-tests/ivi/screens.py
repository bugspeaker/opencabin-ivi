"""화면 객체 (Page Object). 태그 이름은 ivi-app 의 ui/*.kt (testTag), VideoActivity.kt 와 맞춘다.

Compose testTag 는 testTagsAsResourceId 로 resource-id 가 되는데, 패키지 접두사가 없다 (`nav_climate`).
UiAutomator2 의 By.ID 는 `dev.opencabin.ivi:id/` 를 붙여 찾아서 못 찾으므로 UiSelector().resourceId() 를 쓴다.
"""
from appium.webdriver.common.appiumby import AppiumBy

from ivi.vehicle import Seat
from ivi.waits import polling, wait_until

TIMEOUT = 10.0

# 누를 요소가 이보다 좁게(가로나 세로) 보이면 거의 가려진 것으로 본다. 그 가운데를 누르면 가린 요소가 대신 눌린다
# (2026-11-23 갤럭시 폴드 가로: 후보 카드가 높이 10px 만 보였고, 가운데를 누르자 바로 아래 추천 칩이 눌렸다).
MIN_VISIBLE_DP = 16
SCROLL_TRIES = 3          # 가려진 요소를 보이게 하려고 목록을 넘겨 보는 횟수
SCROLL_PERCENT = 0.3      # 한 번에 목록 높이(폭)의 30% 만큼 넘긴다
SCROLLABLE = AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().scrollable(true)"

_density = {}  # Appium 세션 → 1dp 의 px 수


class HiddenElement(AssertionError):
    """누를 요소가 거의 가려져 있고, 목록을 넘겨도 보이지 않는다.
    AssertionError 라서 대기(wait_until) 안에서 누를 때는 '아직 아님'으로 보고 다시 본다."""


def by_tag(tag):
    return AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().resourceId("{tag}")'


def parse_celsius(text):
    """'25.0°C' → 25.0, '25.0°' (아래 바) → 25.0, '--' → None"""
    text = text.strip()
    return None if text in ("", "--") else float(text.removesuffix("°C").removesuffix("°"))


class Screen:
    """tapper: 요소를 누르는 방법. None 이면 Appium click. 화웨이처럼 UiAutomator 입력이 느린 기기는
    Device.tapper() 가 요소 중심 좌표를 adb input tap 으로 누르는 함수를 준다 (docs/phase3-framework.md)."""

    def __init__(self, driver, tapper=None):
        self.driver = driver
        self.tapper = tapper

    def _screen(self, cls):
        return cls(self.driver, self.tapper)

    def find(self, tag, timeout=TIMEOUT):
        if polling():
            # 바깥의 wait_until 이 이미 다시 보고 있다. 여기서 또 기다리면 제한 시간이 겹친다 (10초 + 10초).
            # 한 번만 찾고, 없으면 NoSuchElementException 을 바깥 대기에 넘긴다
            return self.driver.find_element(*by_tag(tag))
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
        element = self._tappable(tag)
        if self.tapper is None:
            element.click()
        else:
            self.tapper(element)

    def _tappable(self, tag):
        """누를 요소. UiAutomator 가 주는 위치는 '보이는 부분'이라, 거의 가려진 요소도 찾기는 된다.
        보이는 부분이 MIN_VISIBLE_DP 보다 좁으면 그 요소를 감싼 스크롤 목록을 잘린 쪽으로 넘겨 본다.
        그래도 좁으면 누르지 않고 HiddenElement 로 실패한다 (다른 요소가 눌려 엉뚱한 단계에서 실패하지 않게)."""
        element = self.find(tag)
        least = MIN_VISIBLE_DP * self._px_per_dp()
        for attempt in range(SCROLL_TRIES + 1):
            rect = element.rect
            if min(rect["width"], rect["height"]) >= least or self._cut_by_screen(rect):
                return element
            if attempt == SCROLL_TRIES or not self._scroll_toward(rect):
                break
            element = self.find(tag)
        raise HiddenElement(
            f"'{tag}' 이(가) 거의 가려져 있어 누르지 않는다: 보이는 부분 {rect['width']}x{rect['height']}px "
            f"(최소 {MIN_VISIBLE_DP}dp = {least:.0f}px). 화면 배치가 넘쳤거나 다른 요소에 덮였는지 확인")

    def _cut_by_screen(self, rect):
        """UiAutomator 가 아는 화면 가장자리에서 잘렸는가. 이때는 다른 요소에 덮인 것이 아니라서, 보이는 부분 가운데를 눌러도
        그 요소가 눌린다. 갤럭시 폴드 가로는 앱이 카메라 컷아웃(104px)만큼 오른쪽으로 밀렸는데 UiAutomator 는 위치를
        표시 영역 폭(2048px)에서 자른다. 그래서 맨 오른쪽 버튼(아래 바 조수석 온도 ›)은 화면에 다 보여도 폭 33px 로 나온다."""
        screen = self.driver.get_window_size()
        return (rect["x"] <= 0 or rect["y"] <= 0
                or rect["x"] + rect["width"] >= screen["width"]
                or rect["y"] + rect["height"] >= screen["height"])

    def _px_per_dp(self):
        session = getattr(self.driver, "session_id", None)
        if session not in _density:
            _density[session] = self.driver.get_display_density() / 160
        return _density[session]

    def _scroll_toward(self, rect):
        """rect 를 감싼 가장 안쪽 스크롤 목록을, rect 가 잘린 쪽으로 조금 넘긴다. 넘길 목록이 없으면 False."""
        def inside(outer):
            return (outer["x"] <= rect["x"] and outer["y"] <= rect["y"]
                    and rect["x"] + rect["width"] <= outer["x"] + outer["width"]
                    and rect["y"] + rect["height"] <= outer["y"] + outer["height"])

        containers = [(c, c.rect) for c in self.driver.find_elements(*SCROLLABLE)]
        containers = [(c, r) for c, r in containers if inside(r)]
        if not containers:
            return False
        container, box = min(containers, key=lambda pair: pair[1]["width"] * pair[1]["height"])
        edge = 4 * self._px_per_dp()
        if rect["y"] + rect["height"] >= box["y"] + box["height"] - edge:
            direction = "down"    # 목록 아래 끝에 걸림 → 아래 내용을 올린다
        elif rect["y"] <= box["y"] + edge:
            direction = "up"
        elif rect["x"] + rect["width"] >= box["x"] + box["width"] - edge:
            direction = "right"
        elif rect["x"] <= box["x"] + edge:
            direction = "left"
        else:
            return False          # 목록 가장자리가 아니라 다른 요소에 덮였다. 넘겨도 소용없다
        self.driver.execute_script("mobile: scrollGesture",
                                   {"elementId": container.id, "direction": direction, "percent": SCROLL_PERCENT})
        return True


class IviApp(Screen):
    """메인 화면의 공통 영역 (아래 바, 상단 바, 주행 정보).

    7단계(3영역 화면 개편)부터 아래 바에는 차량·공조·미디어·전화·내비·AI·앱 목록만 고정이다.
    라디오·설정은 앱 목록에서 연다 → 테스트는 그대로 두고, 여는 길만 여기서 바꿨다.
    """

    BAR = ("nav_vehicle", "nav_climate", "nav_media", "nav_phone", "nav_home", "nav_assistant", "nav_apps")

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
        # 내비게이션 = 홈 (분할 화면이면 오른쪽에 오디오 카드가 같이 보인다)
        self.tap("nav_home")
        return self._screen(Navigation).wait_loaded()

    def open_from_apps(self, app_id):
        """앱 목록(아래 바 ⊞)에서 앱을 연다."""
        self.tap("nav_apps")
        self.tap(f"app_{app_id}")

    def radio(self):
        self.open_from_apps("radio")
        return self._screen(Radio).wait_loaded()

    def phone(self):
        self.tap("nav_phone")
        return self._screen(Phone).wait_loaded()

    def settings(self):
        self.open_from_apps("settings")
        return self._screen(Settings).wait_loaded()

    def assistant(self):
        self.tap("nav_assistant")
        return self._screen(Assistant).wait_loaded()

    def vehicle_controls(self):
        self.tap("nav_vehicle")
        return self._screen(QuickControl).wait_loaded()

    def apps(self):
        self.tap("nav_apps")
        self.find("app_navigation")
        return self

    def bar(self):
        """아래 바의 좌석 온도 (어느 화면에서나 보인다)."""
        return self._screen(BottomBar)

    def cluster(self):
        """왼쪽 주행 정보 (어느 화면에서나 보인다)."""
        return self._screen(Cluster)

    def notifications(self):
        """알림 패널을 연다."""
        self.tap("top_notifications")
        self.find("notification_panel")
        return self._screen(Notifications)

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
        """홈에서 보이는 좌석 온도. 7단계부터 온도 요약은 아래 바에 있다 ('25.0°')."""
        return parse_celsius(self.text(f"bar_{seat.tag}_temp"))

    def split(self):
        """분할 화면(내비 + 오디오)인가."""
        return self.visible("home_audio")

    def toggle_split(self):
        before = self.split()
        self.tap("split_toggle")
        wait_until(lambda: self.split() != before, what="분할 화면 전환")


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

    # ---- 8단계: 차량 신호에 연결된 공조 부가 기능 ----
    def checked(self, name):
        """토글 상태. name: ac / max_ac / auto / sync / defrost_front / defrost_rear (색이 아니라 접근성 checked 를 읽는다)"""
        return self.find(f"climate_{name}").get_attribute("checked") == "true"

    def wait_checked(self, name, expected, timeout=TIMEOUT):
        wait_until(lambda: self.checked(name) == expected, timeout=timeout, what=f"공조 {name} {'켜짐' if expected else '꺼짐'}")

    def toggle(self, name):
        self.tap(f"climate_{name}")

    def fan(self):
        return int(self.text("climate_fan_level"))

    def fan_up(self):
        self.tap("climate_fan_up")

    def fan_down(self):
        self.tap("climate_fan_down")

    def seat_heat(self, seat):
        """'열선 2단' → 2, '열선 꺼짐' → 0"""
        text = self.text(f"seat_heat_{seat.tag}_value")
        return 0 if "꺼짐" in text else int(text.split()[1].removesuffix("단"))

    def tap_seat_heat(self, seat):
        self.tap(f"seat_heat_{seat.tag}")

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

    def elapsed_seconds(self):
        minutes, seconds = self.elapsed().split(":")
        return int(minutes) * 60 + int(seconds)

    def has_clips(self):
        """기기에 블랙박스 영상이 올라가 있어 실제 재생 중인가 (없으면 가짜 재생 화면, tools/push_drive_videos.py)."""
        return self.visible("video_index")

    def clip_index(self):
        """'1 / 2' 형식."""
        return self.text("video_index")

    def next_clip(self):
        self.tap("video_next")

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

    def category(self, which):
        """분류 바로가기(charger / parking)를 누른다. 목록이 그 분류만 가까운 순으로 바뀐다. 다시 누르면 풀린다."""
        self.tap(f"nav_cat_{which}")

    def cancel(self):
        """미리 보기에서 '취소' (안내를 시작하지 않고 찾기 화면으로)."""
        self.tap("nav_cancel")

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

    KEY_TAGS = {"*": "phone_key_star", "#": "phone_key_hash"}

    def press(self, keys):
        """키패드 버튼을 차례로 누른다 (번호 칸을 확인하지 않는다). '*', '#' 도 된다."""
        for key in keys:
            self.tap(self.KEY_TAGS.get(key, f"phone_key_{key}"))

    def dial(self, digits):
        self.press(digits)
        self.wait_text("phone_dial_number", digits)

    def dialed(self):
        return self.text("phone_dial_number")

    def backspace(self):
        self.tap("phone_backspace")

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
        return self.text("voice_result").strip()  # 결과는 상단 바에 잠깐 보인다

    def close(self):
        """명령을 실행하면 패널은 저절로 닫힌다. 명령 없이 닫을 때만 쓴다."""
        if self.visible("voice_panel"):
            self.tap("voice_close")
        self.wait_visible("voice_panel", expected=False)


class BottomBar(Screen):
    """아래 바: ‹ 온도 ›. 온도는 실제 차량 신호(HVAC_TEMPERATURE_SET)를 바꾼다."""

    def temperature(self, seat):
        return parse_celsius(self.text(f"bar_{seat.tag}_temp"))

    def wait_temperature(self, seat, celsius, timeout=TIMEOUT):
        wait_until(lambda: self.temperature(seat) == celsius, timeout=timeout, what=f"아래 바 {seat.tag} {celsius}°")

    def increase(self, seat):
        self.tap(f"bar_{seat.tag}_temp_up")

    def decrease(self, seat):
        self.tap(f"bar_{seat.tag}_temp_down")

    def seat_heat(self, seat):
        """아래 바 열선 단계 (0 = 꺼짐). 단계 숫자는 켜져 있을 때만 보인다."""
        return int(self.text(f"bar_seat_heat_{seat.tag}_level") or 0)

    def tap_seat_heat(self, seat):
        self.tap(f"bar_seat_heat_{seat.tag}")


class Cluster(Screen):
    """왼쪽 주행 정보: 속도·기어·운전자 보조 표시·경로·유틸리티 위젯."""

    def adas(self):
        return self.text("adas_state")

    def range_km(self):
        """주행 가능 거리 ('320 km' → 320). 속도 단위가 mph 면 mi 로 보인다."""
        return int(self.text("range_value").split()[0])

    def range_unit(self):
        return self.text("range_value").split()[1]

    def battery_percent(self):
        return int(self.text("battery_value").removesuffix("%"))

    def outside_temperature(self):
        return parse_celsius(self.text("outside_temp"))

    def low_range_warning(self):
        return self.visible("range_low")

    def route(self):
        """안내 중이면 '회사까지 8.7 km', 아니면 None."""
        return self.text("cluster_route") if self.visible("cluster_route") else None

    def trip_km(self):
        return float(self.text("trip_distance"))

    def widget_title(self):
        return self.text("utility_title")

    def next_widget(self):
        before = self.widget_title()
        self.tap("utility_widget")
        wait_until(lambda: self.widget_title() != before, what="유틸리티 위젯 넘김")
        return self.widget_title()


class Assistant(Screen):
    """AI 어시스턴트 대화 화면. 음성 대신 추천 명령(칩)이나 글자 입력으로 말한다."""

    def wait_loaded(self):
        self.find("assistant_reply")
        return self

    def zone(self, seat):
        """말하는 좌석을 고른다 (좌석별 음성 인식 대신)."""
        self.tap(f"assistant_zone_{seat.tag}")
        wait_until(lambda: self.text("assistant_listening").startswith("운전석" if seat == Seat.DRIVER else "조수석"),
                   what=f"{seat.tag} 에서 듣는 중")

    def reply(self):
        return self.text("assistant_reply")

    def _said(self, action):
        before = self.reply()
        action()
        wait_until(lambda: self.reply() != before, what="비서 대답")
        return self.reply()

    def chip(self, index):
        """추천 명령 index 번을 말한다. 대답을 돌려준다."""
        return self._said(lambda: self.tap(f"assistant_chip_{index}"))

    def say(self, text):
        """글자로 말한다 (정차 중에만 된다)."""
        def type_and_send():
            field = self.find("assistant_input")
            field.clear()
            field.send_keys(text)
            self.tap("assistant_send")
        return self._said(type_and_send)

    def typing_enabled(self):
        return self.enabled("assistant_input")

    def choose(self, index):
        """목적지 후보 카드 index 번을 고른다 (고르면 내비 화면으로 간다)."""
        self.tap(f"assistant_candidate_{index}")


class QuickControl(Screen):
    """차량 빠른 제어 (도어·사이드 미러·트렁크 등. 화면 상태이며 VHAL 에 연결하지 않았다)."""

    def wait_loaded(self):
        self.find("qc_door_lock")
        return self

    def value(self, name):
        return self.text(f"qc_{name}_value")

    def toggle(self, name):
        before = self.value(name)
        self.tap(f"qc_{name}")
        wait_until(lambda: self.value(name) != before, what=f"{name} 전환")
        return self.value(name)

    def can_toggle(self, name):
        return self.enabled(f"qc_{name}")


class Notifications(Screen):
    def titles(self):
        return [element.text for element in tags_matching(self.driver, "notification_[0-9]+_title")]

    def clear(self):
        """'모두 지우기'. 목록이 비고 빈 상태 문구가 보일 때까지 기다린다."""
        self.tap("notification_clear")
        self.find("notification_empty")

    def close(self):
        self.tap("top_notifications")
        self.wait_visible("notification_panel", expected=False)


__all__ = ["IviApp", "Home", "Climate", "Media", "Video", "Navigation", "Radio", "Phone", "Settings", "Voice",
           "BottomBar", "Cluster", "Assistant", "QuickControl", "Notifications",
           "Seat", "by_tag", "parse_celsius", "tags_matching"]
