// 공고 항목마다 이 프로젝트에서 한 것과 근거.
// build-docs.mjs 가 이 표로 두 가지를 만든다.
//   1) site/index.html 첫 화면의 '요구 역량' 목차 (<!-- fit:start --> ~ <!-- fit:end -->)
//   2) 결과 페이지의 ?req=<id> 거르기 (그 항목의 근거가 되는 테스트만 보여 준다)
//
// select 는 합집합이다: files(테스트 파일) · tests(함수 이름) · doc(설명 정규식) 중 하나라도 맞으면 넣는다.
// select 대신 chip(마커 칩을 미리 고름) · onlyBad(실패·재시도만) · all(전체) 을 쓸 수 있다.
// 테스트로 보일 수 없는 항목은 link 로 문서의 해당 절에 잇는다.

export const GROUPS = [
  { id: "duty", label: "주요 업무" },
  { id: "must", label: "자격요건" },
  { id: "plus", label: "우대사항" },
];

export const REQUIREMENTS = [
  {
    id: "services", group: "duty", title: "IVI 서비스별 검증 전략",
    done: "HVAC, 차량 설정, 클러스터 연동, 미디어를 서비스별 테스트로 나눔",
    select: { files: ["test_climate.py", "test_vehicle_signals.py", "test_settings.py", "test_cockpit.py", "test_driving.py", "test_media.py", "test_radio.py"] },
  },
  {
    id: "gating", group: "duty", title: "Smoke · Sanity · Regression 게이팅",
    done: (s) => `smoke ${s.smoke} · sanity ${s.sanity} · regression ${s.regression}. PR, main, Nightly마다 범위가 다름`,
    chip: "smoke",
    note: "빌드를 받을지 정하는 smoke 테스트입니다. 위의 칩으로 sanity, regression 범위도 볼 수 있습니다.",
  },
  {
    id: "e2e", group: "duty", title: "UI와 CarProperty/VHAL을 잇는 E2E",
    done: "화면 조작 → 차량 신호, 차량 신호 → 화면을 모두 확인. area 단위로 판정",
    select: { doc: /상위 → 하위|하위 → 상위/, files: ["test_spike_aaos.py"] },
  },
  {
    id: "integration", group: "duty", title: "터치부터 하위 연동까지 통합 검증",
    done: "말과 터치가 차량 신호까지, 신호가 경고와 충전소 안내까지 이어지는지",
    select: {
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
    done: "화면 객체 패턴. 7단계 화면 개편 때 테스트 64개 중 1개만 고침",
    link: { href: "docs/phase7-pleos.html#5-테스트", label: "7단계 기록" },
  },
  {
    id: "injection", group: "duty", title: "ADB · shell · CarPropertyManager로 Property Injection",
    done: "속도, 기어, 주행 가능 거리 같은 읽기 전용 신호는 dumpsys VHAL --set으로 넣음",
    select: {
      doc: /하위 → 상위/,
      files: ["test_driving.py", "test_rear_camera.py", "test_spike_aaos.py"],
      tests: [
        "test_parked_vehicle_does_not_advance_route", "test_trip_distance_follows_speed_signal",
        "test_lane_assist_indicator_follows_speed", "test_low_range_threshold", "test_range_recovers_after_charging",
      ],
    },
  },
  {
    id: "flaky", group: "duty", title: "Flaky 최소화 · 병렬 실행",
    done: (s) => `재시도 기록, 격리 목록, flaky 통계, 두 기기 병렬. 이번 실행 재시도 ${s.retries}`,
    onlyBad: true,
    note: (s) => `두 기기에서 ${s.runs}번 실행해 실패와 재시도가 ${s.bad}건입니다. 재시도 기록과 격리, 통계 방식은 <a href="portfolio.html#8-1-flaky-관리">포트폴리오 8-1</a>에 있습니다.`,
  },
  {
    id: "android", group: "must", title: "Android/AAOS 테스트 자동화 구축과 운영",
    done: (s) => `AAOS 에뮬레이터와 태블릿에서 E2E ${s.total}개. 테스트마다 끝 화면 보관`,
    all: true,
  },
  {
    id: "pytest", group: "must", title: "Python 테스트 프레임워크 (pytest)",
    done: "훅, 픽스처, 마커, 결과 기록 플러그인. 프레임워크 단위 테스트 36개",
    link: { href: "docs/phase3-framework.html#구조", label: "3단계 기록" },
  },
  {
    id: "appium", group: "must", title: "Appium 등 UI 자동화 도구",
    done: "Appium(UiAutomator2). AAOS 다중 사용자(user 10)에서 세션 연결",
    link: { href: "docs/phase1-spike.html#appium을-aaos에-붙일-때-필요한-것", label: "1단계 기록" },
  },
  {
    id: "adb", group: "must", title: "ADB · Logcat · Shell",
    done: "실패하면 logcat 자동 저장. logcat으로 앱이 꺼지는 원인을 찾음",
    link: { href: "docs/portfolio.html#5-결함과-원인-분석", label: "결함 기록" },
  },
  {
    id: "ci", group: "must", title: "Git · CI/CD",
    done: "PR 단위로 작업. GitHub Actions가 PR마다 build와 unit을 돌림",
    link: { href: "docs/portfolio.html#8-3-github-실행-기록", label: "실행 기록" },
  },
  {
    id: "vhal", group: "plus", title: "VHAL · CarService · CarPropertyManager",
    done: "신호 12종, area 구성, 권한 등급, priv-app 허용 목록",
    select: { files: ["test_vehicle_signals.py", "test_spike_aaos.py"] },
  },
  { id: "network", group: "plus", title: "차량 네트워크 (Ethernet, DDS, SOME/IP, CAN)", gap: "경험 없음" },
  { id: "rest", group: "plus", title: "REST API 자동화, 원격 전원 제어", gap: "아직 없음" },
  { id: "safety", group: "plus", title: "ISO 26262, A-SPICE", gap: "공부 필요" },
];
