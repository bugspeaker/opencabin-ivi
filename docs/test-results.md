# 테스트 결과

기기별 전체 E2E 실행 결과와 테스트마다 끝 화면입니다. `ivi-tests/tools/publish_results.py`가 실행 기록에서 만듭니다.
소개 사이트에서는 같은 내용을 화면 미리 보기와 함께 볼 수 있습니다 (`site/docs/test-results.html`).

| 기기 | 실행 | 결과 | 시간 |
|---|---|---|---|
| AAOS 에뮬레이터 (Car on x86_64 emulator) | 2026-11-18 10:18:54 | passed 111, skipped 1, xfailed 1 | 8분 4초 |
| 태블릿 (Mock) (DBY-W09) | 2026-11-18 10:36:28 | passed 107, skipped 6 | 8분 57초 |

## test_assistant.py

AI 어시스턴트 E2E (7단계): 말 → 실제 차량 신호까지 본다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_zone_applies_command_to_speaking_seat"></a>`test_zone_applies_command_to_speaking_seat`<br>좌석 인식: 조수석에서 '나 더워' → 조수석만 1°C 내려간다 (차량 신호 확인). | 통과 · 8.0초 · [화면](../site/results/img/aaos/test_zone_applies_command_to_speaking_seat.webp) | 통과 · 9.5초 · [화면](../site/results/img/mock/test_zone_applies_command_to_speaking_seat.webp) |
| <a id="test_typed_command_sets_vehicle_temperature"></a>`test_typed_command_sets_vehicle_temperature`<br>글자로 말하기: '운전석 25.5도로 맞춰줘' → 차량 운전석 25.5 (상위 → 하위). | 통과 · 3.9초 · [화면](../site/results/img/aaos/test_typed_command_sets_vehicle_temperature.webp) | 통과 · 4.9초 · [화면](../site/results/img/mock/test_typed_command_sets_vehicle_temperature.webp) |
| <a id="test_multiple_commands_in_one_sentence"></a>`test_multiple_commands_in_one_sentence`<br>한 문장에 두 명령: 에어컨 켜고 음악 틀어줘 → 두 동작 모두. | 통과 · 4.1초 · [화면](../site/results/img/aaos/test_multiple_commands_in_one_sentence.webp) | 통과 · 5.8초 · [화면](../site/results/img/mock/test_multiple_commands_in_one_sentence.webp) |
| <a id="test_ambiguous_destination_offers_candidates"></a>`test_ambiguous_destination_offers_candidates`<br>후보가 여럿이면 고르게 한다: '판교 가자' → 3곳 → 판교역을 고르면 안내가 시작된다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_ambiguous_destination_offers_candidates.webp) | 통과 · 4.9초 · [화면](../site/results/img/mock/test_ambiguous_destination_offers_candidates.webp) |
| <a id="test_driving_locks_typing_and_refuses_mirror_fold"></a>`test_driving_locks_typing_and_refuses_mirror_fold`<br>주행 중: 글자 입력은 막히고(칩은 된다), 사이드 미러 접기는 거절한다. | 통과 · 7.0초 · [화면](../site/results/img/aaos/test_driving_locks_typing_and_refuses_mirror_fold.webp) | 통과 · 6.9초 · [화면](../site/results/img/mock/test_driving_locks_typing_and_refuses_mirror_fold.webp) |
| <a id="test_voice_popup_and_assistant_share_history"></a>`test_voice_popup_and_assistant_share_history`<br>음성 팝업에서 한 말이 AI 어시스턴트 대화 내역에도 남는다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_voice_popup_and_assistant_share_history.webp) | 통과 · 4.2초 · [화면](../site/results/img/mock/test_voice_popup_and_assistant_share_history.webp) |

## test_climate.py

공조 E2E: 차량 신호 ↔ 앱 화면을 양방향으로 본다. 같은 테스트가 AAOS(VHAL)와 Mock 기기에서 돈다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_signal_is_shown_on_climate_and_home"></a>`test_signal_is_shown_on_climate_and_home` `[driver]`<br>하위 → 상위: 차량의 설정 온도가 바뀌면 공조 화면과 홈 요약이 같은 값을 보여 준다. | 통과 · 4.3초 · [화면](../site/results/img/aaos/test_signal_is_shown_on_climate_and_home_driver.webp) | 통과 · 3.8초 · [화면](../site/results/img/mock/test_signal_is_shown_on_climate_and_home_driver.webp) |
| `test_signal_is_shown_on_climate_and_home` `[passenger]` | 통과 · 4.1초 · [화면](../site/results/img/aaos/test_signal_is_shown_on_climate_and_home_passenger.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_signal_is_shown_on_climate_and_home_passenger.webp) |
| <a id="test_button_changes_signal_by_one_step"></a>`test_button_changes_signal_by_one_step` `[up-driver]`<br>상위 → 하위: 화면의 +/- 를 한 번 누르면 차량 값이 0.5°C 바뀌고 화면도 따라간다. | 통과 · 3.6초 · [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_up-driver.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_up-driver.webp) |
| `test_button_changes_signal_by_one_step` `[up-passenger]` | 통과 · 3.3초 · [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_up-passenger.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_up-passenger.webp) |
| `test_button_changes_signal_by_one_step` `[down-driver]` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_down-driver.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_down-driver.webp) |
| `test_button_changes_signal_by_one_step` `[down-passenger]` | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_button_changes_signal_by_one_step_down-passenger.webp) | 통과 · 3.7초 · [화면](../site/results/img/mock/test_button_changes_signal_by_one_step_down-passenger.webp) |
| <a id="test_buttons_disabled_at_limits"></a>`test_buttons_disabled_at_limits` `[driver]`<br>경계 값: 최저(16.0)에서 -, 최고(28.0)에서 + 가 비활성이고 반대쪽은 활성이다. | 통과 · 3.8초 · [화면](../site/results/img/aaos/test_buttons_disabled_at_limits_driver.webp) | 통과 · 3.3초 · [화면](../site/results/img/mock/test_buttons_disabled_at_limits_driver.webp) |
| `test_buttons_disabled_at_limits` `[passenger]` | 통과 · 3.9초 · [화면](../site/results/img/aaos/test_buttons_disabled_at_limits_passenger.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_buttons_disabled_at_limits_passenger.webp) |
| <a id="test_seats_are_independent"></a>`test_seats_are_independent`<br>한쪽 좌석을 바꿔도 다른 좌석 값은 그대로다 (area 혼동 방지). | 통과 · 3.7초 · [화면](../site/results/img/aaos/test_seats_are_independent.webp) | 통과 · 3.7초 · [화면](../site/results/img/mock/test_seats_are_independent.webp) |

## test_cockpit.py

화면 틀 E2E (7단계, Pleos Connect 구조): 아래 바 공조 · 동기화 · 주행 정보 · 분할 화면 · 빠른 제어 · 알림.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_bottom_bar_temperature_drives_vehicle"></a>`test_bottom_bar_temperature_drives_vehicle` `[driver]`<br>아래 바 ‹ › 는 어느 화면에서든 차량 온도를 바꾼다 (상위 → 하위), 차량 값이 바뀌면 아래 바도 따라간다 (하위 → 상위). | 통과 · 3.8초 · [화면](../site/results/img/aaos/test_bottom_bar_temperature_drives_vehicle_driver.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_bottom_bar_temperature_drives_vehicle_driver.webp) |
| `test_bottom_bar_temperature_drives_vehicle` `[passenger]` | 통과 · 3.8초 · [화면](../site/results/img/aaos/test_bottom_bar_temperature_drives_vehicle_passenger.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_bottom_bar_temperature_drives_vehicle_passenger.webp) |
| <a id="test_sync_mirrors_driver_temperature_to_passenger"></a>`test_sync_mirrors_driver_temperature_to_passenger`<br>SYNC: 켜면 조수석이 운전석 값으로 맞춰지고, 운전석을 바꾸면 조수석 차량 값도 같이 바뀐다. | 통과 · 4.5초 · [화면](../site/results/img/aaos/test_sync_mirrors_driver_temperature_to_passenger.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_sync_mirrors_driver_temperature_to_passenger.webp) |
| <a id="test_passenger_change_releases_sync"></a>`test_passenger_change_releases_sync`<br>동기화 중 조수석을 직접 바꾸면 동기화가 풀린다 (이후 운전석만 바뀐다). | 통과 · 4.6초 · [화면](../site/results/img/aaos/test_passenger_change_releases_sync.webp) | 통과 · 4.9초 · [화면](../site/results/img/mock/test_passenger_change_releases_sync.webp) |
| <a id="test_trip_distance_follows_speed_signal"></a>`test_trip_distance_follows_speed_signal`<br>현 주행 정보: 거리는 속도 신호로 늘고, 정차하면 멈춘다 (120 km/h ≈ 3초에 0.1 km). | 통과 · 7.6초 · [화면](../site/results/img/aaos/test_trip_distance_follows_speed_signal.webp) | 통과 · 7.0초 · [화면](../site/results/img/mock/test_trip_distance_follows_speed_signal.webp) |
| <a id="test_lane_assist_indicator_follows_speed"></a>`test_lane_assist_indicator_follows_speed`<br>운전자 보조 표시(화면 연출): D 에서 30 km/h 이상이면 작동, 그 아래면 대기. | 통과 · 3.7초 · [화면](../site/results/img/aaos/test_lane_assist_indicator_follows_speed.webp) | 통과 · 2.2초 · [화면](../site/results/img/mock/test_lane_assist_indicator_follows_speed.webp) |
| <a id="test_utility_widget_pages"></a>`test_utility_widget_pages` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_utility_widget_pages.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_utility_widget_pages.webp) |
| <a id="test_split_screen_toggle"></a>`test_split_screen_toggle`<br>홈: 분할(내비 + 오디오) ↔ 단일(내비만). 내비는 두 모드 모두에서 쓸 수 있다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_split_screen_toggle.webp) | 통과 · 4.5초 · [화면](../site/results/img/mock/test_split_screen_toggle.webp) |
| <a id="test_quick_control_mirror_locked_while_driving"></a>`test_quick_control_mirror_locked_while_driving`<br>빠른 제어: 주행 중에는 사이드 미러 접기 · 트렁크가 막히고, 도어 잠금은 된다. | 통과 · 6.4초 · [화면](../site/results/img/aaos/test_quick_control_mirror_locked_while_driving.webp) | 통과 · 5.5초 · [화면](../site/results/img/mock/test_quick_control_mirror_locked_while_driving.webp) |
| <a id="test_notifications_record_guidance_and_restriction"></a>`test_notifications_record_guidance_and_restriction`<br>알림 센터: 경로 안내 시작 · 주행 제한이 쌓이고, 열면 배지가 사라진다. | 통과 · 5.1초 · [화면](../site/results/img/aaos/test_notifications_record_guidance_and_restriction.webp) | 통과 · 5.3초 · [화면](../site/results/img/mock/test_notifications_record_guidance_and_restriction.webp) |
| <a id="test_recent_app_slot"></a>`test_recent_app_slot`<br>아래 바 '이전 실행 앱': 앱 목록에서 연 라디오가 다른 앱으로 가면 아래 바에 남아 바로 돌아갈 수 있다. | 통과 · 4.4초 · [화면](../site/results/img/aaos/test_recent_app_slot.webp) | 통과 · 4.6초 · [화면](../site/results/img/mock/test_recent_app_slot.webp) |

## test_driving.py

주행 상태 E2E: 속도·기어 신호 → 화면 표시, 주행 중 UX 제한(영상 차단).

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_driving_signals_are_shown"></a>`test_driving_signals_are_shown` | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_driving_signals_are_shown.webp) | 통과 · 3.3초 · [화면](../site/results/img/mock/test_driving_signals_are_shown.webp) |
| <a id="test_video_button_locked_while_driving"></a>`test_video_button_locked_while_driving` | 통과 · 4.7초 · [화면](../site/results/img/aaos/test_video_button_locked_while_driving.webp) | 통과 · 3.4초 · [화면](../site/results/img/mock/test_video_button_locked_while_driving.webp) |
| <a id="test_video_is_blocked_while_driving"></a>`test_video_is_blocked_while_driving`<br>버튼을 거치지 않고 영상 화면을 직접 열어도(다른 앱·알림에서 들어오는 경우) 주행 중에는 막힌다. | 통과 · 2.9초 · [화면](../site/results/img/aaos/test_video_is_blocked_while_driving.webp) | 통과 · 3.1초 · [화면](../site/results/img/mock/test_video_is_blocked_while_driving.webp) |
| <a id="test_video_plays_when_parked"></a>`test_video_plays_when_parked` | 통과 · 4.7초 · [화면](../site/results/img/aaos/test_video_plays_when_parked.webp) | 통과 · 4.1초 · [화면](../site/results/img/mock/test_video_plays_when_parked.webp) |
| <a id="test_video_blocked_screen_follows_parking"></a>`test_video_blocked_screen_follows_parking`<br>주행 중 차단된 영상은 정차하면 다시 쓸 수 있어야 한다 (차단 화면이 그대로 남으면 결함). | 통과 · 3.5초 · [화면](../site/results/img/aaos/test_video_blocked_screen_follows_parking.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_video_blocked_screen_follows_parking.webp) |

## test_media.py

미디어 화면 회귀: 차량 신호와 무관한 기본 기능.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_selecting_track_starts_it"></a>`test_selecting_track_starts_it` `[0]` | 통과 · 3.3초 · [화면](../site/results/img/aaos/test_selecting_track_starts_it_0.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_selecting_track_starts_it_0.webp) |
| `test_selecting_track_starts_it` `[2]` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_selecting_track_starts_it_2.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_selecting_track_starts_it_2.webp) |
| `test_selecting_track_starts_it` `[4]` | 통과 · 3.3초 · [화면](../site/results/img/aaos/test_selecting_track_starts_it_4.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_selecting_track_starts_it_4.webp) |
| <a id="test_play_pause_toggles"></a>`test_play_pause_toggles` | 통과 · 4.2초 · [화면](../site/results/img/aaos/test_play_pause_toggles.webp) | 통과 · 4.8초 · [화면](../site/results/img/mock/test_play_pause_toggles.webp) |
| <a id="test_media_stays_usable_while_driving"></a>`test_media_stays_usable_while_driving`<br>주행 중에도 음악 선택은 된다 (메인 화면은 distractionOptimized). 영상만 막혀야 한다. | 통과 · 4.3초 · [화면](../site/results/img/aaos/test_media_stays_usable_while_driving.webp) | 통과 · 3.7초 · [화면](../site/results/img/mock/test_media_stays_usable_while_driving.webp) |

## test_navigation.py

내비게이션 E2E: 경로 안내가 차량 속도 신호로 진행되고, 주행 중에는 글자 입력(검색)이 막힌다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_guidance_counts_down_with_vehicle_speed"></a>`test_guidance_counts_down_with_vehicle_speed`<br>하위 → 상위: 차량 속도 신호만큼 남은 거리가 줄어든다 (120 km/h ≈ 3초에 0.1 km). | 통과 · 8.5초 · [화면](../site/results/img/aaos/test_guidance_counts_down_with_vehicle_speed.webp) | 통과 · 8.9초 · [화면](../site/results/img/mock/test_guidance_counts_down_with_vehicle_speed.webp) |
| <a id="test_parked_vehicle_does_not_advance_route"></a>`test_parked_vehicle_does_not_advance_route`<br>정차 중에는 남은 거리가 그대로다 (시간이 아니라 속도 신호로 진행). | 통과 · 6.7초 · [화면](../site/results/img/aaos/test_parked_vehicle_does_not_advance_route.webp) | 통과 · 7.0초 · [화면](../site/results/img/mock/test_parked_vehicle_does_not_advance_route.webp) |
| <a id="test_search_locked_while_driving_but_favorites_work"></a>`test_search_locked_while_driving_but_favorites_work`<br>주행 중 UX 제한: 검색 입력은 막히고, 즐겨찾기로는 목적지를 고를 수 있다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_search_locked_while_driving_but_favorites_work.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_search_locked_while_driving_but_favorites_work.webp) |
| <a id="test_search_filters_destinations"></a>`test_search_filters_destinations` | 통과 · 2.6초 · [화면](../site/results/img/aaos/test_search_filters_destinations.webp) | 통과 · 2.9초 · [화면](../site/results/img/mock/test_search_filters_destinations.webp) |
| <a id="test_arrival"></a>`test_arrival` | 통과 · 8.7초 · [화면](../site/results/img/aaos/test_arrival.webp) | 통과 · 7.9초 · [화면](../site/results/img/mock/test_arrival.webp) |
| <a id="test_stop_guidance_returns_to_search_and_clears_cluster_route"></a>`test_stop_guidance_returns_to_search_and_clears_cluster_route`<br>7단계: 홈 위젯 대신 주행 정보(왼쪽)에 경로를 보여 준다. 다른 앱을 보고 있어도 보이고, 안내를 끝내면 사라진다. | 통과 · 4.9초 · [화면](../site/results/img/aaos/test_stop_guidance_returns_to_search_and_clears_cluster_route.webp) | 통과 · 5.9초 · [화면](../site/results/img/mock/test_stop_guidance_returns_to_search_and_clears_cluster_route.webp) |

## test_phone.py

전화 (블루투스 핸즈프리, 가상): 통화 화면 · 최근 통화 · 키패드 · 주행 중 제한 · 통화 중 오디오 일시 정지.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_call_contact_shows_call_screen_and_recent"></a>`test_call_contact_shows_call_screen_and_recent` | 통과 · 5.9초 · [화면](../site/results/img/aaos/test_call_contact_shows_call_screen_and_recent.webp) | 통과 · 6.1초 · [화면](../site/results/img/mock/test_call_contact_shows_call_screen_and_recent.webp) |
| <a id="test_keypad_dial"></a>`test_keypad_dial` | 통과 · 6.8초 · [화면](../site/results/img/aaos/test_keypad_dial.webp) | 통과 · 7.8초 · [화면](../site/results/img/mock/test_keypad_dial.webp) |
| <a id="test_driving_locks_keypad_and_limits_contacts"></a>`test_driving_locks_keypad_and_limits_contacts`<br>주행 중 UX 제한: 키패드는 막히고 연락처는 5개까지만 보인다. | 통과 · 5.5초 · [화면](../site/results/img/aaos/test_driving_locks_keypad_and_limits_contacts.webp) | 통과 · 5.4초 · [화면](../site/results/img/mock/test_driving_locks_keypad_and_limits_contacts.webp) |
| <a id="test_call_pauses_radio_then_resumes"></a>`test_call_pauses_radio_then_resumes` | 통과 · 6.2초 · [화면](../site/results/img/aaos/test_call_pauses_radio_then_resumes.webp) | 통과 · 7.7초 · [화면](../site/results/img/mock/test_call_pauses_radio_then_resumes.webp) |

## test_radio.py

라디오: 켜기 · 미세 조정 · 방송국 찾기 · 대역 · 프리셋(저장 유지) · 오디오 소스 하나만 재생.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_power_on_plays_default_station"></a>`test_power_on_plays_default_station` | 통과 · 3.5초 · [화면](../site/results/img/aaos/test_power_on_plays_default_station.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_power_on_plays_default_station.webp) |
| <a id="test_tune_and_seek"></a>`test_tune_and_seek` | 통과 · 5.9초 · [화면](../site/results/img/aaos/test_tune_and_seek.webp) | 통과 · 6.1초 · [화면](../site/results/img/mock/test_tune_and_seek.webp) |
| <a id="test_am_band_uses_khz_steps"></a>`test_am_band_uses_khz_steps` | 통과 · 4.3초 · [화면](../site/results/img/aaos/test_am_band_uses_khz_steps.webp) | 통과 · 4.7초 · [화면](../site/results/img/mock/test_am_band_uses_khz_steps.webp) |
| <a id="test_preset_save_and_recall"></a>`test_preset_save_and_recall` | 통과 · 5.9초 · [화면](../site/results/img/aaos/test_preset_save_and_recall.webp) | 통과 · 7.2초 · [화면](../site/results/img/mock/test_preset_save_and_recall.webp) |
| <a id="test_preset_and_frequency_survive_app_restart"></a>`test_preset_and_frequency_survive_app_restart`<br>저장 설정: 앱 프로세스를 끝내고 다시 켜도 프리셋과 마지막 주파수가 남는다. | 통과 · 10.3초 · [화면](../site/results/img/aaos/test_preset_and_frequency_survive_app_restart.webp) | 통과 · 10.5초 · [화면](../site/results/img/mock/test_preset_and_frequency_survive_app_restart.webp) |
| <a id="test_radio_and_media_play_one_at_a_time"></a>`test_radio_and_media_play_one_at_a_time`<br>오디오 소스는 하나: 음악 재생 중 라디오를 켜면 음악이 일시 정지된다. | 통과 · 6.0초 · [화면](../site/results/img/aaos/test_radio_and_media_play_one_at_a_time.webp) | 통과 · 6.5초 · [화면](../site/results/img/mock/test_radio_and_media_play_one_at_a_time.webp) |

## test_rear_camera.py

후방 카메라: 기어 신호가 R 이면 어떤 화면에서든 카메라가 뜨고, R 을 벗어나면 원래 화면으로 돌아온다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_reverse_gear_shows_camera"></a>`test_reverse_gear_shows_camera` | 통과 · 3.1초 · [화면](../site/results/img/aaos/test_reverse_gear_shows_camera.webp) | 통과 · 2.3초 · [화면](../site/results/img/mock/test_reverse_gear_shows_camera.webp) |
| <a id="test_camera_returns_to_previous_screen"></a>`test_camera_returns_to_previous_screen` | 통과 · 4.8초 · [화면](../site/results/img/aaos/test_camera_returns_to_previous_screen.webp) | 통과 · 4.1초 · [화면](../site/results/img/mock/test_camera_returns_to_previous_screen.webp) |
| <a id="test_gear_value_shows_reverse"></a>`test_gear_value_shows_reverse` | 통과 · 3.0초 · [화면](../site/results/img/aaos/test_gear_value_shows_reverse.webp) | 통과 · 2.7초 · [화면](../site/results/img/mock/test_gear_value_shows_reverse.webp) |

## test_settings.py

설정: 속도 단위(차량 신호 표시에 반영) · 볼륨 · 저장 유지 · 초기화 · 시계 형식.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_mph_setting_converts_vehicle_speed"></a>`test_mph_setting_converts_vehicle_speed`<br>설정 → 주행 정보: mph 로 바꾸면 차량 속도 50 km/h 가 31 mph 로 보인다. | 통과 · 4.9초 · [화면](../site/results/img/aaos/test_mph_setting_converts_vehicle_speed.webp) | 통과 · 5.0초 · [화면](../site/results/img/mock/test_mph_setting_converts_vehicle_speed.webp) |
| <a id="test_volume_steps"></a>`test_volume_steps` | 통과 · 4.9초 · [화면](../site/results/img/aaos/test_volume_steps.webp) | 통과 · 5.5초 · [화면](../site/results/img/mock/test_volume_steps.webp) |
| <a id="test_settings_survive_app_restart"></a>`test_settings_survive_app_restart` | 통과 · 10.7초 · [화면](../site/results/img/aaos/test_settings_survive_app_restart.webp) | 통과 · 10.8초 · [화면](../site/results/img/mock/test_settings_survive_app_restart.webp) |
| <a id="test_reset_restores_defaults"></a>`test_reset_restores_defaults` | 통과 · 6.3초 · [화면](../site/results/img/aaos/test_reset_restores_defaults.webp) | 통과 · 6.9초 · [화면](../site/results/img/mock/test_reset_restores_defaults.webp) |
| <a id="test_12_hour_clock_on_tablet"></a>`test_12_hour_clock_on_tablet`<br>시계는 시스템 바가 없는 태블릿(Mock)에서만 앱이 그린다. | 건너뜀 · 1.7초 · [화면](../site/results/img/aaos/test_12_hour_clock_on_tablet.webp) | 통과 · 4.5초 · [화면](../site/results/img/mock/test_12_hour_clock_on_tablet.webp) |

## test_smoke.py

Smoke: 빌드가 나오면 가장 먼저 도는 최소 확인. 실패하면 나머지 검증을 돌릴 의미가 없다.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_app_starts_with_vehicle_source_for_device"></a>`test_app_starts_with_vehicle_source_for_device`<br>앱이 뜨고, 기기에 맞는 차량 데이터 소스에 연결된다 (AAOS → CarService, 그 외 → Mock). | 통과 · 2.3초 · [화면](../site/results/img/aaos/test_app_starts_with_vehicle_source_for_device.webp) | 통과 · 2.1초 · [화면](../site/results/img/mock/test_app_starts_with_vehicle_source_for_device.webp) |
| <a id="test_parked_on_start"></a>`test_parked_on_start`<br>정차 상태로 시작하면 주행 제한 배지가 없고 속도 0, 기어 P 다. | 통과 · 3.6초 · [화면](../site/results/img/aaos/test_parked_on_start.webp) | 통과 · 2.7초 · [화면](../site/results/img/mock/test_parked_on_start.webp) |
| <a id="test_each_tab_opens"></a>`test_each_tab_opens` `[home]`<br>탭마다 화면이 열린다 (화면 객체의 wait_loaded 가 핵심 요소를 기다린다). | 통과 · 2.7초 · [화면](../site/results/img/aaos/test_each_tab_opens_home.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_home.webp) |
| `test_each_tab_opens` `[navigation]` | 통과 · 2.8초 · [화면](../site/results/img/aaos/test_each_tab_opens_navigation.webp) | 통과 · 2.6초 · [화면](../site/results/img/mock/test_each_tab_opens_navigation.webp) |
| `test_each_tab_opens` `[radio]` | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_each_tab_opens_radio.webp) | 통과 · 3.3초 · [화면](../site/results/img/mock/test_each_tab_opens_radio.webp) |
| `test_each_tab_opens` `[media]` | 통과 · 2.4초 · [화면](../site/results/img/aaos/test_each_tab_opens_media.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_media.webp) |
| `test_each_tab_opens` `[phone]` | 통과 · 2.4초 · [화면](../site/results/img/aaos/test_each_tab_opens_phone.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_phone.webp) |
| `test_each_tab_opens` `[climate]` | 통과 · 2.6초 · [화면](../site/results/img/aaos/test_each_tab_opens_climate.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_climate.webp) |
| `test_each_tab_opens` `[settings]` | 통과 · 3.1초 · [화면](../site/results/img/aaos/test_each_tab_opens_settings.webp) | 통과 · 3.3초 · [화면](../site/results/img/mock/test_each_tab_opens_settings.webp) |
| `test_each_tab_opens` `[assistant]` | 통과 · 2.3초 · [화면](../site/results/img/aaos/test_each_tab_opens_assistant.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_assistant.webp) |
| `test_each_tab_opens` `[vehicle_controls]` | 통과 · 2.4초 · [화면](../site/results/img/aaos/test_each_tab_opens_vehicle_controls.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_vehicle_controls.webp) |
| `test_each_tab_opens` `[apps]` | 통과 · 2.4초 · [화면](../site/results/img/aaos/test_each_tab_opens_apps.webp) | 통과 · 2.5초 · [화면](../site/results/img/mock/test_each_tab_opens_apps.webp) |
| <a id="test_hvac_is_controllable"></a>`test_hvac_is_controllable`<br>공조를 제어할 수 있다. AAOS 에서 실패하면 priv-app 설치(CONTROL_CAR_CLIMATE)부터 의심한다. | 통과 · 2.5초 · [화면](../site/results/img/aaos/test_hvac_is_controllable.webp) | 통과 · 2.8초 · [화면](../site/results/img/mock/test_hvac_is_controllable.webp) |

## test_spike_aaos.py

1단계 기술 검증 (spike).

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_hvac_signal_is_shown_on_ui"></a>`test_hvac_signal_is_shown_on_ui` `[25.0]`<br>하위 → 상위: 운전석 설정 온도를 property 로 바꾸면 하단 HVAC 바 표시가 따라 바뀐다. | 통과 · 1.9초 · [화면](../site/results/img/aaos/test_hvac_signal_is_shown_on_ui_25.0.webp) | 건너뜀 · 0.0초 |
| `test_hvac_signal_is_shown_on_ui` `[20.0]` | 통과 · 1.5초 · [화면](../site/results/img/aaos/test_hvac_signal_is_shown_on_ui_20.0.webp) | 건너뜀 · 0.0초 |
| <a id="test_hvac_ui_tap_changes_signal"></a>`test_hvac_ui_tap_changes_signal` `[driver-hvac_decrease_button--0.5]`<br>상위 → 하위: 화면의 온도 ▲/▼ 를 한 번 누르면 실제 property 값이 한 단계(0.5°C) 바뀐다. | 통과 · 2.5초 · [화면](../site/results/img/aaos/test_hvac_ui_tap_changes_signal_driver-hvac_decrease_button--0.5.webp) | 건너뜀 · 0.0초 |
| `test_hvac_ui_tap_changes_signal` `[passenger-hvac_increase_button-0.5]` | 통과 · 2.3초 · [화면](../site/results/img/aaos/test_hvac_ui_tap_changes_signal_passenger-hvac_increase_button-0.5.webp) | 건너뜀 · 0.0초 |
| <a id="test_driver_temp_up_is_not_covered_by_home"></a>`test_driver_temp_up_is_not_covered_by_home`<br>버튼 영역이 겹치지 않는지 본다. 겹치면 사용자가 ▲ 를 눌러도 온도가 안 바뀐다 (1단계에서 발견). | 알려진 결함 · 0.7초 · [화면](../site/results/img/aaos/test_driver_temp_up_is_not_covered_by_home.webp) | 건너뜀 · 0.0초 |
| <a id="test_speed_and_gear_change_driving_state"></a>`test_speed_and_gear_change_driving_state`<br>속도·기어를 VHAL 에 넣으면 CarService 의 주행 상태가 바뀐다 (주행 중 UX 제한의 입력). | 통과 · 1.0초 | 건너뜀 · 0.0초 |

## test_vehicle_signals.py

8단계 차량 신호 E2E: 공조 부가 기능 · 좌석 열선 · 도어 잠금 · 주행 가능 거리 · 배터리 · 외기 온도.

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_ac_toggle_reaches_every_seat"></a>`test_ac_toggle_reaches_every_seat`<br>상위 → 하위: A/C 를 끄면 전 좌석 area 의 HVAC_AC_ON 이 꺼진다 (운전석만 꺼지면 결함). | 통과 · 3.9초 · [화면](../site/results/img/aaos/test_ac_toggle_reaches_every_seat.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_ac_toggle_reaches_every_seat.webp) |
| <a id="test_ac_signal_is_shown_on_climate_and_bottom_bar"></a>`test_ac_signal_is_shown_on_climate_and_bottom_bar`<br>하위 → 상위: 차량이 A/C 를 끄면 공조 화면의 토글이 꺼진다. 다시 켜면 켜진다. | 통과 · 2.8초 · [화면](../site/results/img/aaos/test_ac_signal_is_shown_on_climate_and_bottom_bar.webp) | 통과 · 3.3초 · [화면](../site/results/img/mock/test_ac_signal_is_shown_on_climate_and_bottom_bar.webp) |
| <a id="test_fan_button_changes_signal_by_one"></a>`test_fan_button_changes_signal_by_one` `[up-4]`<br>상위 → 하위: 풍량 +/- 한 번에 HVAC_FAN_SPEED 가 한 단계 바뀌고 화면 숫자도 따라간다. | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_fan_button_changes_signal_by_one_up-4.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_fan_button_changes_signal_by_one_up-4.webp) |
| `test_fan_button_changes_signal_by_one` `[down-2]` | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_fan_button_changes_signal_by_one_down-2.webp) | 통과 · 3.4초 · [화면](../site/results/img/mock/test_fan_button_changes_signal_by_one_down-2.webp) |
| <a id="test_fan_buttons_disabled_at_limits"></a>`test_fan_buttons_disabled_at_limits` `[1-climate_fan_down]`<br>경계 값: 최저(1)에서 -, 최고(7)에서 + 가 눌리지 않고 신호도 범위를 벗어나지 않는다. | 통과 · 3.3초 · [화면](../site/results/img/aaos/test_fan_buttons_disabled_at_limits_1-climate_fan_down.webp) | 통과 · 3.1초 · [화면](../site/results/img/mock/test_fan_buttons_disabled_at_limits_1-climate_fan_down.webp) |
| `test_fan_buttons_disabled_at_limits` `[7-climate_fan_up]` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_fan_buttons_disabled_at_limits_7-climate_fan_up.webp) | 통과 · 3.2초 · [화면](../site/results/img/mock/test_fan_buttons_disabled_at_limits_7-climate_fan_up.webp) |
| <a id="test_max_ac_sets_signal_and_coldest_settings"></a>`test_max_ac_sets_signal_and_coldest_settings`<br>상위 → 하위: FULL(최대 냉방)을 켜면 전 좌석 HVAC_MAX_AC_ON 이 켜지고, 온도는 최저 · 풍량은 최대 · AUTO 는 꺼진다. | 통과 · 4.5초 · [화면](../site/results/img/aaos/test_max_ac_sets_signal_and_coldest_settings.webp) | 통과 · 4.3초 · [화면](../site/results/img/mock/test_max_ac_sets_signal_and_coldest_settings.webp) |
| <a id="test_max_ac_off_restores_previous_settings"></a>`test_max_ac_off_restores_previous_settings`<br>FULL 을 버튼으로 끄면 켜기 전 값(22.0°C, 풍량 3)으로 돌아간다. | 통과 · 4.1초 · [화면](../site/results/img/aaos/test_max_ac_off_restores_previous_settings.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_max_ac_off_restores_previous_settings.webp) |
| <a id="test_max_ac_signal_is_shown_on_toggle"></a>`test_max_ac_signal_is_shown_on_toggle`<br>하위 → 상위: 차량이 최대 냉방을 켜고 끄면 FULL 토글이 따라간다. | 통과 · 2.7초 · [화면](../site/results/img/aaos/test_max_ac_signal_is_shown_on_toggle.webp) | 통과 · 2.9초 · [화면](../site/results/img/mock/test_max_ac_signal_is_shown_on_toggle.webp) |
| <a id="test_manual_fan_releases_max_ac"></a>`test_manual_fan_releases_max_ac`<br>앱 규칙: FULL 중에 풍량을 직접 내리면 최대 냉방이 풀린다. 이때 온도는 되돌리지 않는다 (방금 바꾼 값이 우선). | 통과 · 6.0초 · [화면](../site/results/img/aaos/test_manual_fan_releases_max_ac.webp) | 통과 · 4.4초 · [화면](../site/results/img/mock/test_manual_fan_releases_max_ac.webp) |
| <a id="test_turning_ac_off_releases_max_ac"></a>`test_turning_ac_off_releases_max_ac`<br>앱 규칙: FULL 중에 A/C 를 끄면 최대 냉방도 꺼진다 (A/C 없이 최대 냉방일 수 없다). | 통과 · 4.5초 · [화면](../site/results/img/aaos/test_turning_ac_off_releases_max_ac.webp) | 통과 · 4.3초 · [화면](../site/results/img/mock/test_turning_ac_off_releases_max_ac.webp) |
| <a id="test_manual_fan_releases_auto"></a>`test_manual_fan_releases_auto`<br>앱 규칙: AUTO 중에 풍량을 직접 바꾸면 AUTO 가 풀린다 (HVAC_AUTO_ON = false). | 통과 · 4.2초 · [화면](../site/results/img/aaos/test_manual_fan_releases_auto.webp) | 통과 · 4.4초 · [화면](../site/results/img/mock/test_manual_fan_releases_auto.webp) |
| <a id="test_defrost_changes_only_its_window"></a>`test_defrost_changes_only_its_window` `[defrost_front-defrost_front-defrost_rear]`<br>상위 → 하위: 앞(뒤) 김서림 제거는 그 유리의 HVAC_DEFROSTER 만 켠다 (area 혼동 방지). | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_defrost_changes_only_its_window_defrost_front-defrost_front-defrost_rear.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_defrost_changes_only_its_window_defrost_front-defrost_front-defrost_rear.webp) |
| `test_defrost_changes_only_its_window` `[defrost_rear-defrost_rear-defrost_front]` | 통과 · 3.5초 · [화면](../site/results/img/aaos/test_defrost_changes_only_its_window_defrost_rear-defrost_rear-defrost_front.webp) | 통과 · 3.7초 · [화면](../site/results/img/mock/test_defrost_changes_only_its_window_defrost_rear-defrost_rear-defrost_front.webp) |
| <a id="test_seat_heat_cycles_levels_on_vehicle"></a>`test_seat_heat_cycles_levels_on_vehicle` `[driver]`<br>상위 → 하위: 열선 버튼을 누를 때마다 꺼짐 → 2단 → 1단 → 꺼짐. 다른 좌석은 그대로다. | 통과 · 4.2초 · [화면](../site/results/img/aaos/test_seat_heat_cycles_levels_on_vehicle_driver.webp) | 통과 · 4.3초 · [화면](../site/results/img/mock/test_seat_heat_cycles_levels_on_vehicle_driver.webp) |
| `test_seat_heat_cycles_levels_on_vehicle` `[passenger]` | 통과 · 4.5초 · [화면](../site/results/img/aaos/test_seat_heat_cycles_levels_on_vehicle_passenger.webp) | 통과 · 4.7초 · [화면](../site/results/img/mock/test_seat_heat_cycles_levels_on_vehicle_passenger.webp) |
| <a id="test_seat_heat_signal_is_shown_everywhere"></a>`test_seat_heat_signal_is_shown_everywhere`<br>하위 → 상위: 차량의 열선 단계가 공조 화면 · 아래 바 · 빠른 제어 세 곳에 같은 값으로 보인다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_seat_heat_signal_is_shown_everywhere.webp) | 통과 · 4.2초 · [화면](../site/results/img/mock/test_seat_heat_signal_is_shown_everywhere.webp) |
| <a id="test_bottom_bar_seat_heat_works_from_any_screen"></a>`test_bottom_bar_seat_heat_works_from_any_screen`<br>아래 바 열선 버튼은 다른 앱을 보고 있어도 차량 신호를 바꾼다. | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_bottom_bar_seat_heat_works_from_any_screen.webp) | 통과 · 3.5초 · [화면](../site/results/img/mock/test_bottom_bar_seat_heat_works_from_any_screen.webp) |
| <a id="test_assistant_seat_heat_follows_speaker_zone"></a>`test_assistant_seat_heat_follows_speaker_zone`<br>AI 어시스턴트 → 차량 신호: 조수석에서 '열선 켜줘' 는 조수석 HVAC_SEAT_TEMPERATURE 만 올린다. | 통과 · 4.6초 · [화면](../site/results/img/aaos/test_assistant_seat_heat_follows_speaker_zone.webp) | 통과 · 4.7초 · [화면](../site/results/img/mock/test_assistant_seat_heat_follows_speaker_zone.webp) |
| <a id="test_door_lock_button_drives_every_door"></a>`test_door_lock_button_drives_every_door`<br>상위 → 하위: 빠른 제어의 도어 버튼은 전 도어의 DOOR_LOCK 을 같이 바꾼다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_door_lock_button_drives_every_door.webp) | 통과 · 4.2초 · [화면](../site/results/img/mock/test_door_lock_button_drives_every_door.webp) |
| <a id="test_door_lock_signal_is_shown"></a>`test_door_lock_signal_is_shown`<br>하위 → 상위: 차량에서 문이 열리면(키·도어 스위치) 화면 표시가 따라 바뀐다. | 통과 · 2.6초 · [화면](../site/results/img/aaos/test_door_lock_signal_is_shown.webp) | 통과 · 2.7초 · [화면](../site/results/img/mock/test_door_lock_signal_is_shown.webp) |
| <a id="test_energy_signals_are_shown_on_cluster"></a>`test_energy_signals_are_shown_on_cluster`<br>하위 → 상위: 주행 가능 거리 · 배터리 · 외기 온도 신호가 주행 정보에 보인다 (단위 변환: m → km, Wh → %). | 통과 · 3.1초 · [화면](../site/results/img/aaos/test_energy_signals_are_shown_on_cluster.webp) | 통과 · 2.3초 · [화면](../site/results/img/mock/test_energy_signals_are_shown_on_cluster.webp) |
| <a id="test_low_range_threshold"></a>`test_low_range_threshold` `[31.0-False]`<br>경계 값: 30 km 이하면 '충전 필요' 와 충전소 안내 카드가 뜬다. 31 km 는 뜨지 않는다. | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_low_range_threshold_31.0-False.webp) | 통과 · 2.0초 · [화면](../site/results/img/mock/test_low_range_threshold_31.0-False.webp) |
| `test_low_range_threshold` `[30.0-True]` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_low_range_threshold_30.0-True.webp) | 통과 · 2.0초 · [화면](../site/results/img/mock/test_low_range_threshold_30.0-True.webp) |
| `test_low_range_threshold` `[29.0-True]` | 통과 · 3.4초 · [화면](../site/results/img/aaos/test_low_range_threshold_29.0-True.webp) | 통과 · 2.2초 · [화면](../site/results/img/mock/test_low_range_threshold_29.0-True.webp) |
| <a id="test_low_range_card_starts_guidance_to_nearest_charger"></a>`test_low_range_card_starts_guidance_to_nearest_charger`<br>신호 → 화면 → 동작: 주행 가능 거리가 부족해지면 카드가 뜨고, 누르면 가장 가까운 충전소로 안내한다. 주행 중(글자 검색이 잠긴 상태)에도 한 번 눌러 쓸 수 있어야 한다. | 통과 · 4.0초 · [화면](../site/results/img/aaos/test_low_range_card_starts_guidance_to_nearest_charger.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_low_range_card_starts_guidance_to_nearest_charger.webp) |
| <a id="test_low_range_is_recorded_in_notifications"></a>`test_low_range_is_recorded_in_notifications`<br>주행 가능 거리 부족은 알림 센터에도 남는다 (화면을 보지 않았어도 나중에 확인할 수 있게). | 통과 · 3.9초 · [화면](../site/results/img/aaos/test_low_range_is_recorded_in_notifications.webp) | 통과 · 3.2초 · [화면](../site/results/img/mock/test_low_range_is_recorded_in_notifications.webp) |
| <a id="test_range_recovers_after_charging"></a>`test_range_recovers_after_charging`<br>충전해서 거리가 늘면 경고와 카드가 사라진다 (남아 있으면 결함). | 통과 · 4.9초 · [화면](../site/results/img/aaos/test_range_recovers_after_charging.webp) | 통과 · 2.4초 · [화면](../site/results/img/mock/test_range_recovers_after_charging.webp) |
| <a id="test_range_follows_speed_unit_setting"></a>`test_range_follows_speed_unit_setting`<br>설정의 속도 단위(mph)를 따르면 주행 가능 거리도 마일로 보인다 (320 km = 199 mi). | 통과 · 4.3초 · [화면](../site/results/img/aaos/test_range_follows_speed_unit_setting.webp) | 통과 · 4.3초 · [화면](../site/results/img/mock/test_range_follows_speed_unit_setting.webp) |

## test_voice.py

음성 명령: 인식된 문장이 실제 기능으로 이어지는지 본다. 온도 명령은 차량 신호까지 확인한다 (E2E).

| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| <a id="test_voice_sets_driver_temperature_on_vehicle"></a>`test_voice_sets_driver_temperature_on_vehicle` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_voice_sets_driver_temperature_on_vehicle.webp) | 통과 · 4.2초 · [화면](../site/results/img/mock/test_voice_sets_driver_temperature_on_vehicle.webp) |
| <a id="test_voice_turns_on_radio"></a>`test_voice_turns_on_radio` | 통과 · 3.5초 · [화면](../site/results/img/aaos/test_voice_turns_on_radio.webp) | 통과 · 3.6초 · [화면](../site/results/img/mock/test_voice_turns_on_radio.webp) |
| <a id="test_voice_starts_guidance_home"></a>`test_voice_starts_guidance_home` | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_voice_starts_guidance_home.webp) | 통과 · 3.8초 · [화면](../site/results/img/mock/test_voice_starts_guidance_home.webp) |
| <a id="test_voice_panel_closes_after_command"></a>`test_voice_panel_closes_after_command`<br>명령을 처리하면 패널이 닫혀 안내·통화 화면을 가리지 않는다 (6단계 회귀에서 찾은 결함의 회귀 테스트). | 통과 · 3.2초 · [화면](../site/results/img/aaos/test_voice_panel_closes_after_command.webp) | 통과 · 3.9초 · [화면](../site/results/img/mock/test_voice_panel_closes_after_command.webp) |
| <a id="test_voice_calls_contact"></a>`test_voice_calls_contact` | 통과 · 3.6초 · [화면](../site/results/img/aaos/test_voice_calls_contact.webp) | 통과 · 4.2초 · [화면](../site/results/img/mock/test_voice_calls_contact.webp) |
