# 테스트 결과

기기마다 E2E 전체를 돌린 결과와 판정 직후 화면입니다. 실행 기록을 바탕으로 `ivi-tests/tools/publish_results.py`가 만듭니다. 두 기기에서 5회 반복한 실행의 마지막 회차이고, 반복 전체의 통계는 [반복 실행 통계](flaky-report.md)에 있습니다.
AAOS 칸 아래의 `PROPERTY[area]=값`은 그 테스트가 판정에 쓴 VHAL 값(CarService로 읽은 마지막 값)입니다.
소개 사이트(`site/docs/test-results.html`)에서는 같은 내용을 화면과 함께 볼 수 있습니다.

| 기기 | 실행 | 결과 | 시간 |
|---|---|---|---|
| AAOS 에뮬레이터 (Car on x86_64 emulator) | 2026-11-18 20:36:17 | 통과 127, 건너뜀 1, 알려진 결함 1 | 9분 45초 |
| 태블릿 (Mock) (DBY-W09) | 2026-11-18 20:36:18 | 통과 122, 건너뜀 7 | 10분 15초 |

태블릿 열은 화면 동작과 실기기에서만 나는 문제(터치 지연, 백그라운드 강제 종료)를 보는 기기입니다. 차량 값은 앱 안의 Mock이라, VHAL 경로는 AAOS 열에서만 확인합니다.

## test_assistant.py

AI 어시스턴트에 한 말이 실제 차량 신호까지 이어지는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_zone_applies_command_to_speaking_seat"></a>`test_zone_applies_command_to_speaking_seat`<br>조수석에서 '나 더워'라고 하면 조수석 온도만 1°C 내려가야 합니다. 차량 신호로 확인합니다. | 통과, 9.4초, [화면](../site/results/img/aaos/test_zone_applies_command_to_speaking_seat.webp)<br>`HVAC_TEMPERATURE_SET[0x4]=21.0`<br>`HVAC_TEMPERATURE_SET[0x1]=22.0` | 통과, 9.0초, [화면](../site/results/img/mock/test_zone_applies_command_to_speaking_seat.webp) |
| <a id="test_typed_command_sets_vehicle_temperature"></a>`test_typed_command_sets_vehicle_temperature`<br>'운전석 25.5도로 맞춰줘'를 글자로 입력하면 차량의 운전석 온도가 25.5°C가 됩니다. | 통과, 4.0초, [화면](../site/results/img/aaos/test_typed_command_sets_vehicle_temperature.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=25.5` | 통과, 4.5초, [화면](../site/results/img/mock/test_typed_command_sets_vehicle_temperature.webp) |
| <a id="test_multiple_commands_in_one_sentence"></a>`test_multiple_commands_in_one_sentence`<br>'에어컨 켜고 음악 틀어줘'처럼 한 문장에 명령이 두 개 들어 있으면 둘 다 실행합니다. | 통과, 4.6초, [화면](../site/results/img/aaos/test_multiple_commands_in_one_sentence.webp) | 통과, 4.9초, [화면](../site/results/img/mock/test_multiple_commands_in_one_sentence.webp) |
| <a id="test_ambiguous_destination_offers_candidates"></a>`test_ambiguous_destination_offers_candidates`<br>'판교 가자'처럼 목적지 후보가 여럿이면 세 곳을 보여 주고 고르게 합니다. 판교역을 고르면 안내가 시작됩니다. | 통과, 4.4초, [화면](../site/results/img/aaos/test_ambiguous_destination_offers_candidates.webp) | 통과, 5.0초, [화면](../site/results/img/mock/test_ambiguous_destination_offers_candidates.webp) |
| <a id="test_driving_locks_typing_and_refuses_mirror_fold"></a>`test_driving_locks_typing_and_refuses_mirror_fold`<br>주행 중에는 글자 입력이 막히고 추천 명령만 쓸 수 있습니다. 사이드 미러를 접어 달라는 명령은 거절합니다. | 통과, 7.1초, [화면](../site/results/img/aaos/test_driving_locks_typing_and_refuses_mirror_fold.webp) | 통과, 7.3초, [화면](../site/results/img/mock/test_driving_locks_typing_and_refuses_mirror_fold.webp) |
| <a id="test_voice_popup_and_assistant_share_history"></a>`test_voice_popup_and_assistant_share_history`<br>음성 팝업에서 한 말이 AI 어시스턴트 대화 내역에도 남습니다. | 통과, 3.9초, [화면](../site/results/img/aaos/test_voice_popup_and_assistant_share_history.webp) | 통과, 4.3초, [화면](../site/results/img/mock/test_voice_popup_and_assistant_share_history.webp) |

## test_bench_api.py

Test Bench REST API로 차량 신호를 넣고 읽으면서 앱 화면이 따라오는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_api_signals_drive_the_screen"></a>`test_api_signals_drive_the_screen`<br>REST API로 기어 D와 속도 50 km/h를 넣으면 화면 속도가 50이 되고 주행 제한 배지가 뜹니다. API로 다시 읽은 신호에도 주행 중으로 나옵니다. | 통과, 5.1초, [화면](../site/results/img/aaos/test_api_signals_drive_the_screen.webp) | 통과, 5.3초, [화면](../site/results/img/mock/test_api_signals_drive_the_screen.webp) |
| <a id="test_api_low_range_shows_charger_card"></a>`test_api_low_range_shows_charger_card`<br>REST API로 주행 가능 거리 25 km를 넣으면 '충전 필요'와 충전소 안내 카드가 뜹니다. | 통과, 2.0초, [화면](../site/results/img/aaos/test_api_low_range_shows_charger_card.webp) | 통과, 2.7초, [화면](../site/results/img/mock/test_api_low_range_shows_charger_card.webp) |
| <a id="test_api_rejects_invalid_value_and_leaves_vehicle_alone"></a>`test_api_rejects_invalid_value_and_leaves_vehicle_alone`<br>범위를 벗어난 값(풍량 9)은 400으로 거절하고, 차량의 풍량은 그대로 둡니다. | 통과, 2.5초, [화면](../site/results/img/aaos/test_api_rejects_invalid_value_and_leaves_vehicle_alone.webp)<br>`HVAC_FAN_SPEED[0x1]=3` | 통과, 3.3초, [화면](../site/results/img/mock/test_api_rejects_invalid_value_and_leaves_vehicle_alone.webp) |

## test_can_gateway.py

가상 CAN 버스의 ECU 프레임이 게이트웨이와 VHAL을 거쳐 화면까지 오는지, 화면에서 바꾼 공조 값이 CAN으로 나가는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_can_drive_frames_reach_screen"></a>`test_can_drive_frames_reach_screen`<br>VCU가 CAN으로 기어 D, 속도 50 km/h를 100 ms마다 보내면 화면 속도가 50이 되고 주행 제한 배지가 뜹니다. P로 바꿔 보내면 0으로 돌아옵니다. 같은 값이 계속 와도 VHAL에는 한 번만 넣습니다. | 통과, 4.5초, [화면](../site/results/img/aaos/test_can_drive_frames_reach_screen.webp) | 통과, 4.1초, [화면](../site/results/img/mock/test_can_drive_frames_reach_screen.webp) |
| <a id="test_can_battery_and_door_frames_reach_screen"></a>`test_can_battery_and_door_frames_reach_screen`<br>BMS가 주행 가능 거리 25 km를 보내면 '충전 필요'가 뜨고, BCM이 문 열림을 보내면 빠른 제어의 도어 표시가 '열림'이 됩니다. | 통과, 3.8초, [화면](../site/results/img/aaos/test_can_battery_and_door_frames_reach_screen.webp) | 통과, 3.5초, [화면](../site/results/img/mock/test_can_battery_and_door_frames_reach_screen.webp) |
| <a id="test_climate_button_goes_out_on_can"></a>`test_climate_button_goes_out_on_can`<br>화면에서 운전석 온도를 한 칸 올리면 게이트웨이가 보내는 IVI_HvacStatus 프레임의 운전석 온도가 22.5°C가 됩니다. | 통과, 4.4초, [화면](../site/results/img/aaos/test_climate_button_goes_out_on_can.webp) | 통과, 4.8초, [화면](../site/results/img/mock/test_climate_button_goes_out_on_can.webp) |

## test_climate.py

공조 온도를 차량 신호와 앱 화면 양쪽에서 확인합니다. 같은 테스트를 AAOS(VHAL)와 태블릿(Mock)에서 돌립니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_signal_is_shown_on_climate_and_home"></a>`test_signal_is_shown_on_climate_and_home` `[driver]`<br>차량의 설정 온도가 바뀌면 공조 화면과 홈 화면이 같은 값을 보여 줍니다. | 통과, 3.8초, [화면](../site/results/img/aaos/test_signal_is_shown_on_climate_and_home_driver.webp) | 통과, 3.8초, [화면](../site/results/img/mock/test_signal_is_shown_on_climate_and_home_driver.webp) |
| `test_signal_is_shown_on_climate_and_home` `[passenger]` | 통과, 3.7초, [화면](../site/results/img/aaos/test_signal_is_shown_on_climate_and_home_passenger.webp) | 통과, 3.8초, [화면](../site/results/img/mock/test_signal_is_shown_on_climate_and_home_passenger.webp) |
| <a id="test_button_changes_signal_by_one_step"></a>`test_button_changes_signal_by_one_step` `[up-driver]`<br>화면의 + 또는 -를 한 번 누르면 차량 온도가 0.5°C 바뀌고, 화면 숫자도 같이 바뀝니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_up-driver.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.5` | 통과, 3.5초, [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_up-driver.webp) |
| `test_button_changes_signal_by_one_step` `[up-passenger]` | 통과, 3.5초, [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_up-passenger.webp)<br>`HVAC_TEMPERATURE_SET[0x4]=22.5` | 통과, 3.6초, [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_up-passenger.webp) |
| `test_button_changes_signal_by_one_step` `[down-driver]` | 통과, 3.4초, [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_down-driver.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=21.5` | 통과, 3.4초, [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_down-driver.webp) |
| `test_button_changes_signal_by_one_step` `[down-passenger]` | 통과, 3.4초, [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_down-passenger.webp)<br>`HVAC_TEMPERATURE_SET[0x4]=21.5` | 통과, 3.7초, [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_down-passenger.webp) |
| <a id="test_buttons_disabled_at_limits"></a>`test_buttons_disabled_at_limits` `[driver]`<br>최저 온도 16.0°C에서는 - 버튼이, 최고 온도 28.0°C에서는 + 버튼이 꺼지고 반대쪽 버튼은 그대로 눌립니다. | 통과, 3.0초, [화면](../site/results/img/aaos/test_buttons_disabled_at_limits_driver.webp) | 통과, 3.3초, [화면](../site/results/img/mock/test_buttons_disabled_at_limits_driver.webp) |
| `test_buttons_disabled_at_limits` `[passenger]` | 통과, 3.1초, [화면](../site/results/img/aaos/test_buttons_disabled_at_limits_passenger.webp) | 통과, 3.7초, [화면](../site/results/img/mock/test_buttons_disabled_at_limits_passenger.webp) |
| <a id="test_step_reaches_limit_and_disables"></a>`test_step_reaches_limit_and_disables` `[driver]`<br>16.5°C에서 -를 한 번 누르면 차량 온도가 16.0°C가 되고 - 버튼이 꺼집니다. 27.5°C에서 +도 같습니다. 끝에 닿은 뒤 꺼진 버튼을 눌러도 차량 온도는 범위를 넘지 않습니다. | 통과, 8.0초, [화면](../site/results/img/aaos/test_step_reaches_limit_and_disables_driver.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=28.0` | 통과, 8.6초, [화면](../site/results/img/mock/test_step_reaches_limit_and_disables_driver.webp) |
| `test_step_reaches_limit_and_disables` `[passenger]` | 통과, 8.3초, [화면](../site/results/img/aaos/test_step_reaches_limit_and_disables_passenger.webp)<br>`HVAC_TEMPERATURE_SET[0x4]=28.0` | 통과, 9.1초, [화면](../site/results/img/mock/test_step_reaches_limit_and_disables_passenger.webp) |
| <a id="test_out_of_range_signal_is_shown_safely"></a>`test_out_of_range_signal_is_shown_safely` `[below_min]`<br>차량 쪽에서 범위 밖 온도(15.5°C, 28.5°C)가 와도 앱은 멈추지 않고 차량 값을 그대로 보여 줍니다. 범위 밖으로 더 가는 버튼은 꺼지고, 반대 버튼을 한 번 누르면 차량 온도가 16.0~28.0°C 안의 0.5°C 단위 값이 됩니다. AAOS는 VHAL에 값을 바로 넣고, Mock 차량은 받은 값을 범위 안으로 잘라 둡니다. | 통과, 3.5초, [화면](../site/results/img/aaos/test_out_of_range_signal_is_shown_safely_below_min.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=16.0` | 통과, 3.9초, [화면](../site/results/img/mock/test_out_of_range_signal_is_shown_safely_below_min.webp) |
| `test_out_of_range_signal_is_shown_safely` `[above_max]` | 통과, 3.5초, [화면](../site/results/img/aaos/test_out_of_range_signal_is_shown_safely_above_max.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=28.0` | 통과, 3.8초, [화면](../site/results/img/mock/test_out_of_range_signal_is_shown_safely_above_max.webp) |
| <a id="test_off_grid_signal_steps_back_to_grid"></a>`test_off_grid_signal_steps_back_to_grid` `[up-22.5]`<br>차량 쪽에서 0.5°C 단위가 아닌 온도(22.3°C)가 와도, 버튼을 한 번 누르면 차량 온도가 0.5°C 단위(+는 22.5°C, -는 22.0°C)로 맞춰집니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_off_grid_signal_steps_back_to_grid_up-22.5.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.5` | 통과, 3.5초, [화면](../site/results/img/mock/test_off_grid_signal_steps_back_to_grid_up-22.5.webp) |
| `test_off_grid_signal_steps_back_to_grid` `[down-22.0]` | 통과, 3.4초, [화면](../site/results/img/aaos/test_off_grid_signal_steps_back_to_grid_down-22.0.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.0` | 통과, 3.5초, [화면](../site/results/img/mock/test_off_grid_signal_steps_back_to_grid_down-22.0.webp) |
| <a id="test_seats_are_independent"></a>`test_seats_are_independent`<br>한쪽 좌석 온도를 바꿔도 다른 좌석 값은 그대로여야 합니다. 좌석 area를 헷갈리는 결함을 잡는 테스트입니다. | 통과, 5.2초, [화면](../site/results/img/aaos/test_seats_are_independent.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.5`<br>`HVAC_TEMPERATURE_SET[0x4]=22.0` | 통과, 5.2초, [화면](../site/results/img/mock/test_seats_are_independent.webp) |

## test_cockpit.py

화면 틀을 확인합니다. 아래 바 공조, 온도 동기화, 주행 정보, 분할 화면, 빠른 제어, 알림이 대상입니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_bottom_bar_temperature_drives_vehicle"></a>`test_bottom_bar_temperature_drives_vehicle` `[driver]`<br>아래 바의 온도 버튼은 어느 화면에서든 차량 온도를 바꿉니다. 차량 쪽 값이 바뀌면 아래 바 숫자도 따라 바뀝니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_bottom_bar_temperature_drives_vehicle_driver.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.5` | 통과, 3.4초, [화면](../site/results/img/mock/test_bottom_bar_temperature_drives_vehicle_driver.webp) |
| `test_bottom_bar_temperature_drives_vehicle` `[passenger]` | 통과, 3.4초, [화면](../site/results/img/aaos/test_bottom_bar_temperature_drives_vehicle_passenger.webp)<br>`HVAC_TEMPERATURE_SET[0x4]=22.5` | 통과, 3.5초, [화면](../site/results/img/mock/test_bottom_bar_temperature_drives_vehicle_passenger.webp) |
| <a id="test_sync_mirrors_driver_temperature_to_passenger"></a>`test_sync_mirrors_driver_temperature_to_passenger`<br>SYNC를 켜면 조수석 온도가 운전석과 같아지고, 그 뒤 운전석을 바꾸면 조수석 차량 값도 같이 바뀝니다. | 통과, 4.0초, [화면](../site/results/img/aaos/test_sync_mirrors_driver_temperature_to_passenger.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=24.5`<br>`HVAC_TEMPERATURE_SET[0x4]=24.5` | 통과, 3.8초, [화면](../site/results/img/mock/test_sync_mirrors_driver_temperature_to_passenger.webp) |
| <a id="test_passenger_change_releases_sync"></a>`test_passenger_change_releases_sync`<br>동기화 중에 조수석 온도를 직접 바꾸면 동기화가 풀립니다. 그 뒤로는 운전석을 바꿔도 운전석만 바뀝니다. | 통과, 4.9초, [화면](../site/results/img/aaos/test_passenger_change_releases_sync.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.5`<br>`HVAC_TEMPERATURE_SET[0x4]=21.5` | 통과, 4.5초, [화면](../site/results/img/mock/test_passenger_change_releases_sync.webp) |
| <a id="test_trip_distance_follows_speed_signal"></a>`test_trip_distance_follows_speed_signal`<br>현 주행 정보의 거리는 속도 신호에 따라 늘고, 차를 세우면 멈춥니다. 120 km/h로 3초를 달리면 0.1 km쯤 늘어납니다. | 통과, 7.5초, [화면](../site/results/img/aaos/test_trip_distance_follows_speed_signal.webp) | 통과, 6.9초, [화면](../site/results/img/mock/test_trip_distance_follows_speed_signal.webp) |
| <a id="test_lane_assist_indicator_follows_speed"></a>`test_lane_assist_indicator_follows_speed`<br>운전자 보조 표시는 D 기어에서 30 km/h 이상이면 '작동', 그보다 느리면 '대기'가 됩니다. 실제 ADAS 신호가 아니라 화면 연출입니다. | 통과, 3.0초, [화면](../site/results/img/aaos/test_lane_assist_indicator_follows_speed.webp) | 통과, 1.9초, [화면](../site/results/img/mock/test_lane_assist_indicator_follows_speed.webp) |
| <a id="test_utility_widget_pages"></a>`test_utility_widget_pages`<br>주행 정보 위젯을 넘기면 현 주행 정보, 경로, 타이어 공기압 순서로 바뀌고 다시 처음으로 돌아옵니다. | 통과, 2.9초, [화면](../site/results/img/aaos/test_utility_widget_pages.webp) | 통과, 3.2초, [화면](../site/results/img/mock/test_utility_widget_pages.webp) |
| <a id="test_split_screen_toggle"></a>`test_split_screen_toggle`<br>홈 화면을 내비와 오디오가 같이 있는 분할 화면, 내비만 있는 화면으로 바꿀 수 있습니다. 두 화면 모두에서 내비를 쓸 수 있습니다. | 통과, 3.9초, [화면](../site/results/img/aaos/test_split_screen_toggle.webp) | 통과, 4.3초, [화면](../site/results/img/mock/test_split_screen_toggle.webp) |
| <a id="test_quick_control_mirror_locked_while_driving"></a>`test_quick_control_mirror_locked_while_driving`<br>주행 중에는 빠른 제어의 사이드 미러 접기와 트렁크가 막히지만, 도어 잠금은 쓸 수 있습니다. | 통과, 7.0초, [화면](../site/results/img/aaos/test_quick_control_mirror_locked_while_driving.webp) | 통과, 5.4초, [화면](../site/results/img/mock/test_quick_control_mirror_locked_while_driving.webp) |
| <a id="test_notifications_record_guidance_and_restriction"></a>`test_notifications_record_guidance_and_restriction`<br>경로 안내 시작과 주행 제한이 알림 센터에 쌓이고, 알림 센터를 열면 배지가 사라집니다. | 통과, 4.7초, [화면](../site/results/img/aaos/test_notifications_record_guidance_and_restriction.webp) | 통과, 5.1초, [화면](../site/results/img/mock/test_notifications_record_guidance_and_restriction.webp) |
| <a id="test_recent_app_slot"></a>`test_recent_app_slot`<br>앱 목록에서 라디오를 연 뒤 다른 앱으로 넘어가도 아래 바에 라디오가 남아 있어 바로 돌아갈 수 있습니다. | 통과, 4.2초, [화면](../site/results/img/aaos/test_recent_app_slot.webp) | 통과, 4.6초, [화면](../site/results/img/mock/test_recent_app_slot.webp) |

## test_driving.py

속도와 기어 신호가 화면에 보이는지, 주행 중에 영상이 막히는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_driving_signals_are_shown"></a>`test_driving_signals_are_shown`<br>속도 50 km/h와 D 기어 신호를 넣으면 화면에 그대로 보이고 주행 제한 배지가 뜹니다. 차를 세우면 0과 P로 돌아오고 배지가 사라집니다. | 통과, 4.5초, [화면](../site/results/img/aaos/test_driving_signals_are_shown.webp) | 통과, 3.1초, [화면](../site/results/img/mock/test_driving_signals_are_shown.webp) |
| <a id="test_video_button_locked_while_driving"></a>`test_video_button_locked_while_driving`<br>주행 중에는 미디어 화면의 영상 버튼이 꺼지고 안내 문구가 나옵니다. 차를 세우면 다시 누를 수 있습니다. | 통과, 4.4초, [화면](../site/results/img/aaos/test_video_button_locked_while_driving.webp) | 통과, 3.2초, [화면](../site/results/img/mock/test_video_button_locked_while_driving.webp) |
| <a id="test_video_is_blocked_while_driving"></a>`test_video_is_blocked_while_driving`<br>영상 버튼을 거치지 않고 영상 화면을 바로 열어도 주행 중에는 막혀야 합니다. 다른 앱이나 알림에서 들어오는 경우입니다. | 통과, 3.2초, [화면](../site/results/img/aaos/test_video_is_blocked_while_driving.webp) | 통과, 3.2초, [화면](../site/results/img/mock/test_video_is_blocked_while_driving.webp) |
| <a id="test_video_plays_when_parked"></a>`test_video_plays_when_parked`<br>차가 서 있을 때는 영상 화면이 열리고 재생 시간이 흐릅니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_video_plays_when_parked.webp) | 통과, 3.3초, [화면](../site/results/img/mock/test_video_plays_when_parked.webp) |
| <a id="test_video_blocked_screen_follows_parking"></a>`test_video_blocked_screen_follows_parking`<br>주행 중에 막혔던 영상은 차를 세우면 다시 볼 수 있어야 합니다. 차단 화면이 그대로 남아 있으면 결함입니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_video_blocked_screen_follows_parking.webp) | 통과, 4.1초, [화면](../site/results/img/mock/test_video_blocked_screen_follows_parking.webp) |
| <a id="test_video_resumes_where_it_stopped"></a>`test_video_resumes_where_it_stopped`<br>주행 때문에 멈춘 영상은 차를 세우면 처음부터가 아니라 멈춘 자리에서 이어집니다. 막혀 있는 동안에는 재생 시간이 흐르지 않아야 합니다. | 통과, 12.2초, [화면](../site/results/img/aaos/test_video_resumes_where_it_stopped.webp) | 통과, 12.7초, [화면](../site/results/img/mock/test_video_resumes_where_it_stopped.webp) |
| <a id="test_video_next_clip"></a>`test_video_next_clip`<br>영상이 여러 개 있으면 다음 버튼으로 두 번째 영상으로 넘어갑니다. | 통과, 4.2초, [화면](../site/results/img/aaos/test_video_next_clip.webp) | 통과, 3.4초, [화면](../site/results/img/mock/test_video_next_clip.webp) |

## test_media.py

미디어 화면의 기본 기능을 확인합니다. 차량 신호와는 관계없는 회귀 테스트입니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_selecting_track_starts_it"></a>`test_selecting_track_starts_it` `[0]`<br>재생 목록에서 곡을 고르면 그 곡이 재생됩니다. | 통과, 3.3초, [화면](../site/results/img/aaos/test_selecting_track_starts_it_0.webp) | 통과, 3.5초, [화면](../site/results/img/mock/test_selecting_track_starts_it_0.webp) |
| `test_selecting_track_starts_it` `[2]` | 통과, 3.3초, [화면](../site/results/img/aaos/test_selecting_track_starts_it_2.webp) | 통과, 3.5초, [화면](../site/results/img/mock/test_selecting_track_starts_it_2.webp) |
| `test_selecting_track_starts_it` `[4]` | 통과, 3.3초, [화면](../site/results/img/aaos/test_selecting_track_starts_it_4.webp) | 통과, 3.5초, [화면](../site/results/img/mock/test_selecting_track_starts_it_4.webp) |
| <a id="test_play_pause_toggles"></a>`test_play_pause_toggles`<br>재생 버튼을 누를 때마다 재생과 일시 정지가 번갈아 바뀝니다. | 통과, 4.5초, [화면](../site/results/img/aaos/test_play_pause_toggles.webp) | 통과, 4.6초, [화면](../site/results/img/mock/test_play_pause_toggles.webp) |
| <a id="test_media_stays_usable_while_driving"></a>`test_media_stays_usable_while_driving`<br>주행 중에도 음악은 고를 수 있습니다. 막혀야 하는 것은 영상뿐입니다. | 통과, 4.4초, [화면](../site/results/img/aaos/test_media_stays_usable_while_driving.webp) | 통과, 3.6초, [화면](../site/results/img/mock/test_media_stays_usable_while_driving.webp) |

## test_navigation.py

경로 안내가 차량 속도에 맞춰 진행되는지, 주행 중에 검색 입력이 막히는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_guidance_counts_down_with_vehicle_speed"></a>`test_guidance_counts_down_with_vehicle_speed`<br>경로 안내의 남은 거리가 차량 속도 신호만큼 줄어듭니다. 120 km/h로 3초를 달리면 0.1 km쯤 줄어듭니다. | 통과, 8.4초, [화면](../site/results/img/aaos/test_guidance_counts_down_with_vehicle_speed.webp) | 통과, 8.8초, [화면](../site/results/img/mock/test_guidance_counts_down_with_vehicle_speed.webp) |
| <a id="test_parked_vehicle_does_not_advance_route"></a>`test_parked_vehicle_does_not_advance_route`<br>차가 서 있으면 남은 거리가 줄지 않습니다. 안내가 시간이 아니라 속도 신호를 따라 진행된다는 것을 확인합니다. | 통과, 6.5초, [화면](../site/results/img/aaos/test_parked_vehicle_does_not_advance_route.webp) | 통과, 7.0초, [화면](../site/results/img/mock/test_parked_vehicle_does_not_advance_route.webp) |
| <a id="test_search_locked_while_driving_but_favorites_work"></a>`test_search_locked_while_driving_but_favorites_work`<br>주행 중에는 검색 입력이 막히지만, 즐겨찾기로는 목적지를 고를 수 있습니다. | 통과, 4.1초, [화면](../site/results/img/aaos/test_search_locked_while_driving_but_favorites_work.webp) | 통과, 4.3초, [화면](../site/results/img/mock/test_search_locked_while_driving_but_favorites_work.webp) |
| <a id="test_search_filters_destinations"></a>`test_search_filters_destinations`<br>'역'으로 검색하면 판교역과 서울역만 남습니다. | 통과, 2.8초, [화면](../site/results/img/aaos/test_search_filters_destinations.webp) | 통과, 2.8초, [화면](../site/results/img/mock/test_search_filters_destinations.webp) |
| <a id="test_arrival"></a>`test_arrival`<br>0.1 km 떨어진 편의점으로 안내를 시작하고 120 km/h로 달리면 도착 화면이 뜹니다. | 통과, 7.4초, [화면](../site/results/img/aaos/test_arrival.webp) | 통과, 8.0초, [화면](../site/results/img/mock/test_arrival.webp) |
| <a id="test_stop_guidance_returns_to_search_and_clears_cluster_route"></a>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>안내 중인 경로는 왼쪽 주행 정보에 보이고, 다른 앱을 보고 있어도 남아 있습니다. 안내를 끝내면 검색 화면으로 돌아가고 경로 표시도 사라집니다. | 통과, 4.8초, [화면](../site/results/img/aaos/test_stop_guidance_returns_to_search_and_clears_cluster_route.webp) | 통과, 5.6초, [화면](../site/results/img/mock/test_stop_guidance_returns_to_search_and_clears_cluster_route.webp) |

## test_phone.py

블루투스 핸즈프리 전화(가상)의 통화 화면, 최근 통화, 키패드, 주행 중 제한을 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_call_contact_shows_call_screen_and_recent"></a>`test_call_contact_shows_call_screen_and_recent`<br>연락처에서 전화를 걸면 통화 화면에 이름과 통화 시간이 보이고, 끊고 나면 최근 통화 맨 위에 남습니다. | 통과, 5.5초, [화면](../site/results/img/aaos/test_call_contact_shows_call_screen_and_recent.webp) | 통과, 6.3초, [화면](../site/results/img/mock/test_call_contact_shows_call_screen_and_recent.webp) |
| <a id="test_keypad_dial"></a>`test_keypad_dial`<br>키패드로 번호를 눌러 전화를 걸면 통화 화면에 그 번호가 보입니다. | 통과, 6.3초, [화면](../site/results/img/aaos/test_keypad_dial.webp) | 통과, 7.3초, [화면](../site/results/img/mock/test_keypad_dial.webp) |
| <a id="test_driving_locks_keypad_and_limits_contacts"></a>`test_driving_locks_keypad_and_limits_contacts`<br>주행 중에는 키패드가 막히고 연락처는 5개까지만 보입니다. | 통과, 5.3초, [화면](../site/results/img/aaos/test_driving_locks_keypad_and_limits_contacts.webp) | 통과, 5.2초, [화면](../site/results/img/mock/test_driving_locks_keypad_and_limits_contacts.webp) |
| <a id="test_call_pauses_radio_then_resumes"></a>`test_call_pauses_radio_then_resumes`<br>라디오를 듣다가 전화를 걸면 라디오가 멈추고, 통화를 끝내면 다시 나옵니다. | 통과, 6.0초, [화면](../site/results/img/aaos/test_call_pauses_radio_then_resumes.webp) | 통과, 7.5초, [화면](../site/results/img/mock/test_call_pauses_radio_then_resumes.webp) |

## test_power.py

원격 전원 제어로 에뮬레이터를 껐다 켠 뒤 부팅, 앱, 공조 기본값이 돌아오는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_power_cycle_brings_back_app_and_cabin_defaults"></a>`test_power_cycle_brings_back_app_and_cabin_defaults`<br>전원을 껐다 켜면 3분 안에 부팅이 끝나고, 앱이 다시 CarService에 붙으며, 공조는 기본값 22.0°C로 시작합니다. 부팅에 걸린 시간은 결과에 남깁니다. | 통과, 37.2초, [화면](../site/results/img/aaos/test_power_cycle_brings_back_app_and_cabin_defaults.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=22.0`<br>`HVAC_TEMPERATURE_SET[0x4]=22.0` | 건너뜀, 0.2초 |

## test_radio.py

라디오의 켜기, 주파수 조정, 방송국 찾기, 대역 전환, 프리셋을 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_power_on_plays_default_station"></a>`test_power_on_plays_default_station`<br>라디오를 켜면 기본 방송인 89.1 MHz 뉴스 FM이 나옵니다. | 통과, 3.5초, [화면](../site/results/img/aaos/test_power_on_plays_default_station.webp) | 통과, 3.9초, [화면](../site/results/img/mock/test_power_on_plays_default_station.webp) |
| <a id="test_tune_and_seek"></a>`test_tune_and_seek`<br>미세 조정은 0.1 MHz씩 움직이고, 방송국 찾기는 방송이 있는 다음 주파수로 바로 넘어갑니다. | 통과, 5.1초, [화면](../site/results/img/aaos/test_tune_and_seek.webp) | 통과, 6.1초, [화면](../site/results/img/mock/test_tune_and_seek.webp) |
| <a id="test_am_band_uses_khz_steps"></a>`test_am_band_uses_khz_steps`<br>AM으로 바꾸면 주파수가 kHz 단위로 바뀌고 9 kHz씩 움직입니다. | 통과, 4.2초, [화면](../site/results/img/aaos/test_am_band_uses_khz_steps.webp) | 통과, 4.6초, [화면](../site/results/img/mock/test_am_band_uses_khz_steps.webp) |
| <a id="test_preset_save_and_recall"></a>`test_preset_save_and_recall`<br>지금 주파수를 프리셋에 저장하고 다른 방송으로 옮긴 뒤 프리셋을 누르면, 저장한 주파수로 돌아옵니다. | 통과, 5.6초, [화면](../site/results/img/aaos/test_preset_save_and_recall.webp) | 통과, 6.8초, [화면](../site/results/img/mock/test_preset_save_and_recall.webp) |
| <a id="test_preset_and_frequency_survive_app_restart"></a>`test_preset_and_frequency_survive_app_restart`<br>앱을 완전히 껐다 켜도 프리셋과 마지막으로 듣던 주파수가 남아 있습니다. | 통과, 9.9초, [화면](../site/results/img/aaos/test_preset_and_frequency_survive_app_restart.webp) | 통과, 10.1초, [화면](../site/results/img/mock/test_preset_and_frequency_survive_app_restart.webp) |
| <a id="test_radio_and_media_play_one_at_a_time"></a>`test_radio_and_media_play_one_at_a_time`<br>음악을 듣다가 라디오를 켜면 음악이 일시 정지됩니다. 소리는 한 번에 하나만 나옵니다. | 통과, 5.3초, [화면](../site/results/img/aaos/test_radio_and_media_play_one_at_a_time.webp) | 통과, 6.2초, [화면](../site/results/img/mock/test_radio_and_media_play_one_at_a_time.webp) |

## test_rear_camera.py

기어가 R이 되면 어느 화면에서든 후방 카메라가 뜨고, R에서 벗어나면 보던 화면으로 돌아오는지 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_reverse_gear_shows_camera"></a>`test_reverse_gear_shows_camera`<br>기어가 R이 되면 후방 카메라 화면이 뜨고, P로 바꾸면 사라집니다. | 통과, 3.3초, [화면](../site/results/img/aaos/test_reverse_gear_shows_camera.webp) | 통과, 2.3초, [화면](../site/results/img/mock/test_reverse_gear_shows_camera.webp) |
| <a id="test_camera_returns_to_previous_screen"></a>`test_camera_returns_to_previous_screen`<br>라디오를 보다가 후진하면 카메라가 뜨고, 기어를 바꾸면 보던 라디오 화면으로 돌아옵니다. | 통과, 4.7초, [화면](../site/results/img/aaos/test_camera_returns_to_previous_screen.webp) | 통과, 4.1초, [화면](../site/results/img/mock/test_camera_returns_to_previous_screen.webp) |
| <a id="test_gear_value_shows_reverse"></a>`test_gear_value_shows_reverse`<br>후진 기어 신호가 들어오면 주행 정보의 기어 표시가 R로 바뀝니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_gear_value_shows_reverse.webp) | 통과, 2.6초, [화면](../site/results/img/mock/test_gear_value_shows_reverse.webp) |
| <a id="test_rear_camera_appears_within_two_seconds"></a>`test_rear_camera_appears_within_two_seconds`<br>기어를 R로 바꾼 뒤 2.0초 안에 후방 카메라 화면이 떠야 합니다(FMVSS 111). 다섯 번 재서 가장 느린 값으로 판정하고, 신호를 넣는 adb 시간까지 포함해 잽니다. | 통과, 7.6초, [화면](../site/results/img/aaos/test_rear_camera_appears_within_two_seconds.webp) | 통과, 4.4초, [화면](../site/results/img/mock/test_rear_camera_appears_within_two_seconds.webp) |

## test_settings.py

설정의 속도 단위, 볼륨, 저장 유지, 초기화, 시계 형식을 확인합니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_mph_setting_converts_vehicle_speed"></a>`test_mph_setting_converts_vehicle_speed`<br>속도 단위를 mph로 바꾸면 차량 속도 50 km/h가 31 mph로 보입니다. | 통과, 4.7초, [화면](../site/results/img/aaos/test_mph_setting_converts_vehicle_speed.webp) | 통과, 4.7초, [화면](../site/results/img/mock/test_mph_setting_converts_vehicle_speed.webp) |
| <a id="test_volume_steps"></a>`test_volume_steps`<br>볼륨은 한 단계씩 오르내립니다. 기본값 15에서 한 번 올리고 두 번 내리면 14가 됩니다. | 통과, 4.6초, [화면](../site/results/img/aaos/test_volume_steps.webp) | 통과, 5.1초, [화면](../site/results/img/mock/test_volume_steps.webp) |
| <a id="test_settings_survive_app_restart"></a>`test_settings_survive_app_restart`<br>속도 단위, 무드등 색, 밝기를 바꾸고 앱을 껐다 켜도 바꾼 값이 그대로 남아 있습니다. | 통과, 10.5초, [화면](../site/results/img/aaos/test_settings_survive_app_restart.webp) | 통과, 10.8초, [화면](../site/results/img/mock/test_settings_survive_app_restart.webp) |
| <a id="test_reset_restores_defaults"></a>`test_reset_restores_defaults`<br>설정 초기화를 누르면 바꿔 둔 볼륨과 도어 자동 잠금이 기본값으로 돌아옵니다. | 통과, 5.7초, [화면](../site/results/img/aaos/test_reset_restores_defaults.webp) | 통과, 6.5초, [화면](../site/results/img/mock/test_reset_restores_defaults.webp) |
| <a id="test_12_hour_clock_on_tablet"></a>`test_12_hour_clock_on_tablet`<br>태블릿에는 시스템 바가 없어서 앱이 시계를 직접 그립니다. 24시간 시계를 끄면 오전, 오후가 붙은 12시간 형식으로 바뀝니다. | 건너뜀, 1.7초, [화면](../site/results/img/aaos/test_12_hour_clock_on_tablet.webp) | 통과, 4.5초, [화면](../site/results/img/mock/test_12_hour_clock_on_tablet.webp) |

## test_smoke.py

빌드가 나오면 가장 먼저 돌리는 최소 확인입니다. 여기서 실패하면 나머지 테스트는 돌려도 의미가 없습니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_app_starts_with_vehicle_source_for_device"></a>`test_app_starts_with_vehicle_source_for_device`<br>앱이 뜨고 기기에 맞는 차량 데이터에 연결됩니다. AAOS에서는 CarService, 태블릿에서는 Mock입니다. | 통과, 2.0초, [화면](../site/results/img/aaos/test_app_starts_with_vehicle_source_for_device.webp) | 통과, 2.0초, [화면](../site/results/img/mock/test_app_starts_with_vehicle_source_for_device.webp) |
| <a id="test_parked_on_start"></a>`test_parked_on_start`<br>정차 상태로 시작하면 속도는 0, 기어는 P이고 주행 제한 배지가 없습니다. | 통과, 2.7초, [화면](../site/results/img/aaos/test_parked_on_start.webp) | 통과, 2.7초, [화면](../site/results/img/mock/test_parked_on_start.webp) |
| <a id="test_each_tab_opens"></a>`test_each_tab_opens` `[home]`<br>탭마다 화면이 열리는지 봅니다. 화면마다 핵심 요소가 나타날 때까지 기다립니다. | 통과, 2.5초, [화면](../site/results/img/aaos/test_each_tab_opens_home.webp) | 통과, 2.4초, [화면](../site/results/img/mock/test_each_tab_opens_home.webp) |
| `test_each_tab_opens` `[navigation]` | 통과, 2.6초, [화면](../site/results/img/aaos/test_each_tab_opens_navigation.webp) | 통과, 2.5초, [화면](../site/results/img/mock/test_each_tab_opens_navigation.webp) |
| `test_each_tab_opens` `[radio]` | 통과, 3.2초, [화면](../site/results/img/aaos/test_each_tab_opens_radio.webp) | 통과, 3.2초, [화면](../site/results/img/mock/test_each_tab_opens_radio.webp) |
| `test_each_tab_opens` `[media]` | 통과, 2.6초, [화면](../site/results/img/aaos/test_each_tab_opens_media.webp) | 통과, 2.5초, [화면](../site/results/img/mock/test_each_tab_opens_media.webp) |
| `test_each_tab_opens` `[phone]` | 통과, 2.6초, [화면](../site/results/img/aaos/test_each_tab_opens_phone.webp) | 통과, 2.6초, [화면](../site/results/img/mock/test_each_tab_opens_phone.webp) |
| `test_each_tab_opens` `[climate]` | 통과, 2.6초, [화면](../site/results/img/aaos/test_each_tab_opens_climate.webp) | 통과, 2.6초, [화면](../site/results/img/mock/test_each_tab_opens_climate.webp) |
| `test_each_tab_opens` `[settings]` | 통과, 3.2초, [화면](../site/results/img/aaos/test_each_tab_opens_settings.webp) | 통과, 3.4초, [화면](../site/results/img/mock/test_each_tab_opens_settings.webp) |
| `test_each_tab_opens` `[assistant]` | 통과, 2.6초, [화면](../site/results/img/aaos/test_each_tab_opens_assistant.webp) | 통과, 2.5초, [화면](../site/results/img/mock/test_each_tab_opens_assistant.webp) |
| `test_each_tab_opens` `[vehicle_controls]` | 통과, 2.5초, [화면](../site/results/img/aaos/test_each_tab_opens_vehicle_controls.webp) | 통과, 2.5초, [화면](../site/results/img/mock/test_each_tab_opens_vehicle_controls.webp) |
| `test_each_tab_opens` `[apps]` | 통과, 2.7초, [화면](../site/results/img/aaos/test_each_tab_opens_apps.webp) | 통과, 2.5초, [화면](../site/results/img/mock/test_each_tab_opens_apps.webp) |
| <a id="test_hvac_is_controllable"></a>`test_hvac_is_controllable`<br>공조를 제어할 수 있는지 봅니다. AAOS에서 실패하면 priv-app 설치와 공조 권한부터 확인합니다. | 통과, 2.7초, [화면](../site/results/img/aaos/test_hvac_is_controllable.webp) | 통과, 2.7초, [화면](../site/results/img/mock/test_hvac_is_controllable.webp) |

## test_spike_aaos.py

1단계 기술 검증입니다. 앱을 만들기 전에 AAOS 기본 SystemUI로 신호와 화면이 이어지는지 먼저 확인했습니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_hvac_signal_is_shown_on_ui"></a>`test_hvac_signal_is_shown_on_ui` `[25.0]`<br>운전석 설정 온도 property를 바꾸면 AAOS 기본 하단 공조 바의 숫자가 따라 바뀝니다. | 통과, 1.8초, [화면](../site/results/img/aaos/test_hvac_signal_is_shown_on_ui_25.0.webp)<br>`HVAC_TEMPERATURE_DISPLAY_UNITS=48` | 건너뜀, 0.0초 |
| `test_hvac_signal_is_shown_on_ui` `[20.0]` | 통과, 2.3초, [화면](../site/results/img/aaos/test_hvac_signal_is_shown_on_ui_20.0.webp)<br>`HVAC_TEMPERATURE_DISPLAY_UNITS=48` | 건너뜀, 0.0초 |
| <a id="test_hvac_ui_tap_changes_signal"></a>`test_hvac_ui_tap_changes_signal` `[driver-hvac_decrease_button--0.5]`<br>하단 공조 바의 온도 ▲ 또는 ▼를 한 번 누르면 property 값이 0.5°C 바뀝니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_hvac_ui_tap_changes_signal_driver-hvac_decrease_button--0.5.webp)<br>`HVAC_TEMPERATURE_DISPLAY_UNITS=48`<br>`HVAC_TEMPERATURE_SET[0x1]=19.5` | 건너뜀, 0.0초 |
| `test_hvac_ui_tap_changes_signal` `[passenger-hvac_increase_button-0.5]` | 통과, 3.0초, [화면](../site/results/img/aaos/test_hvac_ui_tap_changes_signal_passenger-hvac_increase_button-0.5.webp)<br>`HVAC_TEMPERATURE_DISPLAY_UNITS=48`<br>`HVAC_TEMPERATURE_SET[0x4]=20.5` | 건너뜀, 0.0초 |
| <a id="test_driver_temp_up_is_not_covered_by_home"></a>`test_driver_temp_up_is_not_covered_by_home`<br>운전석 온도 ▲ 버튼이 홈 버튼에 가려지지 않는지 봅니다. 1단계에서 찾은 SystemUI 결함이라 알려진 결함으로 남겨 두었습니다. | 알려진 결함, 1.4초, [화면](../site/results/img/aaos/test_driver_temp_up_is_not_covered_by_home.webp) | 건너뜀, 0.0초 |
| <a id="test_speed_and_gear_change_driving_state"></a>`test_speed_and_gear_change_driving_state`<br>속도와 기어를 VHAL에 넣으면 CarService의 주행 상태가 바뀝니다. 주행 중 화면 제한은 이 값을 보고 동작합니다. | 통과, 1.4초, [화면](../site/results/img/aaos/test_speed_and_gear_change_driving_state.webp) | 건너뜀, 0.0초 |

## test_vehicle_signals.py

8단계에서 연결한 차량 신호를 확인합니다. 공조 부가 기능, 좌석 열선, 도어 잠금, 주행 가능 거리, 배터리, 외기 온도입니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_ac_toggle_reaches_every_seat"></a>`test_ac_toggle_reaches_every_seat`<br>화면에서 A/C를 끄면 운전석만이 아니라 모든 좌석의 HVAC_AC_ON이 꺼져야 합니다. | 통과, 3.5초, [화면](../site/results/img/aaos/test_ac_toggle_reaches_every_seat.webp)<br>`HVAC_AC_ON[0x10]=0`<br>`HVAC_AC_ON[0x40]=0`<br>`HVAC_AC_ON[0x20]=0` | 통과, 3.6초, [화면](../site/results/img/mock/test_ac_toggle_reaches_every_seat.webp) |
| <a id="test_ac_signal_is_shown_on_climate_and_bottom_bar"></a>`test_ac_signal_is_shown_on_climate_and_bottom_bar`<br>차량 쪽에서 A/C를 끄면 공조 화면의 토글도 꺼지고, 다시 켜면 켜집니다. | 통과, 2.8초, [화면](../site/results/img/aaos/test_ac_signal_is_shown_on_climate_and_bottom_bar.webp) | 통과, 2.8초, [화면](../site/results/img/mock/test_ac_signal_is_shown_on_climate_and_bottom_bar.webp) |
| <a id="test_fan_button_changes_signal_by_one"></a>`test_fan_button_changes_signal_by_one` `[up-4]`<br>풍량 + 또는 -를 한 번 누르면 HVAC_FAN_SPEED가 한 단계 바뀌고 화면 숫자도 같이 바뀝니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_fan_button_changes_signal_by_one_up-4.webp)<br>`HVAC_FAN_SPEED[0x1]=4` | 통과, 3.6초, [화면](../site/results/img/mock/test_fan_button_changes_signal_by_one_up-4.webp) |
| `test_fan_button_changes_signal_by_one` `[down-2]` | 통과, 3.4초, [화면](../site/results/img/aaos/test_fan_button_changes_signal_by_one_down-2.webp)<br>`HVAC_FAN_SPEED[0x1]=2` | 통과, 3.5초, [화면](../site/results/img/mock/test_fan_button_changes_signal_by_one_down-2.webp) |
| <a id="test_fan_buttons_disabled_at_limits"></a>`test_fan_buttons_disabled_at_limits` `[1-climate_fan_down]`<br>풍량이 최저 1이면 -가, 최고 7이면 +가 눌리지 않고 신호도 범위를 벗어나지 않습니다. | 통과, 2.9초, [화면](../site/results/img/aaos/test_fan_buttons_disabled_at_limits_1-climate_fan_down.webp)<br>`HVAC_FAN_SPEED[0x1]=1` | 통과, 3.2초, [화면](../site/results/img/mock/test_fan_buttons_disabled_at_limits_1-climate_fan_down.webp) |
| `test_fan_buttons_disabled_at_limits` `[7-climate_fan_up]` | 통과, 4.1초, [화면](../site/results/img/aaos/test_fan_buttons_disabled_at_limits_7-climate_fan_up.webp)<br>`HVAC_FAN_SPEED[0x1]=7` | 통과, 3.1초, [화면](../site/results/img/mock/test_fan_buttons_disabled_at_limits_7-climate_fan_up.webp) |
| <a id="test_max_ac_sets_signal_and_coldest_settings"></a>`test_max_ac_sets_signal_and_coldest_settings`<br>FULL(최대 냉방)을 켜면 모든 좌석의 HVAC_MAX_AC_ON이 켜지고, 온도는 최저, 풍량은 최대가 되며 AUTO는 꺼집니다. | 통과, 4.4초, [화면](../site/results/img/aaos/test_max_ac_sets_signal_and_coldest_settings.webp)<br>`HVAC_AC_ON[0x1]=1`<br>`HVAC_TEMPERATURE_SET[0x1]=16.0`<br>`HVAC_TEMPERATURE_SET[0x4]=16.0` | 통과, 4.3초, [화면](../site/results/img/mock/test_max_ac_sets_signal_and_coldest_settings.webp) |
| <a id="test_max_ac_off_restores_previous_settings"></a>`test_max_ac_off_restores_previous_settings`<br>FULL을 버튼으로 끄면 켜기 전 값인 22.0°C, 풍량 3으로 돌아갑니다. | 통과, 3.8초, [화면](../site/results/img/aaos/test_max_ac_off_restores_previous_settings.webp)<br>`HVAC_FAN_SPEED[0x1]=3`<br>`HVAC_TEMPERATURE_SET[0x1]=22.0`<br>`HVAC_TEMPERATURE_SET[0x4]=22.0` | 통과, 4.0초, [화면](../site/results/img/mock/test_max_ac_off_restores_previous_settings.webp) |
| <a id="test_max_ac_signal_is_shown_on_toggle"></a>`test_max_ac_signal_is_shown_on_toggle`<br>차량 쪽에서 최대 냉방을 켜고 끄면 화면의 FULL 토글도 따라 바뀝니다. | 통과, 3.0초, [화면](../site/results/img/aaos/test_max_ac_signal_is_shown_on_toggle.webp) | 통과, 2.9초, [화면](../site/results/img/mock/test_max_ac_signal_is_shown_on_toggle.webp) |
| <a id="test_manual_fan_releases_max_ac"></a>`test_manual_fan_releases_max_ac`<br>FULL 중에 풍량을 직접 내리면 최대 냉방이 풀립니다. 온도는 되돌리지 않고 방금 바꾼 값을 따릅니다. | 통과, 3.8초, [화면](../site/results/img/aaos/test_manual_fan_releases_max_ac.webp)<br>`HVAC_MAX_AC_ON[0x1]=0`<br>`HVAC_FAN_SPEED[0x1]=6`<br>`HVAC_TEMPERATURE_SET[0x1]=16.0` | 통과, 4.3초, [화면](../site/results/img/mock/test_manual_fan_releases_max_ac.webp) |
| <a id="test_turning_ac_off_releases_max_ac"></a>`test_turning_ac_off_releases_max_ac`<br>FULL 중에 A/C를 끄면 최대 냉방도 같이 꺼집니다. A/C 없이 최대 냉방만 켜져 있을 수는 없습니다. | 통과, 4.1초, [화면](../site/results/img/aaos/test_turning_ac_off_releases_max_ac.webp)<br>`HVAC_AC_ON[0x1]=0`<br>`HVAC_MAX_AC_ON[0x1]=0` | 통과, 4.3초, [화면](../site/results/img/mock/test_turning_ac_off_releases_max_ac.webp) |
| <a id="test_manual_fan_releases_auto"></a>`test_manual_fan_releases_auto`<br>AUTO 중에 풍량을 직접 바꾸면 AUTO가 풀리고 HVAC_AUTO_ON이 꺼집니다. | 통과, 4.2초, [화면](../site/results/img/aaos/test_manual_fan_releases_auto.webp)<br>`HVAC_FAN_SPEED[0x1]=4`<br>`HVAC_AUTO_ON[0x1]=0` | 통과, 4.3초, [화면](../site/results/img/mock/test_manual_fan_releases_auto.webp) |
| <a id="test_defrost_changes_only_its_window"></a>`test_defrost_changes_only_its_window` `[defrost_front-defrost_front-defrost_rear]`<br>앞 유리 김서림 제거를 누르면 앞 유리 신호만, 뒤를 누르면 뒤 유리 신호만 켜집니다. | 통과, 3.5초, [화면](../site/results/img/aaos/test_defrost_changes_only_its_window_defrost_front-defrost_front-defrost_rear.webp)<br>`HVAC_DEFROSTER[0x1]=1`<br>`HVAC_DEFROSTER[0x2]=0` | 통과, 4.2초, [화면](../site/results/img/mock/test_defrost_changes_only_its_window_defrost_front-defrost_front-defrost_rear.webp) |
| `test_defrost_changes_only_its_window` `[defrost_rear-defrost_rear-defrost_front]` | 통과, 3.6초, [화면](../site/results/img/aaos/test_defrost_changes_only_its_window_defrost_rear-defrost_rear-defrost_front.webp)<br>`HVAC_DEFROSTER[0x2]=1`<br>`HVAC_DEFROSTER[0x1]=0` | 통과, 3.7초, [화면](../site/results/img/mock/test_defrost_changes_only_its_window_defrost_rear-defrost_rear-defrost_front.webp) |
| <a id="test_seat_heat_cycles_levels_on_vehicle"></a>`test_seat_heat_cycles_levels_on_vehicle` `[driver]`<br>열선 버튼을 누를 때마다 꺼짐, 2단, 1단, 꺼짐 순서로 바뀝니다. 다른 좌석의 열선은 그대로입니다. | 통과, 3.7초, [화면](../site/results/img/aaos/test_seat_heat_cycles_levels_on_vehicle_driver.webp)<br>`HVAC_SEAT_TEMPERATURE[0x1]=0`<br>`HVAC_SEAT_TEMPERATURE[0x4]=0` | 통과, 4.4초, [화면](../site/results/img/mock/test_seat_heat_cycles_levels_on_vehicle_driver.webp) |
| `test_seat_heat_cycles_levels_on_vehicle` `[passenger]` | 통과, 4.1초, [화면](../site/results/img/aaos/test_seat_heat_cycles_levels_on_vehicle_passenger.webp)<br>`HVAC_SEAT_TEMPERATURE[0x4]=0`<br>`HVAC_SEAT_TEMPERATURE[0x1]=0` | 통과, 4.6초, [화면](../site/results/img/mock/test_seat_heat_cycles_levels_on_vehicle_passenger.webp) |
| <a id="test_seat_heat_signal_is_shown_everywhere"></a>`test_seat_heat_signal_is_shown_everywhere`<br>차량의 열선 단계가 공조 화면, 아래 바, 빠른 제어 세 곳에 같은 값으로 보입니다. | 통과, 3.7초, [화면](../site/results/img/aaos/test_seat_heat_signal_is_shown_everywhere.webp) | 통과, 4.0초, [화면](../site/results/img/mock/test_seat_heat_signal_is_shown_everywhere.webp) |
| <a id="test_bottom_bar_seat_heat_works_from_any_screen"></a>`test_bottom_bar_seat_heat_works_from_any_screen`<br>아래 바의 열선 버튼은 다른 앱을 보고 있을 때 눌러도 차량 신호를 바꿉니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_bottom_bar_seat_heat_works_from_any_screen.webp)<br>`HVAC_SEAT_TEMPERATURE[0x4]=2`<br>`HVAC_SEAT_TEMPERATURE[0x1]=0` | 통과, 3.4초, [화면](../site/results/img/mock/test_bottom_bar_seat_heat_works_from_any_screen.webp) |
| <a id="test_assistant_seat_heat_follows_speaker_zone"></a>`test_assistant_seat_heat_follows_speaker_zone`<br>조수석에서 AI 어시스턴트에 '열선 켜줘'라고 하면 조수석 열선 신호만 올라갑니다. | 통과, 4.3초, [화면](../site/results/img/aaos/test_assistant_seat_heat_follows_speaker_zone.webp)<br>`HVAC_SEAT_TEMPERATURE[0x4]=2`<br>`HVAC_SEAT_TEMPERATURE[0x1]=0` | 통과, 4.6초, [화면](../site/results/img/mock/test_assistant_seat_heat_follows_speaker_zone.webp) |
| <a id="test_door_lock_button_drives_every_door"></a>`test_door_lock_button_drives_every_door`<br>빠른 제어의 도어 버튼을 누르면 네 문의 DOOR_LOCK이 함께 바뀝니다. | 통과, 3.8초, [화면](../site/results/img/aaos/test_door_lock_button_drives_every_door.webp)<br>`DOOR_LOCK[0x4]=1`<br>`DOOR_LOCK[0x10]=1`<br>`DOOR_LOCK[0x40]=1` | 통과, 4.1초, [화면](../site/results/img/mock/test_door_lock_button_drives_every_door.webp) |
| <a id="test_door_lock_signal_is_shown"></a>`test_door_lock_signal_is_shown`<br>키나 도어 스위치로 차량 쪽에서 문이 열리면 화면의 도어 표시도 바뀝니다. | 통과, 2.8초, [화면](../site/results/img/aaos/test_door_lock_signal_is_shown.webp) | 통과, 2.7초, [화면](../site/results/img/mock/test_door_lock_signal_is_shown.webp) |
| <a id="test_energy_signals_are_shown_on_cluster"></a>`test_energy_signals_are_shown_on_cluster`<br>주행 가능 거리, 배터리, 외기 온도 신호가 주행 정보에 보입니다. 미터는 km로, Wh는 %로 바꿔 보여 줍니다. | 통과, 2.0초, [화면](../site/results/img/aaos/test_energy_signals_are_shown_on_cluster.webp) | 통과, 2.3초, [화면](../site/results/img/mock/test_energy_signals_are_shown_on_cluster.webp) |
| <a id="test_low_range_threshold"></a>`test_low_range_threshold` `[31.0-False]`<br>주행 가능 거리가 30 km 이하로 떨어지면 '충전 필요'와 충전소 안내 카드가 뜹니다. 31 km에서는 뜨지 않습니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_low_range_threshold_31.0-False.webp) | 통과, 1.9초, [화면](../site/results/img/mock/test_low_range_threshold_31.0-False.webp) |
| `test_low_range_threshold` `[30.0-True]` | 통과, 2.8초, [화면](../site/results/img/aaos/test_low_range_threshold_30.0-True.webp) | 통과, 2.0초, [화면](../site/results/img/mock/test_low_range_threshold_30.0-True.webp) |
| `test_low_range_threshold` `[29.0-True]` | 통과, 2.9초, [화면](../site/results/img/aaos/test_low_range_threshold_29.0-True.webp) | 통과, 1.9초, [화면](../site/results/img/mock/test_low_range_threshold_29.0-True.webp) |
| <a id="test_low_range_card_starts_guidance_to_nearest_charger"></a>`test_low_range_card_starts_guidance_to_nearest_charger`<br>주행 가능 거리가 부족해지면 충전소 카드가 뜨고, 누르면 가장 가까운 충전소로 안내를 시작합니다. 글자 검색이 막힌 주행 중에도 카드는 한 번에 누를 수 있어야 합니다. | 통과, 5.2초, [화면](../site/results/img/aaos/test_low_range_card_starts_guidance_to_nearest_charger.webp) | 통과, 3.7초, [화면](../site/results/img/mock/test_low_range_card_starts_guidance_to_nearest_charger.webp) |
| <a id="test_low_range_is_recorded_in_notifications"></a>`test_low_range_is_recorded_in_notifications`<br>주행 가능 거리 부족은 알림 센터에도 남습니다. 그때 화면을 보지 못했어도 나중에 확인할 수 있습니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_low_range_is_recorded_in_notifications.webp) | 통과, 3.1초, [화면](../site/results/img/mock/test_low_range_is_recorded_in_notifications.webp) |
| <a id="test_range_recovers_after_charging"></a>`test_range_recovers_after_charging`<br>충전해서 주행 가능 거리가 늘어나면 경고와 카드가 사라져야 합니다. | 통과, 3.6초, [화면](../site/results/img/aaos/test_range_recovers_after_charging.webp) | 통과, 2.2초, [화면](../site/results/img/mock/test_range_recovers_after_charging.webp) |
| <a id="test_range_follows_speed_unit_setting"></a>`test_range_follows_speed_unit_setting`<br>속도 단위를 mph로 바꾸면 주행 가능 거리도 마일로 보입니다. 320 km는 199 mi입니다. | 통과, 4.1초, [화면](../site/results/img/aaos/test_range_follows_speed_unit_setting.webp) | 통과, 4.4초, [화면](../site/results/img/mock/test_range_follows_speed_unit_setting.webp) |

## test_voice.py

음성 명령으로 알아들은 문장이 실제 기능으로 이어지는지 확인합니다. 온도 명령은 차량 신호까지 봅니다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_voice_sets_driver_temperature_on_vehicle"></a>`test_voice_sets_driver_temperature_on_vehicle`<br>'운전석 온도 24도로 맞춰줘'라고 하면 차량의 운전석 온도가 24.0°C가 됩니다. | 통과, 3.3초, [화면](../site/results/img/aaos/test_voice_sets_driver_temperature_on_vehicle.webp)<br>`HVAC_TEMPERATURE_SET[0x1]=24.0` | 통과, 3.6초, [화면](../site/results/img/mock/test_voice_sets_driver_temperature_on_vehicle.webp) |
| <a id="test_voice_turns_on_radio"></a>`test_voice_turns_on_radio`<br>'라디오 켜줘'라고 하면 라디오가 켜집니다. | 통과, 3.3초, [화면](../site/results/img/aaos/test_voice_turns_on_radio.webp) | 통과, 3.6초, [화면](../site/results/img/mock/test_voice_turns_on_radio.webp) |
| <a id="test_voice_starts_guidance_home"></a>`test_voice_starts_guidance_home`<br>'집으로 안내해줘'라고 하면 집까지 경로 안내가 시작됩니다. | 통과, 3.4초, [화면](../site/results/img/aaos/test_voice_starts_guidance_home.webp) | 통과, 3.7초, [화면](../site/results/img/mock/test_voice_starts_guidance_home.webp) |
| <a id="test_voice_panel_closes_after_command"></a>`test_voice_panel_closes_after_command`<br>명령을 처리하면 음성 패널이 닫혀 안내나 통화 화면을 가리지 않습니다. 6단계 회귀 테스트에서 찾은 결함이 다시 생기지 않는지 봅니다. | 통과, 3.1초, [화면](../site/results/img/aaos/test_voice_panel_closes_after_command.webp) | 통과, 3.6초, [화면](../site/results/img/mock/test_voice_panel_closes_after_command.webp) |
| <a id="test_voice_calls_contact"></a>`test_voice_calls_contact`<br>'엄마에게 전화해줘'라고 하면 엄마에게 전화를 걸고, 끊으면 통화 화면이 닫힙니다. | 통과, 3.5초, [화면](../site/results/img/aaos/test_voice_calls_contact.webp) | 통과, 4.0초, [화면](../site/results/img/mock/test_voice_calls_contact.webp) |
