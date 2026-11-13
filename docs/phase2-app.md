# 2단계 IVI 앱 (OpenCabin)

작성 2026-11-13. 자동화 대상이 될 가상 IVI 앱. 화면보다 **차량 신호와의 경계**와 **테스트하기 쉬운 구조**에 집중했다.

## 구조

```
ivi-app/app/src/main/java/dev/opencabin/ivi/
  vehicle/VehicleDataSource.kt     화면이 보는 상태(VehicleState)와 경계 인터페이스
  vehicle/CarVehicleDataSource.kt  AAOS: CarPropertyManager(속도·기어·공조) + CarUxRestrictionsManager(주행 중 제한)
  vehicle/MockVehicleDataSource.kt 일반 Android: adb broadcast 로 값을 넣고 읽는다 (debug 빌드만)
  IviApp.kt                        FEATURE_AUTOMOTIVE 로 둘 중 하나를 고른다
  MainActivity.kt                  홈 · 공조 · 미디어 (distractionOptimized = 주행 중에도 사용)
  VideoActivity.kt                 영상 (DO 아님 = 주행 중 차단 대상)
  ui/IviScreens.kt                 Compose 화면, 테스트 태그
ivi-app/privileged/                priv-app 설치 스크립트와 권한 허용 목록
```

## 화면과 테스트 태그

Compose `testTag` 를 `testTagsAsResourceId = true` 로 노출한다. Appium 에서는 resource-id 가 **패키지 접두사 없이** 태그 그대로다 (`nav_climate`).
그래서 `By.ID` 대신 `-android uiautomator` 의 `new UiSelector().resourceId("nav_climate")` 로 찾는다 (`By.ID` 는 `dev.opencabin.ivi:id/` 를 붙여 찾아서 실패).

| 화면 | 태그 |
|---|---|
| 공통 | `nav_home` `nav_climate` `nav_media`, `source_badge`(AAOS/Mock), `restriction_banner`, `vehicle_disconnected`, `vehicle_error` |
| 홈 | `speed_value`, `gear_value`, `home_driver_temp`, `home_passenger_temp` |
| 공조 | `driver_temp_value` `driver_temp_up` `driver_temp_down`, `passenger_…` 같은 형식, 권한 없으면 `hvac_unavailable` |
| 미디어 | `track_0`~`track_4`, `now_playing_title`, `playback_state`, `play_pause`, `open_video`, 주행 중 `video_restricted_notice` |
| 영상 | `video_player` `video_elapsed` `video_close`, 앱이 막으면 `video_blocked` |

## AAOS 에서 확인한 것 (에뮬레이터, 2026-11-13)

| 확인 | 결과 |
|---|---|
| 속도·기어 신호 → 홈 | VHAL 에 D, 13.9 m/s → `50 km/h`, `D`, '주행 중 · 일부 기능 제한' 배지 |
| 공조 신호 → 화면 | `set-property-value` 운전석 25.0 → `driver_temp_value` = `25.0°C` |
| 화면 → 공조 신호 | 조수석 `+` 1회 → property 17.0 → 17.5 |
| 주행 중 영상 | `VideoActivity` 를 열면 AAOS 가 `ActivityBlockingActivity` ("You can't use this feature while driving") 로 막음 |
| 주행 중 메인 화면 | DO 선언이라 막히지 않음 |

## 공조 권한: priv-app 설치

- `CONTROL_CAR_CLIMATE` 는 `signature|privileged`. 일반 설치(`adb install`)로는 공조를 읽지도 쓰지도 못한다 → 화면이 `hvac_unavailable` 을 보여 준다 (이것도 테스트 케이스가 된다).
- 실제 IVI 앱처럼 시스템 이미지에 넣는다: `privileged/install_priv_app.py`
  1. 에뮬레이터를 `-writable-system` 으로 실행
  2. `adb root` → `adb remount` (처음 한 번은 재부팅 필요, 스크립트가 처리)
  3. `/system/priv-app/OpenCabinIvi/` 에 APK, `/system/etc/permissions/` 에 권한 허용 목록
  4. 재부팅 후 `PRIVILEGED` 플래그와 `CONTROL_CAR_CLIMATE: granted=true` 확인, `CAR_SPEED`(dangerous)는 `pm grant --user 10`
- 이후 코드를 고치면 `adb install -r` 로 덮어써도 서명이 같아서 priv-app 권한이 유지된다.

## Mock (태블릿) 제어 규약

```
쓰기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET \
        --ef speed_kmh 50 --es gear D --ef temp_driver 25 --ef temp_passenger 20
읽기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.GET
      → Broadcast completed: result=0, data="speed_kmh=50.0;gear=D;temp_driver=25.0;temp_passenger=22.0;restricted=true"
```
- 주행 중 제한 규칙은 AAOS 기본과 맞춘다: 기어가 P 가 아니고 속도 > 0.
- 태블릿에는 시스템 차단이 없으므로 `VideoActivity` 가 직접 `video_blocked` 를 보여 준다. 두 기기 모두 "주행 중 영상 차단" 을 같은 테스트로 확인할 수 있다 (판정 요소만 다르다: AAOS = `ActivityBlockingActivity`, 태블릿 = `video_blocked`).

## 태블릿에서 확인한 것 (화웨이 DBY-W09, Android 12 기반, 2026-11-13)

| 확인 | 결과 |
|---|---|
| 데이터 소스 | `source_badge` = `Mock` |
| Mock 쓰기·읽기 | SET 후 GET 이 `speed_kmh=50.0;gear=D;…;restricted=true`, 정차로 돌리면 `restricted=false` |
| 신호 → 화면 | `temp_driver=25` → `driver_temp_value` = `25.0°C` |
| 화면 → 신호 | 조수석 `+` 1회 → GET 의 `temp_passenger` 22.0 → 22.5 |
| 주행 표시 | `50`, `D`, `restriction_banner` 표시 |
| 주행 중 미디어 | `open_video` 비활성, `video_restricted_notice` 표시 |
| 주행 중 영상 직접 실행 | `video_blocked` 표시, `video_player` 없음 |
| 정차로 바꾸면 | 같은 화면이 `video_player` 로 바뀜, `open_video` 다시 활성 |
| Appium 세션 | 약 4.6초 (AAOS 전용 설정 없이 기본 UiAutomator2) |

### 화웨이 기기 주의

- adb 로 앱을 설치할 때마다 **기기 화면에서 승인**해야 한다. 아무도 누르지 않으면 `INSTALL_FAILED_ABORTED: User rejected permissions`.
- Appium 첫 연결 때 보조 앱 3개(`io.appium.settings`, `io.appium.uiautomator2.server`, `…server.test`)를 설치한다. 승인이 늦으면
  `uiautomator2ServerInstallTimeout`(기본 2분)에 걸려 세션이 실패하고, 마지막 테스트 APK 만 빠진 채로 남을 수 있다 → `pm list instrumentation` 으로 확인하고 직접 설치한다.
- 무인 실행(CI)에서는 승인할 사람이 없으므로, 보조 앱과 테스트 대상 앱은 **실행 전에 미리 설치**해 두고 테스트 단계에서는 재설치하지 않게 한다 (`no_reset`, 버전이 같으면 Appium 이 건너뛴다).

## 만들면서 고친 것

| 문제 | 원인 | 해결 |
|---|---|---|
| Gradle: `Your project path contains non-ASCII characters` | 사용자 폴더에 한글 | 프로젝트를 `C:\dev\opencabin-ivi`, Gradle 캐시를 `GRADLE_USER_HOME=C:\dev\.gradle` 로 |
| 속도 숫자가 안 보임 (검은 글자) | Surface 없이 그린 Text 의 기본 색이 검정 | 테마에서 `LocalContentColor` 를 밝은 색으로 |
| `screencap` 결과가 PNG 가 아님 | 디스플레이가 2개 (메인 + 클러스터) | `screencap -d <display id>` (`dumpsys SurfaceFlinger --display-id`) |

## 빌드

```powershell
cd C:\dev\opencabin-ivi\ivi-app
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:GRADLE_USER_HOME = "C:\dev\.gradle"
.\gradlew assembleDebug
```
