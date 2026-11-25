# 예외 경로 수정과 동시 조작 테스트 뒤 반복 3회 (2026-11-24)

외부 검토(IVI-REV-03~07)의 예외 경로를 고치고 동시 조작 E2E 6개(요구사항 SYS-02)를 더한 커밋을 main에 병합한 뒤(`101de99`, PR [#54](https://github.com/bugspeaker/opencabin-ivi/pull/54)), 두 기기 × 3회와 갤럭시 폴드 1회를 다시 돌린 원자료입니다. 테스트는 144개에서 150개가 됐고 앱(0.4.2)은 바뀌지 않았습니다. 무엇을 고쳤고 왜 넣었는지는 [9단계 기록 9절](../../phase9-bench.md#9-외부-검토-반영-2026-11-24-예외-경로와-동시-조작)에 있습니다.

## 첫 확인

커밋하기 전 작업 트리(`410a052` + 변경)로 새 테스트 6개와, 바꾼 CAN 게이트웨이를 쓰는 CAN E2E 3개를 먼저 돌렸습니다([runs-first](runs-first/)).

| 실행 | 기기 | 결과 |
|---|---|---|
| `20261124-153908`, `20261124-153909` | AAOS 에뮬레이터, 태블릿 | 태블릿 9개 통과. AAOS는 빠른 누름 2개가 실패하고 7개 통과 |
| `20261124-154050` | AAOS 에뮬레이터 | 빠른 누름 2개를 누름 사이 대기 없이 다시 보냈으나 같은 실패 |
| `20261124-154132` | AAOS 에뮬레이터 | adb `input tap`으로 바꾼 빠른 누름 2개 통과 |
| `20261124-154306` | 세 기기 | 9개 모두 통과 |

- 실패는 앱이 아니라 테스트 도구 문제였습니다. 빠른 누름을 Appium W3C 동작으로 보냈더니, AAOS 에뮬레이터에서 누른 채 기다리는 동안 UiAutomator2가 만드는 MOVE 이벤트 주입이 실패해 동작 전체가 `Unable to perform W3C actions`로 끝났습니다. 태블릿과 폴드에서는 같은 동작이 통과했습니다.
- adb 셸 한 번에 `input tap`과 `sleep 0.1`을 잇는 방식으로 바꾼 뒤 세 기기 모두 통과했습니다.
- 누름 사이를 0.05초, 0.03초, 0초로 줄여 보는 확인은 저장소에 넣지 않은 임시 테스트로 했습니다([probe](probe/), 두 기기 각 3개 통과). 간격 0에서도 네 번이 모두 들어갔습니다.

## 두 기기 × 3회와 폴드 1회

병합 커밋 `101de99`(커밋하지 않은 변경 없음, 앱 0.4.2 (6) APK sha256 `c977c9069411…`)에서 돌렸습니다.

```powershell
.venv\Scripts\python tools\run_bench.py --devices emulator-5554,W3VBB22125209573 --repeat 3 --reruns 1 --shots
.venv\Scripts\python -m pytest --serial R38M309YKQY --reruns 1 --shots --run-id 20261124-fold-150
```

| 회차 (run id) | AAOS 에뮬레이터 | 태블릿 (Mock) | 병렬 실행 |
|---|---|---|---|
| `20261124-155827-r1` | 148 통과, 1 건너뜀, 1 알려진 결함 (13분 10초) | 142 통과, 8 건너뜀 (13분 38초) | 13분 39초 |
| `20261124-161206-r2` | 148 통과, 1 건너뜀, 1 알려진 결함 (13분 6초) | 142 통과, 8 건너뜀 (13분 32초) | 13분 33초 |
| `20261124-162540-r3` | 148 통과, 1 건너뜀, 1 알려진 결함 (13분 1초) | 142 통과, 8 건너뜀 (13분 35초) | 13분 36초 |
| `20261124-fold-150` (폴드, 따로 1회) | | 갤럭시 폴드: 142 통과, 8 건너뜀 (14분 24초) | |

- 실행한 테스트 873건(AAOS 447건, 태블릿 426건), 재시도 0번, flaky 0건, 실패 0건, 세션 재연결 0번입니다([runs](runs/), [runs-fold](runs-fold/)).
- 1회차 AAOS의 `test_low_range_card_starts_guidance_to_nearest_charger`에서 차량 속도(50 km/h)를 넣는 VHAL 명령이 첫 시도에 실패하고 0.3초 뒤 두 번째에 성공했습니다(신호 재시도 1번). 테스트를 다시 돌린 것이 아니라 flaky로 세지 않고, 결과 파일과 [반복 실행 통계](../../flaky-report.md)에 그대로 남겼습니다.
- Release 게이트 여섯 조건을 `--commit 101de99`로 확인해 모두 통과했습니다([release-gate.txt](release-gate.txt)). 폴드 1회도 따로 확인해 통과했습니다([release-gate-fold.txt](release-gate-fold.txt)).
- 병렬 실행 한 회차가 144개 때(12분 45초~12분 49초)보다 약 50초 길어졌습니다. 더한 6개의 테스트 시간이 AAOS 약 43초, 태블릿 약 48초입니다.
- [결과 페이지](../../test-results.md)의 판정과 화면은 3회차와 폴드 1회입니다. 영상 화면 세 장(`test_video_resumes_where_it_stopped`)은 앞차 번호판을 흐리게 해서 올렸습니다.

다시 세는 방법 (`ivi-tests`에서):

```powershell
.venv\Scripts\python tools\flaky_report.py --runs-dir ..\docs\evidence\2026-11-24-concurrency\runs
.venv\Scripts\python tools\release_gate.py --runs-dir ..\docs\evidence\2026-11-24-concurrency\runs --expect 3 --commit 101de99
```

## 이 실행 뒤에 바뀐 것

이 실행 뒤의 커밋은 문서, 소개 사이트, 결과 자료와 실행 기록 등록부(`ivi-tests/tools/run_history.py`), 결함 주입 집계 도구(`ivi-tests/tools/fault_report.py`)입니다. 앱(`ivi-app`)은 `101de99`와 같습니다. E2E 테스트 코드는 2026-11-25 [결함 주입 실험](../2026-11-25-fault-injection/README.md#놓친-결함-f08)에서 `test_seat_heat_signal_is_shown_everywhere` 하나를 보강한 것만 다릅니다(테스트 수는 150개 그대로). 보강한 테스트는 두 기기에서 main 앱으로 통과를 확인했고, 보강 뒤에 반복 실행은 다시 하지 않았습니다.

```powershell
git diff --stat 101de99 HEAD -- ivi-tests/tests ivi-tests/ivi ivi-app
```
