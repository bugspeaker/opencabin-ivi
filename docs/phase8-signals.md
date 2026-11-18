# 8단계 화면 상태를 차량 신호로: 공조 · 도어 · 주행 가능 거리 E2E

작성 2026-11-16. 7단계를 검토해 보니 새로 넣은 차량 기능 대부분이 화면 안에서만 바뀌고 차량 신호까지 가지 않았다.
이 프로젝트는 UI 조작부터 차량 신호(CarProperty/VHAL)까지 확인하는 것이 목적이라, 화면 상태였던 것을 신호로 바꾸고 양방향 테스트를 붙였다.

여기서 '차량 신호'는 AAOS 에뮬레이터의 CarService·VHAL이다. 실제 차량에 연결한 것이 아니다.
앱은 양산 앱과 같은 API(`CarPropertyManager`)로 읽고 쓰고, 테스트는 adb로 VHAL에 값을 넣고(Property Injection) CarService로 읽는다.

## 1. 연결한 신호

| 기능 | VHAL property | area | 앱 | 필요한 권한 |
|---|---|---|---|---|
| A/C | `HVAC_AC_ON` | 좌석 5개 | 읽기 + 쓰기 (전 좌석) | `CONTROL_CAR_CLIMATE` (priv-app) |
| AUTO | `HVAC_AUTO_ON` | 좌석 5개 | 읽기 + 쓰기 (전 좌석) | 〃 |
| 풍량 1~7 | `HVAC_FAN_SPEED` | 좌석 5개 | 읽기 + 쓰기 (전 좌석) | 〃 |
| 김서림 제거 앞/뒤 | `HVAC_DEFROSTER` | 창 2개 | 읽기 + 쓰기 (그 유리만) | 〃 |
| 좌석 열선 0~2단 | `HVAC_SEAT_TEMPERATURE` | 좌석별 | 읽기 + 쓰기 (그 좌석만) | 〃 |
| 도어 잠금 | `DOOR_LOCK` | 문 4개 | 읽기 + 쓰기 (전 도어) | `CONTROL_CAR_DOORS` (priv-app), 새로 추가 |
| 주행 가능 거리 | `RANGE_REMAINING` (m) | 전역 | 읽기 | `CAR_ENERGY` (dangerous), 새로 추가 |
| 배터리 잔량 | `EV_BATTERY_LEVEL` ÷ `INFO_EV_BATTERY_CAPACITY` (Wh → %) | 전역 | 읽기 | `CAR_ENERGY`, `CAR_INFO` |
| 외기 온도 | `ENV_OUTSIDE_TEMPERATURE` (°C) | 전역 | 읽기 | `CAR_EXTERIOR_ENVIRONMENT` |

- 7단계까지 연결돼 있던 것: 속도, 기어, 좌석 온도, 주행 중 UX 제한.
- 아직 화면 상태로 남은 것: 사이드 미러 접기, 트렁크, 차일드 락, 실내등, 전조등. 에뮬레이터 VHAL에 맞는 property가 없거나(미러 접기·트렁크)
  이번 범위에서 뺐다. 운전자 보조 표시와 주변 차량은 여전히 연출이다.
- area 구성은 차마다 다르므로 앱은 하드코딩하지 않고 `CarPropertyConfig.areaIds`에서 읽어 쓴다.
- 권한이 없는 신호는 구독이 실패하고 화면에 '값 없음'으로 남는다 (도어 '제어 불가', '주행 가능 거리 정보 없음'). 앱은 죽지 않는다.

## 2. 화면에서 달라진 것

| 주행 가능 거리 부족 (신호: 22 km · 8 % · -3 °C) | 전 좌석 공조 (화면 → 신호) |
|---|---|
| ![low range](images/p8-lowrange.png) | ![climate](images/p8-climate.png) |

- 주행 정보: 배터리 잔량 · 주행 가능 거리 줄, 아래 줄에 외기 온도. 속도 단위가 mph면 거리는 마일로.
- 주행 가능 거리 부족 (30 km 이하): 주행 정보가 주황색 + '충전 필요', 내비 지도 위에 가까운 충전소 안내 카드, 알림 센터에 기록.
  카드를 누르면 바로 안내를 시작한다. 주행 중(글자 검색 잠김)에도 한 번 눌러 쓸 수 있다.
- 공조: A/C · AUTO · 풍량(1~7, 에뮬레이터 config 범위) · 김서림이 신호. 풍량을 직접 바꾸면 AUTO가 풀린다(앱 규칙).
- 좌석 열선: 누를 때마다 꺼짐 → 2단 → 1단 → 꺼짐. 공조 화면 · 아래 바 · 빠른 제어 세 곳이 같은 신호를 본다.
- 도어 잠금: 빠른 제어의 도어 버튼이 전 도어 `DOOR_LOCK`을 쓴다.
- AI 어시스턴트: "에어컨 켜줘", "열선 켜줘"가 이제 차량 신호까지 간다 (말한 좌석의 열선만).

## 3. 테스트 설계

### 3-1) 어댑터: `car.set_signal()` / `car.signal()`

테스트는 신호 이름과 화면 단위(km, %, °C, 단계)만 쓴다. 기기 차이와 단위 변환은 어댑터(`ivi/vehicle.py`)가 맡는다.

| | AAOS (`AaosVehicle`) | 태블릿 (`MockVehicle`) |
|---|---|---|
| 넣기 | VHAL에 직접: `dumpsys <VHAL> --set <prop> -i/-f <값> -a <area>` | `am broadcast … mock.SET --ez/--ei/--ef` |
| 읽기 | CarService: `cmd car_service get-property-value` | `am broadcast … mock.GET` |
| 변환 | km → m, % → Wh(용량 대비), bool → 0/1 | 없음 |
| area | '전 좌석' 신호는 5개, 도어는 4개 area 모두 | 값 하나 |

- `car.signal_all(이름)`은 area별 값을 돌려준다. 이것으로 "A/C를 끄면 전 좌석이 꺼진다", "도어 버튼이 4개 문 모두를 잠근다"를 확인한다.
  운전석 area만 쓰는 구현은 화면만 봐서는 통과하지만 이 확인에서 걸린다.

### 3-2) 테스트마다 기준 값으로 (테스트 격리)

차량 신호는 앱을 다시 띄워도 남는다. 앞 테스트가 문을 열어 두면 다음 테스트의 "누르면 열림"이 거꾸로 된다.
그래서 `app` 픽스처의 `prepare()`가 테스트마다 신호 11개를 기준 값(`CABIN_DEFAULTS`)으로 되돌린다.

- AAOS에서 이 초기화는 `--set` 26번(11개 신호 × area)이다. 하나씩 보내면 테스트마다 adb 왕복이 26번이라
  adb shell 한 번에 묶어 보낸다 (`set_signals`). 26개가 모두 들어갔는지 세고, 모자라면 통째로 한 번 더 시도하고 기록한다(4단계의 VHAL 재시도 규칙과 같다).
- 결과: 테스트 수가 84 → 108개로 늘었는데 전체 시간은 5분 47초 → 6분 40초 (테스트당 4.1초 → 3.7초).

### 3-3) 토글 상태를 색이 아니라 `checked`로

A/C · AUTO · 김서림 토글은 글자가 바뀌지 않고 색만 바뀐다. 색은 자동화가 읽기 어렵다.
앱에서 `Modifier.toggleable(role = Switch)`로 켜짐/꺼짐을 접근성 정보로 내보내고, 화면 객체는 `checked` 속성을 읽는다 (설정 화면 스위치와 같은 방식).
접근성(TalkBack)에도 같은 정보가 간다.

### 3-4) 테스트 목록 (`tests/test_vehicle_signals.py`, 24개)

테스트 설명을 누르면 기기별 결과와 끝 화면을 볼 수 있다 ([테스트 결과](test-results.md)).

| 분류 | 테스트 | 방향 |
|---|---|---|
| sanity | [A/C를 끄면 전 좌석 area가 꺼진다](test-results.md#test_ac_toggle_reaches_every_seat) | 화면 → 신호 |
| sanity | [차량이 A/C를 끄고 켜면 토글이 따라간다](test-results.md#test_ac_signal_is_shown_on_climate_and_bottom_bar) | 신호 → 화면 |
| sanity | [풍량 +/- 한 번에 신호가 한 단계 (2건)](test-results.md#test_fan_button_changes_signal_by_one) | 화면 → 신호 |
| regression | [풍량 경계 값 1 · 7에서 버튼 비활성, 신호가 범위를 안 벗어남 (2건)](test-results.md#test_fan_buttons_disabled_at_limits) | 양방향 |
| regression | [AUTO 중 풍량을 바꾸면 `HVAC_AUTO_ON`이 꺼진다](test-results.md#test_manual_fan_releases_auto) | 화면 → 신호 2개 |
| sanity | [앞/뒤 김서림은 그 유리의 신호만 켠다 (2건)](test-results.md#test_defrost_changes_only_its_window) | 양방향, area 혼동 방지 |
| sanity | [열선 꺼짐 → 2 → 1 → 꺼짐, 다른 좌석은 그대로 (좌석 2건)](test-results.md#test_seat_heat_cycles_levels_on_vehicle) | 화면 → 신호 |
| sanity | [열선 신호가 공조 화면 · 아래 바 · 빠른 제어에 같은 값으로](test-results.md#test_seat_heat_signal_is_shown_everywhere) | 신호 → 화면 3곳 |
| regression | [아래 바 열선은 다른 앱을 보고 있어도 신호를 바꾼다](test-results.md#test_bottom_bar_seat_heat_works_from_any_screen) | 화면 → 신호 |
| regression | [조수석에서 "열선 켜줘" → 조수석 신호만](test-results.md#test_assistant_seat_heat_follows_speaker_zone) | 말 → 신호 |
| sanity | [도어 버튼이 전 도어를 잠그고 푼다](test-results.md#test_door_lock_button_drives_every_door) | 화면 → 신호 (4개 area) |
| sanity | [차량에서 문이 열리면 표시가 바뀐다](test-results.md#test_door_lock_signal_is_shown) | 신호 → 화면 |
| sanity | [주행 가능 거리 · 배터리 · 외기 온도가 주행 정보에 (단위 변환 포함)](test-results.md#test_energy_signals_are_shown_on_cluster) | 신호 → 화면 |
| sanity | [경계 값 31 / 30 / 29 km에서 경고와 카드 (3건)](test-results.md#test_low_range_threshold) | 신호 → 화면 |
| sanity | [주행 중 거리 부족 → 카드 → 가까운 충전소 안내 시작](test-results.md#test_low_range_card_starts_guidance_to_nearest_charger) | 신호 → 화면 → 동작 |
| regression | [거리 부족이 알림 센터에 남는다](test-results.md#test_low_range_is_recorded_in_notifications) | 신호 → 화면 |
| regression | [충전하면 경고와 카드가 사라진다](test-results.md#test_range_recovers_after_charging) | 신호 → 화면 |
| regression | [속도 단위 mph면 거리도 마일 (320 km = 199 mi)](test-results.md#test_range_follows_speed_unit_setting) | 설정 × 신호 |

프레임워크 단위 테스트 7개 추가 (기기 없이): area 5개에 한 번의 shell 호출, km·% ↔ m·Wh 변환, 묶음 재시도와 실패 메시지, Mock의 타입별 extra, 기준 값 초기화가 11개를 모두 넣는지.

## 4. 진행 중 잡은 것

### 4-1) 도어 잠금은 권한 목록까지 바꿔야 한다
- `CONTROL_CAR_DOORS`는 `signature|privileged` 권한이다. 매니페스트에 적는 것만으로는 안 되고,
  `/system/etc/permissions`의 priv-app 허용 목록(`privapp-permissions-dev.opencabin.ivi.xml`)에 있어야 한다.
- 그래서 이번에는 `adb install -r`이 아니라 `privileged/install_priv_app.py`로 다시 넣고 재부팅했다. 설치 후 `dumpsys package`로 확인:
  `CONTROL_CAR_DOORS: granted=true`, `CAR_ENERGY: granted=true`(운전자 사용자 10).
- `CAR_ENERGY`는 dangerous 권한이라 권한 창이 뜬다. 창이 뜨면 테스트가 앱 화면을 못 보므로 설치 스크립트가 `pm grant`로 미리 준다.

### 4-2) 테스트 쪽 경쟁 조건 1건 (내가 만든 것)
- 증상: 전체 실행에서 `test_range_recovers_after_charging`이 `battery_percent() == 75`에서 실패. 혼자 돌리면 통과.
- 원인: 주행 가능 거리와 배터리는 서로 다른 신호라 따로 도착한다. 거리(카드 사라짐)를 기다린 뒤 배터리를 바로 `assert` 했다.
- 해결: 배터리도 조건 대기(`wait_until`)로. 같은 모양이던 외기 온도 확인도 고쳤다. 고정 `sleep`은 쓰지 않았다.

## 5. 결과

| 항목 | 결과 |
|---|---|
| 앱 빌드 | Kotlin 경고 0 |
| 앱 단위 테스트 (`CabinAssistantTest`) | 17 passed |
| 프레임워크 단위 테스트 (`pytest unit`) | 33 passed (26 → 33) |
| AAOS 에뮬레이터 전체 E2E (108개) | 106 passed, 1 skipped, 1 xfailed, gate pass, 앱 재실행 0, VHAL 재시도 0 (6분 40초) |
| 화웨이 태블릿 (Mock) 전체 E2E (108개) | 102 passed, 6 skipped (AAOS 전용), gate pass, 앱 재실행 0 (7분 6초) |
| 두 기기 병렬 (`run_bench.py --reruns 1`) | 두 기기 모두 gate pass, flaky 0, 재실행 0, VHAL 재시도 0. 7분 20초 (차례로 돌리면 약 14분 28초, 2.0배) |

- E2E 84 → 108개. 새 24개는 모두 화면과 신호를 양쪽에서 보고, 같은 테스트가 AAOS(VHAL)와 태블릿(Mock) 양쪽에서 통과한다.
- 태블릿은 이 날 처음에 adb `unauthorized`였다 (adb 서버를 다시 켠 뒤 기기에서 USB 디버깅 승인이 필요). USB 디버깅 승인, 설치 승인, 실행 순서로 진행했다.
- 반복 안정성(같은 묶음 여러 번)은 이번에 1회만 봤다. 7단계의 2회 반복에서 한 번 흔들린 `test_video_blocked_screen_follows_parking`은 이번 에뮬레이터 전체 실행 2회(단독 1 + 병렬 1)에서는 재현되지 않았다 (원인은 아직 확인하지 못했다).

## 6. 42dot Test Automation Engineer, IVI System

| 요구 역량 | 이 단계에서 보여 주는 것 |
|---|---|
| AAOS IVI 주요 서비스(HVAC, 차량 설정, 클러스터 연동, 미디어) 검증 | HVAC 6종 신호, 도어, 클러스터(주행 정보)에 차량 신호 3종 |
| UI 상호작용과 CarProperty/VHAL을 아우르는 E2E 설계 | 24개 모두 양방향. area 단위 판정(전 좌석 · 전 도어 · 그 유리만) |
| ADB · shell · CarPropertyManager로 Property Injection | `dumpsys VHAL --set` 묶음 주입, CarService로 읽기, 앱은 CarPropertyManager |
| Flaky 최소화, 피드백 루프 단축 | 테스트마다 기준 값 초기화(격리), 주입 26번을 왕복 1번으로, 경쟁 조건은 조건 대기로 |
| Smoke / Sanity / Regression 범위 | 새 테스트 24개를 sanity 16 · regression 8로 나눔 (parametrize 포함) |

## 7. 8단계 이후에 더한 것 (2026-11-16)

### 7-1) 최대 냉방 (화면 버튼 FULL)

공조 화면 A/C 옆에 FULL 버튼을 넣었다. 차량 신호는 `HVAC_MAX_AC_ON`이고, 에뮬레이터 VHAL에는 좌석 area 5개로 들어 있다 (`cmd car_service get-carpropertyconfig 0x15200506`으로 확인).

![FULL 켠 공조 화면](images/p9-climate-full.png)

| 동작 | 결과 |
|---|---|
| FULL 켬 | 전 좌석 `HVAC_MAX_AC_ON` 켜짐, A/C 켜짐, 온도 16.0°C, 풍량 7, AUTO 꺼짐 |
| FULL을 버튼으로 끔 | 켜기 전 온도, 풍량, A/C, AUTO 값으로 되돌림 |
| FULL 중에 온도나 풍량을 직접 바꿈, A/C를 끔, AUTO를 켬 | 최대 냉방만 꺼짐. 값은 되돌리지 않는다 (방금 바꾼 값을 따른다) |
| 차량 쪽에서 신호가 바뀜 | FULL 토글이 따라간다 |

- 켜기 전 값은 화면 틀 상태(`CockpitState.beforeMaxAc`)에 둔다. 앱을 다시 띄우면 사라지므로, 그 뒤에 끄면 신호만 꺼지고 값은 그대로다.
- 테스트 5개 추가 (`test_vehicle_signals.py`):
  [켜면 전 좌석 신호와 온도·풍량·AUTO](test-results.md#test_max_ac_sets_signal_and_coldest_settings),
  [끄면 복원](test-results.md#test_max_ac_off_restores_previous_settings),
  [신호가 바뀌면 토글](test-results.md#test_max_ac_signal_is_shown_on_toggle),
  [풍량을 내리면 해제](test-results.md#test_manual_fan_releases_max_ac),
  [A/C를 끄면 해제](test-results.md#test_turning_ac_off_releases_max_ac).
- 기준 값 초기화에 `max_ac`를 넣었다. 신호가 11개에서 12개로, AAOS의 `--set`이 26번에서 31번으로 늘었다 (여전히 adb 왕복 한 번).

### 7-2) 화면과 문구

- 상단 바 프로필에 로그인한 운전자 이름(조예훈)을 표시한다. 설정 화면 시스템 항목에도 계정 줄을 넣었다.
- 내비게이션 '회사'의 주소를 42dot 근무지 주소(성남시 수정구 창업로40번길 20)로 바꿨다. 이름과 거리(8.7 km)는 테스트가 보고 있어 그대로 뒀다.
- 에뮬레이터에서 화면을 하나씩 캡처해 보고 고친 것: 앱 목록의 위아래 줄이 어긋나던 것(칸 너비를 같게), 설정의 시스템 정보가 줄글이던 것(이름과 값 줄로), 공조 가운데 패널 아래가 비던 것(묶음 간격을 고르게).
- 비서 대답의 '(으)로', '을(를)' 같은 괄호 표기를 받침에 맞는 조사로 바꿨다 (`CabinAssistant.josa`, 단위 테스트 2개 추가). 알림 문구는 '합니다' 말투로 맞췄다.

### 7-3) 결과

| 항목 | 결과 |
|---|---|
| AAOS 에뮬레이터 전체 E2E (113개, `--reruns 1`) | 111 passed, 1 skipped, 1 xfailed, gate pass, 재시도 0 (7분 27초) |
| 프레임워크 단위 테스트 | 33 passed |
| 앱 단위 테스트 | 컴파일만 확인 (이 PC에서는 Gradle 테스트 실행기가 죽는다. CI에서 돈다) |

- 태블릿과 두 기기 병렬은 이번에 다시 돌리지 않았다. 태블릿은 새 APK 설치에 기기 화면 승인이 필요하다.

### 7-4) 테스트별 결과 화면 (2026-11-18)

`pytest --shots`로 돌리면 테스트마다 판정이 난 직후, 정리 단계 전에 화면을 한 장 남긴다 (재시도가 있으면 마지막 시도). `tools/publish_results.py`가 실행 기록과 화면을 `site/results/`(WebP, 가로 960px)와 [테스트 결과](test-results.md)로 옮긴다. 테스트 설명과 마커는 테스트 코드의 docstring과 `@pytest.mark`에서 읽어서 따로 적지 않는다.

| 기기 | 결과 | 화면 |
|---|---|---|
| AAOS 에뮬레이터 | 111 passed, 1 skipped, 1 xfailed, 재시도 0 (8분 3초) | 112장 |
| 화웨이 태블릿 (Mock) | 107 passed, 6 skipped, 재시도 0 (8분 57초) | 107장 |

- 건너뛴 테스트는 화면이 없다. 주행 중 영상 차단은 AAOS에서는 OS 차단 화면이 스크린샷에 검게 찍히고, 태블릿에서는 앱의 차단 화면이 찍힌다.
- 두 기기를 동시에 돌리지 않고 차례로 돌렸다 (태블릿 설치 승인을 기다리느라).

