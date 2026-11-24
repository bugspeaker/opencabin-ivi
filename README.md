<div align="center">

# OpenCabin IVI

**차량 화면과 차량 신호를 함께 확인하는 AAOS IVI 테스트 자동화**<br>
42dot Test Automation Engineer (IVI System) 지원 포트폴리오

[![포트폴리오 보기](docs/images/readme/btn-portfolio.svg)](https://bugspeaker.github.io/opencabin-ivi/)
[![테스트 결과](docs/images/readme/btn-results.svg)](https://bugspeaker.github.io/opencabin-ivi/site/docs/test-results.html)
[![공고 항목별 근거](docs/images/readme/btn-fit.svg)](https://bugspeaker.github.io/opencabin-ivi/site/fit.html)
[![상세 문서](docs/images/readme/btn-docs.svg)](docs/portfolio.md)

<br><br>

<img src="docs/images/demo-ui-vhal.gif" width="600" alt="운전석 + 를 누르면 VHAL 값이 22.0에서 22.5로, VHAL에 25.0을 넣으면 화면이 25.0으로 바뀌는 모습 (AAOS 에뮬레이터)">

화면에서 + 를 누르면 VHAL 값이 22.0 → 22.5, VHAL에 25.0을 넣으면 화면도 25.0 (AAOS 에뮬레이터)

</div>

## 한눈에 보기

| E2E 테스트 | 반복 실행 | 두 기기 병렬 실행 | 테스트에서 나온 문제 |
|:---:|:---:|:---:|:---:|
| **144개** | **837건 중 실패 0** | **약 13분** | **15건** |
| 두 기기에서 같은 테스트 코드 | 두 기기 × 3회 (2026-11-24)<br>재시도로 통과한 것도 0건 | 차례로 돌리면 약 25분 | 원인과 조치를 [이슈](https://github.com/bugspeaker/opencabin-ivi/issues?q=is%3Aissue)로 기록 |

## 왜 만들었나

IVI는 화면이 맞아도 차량에는 틀린 값이 갈 수 있습니다. A/C를 끄면 화면의 버튼은 '꺼짐'으로 바뀌지만, 앱이 운전석 값만 끄면 나머지 좌석은 계속 켜져 있습니다. 화면만 보는 UI 테스트는 이 경우도 통과로 판정합니다.

그래서 화면과 차량 신호(VHAL)를 따로 읽어 둘 다 맞아야 통과로 보는 E2E 테스트를 만들었습니다. 실차도, 헤드 유닛도 없어서, 테스트할 IVI 앱부터 테스트 도구까지 AI 코딩 도구(Claude Code)로 만들고 같은 테스트를 AAOS 에뮬레이터와 실제 태블릿에서 돌렸습니다. 2026-11-23에는 갤럭시 폴드를 세 번째 기기로 붙였습니다.

| 막힌 곳 | 도구에 더한 것 |
|---|---|
| 차례로 돌리면 약 25분 걸렸습니다. | 두 기기를 병렬로 돌려 약 13분으로 줄였습니다. |
| 재시도 통과가 흔들림을 가렸습니다. | 재시도로 통과하면 flaky로 따로 세고 통계를 냈습니다. |
| '실패 0'이어도 일부만 돌았을 수 있었습니다. | Release 게이트가 끝까지 돌렸는지 먼저 보게 했습니다. |
| 원인을 보려면 다시 재현해야 했습니다. | 실패 순간의 화면, 화면 구조, 차량 값, 로그를 남겼습니다. |
| 결과를 글자로만 볼 수 있었습니다. | 판정 직후 화면을 남기는 [결과 페이지](docs/test-results.md)를 만들었습니다. |
| 매번 손으로 돌려야 했습니다. | PR마다 Actions가 빌드, 단위 테스트, smoke를 돌리게 했습니다. |
| 추적 누락 0이어도 확인하지 않은 조건이 있었습니다. | 조건, 화면 요소, 경계값으로 다시 점검해 테스트 11개를 더했습니다. |
| D 기어로 멈춰 있을 때 기기마다 제한이 달랐습니다. | 플랫폼이 알려 준 제한 종류를 따르게 하고, 속도를 시간에 따라 바꾸는 시나리오로 확인했습니다. |
| 좁은 폴드 화면에서 버튼이 가려졌습니다. | 가려진 버튼은 누르지 않고 실패로 남기게 했습니다. |

찾은 문제와 원인은 [상세 문서 3장](docs/portfolio.md#3-결함과-원인-분석)에, 게이트 기준은 [4장](docs/portfolio.md#4-검증-전략)에 있습니다.

## 만든 사람과 만든 방식

- **경력**: 게임 QA 8년차입니다(2017.12부터 약 7년 8개월, 회사 4곳). 멀티플랫폼 호환성, 라이브 업데이트·BM, 글로벌 현지화를 검수했고, 외부 QA사·퍼블리셔와 협업했으며, AI R&D 조직과 테스트 대시보드를 만들었습니다. ISTQB CTFL을 땄습니다.
- **이전에 만든 도구**: 개인 포트폴리오로 웹 BVT 도구를 바이브 코딩으로 만들었습니다. 엑셀 BVT 대시보드에 Playwright·pytest를 붙여 공개 웹 서비스의 BVT 70개 중 47개를 자동화했습니다([데모](docs/portfolio.md#만든-사람과-만든-방식)). 업무에 쓰는 TC 관리 도구 Bugspeaker Zone에는 이 프로젝트의 결과를 읽어 들이는 화면을 붙였습니다(같은 곳에 GIF). 모바일 자동화는 Appium 실습 경험을 바탕으로 이 프로젝트에서 AAOS까지 넓혀 업무 수준으로 적용했습니다.
- **기간**: 2026-11-13부터, 혼자 진행했습니다.
- **역할**: AI 코딩 도구 Claude Code로 앱과 테스트 도구를 만들었습니다. 무엇을 만들지 정하고, E2E 테스트 설계는 Claude와 함께 했습니다. AI가 낸 변경과 외부 검토 항목은 기기 실행 기록과 자동 검사로 확인하여 반영 여부를 결정했고, PR을 병합했습니다. 무엇을 고르고 버렸는지는 [결정 기록](docs/decisions.md)에 있습니다.
- **AI 결과 검증**: AI의 '통과'는 기기 실행 결과 파일, Release 게이트, CI의 추적·링크 검사로만 받아들였습니다. 검증에서 잡혀 고친 사례 7건, Claude의 추천과 다르게 정한 사례 5건, 앱을 직접 써 보며 준 피드백 6건은 [AI 결과를 어떻게 검증했나](docs/portfolio.md#ai-결과를-어떻게-검증했나)에 있습니다.

## 결과 자료와 검증 시점

| 자료 | 결과 |
|---|---|
| [주행 상태 읽기 수정 후 반복 실행 3회](docs/evidence/2026-11-24-driving-state/README.md)<br>2026-11-24, 코드 `300b081` | 주행 상태를 못 읽으면 '제한 없음'으로 처리하던 테스트 도구를 고친 뒤, 테스트 144개를 두 기기에서 3회 돌렸습니다.<br>실패 0, flaky 0으로 Release 게이트를 통과했습니다. 폴드도 같은 코드로 한 번 통과했습니다. 첫 시도는 USB 창 때문에 1회차 태블릿이 실패해 그대로 남겼습니다. |
| [정지 상태 결함 수정 후 반복 실행 3회](docs/evidence/2026-11-23-idling/README.md)<br>2026-11-23 저녁, 코드 `de9d062` | D 기어로 멈춘 상태의 제한 결함(#47)을 고친 앱 0.4.2와 테스트 144개를 두 기기에서 3회 돌렸습니다.<br>실패 0, flaky 0으로 Release 게이트를 통과했습니다. 폴드도 같은 코드로 한 번 통과했습니다. |
| [테스트 범위 보강과 반복 실행 3회](docs/evidence/2026-11-23-coverage/README.md)<br>2026-11-23 오후, 코드 `55419f7` | 빈 곳에 테스트 11개를 더한 140개를 두 기기에서 3회 돌렸습니다.<br>실패 0, flaky 0으로 Release 게이트를 통과했습니다. 폴드도 같은 코드로 한 번 통과했습니다. |
| [반복 실행 3회 (이전)](docs/evidence/2026-11-21-main/README.md)<br>2026-11-21, 코드 `d54741b` | 129개를 두 기기에서 3회 돌렸습니다.<br>실패 0, flaky 0으로 Release 게이트를 통과했습니다. |
| [GitHub 호스트 러너 smoke](docs/evidence/2026-11-21-main/README.md#github-호스트-러너의-aaos-smoke)<br>2026-11-21, 코드 `8bb3a33` | AAOS smoke 13개가 Actions에서 3회 연속 통과했습니다. |
| [갤럭시 폴드](docs/evidence/2026-11-23-fold/README.md)<br>2026-11-23, 코드 `c112673` → `7aaab6f` | 세 번째 기기에서 129개 중 5개가 실패했습니다(좁은 화면의 배치).<br>앱을 고친 뒤(0.4.1) 폴드, 태블릿, 에뮬레이터 모두 게이트를 통과했습니다. |

반복 실행은 커밋하지 않은 변경 없이 돌렸고, 같은 커밋으로 갤럭시 폴드도 한 번 돌려 통과했습니다. 그 뒤에 바뀐 것은 문서, 소개 사이트, 결과 자료, 원자료를 모두 합치는 도구입니다. 첫 시도와 확인용 실행까지 합친 수와 실패마다의 원인은 [전체 실행 기록](docs/run-history.md)에 있습니다. 이전 실행과 그때의 코드 시점은 [결과 원자료 목록](docs/evidence/README.md)에 있습니다.

## 한계

- 실제 차량, HIL, CAN 장비는 쓰지 않았습니다. VHAL은 에뮬레이터의 가상 값이고, CAN과 원격 전원은 PC 안의 모의 환경입니다.
- GitHub에서 자동으로 도는 E2E는 AAOS smoke 13개입니다. 태블릿과 전체 회귀는 같은 명령을 작업 PC에서 돌렸습니다.
- 앱도 이 프로젝트에서 만들어서 테스트에 필요한 표시를 마음대로 넣을 수 있었습니다. 다른 팀이 만든 앱을 테스트하는 실제 환경과 다릅니다.

## 저장소 구성

```
ivi-app/              테스트할 IVI 앱 (Kotlin, Compose)
ivi-tests/
  ivi/                기기·차량 어댑터, 화면 객체, 결과 기록, Test Bench API, CAN 게이트웨이
  tests/              기기 E2E 테스트
  unit/               프레임워크 단위 테스트 (기기 없이 돎)
  tools/              병렬 실행, flaky 통계, 결과 사이트, 추적표
.github/workflows/    ivi-ci.yml (build, unit, e2e), pages.yml (소개 사이트)
docs/                 상세 문서, 단계별 기록, 요구사항과 추적표, 결정 기록
site/                 소개 사이트 (GitHub Pages)
```

실행 방법은 [docs/run.md](docs/run.md)에 있습니다. 에뮬레이터를 켜고 Appium 서버를 띄운 뒤 `ivi-tests`에서 `pytest -m smoke` 또는 두 기기 병렬 실행 `tools\run_bench.py`를 돌립니다.

## 문서

| 문서 | 내용 |
|---|---|
| [상세 문서](docs/portfolio.md) | 공고 대응표, 테스트 환경, 결함 분석, 검증 전략, CI를 정리했습니다. |
| [테스트 결과](docs/test-results.md) | 테스트 144개의 판정과 판정 직후 화면을 보여 줍니다. |
| [반복 실행 통계](docs/flaky-report.md) | 두 기기 × 3회 실행의 테스트별 불안정률입니다. |
| [전체 실행 기록](docs/run-history.md) | 원자료가 남은 E2E 실행을 모두 합친 수와, 실패·재시도 통과마다 원인입니다. |
| [결정 기록](docs/decisions.md) | 고른 것과 버린 것, 근거가 된 측정값을 적었습니다. |
| [요구사항](docs/requirements.md) | 요구사항 27개와 조건별 확인입니다. |
| [추적표](docs/traceability.md) | 요구사항과 테스트를 양쪽으로 이었습니다. |

단계별 기록: [1 기술 검증](docs/phase1-spike.md) · [2 앱](docs/phase2-app.md) · [3 프레임워크](docs/phase3-framework.md) · [4 운영](docs/phase4-operations.md) · [5 재점검](docs/phase5-design.md) · [6 기능 확장](docs/phase6-features.md) · [7 화면 개편](docs/phase7-layout.md) · [8 차량 신호](docs/phase8-signals.md) · [9 Test Bench](docs/phase9-bench.md)

<details>
<summary>용어 풀이</summary>

| 용어 | 뜻 |
|---|---|
| AAOS | Android Automotive OS. 차량에 직접 들어가는 안드로이드 |
| IVI | In-Vehicle Infotainment. 내비, 미디어, 공조 화면 같은 차량 인포테인먼트 |
| VHAL | Vehicle HAL. 차량 신호를 안드로이드에 넘겨 주는 층. 여기서는 에뮬레이터의 가상 값 |
| CarService | AAOS에서 앱과 VHAL 사이에서 차량 값을 주고받는 시스템 서비스 |
| E2E | 화면 조작부터 차량 값까지 실제 경로 전체를 거치는 테스트 |
| Mock | 실제 대신 쓰는 가짜 구현. 태블릿에서는 앱 안의 가짜 차량 서비스 |
| flaky | 같은 코드인데 실행마다 통과와 실패가 바뀌는 테스트. 여기서는 실패 뒤 재시도에서 통과한 경우 |
| smoke / sanity / regression | 빌드를 받아도 되는지 보는 짧은 확인 / 서비스마다 대표 경로 / 경계값과 조합까지 보는 전체 회귀 |
| Release 게이트 | 릴리스 후보를 내보내도 되는지 정하는 자동 판정 (여섯 조건) |

</details>
