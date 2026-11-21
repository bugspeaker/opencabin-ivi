# 3단계 테스트 프레임워크

2026-11-13에 정리했습니다. 같은 테스트 코드로 AAOS 에뮬레이터(CarService와 에뮬레이터 VHAL)와 일반 태블릿(Mock 차량)을 검증하는 틀을 만들었습니다.

## 결과

| 기기 | 결과 | 시간 | 반복 |
|---|---|---|---|
| AAOS 에뮬레이터 (API 34) | 30개 통과, 1개 알려진 결함 | 2분 7초 ~ 2분 32초 | 네 번 모두 같은 결과 |
| 화웨이 태블릿 DBY-W09 (Mock) | 25개 통과, AAOS 전용 6개 건너뜀 | 1분 31초 ~ 1분 42초 | 고친 뒤 다섯 번 모두 통과 |

알려진 결함 1건은 1단계에서 찾은 SystemUI 결함입니다. 운전석 온도 ▲ 버튼이 홈 버튼에 가려집니다.

태블릿에서는 실행할 때마다 21번째 테스트에서 앱을 한 번 다시 띄운 기록이 남았습니다. 이유는 아래 '화웨이 iAware'에 적었습니다.

## 구조

```
ivi-tests/
  ivi/adb.py        adb 명령, 맨 위 액티비티, logcat
  ivi/waits.py      wait_until. 조건이 맞을 때까지 기다림 (테스트의 대기에 고정 sleep을 쓰지 않음)
  ivi/vehicle.py    VehicleController
                      AaosVehicle  VHAL --set, car_service set-property-value, 값 저장과 복원
                      MockVehicle  am broadcast mock.SET, mock.GET
  ivi/device.py     Device. 기기 종류 판별, Appium 설정, 앱 실행, 누르는 방법, 기기마다 다른 판정
  ivi/screens.py    화면 객체. IviApp(탭, 배지)에서 Home, Climate, Media, Video로
  conftest.py       --serial 옵션, 픽스처(device, driver, app, car, vehicle), aaos 마커 건너뛰기, 실패 자료
  tests/            smoke, sanity, regression, spike
```

테스트에는 `car.drive(50)`, `climate.increase(Seat.DRIVER)`처럼 할 일만 씁니다. VHAL을 쓸지 broadcast를 쓸지, Appium으로 누를지 adb로 누를지는 어댑터가 정합니다.

## 테스트 구성 (31개)

| 마커 | 파일 | 내용 |
|---|---|---|
| smoke | test_smoke.py | 앱이 뜨고 기기에 맞는 데이터 소스에 붙는지, 정차 상태로 시작하는지, 탭 세 개가 열리는지, 공조를 제어할 수 있는지(priv-app 확인) |
| sanity | test_climate.py | 신호가 공조 화면과 홈에 보이는지(좌석 두 곳), 버튼을 누르면 신호가 0.5°C 바뀌는지(좌석 두 곳과 올림, 내림) |
| sanity | test_driving.py | 속도, 기어, 제한 배지가 보였다가 사라지는지, 주행 중 영상 버튼 잠금, 영상 화면을 바로 열어도 막히는지, 정차 중 재생 |
| regression | test_climate.py | 최저, 최고 온도에서 버튼이 꺼지는지(좌석 두 곳), 좌석 값이 서로 영향을 주지 않는지 |
| regression | test_driving.py | 막혔던 영상이 정차하면 재생 화면으로 돌아오는지 |
| regression | test_media.py | 곡 선택(세 곡), 재생과 일시 정지, 주행 중에도 음악을 고를 수 있는지 |
| spike, aaos | test_spike_aaos.py | 1단계에서 했던 기본 SystemUI HVAC 바 검증 (AAOS에서만) |

실행 예입니다.

```powershell
.venv\Scripts\python -m pytest --serial emulator-5554 -m smoke            # 빌드 게이트
.venv\Scripts\python -m pytest --serial emulator-5554 -m "smoke or sanity" # Nightly
.venv\Scripts\python -m pytest --serial W3VBB22125209573                  # 태블릿 전체
```

## 기기마다 다른 점을 감춘 곳

| 차이 | AAOS 에뮬레이터 | 화웨이 태블릿 | 처리하는 곳 |
|---|---|---|---|
| 차량 값 넣기 | `dumpsys <VHAL> --set`, `cmd car_service set-property-value` | `am broadcast … mock.SET` | `ivi/vehicle.py` |
| 테스트 사이 값 되돌리기 | VHAL `--save-prop`, `--restore-prop` | 앱을 다시 시작해 초기화 | `prepare()`, `cleanup()` |
| 주행 중 제한 판정 | CarDrivingStateService가 MOVING인지 | mock.GET의 `restricted=true` | `is_restricted()` |
| 영상 차단 판정 | 맨 위 화면이 OS의 `ActivityBlockingActivity`인지 | 앱의 `video_blocked` 화면 | `Device.video_blocked()` |
| Appium 설정 | `userProfile=10`, `skipDeviceInitialization`, `enableMultiWindows` | 기본값 | `Device.appium_options()` |
| 누르는 방법 | Appium click | 요소 가운데 좌표를 `adb shell input tap` | `Device.tap_mode`. `IVI_TAP`으로 바꿀 수 있습니다. |

AAOS는 주행 중에 막혔던 영상을, 차를 세우면 OS가 다시 앞으로 띄웁니다(2026-11-13 확인). 그래서 '정차하면 재생 화면으로 돌아오는지'는 두 기기에서 같은 방법으로 판정합니다.

## 찾아서 고친 것

### 1) 화웨이에서 탭 한 번에 10초가 걸린 문제

이 문제를 고쳐서 태블릿 전체 실행 시간이 7분 22초에서 1분 32초로 줄었습니다.

| 누르는 방법 | 화웨이 DBY-W09 | AAOS 에뮬레이터 |
|---|---|---|
| `element.click()` | 10,377 ms | 577 ms |
| `mobile: clickGesture` | 10,099 ms | 501 ms |
| W3C actions | 10,430 ms | - |
| `adb shell input tap` | 117 ms | - |

테스트별 시간을 보니 클릭이 많은 테스트일수록 느렸습니다. 재생과 일시 정지 테스트는 43.6초나 걸렸습니다. adb 왕복은 65ms라 원인이 아니었습니다.

`waitForIdleTimeout`과 `actionAcknowledgmentTimeout`을 0으로 바꿔도 그대로였습니다. 설정 문제가 아니라, 화웨이 기기에서 UiAutomator가 넣는 터치를 처리하는 데 10초쯤 걸리는 것이었습니다.

그래서 화웨이와 아너 기기는 기본으로 adb tap을 쓰게 했습니다. 요소는 여전히 Appium으로 찾기 때문에 화면 객체와 테스트 코드는 바꾸지 않았습니다.

### 2) 화웨이 iAware가 테스트 중인 앱을 강제로 끈 문제

태블릿에서 반복 실행하던 중 한 번, 앱을 띄우는 단계에서 `source_badge`를 찾지 못해 error가 났습니다. 실패 자료의 logcat에 `Force stopping dev.opencabin.ivi … iAwareF[CrashClean]`이 남아 있었고, 그 뒤 화면은 런처로 돌아가 있었습니다.

테스트마다 `am start -S`로 앱을 끄고 다시 켜는데, 짧은 간격으로 스무 번쯤 반복되면 화웨이 OS가 이것을 반복 크래시로 보고 앱을 죽였습니다. 실행할 때마다 21번째 테스트에서 재현됐습니다.

우선 `app` 픽스처가 앱이 뜨지 않으면 한 번 더 띄우고, 그 사실을 JUnit property `app_relaunch`로 남기게 했습니다. 테스트는 통과로 처리하지만 다시 띄웠다는 기록은 남습니다.

4단계에서 할 일로 두 가지를 남겼습니다. Mock 기기에서는 프로세스를 끄지 않고 화면과 상태만 초기화해서 재실행 자체를 줄이는 것, 그리고 `app_relaunch` 기록을 flaky 통계로 모으는 것입니다.

## 실패 자료

테스트가 실패하면 정리 단계(teardown) 전에 `reports/artifacts/<실행>-<기기>/<테스트>/`에 자료를 남깁니다(2026-11-18부터 실행과 기기별 폴더. 그 전에는 두 기기를 병렬로 돌리면 같은 테스트의 자료가 덮어써졌습니다). 정리 단계에서 정차시키고 값을 되돌리기 때문에, 그 전에 찍어야 실패한 순간이 남습니다.

| 파일 | 내용 |
|---|---|
| `screen.png` | 화면 |
| `page_source.xml` | UI 계층. 요소를 못 찾았을 때 실제로 무엇이 있었는지 볼 수 있습니다. |
| `vehicle.txt` | 차량 상태. AAOS는 속도(m/s), 기어, 주행 상태, 좌석별 온도이고, Mock은 mock.GET 결과입니다. |
| `activities.txt` | 디스플레이마다 맨 위에 있는 액티비티. AAOS는 메인과 클러스터 두 개입니다. |
| `logcat.txt` | 테스트를 시작할 때 비운 뒤부터 쌓인 로그 |

일부러 실패시킨 확인용 테스트에서 `vehicle.txt`에 `driving_state=2`(주행), `gear=8`(D)이 찍혀 실패 순간이 그대로 남았습니다. 앞의 iAware 원인도 이 logcat으로 찾았습니다.

## 결과 파일

JUnit 결과는 기기마다 `reports/junit-<aaos|mock>-<serial>.xml`로 남고, CI가 이것을 모읍니다. 앱을 다시 띄운 테스트에는 `app_relaunch` property가 붙습니다.
