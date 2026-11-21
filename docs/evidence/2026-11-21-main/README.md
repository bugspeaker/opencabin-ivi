# 지금 코드로 두 기기 전체 반복 3회 (2026-11-21)

2026-11-21 외부 검토(F01)에서 "마지막 기기 실행 뒤에 conftest, 차량 어댑터, 결과 기록, 게이트 코드가 바뀌어, 제출한 코드로 돌린 결과가 없다"는 지적을 받았습니다. 그래서 그 뒤의 변경을 모두 넣은 커밋 `d54741b`에서, 커밋하지 않은 변경 없이 두 기기 전체를 3회 반복했습니다. 같은 날 넣은 변경(바뀌지 않음 확인 10곳을 `stays`로, 앱 크래시·ANR 판정, 전원 테스트의 창 없는 재시작)도 이 실행에 들어 있습니다.

```powershell
.venv\Scripts\python tools\run_bench.py --repeat 3 --reruns 1 --shots
.venv\Scripts\python tools\release_gate.py --since 20261121-121400 --expect 3 --commit HEAD
```

## 결과

| 회차 (run id) | AAOS 에뮬레이터 | 태블릿 (Mock) | 병렬 실행 |
|---|---|---|---|
| `20261121-121421-r1` | 127 통과, 1 건너뜀, 1 알려진 결함 (605초) | 122 통과, 7 건너뜀 (659초) | 660초 |
| `20261121-122521-r2` | 127 통과, 1 건너뜀, 1 알려진 결함 (605초) | 122 통과, 7 건너뜀 (647초) | 649초 |
| `20261121-123610-r3` | 127 통과, 1 건너뜀, 1 알려진 결함 (604초) | 122 통과, 7 건너뜀 (649초) | 651초 |

- 실행한 테스트 750건(AAOS 384건, 태블릿 366건. 기기 전용이라 건너뛴 것은 빼고, 알려진 결함으로 xfail된 3건은 넣은 수), 재시도 0번, flaky 0건, 실패 0건, 세션 재연결 0번.
- 결과 파일 6개 모두 `commit` = `d54741b5…`, `dirty` = false, 앱 0.4.0 (4) APK sha256 `7109e4bd03c8…`, `exitstatus` = 0, 수집 129개, 실행 명령(`run_bench.py --repeat 3 --reruns 1 --shots`)이 남았습니다([runs](runs/)).
- Release 게이트 여섯 조건을 `--commit HEAD`(= `d54741b`)로 확인해 모두 통과했습니다([release-gate.txt](release-gate.txt)).
- 테스트 한 번에 걸리는 시간은 11-18(AAOS 9분 45초, 태블릿 10분 15초)보다 20~35초 늘었습니다. '바뀌지 않음' 확인 10곳이 1.5초씩 보고, 테스트마다 logcat을 한 번 더 읽기 때문입니다.
- [결과 페이지](../../test-results.md)의 판정과 화면은 3회차입니다. 영상 화면 두 장(두 기기의 `test_video_resumes_where_it_stopped`)은 앞차 번호판을 흐리게 해서 올렸습니다.

다시 세는 방법 (`ivi-tests`에서):

```powershell
.venv\Scripts\python tools\flaky_report.py --runs-dir ..\docs\evidence\2026-11-21-main\runs
.venv\Scripts\python tools\release_gate.py --runs-dir ..\docs\evidence\2026-11-21-main\runs --expect 3 --commit d54741b
```

## 첫 시도: 전원 테스트가 멈춘 에뮬레이터를 기다리다 실패

같은 날 11:51에 시작한 첫 반복(`20261121-115127`)은 1회차에서 멈췄습니다. 태블릿은 122개 통과였고, AAOS는 `test_power_cycle_brings_back_app_and_cabin_defaults` 하나가 실패했습니다([attempt1](attempt1/)).

| 시도 | 결과 |
|---|---|
| 1차 | 에뮬레이터를 끄고 다시 켰는데 새 에뮬레이터가 adb에 나타나지 않아 부팅 대기 240초를 넘김(`WaitTimeout`) |
| 재시도 | `PowerError: AVD 이름을 모른다`. 재시도가 만든 전원 제어는 켜져 있는 에뮬레이터에서 AVD 이름을 읽는데, 에뮬레이터가 꺼져 있어 다시 켜지 못함 |

- 원인: 다시 켠 에뮬레이터 프로세스는 떠 있었지만 로그가 `Found systemPath …` 다음에서 멈췄고 CPU도 거의 쓰지 않았습니다([로그 끝부분](attempt1/emulator-restart-tail.log)). 그때 PC 화면은 꺼져 있었습니다(모니터 상태 '오프라인'). 같은 명령을 창 모드로 다시 실행해 같은 지점에서 멈추는 것을 재현했고, `-no-window`를 붙이면 부팅됐습니다.
- 조치: 전원 제어가 에뮬레이터를 창 없이 다시 켜게 바꾸고(`d54741b`, `ivi-tests/ivi/power.py`) 단위 테스트를 더했습니다. 전원 테스트만 다시 돌려 통과(36초)를 확인한 뒤, 반복 3회를 처음부터 다시 돌렸습니다. 첫 시도의 결과는 위 통계에 넣지 않았습니다.
- 남은 약점: 재시도는 꺼진 에뮬레이터를 켜지 못합니다(AVD 이름을 켜진 에뮬레이터에서만 읽음). 이번에는 고치지 않았습니다.
- 첫 시도를 멈춘 뒤 보니 Appium 서버도 꺼져 있었습니다(로그가 세션 정리 도중에 끊김). 다시 띄운 뒤 전원 테스트를 확인했습니다.

## 앱 크래시 판정 확인

테스트 도중 앱이 죽으면 화면 판정이 통과해도 실패로 하는 판정(`ivi-tests/ivi/crashes.py`)을 넣은 뒤, 두 기기에서 테스트 도중 `am crash`로 앱을 일부러 죽이는 임시 테스트를 돌렸습니다(커밋하지 않음).

| 기기 | 결과 | 자료 |
|---|---|---|
| AAOS 에뮬레이터 (`20261121-probe2`) | `AppCrashed`로 failed. 실패 자료에 `app_crash.txt` (`FATAL EXCEPTION: main`, `Process: dev.opencabin.ivi`, `CrashedByAdbException: shell-induced crash`) | [결과 파일](crash-check/20261121-probe2-emulator-5554.json), [app_crash.txt](crash-check/app_crash-emulator-5554.txt) |
| 태블릿 (`20261121-probe5`) | `AppCrashed`로 failed, `app_crash.txt` 있음. 앱 안의 Mock 차량도 같이 죽어 정리 단계 오류도 함께 남음 | [결과 파일](crash-check/20261121-probe5-W3VBB22125209573.json), [app_crash.txt](crash-check/app_crash-W3VBB22125209573.txt) |

- 태블릿의 crash 버퍼에는 2026-11-19 Appium 서버(`io.appium.uiautomator2.server`)의 크래시가 남아 있었습니다. 이 앱의 것이 아니라 판정에 넣지 않습니다(단위 테스트에 같은 로그로 확인).
- 확인 중에 태블릿 화면에 화웨이의 'USB를 사용하여 다음 작업 수행' 창이 떠 앱을 가려 준비 단계 오류가 난 시도가 두 번 있었습니다. '취소'로 닫고(충전 전용 그대로) 다시 돌렸습니다.

## GitHub 호스트 러너의 AAOS smoke

같은 날 `ivi-ci.yml`에 e2e-hosted job을 더하고, 브랜치에서 수동 실행으로 확인했습니다. GitHub 호스트 러너(ubuntu)에 작업 PC와 같은 AAOS 이미지를 창 없이 띄우고, build job의 APK를 priv-app으로 넣은 뒤 smoke를 돌립니다.

| 실행 | e2e-hosted | 내용 |
|---|---|---|
| [44860180322](https://github.com/bugspeaker/opencabin-ivi/actions/runs/44860180322) | 실패 | AVD를 `~/.android/avd`가 아닌 곳에 만들어 설정 파일을 찾지 못함. 위치를 고정 |
| [44861042029](https://github.com/bugspeaker/opencabin-ivi/actions/runs/44861042029) | 통과 | smoke 13개 통과 (부팅 25초, smoke 58초, job 4분 21초) |
| [44861944480](https://github.com/bugspeaker/opencabin-ivi/actions/runs/44861944480) | 통과 | smoke 13개 통과 |
| [44861951956](https://github.com/bugspeaker/opencabin-ivi/actions/runs/44861951956) | 통과 | smoke 13개 통과 |

이 시험 실행들의 unit job은 실패로 남았습니다. 이 문서를 넣기 전이라, 포트폴리오에서 이 문서를 가리키는 링크를 끊긴 링크 검사가 막은 것입니다.

## 이 실행 뒤에 바뀐 것

이 실행 뒤의 커밋은 문서, 소개 사이트, 단위 테스트, CI 설정(e2e-hosted job과 실행 요약), 그리고 결과 자료입니다. E2E 테스트 코드(`ivi-tests/tests`, `ivi-tests/ivi`)와 앱(`ivi-app`)은 `d54741b`와 같습니다.

```powershell
git diff --stat d54741b HEAD -- ivi-tests/tests ivi-tests/ivi ivi-app
```
