/* 용어 풀이: 약어와 전문 용어에 마우스를 올리면 뜻이 보이게 한다 (<abbr title>, 점선 밑줄. 링크처럼 파랗게 하지 않는다).
 * 휴대폰과 키보드에서는 용어를 누르거나 Tab 으로 가면 풀이 상자가 뜬다 (enableTips).
 *
 * - 소개 사이트: 이 파일을 읽은 페이지에서 본문의 용어를 절(h2, section)마다 처음 나올 때 한 번씩 감싼다.
 *   코드, 링크, 제목, 버튼, 그림 안의 글자는 건드리지 않는다.
 * - GitHub README: 자바스크립트가 돌지 않으므로 annotate-readme.mjs 가 같은 목록으로 README.md 에 <abbr> 를 넣는다.
 * 뜻은 이 프로젝트에서 쓰는 뜻으로 짧게 적는다. 표(|)와 따옴표(")는 쓰지 않는다 (README 표와 title 속성이 깨진다).
 */
(function (root) {
  var TERMS = [
    ["AAOS", "Android Automotive OS. 차량에 직접 들어가는 안드로이드"],
    ["IVI", "In-Vehicle Infotainment. 내비, 미디어, 공조 화면 같은 차량 인포테인먼트"],
    ["VHAL", "Vehicle HAL. 차량 신호를 안드로이드에 넘겨 주는 층. 여기서는 에뮬레이터의 가상 값"],
    ["CarService", "AAOS에서 앱과 VHAL 사이에서 차량 값을 주고받는 시스템 서비스"],
    ["CarPropertyManager", "앱이 차량 값(CarProperty)을 읽고 쓰는 AAOS API"],
    ["CarProperty", "온도, 속도처럼 차량 값 하나를 가리키는 AAOS의 단위"],
    ["E2E", "End-to-End. 화면 조작부터 차량 값까지 실제 경로 전체를 거치는 테스트"],
    ["CI/CD", "변경을 올릴 때마다 자동으로 빌드, 테스트, 배포하는 흐름"],
    ["CI", "Continuous Integration. 변경을 올릴 때마다 자동으로 빌드하고 테스트하는 것. 여기서는 GitHub Actions"],
    ["flaky", "같은 코드인데 실행마다 통과와 실패가 바뀌는 테스트. 여기서는 실패 뒤 재시도에서 통과한 경우"],
    ["smoke", "이 빌드를 받아도 되는지 보는 가장 짧은 확인 (13개, PR마다)"],
    ["sanity", "서비스마다 대표 경로를 하나씩 보는 확인 (25개, main에 합칠 때)"],
    ["regression", "경계값, 조합, 예전 결함 재발까지 보는 전체 회귀 테스트"],
    ["Nightly", "매일 밤 자동으로 도는 전체 테스트"],
    ["Release 게이트", "릴리스 후보를 내보내도 되는지 정하는 자동 판정 (여섯 조건)"],
    ["Test Bench", "테스트 기기와 PC를 묶은 시험 환경. 여기서는 PC 한 대, AAOS 에뮬레이터, 태블릿"],
    ["HIL", "Hardware-in-the-Loop. 실제 제어 장치를 붙여 하는 시험. 이 프로젝트에서는 쓰지 않음"],
    ["CAN", "차량 안의 제어 장치끼리 신호를 주고받는 통신 버스. 여기서는 PC 안의 가상 버스"],
    ["ECU", "Electronic Control Unit. 공조, 배터리, 도어 같은 차량 제어 장치"],
    ["DBC", "CAN 프레임에 어떤 신호가 어디 들어 있는지 정의한 파일"],
    ["DDS", "Data Distribution Service. 차량 소프트웨어끼리 데이터를 주고받는 통신 방식"],
    ["SOME/IP", "차량 이더넷에서 서비스를 주고받는 통신 방식"],
    ["Mock", "실제 대신 쓰는 가짜 구현. 태블릿에서는 앱 안의 가짜 차량 서비스"],
    ["xfail", "실패할 것을 알고 있는 테스트 표시 (pytest). 알려진 결함에 쓴다"],
    ["pytest", "파이썬 테스트 프레임워크"],
    ["Appium", "모바일 앱 화면을 코드로 조작하는 자동화 도구"],
    ["UiAutomator2", "안드로이드 화면 자동화 도구. Appium이 기기 안에서 쓴다"],
    ["UiAutomator", "안드로이드 화면 자동화 도구. Appium이 기기 안에서 쓴다"],
    ["Playwright", "웹 브라우저 자동화 도구"],
    ["BVT", "Build Verification Test. 새 빌드가 기본 동작을 하는지 보는 테스트"],
    ["adb", "Android Debug Bridge. PC에서 안드로이드 기기를 명령으로 다루는 도구"],
    ["ADB", "Android Debug Bridge. PC에서 안드로이드 기기를 명령으로 다루는 도구"],
    ["logcat", "안드로이드 기기의 로그"],
    ["APK", "안드로이드 앱 설치 파일"],
    ["SystemUI", "안드로이드의 상태 표시줄, 홈 버튼 같은 시스템 화면"],
    ["priv-app", "시스템 권한을 받는 앱 설치 위치. 공조 제어 권한에 필요"],
    ["area", "같은 차량 신호의 위치 구분 (운전석, 조수석, 문 하나하나)"],
    ["HVAC", "Heating, Ventilation, Air Conditioning. 공조"],
    ["PR", "Pull Request. 변경을 main에 합치기 전에 올리는 검토 요청"],
    ["sha256", "파일 내용으로 만든 지문(해시). 같은 파일인지 비교할 때 쓴다"],
    ["run id", "한 번의 실행 묶음 이름 (시작 시각)"],
    ["A-SPICE", "Automotive SPICE. 자동차 소프트웨어 개발 과정을 평가하는 모델"],
    ["ISO 26262", "자동차 기능 안전 국제 표준"],
    ["SDV", "Software-Defined Vehicle. 기능을 소프트웨어로 정하고 바꾸는 차량"],
  ];

  function escapeRe(text) {
    return text.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
  }

  // 긴 것부터: CI/CD 를 CI 로, CarPropertyManager 를 CarProperty 로 잘못 감싸지 않게
  var sorted = TERMS.slice().sort(function (a, b) { return b[0].length - a[0].length; });
  var pattern = new RegExp("(?<![A-Za-z0-9_\\-])(" + sorted.map(function (t) { return escapeRe(t[0]); }).join("|") + ")(?![A-Za-z0-9_\\-])", "g");
  var meaning = {};
  TERMS.forEach(function (t) { meaning[t[0]] = t[1]; });

  root.IVI_GLOSSARY = { terms: TERMS, pattern: pattern, meaning: meaning };
  if (typeof document === "undefined") return;

  var SKIP = "a, code, pre, kbd, samp, abbr, button, h1, h2, h3, h4, h5, h6, svg, script, style, textarea, nav, .mermaid, [data-no-glossary]";

  function annotate(container) {
    var used = {};
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var texts = [];
    for (var node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === 1) {
        if (node.tagName === "H2" || node.tagName === "SECTION") texts.push({ reset: true });
        if (node.tagName === "ABBR") texts.push({ seen: node.textContent.trim() });
        continue;
      }
      if (node.parentElement && !node.parentElement.closest(SKIP) && pattern.test(node.nodeValue)) texts.push({ node: node });
      pattern.lastIndex = 0;
    }
    texts.forEach(function (item) {
      if (item.reset) { used = {}; return; }
      if (item.seen) { used[item.seen] = true; return; }
      var text = item.node.nodeValue, out = document.createDocumentFragment(), last = 0, changed = false, match;
      pattern.lastIndex = 0;
      while ((match = pattern.exec(text))) {
        var term = match[1];
        if (used[term]) continue;
        used[term] = true;
        changed = true;
        out.appendChild(document.createTextNode(text.slice(last, match.index)));
        var abbr = document.createElement("abbr");
        abbr.title = meaning[term];
        abbr.textContent = term;
        out.appendChild(abbr);
        last = match.index + term.length;
      }
      if (!changed) return;
      out.appendChild(document.createTextNode(text.slice(last)));
      item.node.parentNode.replaceChild(out, item.node);
    });
  }

  // 마우스가 없는 화면(휴대폰)과 키보드에서도 뜻을 볼 수 있게: 용어를 누르거나 Tab 으로 가면 아래에 풀이 상자가 뜬다.
  // title 은 그대로 둔다 (마우스를 올리면 브라우저가 보여 주고, 스크립트가 없어도 남는다). Esc, 바깥 누르기, 다른 곳으로 Tab 하면 닫힌다
  var TIP_STYLE = ".gloss-tip{position:absolute;z-index:60;max-width:min(320px,calc(100vw - 32px));padding:8px 12px;" +
    "border:1px solid var(--hairline-strong,#34343a);border-radius:var(--r-md,8px);background:var(--surface-3,#18191a);" +
    "color:var(--ink,#f7f8f8);font:13px/1.5 var(--font-text,system-ui,sans-serif);box-shadow:0 8px 24px rgba(0,0,0,.4)}" +
    ".gloss-tip strong{display:block;font-weight:600;margin-bottom:2px}" +
    "abbr[data-gloss]:focus-visible{outline:2px solid var(--primary,#5e6ad2);outline-offset:2px;border-radius:2px}";
  var tip = null, owner = null;

  function hideTip() {
    if (!tip || tip.hidden) return;
    tip.hidden = true;
    if (owner) { owner.removeAttribute("aria-describedby"); owner.setAttribute("aria-expanded", "false"); }
    owner = null;
  }

  function showTip(abbr) {
    if (owner === abbr && !tip.hidden) return;
    tip.innerHTML = "";
    var name = document.createElement("strong");
    name.textContent = abbr.textContent;
    tip.appendChild(name);
    tip.appendChild(document.createTextNode(abbr.getAttribute("data-gloss")));
    tip.hidden = false;
    if (owner) owner.removeAttribute("aria-describedby");
    owner = abbr;
    abbr.setAttribute("aria-describedby", "gloss-tip");
    abbr.setAttribute("aria-expanded", "true");
    var box = abbr.getBoundingClientRect(), width = tip.offsetWidth;
    var left = Math.min(Math.max(window.scrollX + box.left, window.scrollX + 16), window.scrollX + document.documentElement.clientWidth - width - 16);
    tip.style.left = left + "px";
    tip.style.top = (window.scrollY + box.bottom + 6) + "px";
  }

  function enableTips(container) {
    // 링크·버튼 안의 용어는 누르면 이동해야 하므로 풀이 상자를 붙이지 않는다 (title 만)
    var terms = Array.prototype.filter.call(container.querySelectorAll("abbr[title]"), function (a) { return !a.closest("a, button"); });
    if (!terms.length) return;
    var style = document.createElement("style");
    style.textContent = TIP_STYLE;
    document.head.appendChild(style);
    tip = document.createElement("div");
    tip.id = "gloss-tip";
    tip.className = "gloss-tip";
    tip.setAttribute("role", "tooltip");
    tip.hidden = true;
    document.body.appendChild(tip);
    terms.forEach(function (abbr) {
      abbr.setAttribute("data-gloss", abbr.title);
      abbr.tabIndex = 0;
      abbr.setAttribute("role", "button");
      abbr.setAttribute("aria-expanded", "false");
    });
    container.addEventListener("click", function (e) {
      var abbr = e.target.closest && e.target.closest("abbr[data-gloss]");
      // 누르면 열기만 한다. 누를 때 포커스가 먼저 열어 두므로, 여기서 다시 누르기로 닫으면 바로 닫혀 버린다
      if (abbr) showTip(abbr);
    });
    container.addEventListener("focusin", function (e) {
      if (e.target.matches && e.target.matches("abbr[data-gloss]")) showTip(e.target);
    });
    container.addEventListener("focusout", function (e) {
      if (e.target === owner) hideTip();
    });
    container.addEventListener("keydown", function (e) {
      if ((e.key === "Enter" || e.key === " ") && e.target.matches && e.target.matches("abbr[data-gloss]")) {
        e.preventDefault();
        showTip(e.target);
      }
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hideTip(); });
    document.addEventListener("click", function (e) {
      if (!(e.target.closest && e.target.closest("abbr[data-gloss], #gloss-tip"))) hideTip();
    });
    window.addEventListener("resize", hideTip);
  }

  function run() {
    var container = document.querySelector("main");
    if (!container) return;
    annotate(container);
    enableTips(container);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
})(typeof window !== "undefined" ? window : globalThis);
