# 요구사항 추적표

[요구사항](requirements.md)마다 그것을 확인하는 테스트와 최신 결과를 이었습니다. 테스트 코드의 `@pytest.mark.req`를 읽어 `ivi-tests/tools/trace_report.py`가 만듭니다.
A-SPICE가 요구하는 요구사항–시험 양방향 추적을 개인 프로젝트 규모로 적용해 본 것이고, 표준 인증이나 심사를 받은 것은 아닙니다.

| 항목 | 개수 |
|---|---|
| 요구사항 | 26개 |
| 테스트가 있는 요구사항 | 26개 |
| 테스트 함수 | 114개 |
| 요구사항이 없는 테스트 | 0개 |

'요구사항이 없는 테스트 0개', '테스트가 있는 요구사항 26개'는 요구사항 ID 연결이 빠지지 않았다는 수치입니다. 조건별 검증이 충분하다거나 표준(ISO 26262, A-SPICE)을 지켰다는 뜻은 아닙니다. 조건별로 어디까지 확인했는지는 아래 '복합 요구사항' 표에 있습니다.

결과 열은 결과 페이지에 실은 최신 실행이고, parametrize 케이스까지 센 것입니다. 알려진 결함은 플랫폼(AAOS SystemUI) 쪽 문제라 xfail로 걸어 둔 결함이고, 건너뜀은 그 기기에서 의미가 없는 테스트입니다. '결과 없는 테스트'는 그 실행 뒤에 더해서 결과 페이지에 아직 결과가 없는 테스트입니다.

## 요구사항에서 테스트로

| ID | 요구사항 | 출처 | 테스트 | AAOS 에뮬레이터 | 태블릿 | 갤럭시 폴드 |
|---|---|---|---|---|---|---|
| SYS-01 | 앱은 기기에 맞는 차량 데이터(AAOS는 CarService, 그 밖의 기기는 Mock)에 연결하고, 권한이 없는 신호는 앱이 멈추지 않고 '값 없음'으로 보여 줍니다. | 기능 | `test_app_starts_with_vehicle_source_for_device`<br>`test_hvac_is_controllable`<br>`test_parked_on_start`<br>`test_signal_without_permission_shows_no_value` | 4/4 통과 | 3/4 통과<br>건너뜀 1 | 3/4 통과<br>건너뜀 1 |
| UI-01 | 화면 틀(아래 바, 분할 화면, 위젯, 알림 센터, 앱 목록, 이전 실행 앱)이 어느 화면에서든 동작합니다. | 기능 | `test_bottom_bar_seat_heat_works_from_any_screen`<br>`test_bottom_bar_temperature_drives_vehicle`<br>`test_clearing_notifications_leaves_empty_panel`<br>`test_each_tab_opens`<br>`test_notifications_record_guidance_and_restriction`<br>`test_recent_app_slot`<br>`test_split_screen_toggle`<br>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>`test_utility_widget_pages` | 19/19 통과 | 19/19 통과 | 19/19 통과 |
| DRIVE-01 | 속도와 기어 신호를 주행 정보에 바로 보여 줍니다. | 기능 | `test_api_signals_drive_the_screen`<br>`test_can_drive_frames_reach_screen`<br>`test_driving_signals_are_shown`<br>`test_gear_value_shows_reverse`<br>`test_lane_assist_indicator_follows_speed`<br>`test_mph_setting_converts_vehicle_speed`<br>`test_parked_on_start`<br>`test_trip_distance_follows_speed_signal` | 8/8 통과 | 8/8 통과 | 8/8 통과 |
| DRIVE-02 | P 기어가 아니면(D·N·R로 멈춰 있어도) 영상을 볼 수 없고, P로 바꾸면 멈춘 자리부터 이어서 볼 수 있습니다. 음악은 주행 중에도 쓸 수 있습니다. | 운전자 주의 분산 | `test_media_stays_usable_while_driving`<br>`test_restrictions_follow_stop_and_go_timeline`<br>`test_stopped_in_gear_blocks_only_video`<br>`test_video_blocked_screen_follows_parking`<br>`test_video_button_locked_while_driving`<br>`test_video_is_blocked_while_driving`<br>`test_video_plays_when_parked`<br>`test_video_resumes_where_it_stopped`<br>`test_video_screen_is_blocked_while_stopped_in_drive` | 6/6 통과<br>결과 없는 테스트 3 | 6/6 통과<br>결과 없는 테스트 3 | 6/6 통과<br>결과 없는 테스트 3 |
| DRIVE-03 | 주행 중(P가 아니고 속도가 0보다 클 때)에는 글자 입력(내비 검색, 키패드, 어시스턴트 입력)과 일부 차량 제어(사이드 미러 접기, 트렁크)를 막습니다. P가 아닌 채 멈춰 있을 때(신호 대기)는 막지 않습니다. | 운전자 주의 분산 | `test_category_shortcut_works_while_driving`<br>`test_driving_locks_keypad_and_limits_contacts`<br>`test_driving_locks_typing_and_refuses_mirror_fold`<br>`test_folded_mirror_can_be_unfolded_while_driving`<br>`test_quick_control_mirror_locked_while_driving`<br>`test_restrictions_follow_stop_and_go_timeline`<br>`test_search_locked_while_driving_but_favorites_work`<br>`test_stopped_in_gear_blocks_only_video` | 7/7 통과<br>결과 없는 테스트 2 | 7/7 통과<br>결과 없는 테스트 2 | 7/7 통과<br>결과 없는 테스트 2 |
| HVAC-01 | 운전석과 조수석 온도는 화면과 차량 신호가 같은 값을 가집니다. 한쪽이 바뀌면 다른 쪽이 따라옵니다. | 기능 | `test_bottom_bar_temperature_drives_vehicle`<br>`test_button_changes_signal_by_one_step`<br>`test_climate_button_goes_out_on_can`<br>`test_hvac_is_controllable`<br>`test_seats_are_independent`<br>`test_signal_is_shown_on_climate_and_home`<br>`test_typed_command_sets_vehicle_temperature`<br>`test_voice_sets_driver_temperature_on_vehicle`<br>`test_zone_applies_command_to_speaking_seat` | 14/14 통과 | 14/14 통과 | 14/14 통과 |
| HVAC-02 | 온도는 16.0~28.0°C 범위에서 0.5°C 단위로 바뀌고, 끝에 닿으면 그 방향 버튼이 꺼집니다. 차량 쪽에서 범위 밖 값이나 0.5°C 단위가 아닌 값이 와도 앱은 멈추지 않고 그 값을 보여 주며, 범위 밖으로 더 가는 버튼은 꺼집니다. 버튼을 누르면 범위 안의 0.5°C 단위 값으로 맞춰 차량에 씁니다. | 기능 | `test_button_changes_signal_by_one_step`<br>`test_buttons_disabled_at_limits`<br>`test_off_grid_signal_steps_back_to_grid`<br>`test_out_of_range_signal_is_shown_safely`<br>`test_step_reaches_limit_and_disables` | 12/12 통과 | 12/12 통과 | 12/12 통과 |
| HVAC-03 | A/C, AUTO, 풍량은 모든 좌석 area에 함께 적용됩니다. 풍량을 직접 바꾸면 AUTO가 풀립니다. | 기능 | `test_ac_signal_is_shown_on_climate_and_bottom_bar`<br>`test_ac_toggle_reaches_every_seat`<br>`test_fan_button_changes_signal_by_one`<br>`test_fan_buttons_disabled_at_limits`<br>`test_manual_fan_releases_auto` | 7/7 통과 | 7/7 통과 | 7/7 통과 |
| HVAC-04 | 최대 냉방(FULL)을 켜면 최저 온도와 최대 풍량이 되고, 끄면 켜기 전 값으로 돌아갑니다. 다른 공조 값을 직접 바꾸면 최대 냉방이 풀립니다. | 기능 | `test_manual_fan_releases_max_ac`<br>`test_manual_temperature_releases_max_ac`<br>`test_max_ac_off_restores_previous_settings`<br>`test_max_ac_sets_signal_and_coldest_settings`<br>`test_max_ac_signal_is_shown_on_toggle`<br>`test_turning_ac_off_releases_max_ac`<br>`test_turning_auto_on_releases_max_ac` | 7/7 통과 | 7/7 통과 | 7/7 통과 |
| HVAC-05 | 김서림 제거와 좌석 열선은 누른 유리, 그 좌석에만 적용되고, 화면 여러 곳에 같은 값으로 보입니다. | 기능 | `test_assistant_seat_heat_follows_speaker_zone`<br>`test_bottom_bar_seat_heat_works_from_any_screen`<br>`test_defrost_changes_only_its_window`<br>`test_seat_heat_cycles_levels_on_vehicle`<br>`test_seat_heat_signal_is_shown_everywhere` | 7/7 통과 | 7/7 통과 | 7/7 통과 |
| HVAC-06 | SYNC를 켜면 조수석 온도가 운전석을 따르고, 조수석을 직접 바꾸면 SYNC가 풀립니다. | 기능 | `test_passenger_change_releases_sync`<br>`test_sync_mirrors_driver_temperature_to_passenger` | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| BODY-01 | 도어 버튼은 모든 문을 함께 잠그고 풀며, 차량 쪽 문 상태를 화면에 보여 줍니다. | 기능 | `test_can_battery_and_door_frames_reach_screen`<br>`test_door_lock_button_drives_every_door`<br>`test_door_lock_signal_is_shown` | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| ENERGY-01 | 주행 가능 거리, 배터리, 외기 온도를 화면 단위(km 또는 마일, %, °C)로 보여 줍니다. | 기능 | `test_energy_signals_are_shown_on_cluster`<br>`test_range_follows_speed_unit_setting`<br>`test_signal_without_permission_shows_no_value` | 3/3 통과 | 2/3 통과<br>건너뜀 1 | 2/3 통과<br>건너뜀 1 |
| ENERGY-02 | 주행 가능 거리가 30 km 이하면 경고와 충전소 안내를 띄우고 알림 센터에 남깁니다. 충전해서 거리가 늘면 경고를 거둡니다. | 기능 | `test_api_low_range_shows_charger_card`<br>`test_can_battery_and_door_frames_reach_screen`<br>`test_low_range_card_starts_guidance_to_nearest_charger`<br>`test_low_range_is_recorded_in_notifications`<br>`test_low_range_threshold`<br>`test_range_recovers_after_charging` | 8/8 통과 | 8/8 통과 | 8/8 통과 |
| CAM-01 | 기어가 R이 되면 어느 화면에서든 후방 카메라를 띄우고, R에서 벗어나면 보던 화면으로 돌아갑니다. | 기능 | `test_camera_returns_to_previous_screen`<br>`test_gear_value_shows_reverse`<br>`test_reverse_gear_shows_camera` | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| CAM-02 | 후방 카메라 화면은 기어를 R로 바꾼 뒤 2.0초 안에 보여야 합니다. FMVSS 111의 2초 기준을 빌렸고, 앱의 카메라 화면 요소가 뜰 때까지를 잽니다(adb 주입과 Appium 조회 시간 포함). 실제 카메라 영상이나 실차에서 잰 값은 아닙니다. | 법규 (FMVSS 111 기준) | `test_rear_camera_appears_within_two_seconds` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| NAV-01 | 목적지를 찾아 안내를 시작하고, 남은 거리는 차량 속도 신호를 따라 줄며, 도착하거나 끝내면 안내를 거둡니다. | 기능 | `test_ambiguous_destination_offers_candidates`<br>`test_arrival`<br>`test_cancel_preview_returns_to_search`<br>`test_category_shortcut_works_while_driving`<br>`test_guidance_counts_down_with_vehicle_speed`<br>`test_low_range_card_starts_guidance_to_nearest_charger`<br>`test_parked_vehicle_does_not_advance_route`<br>`test_search_filters_destinations`<br>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>`test_voice_starts_guidance_home` | 11/11 통과 | 11/11 통과 | 11/11 통과 |
| MEDIA-01 | 음악, 라디오, 통화는 한 번에 하나만 소리를 냅니다. 통화가 끝나면 듣던 것이 다시 나옵니다. | 기능 | `test_call_pauses_radio_then_resumes`<br>`test_radio_and_media_play_one_at_a_time` | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| MEDIA-02 | 음악과 영상 재생, 라디오 조정과 프리셋, 전화 걸기가 동작합니다. | 기능 | `test_am_band_uses_khz_steps`<br>`test_call_contact_shows_call_screen_and_recent`<br>`test_each_band_keeps_its_own_frequency`<br>`test_keypad_dial`<br>`test_keypad_limits_length_and_edits`<br>`test_media_stays_usable_while_driving`<br>`test_play_pause_toggles`<br>`test_power_on_plays_default_station`<br>`test_preset_save_and_recall`<br>`test_seek_wraps_around_band_ends`<br>`test_selecting_track_starts_it`<br>`test_tune_and_seek`<br>`test_video_next_clip`<br>`test_video_plays_when_parked` | 16/16 통과 | 16/16 통과 | 16/16 통과 |
| VOICE-01 | 음성 명령과 AI 어시스턴트는 말한 사람의 좌석에 맞춰 차량 기능과 앱 기능을 실행합니다. | 기능 | `test_ambiguous_destination_offers_candidates`<br>`test_assistant_seat_heat_follows_speaker_zone`<br>`test_multiple_commands_in_one_sentence`<br>`test_typed_command_sets_vehicle_temperature`<br>`test_voice_calls_contact`<br>`test_voice_panel_closes_after_command`<br>`test_voice_popup_and_assistant_share_history`<br>`test_voice_sets_driver_temperature_on_vehicle`<br>`test_voice_starts_guidance_home`<br>`test_voice_turns_on_radio`<br>`test_zone_applies_command_to_speaking_seat` | 11/11 통과 | 11/11 통과 | 11/11 통과 |
| SET-01 | 설정과 라디오 프리셋은 앱을 다시 켜도 남고, 초기화하면 기본값으로 돌아갑니다. 속도 단위는 차량 정보 표시에 반영됩니다. | 기능 | `test_12_hour_clock_on_tablet`<br>`test_mph_setting_converts_vehicle_speed`<br>`test_preset_and_frequency_survive_app_restart`<br>`test_range_follows_speed_unit_setting`<br>`test_reset_restores_defaults`<br>`test_settings_survive_app_restart`<br>`test_volume_steps` | 6/7 통과<br>건너뜀 1 | 7/7 통과 | 7/7 통과 |
| NET-01 | 차량 네트워크(CAN)로 들어온 주행, 배터리, 도어 신호가 VHAL을 거쳐 화면에 보입니다. | 통합 (모의 환경) | `test_can_battery_and_door_frames_reach_screen`<br>`test_can_drive_frames_reach_screen` | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| NET-02 | 화면에서 바꾼 공조 값이 CAN 프레임으로 나갑니다. | 통합 (모의 환경) | `test_climate_button_goes_out_on_can` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| BENCH-01 | Test Bench API로 기기, 차량 신호, 실행 결과를 조회하고 신호를 넣을 수 있습니다. 잘못된 값은 거절하고 차량에 넣지 않습니다. | 운영 | `test_api_low_range_shows_charger_card`<br>`test_api_rejects_invalid_value_and_leaves_vehicle_alone`<br>`test_api_signals_drive_the_screen` | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| BENCH-02 | 전원을 껐다 켜도 기기가 정해진 시간 안에 부팅되고, 앱과 공조 기본값이 돌아옵니다. | 운영 (모의 환경) | `test_power_cycle_brings_back_app_and_cabin_defaults` | 1/1 통과 | 0/1 통과<br>건너뜀 1 | 0/1 통과<br>건너뜀 1 |
| SPIKE-01 | AAOS 기본 SystemUI의 공조 바가 VHAL 신호와 이어지고, 속도와 기어가 주행 상태를 바꿉니다. | 기술 검증 (1단계) | `test_driver_temp_up_is_not_covered_by_home`<br>`test_hvac_signal_is_shown_on_ui`<br>`test_hvac_ui_tap_changes_signal`<br>`test_speed_and_gear_change_driving_state` | 5/6 통과<br>알려진 결함 1 | 0/6 통과<br>건너뜀 6 | 0/6 통과<br>건너뜀 6 |

## 복합 요구사항: 조건마다 확인하는 곳

조건이 여럿인 요구사항은 조건마다 어느 확인이 그 조건을 보는지 [요구사항](requirements.md#복합-요구사항-조건마다-확인하는-곳)에 적었습니다. 조건 36개 가운데 테스트가 없는 조건은 0개입니다.

| 조건 | 내용 | 테스트 | 그 조건을 보는 확인 | AAOS 에뮬레이터 | 태블릿 | 갤럭시 폴드 |
|---|---|---|---|---|---|---|
| SYS-01.1 | 기기에 맞는 차량 데이터에 연결합니다 (AAOS는 CarService, 태블릿은 Mock) | `test_app_starts_with_vehicle_source_for_device` | `assert app.source_badge() == device.vehicle.badge`, 연결 안 됨·오류 표시가 없습니다 | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| SYS-01.2 | 연결한 차량 값이 시작 화면에 맞게 보입니다 | `test_parked_on_start` | `wait_text("speed_value", "0")`, `assert home.gear() == "P"` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| SYS-01.3 | 권한이 있으면 공조를 제어할 수 있습니다 | `test_hvac_is_controllable` | `assert not climate.unavailable()` 뒤 화면 + 한 번이 차량 22.5°C로 | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| SYS-01.4 | 권한이 없는 신호는 앱이 멈추지 않고 '값 없음'으로 보여 줍니다 | `test_signal_without_permission_shows_no_value` | AAOS에서 `pm revoke`로 CAR_ENERGY를 뺀 뒤 앱을 새로 띄우고 `wait_visible("range_unavailable")`, 거리·배터리 표시가 없는지 봅니다. 권한이 있는 외기 온도(18.0°C)와 속도(50)는 그대로 보이고, 거리 12 km를 넣어도 경고와 충전소 카드가 뜨지 않는지 `stays`로 봅니다. 태블릿의 Mock 차량에는 권한이 없어 AAOS에서만 확인합니다 | 1/1 통과 | 0/1 통과<br>건너뜀 1 | 0/1 통과<br>건너뜀 1 |
| HVAC-02.1 | 버튼 한 번에 0.5°C 바뀝니다 | `test_button_changes_signal_by_one_step` | 차량 값 `wait_value(car.temperature(seat), 22.5)`(▼는 21.5)와 화면 `wait_temperature`를 따로 봅니다. 좌석 2 × 방향 2 | 4/4 통과 | 4/4 통과 | 4/4 통과 |
| HVAC-02.2 | 끝값(16.0, 28.0°C)에서는 그 방향 버튼이 꺼지고 반대쪽은 눌립니다 | `test_buttons_disabled_at_limits` | `wait_enabled("<좌석>_temp_down", False)`와 `assert climate.can_increase(seat)`. 28.0°C는 반대 | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| HVAC-02.3 | 버튼으로 끝값에 닿으면 그 버튼이 꺼지고, 꺼진 버튼을 눌러도 범위를 넘지 않습니다 | `test_step_reaches_limit_and_disables` | 16.5→16.0°C `wait_value`, `wait_enabled(False)`, 꺼진 버튼을 누른 뒤 1.5초 동안 `stays(car.temperature(seat) == 16.0)`. 28.0°C도 같습니다 | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| HVAC-02.4 | 차량 쪽 범위 밖 값(15.5, 28.5°C)을 화면에 보여 주고, 범위 밖으로 더 가는 버튼은 꺼집니다 | `test_out_of_range_signal_is_shown_safely` | `wait_temperature(seat, 15.5)`, `wait_enabled("driver_temp_down", False)`. 15.5°C를 그대로 보여 주는 것은 AAOS에서만 확인합니다(태블릿 Mock은 16.0°C로 자릅니다) | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| HVAC-02.5 | 범위 밖 값에서 버튼을 누르면 범위 안의 값을 차량에 씁니다 | `test_out_of_range_signal_is_shown_safely` | ▲ 뒤 `wait_value(car.temperature(seat), 16.0)`(AAOS), 16.5(태블릿) | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| HVAC-02.6 | 0.5°C 단위가 아닌 값(22.3°C)에서 버튼을 누르면 0.5°C 단위로 맞춰 씁니다 | `test_off_grid_signal_steps_back_to_grid` | `wait_value(car.temperature(seat), 22.5)`(▲), 22.0(▼). 이 확인에서 앱 결함(22.8°C를 씀)을 찾았습니다 | 2/2 통과 | 2/2 통과 | 2/2 통과 |
| HVAC-02.7 | 이상한 값이 와도 앱이 멈추지 않습니다 | `test_out_of_range_signal_is_shown_safely`, `test_off_grid_signal_steps_back_to_grid` | 값이 화면에 보이고 그 뒤 버튼이 동작하는지 봅니다. 테스트 도중 이 앱의 크래시(`FATAL EXCEPTION`, `Fatal signal`)나 ANR이 logcat에 남으면 화면 판정이 통과해도 그 테스트를 실패로 합니다(모든 E2E 공통, `ivi/crashes.py`) | 4/4 통과 | 4/4 통과 | 4/4 통과 |
| HVAC-04.1 | FULL을 켜면 전 좌석 최대 냉방, 최저 온도, 최대 풍량이 됩니다 | `test_max_ac_sets_signal_and_coldest_settings` | `wait_until(all(car.signal_all(Signal.MAX_AC)))`, `wait_signal(car, Signal.FAN, 7)`, 좌석마다 `wait_value(car.temperature(seat), 16.0)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.2 | 끄면 켜기 전 값(22.0°C, 풍량 3)으로 돌아갑니다 | `test_max_ac_off_restores_previous_settings` | `wait_signal(car, Signal.FAN, 3)`, 좌석마다 `wait_value(car.temperature(seat), 22.0)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.3 | 풍량을 직접 바꾸면 풀리고, 온도는 되돌리지 않습니다 | `test_manual_fan_releases_max_ac` | `wait_signal(car, Signal.MAX_AC, False)`, `wait_signal(car, Signal.FAN, 6)`, `assert car.temperature(Seat.DRIVER) == 16.0` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.4 | A/C를 끄면 최대 냉방도 꺼집니다 | `test_turning_ac_off_releases_max_ac` | `wait_signal(car, Signal.AC, False)`, `wait_signal(car, Signal.MAX_AC, False)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.5 | 온도를 직접 바꾸면 풀리고, 켜기 전 값으로 되돌리지 않습니다 | `test_manual_temperature_releases_max_ac` | FULL 뒤 운전석 + 한 번에 `wait_value(car.temperature(Seat.DRIVER), 16.5)`, 전 좌석 `MAX_AC` 꺼짐, `stays(풍량 7, 조수석 16.0°C)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.6 | 차량 쪽에서 바뀐 최대 냉방이 화면 토글에 보입니다 | `test_max_ac_signal_is_shown_on_toggle` | `wait_checked("max_ac", True)`, 끄면 `False` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| HVAC-04.7 | AUTO를 켜면 풀립니다 | `test_turning_auto_on_releases_max_ac` | `wait_signal(car, Signal.AUTO, True)`, 전 좌석 `MAX_AC` 꺼짐, 화면 토글 `max_ac` 꺼짐과 `auto` 켜짐 | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-02.1 | 주행 중에는 영상 버튼이 꺼지고 안내가 나옵니다 | `test_video_button_locked_while_driving` | `wait_enabled("open_video", False)`, `assert media.restricted_notice()` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-02.2 | 버튼을 거치지 않고 영상 화면을 열어도 주행 중에는 막힙니다 | `test_video_is_blocked_while_driving` | `wait_until(device.video_blocked(video))`, `assert not video.playing()` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-02.3 | P로 바꾸면 다시 볼 수 있습니다 | `test_video_blocked_screen_follows_parking`, `test_video_button_locked_while_driving`, `test_video_plays_when_parked` | 막힌 화면이 `wait_until(not device.video_blocked(video))` 뒤 `wait_visible("video_player")`, 영상 버튼 `wait_enabled("open_video", True)`, 정차 중 재생 시간이 흐릅니다 | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| DRIVE-02.4 | 멈춘 자리부터 이어집니다. 막힌 동안 재생 시간이 흐르지 않습니다 | `test_video_resumes_where_it_stopped` | `assert resumed >= before`(처음부터 다시 재생하지 않음), `assert resumed - before <= wall - 4`(막힌 5초 동안 흐르지 않음). 기기에 영상이 없으면 건너뛰는데, Release 게이트가 이 건너뜀을 막습니다 | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-02.5 | 주행 중에도 음악은 고를 수 있습니다 | `test_media_stays_usable_while_driving` | 주행 제한 표시(`restriction_banner`)가 뜬 상태에서 곡을 고르고 `wait_text("now_playing_title", title)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-02.6 | P가 아닌 기어(D, N)로 멈춰 있어도 영상 버튼과 영상 화면을 막습니다 | `test_stopped_in_gear_blocks_only_video`, `test_video_screen_is_blocked_while_stopped_in_drive` | `wait_value(car.ux_restrictions, Ux.NO_VIDEO)`(플랫폼 쪽), `wait_enabled("open_video", False)`, 바로 연 영상 화면은 `wait_until(device.video_blocked(video))` 뒤 P에서 `wait_visible("video_player")` | 결과 없음 | 결과 없음 | 결과 없음 |
| DRIVE-03.1 | 주행 중에는 내비 검색 입력을 막고, 즐겨찾기와 충전소·주차 분류로는 목적지를 고를 수 있습니다 | `test_search_locked_while_driving_but_favorites_work`, `test_category_shortcut_works_while_driving` | `wait_enabled("nav_search", False)`, 즐겨찾기로 `destination() == "집"`. 분류는 `wait_value(nav.results(), 가까운 순 두 곳)` 뒤 첫 곳으로 안내를 시작합니다 | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| DRIVE-03.2 | 주행 중에는 전화 키패드를 막고 연락처는 5개까지만 보여 줍니다 | `test_driving_locks_keypad_and_limits_contacts` | `wait_enabled("phone_key_1", False)`, `wait_value(len(phone.contact_names()), 5)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-03.3 | 주행 중에는 어시스턴트 글자 입력을 막고, 추천 명령의 사이드 미러 접기는 거절합니다 | `test_driving_locks_typing_and_refuses_mirror_fold` | `wait_enabled("assistant_input", False)`, 대답에 '주행 중', 빠른 제어의 미러는 '펼침' 그대로입니다 | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-03.4 | 주행 중에는 사이드 미러 접기와 트렁크를 막고, 도어 잠금은 쓸 수 있습니다 | `test_quick_control_mirror_locked_while_driving` | `wait_enabled("qc_mirror", False)`, `assert not qc.can_toggle("trunk")`, 도어 `toggle("door_lock") == "열림"` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-03.5 | 접어 둔 사이드 미러를 펴는 것은 주행 중에도 됩니다 | `test_folded_mirror_can_be_unfolded_while_driving` | 주행 중 `assert qc.can_toggle("mirror")`, `toggle("mirror") == "펼침"`, 편 뒤에는 `wait_enabled("qc_mirror", False)` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| DRIVE-03.6 | P가 아닌 채 멈춰 있을 때는 글자 입력, 키패드, 사이드 미러와 트렁크를 막지 않습니다 | `test_stopped_in_gear_blocks_only_video` | `assert nav.search_enabled()`, `assert phone.enabled("phone_key_1")`, `assert qc.can_toggle("mirror") and qc.can_toggle("trunk")`, 상단 배지 '정지 중 · 영상만 제한' | 결과 없음 | 결과 없음 | 결과 없음 |
| DRIVE-03.7 | 속도가 0과 0 초과를 오가면 제한이 그때마다 바뀌고, 그 상태에 머무는 동안 흔들리지 않습니다 | `test_restrictions_follow_stop_and_go_timeline` | P → D 정지 → 3 km/h → 정지 → 60 km/h → N 정지 → P. 단계마다 `wait_value(car.ux_restrictions, ux)`, `wait_enabled("nav_search", typing)`, 배지 문구, 머무는 2~3초 동안 `stays(...)` | 결과 없음 | 결과 없음 | 결과 없음 |
| ENERGY-02.1 | 30 km 이하에서 경고와 충전소 카드가 뜨고, 31 km에서는 뜨지 않습니다 | `test_low_range_threshold` | 31, 30, 29 km마다 `wait_value(cluster.low_range_warning(), 기대값)`, `assert app.visible("low_range_card") == 기대값` | 3/3 통과 | 3/3 통과 | 3/3 통과 |
| ENERGY-02.2 | 충전소 카드로 가장 가까운 충전소 안내를 시작합니다. 주행 중에도 누를 수 있습니다 | `test_low_range_card_starts_guidance_to_nearest_charger` | 주행 중 `assert app.text("low_range_charger").startswith("판교 급속 충전소")`, 누른 뒤 `wait_text("nav_dest_name", "판교 급속 충전소")` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| ENERGY-02.3 | 알림 센터에 남습니다 | `test_low_range_is_recorded_in_notifications` | `assert panel.titles()[0] == "주행 가능 거리 부족"` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| ENERGY-02.4 | 충전해서 거리가 늘면 경고와 카드를 거둡니다 | `test_range_recovers_after_charging` | `wait_visible("low_range_card", expected=False)`, `wait_until(not cluster.low_range_warning())` | 1/1 통과 | 1/1 통과 | 1/1 통과 |
| ENERGY-02.5 | Test Bench API와 모의 CAN으로 들어온 거리 값에도 같게 동작합니다 | `test_api_low_range_shows_charger_card`, `test_can_battery_and_door_frames_reach_screen` | 25 km를 넣은 뒤 `wait_until(cluster.low_range_warning)`. API 쪽은 카드도 `assert app.visible("low_range_card")` | 2/2 통과 | 2/2 통과 | 2/2 통과 |

## 테스트에서 요구사항으로

| 테스트 파일 | 테스트 수 | 요구사항 |
|---|---|---|
| `test_assistant.py` | 6개 | DRIVE-03, HVAC-01, NAV-01, VOICE-01 |
| `test_bench_api.py` | 3개 | BENCH-01, DRIVE-01, ENERGY-02 |
| `test_can_gateway.py` | 3개 | BODY-01, DRIVE-01, ENERGY-02, HVAC-01, NET-01, NET-02 |
| `test_climate.py` | 7개 | HVAC-01, HVAC-02 |
| `test_cockpit.py` | 12개 | DRIVE-01, DRIVE-03, HVAC-01, HVAC-06, UI-01 |
| `test_driving.py` | 10개 | DRIVE-01, DRIVE-02, DRIVE-03, MEDIA-02 |
| `test_media.py` | 3개 | DRIVE-02, MEDIA-02 |
| `test_navigation.py` | 8개 | DRIVE-03, NAV-01, UI-01 |
| `test_phone.py` | 5개 | DRIVE-03, MEDIA-01, MEDIA-02 |
| `test_power.py` | 1개 | BENCH-02 |
| `test_radio.py` | 8개 | MEDIA-01, MEDIA-02, SET-01 |
| `test_rear_camera.py` | 4개 | CAM-01, CAM-02, DRIVE-01 |
| `test_settings.py` | 5개 | DRIVE-01, SET-01 |
| `test_smoke.py` | 4개 | DRIVE-01, HVAC-01, SYS-01, UI-01 |
| `test_spike_aaos.py` | 4개 | SPIKE-01 |
| `test_vehicle_signals.py` | 26개 | BODY-01, ENERGY-01, ENERGY-02, HVAC-03, HVAC-04, HVAC-05, NAV-01, SET-01, SYS-01, UI-01, VOICE-01 |
| `test_voice.py` | 5개 | HVAC-01, NAV-01, VOICE-01 |
