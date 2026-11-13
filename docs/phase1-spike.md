# 1단계 기술 검증 (AAOS 에뮬레이터 · VHAL · Appium)

작성 2026-11-13. 목적: 자체 IVI 앱을 만들기 전에, PC 한 대로 **차량 신호 주입 → UI 확인 → UI 조작 → 차량 신호 확인** E2E 가 되는지 먼저 확인한다.

## 결론

| 확인 항목 | 결과 | 근거 |
|---|---|---|
| Automotive 에뮬레이터 부팅 | ✅ 약 30초 | API 34 `android-automotive` x86_64, 1024x768 |
| adb root (VHAL 직접 제어용) | ✅ | 이미지가 `userdebug` |
| 읽기 전용 센서 값 주입 (속도·기어) | ✅ `dumpsys <VHAL> --set` | `cmd car_service inject-vhal-event` 는 값이 저장되지 않음 (아래 참고) |
| 쓰기 가능 값 (HVAC 온도) | ✅ `cmd car_service set-property-value` | 앱의 CarPropertyManager 와 같은 경로 |
| 신호 → UI | ✅ | HVAC 25.0°C 넣으면 하단 바 77° |
| UI → 신호 | ✅ | ▼/▲ 1회 = 0.5°C |
| 속도·기어 → 주행 상태 | ✅ | PARKED(0) ↔ MOVING(2), UX 제한 0x1ff, 비최적화 화면에 "You can't use this feature while driving" |
| Appium(UiAutomator2) 세션 | ✅ 3초 | AAOS 전용 설정 3가지 필요 (아래) |
| 안정성 | ✅ | `pytest` 3회 연속 5 passed, 1 xfailed, 회당 약 9초 |

## 차량 신호 제어: 명령 3가지의 차이

| 명령 | 경로 | 결과 |
|---|---|---|
| `cmd car_service set-property-value <prop> <area> <값>` | CarService → VHAL | 쓰기 권한 있는 property 만. HVAC 성공, 속도는 읽기 전용이라 불가 |
| `cmd car_service inject-vhal-event <prop> <area> <값>` | 이벤트만 발생 | **저장 값은 그대로**라 `get-property-value` 로 확인 불가. 테스트 판정에 쓰지 않는다 |
| `dumpsys android.hardware.automotive.vehicle.IVehicle/default --set <prop> -f/-i <값> -a <area>` | VHAL 직접 (root) | 읽기 전용 센서 값도 바뀌고 변경 이벤트가 CarService 로 나감 → 주행 상태까지 실제로 따라 바뀜 |

- VHAL 에는 테스트용 `--save-prop` / `--restore-prop` 가 있다. 픽스처에서 테스트 전후로 값을 저장·복원해서 테스트끼리 영향을 주지 않게 했다.
- `--genfakedata` (선형 값 생성, JSON 시나리오 재생)도 있다. 주행 시나리오(가속·감속) 테스트에 쓸 수 있다 → 3단계 후보.

## Appium 을 AAOS 에 붙일 때 필요한 것

| 증상 | 원인 | 해결 |
|---|---|---|
| `Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported` | Appium 서버 환경 변수 | `ANDROID_HOME=C:\android` 로 서버 실행 |
| `Appium Settings app is not running after 30000ms` | AAOS 는 시스템 사용자(0)와 운전자 사용자(10)가 따로 돈다 | `appium:userProfile` = `am get-current-user` 값, `appium:skipDeviceInitialization: true` |
| 하단 HVAC 바가 화면 소스에 없음 | SystemUI 바는 앱과 다른 창 | 세션 후 `update_settings({"enableMultiWindows": True})` |

## 발견한 결함: 운전석 온도 ▲ 가 홈 버튼에 가려짐

- 화면: 하단 시스템 바, 1024x768 (`automotive_1024p_landscape`)
- 현상: 운전석 온도 ▲ 를 눌러도 온도가 바뀌지 않는다. Appium 클릭, `adb shell input tap` 모두 같다.
- 원인: 영역이 겹친다. ▲ `[192,682][268,758]`, 홈 `[188,682][264,758]` → 72x76px 겹침, 홈이 위에 있어 탭을 가져간다.
- 비교: 운전석 ▼, 조수석 ▲·▼ 는 정상 (1회 = 0.5°C).
- 처리: `test_driver_temp_up_is_not_covered_by_home` 를 `xfail(strict=True)` 로 둔다. 결함이 고쳐지면 XPASS → strict 라 실패로 바뀌어 알려 준다.

## 환경에서 막혔던 것

| 문제 | 해결 |
|---|---|
| 에뮬레이터 35.4.9 로 Automotive 이미지 부팅 중 종료 | 에뮬레이터 37.2.13 으로 업데이트 |
| 사용자 폴더 경로에 한글 (`C:\Users\조예훈\.android\avd`) | AVD 를 `C:\android\avd` 로 옮기고 `ANDROID_AVD_HOME` 지정 |
| `avdmanager` 가 응답 없음 (cmdline-tools 가 SDK XML v4 를 못 읽음) | AVD `config.ini` 를 직접 작성 (`hw.device.name=automotive_1024p_landscape`) |

## 다음 단계로 넘길 것

- 주행 중 제한 E2E 는 기본 앱으로는 판정이 애매하다(어떤 앱이 Distraction Optimized 인지 바깥에서 정하기 어려움). **2단계에서 만드는 자체 앱**에 DO 화면과 비DO 화면(영상 재생)을 둬서 `drive()` → 차단 화면 / `park()` → 복귀를 확인한다.
- 태블릿(화웨이 DBY-W09, Android 12 기반)은 CarService 가 없으므로 앱 안의 Mock 차량 서비스를 `adb shell am broadcast` 로 제어한다. `vehicle.py` 의 `Vehicle` 과 같은 인터페이스로 맞춰 테스트 코드를 그대로 쓴다.
