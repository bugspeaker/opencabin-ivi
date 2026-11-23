"""누르기 전 확인: 거의 가려진 요소는 목록을 넘겨 보이게 하고, 그래도 안 보이면 누르지 않는다. 기기 없이 돈다.

2026-11-23 갤럭시 폴드 가로(앱 높이 513dp)에서 후보 카드가 높이 10px 만 보였는데, 그 가운데를 누르자 아래 추천 칩이 눌렸다.
테스트는 '판교역 안내'를 기다리다 엉뚱한 단계에서 실패했다.
"""
import pytest

from ivi.screens import SCROLL_TRIES, HiddenElement, Screen

DPI = 420  # 폴드: 1dp = 2.625px → 최소 16dp = 42px


class FakeElement:
    def __init__(self, x, y, width, height, element_id="el"):
        self.rect = {"x": x, "y": y, "width": width, "height": height}
        self.id = element_id
        self.clicks = 0

    def click(self):
        self.clicks += 1


class FakeDriver:
    """요소 하나와 스크롤 목록들. scrollGesture 를 부르면 on_scroll 로 요소 위치를 바꾼다."""

    session_id = "unit"

    def __init__(self, element, containers=(), on_scroll=None):
        self.element = element
        self.containers = list(containers)
        self.on_scroll = on_scroll
        self.scrolls = []

    def get_display_density(self):
        return DPI

    def get_window_size(self):
        return {"width": 2048, "height": 1410}  # 폴드 가로에서 UiAutomator 가 아는 표시 영역

    def find_element(self, *_):
        return self.element

    def find_elements(self, *_):
        return self.containers

    def execute_script(self, name, args):
        assert name == "mobile: scrollGesture"
        self.scrolls.append(args)
        if self.on_scroll:
            self.on_scroll(self.element, args)


def test_visible_element_is_clicked_without_scrolling():
    card = FakeElement(100, 600, 900, 95)
    driver = FakeDriver(card)
    Screen(driver).tap("assistant_candidate_0")
    assert card.clicks == 1 and driver.scrolls == []


def test_card_cut_at_list_bottom_is_scrolled_into_view_then_clicked():
    """폴드에서 본 그대로: 대화 목록(위 360 ~ 아래 800) 아래 끝에 높이 10px 만 걸친 카드."""
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 790, 900, 10)

    def scroll(element, args):
        element.rect = {**element.rect, "y": 700, "height": 95}

    driver = FakeDriver(card, [chat], on_scroll=scroll)
    Screen(driver).tap("assistant_candidate_2")
    assert driver.scrolls == [{"elementId": "chat", "direction": "down", "percent": 0.3}]
    assert card.clicks == 1


def test_innermost_list_is_scrolled():
    page = FakeElement(0, 0, 2000, 1400, element_id="page")
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 790, 900, 10)
    driver = FakeDriver(card, [page, chat], on_scroll=lambda el, _: el.rect.update(y=700, height=95))
    Screen(driver).tap("assistant_candidate_2")
    assert [s["elementId"] for s in driver.scrolls] == ["chat"]


def test_card_cut_at_list_top_scrolls_up():
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 360, 900, 12)
    driver = FakeDriver(card, [chat], on_scroll=lambda el, _: el.rect.update(height=95))
    Screen(driver).tap("assistant_candidate_0")
    assert driver.scrolls[0]["direction"] == "up"


def test_hidden_element_without_list_fails_clearly_and_is_not_clicked():
    """넘칠 목록이 없는 배치 넘침(아래 바의 열선 버튼이 공조 타일 밑에 깔린 경우 등)은 누르지 않고 이유를 남긴다."""
    button = FakeElement(540, 1200, 8, 130)
    driver = FakeDriver(button)
    with pytest.raises(HiddenElement, match=r"'bar_seat_heat_driver' 이\(가\) 거의 가려져 있어 누르지 않는다: 보이는 부분 8x130px \(최소 16dp = 42px\)"):
        Screen(driver).tap("bar_seat_heat_driver")
    assert button.clicks == 0


def test_covered_in_the_middle_of_a_list_is_not_scrolled():
    """목록 가장자리가 아닌 곳에서 작게 보이면 다른 요소에 덮인 것이다. 넘겨도 소용없으니 바로 실패한다."""
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 500, 900, 10)
    driver = FakeDriver(card, [chat])
    with pytest.raises(HiddenElement):
        Screen(driver).tap("assistant_candidate_1")
    assert driver.scrolls == [] and card.clicks == 0


def test_gives_up_after_limited_scrolls():
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 790, 900, 10)
    driver = FakeDriver(card, [chat], on_scroll=lambda *_: None)  # 넘겨도 그대로
    with pytest.raises(HiddenElement):
        Screen(driver).tap("assistant_candidate_2")
    assert len(driver.scrolls) == SCROLL_TRIES and card.clicks == 0


def test_adb_tapper_gets_the_element_after_the_check():
    """화웨이처럼 adb 로 누르는 기기도 같은 확인을 거친다."""
    chat = FakeElement(80, 360, 1300, 440, element_id="chat")
    card = FakeElement(100, 790, 900, 10)
    driver = FakeDriver(card, [chat], on_scroll=lambda el, _: el.rect.update(y=700, height=95))
    tapped = []
    Screen(driver, tapper=lambda el: tapped.append(dict(el.rect))).tap("assistant_candidate_2")
    assert tapped == [{"x": 100, "y": 700, "width": 900, "height": 95}]
    assert card.clicks == 0


def test_hidden_element_is_retried_inside_a_wait():
    """대기 안에서 누를 때는 HiddenElement 를 '아직 아님'으로 보고 다시 본다 (화면이 바뀌는 중일 수 있다)."""
    from ivi.waits import wait_until

    button = FakeElement(540, 1200, 8, 130)
    driver = FakeDriver(button)
    calls = []

    def tap_until_ok():
        calls.append(1)
        if len(calls) == 3:
            button.rect = {**button.rect, "width": 130}
        Screen(driver).tap("bar_seat_heat_driver")
        return True

    assert wait_until(tap_until_ok, timeout=2, interval=0.01)
    assert len(calls) == 3 and button.clicks == 1


def test_button_cut_by_the_screen_edge_is_still_clicked():
    """폴드 가로: 아래 바 조수석 온도 › 는 화면에 다 보이지만 UiAutomator 가 표시 영역 폭(2048px)에서 잘라 폭 33px 로 준다.
    다른 요소에 덮인 것이 아니므로 누른다 (가운데를 눌러도 그 버튼이다)."""
    button = FakeElement(2015, 1226, 33, 147)
    driver = FakeDriver(button)
    Screen(driver).tap("bar_passenger_temp_up")
    assert button.clicks == 1 and driver.scrolls == []
