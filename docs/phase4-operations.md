# 4단계 운영: flaky 관리 · 병렬 실행 · CI

작성 2026-11-13. 목표는 "테스트가 있다" 에서 "매일 무인으로 돌고, 흔들리는 테스트를 숫자로 관리한다" 로 가는 것.

## 결과

| 항목 | 3단계 | 4단계 |
|---|---|---|
| 태블릿 앱 재실행(iAware 강제 종료) | 실행마다 1회 | **0회** (3회 연속) |
| 태블릿 전체 시간 | 약 1분 40초 | **약 1분 22초** |
| 두 기기 전체 | 차례로 약 3분 40초 | **병렬 2분 13초 ~ 2분 37초 (1.5~1.6배)** |
| 재시도·flaky 판정 | 없음 | `--reruns 1`, 실패 후 통과 = flaky 로 기록 |
| 격리 | 없음 | `quarantine.txt` (돌리되 게이트 제외) |
| 통계 | 없음 | `tools/flaky_report.py` (불안정률, p95, 격리·해제 후보) |
| 프레임워크 자체 검증 | 없음 | `unit/` 22개, 기기 없이 0.3초 |
| CI | 없음 | `.github/workflows/ivi-ci.yml` (build · unit · e2e on self-hosted bench) |

검증: 전체 스위트를 두 기기 병렬로 3회 (`--reruns 1`) → 모두 게이트 통과, flaky 0, 앱 재실행 0.
- AAOS: 30 passed, 1 xfailed (알려진 SystemUI 결함) × 3
- 태블릿: 25 passed, 6 skipped (AAOS 전용) × 3

## 1. 앱 재실행 줄이기 (3단계에서 남긴 일)

- 3단계: 테스트마다 `am start -S` (프로세스 종료 후 실행) → 화웨이 iAware 가 약 20회째에 '반복 크래시' 로 보고 앱을 강제 종료.
- 4단계: 프로세스 종료는 **세션 시작 때 1번만**, 테스트마다는 `am start --activity-clear-task` 로 화면만 비운다.
  차량 상태는 `prepare()` 가 매번 정차·22.0°C 로 맞추므로 테스트 사이 격리는 그대로다.
- 그래도 앱이 화면에 없으면 그때만 프로세스까지 새로 띄우고 `app_relaunch` 로 기록한다 (안전망).

## 2. 재시도 · 판정 · 기록

- `pytest-rerunfailures` 로 실패한 테스트를 1번 더 돌린다 (`--reruns 1 --reruns-delay 2`). **재시도로 통과해도 숨기지 않는다**:
  `ivi/results.py` 가 테스트마다 최종 판정을 매긴다.

| 판정 | 뜻 | 게이트 |
|---|---|---|
| passed | 한 번에 통과 | 통과 |
| flaky | 실패 후 재시도에서 통과 | 통과 (통계에 남음) |
| failed / error | 재시도까지 실패 / 준비·정리 실패 | **실패** |
| xfailed | 알려진 결함 | 통과 |
| quarantined | 격리 목록 (실제 결과는 `quarantine_result`) | 통과 |
| skipped | AAOS 전용 등 | 통과 |

- 실패한 시도마다 실패 자료(화면·UI 계층·차량 상태·액티비티·logcat)를 남긴다. 재시도 것은 `…__try2` 폴더. flaky 원인은 첫 실패 자료에 있다.
- 기록 위치
  - `reports/history/results.jsonl` 누적 (테스트 1건 = 1줄: run, 기기, 판정, 재시도, 앱 재실행, 시간, 첫 오류)
  - `reports/runs/<run>-<serial>.json` 이번 실행 요약 + 테스트별
  - `reports/junit-<aaos|mock>-<serial>.xml`

실제 기기에서 확인 (일부러 만든 확인용 테스트, 확인 후 삭제):
첫 시도만 실패하는 테스트 → `flaky, reruns 1`, 첫 실패 자료 저장 / 격리 목록의 실패 테스트 → `quarantined`, 게이트 pass.

## 3. 격리 (quarantine.txt)

```
# <nodeid 또는 앞부분> | <이유> | <등록일>
tests/test_media.py::test_play_pause_toggles | 화웨이에서 간헐 실패, 원인 분석 중 | 2026-11-13
```
- 격리된 테스트는 `xfail(strict=False)` 로 바뀐다. **계속 돌려서 데이터를 모으되** 실패해도 빌드를 막지 않는다.
- nodeid 앞부분만 쓰면 매개변수 조합 전체가 격리된다 (`…[driver]`, `…[passenger]`). 이름 앞부분만 같은 다른 테스트는 걸리지 않는다.
- 이유 없는 줄은 오류로 거부한다 (사유 없는 격리 방지).
- 지금은 비어 있다 (격리할 테스트 없음).

## 4. flaky 통계 (tools/flaky_report.py)

```powershell
.venv\Scripts\python tools\flaky_report.py --last 20 --out reports\flaky-report.md
```
- 실행 요약: 기기별 실행 수, 게이트 통과율
- 불안정 테스트: flaky·실패 횟수, 불안정률, 앱 재실행, 평균/p95, 마지막 원인
- 격리 후보: 불안정률 10% 이상 & 5회 이상 실행 → 종료 코드 1 (알림용)
- 격리 해제 후보: 격리 중 20회 연속 실제 통과
- 느린 테스트: p95 상위 5

지금 기록 (204건) 에서 본 것:
- 불안정 테스트 없음, 게이트 통과율 100% (AAOS 5회, Mock 4회).
- **관찰 중**: AAOS `test_video_is_blocked_while_driving` 이 1회 38.3초 (다른 회차 2.5~2.9초). 통과는 했으므로 flaky 는 아니다.
  주행 중 막힌 화면을 `am start -W` 로 띄울 때 실행 완료 대기가 길어진 것으로 의심. p95 로 계속 본다.

## 5. 병렬 실행 (tools/run_bench.py)

```powershell
.venv\Scripts\python tools\run_bench.py                                # 연결된 모든 기기, 전체
.venv\Scripts\python tools\run_bench.py -m "smoke or sanity" --reruns 1
.venv\Scripts\python tools\run_bench.py --repeat 5 --reruns 1          # 안정성 측정
```
- 기기마다 pytest 프로세스를 따로 띄우고 같은 run id 로 묶는다. 출력은 `reports/logs/<run>-<serial>.log`.
- 같은 Appium 서버로 두 세션을 동시에 쓰려면 **UiAutomator2 `systemPort` 가 기기마다 달라야 한다** (8200, 8210 …, `--system-port`).
- 전체 시간 = 가장 느린 기기 (AAOS). 기기를 더 늘려도 시간이 거의 늘지 않는다.
- 다음 단계 후보: 같은 종류 기기가 여러 대면 테스트를 나눠(sharding) 한 기기 몫을 줄이기.

## 6. CI (.github/workflows/ivi-ci.yml)

| job | 실행 위치 | 내용 |
|---|---|---|
| build | GitHub 호스트 (ubuntu) | `assembleDebug` 컴파일 확인, APK 보관 |
| unit | GitHub 호스트 (ubuntu) | `pytest unit` (기기 없음) |
| e2e | self-hosted `ivi-bench` (이 PC) | Bench 점검 → Bench 에서 APK 빌드 → 설치(같으면 건너뜀) → 두 기기 병렬 → flaky 리포트를 Job Summary 에 → 자료 업로드 |

이벤트별 범위 (빠른 것부터, 넓은 것은 Nightly):

| 이벤트 | 범위 | 예상 시간 |
|---|---|---|
| pull_request | smoke | 약 30초 |
| push (main) | smoke or sanity | 약 1~2분 |
| schedule (매일 03:00 KST) | 전체 | 약 2분 30초 |
| workflow_dispatch | 입력한 마커, 반복 횟수 | - |

설계에서 고려한 것
- **서명 키**: AAOS 에는 priv-app 으로 넣어 두었다. GitHub 호스트에서 만든 APK 는 debug 서명 키가 달라 덮어쓰기가 거부된다 → e2e 는 Bench(같은 사용자 계정)에서 다시 빌드한다.
- **화웨이 설치 승인**: adb 설치마다 기기 화면 승인이 필요해 무인 실행이 멈춘다 → `tools/install_app.py` 가 기기의 APK 해시를 비교해 **같으면 설치하지 않는다**. 앱이 바뀐 날은 사람이 한 번 승인해야 한다 (또는 기기 개발자 옵션의 'ADB 설치 앱 확인' 해제 — 기기 정책 결정이라 이 프로젝트에서는 바꾸지 않았다).
- **Bench 는 하나**: `concurrency` 로 e2e 가 동시에 둘 돌지 않게 한다 (뒤 실행은 대기).
- **누적 기록 유지**: checkout `clean: false` 로 `reports/history` 를 남겨 flaky 통계가 실행을 넘어 쌓인다.
- 이 워크플로는 아직 GitHub 에 올려 돌려 보지 않았다. 각 단계 명령은 이 PC 에서 따로 실행해 확인했고, YAML 구조와 PowerShell 인자 처리(`"smoke or sanity"` 가 한 인자로 넘어가는지)는 확인했다.

### Bench 준비 순서
1. 에뮬레이터: `-writable-system` 으로 실행, 처음 한 번 `ivi-app/privileged/install_priv_app.py`
2. 태블릿: USB 연결, USB 디버깅 허용, 앱·Appium 보조 앱 3개 설치 승인 (처음 한 번)
3. Appium 서버 상시 실행: `ANDROID_HOME=C:\android appium --address 127.0.0.1 --port 4723`
4. GitHub 저장소 Settings → Actions → Runners 에서 self-hosted runner 등록, 라벨 `ivi-bench`. 서비스 계정이 아니라 **이 PC 사용자 계정**으로 실행

## 프레임워크 단위 테스트 (unit/)

`pytest unit` — 기기·Appium 없이 0.3초. CI 의 GitHub 호스트에서 돈다.
- 어댑터: VHAL/CarService 출력 해석, km/h → m/s 변환, 쓰기 거부 시 오류, Mock broadcast 인자 형식·결과 해석
- 기기: 브랜드별 누르는 방법과 `IVI_TAP` 덮어쓰기
- 운영: 판정 분류(passed/flaky/failed/error/xfailed/quarantined), 앱 재실행 집계, 격리 목록 형식·매칭, flaky 통계(격리·해제 후보, 최근 N회)

`tests/conftest.py` 는 `tests/` 아래에만 적용되므로 `pytest unit` 은 기기를 찾지 않는다.
