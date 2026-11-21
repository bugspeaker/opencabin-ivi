# 요구사항

OpenCabin IVI 앱과 Test Bench가 지켜야 할 것을 ID를 붙여 적었습니다. 테스트 코드는 `@pytest.mark.req("ID")`로 이 ID를 가리키고, `ivi-tests/tools/trace_report.py`가 둘을 이어 [요구사항 추적표](traceability.md)를 만듭니다.

출처 열의 '기능'은 이 앱에서 정한 동작이고, '운전자 주의 분산'은 AAOS의 주행 중 UX 제한을, '법규'는 해당 기준을 가져온 것입니다. '모의 환경'은 실제 장비 대신 PC 안에서 흉내 낸 환경에서 확인한다는 뜻입니다.

| ID | 요구사항 | 출처 |
|---|---|---|
| SYS-01 | 앱은 기기에 맞는 차량 데이터(AAOS는 CarService, 그 밖의 기기는 Mock)에 연결하고, 권한이 없는 신호는 앱이 멈추지 않고 '값 없음'으로 보여 준다. | 기능 |
| UI-01 | 화면 틀(아래 바, 분할 화면, 위젯, 알림 센터, 앱 목록, 이전 실행 앱)이 어느 화면에서든 동작한다. | 기능 |
| DRIVE-01 | 속도와 기어 신호를 주행 정보에 바로 보여 준다. | 기능 |
| DRIVE-02 | 주행 중에는 영상을 볼 수 없고, 차를 세우면 멈춘 자리부터 이어서 볼 수 있다. 음악은 주행 중에도 쓸 수 있다. | 운전자 주의 분산 |
| DRIVE-03 | 주행 중에는 글자 입력(내비 검색, 키패드, 어시스턴트 입력)과 일부 차량 제어(사이드 미러 접기, 트렁크)를 막는다. | 운전자 주의 분산 |
| HVAC-01 | 운전석과 조수석 온도는 화면과 차량 신호가 같은 값을 가진다. 한쪽이 바뀌면 다른 쪽이 따라온다. | 기능 |
| HVAC-02 | 온도는 16.0~28.0°C 범위에서 0.5°C 단위로 바뀌고, 끝에 닿으면 그 방향 버튼이 꺼진다. 차량 쪽에서 범위 밖 값이나 0.5°C 단위가 아닌 값이 와도 앱은 멈추지 않고 그 값을 보여 주며, 범위 밖으로 더 가는 버튼은 꺼진다. 버튼을 누르면 범위 안의 0.5°C 단위 값으로 맞춰 차량에 쓴다. | 기능 |
| HVAC-03 | A/C, AUTO, 풍량은 모든 좌석 area에 함께 적용된다. 풍량을 직접 바꾸면 AUTO가 풀린다. | 기능 |
| HVAC-04 | 최대 냉방(FULL)을 켜면 최저 온도와 최대 풍량이 되고, 끄면 켜기 전 값으로 돌아간다. 다른 공조 값을 직접 바꾸면 최대 냉방이 풀린다. | 기능 |
| HVAC-05 | 김서림 제거와 좌석 열선은 누른 유리, 그 좌석에만 적용되고, 화면 여러 곳에 같은 값으로 보인다. | 기능 |
| HVAC-06 | SYNC를 켜면 조수석 온도가 운전석을 따르고, 조수석을 직접 바꾸면 SYNC가 풀린다. | 기능 |
| BODY-01 | 도어 버튼은 모든 문을 함께 잠그고 풀며, 차량 쪽 문 상태를 화면에 보여 준다. | 기능 |
| ENERGY-01 | 주행 가능 거리, 배터리, 외기 온도를 화면 단위(km 또는 마일, %, °C)로 보여 준다. | 기능 |
| ENERGY-02 | 주행 가능 거리가 30 km 이하면 경고와 충전소 안내를 띄우고 알림 센터에 남긴다. 충전해서 거리가 늘면 경고를 거둔다. | 기능 |
| CAM-01 | 기어가 R이 되면 어느 화면에서든 후방 카메라를 띄우고, R에서 벗어나면 보던 화면으로 돌아간다. | 기능 |
| CAM-02 | 후방 카메라 화면은 기어를 R로 바꾼 뒤 2.0초 안에 보여야 한다. FMVSS 111의 2초 기준을 빌렸고, 앱의 카메라 화면 요소가 뜰 때까지를 잰다(adb 주입과 Appium 조회 시간 포함). 실제 카메라 영상이나 실차에서 잰 값은 아니다. | 법규 기준을 빌림 (FMVSS 111) |
| NAV-01 | 목적지를 찾아 안내를 시작하고, 남은 거리는 차량 속도 신호를 따라 줄며, 도착하거나 끝내면 안내를 거둔다. | 기능 |
| MEDIA-01 | 음악, 라디오, 통화는 한 번에 하나만 소리를 낸다. 통화가 끝나면 듣던 것이 다시 나온다. | 기능 |
| MEDIA-02 | 음악과 영상 재생, 라디오 조정과 프리셋, 전화 걸기가 동작한다. | 기능 |
| VOICE-01 | 음성 명령과 AI 어시스턴트는 말한 사람의 좌석에 맞춰 차량 기능과 앱 기능을 실행한다. | 기능 |
| SET-01 | 설정과 라디오 프리셋은 앱을 다시 켜도 남고, 초기화하면 기본값으로 돌아간다. 속도 단위는 차량 정보 표시에 반영된다. | 기능 |
| NET-01 | 차량 네트워크(CAN)로 들어온 주행, 배터리, 도어 신호가 VHAL을 거쳐 화면에 보인다. | 통합 (모의 환경) |
| NET-02 | 화면에서 바꾼 공조 값이 CAN 프레임으로 나간다. | 통합 (모의 환경) |
| BENCH-01 | Test Bench API로 기기, 차량 신호, 실행 결과를 조회하고 신호를 넣을 수 있다. 잘못된 값은 거절하고 차량에 넣지 않는다. | 운영 |
| BENCH-02 | 전원을 껐다 켜도 기기가 정해진 시간 안에 부팅되고, 앱과 공조 기본값이 돌아온다. | 운영 (모의 환경) |
| SPIKE-01 | AAOS 기본 SystemUI의 공조 바가 VHAL 신호와 이어지고, 속도와 기어가 주행 상태를 바꾼다. | 기술 검증 (1단계) |

## 복합 요구사항: 조건마다 확인하는 곳

요구사항 하나에 조건이 여럿이면, 테스트 이름이 붙어 있다는 것만으로 모든 조건을 확인했다고 할 수 없습니다. 추적표의 '요구사항 ID 연결 누락 0'은 연결이 빠지지 않았다는 뜻이고, 조건별 검증이 충분하다거나 표준을 지켰다는 뜻은 아닙니다. 그래서 조건을 나누고, 조건마다 어느 테스트의 어떤 확인(assert 또는 대기)이 그 조건을 보는지 적었습니다. 확인하지 않는 조건은 '확인하지 않음'으로 남겼습니다.

`trace_report.py`가 이 표의 테스트가 실제로 있고 그 요구사항 ID를 달고 있는지 검사합니다. 테스트 이름이 바뀌거나 요구사항 표시가 빠지면 CI의 unit job이 실패합니다.

| 조건 | 내용 | 테스트 | 그 조건을 보는 확인 |
|---|---|---|---|
| SYS-01.1 | 기기에 맞는 차량 데이터에 연결한다 (AAOS는 CarService, 태블릿은 Mock) | `test_app_starts_with_vehicle_source_for_device` | `assert app.source_badge() == device.vehicle.badge`, 연결 안 됨·오류 표시가 없음 |
| SYS-01.2 | 연결한 차량 값이 시작 화면에 맞게 보인다 | `test_parked_on_start` | `wait_text("speed_value", "0")`, `assert home.gear() == "P"` |
| SYS-01.3 | 권한이 있으면 공조를 제어할 수 있다 | `test_hvac_is_controllable` | `assert not climate.unavailable()` 뒤 화면 + 한 번이 차량 22.5°C로 |
| SYS-01.4 | 권한이 없는 신호는 앱이 멈추지 않고 '값 없음'으로 보여 준다 | 확인하지 않음 | 앱 코드(`CarVehicleDataSource`가 `SecurityException`을 받아 '값 없음')에는 있지만, 권한을 뺀 상태로 돌리는 E2E나 앱 단위 테스트가 없다 |
| HVAC-02.1 | 버튼 한 번에 0.5°C 바뀐다 | `test_button_changes_signal_by_one_step` | 차량 값 `wait_value(car.temperature(seat), 22.5)`(▼는 21.5)와 화면 `wait_temperature`를 따로 본다. 좌석 2 × 방향 2 |
| HVAC-02.2 | 끝값(16.0, 28.0°C)에서는 그 방향 버튼이 꺼지고 반대쪽은 눌린다 | `test_buttons_disabled_at_limits` | `wait_enabled("<좌석>_temp_down", False)`와 `assert climate.can_increase(seat)`. 28.0°C는 반대 |
| HVAC-02.3 | 버튼으로 끝값에 닿으면 그 버튼이 꺼지고, 꺼진 버튼을 눌러도 범위를 넘지 않는다 | `test_step_reaches_limit_and_disables` | 16.5→16.0°C `wait_value`, `wait_enabled(False)`, 꺼진 버튼을 누른 뒤 1.5초 동안 `stays(car.temperature(seat) == 16.0)`. 28.0°C도 같다 |
| HVAC-02.4 | 차량 쪽 범위 밖 값(15.5, 28.5°C)을 화면에 보여 주고, 범위 밖으로 더 가는 버튼은 꺼진다 | `test_out_of_range_signal_is_shown_safely` | `wait_temperature(seat, 15.5)`, `wait_enabled("driver_temp_down", False)`. 15.5°C를 그대로 보여 주는 것은 AAOS에서만 확인한다(태블릿 Mock은 16.0°C로 자른다) |
| HVAC-02.5 | 범위 밖 값에서 버튼을 누르면 범위 안의 값을 차량에 쓴다 | `test_out_of_range_signal_is_shown_safely` | ▲ 뒤 `wait_value(car.temperature(seat), 16.0)`(AAOS), 16.5(태블릿) |
| HVAC-02.6 | 0.5°C 단위가 아닌 값(22.3°C)에서 버튼을 누르면 0.5°C 단위로 맞춰 쓴다 | `test_off_grid_signal_steps_back_to_grid` | `wait_value(car.temperature(seat), 22.5)`(▲), 22.0(▼). 이 확인에서 앱 결함(22.8°C를 씀)을 찾았다 |
| HVAC-02.7 | 이상한 값이 와도 앱이 멈추지 않는다 | `test_out_of_range_signal_is_shown_safely`, `test_off_grid_signal_steps_back_to_grid` | 값이 화면에 보이고 그 뒤 버튼이 동작하는지 본다. 테스트 도중 이 앱의 크래시(`FATAL EXCEPTION`, `Fatal signal`)나 ANR이 logcat에 남으면 화면 판정이 통과해도 그 테스트를 실패로 한다(모든 E2E 공통, `ivi/crashes.py`) |
| HVAC-04.1 | FULL을 켜면 전 좌석 최대 냉방, 최저 온도, 최대 풍량이 된다 | `test_max_ac_sets_signal_and_coldest_settings` | `wait_until(all(car.signal_all(Signal.MAX_AC)))`, `wait_signal(car, Signal.FAN, 7)`, 좌석마다 `wait_value(car.temperature(seat), 16.0)` |
| HVAC-04.2 | 끄면 켜기 전 값(22.0°C, 풍량 3)으로 돌아간다 | `test_max_ac_off_restores_previous_settings` | `wait_signal(car, Signal.FAN, 3)`, 좌석마다 `wait_value(car.temperature(seat), 22.0)` |
| HVAC-04.3 | 풍량을 직접 바꾸면 풀리고, 온도는 되돌리지 않는다 | `test_manual_fan_releases_max_ac` | `wait_signal(car, Signal.MAX_AC, False)`, `wait_signal(car, Signal.FAN, 6)`, `assert car.temperature(Seat.DRIVER) == 16.0` |
| HVAC-04.4 | A/C를 끄면 최대 냉방도 꺼진다 | `test_turning_ac_off_releases_max_ac` | `wait_signal(car, Signal.AC, False)`, `wait_signal(car, Signal.MAX_AC, False)` |
| HVAC-04.5 | 온도를 직접 바꾸면 풀린다 | 확인하지 않음 | 요구사항의 '다른 공조 값'에 온도도 들어가지만 테스트가 없다. 풍량과 A/C만 확인했다 |
| HVAC-04.6 | 차량 쪽에서 바뀐 최대 냉방이 화면 토글에 보인다 | `test_max_ac_signal_is_shown_on_toggle` | `wait_checked("max_ac", True)`, 끄면 `False` |
| DRIVE-02.1 | 주행 중에는 영상 버튼이 꺼지고 안내가 나온다 | `test_video_button_locked_while_driving` | `wait_enabled("open_video", False)`, `assert media.restricted_notice()` |
| DRIVE-02.2 | 버튼을 거치지 않고 영상 화면을 열어도 주행 중에는 막힌다 | `test_video_is_blocked_while_driving` | `wait_until(device.video_blocked(video))`, `assert not video.playing()` |
| DRIVE-02.3 | 차를 세우면 다시 볼 수 있다 | `test_video_blocked_screen_follows_parking`, `test_video_button_locked_while_driving`, `test_video_plays_when_parked` | 막힌 화면이 `wait_until(not device.video_blocked(video))` 뒤 `wait_visible("video_player")`, 영상 버튼 `wait_enabled("open_video", True)`, 정차 중 재생 시간이 흐름 |
| DRIVE-02.4 | 멈춘 자리부터 이어진다. 막힌 동안 재생 시간이 흐르지 않는다 | `test_video_resumes_where_it_stopped` | `assert resumed >= before`(처음부터 다시 재생하지 않음), `assert resumed - before <= wall - 4`(막힌 5초 동안 흐르지 않음). 기기에 영상이 없으면 건너뛰는데, Release 게이트가 이 건너뜀을 막는다 |
| DRIVE-02.5 | 주행 중에도 음악은 고를 수 있다 | `test_media_stays_usable_while_driving` | 주행 제한 표시(`restriction_banner`)가 뜬 상태에서 곡을 고르고 `wait_text("now_playing_title", title)` |
| ENERGY-02.1 | 30 km 이하에서 경고와 충전소 카드가 뜨고, 31 km에서는 뜨지 않는다 | `test_low_range_threshold` | 31, 30, 29 km마다 `wait_value(cluster.low_range_warning(), 기대값)`, `assert app.visible("low_range_card") == 기대값` |
| ENERGY-02.2 | 충전소 카드로 가장 가까운 충전소 안내를 시작한다. 주행 중에도 누를 수 있다 | `test_low_range_card_starts_guidance_to_nearest_charger` | 주행 중 `assert app.text("low_range_charger").startswith("판교 급속 충전소")`, 누른 뒤 `wait_text("nav_dest_name", "판교 급속 충전소")` |
| ENERGY-02.3 | 알림 센터에 남는다 | `test_low_range_is_recorded_in_notifications` | `assert panel.titles()[0] == "주행 가능 거리 부족"` |
| ENERGY-02.4 | 충전해서 거리가 늘면 경고와 카드를 거둔다 | `test_range_recovers_after_charging` | `wait_visible("low_range_card", expected=False)`, `wait_until(not cluster.low_range_warning())` |
| ENERGY-02.5 | Test Bench API와 모의 CAN으로 들어온 거리 값에도 같게 동작한다 | `test_api_low_range_shows_charger_card`, `test_can_battery_and_door_frames_reach_screen` | 25 km를 넣은 뒤 `wait_until(cluster.low_range_warning)`. API 쪽은 카드도 `assert app.visible("low_range_card")` |
