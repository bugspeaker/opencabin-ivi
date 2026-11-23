// 공고 항목마다 이 프로젝트에서 한 것과 근거.
// build-docs.mjs 가 이 표로 두 가지를 만든다.
//   1) site/index.html 첫 화면의 '요구 역량' 목차 (<!-- fit:start --> ~ <!-- fit:end -->)
//   2) 결과 페이지의 ?req=<id> 거르기 (그 항목의 근거가 되는 테스트만 보여 준다)
//
// select 는 합집합이다: files(테스트 파일) · tests(함수 이름) · doc(설명 정규식) 중 하나라도 맞으면 넣는다.
// doc 은 설명 문구가 바뀌면 조용히 빠지므로, 되도록 files 와 tests 로 적는다.
// lead 는 결과 페이지에서 파일 목록보다 먼저 보여 줄 대표 근거 2~3개다 (select 로 고른 테스트 안에서).
// select 대신 chip(마커 칩을 미리 고름) · onlyBad(실패·재시도만) · all(전체) 을 쓸 수 있다.
// 테스트로 보일 수 없는 항목은 link 로 문서의 해당 절에 잇는다. 근거가 표인 항목은 link 와 select/chip 을 함께 둔다:
// 목차는 문서의 표로 가고, 결과 페이지 ?req=<id> 로 그 항목의 테스트도 볼 수 있다.

export const GROUPS = [
  { id: "duty", label: "주요 업무" },
  { id: "must", label: "자격요건" },
  { id: "plus", label: "우대사항" },
];

export const REQUIREMENTS = [
  {
    id: "services", group: "duty", title: "IVI 서비스별·단계별 검증 전략", partial: "클러스터 제외",
    done: "HVAC, 차량 설정(도어), 주행 정보 패널(앱 왼쪽, 계기판 역할), 미디어를 나누고, 서비스마다 주요 위험과 확인 방향(화면→신호, 신호→화면)을 정해 테스트했습니다. 단계는 앱 단위 테스트, 프레임워크 단위 테스트, 에뮬레이터·태블릿 E2E까지이고 HIL과 실차는 하지 않았습니다.",
    // 근거는 테스트 목록이 아니라 서비스별 전략 표다. 테스트 목록은 결과 페이지 ?req=services 로 그대로 볼 수 있다
    link: { href: "docs/portfolio.html#4-2-서비스별-검증", label: "서비스별·단계별 표" },
    note: "서비스별 위험, 확인 방향, 테스트 수와 검증 단계는 <a href=\"portfolio.html#4-2-서비스별-검증\">포트폴리오 4-2</a>에 표로 정리했습니다. AAOS 클러스터 디스플레이(보조 화면)와의 연동은 검증하지 않았습니다.",
    select: { files: ["test_climate.py", "test_vehicle_signals.py", "test_settings.py", "test_cockpit.py", "test_driving.py", "test_media.py", "test_radio.py"] },
  },
  {
    id: "gating", group: "duty", title: "Smoke · Sanity · Regression 게이팅",
    done: (s) => `smoke ${s.smoke}개, sanity ${s.sanity}개, regression ${s.regression}개를 고르는 기준, 시간, 통과 조건을 정하고 PR, main, Nightly, Release마다 돌리는 범위를 나눴습니다.`,
    // 근거는 게이트 기준 표와 ivi-ci.yml 이다. smoke 목록은 결과 페이지 ?req=gating 으로 볼 수 있다
    link: { href: "docs/portfolio.html#4-1-게이트-단계와-기준", label: "게이트 기준 표" },
    chip: "smoke",
    note: "빌드를 받아도 되는지 정하는 smoke 테스트입니다. 아래 버튼으로 sanity와 regression 범위도 볼 수 있습니다. Release 게이트는 실패가 0인지만 보지 않고, 두 기기 모두 지금 코드의 테스트를 끝까지 돌렸는지(종료 코드 0, 기기 전용이 아닌 건너뜀 없음)를 먼저 봅니다. 단계별 기준과 여섯 조건은 <a href=\"portfolio.html#4-1-게이트-단계와-기준\">포트폴리오 4-1</a>에 있습니다.",
  },
  {
    id: "e2e", group: "duty", title: "UI와 CarProperty/VHAL을 잇는 E2E",
    done: "화면 조작이 차량 신호로, 신호 변화가 화면으로 이어지는지 양쪽을 봤습니다. 좌석과 문은 area마다 확인합니다.",
    // 결과 페이지에서 먼저 보여 줄 대표 근거: 버튼 → VHAL, VHAL → 화면, 전 좌석 area
    lead: ["test_button_changes_signal_by_one_step", "test_signal_is_shown_on_climate_and_home", "test_ac_toggle_reaches_every_seat"],
    select: {
      files: ["test_spike_aaos.py"],
      tests: [
        // 화면에서 신호로, 신호에서 화면으로 양쪽을 보는 테스트
        "test_typed_command_sets_vehicle_temperature", "test_signal_is_shown_on_climate_and_home",
        "test_button_changes_signal_by_one_step", "test_bottom_bar_temperature_drives_vehicle",
        "test_sync_mirrors_driver_temperature_to_passenger", "test_guidance_counts_down_with_vehicle_speed",
        "test_ac_toggle_reaches_every_seat", "test_ac_signal_is_shown_on_climate_and_bottom_bar",
        "test_fan_button_changes_signal_by_one", "test_max_ac_sets_signal_and_coldest_settings",
        "test_max_ac_signal_is_shown_on_toggle", "test_defrost_changes_only_its_window",
        "test_seat_heat_cycles_levels_on_vehicle", "test_seat_heat_signal_is_shown_everywhere",
        "test_door_lock_button_drives_every_door", "test_door_lock_signal_is_shown",
        "test_energy_signals_are_shown_on_cluster",
      ],
    },
  },
  {
    id: "integration", group: "duty", title: "터치부터 하위 연동까지 통합 검증",
    done: "AAOS 에뮬레이터에서 화면의 운전석 온도를 한 칸 올리면, 앱 → CarService → VHAL로 바뀐 값을 게이트웨이가 adb로 읽어 CAN 프레임(IVI_HvacStatus)으로 내보내고, 그 값이 22.5°C인지 확인합니다. 반대로 가상 ECU가 보낸 CAN 프레임이 VHAL을 거쳐 화면에 보이는지도 봅니다.",
    lead: ["test_climate_button_goes_out_on_can", "test_zone_applies_command_to_speaking_seat", "test_low_range_card_starts_guidance_to_nearest_charger"],
    note: "CAN 쪽은 PC 안의 가상 버스(python-can, DBC)입니다. 태블릿에서는 같은 테스트가 VHAL 대신 앱 안의 Mock 차량을 거칩니다. 음성과 터치가 차량 신호까지, 거리 부족 신호가 경고와 충전소 안내까지 이어지는 흐름도 함께 봅니다.",
    select: {
      files: ["test_can_gateway.py"],
      tests: [
        "test_zone_applies_command_to_speaking_seat", "test_typed_command_sets_vehicle_temperature",
        "test_voice_sets_driver_temperature_on_vehicle", "test_assistant_seat_heat_follows_speaker_zone",
        "test_bottom_bar_seat_heat_works_from_any_screen", "test_low_range_card_starts_guidance_to_nearest_charger",
        "test_low_range_is_recorded_in_notifications", "test_guidance_counts_down_with_vehicle_speed",
        "test_mph_setting_converts_vehicle_speed", "test_range_follows_speed_unit_setting",
      ],
    },
  },
  {
    id: "maintenance", group: "duty", title: "프레임워크와 스크립트 유지보수",
    done: "7단계에서 아래 바 구성이 바뀌었을 때 화면 객체(screens.py)의 여는 경로만 고쳤고, 화면 개편 때문에 바꾼 테스트는 기존 64개 가운데 1개입니다.",
    link: { href: "docs/phase7-layout.html#5-테스트", label: "7단계 기록" },
  },
  {
    id: "injection", group: "duty", title: "ADB · shell · CarPropertyManager로 Property Injection과 이벤트 검증",
    done: "앱과 같은 경로가 필요한 설정 온도는 cmd car_service로, 속도·기어 같은 읽기 전용 값과 차량 쪽에서 바뀐 공조·도어 값은 dumpsys로 VHAL에 바로 넣습니다. 이벤트는 값을 넣은 뒤 앱 화면이 바뀌는 것으로 확인합니다(앱이 onChangeEvent로 받은 값). 이벤트 횟수, 순서, 시각, onErrorEvent는 따로 판정하지 않습니다.",
    lead: ["test_signal_is_shown_on_climate_and_home", "test_guidance_counts_down_with_vehicle_speed", "test_door_lock_signal_is_shown"],
    select: {
      files: ["test_driving.py", "test_rear_camera.py", "test_spike_aaos.py"],
      tests: [
        // 차량 쪽 신호를 adb 로 넣고 화면이 따라오는지 보는 테스트
        "test_signal_is_shown_on_climate_and_home", "test_bottom_bar_temperature_drives_vehicle",
        "test_guidance_counts_down_with_vehicle_speed", "test_parked_vehicle_does_not_advance_route",
        "test_trip_distance_follows_speed_signal", "test_lane_assist_indicator_follows_speed",
        "test_ac_signal_is_shown_on_climate_and_bottom_bar", "test_max_ac_signal_is_shown_on_toggle",
        "test_seat_heat_signal_is_shown_everywhere", "test_door_lock_signal_is_shown",
        "test_energy_signals_are_shown_on_cluster", "test_low_range_threshold", "test_range_recovers_after_charging",
      ],
    },
  },
  {
    id: "flaky", group: "duty", title: "Flaky 최소화 · 병렬 실행",
    done: (s) => s.stability
      ? `두 기기를 병렬로 ${s.stability.rounds}번 반복해 테스트 ${s.stability.executions.toLocaleString("en-US")}건을 돌렸고, 재시도로 통과한 것(flaky)은 ${s.stability.flaky}건입니다. 재시도 기록, 격리 목록, flaky 통계와 Release 게이트를 만들었습니다.`
      : "재시도 기록, 격리 목록, flaky 통계를 만들고 두 기기를 병렬로 돌렸습니다.",
    link: { href: "docs/flaky-report.html", label: "반복 실행 통계" },
  },
  {
    id: "experience", group: "must", title: "테스트 자동화나 QA 3년 이상",
    done: "게임 QA 8년차(2017.12부터 약 7년 8개월, 회사 4곳). 멀티플랫폼 호환성, 라이브 업데이트와 BM, 글로벌 현지화 검수, AI R&D 연계 테스트 대시보드 구축. ISTQB CTFL. 자동화는 바이브 코딩으로 만든 웹 BVT 도구(개인 포트폴리오, 엑셀 BVT 대시보드 + Playwright·pytest, 공개 웹 서비스 BVT 70개 중 47개 자동화)와 이 프로젝트입니다.",
    link: { href: "docs/portfolio.html#만든-사람과-만든-방식", label: "경력" },
  },
  {
    id: "android", group: "must", title: "Android/AAOS 테스트 자동화 구축과 운영",
    done: (s) => `AAOS 에뮬레이터와 태블릿에서 E2E ${s.total}개를 돌리고, 테스트마다 판정 직후 화면을 남겼습니다.`,
    all: true,
  },
  {
    id: "pytest", group: "must", title: "Python 테스트 프레임워크 (pytest)",
    done: "훅, 픽스처, 마커와 결과 기록 플러그인을 만들었습니다. 프레임워크 단위 테스트가 195개 있습니다.",
    link: { href: "docs/phase3-framework.html#구조", label: "3단계 기록" },
  },
  {
    id: "appium", group: "must", title: "Appium 등 UI 자동화 도구",
    done: "Appium(UiAutomator2)을 AAOS의 다중 사용자 환경(user 10)에 붙여 썼습니다.",
    link: { href: "docs/phase1-spike.html#appium을-aaos에-붙일-때-필요한-것", label: "1단계 기록" },
  },
  {
    id: "adb", group: "must", title: "ADB · Logcat · Shell",
    done: "테스트 도중 앱 크래시나 ANR이 logcat에 남으면 화면 판정이 통과해도 실패로 합니다. 실패하면 logcat을 자동으로 저장하고, 앱이 강제로 꺼지던 원인도 logcat에서 찾았습니다.",
    link: { href: "docs/portfolio.html#3-결함과-원인-분석", label: "결함 기록" },
  },
  {
    id: "ci", group: "must", title: "Git · CI/CD",
    done: "PR 단위로 작업했고, GitHub Actions가 PR마다 빌드, 단위 테스트, 호스트 러너의 AAOS 에뮬레이터 smoke 13개를 무인으로 돌립니다. 태블릿과 전체 회귀는 작업 PC에서 돌렸습니다.",
    link: { href: "docs/portfolio.html#8-3-github-실행-기록", label: "실행 기록" },
  },
  {
    id: "vhal", group: "plus", title: "VHAL · CarService · CarPropertyManager",
    done: "신호 12종을 연결하면서 area 구성, 권한 등급, priv-app 허용 목록을 다뤘습니다.",
    select: { files: ["test_vehicle_signals.py", "test_spike_aaos.py"] },
  },
  // 아래 셋은 실제 장비나 인증 경험이 아니라 PC 안의 모의 환경, 개념 적용이라 그 사실을 표시한다 (partial)
  {
    id: "network", group: "plus", title: "차량 네트워크 (Ethernet, DDS, SOME/IP, CAN)", partial: "CAN만 모의",
    done: "가상 CAN 버스와 DBC로 VCU, BMS, BCM 역할의 가상 ECU를 두고, 게이트웨이가 VHAL에 넣은 값이 화면까지 오는지 확인했습니다. Ethernet, DDS, SOME/IP는 아직 해 보지 않았습니다.",
    select: { files: ["test_can_gateway.py"] },
    note: "PC 안의 가상 CAN 버스에서 돌린 테스트입니다. 실제 ECU와 CAN 장비, 버스 부하와 타이밍은 다루지 않았습니다.",
  },
  {
    id: "rest", group: "plus", title: "REST API 자동화, 원격 전원 제어", partial: "모의 장비",
    done: "Test Bench REST API로 기기, 차량 신호, 전원, 실행 결과를 다루고, 에뮬레이터 전원을 껐다 켜 부팅 시간을 쟀습니다. 실제 전원 장비는 쓰지 않았습니다.",
    select: { files: ["test_bench_api.py", "test_power.py"] },
    note: "API 서버를 띄워 HTTP로 신호를 넣은 테스트와, 에뮬레이터를 원격으로 껐다 켠 테스트입니다. 실제 벤치라면 전원 공급기나 릴레이가 들어갈 자리를 같은 인터페이스로 비워 두었습니다.",
  },
  {
    id: "safety", group: "plus", title: "ISO 26262, A-SPICE", partial: "개념 적용",
    done: "요구사항 26개와 테스트를 양방향으로 잇는 추적표를 만들고, 빠진 곳이 있으면 CI의 unit job이 실패하게 했습니다. 연결 누락 0은 조건별 검증이 충분하다는 뜻이 아니라서, 조건이 여럿인 요구사항은 조건마다 확인하는 곳을 따로 적고 테스트가 없는 조건을 밝혔습니다. 인증이나 심사 경험은 없습니다.",
    link: { href: "docs/traceability.html", label: "추적표" },
  },
];
