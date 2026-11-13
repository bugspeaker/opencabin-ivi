# 3단계 테스트 프레임워크

작성 2026-11-13. 같은 테스트 코드로 AAOS 에뮬레이터(실제 CarService·VHAL)와 일반 태블릿(Mock 차량)을 검증한다.

## 결과

| 기기 | 결과 | 시간 | 반복 |
|---|---|---|---|
| AAOS 에뮬레이터 (API 34) | 30 passed, 1 xfailed | 2분 7초 ~ 2분 32초 | 4회 모두 동일 |
| 화웨이 태블릿 DBY-W09 (Mock) | 25 passed, 6 skipped (AAOS 전용) | 1분 31초 ~ 1분 42초 | 개선 후 5회 모두 통과 |

- xfailed 1건: 1단계에서 찾은 SystemUI 결함 (운전석 온도 ▲ 가 홈 버튼에 가려짐).
- 태블릿은 실행마다 21번째 테스트에서 앱 재실행 1회가 기록된다 (아래 '화웨이 iAware').

## 구조

```
ivi-tests/
  ivi/adb.py        adb 명령, 맨 위 액티비티, logcat
  ivi/waits.py      wait_until: 조건 대기 (고정 sleep 금지)
  ivi/vehicle.py    VehicleController ─┬ AaosVehicle  VHAL --set / car_service set-property-value, save·restore
                                       └ MockVehicle  am broadcast mock.SET / mock.GET
  ivi/device.py     Device: 종류 판별(automotive feature), Appium 설정, 앱 실행, 누르는 방법, 기기별 판정
  ivi/screens.py    화면 객체: IviApp(탭·배지) → Home / Climate / Media / Video
  conftest.py       --serial, 픽스처(device·driver·app·car·vehicle), aaos 마커 건너뛰기, 실패 자료
  tests/            smoke / sanity / regression / spike
```

테스트는 `car.drive(50)`, `climate.increase(Seat.DRIVER)` 처럼 **무엇을** 하는지만 쓴다. **어떻게**(VHAL 인지 broadcast 인지, click 인지 adb tap 인지)는 어댑터가 정한다.

## 테스트 구성 (31개)

| 마커 | 파일 | 내용 |
|---|---|---|
| smoke | test_smoke.py | 앱 실행 + 기기에 맞는 데이터 소스(AAOS/Mock), 정차 상태 시작, 탭 3개, 공조 제어 가능(priv-app 확인) |
| sanity | test_climate.py | 신호 → 공조 화면·홈 요약 (좌석 2), 버튼 → 신호 0.5°C (좌석 2 × 방향 2) |
| sanity | test_driving.py | 속도·기어·제한 배지 표시와 해제, 주행 중 영상 버튼 잠금, 주행 중 영상 직접 실행 차단, 정차 중 재생 |
| regression | test_climate.py | 최저·최고 온도에서 버튼 비활성 (좌석 2), 좌석 값 독립성 |
| regression | test_driving.py | 차단된 영상이 정차하면 재생 화면으로 돌아옴 |
| regression | test_media.py | 곡 선택(3곡), 재생/일시 정지, 주행 중에도 음악 선택 가능 |
| spike, aaos | test_spike_aaos.py | 1단계 기본 SystemUI HVAC 바 검증 (AAOS 에서만) |

실행 예:
```powershell
.venv\Scripts\python -m pytest --serial emulator-5554 -m smoke            # 빌드 게이트
.venv\Scripts\python -m pytest --serial emulator-5554 -m "smoke or sanity" # Nightly
.venv\Scripts\python -m pytest --serial W3VBB22125209573                  # 태블릿 전체
```

## 기기마다 다른 점을 감춘 곳

| 차이 | AAOS 에뮬레이터 | 화웨이 태블릿 | 어디서 |
|---|---|---|---|
| 차량 값 넣기 | `dumpsys <VHAL> --set`, `cmd car_service set-property-value` | `am broadcast … mock.SET` | `ivi/vehicle.py` |
| 테스트 사이 값 복원 | VHAL `--save-prop` / `--restore-prop` | 앱 재시작으로 초기화 | `prepare()` / `cleanup()` |
| 주행 중 제한 판정 | CarDrivingStateService = MOVING | mock.GET `restricted=true` | `is_restricted()` |
| 영상 차단 판정 | 맨 위가 `ActivityBlockingActivity` (OS 차단) | 앱의 `video_blocked` 화면 | `Device.video_blocked()` |
| Appium 설정 | `userProfile=10`, `skipDeviceInitialization`, `enableMultiWindows` | 기본 | `Device.appium_options()` |
| 누르는 방법 | Appium click | 요소 중심 좌표를 `adb shell input tap` | `Device.tap_mode`, `IVI_TAP` 로 바꿀 수 있음 |

- AAOS 는 주행 중 막힌 영상을 정차하면 **OS 가 다시 앞으로 띄운다** (2026-11-13 확인). 그래서 '정차 후 재생 화면 복귀' 는 두 기기 모두 같은 판정이다.

## 찾아서 고친 것

### 1) 화웨이에서 탭 한 번에 10초 → 태블릿 전체 7분 22초에서 1분 32초로

| 누르는 방법 | 화웨이 DBY-W09 | AAOS 에뮬레이터 |
|---|---|---|
| `element.click()` | 10,377 ms | 577 ms |
| `mobile: clickGesture` | 10,099 ms | 501 ms |
| W3C actions | 10,430 ms | - |
| `adb shell input tap` | **117 ms** | - |

- 테스트별 시간을 보니 클릭이 많은 테스트일수록 느렸다 (재생/일시 정지 43.6초). adb 왕복은 65ms 로 원인이 아니었다.
- `waitForIdleTimeout`, `actionAcknowledgmentTimeout` 을 0 으로 해도 그대로 → 설정 문제가 아니라 화웨이에서 UiAutomator 가 넣는 터치 처리 자체가 약 10초 걸린다.
- 화웨이·아너는 기본으로 adb tap 을 쓰게 했다. 요소는 여전히 Appium 으로 찾으므로 화면 객체·테스트 코드는 그대로다.

### 2) 화웨이 iAware 가 테스트 중인 앱을 강제 종료

- 증상: 태블릿 반복 실행 중 한 번, 앱 시작 단계에서 `source_badge` 를 못 찾아 error.
- 실패 자료의 logcat: `Force stopping dev.opencabin.ivi … iAwareF[CrashClean]` → 런처로 돌아감.
- 원인: 테스트마다 앱을 종료·재실행(`am start -S`)하는데, 짧은 간격으로 20번쯤 반복되면 화웨이가 '반복 크래시' 로 보고 앱을 죽인다. 실행마다 **21번째 테스트**에서 재현된다.
- 처리: `app` 픽스처가 앱이 안 뜨면 한 번 더 띄우고, 그 사실을 JUnit property `app_relaunch` 로 남긴다. 통과는 하되 숨기지 않는다.
- 남은 일(4단계): Mock 기기는 프로세스를 죽이지 않고 화면·상태만 초기화해서 재실행 횟수 자체를 줄이기, `app_relaunch` 를 flaky 통계로 모으기.

## 실패 자료

실패하면 정리(teardown) 전에 `reports/artifacts/<테스트>/` 에 남긴다. 정리가 정차·값 복원을 하므로 그 전에 찍어야 실패 순간이 보인다.

| 파일 | 내용 |
|---|---|
| `screen.png` | 화면 |
| `page_source.xml` | UI 계층 (요소를 못 찾을 때 실제로 무엇이 있었는지) |
| `vehicle.txt` | 차량 상태 (AAOS: 속도 m/s, 기어, 주행 상태, 좌석별 온도 / Mock: mock.GET 결과) |
| `activities.txt` | 디스플레이별 맨 위 액티비티 (AAOS 는 메인 + 클러스터) |
| `logcat.txt` | 테스트 시작 때 비운 뒤의 로그 |

일부러 실패시킨 확인 테스트에서 `vehicle.txt` 가 `driving_state=2`(주행), `gear=8`(D) 로 실패 순간을 담았다. iAware 원인도 이 logcat 으로 찾았다.

## 결과 파일

- JUnit: `reports/junit-<aaos|mock>-<serial>.xml` (기기별, CI 가 모은다)
- `app_relaunch` property: 앱을 다시 띄운 테스트
