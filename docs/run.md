# 실행 방법 (Windows)

프로젝트는 영문 경로(`C:\dev\opencabin-ivi`)에 둡니다. Android 빌드 도구가 한글 경로에서 실패합니다.

## 1. 에뮬레이터와 Appium

1. Automotive 에뮬레이터를 켭니다. AVD도 영문 경로에 두고, priv-app으로 앱을 넣으려면 `-writable-system`으로 켭니다.
   ```powershell
   $env:ANDROID_AVD_HOME = "C:\android\avd"; $env:ANDROID_SDK_ROOT = "C:\android"
   C:\android\emulator\emulator.exe -avd OpenCabin_AAOS_34 -writable-system -no-snapshot -no-boot-anim
   ```
   앱 빌드와 priv-app 설치 방법은 [phase2-app.md](phase2-app.md)에 있습니다.
   에뮬레이터 공조를 태블릿과 같은 22.0°C, 섭씨 표시로 맞추려면 `python ivi-tests/tools/emulator_defaults.py --persist`를 한 번 돌립니다. 에뮬레이터가 재부팅됩니다.
   영상 화면에 실제 주행 영상을 띄우려면 블랙박스 mp4를 `.drive/`에 넣고 `python ivi-tests/tools/push_drive_videos.py`를 돌립니다. 영상이 없으면 가짜 재생 화면이 나옵니다.
2. Appium 서버를 띄웁니다.
   ```powershell
   $env:ANDROID_HOME = "C:\android"; appium --address 127.0.0.1 --port 4723
   ```

## 2. 테스트

```powershell
cd ivi-tests
python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest --serial emulator-5554              # 전체
.venv\Scripts\python -m pytest --serial emulator-5554 -m smoke     # 빌드 게이트
```

기기가 한 대만 연결돼 있으면 `--serial`은 빼도 됩니다. 기기 종류는 자동으로 판별합니다.

## 3. 두 기기 병렬 실행, 반복 실행, 단위 테스트

```powershell
.venv\Scripts\python tools\run_bench.py -m "smoke or sanity" --reruns 1
.venv\Scripts\python tools\run_bench.py --repeat 5 --reruns 1        # 안정성 측정
.venv\Scripts\python tools\flaky_report.py --last 5
.venv\Scripts\python -m pytest unit
```

게이트 단계(smoke, sanity, regression, Release)의 기준은 [포트폴리오 4-1](portfolio.md#4-1-게이트-단계와-기준)에 있습니다.

앱 단위 테스트는 `ivi-app`에서 `.\gradlew testDebugUnitTest`로 돌립니다. 사용자 폴더가 한글 경로이면 Gradle 테스트 실행기가 실패하므로, 임시 폴더를 영문 경로로 바꿔서 돌립니다(`$env:TMP = "C:\dev\.tmp"; $env:TEMP = $env:TMP`).

## 4. Test Bench API

API를 띄우면 다른 도구가 HTTP로 기기와 신호, 전원, 실행 결과를 다룰 수 있습니다. 인증이 없으니 벤치 PC 안에서만 씁니다.

```powershell
.venv\Scripts\python tools\bench_api.py          # http://127.0.0.1:8770/api
```

## 5. 결과 사이트 만들기

`--shots`를 붙이면 테스트마다 판정 직후 화면을 남기고, 아래 명령이 그 결과를 소개 사이트로 옮깁니다.

```powershell
.venv\Scripts\python tools\run_bench.py --repeat 5 --reruns 1 --shots
.venv\Scripts\python tools\publish_results.py --repeat-runs "reports/runs/<날짜>-*-r*.json"
.venv\Scripts\python tools\trace_report.py
cd ..\site; npm install; npm run build-docs
```

영상 화면에 다른 차 번호판이 읽히면 `publish_results.py --blur`로 그 부분을 흐리게 합니다.

## 환경 변수

| 환경 변수 | 기본값 | 설명 |
|---|---|---|
| `IVI_SERIAL` | 연결된 기기 한 대 | 대상 기기. `--serial`과 같습니다. |
| `IVI_TAP` | 화웨이와 아너는 `adb`, 그 밖에는 `appium` | 화면을 누르는 방법 |
| `APPIUM_URL` | `http://127.0.0.1:4723` | Appium 서버 주소 |
