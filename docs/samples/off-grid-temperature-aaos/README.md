# 실패 자료 예시: 0.5°C 단위가 아닌 차량 값에서 온도 버튼

`test_off_grid_signal_steps_back_to_grid[up-22.5]`가 고치기 전 앱에서 실패했을 때(2026-11-18, AAOS 에뮬레이터) 프레임워크가 정리 단계 전에 저장한 자료를 그대로 옮겼습니다. 원래 위치는 `ivi-tests/reports/artifacts/<실행>-<기기>/<테스트>/`입니다.

| 파일 | 내용 | 이 결함에서 본 것 |
|---|---|---|
| `screen.png` | 실패한 순간의 화면 | 운전석 온도가 22.8°C로 보임 |
| `page_source.xml` | UI 계층 (Appium) | `driver_temp_value`의 글자 `22.8°C` |
| `vehicle.txt` | 차량 상태 (CarService로 읽은 VHAL 값) | `temp_driver=22.8`. 화면만이 아니라 차량 값까지 어긋남 |
| `activities.txt` | 맨 위 액티비티 | 앱이 앞에 떠 있었음 (앱이 꺼져서 생긴 실패가 아님) |
| `logcat.txt` | 이 테스트 동안의 logcat (테스트 시작 때 비움) | 앱 오류 없음. 계산 결과가 틀린 결함 |

실패 메시지(이때의 형식): `10초 안에 차량 driver 온도 22.5이(가) 맞지 않았다 (마지막 값: False) 마지막으로 읽은 값: 22.8`. 그 뒤 `wait_value`가 '마지막으로 읽은 값'만 남기도록 메시지를 다듬었습니다.

원인과 수정은 [포트폴리오 3장 8번](../../portfolio.md#3-결함과-원인-분석)에 있습니다.
