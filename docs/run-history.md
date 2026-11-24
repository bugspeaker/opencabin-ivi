# 전체 실행 기록

[근거 자료](evidence/README.md)에 결과 파일(원자료)이 남은 E2E 실행을 모두 합친 기록입니다(2026년 11-18부터 11-24까지). `ivi-tests/tools/run_history.py`가 결과 파일에서 다시 세어 만듭니다. 결과 파일을 남기기 전인 11-13부터 11-17까지의 실행은 들어 있지 않습니다.

실패, 오류, 재시도 후 통과는 하나도 빼지 않고 원인과 함께 적었습니다. 다만 판정 기능을 확인하려고 앱을 일부러 죽인 실행(2회)은 합계에서 빼고 아래 표에만 둡니다. 세션을 일부러 끊은 실행은 그 상황에서도 끝까지 통과하는지 본 것이라 합계에 넣었습니다.

## 합계

| 실행 | 테스트 실행 | 통과 | 재시도 후 통과 | 실패·오류 | 알려진 결함 |
|---|---|---|---|---|---|
| 80회 | 8,483건 | 8,436건 | 7건 | 13건 | 27건 |

- 테스트 실행은 건너뜀을 뺀 수입니다. 알려진 결함은 플랫폼 결함 하나(#21)를 `xfail(strict=True)`로 걸어 둔 것입니다.
- 실패·오류와 재시도 후 통과의 원인은 아래 '나온 곳' 표에 있습니다.

## 기기별

| 기기 | 실행 | 테스트 실행 | 통과 | 재시도 후 통과 | 실패·오류 |
|---|---|---|---|---|---|
| AAOS 에뮬레이터 | 38회 | 3,948건 | 3,909건 | 5건 | 7건 |
| 갤럭시 폴드 | 10회 | 955건 | 950건 | 0건 | 5건 |
| 태블릿 | 32회 | 3,580건 | 3,577건 | 2건 | 1건 |

## 날짜별

| 날짜 | 무엇을 확인했나 | 코드 | 기기 | 테스트 실행 | 실패·오류 | 재시도 후 통과 |
|---|---|---|---|---|---|---|
| 11-18 | [반복 5회 (129개)](evidence/2026-11-18-repeat5/README.md) | 기록 없음 | AAOS 에뮬레이터, 태블릿 | 1,250건 | 0건 | 0건 |
| 11-19 | [대기 방식을 바꾼 뒤 전체 1회](evidence/2026-11-19-after-review/README.md) | 기록 없음 | AAOS 에뮬레이터, 태블릿 | 250건 | 0건 | 0건 |
| 11-20 | [세션 복구 확인 (A·B는 세션을 일부러 끊은 실행)](evidence/2026-11-20-session-recovery/README.md) | 기록 없음 | AAOS 에뮬레이터, 태블릿 | 326건 | 0건 | 4건 |
| 11-21 | [앱 크래시 판정 확인 (앱을 일부러 죽인 실행)](evidence/2026-11-21-main/README.md) | `d41337a` | AAOS 에뮬레이터, 태블릿 | 2건 | 2건 | 0건 |
| 11-21 | [반복 3회의 첫 시도 (1회차에서 멈춤)](evidence/2026-11-21-main/README.md) | `d41337a` | AAOS 에뮬레이터, 태블릿 | 250건 | 1건 | 0건 |
| 11-21 | [반복 3회 (129개)](evidence/2026-11-21-main/README.md) | `d54741b` | AAOS 에뮬레이터, 태블릿 | 750건 | 0건 | 0건 |
| 11-23 | [갤럭시 폴드 첫 실행 (배치 수정 전)](evidence/2026-11-23-fold/README.md) | `c112673` | 갤럭시 폴드 | 145건 | 5건 | 0건 |
| 11-23 | [배치 수정 후 세 기기](evidence/2026-11-23-fold/README.md) | `7aaab6f` | AAOS 에뮬레이터, 갤럭시 폴드, 태블릿 | 494건 | 0건 | 0건 |
| 11-23 | [새 테스트 11개 첫 확인](evidence/2026-11-23-coverage/README.md) | `89177b5` | AAOS 에뮬레이터, 갤럭시 폴드, 태블릿 | 35건 | 1건 | 0건 |
| 11-23 | [가장 작은 화면 760×500dp 전체](evidence/2026-11-23-coverage/README.md) | `89177b5` | AAOS 에뮬레이터 | 139건 | 1건 | 0건 |
| 11-23 | [반복 3회 (140개)](evidence/2026-11-23-coverage/README.md) | `55419f7` | AAOS 에뮬레이터, 태블릿 | 813건 | 0건 | 0건 |
| 11-23 | [폴드 1회 (140개)](evidence/2026-11-23-coverage/README.md) | `55419f7` | 갤럭시 폴드 | 132건 | 0건 | 0건 |
| 11-23 | [정지 상태 수정 첫 확인](evidence/2026-11-23-idling/README.md) | `4144f52` | AAOS 에뮬레이터 | 21건 | 0건 | 1건 |
| 11-23 | [반복 3회 (144개)](evidence/2026-11-23-idling/README.md) | `de9d062` | AAOS 에뮬레이터, 태블릿 | 837건 | 0건 | 0건 |
| 11-23 | [폴드 1회 (144개)](evidence/2026-11-23-idling/README.md) | `de9d062` | 갤럭시 폴드 | 136건 | 0건 | 0건 |
| 11-24 | [주행 상태 읽기 수정 첫 확인](evidence/2026-11-24-driving-state/README.md) | `300b081` | AAOS 에뮬레이터 | 25건 | 0건 | 1건 |
| 11-24 | [반복 3회의 첫 시도 (1회차 태블릿 실패)](evidence/2026-11-24-driving-state/README.md) | `300b081` | AAOS 에뮬레이터, 태블릿 | 837건 | 1건 | 1건 |
| 11-24 | [폴드 1회 (144개)](evidence/2026-11-24-driving-state/README.md) | `300b081` | 갤럭시 폴드 | 136건 | 0건 | 0건 |
| 11-24 | [반복 3회 (144개)](evidence/2026-11-24-driving-state/README.md) | `300b081` | AAOS 에뮬레이터, 태블릿 | 837건 | 0건 | 0건 |
| 11-24 | [동시 조작 테스트 첫 확인 (커밋 전)](evidence/2026-11-24-concurrency/README.md) | `410a052` | AAOS 에뮬레이터, 갤럭시 폴드, 태블릿 | 49건 | 4건 | 0건 |
| 11-24 | [빠른 누름 간격 줄여 보기 (저장소에 넣지 않은 임시 테스트)](evidence/2026-11-24-concurrency/README.md) | `410a052` | AAOS 에뮬레이터, 태블릿 | 6건 | 0건 | 0건 |
| 11-24 | [반복 3회 (150개)](evidence/2026-11-24-concurrency/README.md) | `101de99` | AAOS 에뮬레이터, 태블릿 | 873건 | 0건 | 0건 |
| 11-24 | [폴드 1회 (150개)](evidence/2026-11-24-concurrency/README.md) | `101de99` | 갤럭시 폴드 | 142건 | 0건 | 0건 |

## 실패, 오류, 재시도 후 통과가 나온 곳

| 날짜 | 실행 | 기기 | 테스트 | 결과 | 원인 |
|---|---|---|---|---|---|
| 11-20 | `20261120-session-a` | AAOS 에뮬레이터 | `test_typed_command_sets_vehicle_temperature` | 재시도 후 통과 | **확인용** 실행 120초에 UiAutomator2 서버를 일부러 강제 종료했습니다. 세션을 다시 붙이고 재시도에서 통과했습니다. |
| 11-20 | `20261120-session-a` | AAOS 에뮬레이터 | `test_signal_is_shown_on_climate_and_home[driver]` | 재시도 후 통과 | **확인용** 실행 120초에 UiAutomator2 서버를 일부러 강제 종료했습니다. 세션을 다시 붙이고 재시도에서 통과했습니다. |
| 11-20 | `20261120-session-a` | AAOS 에뮬레이터 | `test_mph_setting_converts_vehicle_speed` | 재시도 후 통과 | **확인용** 실행 120초에 UiAutomator2 서버를 일부러 강제 종료했습니다. 세션을 다시 붙이고 재시도에서 통과했습니다. |
| 11-20 | `20261120-session-b` | 태블릿 | `test_driving_signals_are_shown` | 재시도 후 통과 | **확인용** 실행 45초에 Appium 서버를 일부러 껐다 켰습니다. 세션을 다시 붙이고 재시도에서 통과했습니다. |
| 11-21 | `20261121-probe2` | AAOS 에뮬레이터 | `test_probe_app_killed_midtest` | 실패 | **확인용** 앱 크래시 판정을 확인하려고 테스트 도중 앱을 일부러 죽였습니다. |
| 11-21 | `20261121-probe5` | 태블릿 | `test_probe_app_killed_midtest` | 실패 | **확인용** 앱 크래시 판정을 확인하려고 테스트 도중 앱을 일부러 죽였습니다. |
| 11-21 | `20261121-115127-r1` | AAOS 에뮬레이터 | `test_power_cycle_brings_back_app_and_cabin_defaults` | 실패 | **환경** PC 화면이 꺼진 상태에서 창 모드로 다시 켠 에뮬레이터가 멈췄습니다. 창 없이 켜게 고치고 처음부터 다시 돌렸습니다. |
| 11-23 | `20261123-fold-full-portrait` | 갤럭시 폴드 | `test_ambiguous_destination_offers_candidates` | 실패 | **앱 결함** 좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다. |
| 11-23 | `20261123-fold-full-portrait` | 갤럭시 폴드 | `test_tune_and_seek` | 실패 | **앱 결함** 좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다. |
| 11-23 | `20261123-fold-full-portrait` | 갤럭시 폴드 | `test_preset_save_and_recall` | 실패 | **앱 결함** 좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다. |
| 11-23 | `20261123-fold-full-portrait` | 갤럭시 폴드 | `test_preset_and_frequency_survive_app_restart` | 실패 | **앱 결함** 좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다. |
| 11-23 | `20261123-fold-full-portrait` | 갤럭시 폴드 | `test_seat_heat_signal_is_shown_everywhere` | 실패 | **앱 결함** 좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다. |
| 11-23 | `20261123-new-aaos` | AAOS 에뮬레이터 | `test_folded_mirror_can_be_unfolded_while_driving` | 실패 | **테스트 도구** 막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상). 그 테스트만 다시 돌려 통과했습니다. |
| 11-23 | `20261123-min760` | AAOS 에뮬레이터 | `test_driver_temp_up_is_not_covered_by_home` | 실패 | **플랫폼** 1024×768에서만 나는 SystemUI 겹침(#21)이 760×500dp에서는 재현되지 않아, 알려진 결함 표시(xfail strict)가 실패로 뒤집혔습니다. |
| 11-23 | `20261123-ux-aaos` | AAOS 에뮬레이터 | `test_driving_locks_typing_and_refuses_mirror_fold` | 재시도 후 통과 | **테스트 도구** 막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상). |
| 11-24 | `20261124-driving-state-aaos` | AAOS 에뮬레이터 | `test_driving_signals_are_shown` | 재시도 후 통과 | **테스트 도구** 막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상). |
| 11-24 | `20261124-110716-r1` | 태블릿 | `test_zone_applies_command_to_speaking_seat` | 오류 | **환경** 실행을 시작할 무렵 USB를 연결해 태블릿에 뜬 시스템 창(USB 연결 방식 선택)이 앱을 가렸습니다. 첫 시도로 남기고 3회를 다시 돌렸습니다. |
| 11-24 | `20261124-110716-r1` | 태블릿 | `test_typed_command_sets_vehicle_temperature` | 재시도 후 통과 | **환경** 실행을 시작할 무렵 USB를 연결해 태블릿에 뜬 시스템 창(USB 연결 방식 선택)이 앱을 가렸습니다. 첫 시도로 남기고 3회를 다시 돌렸습니다. |
| 11-24 | `20261124-153908` | AAOS 에뮬레이터 | `test_quick_taps_are_all_applied[driver]` | 실패 | **테스트 도구** AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. adb input tap으로 바꿔 통과했습니다. |
| 11-24 | `20261124-153908` | AAOS 에뮬레이터 | `test_quick_taps_are_all_applied[passenger]` | 실패 | **테스트 도구** AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. adb input tap으로 바꿔 통과했습니다. |
| 11-24 | `20261124-154050` | AAOS 에뮬레이터 | `test_quick_taps_are_all_applied[driver]` | 실패 | **테스트 도구** AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. 누름 사이 대기를 빼도 같아서 adb input tap으로 바꿨습니다. |
| 11-24 | `20261124-154050` | AAOS 에뮬레이터 | `test_quick_taps_are_all_applied[passenger]` | 실패 | **테스트 도구** AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. 누름 사이 대기를 빼도 같아서 adb input tap으로 바꿨습니다. |

다시 만드는 방법 (`ivi-tests`에서):

```powershell
.venv\Scripts\python tools\run_history.py
```
