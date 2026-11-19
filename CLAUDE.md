# CLAUDE.md

AAOS 인포테인먼트(IVI) 테스트 자동화 포트폴리오입니다. 직접 만든 IVI 앱(`ivi-app`)을 pytest + Appium E2E(`ivi-tests`)로 AAOS 에뮬레이터(CarService/VHAL)와 화웨이 태블릿(앱 안 Mock 차량)에서 같은 코드로 돌립니다.
채용 공고에 맞춘 포트폴리오라서 문서와 사이트의 모든 주장과 숫자는 실제 실행 결과와 맞아야 합니다.

## 저장소 구성

- `ivi-app/`: Kotlin + Compose 앱. 패키지는 `dev.opencabin.ivi`. `privileged/`에는 priv-app 설치 스크립트가 있음
- `ivi-tests/`: `ivi/`(프레임워크), `tests/`(기기 E2E), `unit/`(기기 없이 도는 프레임워크 테스트), `tools/`(병렬 실행, 통계, 결과 사이트, 추적표), `dbc/`
- `docs/`: 포트폴리오, 단계별 기록(phase1~9), 요구사항, 추적표, 결정 기록, 실행 방법(`run.md`)
- `site/`: GitHub Pages 소개 사이트. `build-docs.mjs`가 `docs/*.md`와 `README.md`를 HTML로 바꿈

## 클라우드 세션에서 되는 것과 안 되는 것

- **됨**: 프레임워크 단위 테스트(Linux에서 71개 통과 확인, 약 10초), 사이트 빌드(Node 22), 추적표 생성
- **안 됨**: E2E. adb 기기, Appium, AAOS 에뮬레이터가 없습니다. Android SDK가 없어서 Gradle 앱 빌드도 안 되고, 그 확인은 CI의 `build` job이 합니다.
- E2E 결과, 개수, 시간, flaky 수치를 추정하거나 지어내지 않습니다. 기기 실행이 필요하면 사용자가 Windows Test Bench에서 돌릴 명령을 알려 줍니다(`docs/run.md`).

## 명령

프레임워크 단위 테스트 (CI `unit` job과 같음, Python 3.12):

```bash
cd ivi-tests && python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest unit
```

앱 빌드와 앱 단위 테스트 (CI `build` job과 같음, Android SDK platform 35 + JDK 17 필요):

```bash
cd ivi-app && ./gradlew assembleDebug --no-daemon && ./gradlew testDebugUnitTest --no-daemon
```

추적표와 사이트 다시 만들기:

```bash
cd ivi-tests && .venv/bin/python tools/trace_report.py      # docs/traceability.md
cd site && npm install && npm run build-docs                # site/docs/*.html, site/index.html 안의 생성 구간
```

Windows Test Bench에서 사용자가 돌리는 E2E (`ivi-tests`에서):

```powershell
.venv\Scripts\python -m pytest --serial emulator-5554 -m smoke
.venv\Scripts\python tools\run_bench.py -m "smoke or sanity" --reruns 1     # 두 기기 병렬
.venv\Scripts\python tools\run_bench.py --repeat 5 --reruns 1 --shots       # 반복 + 결과 사이트용 화면
```

`pytest`의 기본 `testpaths`는 `tests`(기기 E2E)입니다. 기기 없이 돌릴 때는 반드시 `pytest unit`으로 경로를 줍니다.

## CI (`.github/workflows/`)

- `ivi-ci.yml`: `build`와 `unit`은 모든 PR과 push에서 GitHub 호스트로 돕니다. `e2e`는 저장소 변수 `IVI_BENCH=online`일 때만 self-hosted Windows 러너에서 돌고, 지금은 GitHub에서 돌지 않습니다.
- 공개 저장소라 다음 보호는 유지합니다. 포크 PR은 `e2e`를 돌리지 않고, `workflow_dispatch` 입력은 스크립트에 바로 넣지 않고 `env`로 넘깁니다.
- `pages.yml`: `site/**`, `docs/images/**`가 main에 바뀌면 배포합니다.

## E2E 테스트를 쓸 때

- 테스트 함수마다 `@pytest.mark.req("ID")`를 붙이고, ID는 `docs/requirements.md` 표에 있어야 합니다. 빠지면 `unit/test_operations.py`가 CI에서 실패합니다. 요구사항을 새로 만들면 표에 행을 더하고 `trace_report.py`를 다시 돌립니다.
- 게이트 마커는 `smoke` / `sanity` / `regression` 가운데 하나입니다. sanity는 서비스마다 대표 경로 하나로 줄여 둔 것(25개)이라, 새 테스트는 기본으로 `regression`에 둡니다. smoke나 sanity에 더하면 PR과 main 게이트 시간이 바뀌니 먼저 묻습니다.
- 그 밖의 마커: `aaos`(Mock에서는 자동으로 건너뜀), `power`(맨 끝에 돎), `spike`. `quarantined`는 자동으로 붙으니 직접 쓰지 않습니다.
- 독스트링은 한국어 존댓말로, 사용자가 보는 동작을 적습니다("…하면 …가 바뀝니다"). `publish_results.py`가 결과 페이지의 테스트 설명으로 그대로 씁니다.
- 픽스처: `app`(화면 객체 `IviApp`), `car`(`app`과 함께 쓰는 차량 어댑터), `vehicle`(앱 없이 차량만), `device`, `driver`. 같은 테스트 코드가 두 기기에서 돌아야 하므로, 기기 차이는 테스트 안에서 분기하지 않고 `ivi/vehicle.py`, `ivi/device.py`에서 처리합니다.
- 고정 `time.sleep`은 쓰지 않습니다. `ivi.waits`의 `wait_until`, `wait_value`, `stays`를 씁니다. `RETRY_ERRORS`에 든 예외만 다시 보고, 코드 오류는 바로 올립니다. `wait_until` 안에서 화면 객체는 따로 기다리지 않습니다(`polling()`).
- 화면 요소 이름은 앱의 Compose `testTag`(`ivi-app/.../ui/*.kt`, `VideoActivity.kt`)와 `ivi/screens.py`가 같아야 합니다. 한쪽을 바꾸면 다른 쪽도 바꿉니다. 요소는 `by_tag`(UiSelector `resourceId`)로 찾습니다.
- 차량 값 주입: 앱이 바꾸는 값(설정 온도)은 CarService(`cmd car_service set-property-value`)로, 차량 쪽에서 바뀌는 값(속도, 기어, 범위 밖 값)은 `dumpsys <VHAL> --set`으로 넣습니다. 읽기는 모두 CarService로 합니다. `inject-vhal-event`는 쓰지 않습니다(`docs/decisions.md` 3, 4번).
- 앱 프로세스는 세션 시작 때 한 번만 종료합니다. 테스트마다 `am start -S`를 쓰면 화웨이 iAware가 앱을 강제 종료합니다.
- 플랫폼 결함은 skip이 아니라 `xfail(strict=True)`로 겁니다. 재시도는 1회이고, 재시도로 통과하면 flaky로 따로 기록합니다. 격리(`quarantine.txt`)는 사유와 등록일을 함께 적고 사람이 정합니다. 해제 기준은 연속 20회 통과입니다.

## 코드 스타일

- 주석, 독스트링, 오류 메시지, 로그는 한국어로 씁니다. 코드 주석은 평서체("~한다")로 쓰고, **왜** 그렇게 했는지를 측정값이나 단계 기록과 함께 적습니다. 예: `# (6단계: 에뮬레이터가 응답을 멈춰 3회차가 14분 넘게 멈춰 있었다)`
- Python: 포매터와 린터 설정이 없습니다. 주변 코드에 맞춥니다(4칸 들여쓰기, 대부분 120자 안쪽, `pathlib`, 상수는 대문자). 기기 없이 확인할 수 있는 로직을 바꾸면 `unit/`에 테스트를 더합니다.
- Kotlin: `kotlin.code.style=official`, KDoc도 한국어로 씁니다. 테스트 전용 코드(`TestHookReceiver`)는 `src/debug`에만 둡니다. 차량 데이터는 `VehicleDataSource` 인터페이스 뒤에 CarService 구현과 Mock 구현을 둡니다.
- 줄 끝은 LF입니다(`*.bat`, `*.ps1`은 CRLF, `.gitattributes`). `gradlew`가 CRLF면 CI에서 실행되지 않습니다.

## 문서와 사이트

- 문서는 한국어 존댓말("~습니다")로, 짧고 쉬운 문장으로 씁니다.
- 과장하지 않습니다. 정해 둔 용어를 씁니다: "에뮬레이터 VHAL"("실제 VHAL" 아님), "주행 정보 패널"("클러스터" 아님). CAN, 원격 전원, Test Bench는 "모의 환경"이라고 밝힙니다. 실차, HIL, CAN 장비는 쓰지 않았습니다.
- 생성 파일은 손으로 고치지 않고 다시 만듭니다: `docs/traceability.md`(`trace_report.py`), `docs/test-results.md`와 `site/results/`(`publish_results.py`), `site/docs/*.html`과 `site/index.html`의 `<!-- fit:… -->`, `<!-- stats:… -->`, `<!-- devices:… -->` 구간(`build-docs.mjs`). 생성된 HTML은 커밋합니다.
- 손으로 쓴 숫자(테스트 개수, 시간, 게이트별 개수)는 README, `docs/portfolio.md` 4-1, `ivi-ci.yml` 주석, phase 문서에 흩어져 있습니다. 하나를 바꾸면 나머지도 같은 값으로 맞춥니다. 새 값은 실제 실행 결과에서만 가져옵니다.
- 방향을 정한 결정은 `docs/decisions.md`에 상황 / 고른 것 / 버린 것 / 근거(측정값) / 결과 형식으로 더합니다.
- 앱 화면, 파일 이름, 문서 제목에 다른 회사나 제품 이름을 넣지 않습니다(테스트 기기 이름은 괜찮음). 사이트 디자인 값은 `site/design-tokens.md`의 토큰만 씁니다.

## 개인 자료

- `.drive/`(블랙박스 주행 영상, 번호판과 위치가 담김)는 커밋하지 않습니다. 결과 화면에 다른 차 번호판이 읽히면 `publish_results.py --blur`로 흐리게 합니다.

## Git

- 브랜치는 `claude/<주제>`로 만들고, main으로 PR을 올려 사용자가 머지합니다.
- 커밋 메시지는 한국어로 씁니다. 첫 줄에 바뀐 것을 쉼표로 이어 요약하고, 빈 줄 뒤에 파일이나 영역별 `- ` 항목으로 무엇을 왜 바꿨는지 적습니다.
