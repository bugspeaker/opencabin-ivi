# 2단계 IVI 앱 (OpenCabin)

작성 2026-11-13. 자동화 대상이 될 가상 IVI 앱. 화면보다 차량 신호와의 경계와 테스트하기 쉬운 구조에 집중했다.

## 구조

```
ivi-app/app/src/main/java/dev/opencabin/ivi/
  vehicle/VehicleDataSource.kt     화면이 보는 상태(VehicleState)와 경계 인터페이스
  vehicle/CarVehicleDataSource.kt  AAOS: CarPropertyManager(속도·기어·공조) + CarUxRestrictionsManager(주행 중 제한)
  vehicle/MockVehicleDataSource.kt 일반 Android: adb broadcast 로 값을 넣고 읽는다 (debug 빌드만)
  IviApp.kt                        FEATURE_AUTOMOTIVE 로 둘 중 하나를 고른다
  MainActivity.kt                  홈 · 공조 · 미디어 (distractionOptimized = 주행 중에도 사용)
  VideoActivity.kt                 영상 (DO 아님 = 주행 중 차단 대상). Media3 로 기기에 올린 주행 영상 재생, 없으면 가짜 화면
  ui/IviScreens.kt                 Compose 화면, 테스트 태그
ivi-app/privileged/                priv-app 설치 스크립트와 권한 허용 목록
```

## 화면과 테스트 태그

Compose `testTag`를 `testTagsAsResourceId = true`로 노출한다. Appium에서는 resource-id가 패키지 접두사 없이 태그 그대로다 (`nav_climate`).
그래서 `By.ID` 대신 `-android uiautomator`의 `new UiSelector().resourceId("nav_climate")`로 찾는다 (`By.ID`는 `dev.opencabin.ivi:id/`를 붙여 찾아서 실패).

| 화면 | 태그 |
|---|---|
| 공통 | `nav_home` `nav_climate` `nav_media` (5단계부터 아래 앱 바), `source_badge`(AAOS/Mock), `restriction_banner`, `vehicle_disconnected`, `vehicle_error` |
| 주행 정보(항상 보임) | `speed_value`, `gear_value` (5단계부터 지금 기어 칸 자체) |
| 홈 | `home_media_title`, `home_driver_temp`, `home_passenger_temp` |
| 공조 | `driver_temp_value` `driver_temp_up` `driver_temp_down`, `passenger_…` 같은 형식, 권한 없으면 `hvac_unavailable` |
| 미디어 | `track_0`~`track_4` (줄), `track_N_title` (제목, 5단계 추가), `now_playing_title`, `playback_state`, `play_pause`, `open_video`, 주행 중 `video_restricted_notice` |
| 영상 | `video_player` `video_elapsed` `video_close`, 앱이 막으면 `video_blocked`. 실제 영상이면 `video_surface` `video_index`(`1 / 2`) `video_next` |

## 주행 영상 (블랙박스, 2026-11-16 추가)

영상 화면은 원래 그라데이션에 재생 시간만 흐르는 가짜였다. 지금은 앱 전용 폴더 `files/drive/`의 mp4를 Media3(ExoPlayer)로 재생하고, 파일이 없으면 예전 가짜 화면을 보여 준다. 테스트 태그는 두 경우가 같아서 기존 테스트는 영상 유무와 상관없이 돈다.

- **올리기**: `ivi-tests/tools/push_drive_videos.py --src <원본 폴더>`. 원본은 `.drive/`(gitignore, 번호판·위치가 담긴 개인 자료).
- **다듬기 (ffmpeg)**: 블랙박스(1920x1080)는 화면 아래에 날짜·제품명·GPS 좌표·속도 줄을 보닛 위에 겹쳐 녹화한다. 아래 81px와 오른쪽 거치대 쪽 144px를 잘라 16:9(1776x999)로 맞춘 뒤 1280x720으로 줄인다. 잘린 끝이 보닛 위라 어색하지 않다.
- **코덱**: 원본은 H.265. 에뮬레이터는 HEVC를 소프트웨어로 풀어 끊기므로 H.264로 바꾼다. 음성(실내 대화)과 메타데이터는 지운다.
- **화면**: 남는 자리 안에서 16:9를 가장 크게 잡고 둥근 모서리로 자른다 (`PlayerView`를 `texture_view`로 써야 Compose clip이 먹는다).
- **AAOS 저장 위치**: 현재 사용자가 10이라 `adb push /sdcard/...`(사용자 0)로는 앱이 못 보고, 셸은 `/storage/emulated/10`에 쓸 권한이 없다. root로 `/data/media/10/Android/data/<pkg>/files/drive/`에 넣고, 앱이 만든 폴더의 소유자(`u10_aNNN:ext_data_rw`)로 `chown`, `restorecon`한다.
- **주행 전환**: 막히면 멈추고 정차하면 그 자리에서 이어서 재생한다. AAOS는 OS 차단으로 `onStop`/`onStart`, 태블릿은 같은 화면 안의 `restricted` 변화로 처리한다. `test_video_resumes_where_it_stopped`가 '처음부터 다시 재생되지 않음'과 '막힌 동안 재생이 흐르지 않음'을 함께 확인한다.

## AAOS에서 확인한 것 (에뮬레이터, 2026-11-13)

| 확인 | 결과 |
|---|---|
| 속도·기어 신호 → 홈 | VHAL에 D, 13.9 m/s → `50 km/h`, `D`, '주행 중 · 일부 기능 제한' 배지 |
| 공조 신호 → 화면 | `set-property-value` 운전석 25.0 → `driver_temp_value` = `25.0°C` |
| 화면 → 공조 신호 | 조수석 `+` 1회 → property 17.0 → 17.5 |
| 주행 중 영상 | `VideoActivity`를 열면 AAOS가 `ActivityBlockingActivity` ("You can't use this feature while driving")로 막음 |
| 주행 중 메인 화면 | DO 선언이라 막히지 않음 |

## 공조 권한: priv-app 설치

- `CONTROL_CAR_CLIMATE`는 `signature|privileged`. 일반 설치(`adb install`)로는 공조를 읽지도 쓰지도 못하고, 화면은 `hvac_unavailable`을 보여 준다. 이 상태도 테스트 케이스로 쓴다.
- 실제 IVI 앱처럼 시스템 이미지에 넣는다: `privileged/install_priv_app.py`
  1. 에뮬레이터를 `-writable-system`으로 실행
  2. `adb root` → `adb remount` (처음 한 번은 재부팅 필요, 스크립트가 처리)
  3. `/system/priv-app/OpenCabinIvi/`에 APK, `/system/etc/permissions/`에 권한 허용 목록
  4. 재부팅 후 `PRIVILEGED` 플래그와 `CONTROL_CAR_CLIMATE: granted=true` 확인, `CAR_SPEED`(dangerous)는 `pm grant --user 10`
- 이후 코드를 고치면 `adb install -r`로 덮어써도 서명이 같아서 priv-app 권한이 유지된다.

## Mock (태블릿) 제어 규약

```
쓰기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET \
        --ef speed_kmh 50 --es gear D --ef temp_driver 25 --ef temp_passenger 20
읽기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.GET
      → Broadcast completed: result=0, data="speed_kmh=50.0;gear=D;temp_driver=25.0;temp_passenger=22.0;restricted=true"
```
- 주행 중 제한 규칙은 AAOS 기본과 맞춘다: 기어가 P가 아니고 속도 > 0.
- 태블릿에는 시스템 차단이 없으므로 `VideoActivity`가 직접 `video_blocked`를 보여 준다. 두 기기 모두 "주행 중 영상 차단"을 같은 테스트로 확인할 수 있다 (판정 요소만 다르다: AAOS = `ActivityBlockingActivity`, 태블릿 = `video_blocked`).

## 태블릿에서 확인한 것 (화웨이 DBY-W09, Android 12 기반, 2026-11-13)

| 확인 | 결과 |
|---|---|
| 데이터 소스 | `source_badge` = `Mock` |
| Mock 쓰기·읽기 | SET 후 GET이 `speed_kmh=50.0;gear=D;…;restricted=true`, 정차로 돌리면 `restricted=false` |
| 신호 → 화면 | `temp_driver=25` → `driver_temp_value` = `25.0°C` |
| 화면 → 신호 | 조수석 `+` 1회 → GET의 `temp_passenger` 22.0 → 22.5 |
| 주행 표시 | `50`, `D`, `restriction_banner` 표시 |
| 주행 중 미디어 | `open_video` 비활성, `video_restricted_notice` 표시 |
| 주행 중 영상 직접 실행 | `video_blocked` 표시, `video_player` 없음 |
| 정차로 바꾸면 | 같은 화면이 `video_player`로 바뀜, `open_video` 다시 활성 |
| Appium 세션 | 약 4.6초 (AAOS 전용 설정 없이 기본 UiAutomator2) |

### 화웨이 기기 주의

- adb로 앱을 설치할 때마다 기기 화면에서 승인해야 한다. 아무도 누르지 않으면 `INSTALL_FAILED_ABORTED: User rejected permissions`.
- Appium 첫 연결 때 보조 앱 3개(`io.appium.settings`, `io.appium.uiautomator2.server`, `…server.test`)를 설치한다. 승인이 늦으면
  `uiautomator2ServerInstallTimeout`(기본 2분)에 걸려 세션이 실패하고, 마지막 테스트 APK만 빠진 채로 남을 수 있다. 그럴 때는 `pm list instrumentation`으로 확인하고 직접 설치한다.
- 무인 실행(CI)에서는 승인할 사람이 없으므로, 보조 앱과 테스트 대상 앱은 실행 전에 미리 설치해 두고 테스트 단계에서는 재설치하지 않게 한다 (`no_reset`, 버전이 같으면 Appium이 건너뛴다).

## 만들면서 고친 것

| 문제 | 원인 | 해결 |
|---|---|---|
| Gradle: `Your project path contains non-ASCII characters` | 사용자 폴더에 한글 | 프로젝트를 `C:\dev\opencabin-ivi`, Gradle 캐시를 `GRADLE_USER_HOME=C:\dev\.gradle`로 |
| 속도 숫자가 안 보임 (검은 글자) | Surface 없이 그린 Text의 기본 색이 검정 | 테마에서 `LocalContentColor`를 밝은 색으로 |
| `screencap` 결과가 PNG가 아님 | 디스플레이가 2개 (메인 + 클러스터) | `screencap -d <display id>` (`dumpsys SurfaceFlinger --display-id`) |

## 빌드

```powershell
cd C:\dev\opencabin-ivi\ivi-app
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:GRADLE_USER_HOME = "C:\dev\.gradle"
.\gradlew assembleDebug
```
