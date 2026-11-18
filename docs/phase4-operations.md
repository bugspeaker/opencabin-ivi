# 4단계 운영: flaky 관리, 병렬 실행, CI

2026-11-13에 정리했습니다. 3단계까지는 테스트를 사람이 직접 돌렸습니다. 이번 단계에서는 매일 무인으로 돌리고, 흔들리는 테스트를 통계로 관리하는 데 필요한 것들을 만들었습니다.

## 결과

| 항목 | 3단계 | 4단계 |
|---|---|---|
| 태블릿에서 앱을 다시 띄운 횟수 (iAware 강제 종료) | 실행마다 1번 | 세 번 연속 0번 |
| 태블릿 전체 시간 | 약 1분 40초 | 약 1분 22초 |
| 두 기기 전체 시간 | 차례로 돌려 약 3분 40초 | 병렬로 2분 13초 ~ 2분 37초 (1.5~1.6배 빠름) |
| 재시도와 flaky 판정 | 없음 | `--reruns 1`. 실패했다가 통과하면 flaky로 기록 |
| 격리 | 없음 | `quarantine.txt`. 테스트는 돌리되 게이트에서는 뺌 |
| 통계 | 없음 | `tools/flaky_report.py`. 불안정률, p95, 격리 후보와 해제 후보 |
| 프레임워크 자체 검증 | 없음 | `unit/` 22개. 기기 없이 0.3초 |
| CI | 없음 | `.github/workflows/ivi-ci.yml`. build, unit, 그리고 self-hosted Bench의 e2e |

전체 스위트를 두 기기에서 병렬로 세 번 돌렸고(`--reruns 1`) 세 번 모두 게이트를 통과했습니다. flaky와 앱 재실행은 0이었습니다. AAOS는 매번 30개 통과, 1개 알려진 결함(SystemUI)이었고, 태블릿은 매번 25개 통과, AAOS 전용 6개 건너뜀이었습니다.

## 1. 앱 재실행 줄이기 (3단계에서 남긴 일)

3단계에서는 테스트마다 `am start -S`로 프로세스를 끄고 다시 켰습니다. 그랬더니 화웨이 iAware가 스무 번째쯤에 이것을 반복 크래시로 보고 앱을 강제로 껐습니다.

4단계에서는 프로세스를 끄는 것은 세션을 시작할 때 한 번만 하고, 테스트마다는 `am start --activity-clear-task`로 화면만 비웁니다. 차량 상태는 `prepare()`가 매번 정차, 22.0°C로 맞추기 때문에 테스트 사이의 격리는 그대로 유지됩니다.

그래도 앱이 화면에 없으면 그때만 프로세스까지 새로 띄우고 `app_relaunch`로 기록합니다. 안전망으로 남겨 둔 것입니다.

## 2. 재시도, 판정, 기록

`pytest-rerunfailures`로 실패한 테스트를 한 번 더 돌립니다(`--reruns 1 --reruns-delay 2`). 재시도에서 통과한 테스트는 passed가 아니라 flaky로 기록합니다. 판정은 `ivi/results.py`가 테스트마다 매깁니다.

| 판정 | 뜻 | 게이트 |
|---|---|---|
| passed | 한 번에 통과 | 통과 |
| flaky | 실패했다가 재시도에서 통과 | 통과, 통계에 남음 |
| failed / error | 재시도까지 실패했거나 준비, 정리 단계에서 실패 | 실패 |
| xfailed | 알려진 결함 | 통과 |
| quarantined | 격리 목록에 있는 테스트. 실제 결과는 `quarantine_result`에 남음 | 통과 |
| skipped | AAOS 전용 테스트 등 | 통과 |

실패한 시도마다 실패 자료(화면, UI 계층, 차량 상태, 액티비티, logcat)를 남깁니다. 재시도의 자료는 `…__try2` 폴더에 들어갑니다. flaky의 원인은 첫 번째 실패 자료에 있습니다.

기록은 세 곳에 남습니다.

- `reports/history/results.jsonl`: 누적 기록. 테스트 하나가 한 줄이고 실행, 기기, 판정, 재시도, 앱 재실행, 시간, 첫 오류를 담습니다.
- `reports/runs/<run>-<serial>.json`: 이번 실행의 요약과 테스트별 결과
- `reports/junit-<aaos|mock>-<serial>.xml`

실제 기기에서 확인용 테스트를 일부러 만들어 돌려 봤고, 확인한 뒤에는 지웠습니다. 첫 시도만 실패하는 테스트는 `flaky, reruns 1`로 기록되고 첫 실패 자료가 저장됐습니다. 격리 목록에 넣은 실패 테스트는 `quarantined`로 기록되고 게이트는 통과했습니다.

## 3. 격리 (quarantine.txt)

```
# <nodeid 또는 앞부분> | <이유> | <등록일>
tests/test_media.py::test_play_pause_toggles | 화웨이에서 간헐 실패, 원인 분석 중 | 2026-11-13
```

격리된 테스트는 `xfail(strict=False)`로 바뀝니다. 계속 돌려서 데이터를 모으지만, 실패해도 빌드를 막지 않습니다.

nodeid 앞부분만 적으면 매개변수 조합 전체(`…[driver]`, `…[passenger]`)가 격리됩니다. 이름 앞부분만 같은 다른 테스트는 걸리지 않습니다.

이유를 적지 않은 줄은 오류로 거부합니다. 사유 없이 테스트를 격리하는 일을 막기 위해서입니다. 지금은 격리할 테스트가 없어서 목록이 비어 있습니다.

## 4. flaky 통계 (tools/flaky_report.py)

```powershell
.venv\Scripts\python tools\flaky_report.py --last 20 --out reports\flaky-report.md
```

리포트에는 다음 내용이 들어갑니다.

- 기기별 실행 수와 게이트 통과율
- 불안정한 테스트의 flaky와 실패 횟수, 불안정률, 앱 재실행, 평균과 p95 시간, 마지막 원인
- 격리 후보: 불안정률이 10% 이상이고 다섯 번 이상 실행된 테스트. 후보가 있으면 종료 코드 1을 돌려줘서 알림에 쓸 수 있습니다.
- 격리 해제 후보: 격리된 상태에서 스무 번 연속 실제로 통과한 테스트
- 느린 테스트: p95가 큰 순서로 다섯 개

지금까지 쌓인 기록 204건에서는 불안정한 테스트가 없었고, 게이트 통과율은 100%였습니다(AAOS 5회, Mock 4회).

지켜보고 있는 것이 하나 있습니다. AAOS의 `test_video_is_blocked_while_driving`이 한 번 38.3초가 걸렸습니다. 다른 회차는 2.5~2.9초였습니다. 통과했으니 flaky는 아닙니다. 주행 중에 막힌 화면을 `am start -W`로 띄울 때 실행 완료를 기다리는 시간이 길어진 것으로 보고 있고, p95로 계속 확인합니다.

## 5. 병렬 실행 (tools/run_bench.py)

```powershell
.venv\Scripts\python tools\run_bench.py                                # 연결된 모든 기기, 전체
.venv\Scripts\python tools\run_bench.py -m "smoke or sanity" --reruns 1
.venv\Scripts\python tools\run_bench.py --repeat 5 --reruns 1          # 안정성 측정
```

기기마다 pytest 프로세스를 따로 띄우고 같은 run id로 묶습니다. 출력은 `reports/logs/<run>-<serial>.log`에 남습니다.

Appium 서버 하나로 두 세션을 동시에 쓰려면 UiAutomator2 `systemPort`가 기기마다 달라야 합니다. 8200, 8210처럼 나눠 주고 `--system-port`로 넘깁니다.

전체 시간은 가장 느린 기기(AAOS)가 정합니다. 기기를 더 늘려도 시간은 거의 늘지 않습니다. 같은 종류의 기기가 여러 대라면 테스트를 나눠(sharding) 기기 한 대가 맡는 몫을 줄일 수 있어서, 다음 단계 후보로 적어 두었습니다.

## 6. CI (.github/workflows/ivi-ci.yml)

| job | 실행 위치 | 내용 |
|---|---|---|
| build | GitHub 호스트 (ubuntu) | `assembleDebug`로 컴파일되는지 보고 APK를 보관합니다. |
| unit | GitHub 호스트 (ubuntu) | 기기 없이 `pytest unit`을 돌립니다. |
| e2e | self-hosted `ivi-bench` (이 PC) | Bench를 점검하고, Bench에서 APK를 빌드해 설치(같으면 건너뜀)한 뒤 두 기기에서 병렬로 돌립니다. flaky 리포트는 Job Summary에 붙이고 자료를 올립니다. |

이벤트마다 돌리는 범위를 다르게 했습니다. 자주 도는 것은 빠르게, 넓은 범위는 Nightly에서 돌립니다.

| 이벤트 | 범위 | 기기당 시간 (2026-11-18 실측, 129개 기준) |
|---|---|---|
| pull_request | smoke (13개) | 약 35초 |
| push (main) | smoke와 sanity (38개) | 약 2분 15초, 두 기기 병렬 |
| schedule (매일 03:00 KST) | 전체 (129개) | 약 8분 45초~9분 15초, 두 기기 병렬 |
| workflow_dispatch | 입력한 마커와 반복 횟수. Release 후보는 전체, 반복 3회 | - |

4단계(테스트 31개) 때는 전체가 기기당 약 2분 30초였습니다. 시간은 테스트별 시간의 합이고, 단계별 기준은 [포트폴리오 4-1](portfolio.md#4-1-게이트-단계와-기준)에 있습니다.

워크플로를 짜면서 고려한 것들입니다.

- **서명 키.** AAOS에는 앱을 priv-app으로 넣어 두었습니다. GitHub 호스트에서 만든 APK는 debug 서명 키가 달라서 덮어쓰기가 거부됩니다. 그래서 e2e에서는 Bench(같은 사용자 계정)에서 다시 빌드합니다.
- **화웨이 설치 승인.** adb로 설치할 때마다 기기 화면에서 승인해야 해서 무인 실행이 멈춥니다. 그래서 `tools/install_app.py`가 기기에 있는 APK의 해시를 비교해 같으면 설치하지 않습니다. 앱이 바뀐 날에는 사람이 한 번 승인해야 합니다. 기기 개발자 옵션의 'ADB 설치 앱 확인'을 끄는 방법도 있지만, 기기 정책에 관한 결정이라 이 프로젝트에서는 바꾸지 않았습니다.
- **Bench는 한 대.** `concurrency`로 e2e가 동시에 두 개 돌지 않게 했습니다. 뒤에 온 실행은 기다립니다.
- **누적 기록 유지.** checkout에 `clean: false`를 줘서 `reports/history`가 남게 했습니다. 그래야 flaky 통계가 실행을 넘어 쌓입니다.

GitHub에서 처음 돌린 기록입니다(2026-11-16, 비공개 저장소). GitHub 호스트 job은 첫 실행부터 통과했습니다.

- PR #1의 실행(run 43812382880)에서 unit은 15초, build는 약 5분 걸려 통과했습니다. build에는 assembleDebug와 앱 단위 테스트가 들어 있습니다. e2e는 `IVI_BENCH` 변수가 없어서 건너뛰었고, 실행 전체는 success였습니다.
- main push 실행(run 43812370154)에서도 build와 unit은 통과했습니다. 다만 변수 조건을 넣기 전 워크플로라 e2e가 러너를 기다리며 멈춰 있어서 직접 취소했습니다. 이 일을 계기로 e2e를 변수로 켜고 끌 수 있게 바꿨습니다.
- e2e는 아직 GitHub에서 돌리지 않았습니다. 각 단계의 명령은 이 PC에서 따로 실행해 확인했고, PowerShell이 `"smoke or sanity"`를 인자 하나로 넘기는지도 확인했습니다.

### Bench 준비 순서

1. 에뮬레이터를 `-writable-system`으로 켜고, 처음 한 번 `ivi-app/privileged/install_priv_app.py`를 돌립니다.
2. 태블릿을 USB로 연결해 USB 디버깅을 허용하고, 앱과 Appium 보조 앱 세 개의 설치를 처음 한 번 승인합니다.
3. Appium 서버를 계속 켜 둡니다: `ANDROID_HOME=C:\android appium --address 127.0.0.1 --port 4723`
4. GitHub 저장소의 Settings, Actions, Runners에서 self-hosted runner를 `ivi-bench` 라벨로 등록합니다. 서비스 계정이 아니라 이 PC의 사용자 계정으로 실행합니다.
5. Settings, Secrets and variables, Actions, Variables에 `IVI_BENCH=online`을 넣습니다. 이 변수가 없으면 e2e job을 건너뜁니다. 러너가 없을 때 job이 하염없이 기다리지 않게 하려는 것입니다. Bench를 끌 때는 변수를 지우거나 다른 값으로 바꿉니다.

## 프레임워크 단위 테스트 (unit/)

`pytest unit`은 기기와 Appium 없이 0.3초 만에 끝나고, CI에서는 GitHub 호스트에서 돕니다. 확인하는 것은 이렇습니다.

- 어댑터: VHAL과 CarService 출력 해석, km/h를 m/s로 바꾸는 계산, 쓰기가 거부됐을 때의 오류, Mock broadcast 인자 형식과 결과 해석
- 기기: 제조사별로 누르는 방법을 고르는 규칙과 `IVI_TAP`으로 덮어쓰기
- 운영: 판정 분류(passed, flaky, failed, error, xfailed, quarantined), 앱 재실행 집계, 격리 목록 형식과 매칭, flaky 통계(격리 후보와 해제 후보, 최근 N회)

`tests/conftest.py`는 `tests/` 아래에만 적용되기 때문에 `pytest unit`은 기기를 찾지 않습니다.
