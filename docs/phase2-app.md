# 2단계 IVI 앱 (OpenCabin)

2026-11-13에 정리했습니다. 자동화 대상이 될 가상 IVI 앱입니다. 화면을 꾸미는 것보다 차량 신호와 맞닿는 부분, 그리고 테스트하기 쉬운 구조에 신경을 썼습니다.

## 구조

```
ivi-app/app/src/main/java/dev/opencabin/ivi/
  vehicle/VehicleDataSource.kt     화면이 보는 상태(VehicleState)와 차량 쪽 인터페이스
  vehicle/CarVehicleDataSource.kt  AAOS용. CarPropertyManager로 속도, 기어, 공조를, CarUxRestrictionsManager로 주행 중 제한을 읽음
  vehicle/MockVehicleDataSource.kt 일반 Android용. adb broadcast로 값을 넣고 읽음 (debug 빌드만)
  IviApp.kt                        FEATURE_AUTOMOTIVE를 보고 둘 중 하나를 고름
  MainActivity.kt                  홈, 공조, 미디어. 주행 중에도 쓰는 화면(distractionOptimized)
  VideoActivity.kt                 영상. 주행 중에 막혀야 하는 화면. 기기에 올린 주행 영상을 Media3로 재생
  ui/IviScreens.kt                 Compose 화면과 테스트 태그
ivi-app/privileged/                priv-app 설치 스크립트와 권한 허용 목록
```

## 화면과 테스트 태그

Compose의 `testTag`를 `testTagsAsResourceId = true`로 내보냅니다. 이렇게 하면 Appium에서 resource-id가 패키지 접두사 없이 태그 이름 그대로 보입니다(`nav_climate`). `By.ID`는 `dev.opencabin.ivi:id/`를 붙여서 찾기 때문에 실패하고, 그래서 `-android uiautomator`의 `new UiSelector().resourceId("nav_climate")`로 찾습니다.

| 화면 | 태그 |
|---|---|
| 공통 | `nav_home` `nav_climate` `nav_media` (5단계부터 아래 앱 바), `source_badge`(AAOS 또는 Mock), `restriction_banner`, `vehicle_disconnected`, `vehicle_error` |
| 주행 정보 (항상 보임) | `speed_value`, `gear_value` (5단계부터는 현재 기어 칸) |
| 홈 | `home_media_title`, `home_driver_temp`, `home_passenger_temp` |
| 공조 | `driver_temp_value` `driver_temp_up` `driver_temp_down`, 조수석은 `passenger_`로 시작하는 같은 이름. 권한이 없으면 `hvac_unavailable` |
| 미디어 | 곡 줄 `track_0`~`track_4`, 곡 제목 `track_N_title`(5단계에 추가), `now_playing_title`, `playback_state`, `play_pause`, `open_video`, 주행 중에는 `video_restricted_notice` |
| 영상 | `video_player` `video_elapsed` `video_close`, 앱이 막으면 `video_blocked`. 실제 영상을 틀면 `video_surface` `video_index`(`1 / 2`) `video_next`도 있습니다. |

## 주행 영상 (블랙박스, 2026-11-16 추가)

처음 만든 영상 화면은 그라데이션 위에 재생 시간만 흐르는 가짜였습니다. 지금은 앱 전용 폴더 `files/drive/`에 있는 mp4를 Media3(ExoPlayer)로 재생하고, 파일이 없을 때만 예전 가짜 화면을 보여 줍니다. 두 경우 모두 테스트 태그가 같아서, 기존 테스트는 영상이 있든 없든 그대로 돕니다.

영상은 직접 찍은 블랙박스 영상입니다. 번호판과 위치가 담긴 개인 자료라 저장소에는 넣지 않고(`.drive/`는 gitignore), `ivi-tests/tools/push_drive_videos.py --src <원본 폴더>`로 기기에만 올립니다.

올리기 전에 ffmpeg로 다듬습니다. 블랙박스는 1920x1080 화면 아래쪽, 보닛 위에 날짜와 제품명, GPS 좌표, 속도를 겹쳐 녹화합니다. 아래 81px와 오른쪽 거치대 쪽 144px를 잘라 16:9(1776x999)로 맞추고 1280x720으로 줄였습니다. 잘린 끝이 보닛 위라 화면이 어색하지 않습니다. 원본은 H.265인데 에뮬레이터가 HEVC를 소프트웨어로 풀면서 끊겨서 H.264로 바꿨고, 실내 대화가 담긴 음성과 메타데이터는 지웠습니다.

화면에서는 남는 자리 안에 16:9 영역을 가장 크게 잡고 모서리를 둥글게 잘랐습니다. `PlayerView`를 `texture_view`로 써야 Compose의 clip이 적용됩니다.

AAOS에서는 저장 위치가 까다로웠습니다. 현재 사용자가 10이라 `adb push /sdcard/...`로 올리면 사용자 0의 폴더에 들어가서 앱이 보지 못합니다. 셸에는 `/storage/emulated/10`에 쓸 권한도 없습니다. 그래서 root로 `/data/media/10/Android/data/<pkg>/files/drive/`에 넣고, 앱이 만든 폴더의 소유자(`u10_aNNN:ext_data_rw`)로 `chown`한 뒤 `restorecon`합니다.

주행으로 바뀌어 화면이 막히면 영상을 멈추고, 차를 세우면 멈춘 자리부터 이어서 재생합니다. AAOS는 OS가 화면을 막으면서 `onStop`과 `onStart`가 불리고, 태블릿은 같은 화면 안에서 `restricted` 값이 바뀝니다. `test_video_resumes_where_it_stopped`가 처음부터 다시 재생되지 않는지, 막혀 있는 동안 재생 시간이 흐르지 않는지를 함께 확인합니다.

## AAOS 에뮬레이터에서 확인한 것 (2026-11-13)

| 확인한 것 | 결과 |
|---|---|
| 속도와 기어 신호가 홈에 보이는지 | VHAL에 D, 13.9 m/s를 넣으면 `50 km/h`, `D`와 '주행 중 · 일부 기능 제한' 배지가 보입니다. |
| 공조 신호가 화면에 보이는지 | `set-property-value`로 운전석 25.0을 넣으면 `driver_temp_value`가 `25.0°C`가 됩니다. |
| 화면을 누르면 공조 신호가 바뀌는지 | 조수석 `+`를 한 번 누르면 property가 17.0에서 17.5가 됩니다. |
| 주행 중 영상 | `VideoActivity`를 열면 AAOS가 `ActivityBlockingActivity`("You can't use this feature while driving")로 막습니다. |
| 주행 중 메인 화면 | distractionOptimized로 선언해서 막히지 않습니다. |

## 공조 권한과 priv-app 설치

`CONTROL_CAR_CLIMATE`는 `signature|privileged` 권한입니다. 보통처럼 `adb install`로 설치하면 공조를 읽지도 쓰지도 못하고, 화면에는 `hvac_unavailable`이 보입니다. 이 상태도 테스트 케이스로 씁니다.

실제 IVI 앱처럼 시스템 이미지에 넣으려고 `privileged/install_priv_app.py`를 만들었습니다. 하는 일은 이렇습니다.

1. 에뮬레이터를 `-writable-system`으로 켭니다.
2. `adb root`와 `adb remount`를 합니다. 처음 한 번은 재부팅이 필요한데 스크립트가 알아서 합니다.
3. `/system/priv-app/OpenCabinIvi/`에 APK를, `/system/etc/permissions/`에 권한 허용 목록을 넣습니다.
4. 재부팅한 뒤 `PRIVILEGED` 플래그와 `CONTROL_CAR_CLIMATE: granted=true`를 확인하고, dangerous 권한인 `CAR_SPEED`는 `pm grant --user 10`으로 줍니다.

그 뒤로 코드를 고쳐서 `adb install -r`로 덮어써도 서명이 같으면 priv-app 권한이 유지됩니다.

## 태블릿(Mock) 제어 방법

```
쓰기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET \
        --ef speed_kmh 50 --es gear D --ef temp_driver 25 --ef temp_passenger 20
읽기  adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.GET
      → Broadcast completed: result=0, data="speed_kmh=50.0;gear=D;temp_driver=25.0;temp_passenger=22.0;restricted=true"
```

주행 중 제한 규칙은 AAOS 기본값과 맞췄습니다. 기어가 P가 아니고 속도가 0보다 크면 주행 중입니다.

태블릿에는 시스템 차단이 없어서 `VideoActivity`가 직접 `video_blocked` 화면을 보여 줍니다. 덕분에 "주행 중 영상 차단"을 두 기기에서 같은 테스트로 확인할 수 있습니다. 판정에 쓰는 요소만 다르고, AAOS는 `ActivityBlockingActivity`, 태블릿은 `video_blocked`를 봅니다.

## 화웨이 태블릿에서 확인한 것 (DBY-W09, Android 12 기반, 2026-11-13)

| 확인한 것 | 결과 |
|---|---|
| 데이터 소스 | `source_badge`가 `Mock`입니다. |
| Mock에 쓰고 읽기 | SET 뒤 GET이 `speed_kmh=50.0;gear=D;…;restricted=true`이고, 정차로 돌리면 `restricted=false`가 됩니다. |
| 신호가 화면에 보이는지 | `temp_driver=25`를 넣으면 `driver_temp_value`가 `25.0°C`가 됩니다. |
| 화면을 누르면 신호가 바뀌는지 | 조수석 `+`를 한 번 누르면 GET의 `temp_passenger`가 22.0에서 22.5가 됩니다. |
| 주행 표시 | `50`, `D`, `restriction_banner`가 보입니다. |
| 주행 중 미디어 | `open_video`가 꺼지고 `video_restricted_notice`가 보입니다. |
| 주행 중에 영상 화면을 바로 열면 | `video_blocked`가 보이고 `video_player`는 없습니다. |
| 정차로 바꾸면 | 같은 화면이 `video_player`로 바뀌고 `open_video`도 다시 켜집니다. |
| Appium 세션 | 약 4.6초. AAOS용 설정 없이 기본 UiAutomator2로 됩니다. |

### 화웨이 기기에서 주의할 점

adb로 앱을 설치할 때마다 기기 화면에서 승인해야 합니다. 아무도 누르지 않으면 `INSTALL_FAILED_ABORTED: User rejected permissions`로 끝납니다.

Appium은 처음 연결할 때 보조 앱 세 개(`io.appium.settings`, `io.appium.uiautomator2.server`, `…server.test`)를 설치합니다. 승인이 늦으면 `uiautomator2ServerInstallTimeout`(기본 2분)에 걸려 세션이 실패하고, 마지막 테스트 APK만 빠진 채로 남기도 합니다. 그럴 때는 `pm list instrumentation`으로 확인하고 직접 설치합니다.

무인 실행(CI)에서는 승인할 사람이 없습니다. 그래서 보조 앱과 테스트 대상 앱은 실행 전에 미리 설치해 두고, 테스트 중에는 다시 설치하지 않게 했습니다. `no_reset`을 쓰고, 버전이 같으면 Appium이 설치를 건너뜁니다.

## 만들면서 고친 것

| 문제 | 원인 | 해결 |
|---|---|---|
| Gradle이 `Your project path contains non-ASCII characters`로 멈췄습니다. | 사용자 폴더 경로에 한글이 있습니다. | 프로젝트를 `C:\dev\opencabin-ivi`로, Gradle 캐시를 `GRADLE_USER_HOME=C:\dev\.gradle`로 옮겼습니다. |
| 속도 숫자가 검은 글자라 보이지 않았습니다. | Surface 없이 그린 Text의 기본 색이 검정입니다. | 테마에서 `LocalContentColor`를 밝은 색으로 바꿨습니다. |
| `screencap` 결과가 PNG가 아니었습니다. | 디스플레이가 메인과 클러스터 두 개입니다. | `dumpsys SurfaceFlinger --display-id`로 id를 찾아 `screencap -d <display id>`로 찍습니다. |

## 빌드

```powershell
cd C:\dev\opencabin-ivi\ivi-app
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:GRADLE_USER_HOME = "C:\dev\.gradle"
.\gradlew assembleDebug
```
