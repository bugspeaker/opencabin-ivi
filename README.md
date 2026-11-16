# OpenCabin IVI — AAOS 인포테인먼트 테스트 자동화

가상 차량 인포테인먼트(IVI) 앱과, 그 앱을 **UI 조작부터 차량 신호(VHAL)까지** E2E 로 검증하는 테스트 자동화 환경입니다.
같은 테스트를 AAOS 에뮬레이터(실제 CarService·VHAL)와 일반 Android 태블릿(Mock 차량 서비스)에서 돌리는 것이 목표입니다.

![주행 중 경로 안내 (7단계, Pleos Connect 구조)](docs/images/p7-guidance.png)

## 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| 1. 기술 검증 | AAOS 에뮬레이터, VHAL 값 주입·조회, Appium 세션, 신호↔UI E2E | ✅ [docs/phase1-spike.md](docs/phase1-spike.md) |
| 2. IVI 앱 | Kotlin + Compose. 홈 · 공조 · 미디어 · 영상(주행 중 차단), `VehicleDataSource` (CarPropertyManager / Mock), priv-app 설치 | ✅ AAOS 에뮬레이터 · 태블릿 모두 확인 [docs/phase2-app.md](docs/phase2-app.md) |
| 3. 테스트 프레임워크 | 기기 어댑터(AAOS/Mock), 화면 객체, smoke / sanity / regression 31개, 실패 자료 자동 수집 | ✅ [docs/phase3-framework.md](docs/phase3-framework.md) |
| 4. 운영 | 재시도·flaky 판정·격리·통계, 두 기기 병렬 실행, 프레임워크 단위 테스트, GitHub Actions(호스트 build·unit + self-hosted Bench e2e) | ✅ [docs/phase4-operations.md](docs/phase4-operations.md) (워크플로는 GitHub 에서 아직 미실행) |
| 5. 재점검·디자인 | 1~4단계 재점검, 양산 IVI 구조(왼쪽 주행 정보 · 오른쪽 앱 · 아래 앱 바) 참고 디자인 개편, 회귀에서 찾은 3건 수정 | ✅ [docs/phase5-design.md](docs/phase5-design.md) |
| 6. 기능 확장 | 내비게이션 · 라디오 · 전화 · 설정 · 후방 카메라(기어 R) · 음성 명령, 테스트 훅, 테스트 31 → 64개 | ✅ [docs/phase6-features.md](docs/phase6-features.md) |
| 7. Pleos Connect 구조 | 3영역 화면(주행 정보 · 상단 바 · 앱 / 하단 바), 분할 화면, 하단 공조 바(VHAL), 전 좌석 공조 · SYNC, 주행 뷰 · 유틸리티 위젯, **AI 어시스턴트**(여러 명령 · 좌석 인식 · 목적지 후보 · 주행 제한), 빠른 제어, 알림 센터, 앱 목록. E2E 64 → 84개, 앱 단위 테스트 17개 | ✅ [docs/phase7-pleos.md](docs/phase7-pleos.md) |
| 8. 차량 신호 확장 | 화면 상태였던 공조(A/C · AUTO · 풍량 · 김서림 · 좌석 열선)와 도어 잠금을 **CarProperty/VHAL 신호**로, 주행 가능 거리 · 배터리 · 외기 온도를 주행 정보에. 거리 부족 → 충전소 안내. 양방향 E2E 24개(area 단위 판정), 테스트마다 신호 기준 값 초기화. E2E 84 → 108개 | ✅ 에뮬레이터 확인, 태블릿 미실행 [docs/phase8-signals.md](docs/phase8-signals.md) |

## 구조

```
ivi-app/              Kotlin + Compose IVI 앱 (assistant/ AI 어시스턴트 규칙, state/ 설정·앱 상태, ui/ 화면 틀·기능별 화면, src/debug/ 테스트 훅, src/test/ JVM 단위 테스트), privileged/ = priv-app 설치
ivi-tests/
  ivi/                adb · 대기 · 차량 어댑터(AaosVehicle / MockVehicle) · 기기 · 화면 객체 · 결과 기록 · 격리 목록
  tests/              기기 E2E: smoke / sanity / regression (공조·주행·미디어·내비·라디오·전화·설정·후방 카메라·음성·AI 어시스턴트·화면 틀·차량 신호), spike(1단계), conftest.py
  unit/               프레임워크 단위 테스트 (기기 없이)
  tools/              run_bench.py (기기 병렬), flaky_report.py (통계), install_app.py (같은 APK 면 건너뜀), emulator_defaults.py (에뮬레이터 공조 22.0°C · 섭씨)
  quarantine.txt      격리 목록
.github/workflows/    ivi-ci.yml
docs/                 단계별 설계·검증 기록
```

## 실행 (Windows)

프로젝트는 영문 경로(`C:\dev\opencabin-ivi`)에 둡니다. Android 빌드 도구가 한글 경로에서 실패합니다.

1. Automotive 에뮬레이터 실행 (AVD 도 영문 경로. priv-app 앱을 쓰려면 `-writable-system`)
   ```powershell
   $env:ANDROID_AVD_HOME = "C:\android\avd"; $env:ANDROID_SDK_ROOT = "C:\android"
   C:\android\emulator\emulator.exe -avd OpenCabin_AAOS_34 -writable-system -no-snapshot -no-boot-anim
   ```
   앱 빌드와 priv-app 설치는 [docs/phase2-app.md](docs/phase2-app.md) 참고.
   공조 값을 태블릿과 같게(22.0°C, 섭씨 표시) 맞추려면 `python ivi-tests/tools/emulator_defaults.py`.
2. Appium 서버
   ```powershell
   $env:ANDROID_HOME = "C:\android"; appium --address 127.0.0.1 --port 4723
   ```
3. 테스트
   ```powershell
   cd ivi-tests
   python -m venv .venv; .venv\Scripts\python -m pip install -r requirements.txt
   .venv\Scripts\python -m pytest --serial emulator-5554              # 전체
   .venv\Scripts\python -m pytest --serial emulator-5554 -m smoke     # 빌드 게이트
   ```
   기기가 1대만 연결돼 있으면 `--serial` 을 빼도 됩니다. 기기 종류(AAOS/Mock)는 자동으로 판별합니다.
4. 두 기기 병렬 · 재시도 · flaky 통계 · 단위 테스트
   ```powershell
   .venv\Scripts\python tools\run_bench.py -m "smoke or sanity" --reruns 1
   .venv\Scripts\python tools\flaky_report.py --last 20
   .venv\Scripts\python -m pytest unit
   ```

| 환경 변수 | 기본값 | 설명 |
|---|---|---|
| `IVI_SERIAL` | (연결된 1대) | 대상 기기 (`--serial` 과 같음) |
| `IVI_TAP` | 화웨이·아너 `adb`, 그 외 `appium` | 요소를 누르는 방법 |
| `APPIUM_URL` | `http://127.0.0.1:4723` | Appium 서버 |

8단계 결과 (2026-11-16): AAOS 에뮬레이터 E2E 108개 중 **106 passed, 1 skipped, 1 xfailed** (6분 40초), 앱 단위 17 passed, 프레임워크 단위 33 passed. 태블릿은 adb 승인 대기로 아직 미실행 ([docs/phase8-signals.md](docs/phase8-signals.md)).

7단계 결과 (2026-11-14): AAOS 에뮬레이터 E2E 84개 중 **82 passed, 1 skipped, 1 xfailed** (5분 47초), 화웨이 태블릿 **78 passed, 6 skipped** (AAOS 전용, 5분 46초), 앱 단위 17 passed, 프레임워크 단위 26 passed ([docs/phase7-pleos.md](docs/phase7-pleos.md)).

6단계까지의 결과 (2026-11-13)

| 기기 | 결과 | 시간 |
|---|---|---|
| AAOS 에뮬레이터 | 30 passed, 1 xfailed | 약 2분 10초 ~ 2분 35초 |
| 화웨이 태블릿 (Mock) | 25 passed, 6 skipped (AAOS 전용) | 약 1분 22초 |
| 두 기기 병렬 (`run_bench.py`, 재시도 1) | 디자인 개편 후 3회 모두 게이트 통과, flaky 0, 앱 재실행 0 | 2분 10초 ~ 2분 22초 |
| 프레임워크 단위 테스트 (`pytest unit`) | 25 passed | 0.3초 |

xfail 1건은 1단계에서 찾은 레이아웃 결함입니다 (운전석 온도 ▲ 가 홈 버튼에 가려짐).
