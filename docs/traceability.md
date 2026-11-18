# 요구사항 추적표

[요구사항](requirements.md)마다 그것을 확인하는 테스트와 최신 결과를 이었습니다. 테스트 코드의 `@pytest.mark.req`를 읽어 `ivi-tests/tools/trace_report.py`가 만듭니다.
A-SPICE의 검증 단계에서 요구하는 요구사항과 시험 사이의 양방향 추적을 흉내 낸 것이고, 표준 인증이나 심사를 받은 것은 아닙니다.

| 항목 | 개수 |
|---|---|
| 요구사항 | 26개 |
| 테스트가 있는 요구사항 | 26개 |
| 테스트 함수 | 98개 |
| 요구사항이 없는 테스트 | 0개 |

결과 열은 parametrize 케이스까지 센 것입니다. 알려진 결함은 일부러 남겨 둔 결함이고, 건너뜀은 그 기기에서 의미가 없는 테스트입니다.

## 요구사항에서 테스트로

| ID | 요구사항 | 출처 | 테스트 | AAOS 에뮬레이터 | 태블릿 |
|---|---|---|---|---|---|
| SYS-01 | 앱은 기기에 맞는 차량 데이터(AAOS는 CarService, 그 밖의 기기는 Mock)에 연결하고, 권한이 없는 신호는 앱이 멈추지 않고 '값 없음'으로 보여 준다. | 기능 | `test_app_starts_with_vehicle_source_for_device`<br>`test_hvac_is_controllable`<br>`test_parked_on_start` | 3/3 통과 | 3/3 통과 |
| UI-01 | 화면 틀(아래 바, 분할 화면, 위젯, 알림 센터, 앱 목록, 이전 실행 앱)이 어느 화면에서든 동작한다. | 기능 | `test_bottom_bar_seat_heat_works_from_any_screen`<br>`test_bottom_bar_temperature_drives_vehicle`<br>`test_each_tab_opens`<br>`test_notifications_record_guidance_and_restriction`<br>`test_recent_app_slot`<br>`test_split_screen_toggle`<br>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>`test_utility_widget_pages` | 18/18 통과 | 18/18 통과 |
| DRIVE-01 | 속도와 기어 신호를 주행 정보에 바로 보여 준다. | 기능 | `test_api_signals_drive_the_screen`<br>`test_can_drive_frames_reach_screen`<br>`test_driving_signals_are_shown`<br>`test_gear_value_shows_reverse`<br>`test_lane_assist_indicator_follows_speed`<br>`test_mph_setting_converts_vehicle_speed`<br>`test_parked_on_start`<br>`test_trip_distance_follows_speed_signal` | 8/8 통과 | 8/8 통과 |
| DRIVE-02 | 주행 중에는 영상을 볼 수 없고, 차를 세우면 멈춘 자리부터 이어서 볼 수 있다. 음악은 주행 중에도 쓸 수 있다. | 운전자 주의 분산 | `test_media_stays_usable_while_driving`<br>`test_video_blocked_screen_follows_parking`<br>`test_video_button_locked_while_driving`<br>`test_video_is_blocked_while_driving`<br>`test_video_plays_when_parked`<br>`test_video_resumes_where_it_stopped` | 6/6 통과 | 6/6 통과 |
| DRIVE-03 | 주행 중에는 글자 입력(내비 검색, 키패드, 어시스턴트 입력)과 일부 차량 제어(사이드 미러 접기, 트렁크)를 막는다. | 운전자 주의 분산 | `test_driving_locks_keypad_and_limits_contacts`<br>`test_driving_locks_typing_and_refuses_mirror_fold`<br>`test_quick_control_mirror_locked_while_driving`<br>`test_search_locked_while_driving_but_favorites_work` | 4/4 통과 | 4/4 통과 |
| HVAC-01 | 운전석과 조수석 온도는 화면과 차량 신호가 같은 값을 가진다. 한쪽이 바뀌면 다른 쪽이 따라온다. | 기능 | `test_bottom_bar_temperature_drives_vehicle`<br>`test_button_changes_signal_by_one_step`<br>`test_climate_button_goes_out_on_can`<br>`test_hvac_is_controllable`<br>`test_seats_are_independent`<br>`test_signal_is_shown_on_climate_and_home`<br>`test_typed_command_sets_vehicle_temperature`<br>`test_voice_sets_driver_temperature_on_vehicle`<br>`test_zone_applies_command_to_speaking_seat` | 14/14 통과 | 14/14 통과 |
| HVAC-02 | 온도는 16.0~28.0°C 범위에서 0.5°C 단위로 바뀌고, 끝에 닿으면 그 방향 버튼이 꺼진다. | 기능 | `test_button_changes_signal_by_one_step`<br>`test_buttons_disabled_at_limits` | 6/6 통과 | 6/6 통과 |
| HVAC-03 | A/C, AUTO, 풍량은 모든 좌석 area에 함께 적용된다. 풍량을 직접 바꾸면 AUTO가 풀린다. | 기능 | `test_ac_signal_is_shown_on_climate_and_bottom_bar`<br>`test_ac_toggle_reaches_every_seat`<br>`test_fan_button_changes_signal_by_one`<br>`test_fan_buttons_disabled_at_limits`<br>`test_manual_fan_releases_auto` | 7/7 통과 | 7/7 통과 |
| HVAC-04 | 최대 냉방(FULL)을 켜면 최저 온도와 최대 풍량이 되고, 끄면 켜기 전 값으로 돌아간다. 다른 공조 값을 직접 바꾸면 최대 냉방이 풀린다. | 기능 | `test_manual_fan_releases_max_ac`<br>`test_max_ac_off_restores_previous_settings`<br>`test_max_ac_sets_signal_and_coldest_settings`<br>`test_max_ac_signal_is_shown_on_toggle`<br>`test_turning_ac_off_releases_max_ac` | 5/5 통과 | 5/5 통과 |
| HVAC-05 | 김서림 제거와 좌석 열선은 누른 유리, 그 좌석에만 적용되고, 화면 여러 곳에 같은 값으로 보인다. | 기능 | `test_assistant_seat_heat_follows_speaker_zone`<br>`test_bottom_bar_seat_heat_works_from_any_screen`<br>`test_defrost_changes_only_its_window`<br>`test_seat_heat_cycles_levels_on_vehicle`<br>`test_seat_heat_signal_is_shown_everywhere` | 7/7 통과 | 7/7 통과 |
| HVAC-06 | SYNC를 켜면 조수석 온도가 운전석을 따르고, 조수석을 직접 바꾸면 SYNC가 풀린다. | 기능 | `test_passenger_change_releases_sync`<br>`test_sync_mirrors_driver_temperature_to_passenger` | 2/2 통과 | 2/2 통과 |
| BODY-01 | 도어 버튼은 모든 문을 함께 잠그고 풀며, 차량 쪽 문 상태를 화면에 보여 준다. | 기능 | `test_can_battery_and_door_frames_reach_screen`<br>`test_door_lock_button_drives_every_door`<br>`test_door_lock_signal_is_shown` | 3/3 통과 | 3/3 통과 |
| ENERGY-01 | 주행 가능 거리, 배터리, 외기 온도를 화면 단위(km 또는 마일, %, °C)로 보여 준다. | 기능 | `test_energy_signals_are_shown_on_cluster`<br>`test_range_follows_speed_unit_setting` | 2/2 통과 | 2/2 통과 |
| ENERGY-02 | 주행 가능 거리가 30 km 이하면 경고와 충전소 안내를 띄우고 알림 센터에 남긴다. 충전해서 거리가 늘면 경고를 거둔다. | 기능 | `test_api_low_range_shows_charger_card`<br>`test_can_battery_and_door_frames_reach_screen`<br>`test_low_range_card_starts_guidance_to_nearest_charger`<br>`test_low_range_is_recorded_in_notifications`<br>`test_low_range_threshold`<br>`test_range_recovers_after_charging` | 8/8 통과 | 8/8 통과 |
| CAM-01 | 기어가 R이 되면 어느 화면에서든 후방 카메라를 띄우고, R에서 벗어나면 보던 화면으로 돌아간다. | 기능 | `test_camera_returns_to_previous_screen`<br>`test_gear_value_shows_reverse`<br>`test_reverse_gear_shows_camera` | 3/3 통과 | 3/3 통과 |
| CAM-02 | 후방 카메라 영상은 기어를 R로 바꾼 뒤 2.0초 안에 보여야 한다. | 법규 (FMVSS 111) | `test_rear_camera_appears_within_two_seconds` | 1/1 통과 | 1/1 통과 |
| NAV-01 | 목적지를 찾아 안내를 시작하고, 남은 거리는 차량 속도 신호를 따라 줄며, 도착하거나 끝내면 안내를 거둔다. | 기능 | `test_ambiguous_destination_offers_candidates`<br>`test_arrival`<br>`test_guidance_counts_down_with_vehicle_speed`<br>`test_low_range_card_starts_guidance_to_nearest_charger`<br>`test_parked_vehicle_does_not_advance_route`<br>`test_search_filters_destinations`<br>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>`test_voice_starts_guidance_home` | 8/8 통과 | 8/8 통과 |
| MEDIA-01 | 음악, 라디오, 통화는 한 번에 하나만 소리를 낸다. 통화가 끝나면 듣던 것이 다시 나온다. | 기능 | `test_call_pauses_radio_then_resumes`<br>`test_radio_and_media_play_one_at_a_time` | 2/2 통과 | 2/2 통과 |
| MEDIA-02 | 음악과 영상 재생, 라디오 조정과 프리셋, 전화 걸기가 동작한다. | 기능 | `test_am_band_uses_khz_steps`<br>`test_call_contact_shows_call_screen_and_recent`<br>`test_keypad_dial`<br>`test_media_stays_usable_while_driving`<br>`test_play_pause_toggles`<br>`test_power_on_plays_default_station`<br>`test_preset_save_and_recall`<br>`test_selecting_track_starts_it`<br>`test_tune_and_seek`<br>`test_video_next_clip`<br>`test_video_plays_when_parked` | 13/13 통과 | 13/13 통과 |
| VOICE-01 | 음성 명령과 AI 어시스턴트는 말한 사람의 좌석에 맞춰 차량 기능과 앱 기능을 실행한다. | 기능 | `test_ambiguous_destination_offers_candidates`<br>`test_assistant_seat_heat_follows_speaker_zone`<br>`test_multiple_commands_in_one_sentence`<br>`test_typed_command_sets_vehicle_temperature`<br>`test_voice_calls_contact`<br>`test_voice_panel_closes_after_command`<br>`test_voice_popup_and_assistant_share_history`<br>`test_voice_sets_driver_temperature_on_vehicle`<br>`test_voice_starts_guidance_home`<br>`test_voice_turns_on_radio`<br>`test_zone_applies_command_to_speaking_seat` | 11/11 통과 | 11/11 통과 |
| SET-01 | 설정과 라디오 프리셋은 앱을 다시 켜도 남고, 초기화하면 기본값으로 돌아간다. 속도 단위는 차량 정보 표시에 반영된다. | 기능 | `test_12_hour_clock_on_tablet`<br>`test_mph_setting_converts_vehicle_speed`<br>`test_preset_and_frequency_survive_app_restart`<br>`test_range_follows_speed_unit_setting`<br>`test_reset_restores_defaults`<br>`test_settings_survive_app_restart`<br>`test_volume_steps` | 6/7 통과, 건너뜀 1 | 7/7 통과 |
| NET-01 | 차량 네트워크(CAN)로 들어온 주행, 배터리, 도어 신호가 VHAL을 거쳐 화면에 보인다. | 통합 (모의 환경) | `test_can_battery_and_door_frames_reach_screen`<br>`test_can_drive_frames_reach_screen` | 2/2 통과 | 2/2 통과 |
| NET-02 | 화면에서 바꾼 공조 값이 CAN 프레임으로 나간다. | 통합 (모의 환경) | `test_climate_button_goes_out_on_can` | 1/1 통과 | 1/1 통과 |
| BENCH-01 | Test Bench API로 기기, 차량 신호, 실행 결과를 조회하고 신호를 넣을 수 있다. 잘못된 값은 거절하고 차량에 넣지 않는다. | 운영 | `test_api_low_range_shows_charger_card`<br>`test_api_rejects_invalid_value_and_leaves_vehicle_alone`<br>`test_api_signals_drive_the_screen` | 3/3 통과 | 3/3 통과 |
| BENCH-02 | 전원을 껐다 켜도 기기가 정해진 시간 안에 부팅되고, 앱과 공조 기본값이 돌아온다. | 운영 (모의 환경) | `test_power_cycle_brings_back_app_and_cabin_defaults` | 1/1 통과 | 0/1 통과, 건너뜀 1 |
| SPIKE-01 | AAOS 기본 SystemUI의 공조 바가 VHAL 신호와 이어지고, 속도와 기어가 주행 상태를 바꾼다. | 기술 검증 (1단계) | `test_driver_temp_up_is_not_covered_by_home`<br>`test_hvac_signal_is_shown_on_ui`<br>`test_hvac_ui_tap_changes_signal`<br>`test_speed_and_gear_change_driving_state` | 5/6 통과, 알려진 결함 1 | 0/6 통과, 건너뜀 6 |

## 테스트에서 요구사항으로

| 테스트 파일 | 테스트 수 | 요구사항 |
|---|---|---|
| `test_assistant.py` | 6개 | DRIVE-03, HVAC-01, NAV-01, VOICE-01 |
| `test_bench_api.py` | 3개 | BENCH-01, DRIVE-01, ENERGY-02 |
| `test_can_gateway.py` | 3개 | BODY-01, DRIVE-01, ENERGY-02, HVAC-01, NET-01, NET-02 |
| `test_climate.py` | 4개 | HVAC-01, HVAC-02 |
| `test_cockpit.py` | 10개 | DRIVE-01, DRIVE-03, HVAC-01, HVAC-06, UI-01 |
| `test_driving.py` | 7개 | DRIVE-01, DRIVE-02, MEDIA-02 |
| `test_media.py` | 3개 | DRIVE-02, MEDIA-02 |
| `test_navigation.py` | 6개 | DRIVE-03, NAV-01, UI-01 |
| `test_phone.py` | 4개 | DRIVE-03, MEDIA-01, MEDIA-02 |
| `test_power.py` | 1개 | BENCH-02 |
| `test_radio.py` | 6개 | MEDIA-01, MEDIA-02, SET-01 |
| `test_rear_camera.py` | 4개 | CAM-01, CAM-02, DRIVE-01 |
| `test_settings.py` | 5개 | DRIVE-01, SET-01 |
| `test_smoke.py` | 4개 | DRIVE-01, HVAC-01, SYS-01, UI-01 |
| `test_spike_aaos.py` | 4개 | SPIKE-01 |
| `test_vehicle_signals.py` | 23개 | BODY-01, ENERGY-01, ENERGY-02, HVAC-03, HVAC-04, HVAC-05, NAV-01, SET-01, UI-01, VOICE-01 |
| `test_voice.py` | 5개 | HVAC-01, NAV-01, VOICE-01 |
