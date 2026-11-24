# 주행 상태 읽기 수정 후 반복 3회 (2026-11-24)

테스트 도구가 AAOS 에뮬레이터의 주행 상태를 못 읽었을 때 '제한 없음'으로 처리하던 것을 오류로 바꾼 뒤(커밋 `300b081`), 두 기기 × 3회와 갤럭시 폴드 1회를 다시 돌린 원자료입니다. 앱(0.4.2)과 테스트 수(144개)는 바뀌지 않았습니다.

## 무엇을 고쳤나

`AaosVehicle.driving_state()`([`ivi/vehicle.py`](../../../ivi-tests/ivi/vehicle.py))는 `dumpsys car_service`의 CarDrivingStateService 출력에서 상태 줄을 못 찾으면 '알 수 없음'(-1)을 돌려줬습니다. `is_restricted()`는 '주행 중'일 때만 제한으로 보므로, 못 읽은 상태가 '제한 없음'으로 읽혔고 정차를 기다리는 `wait_restricted(False)`가 기다리지 않고 바로 지나갔습니다.

- 다른 읽기(`get_property`, `ux_restrictions`)처럼 못 읽으면 `RuntimeError`를 내게 바꿨습니다. 대기는 이 예외를 '아직 아님'으로 보고 다시 읽으므로, 잠깐 못 읽은 것은 다시 읽고 끝까지 못 읽으면 그때 출력과 함께 실패로 남습니다.
- 실패 자료(`dump`)는 하나가 안 읽혀도 나머지 값을 계속 모으게 했습니다.
- 단위 테스트 6개를 더했습니다(`unit/test_adapters.py`): 정상으로 읽는 경우, 못 읽는 출력 세 가지, 대기가 바로 지나가지 않는 것, 실패 자료가 계속 모이는 것.
- 외부 리뷰의 예상 질문('`cmd car_service` 출력을 정규식으로 읽는 방식의 한계')에 답을 정리하며 코드와 대조하다 찾았습니다.

## 첫 확인

커밋한 코드로 에뮬레이터에서 주행 상태를 쓰는 테스트 25개(`test_driving.py`, `test_cockpit.py`, 주행 상태 spike 1개)를 돌렸습니다(`20261124-driving-state-aaos`, [runs-first](runs-first/)). 25개 모두 통과했고, 1개(`test_driving_signals_are_shown`)는 막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽어 세션을 다시 붙인 뒤 재시도에서 통과했습니다(#29와 같은 현상).

## 첫 시도: 1회차 태블릿 실패

같은 커밋으로 처음 돌린 반복(`20261124-110716-r1` ~ `20261124-113508-r3`, [attempt1/runs](attempt1/runs/))은 1회차 태블릿에서 오류 1개와 재시도 후 통과 1개가 나왔습니다. 2·3회차는 두 기기 모두 통과했습니다.

| 회차 | AAOS 에뮬레이터 | 태블릿 (Mock) |
|---|---|---|
| 1 | 통과 142, 건너뜀 1, 알려진 결함 1 (13분 3초) | 오류 1, 재시도 후 통과 1, 통과 134, 건너뜀 8, 세션 재연결 1 (14분 11초) |
| 2 | 통과 142, 건너뜀 1, 알려진 결함 1 (13분 37초) | 통과 136, 건너뜀 8 (12분 57초) |
| 3 | 통과 142, 건너뜀 1, 알려진 결함 1 (13분 20초) | 통과 136, 건너뜀 8 (12분 53초) |

- 원인: 첫 테스트가 시작될 때 태블릿에 USB 연결 방식을 묻는 시스템 창('USB를 사용하여 다음 작업 수행')이 떠서 앱을 가렸습니다([실패 순간 화면](images/attempt1-usb-dialog.png)). 실행을 시작할 무렵 태블릿과 폴드의 USB를 연결한 때와 겹칩니다. 첫 테스트(`test_zone_applies_command_to_speaking_seat`)는 앱 요소를 찾지 못해 재시도까지 오류로 끝났고, 두 번째 테스트 중에는 UiAutomator2 계측 프로세스가 끊겨 세션을 다시 붙인 뒤 통과했습니다.
- Release 게이트는 조건 2(오류)와 3(flaky)으로 막았습니다([attempt1/release-gate.txt](attempt1/release-gate.txt)).
- 코드가 아니라 실행 중에 기기 연결이 바뀐 탓이라 첫 시도로 남기고, USB를 건드리지 않은 채 같은 커밋으로 3회를 다시 돌렸습니다.

## 두 기기 × 3회와 폴드 1회

커밋 `300b081`(커밋하지 않은 변경 없음, 앱 0.4.2 (6) APK sha256 `c977c9069411…`)에서 돌렸습니다.

```powershell
.venv\Scripts\python tools\run_bench.py --devices emulator-5554,W3VBB22125209573 --repeat 3 --reruns 1 --shots
.venv\Scripts\python -m pytest --serial R38M309YKQY --reruns 1 --shots --run-id 20261124-fold-144
```

| 회차 (run id) | AAOS 에뮬레이터 | 태블릿 (Mock) | 병렬 실행 |
|---|---|---|---|
| `20261124-120332-r1` | 142 통과, 1 건너뜀, 1 알려진 결함 (12분 37초) | 136 통과, 8 건너뜀 (12분 45초) | 12분 48초 |
| `20261124-121620-r2` | 142 통과, 1 건너뜀, 1 알려진 결함 (11분 54초) | 136 통과, 8 건너뜀 (12분 47초) | 12분 49초 |
| `20261124-122909-r3` | 142 통과, 1 건너뜀, 1 알려진 결함 (11분 59초) | 136 통과, 8 건너뜀 (12분 43초) | 12분 45초 |
| `20261124-fold-144` (폴드, 따로 1회) | | 갤럭시 폴드: 136 통과, 8 건너뜀 (13분 59초) | |

- 실행한 테스트 837건(AAOS 429건, 태블릿 408건), 재시도 0번, flaky 0건, 실패 0건, 세션 재연결 0번입니다([runs](runs/), [runs-fold](runs-fold/)).
- Release 게이트 여섯 조건을 `--commit 300b081`로 확인해 모두 통과했습니다([release-gate.txt](release-gate.txt)). 폴드 1회도 따로 확인해 통과했습니다([release-gate-fold.txt](release-gate-fold.txt)).
- 이번 수정은 AAOS 쪽 코드만 바꿔 폴드와 태블릿(Mock)은 영향을 받지 않지만, 결과 페이지의 세 기기 칸을 같은 코드로 맞추려고 폴드도 한 번 돌렸습니다.
- [결과 페이지](../../test-results.md)의 판정과 화면은 3회차와 폴드 1회입니다. 영상 화면 세 장(`test_video_resumes_where_it_stopped`)은 앞차 번호판을 흐리게 해서 올렸습니다.

다시 세는 방법 (`ivi-tests`에서):

```powershell
.venv\Scripts\python tools\flaky_report.py --runs-dir ..\docs\evidence\2026-11-24-driving-state\runs
.venv\Scripts\python tools\release_gate.py --runs-dir ..\docs\evidence\2026-11-24-driving-state\runs --expect 3 --commit 300b081
```

## 이 실행 뒤에 바뀐 것

이 실행 뒤의 커밋은 문서, 소개 사이트, 결과 자료, 그리고 원자료를 모두 합치는 도구(`ivi-tests/tools/run_history.py`, [전체 실행 기록](../../run-history.md))와 그 단위 테스트입니다. E2E 테스트 코드(`ivi-tests/tests`, `ivi-tests/ivi`)와 앱(`ivi-app`)은 `300b081`과 같습니다.

```powershell
git diff --stat 300b081 HEAD -- ivi-tests/tests ivi-tests/ivi ivi-app
```
