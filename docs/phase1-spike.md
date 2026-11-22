# 1단계 기술 검증: AAOS 에뮬레이터, VHAL, Appium

2026-11-13에 정리했습니다. 앱을 만들기 전에 PC 한 대로 이런 흐름이 되는지부터 확인했습니다. 차량 신호를 넣으면 화면이 바뀌고, 화면을 누르면 차량 신호가 바뀌는지입니다.

## 결론

| 확인한 것 | 결과 | 비고 |
|---|---|---|
| Automotive 에뮬레이터 부팅 | 약 30초 만에 켜졌습니다. | API 34 `android-automotive` x86_64, 화면 1024x768 |
| adb root (VHAL 직접 제어용) | 됨 | 이미지가 `userdebug`입니다. |
| 읽기 전용 센서 값 넣기 (속도, 기어) | `dumpsys <VHAL> --set`으로 됩니다. | `cmd car_service inject-vhal-event`는 값이 저장되지 않습니다. 아래에 자세히 적었습니다. |
| 쓰기 가능한 값 (HVAC 온도) | `cmd car_service set-property-value`로 됩니다. | 앱의 CarPropertyManager와 같은 경로입니다. |
| 신호를 넣으면 화면이 바뀌는지 | 됨 | HVAC 25.0°C를 넣으면 하단 바에 77°가 보입니다. |
| 화면을 누르면 신호가 바뀌는지 | 됨 | ▼나 ▲를 한 번 누르면 0.5°C 바뀝니다. |
| 속도와 기어로 주행 상태가 바뀌는지 | 됨 | PARKED(0)와 MOVING(2) 사이를 오가고, UX 제한이 0x1ff가 되면 주행 중에 쓸 수 없는 화면에 "You can't use this feature while driving"이 뜹니다. |
| Appium(UiAutomator2) 세션 | 3초 만에 연결 | AAOS에 맞는 설정이 세 가지 필요합니다. 아래에 적었습니다. |
| 안정성 | 됨 | `pytest`를 세 번 연속 돌려 모두 5개 통과, 1개 알려진 결함이었고 한 번에 9초쯤 걸렸습니다. |

## 차량 신호를 넣는 명령 세 가지

| 명령 | 경로 | 결과 |
|---|---|---|
| `cmd car_service set-property-value <prop> <area> <값>` | CarService를 거쳐 VHAL로 | 쓰기 권한이 있는 property만 됩니다. HVAC는 되고, 속도는 읽기 전용이라 안 됩니다. |
| `cmd car_service inject-vhal-event <prop> <area> <값>` | 이벤트만 보냅니다. | 저장된 값이 그대로라 `get-property-value`로 확인할 수 없습니다. 테스트 판정에는 쓰지 않습니다. |
| `dumpsys android.hardware.automotive.vehicle.IVehicle/default --set <prop> -f/-i <값> -a <area>` | VHAL에 바로 (root) | 읽기 전용 센서 값도 바뀌고 변경 이벤트가 CarService로 나가서, 주행 상태까지 실제로 바뀝니다. |

VHAL에는 테스트용 `--save-prop`과 `--restore-prop`이 있습니다. 픽스처에서 테스트 앞뒤로 값을 저장하고 되돌려서 테스트끼리 서로 영향을 주지 않게 했습니다.

`--genfakedata`로 값을 선형으로 만들거나 JSON 시나리오를 재생할 수도 있습니다. 가속과 감속 같은 주행 시나리오 테스트에 쓸 수 있어서 3단계 후보로 남겨 두었습니다.

## Appium을 AAOS에 붙일 때 필요한 것

| 증상 | 원인 | 해결 |
|---|---|---|
| `Neither ANDROID_HOME nor ANDROID_SDK_ROOT environment variable was exported` | Appium 서버에 환경 변수가 없었습니다. | `ANDROID_HOME=C:\android`를 주고 서버를 켰습니다. |
| `Appium Settings app is not running after 30000ms` | AAOS에서는 시스템 사용자(0)와 운전자 사용자(10)가 따로 돕니다. | `appium:userProfile`에 `am get-current-user` 값을 넣고 `appium:skipDeviceInitialization: true`를 줬습니다. |
| 하단 HVAC 바가 화면 소스에 보이지 않았습니다. | SystemUI 바는 앱과 다른 창입니다. | 세션을 연 뒤 `update_settings({"enableMultiWindows": True})`를 불렀습니다. |

## 찾은 결함: 운전석 온도 ▲ 버튼이 홈 버튼에 가려졌습니다

1024x768 화면(`automotive_1024p_landscape`)의 하단 시스템 바에서 운전석 온도 ▲를 눌러도 온도가 바뀌지 않았습니다. Appium으로 눌러도, `adb shell input tap`으로 눌러도 같았습니다.

원인은 버튼 영역이 겹친 것이었습니다. ▲는 `[192,682][268,758]`, 홈 버튼은 `[188,682][264,758]`이라 72x76px가 겹치고, 홈 버튼이 위에 있어서 탭을 가져갑니다. 운전석 ▼와 조수석 ▲, ▼는 정상이었습니다.

`test_driver_temp_up_is_not_covered_by_home`을 `xfail(strict=True)`로 두었습니다. 나중에 결함이 고쳐지면 이 테스트가 통과하게 되고, strict 설정 때문에 그 결과가 실패로 바뀌어서 바로 알 수 있습니다.

이 결함은 GitHub 이슈 [#21](https://github.com/bugspeaker/opencabin-ivi/issues/21)로 열어 두었습니다.

## 환경에서 막혔던 것

| 문제 | 해결 |
|---|---|
| 에뮬레이터 35.4.9에서 Automotive 이미지가 부팅 중에 꺼졌습니다. | 에뮬레이터를 37.2.13으로 올렸습니다. |
| 사용자 폴더 경로에 한글이 있었습니다 (`C:\Users\조예훈\.android\avd`). | AVD를 `C:\android\avd`로 옮기고 `ANDROID_AVD_HOME`을 지정했습니다. |
| `avdmanager`가 응답하지 않았습니다. cmdline-tools가 SDK XML v4를 읽지 못했습니다. | AVD의 `config.ini`를 직접 썼습니다 (`hw.device.name=automotive_1024p_landscape`). |

## 다음 단계로 넘긴 것

주행 중 제한은 기본 앱만으로는 판정이 애매했습니다. 어떤 앱이 Distraction Optimized인지 바깥에서 정하기 어렵기 때문입니다. 그래서 2단계에서 만드는 앱에 주행 중에도 쓰는 화면과 막혀야 하는 화면(영상 재생)을 함께 두고, 주행으로 바꾸면 막히고 정차하면 돌아오는지 확인하기로 했습니다.

화웨이 태블릿(DBY-W09, Android 12 기반)에는 CarService가 없습니다. 그래서 앱 안에 Mock 차량 서비스를 두고 `adb shell am broadcast`로 제어하기로 했습니다. 테스트 코드가 기기를 가리지 않도록 `vehicle.py`의 `Vehicle`과 같은 인터페이스로 맞춥니다.
