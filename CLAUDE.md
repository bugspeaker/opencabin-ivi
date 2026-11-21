# OpenCabin IVI

AAOS 인포테인먼트 화면과 차량 신호(CarProperty/VHAL)를 E2E로 확인하는 pytest 프레임워크와, 그 테스트 대상인 가상 IVI 앱입니다.
같은 테스트를 AAOS 에뮬레이터(CarService, 에뮬레이터 VHAL)와 화웨이 태블릿(앱 안 Mock 차량)에서 돌립니다.
공개 저장소(`bugspeaker/opencabin-ivi`)이고, 채용 지원용 포트폴리오입니다. 소개 사이트: https://bugspeaker.github.io/opencabin-ivi/

## 구성

| 폴더 | 내용 |
|---|---|
| `ivi-app/` | Kotlin, Jetpack Compose 앱 (`dev.opencabin.ivi`). `privileged/`는 에뮬레이터에 priv-app으로 넣는 스크립트와 VHAL 설정 덮어쓰기 |
| `ivi-tests/ivi/` | 프레임워크: adb, 대기(`waits.py`), 차량 어댑터, 기기, 화면 객체(`screens.py`), 결과 기록, 격리, Bench API, 전원, CAN 게이트웨이 |
| `ivi-tests/tests/` | 기기 E2E 테스트와 `conftest.py` (pytest 기본 경로) |
| `ivi-tests/unit/` | 기기 없이 도는 프레임워크 단위 테스트 |
| `ivi-tests/tools/` | 두 기기 병렬 실행, flaky 통계, Release 게이트, 결과 사이트, 추적표 등 |
| `docs/` | 포트폴리오, 단계별 기록(phase1~9), 요구사항과 추적표, 결정 기록, 원자료(`evidence/`) |
| `site/` | 소개 사이트. `site/docs/*.html`은 `build-docs.mjs`가 만든 파일 |

## 이 PC의 환경 (Windows)

- 사용자 폴더가 한글 경로라 Android, Gradle 도구가 실패합니다. 저장소, AVD, Gradle 홈, 임시 폴더를 모두 영문 경로에 둡니다.
- 워크트리에는 `ivi-tests/.venv`와 `ivi-app/local.properties`가 없습니다(gitignore). 메인 체크아웃의 venv를 쓰고, `local.properties`는 만들어 씁니다.
  - Python: `C:\dev\opencabin-ivi\ivi-tests\.venv\Scripts\python` (워크트리의 `ivi-tests`에서 실행하면 워크트리 코드를 씁니다)
  - `ivi-app/local.properties`: `sdk.dir=C:/android`
- Android SDK `C:\android`, AVD `C:\android\avd`의 `OpenCabin_AAOS_34`(API 34).
- 기기 serial: AAOS 에뮬레이터 `emulator-5554`, 화웨이 태블릿 `W3VBB22125209573`.
- CI는 Python 3.12, JDK 17입니다.

## 명령

모두 PowerShell 기준입니다. `$py`는 위 venv의 python입니다.

```powershell
$py = "C:\dev\opencabin-ivi\ivi-tests\.venv\Scripts\python"

# 프레임워크 단위 테스트 (ivi-tests 에서, 기기 없음, 약 10초)
& $py -m pytest unit

# 앱 단위 테스트 (ivi-app 에서). Gradle 홈과 임시 폴더를 영문 경로로 바꿔야 돕니다
$env:GRADLE_USER_HOME = "C:\dev\.gradle"; $env:TMP = "C:\dev\.tmp"; $env:TEMP = $env:TMP
.\gradlew testDebugUnitTest
.\gradlew assembleDebug        # APK: app\build\outputs\apk\debug\app-debug.apk

# 요구사항 추적표 다시 만들기 (ivi-tests 에서) → docs/traceability.md
& $py tools\trace_report.py

# 사이트 문서 다시 만들기 (site 에서) → site/docs/*.html, site/index.html 의 자동 생성 구역
npm install; npm run build-docs
```

E2E는 기기와 Appium 서버가 있어야 돕니다(자세한 준비는 `docs/run.md`).

```powershell
# 준비 확인
adb devices
Invoke-RestMethod http://127.0.0.1:4723/status      # Appium (없으면: $env:ANDROID_HOME = "C:\android"; appium --address 127.0.0.1 --port 4723)

# ivi-tests 에서
& $py -m pytest --serial emulator-5554 -m smoke      # smoke 13개, 기기당 약 45초
& $py -m pytest --serial emulator-5554               # 전체 129개, 기기당 약 10분
& $py tools\run_bench.py -m "smoke or sanity" --reruns 1   # 연결된 기기 모두 병렬
& $py tools\run_bench.py --repeat 5 --reruns 1             # 반복 실행 (안정성)
& $py tools\release_gate.py --since <yyyyMMdd-HHmmss> --expect <반복 수>
& $py tools\flaky_report.py --last 5
```

- 전체 E2E는 오래 걸리니 백그라운드로 돌립니다. 결과는 `ivi-tests/reports/`(gitignore)에 남습니다.
- 에뮬레이터를 켜거나 재부팅하는 일(`tools/emulator_defaults.py --persist`, `privileged/install_priv_app.py`)은 먼저 묻습니다.
- 기기가 없어서 E2E를 못 돌렸으면 그렇다고 말합니다. 단위 테스트 통과를 E2E 통과처럼 쓰지 않습니다.

## 코드 스타일

공통
- 주석, docstring, 오류 메시지, 문서는 한국어로 씁니다. 식별자(함수, 변수, 파일 이름)는 영어 snake_case(Python), camelCase(Kotlin)입니다.
- 주석은 '무엇'보다 '왜'를 적습니다. 기기에서 겪은 일이 이유라면 날짜와 증상을 함께 적습니다(예: `2026-11-19: 막 켠 에뮬레이터에서 ...`).
- 줄 끝은 LF입니다(`.bat`, `.ps1`만 CRLF, `.gitattributes`). 한 줄은 대략 120자 안쪽입니다.
- 포매터나 린터 설정은 없습니다. 주변 코드 모양을 따릅니다.

E2E 테스트 (`ivi-tests/tests/`)
- 테스트마다 게이트 마커 하나(`smoke`, `sanity`, `regression`)와 `@pytest.mark.req("ID", ...)`를 붙입니다. ID는 `docs/requirements.md` 표에 있어야 합니다. 요구사항 없는 테스트나 테스트 없는 요구사항이 생기면 `unit/test_operations.py`가 실패합니다.
- AAOS에서만 뜻이 있는 테스트는 `aaos`, 기기 전원을 껐다 켜는 테스트는 `power` 마커를 붙입니다.
- docstring은 결과 사이트에 그대로 나오는 설명입니다. 화면과 차량에서 무엇이 어떻게 되는지 한국어 문장으로 씁니다.
- 고정 `sleep`을 쓰지 않습니다. `ivi.waits`의 `wait_until`, `wait_value`(실패 때 마지막 값을 남김), `stays`(일정 시간 그대로인지)를 씁니다. 대기는 다시 볼 예외만 기다리고 코드 오류는 바로 올립니다.
- 화면 요소는 `ivi/screens.py`의 화면 객체로만 다룹니다. 태그 이름은 앱의 Compose `testTag`(snake_case, 예: `nav_climate`, `driver_temp_up`)와 같아야 합니다. 앱 태그를 바꾸면 화면 객체도 함께 바꿉니다.
- 기기 차이(VHAL과 Mock, adb 탭과 Appium 탭)는 `Device`와 차량 어댑터 안에서 처리하고, 테스트 코드는 두 기기에서 같게 둡니다.
- 플랫폼 결함은 `xfail(strict=True)`로 걸고 `known_defects.txt`에 적습니다. flaky는 `quarantine.txt`(네 칸 형식, 2줄 이하)에 사람이 올립니다.

앱 (`ivi-app/`)
- Kotlin 공식 스타일(`kotlin.code.style=official`), Compose, minSdk 31, targetSdk 34, `useLibrary("android.car")`.
- 차량 값은 `VehicleDataSource`를 거칩니다. AAOS는 `CarVehicleDataSource`, 그 밖의 기기는 `MockVehicleDataSource`입니다.
- 테스트만을 위한 코드는 debug 소스셋(`src/debug/`, 예: `TestHookReceiver`)에 둡니다.
- 규칙 로직(어시스턴트, `HvacSpec` 등)은 JVM 단위 테스트(`src/test/`)로 확인합니다.

## 문서와 숫자

- 테스트 수, 단위 테스트 수, 요구사항 수, 실행 시간 같은 숫자는 README, `docs/portfolio.md`, 단계별 기록, `ivi-ci.yml` 주석 등 여러 곳에 손으로 적혀 있습니다. 숫자를 바꾸는 변경이면 `git grep`으로 모든 곳을 찾아 함께 고칩니다.
- `site/index.html`에서 `<!-- fit:start … -->`~`<!-- fit:end -->`처럼 `fit`, `stats`, `devices` 표시 사이 구역과 `site/docs/*.html`은 `build-docs`가 만듭니다. 손으로 고치지 말고, `docs/*.md`나 README를 고쳤으면 `npm run build-docs`를 돌려 생성된 HTML도 같이 커밋합니다.
- 테스트나 `@pytest.mark.req`를 바꿨으면 `tools/trace_report.py`로 `docs/traceability.md`를 다시 만듭니다.
- 결과 수치는 실제 실행 파일에서만 가져옵니다. 문서에 새 결과를 인용하면 원자료(`reports/runs/*.json`)를 `docs/evidence/<날짜>-<주제>/`에 README와 함께 남기고, 파일 안의 사용자 경로는 `%USERPROFILE%`로 바꿉니다.
- 방향을 정한 판단(무엇을 고르고 무엇을 버렸는지, 근거가 된 측정값)은 `docs/decisions.md`에 번호를 붙여 더합니다(상황, 고른 것, 버린 것, 근거, 결과).
- 문서 문장은 '~습니다'체, 코드 주석은 '~한다'체입니다. 짧은 문장, 측정값과 날짜, 근거 링크를 씁니다.

용어와 표기
- 이 프로젝트는 실제 차량, HIL, CAN 장비를 쓰지 않습니다. '차량 신호'는 에뮬레이터 VHAL(CarService)을 뜻하고, CAN과 원격 전원은 PC 안의 모의 환경이라고 분명히 씁니다.
- 앱 왼쪽 영역은 '주행 정보 패널'이라고 부릅니다('클러스터'라고 쓰지 않습니다).
- 다른 회사의 제품 이름이나 화면을 그대로 가져와 쓰지 않습니다.
- '만든 사람과 만든 방식' 문장(기간, 배경, 코드는 거의 전부 AI 코딩 도구가 작성)은 README, `docs/portfolio.md`, `site/index.html` 세 곳이 같아야 합니다. 바꿀 때는 세 곳을 함께 고칩니다. '직접 만들었다', '직접 구축했다' 같은 표현은 쓰지 않습니다.

## Git과 PR

- 작업은 `claude/<주제>` 브랜치에서 하고 PR로 올립니다. PR은 사용자가 실행 결과와 변경 내용을 확인하고 병합합니다. 직접 병합하지 않습니다.
- 커밋 메시지는 한국어입니다. 첫 줄에 바꾼 것을 한 줄로, 본문에 왜 바꿨는지와 바꾼 것(`- ` 목록), 기기에서 확인한 결과를 적습니다. 외부 검토 항목을 반영했으면 `(검토 F12)`처럼 번호를 붙입니다.
- 비공개 자료는 `.git/info/exclude`와 `.gitignore`(예: 블랙박스 영상 `.drive/`)로 빠져 있습니다. `git add -A`나 `git add .` 대신 파일 이름을 적어서 추가하고, 커밋 전에 `git status`로 확인합니다.
- 공개 저장소라 self-hosted 러너를 붙이지 않습니다. CI의 e2e job은 저장소 변수 `IVI_BENCH == 'online'`일 때만 돌고, 지금은 GitHub에서 build와 unit만 돕니다.
