// docs/*.md 와 README.md 를 사이트 디자인(site/design-tokens.md 토큰)에 맞춘 HTML 로 바꾼다.
// file:// 로 열면 브라우저가 .md 를 읽어 올 수 없어서, 미리 HTML 로 만들어 둔다.
//
//   cd site && npm install && npm run build-docs
//
// 결과: site/docs/*.html (커밋한다. 문서를 고치면 다시 실행)
// 테스트 결과 페이지(test-results.html)는 site/results/results.json 으로 만든다
// (ivi-tests/tools/publish_results.py 가 실행 기록과 끝 화면에서 만든다).
// 소개 페이지(site/index.html)의 숫자 띠와 기기별 결과(<!-- stats:… -->, <!-- devices:… -->),
// 공고 항목별 근거 페이지(site/fit.html)의 목차(<!-- fit:… -->)도 같은 자료로 다시 쓴다.
// 숫자를 손으로 쓰지 않는다: 같은 페이지 안에서 시간이 1초씩 달랐던 일이 있다 (2026-11-18 검토).
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import { GROUPS, REQUIREMENTS } from "./requirements.mjs";

const SITE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SITE, "..");
const OUT = path.join(SITE, "docs");
const RESULTS_JSON = path.join(SITE, "results", "results.json");
const INDEX = path.join(SITE, "index.html");
const FIT = path.join(SITE, "fit.html");
// 사이트(GitHub Pages)에는 site/ 와 docs/images/ 만 올린다. 소스 코드와 원문 .md 는 GitHub 화면으로 잇는다.
const REPO = "https://github.com/bugspeaker/opencabin-ivi";
const IMAGE = /\.(png|jpe?g|webp|gif|svg)$/i;

function githubUrl(target) {
  const full = path.join(ROOT, target);
  const dir = existsSync(full) && statSync(full).isDirectory();
  return `${REPO}/${dir ? "tree" : "blob"}/main/${target.replace(/\/$/, "")}`;
}

// 사이드바 순서. src 는 저장소 루트 기준
const PAGES = [
  { src: "docs/portfolio.md", out: "portfolio.html", nav: "포트폴리오" },
  { src: "docs/test-results.md", out: "test-results.html", nav: "테스트 결과", results: true },
  { src: "docs/flaky-report.md", out: "flaky-report.html", nav: "반복 실행 통계" },
  { src: "docs/decisions.md", out: "decisions.html", nav: "결정 기록" },
  { src: "docs/traceability.md", out: "traceability.html", nav: "요구사항 추적표", wide: true },
  { src: "docs/requirements.md", out: "requirements.html", nav: "요구사항" },
  { src: "README.md", out: "readme.html", nav: "README" },
  { src: "docs/run.md", out: "run.html", nav: "실행 방법" },
  { src: "docs/phase1-spike.md", out: "phase1-spike.html", nav: "1. 기술 검증" },
  { src: "docs/phase2-app.md", out: "phase2-app.html", nav: "2. 앱" },
  { src: "docs/phase3-framework.md", out: "phase3-framework.html", nav: "3. 테스트 프레임워크" },
  { src: "docs/phase4-operations.md", out: "phase4-operations.html", nav: "4. 운영 · CI" },
  { src: "docs/phase5-design.md", out: "phase5-design.html", nav: "5. 재점검과 디자인" },
  { src: "docs/phase6-features.md", out: "phase6-features.html", nav: "6. 기능 확장" },
  { src: "docs/phase7-layout.md", out: "phase7-layout.html", nav: "7. 3영역 화면 개편" },
  { src: "docs/phase8-signals.md", out: "phase8-signals.html", nav: "8. 차량 신호 확장" },
  { src: "docs/phase9-bench.md", out: "phase9-bench.html", nav: "9. Test Bench 확장" },
];
const OUT_BY_SRC = new Map(PAGES.map((p) => [p.src, p.out]));

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const stripTags = (s) => s.replace(/<[^>]*>/g, "");
const unesc = (s) => s.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'");

const RESULTS = existsSync(RESULTS_JSON) ? JSON.parse(readFileSync(RESULTS_JSON, "utf8")) : null;
// 문서 본문의 `test_이름` · `test_파일.py` 를 결과 페이지로 잇는다
const TEST_LINKS = new Map();
for (const f of RESULTS?.files ?? []) {
  TEST_LINKS.set(f.file, `test-results.html#file-${f.file.replace(/\.py$/, "")}`);
  TEST_LINKS.set(`tests/${f.file}`, `test-results.html#file-${f.file.replace(/\.py$/, "")}`);
  for (const t of f.tests) TEST_LINKS.set(t.name, `test-results.html#${t.name}`);
}

// GitHub 과 같은 규칙으로 제목 id 를 만든다 (문서 안 #링크가 그대로 동작하도록)
function slugger() {
  const seen = new Map();
  return (text) => {
    let s = unesc(stripTags(text)).toLowerCase().trim()
      .replace(/[^\p{L}\p{N}\s_-]/gu, "")
      .replace(/ /g, "-");
    const n = seen.get(s) ?? 0;
    seen.set(s, n + 1);
    return n ? `${s}-${n}` : s;
  };
}

// 문서 안의 상대 경로를 site/docs/ 기준으로 바꾼다. .md 는 만든 HTML 로
function rewrite(href, srcDir) {
  if (!href || /^(?:[a-z]+:|#|\/\/)/i.test(href)) return href;
  const [p, hash = ""] = href.split("#");
  const target = path.posix.normalize(path.posix.join(srcDir, p));
  const html = OUT_BY_SRC.get(target);
  if (html) return html + (hash ? `#${hash}` : "");
  if (!target.startsWith("site/") && !IMAGE.test(target)) return githubUrl(target) + (hash ? `#${hash}` : "");
  return path.posix.relative("site/docs", target) + (hash ? `#${hash}` : "");
}

/** 링크 밖에 있는 <code>test_…</code> 를 결과 페이지 링크로 감싼다 (링크 안의 코드는 그대로). */
function linkTests(body) {
  if (!TEST_LINKS.size) return body;
  return body.split(/(<a\b[\s\S]*?<\/a>)/).map((part) => part.startsWith("<a") ? part
    : part.replace(/<code>((?:tests\/)?test_[\w.]+?)(?:\[[^\]<]*\])?<\/code>/g, (m, name) => {
      const href = TEST_LINKS.get(name);
      return href ? `<a class="test-link" href="${href}" title="테스트 결과와 화면 보기">${m}</a>` : m;
    })).join("");
}

function shell(page, { title, body, toc = [], head = "", scripts = "", mainClass = "doc" }) {
  const nav = PAGES.filter((p) => !p.results || RESULTS).map((p) =>
    `<a href="${p.out}"${p.out === page.out ? ' aria-current="page"' : ""}>${esc(p.nav)}</a>`).join("\n        ");
  const tocHtml = toc.filter((t) => t.level === 2).length > 1
    ? `<nav class="toc" aria-label="이 문서의 목차"><p class="eyebrow">이 문서</p>${toc.map((t) =>
        `<a class="l${t.level}" href="#${esc(t.id)}">${esc(t.text)}</a>`).join("")}</nav>`
    : "";
  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · OpenCabin IVI</title>
<meta name="theme-color" content="#ffffff">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="doc.css">${head}
</head>
<body>
<a class="skip" href="#content">본문으로 건너뛰기</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark" aria-hidden="true"></span>OpenCabin IVI</a>
  <span class="crumb">문서 · ${esc(page.nav)}</span>
  <a class="home" href="../index.html">포트폴리오</a>
  <a class="src" href="${esc(githubUrl(page.src))}">원문 .md</a>
</header>
<div class="layout${/results|wide-doc/.test(mainClass) ? " wide" : ""}">
  <aside class="side">
    <nav aria-label="문서 목록">
        ${nav}
    </nav>
  </aside>
  <main id="content" class="${mainClass}">
${body}
  </main>
  ${tocHtml}
</div>
${scripts}
<script src="../glossary.js" defer></script>
</body>
</html>
`;
}

function render(page) {
  const md = readFileSync(path.join(ROOT, page.src), "utf8");
  const srcDir = path.posix.dirname(page.src);
  const slug = slugger();
  const toc = [];
  let title = page.nav;

  const renderer = new marked.Renderer();
  renderer.heading = (text, level) => {
    const id = slug(text);
    if (level === 1) title = unesc(stripTags(text));
    if (level === 2 || level === 3) toc.push({ id, level, text: stripTags(text) });
    return `<h${level} id="${esc(id)}"><a class="anchor" href="#${esc(id)}" aria-hidden="true">#</a>${text}</h${level}>\n`;
  };
  renderer.code = (code, lang) => {
    if ((lang || "").trim() === "mermaid") return `<pre class="mermaid">${esc(code)}</pre>\n`;
    return `<pre class="code"><code${lang ? ` data-lang="${esc(lang)}"` : ""}>${esc(code)}</code></pre>\n`;
  };
  renderer.link = (href, t, text) =>
    `<a href="${esc(rewrite(href, srcDir))}"${t ? ` title="${esc(t)}"` : ""}${/^https?:/.test(href) ? ' target="_blank" rel="noopener"' : ""}>${text}</a>`;
  renderer.image = (href, t, text) =>
    `<img data-md src="${esc(rewrite(href, srcDir))}" alt="${esc(text)}" loading="lazy">`;
  // 표 첫 칸이 짧은 이름(12자 이하)이면 줄을 바꾸지 않는다. 설명이 긴 표에서 '앞뒤 / 김서림 / 제거'처럼 접히지 않게 (2026-11-22 표 점검)
  const noWrapFirst = (rows) => rows.replace(/<tr>\n<td>([\s\S]*?)<\/td>/g, (m, c) => (unesc(stripTags(c)).length <= 12 ? `<tr>\n<td class="nw">${c}</td>` : m));
  renderer.table = (header, body) => `<div class="table"><table><thead>${header}</thead><tbody>${noWrapFirst(body)}</tbody></table></div>\n`;

  let body = marked.parse(md, { renderer, gfm: true });
  // GitHub 알림 문법(> [!TIP] 등)을 GitHub 처럼 색 있는 상자로. marked 는 '[!TIP]'을 글자 그대로 남긴다
  const CALLOUT = { NOTE: "참고", TIP: "안내", IMPORTANT: "중요", WARNING: "주의", CAUTION: "주의" };
  body = body.replace(/<blockquote>\n<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n?/g,
    (m, kind) => `<blockquote class="callout callout-${kind.toLowerCase()}"><p class="callout-title">${CALLOUT[kind]}</p>\n<p>`);
  // 원문 HTML(<details> 안의 이미지 등)에 남은 상대 경로도 바꾼다
  // (renderer.image 가 만든 것은 data-md 표시가 있어 건너뛴다. 두 번 바꾸면 경로가 깨진다)
  body = body.replace(/<img(?![^>]*\sdata-md)([^>]*\ssrc=")([^"]+)(")/g, (m, a, src, b) => `<img${a}${rewrite(src, srcDir)}${b}`);
  // ✅ ❌ ⚠️ 를 상태 배지처럼
  body = body.replace(/✅/g, '<span class="ok">✅</span>').replace(/❌/g, '<span class="no">❌</span>');
  body = linkTests(body);
  // 표 안의 긴 코드 이름(테스트 함수, 경로)은 '_', '.', '/' 뒤에서 줄을 바꿀 수 있게 한다.
  // 글자 중간에서 자르지는 않되, 이름 하나 때문에 표가 본문 밖으로 넘치거나 옆 칸이 눌리지 않게 (2026-11-22 표 점검)
  body = body.replace(/<code>([^<]{16,})<\/code>/g, (m, t) => `<code>${t.replace(/([_./])(?=[^\s<])/g, "$1<wbr>")}</code>`);

  const scripts = body.includes('class="mermaid"') ? `<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: true, theme: "base", themeVariables: {
  background: "#ffffff", primaryColor: "#ecf2ff", primaryTextColor: "#191f28",
  primaryBorderColor: "#1b5be6", lineColor: "#6b7684", secondaryColor: "#f4f6f9", tertiaryColor: "#f4f6f9",
  clusterBkg: "#f9fafb", clusterBorder: "#d1d6db", edgeLabelBackground: "#ffffff",
  fontFamily: "Pretendard Variable, Pretendard, system-ui, sans-serif", fontSize: "14px" } });
</script>` : "";
  // 넓은 표가 있는 문서(추적표)는 오른쪽 목차 없이 본문을 넓게 쓴다
  return shell(page, { title, body, toc: page.wide ? [] : toc, scripts, mainClass: page.wide ? "doc wide-doc" : "doc" });
}

// ---------------- 테스트 결과 페이지 ----------------

const BAD = new Set(["failed", "error", "flaky", "xpassed"]);
const MEASURE_LABEL = { camera_seconds: "카메라가 뜨기까지", boot_seconds: "부팅" };
const MARKER_LABEL = { smoke: "smoke", sanity: "sanity", regression: "regression", spike: "spike", aaos: "AAOS 전용", tablet: "태블릿 전용" };
// 필터 칩은 게이트 순서대로 (smoke → sanity → regression), 그 뒤에 기술 검증과 기기 조건
const MARKER_ORDER = ["smoke", "sanity", "regression", "spike", "aaos", "tablet"];
// 긴 테스트 이름이 좁은 화면에서 글자 중간이 아니라 단어('_') 뒤에서 줄바꿈되게
const breakable = (name) => esc(name).replace(/_/g, "_<wbr>");
const fmtTime = (s) => `${Math.floor(s / 60)}분 ${Math.floor(s % 60)}초`;  // pytest 와 같이 버림

/** requirements.mjs 의 항목마다 근거 테스트와 숫자를 붙인다. */
function reqIndex(data) {
  const all = data.files.flatMap((f) => f.tests.map((t) => ({ ...t, file: f.file })));
  const results = all.flatMap((t) => t.cases.flatMap((c) => Object.values(c.results)));
  const casesOf = (tests) => tests.reduce((n, t) => n + t.cases.length, 0);
  const stats = {
    total: casesOf(all),
    smoke: casesOf(all.filter((t) => t.markers.includes("smoke"))),
    sanity: casesOf(all.filter((t) => t.markers.includes("sanity"))),
    regression: casesOf(all.filter((t) => t.markers.includes("regression"))),
    runs: results.filter((r) => r.outcome !== "skipped").length,
    bad: results.filter((r) => BAD.has(r.outcome)).length,
    retries: results.reduce((n, r) => n + (r.reruns || 0), 0),
    stability: data.stability ?? null,  // publish_results.py --repeat-runs 로 넣는 반복 실행 통계
  };
  const byTest = new Map(); // 테스트 이름 → 이 테스트를 근거로 쓰는 항목 id
  const text = (v) => (typeof v === "function" ? v(stats) : v);
  const reqs = REQUIREMENTS.map((r, i) => {
    let tests = [];
    if (r.select) {
      const { files = [], tests: names = [], doc } = r.select;
      for (const n of names) if (!all.some((t) => t.name === n)) console.warn(`주의: 요구 역량 ${r.id} 의 테스트 ${n} 가 결과에 없다`);
      tests = all.filter((t) => files.includes(t.file) || names.includes(t.name) || (doc && doc.test(t.doc)));
      for (const n of r.lead ?? []) if (!tests.some((t) => t.name === n)) console.warn(`주의: 요구 역량 ${r.id} 의 대표 근거 ${n} 가 그 항목의 테스트에 없다`);
      for (const t of tests) byTest.set(t.name, [...(byTest.get(t.name) ?? []), r.id]);
    }
    const count = r.select ? casesOf(tests) : r.chip ? stats[r.chip] : r.all ? stats.total : null;
    return { ...r, num: String(i + 1).padStart(2, "0"), done: text(r.done), note: text(r.note), count };
  });
  return { stats, reqs, byTest };
}

function countsLine(counts) {
  const order = ["passed", "flaky", "failed", "error", "skipped", "xfailed", "xpassed", "quarantined"];
  const label = { passed: "통과", flaky: "재시도 후 통과", failed: "실패", error: "오류", skipped: "건너뜀", xfailed: "알려진 결함", xpassed: "알려진 결함 통과", quarantined: "격리" };
  return order.filter((k) => counts[k]).map((k) =>
    `<span class="pill p-${k}">${label[k]} ${counts[k]}</span>`).join("");
}

// 결과 페이지 기기 카드의 설명. 칸(kind)으로 먼저 찾고, 없으면 기기 종류(type)로
const DEVICE_NOTE = {
  aaos: "CarService와 에뮬레이터 VHAL을 거칩니다. 화면→신호, 신호→화면을 모두 VHAL 값으로 판정합니다.",
  mock: "화면 동작과 실기기 문제(터치 지연, 백그라운드 강제 종료)를 보는 기기입니다. 차량 값은 앱 안의 Mock이라 VHAL 경로는 AAOS에서만 확인합니다.",
  fold: "펼친 화면을 가로로 눕혀 돌렸습니다. 다른 두 기기보다 좁고 낮은 화면(앱 영역 약 780×513dp)이라 배치가 넘치는지 봅니다. 배치를 고치기 전에는 5개가 실패했습니다(<a href=\"https://github.com/bugspeaker/opencabin-ivi/blob/main/docs/evidence/2026-11-23-fold/README.md\">폴드 기록</a>). 차량 값은 앱 안의 Mock입니다.",
};
const KO_NUM = { 1: "한", 2: "두", 3: "세", 4: "네" };
const NAME = { aaos: "AAOS 에뮬레이터", mock: "태블릿", fold: "갤럭시 폴드" };
// 받침이 있으면 앞의 것(은, 과), 없으면 뒤의 것(는, 와)
const josa = (w, withFinal, without) => { const c = w.charCodeAt(w.length - 1); return c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 ? withFinal : without; };
const names = (devices) => { const n = devices.map((d) => NAME[d.kind] ?? d.label); return n.slice(0, -1).map((w) => w + josa(w, "과 ", "와 ")).join("") + n.at(-1); };
// 반복 실행의 마지막 회차인 기기 (첫 화면의 '두 기기 × 3회' 수치는 이 기기들로만 낸다)
const repeatDevices = (data) => data.stability ? data.devices.filter((d) => data.stability.run_ids.includes(d.run_id)) : data.devices;
const appOf = (devices) => `앱 ${[...new Set(devices.map((d) => d.app?.version ?? "버전 미기록"))].join(", ")}`;

/** 기기마다 어느 실행의 결과인지. publish_results.py 의 run_note 와 같은 문장 */
function runNote(data) {
  const st = data.stability;
  const rep = st ? repeatDevices(data) : [];
  const parts = [];
  if (rep.length) {
    const n = names(rep);
    parts.push(`${n}${josa(n, "은", "는")} ${st.rounds}회 반복한 실행의 마지막 회차(${esc(appOf(rep))})이고, 반복 전체의 통계는 <a href="flaky-report.html">반복 실행 통계</a>에 있습니다.`);
  }
  for (const d of data.devices.filter((x) => !rep.includes(x))) {
    const n = names([d]);
    parts.push(`${n}${josa(n, "은", "는")} ${d.time.slice(0, 10)}에 따로 돌린 실행(${esc(appOf([d]))})입니다.`);
  }
  return parts.join(" ");
}

function renderResults(page) {
  const data = RESULTS;
  const kinds = data.devices.map((d) => d.kind);
  const { reqs, byTest } = reqIndex(data);
  const groupLabel = Object.fromEntries(GROUPS.map((g) => [g.id, g.label]));
  // 첫 화면 목차에서 ?req=<id> 로 들어올 때 쓰는 정보 (근거가 테스트인 항목만)
  const reqMeta = Object.fromEntries(reqs.filter((r) => !r.gap && (r.select || r.chip || r.onlyBad || r.all)).map((r) => [r.id, {
    eyebrow: `요구 역량 ${r.num} · ${groupLabel[r.group]}`, title: r.title, note: r.note ? `${esc(r.done)} ${r.note}` : r.done,
    count: r.count, filter: Boolean(r.select), chip: r.chip || "", onlyBad: Boolean(r.onlyBad), lead: r.lead ?? [],
  }]));
  const devices = data.devices.map((d) => `
      <section class="device-card">
        <p class="eyebrow">${esc(d.label)}</p>
        <p class="device-model">${esc(d.model)}</p>
        <div class="pills">${countsLine(d.counts)}</div>
        <p class="device-note">${DEVICE_NOTE[d.kind] ?? DEVICE_NOTE[d.type] ?? ""}</p>
        <dl>
          <div><dt>실행</dt><dd>${esc(d.time.replace("T", " ").slice(0, 16))}</dd></div>
          <div><dt>앱</dt><dd>${esc(d.app?.version ?? "기록 없음")}</dd></div>
          <div><dt>시간</dt><dd>${fmtTime(d.duration)}</dd></div>
          <div><dt>게이트</dt><dd class="${d.gate === "pass" ? "gate-pass" : "gate-fail"}">${d.gate === "pass" ? "통과" : "실패"}</dd></div>
        </dl>
      </section>`).join("");

  const toc = [];
  let total = 0;
  const files = data.files.map((f) => {
    const id = `file-${f.file.replace(/\.py$/, "")}`;
    toc.push({ id, level: 2, text: f.file });
    const tests = f.tests.map((t) => {
      total += t.cases.length;
      const bad = t.cases.some((c) => Object.values(c.results).some((r) => BAD.has(r.outcome)));
      const cases = t.cases.map((c) => {
        const cells = kinds.map((k) => {
          const r = c.results[k];
          const dev = data.devices.find((d) => d.kind === k);
          if (!r) return `<div class="shot-cell is-empty"><span class="cell-device">${esc(dev.label)}</span><p class="cell-note">이 기기에서는 돌리지 않았습니다</p></div>`;
          const caption = `${t.name}${c.param ? ` [${c.param}]` : ""} · ${dev.label} · ${r.label} · ${r.duration}초`;
          const media = r.image
            ? `<button type="button" class="shot shot-${k}" data-full="../results/${esc(r.image)}" data-caption="${esc(caption)}" aria-label="${esc(dev.label)} 화면 크게 보기">
                <img src="../results/${esc(r.image)}" alt="${esc(dev.label)}에서 ${esc(t.name)} 판정 직후 화면" loading="lazy" decoding="async">
              </button>`
            : `<div class="shot shot-${k} no-shot"><p>${esc(r.message || "화면 없음")}</p></div>`;
          const measures = Object.entries(r.measures || {}).map(([k, v]) =>
            `<p class="cell-measure">${esc(MEASURE_LABEL[k] || k)}: ${esc(v)}초</p>`).join("");
          // 테스트 중 마지막으로 읽은 차량 값, 최대 3개 (AAOS: CarService 로 읽은 VHAL 값)
          const signals = (r.signals || []).length
            ? `<p class="cell-signals" title="테스트 중 마지막으로 읽은 차량 값, 최대 3개 (CarService로 읽은 VHAL 값)">${r.signals.map((s) => `<code>${esc(s)}</code>`).join("")}</p>` : "";
          return `<div class="shot-cell">
              ${media}
              <div class="cell-meta"><span class="cell-device">${esc(dev.label)}</span><span class="pill p-${r.outcome}">${esc(r.label)}</span><span class="cell-time">${r.duration}초</span></div>
              ${measures}
              ${signals}
            </div>`;
        }).join("");
        return `<div class="case">${c.param ? `<p class="case-param"><code>[${esc(c.param)}]</code></p>` : ""}<div class="case-shots">${cells}</div></div>`;
      }).join("");
      const marks = t.markers.map((m) => `<span class="mark-chip">${esc(MARKER_LABEL[m] || m)}</span>`).join("");
      return `<article class="rtest" id="${esc(t.name)}" data-markers="${esc(t.markers.join(" "))}" data-reqs="${esc((byTest.get(t.name) ?? []).join(" "))}" data-bad="${bad ? 1 : 0}">
          <div class="rtest-text">
            <header class="rtest-head"><a class="rtest-name" href="#${esc(t.name)}"><code>${breakable(t.name)}</code></a>${marks}</header>
            ${t.doc ? `<p class="rtest-doc">${esc(t.doc)}</p>` : ""}
          </div>
          <div class="rtest-cases">${cases}</div>
        </article>`;
    }).join("\n");
    return `<section class="rfile" id="${id}">
        <h2><a class="anchor" href="#${id}" aria-hidden="true">#</a>${esc(f.file)} <span class="rfile-count">${f.tests.reduce((n, t) => n + t.cases.length, 0)}</span></h2>
        <p class="rfile-title">${esc(f.title)}</p>
        ${tests}
      </section>`;
  }).join("\n");

  const used = new Set(data.files.flatMap((f) => f.tests.flatMap((t) => t.markers)));
  const markers = [...MARKER_ORDER.filter((m) => used.has(m)), ...[...used].filter((m) => !MARKER_ORDER.includes(m))];
  const body = `
    <h1 id="테스트-결과">테스트 결과</h1>
    <p class="lead">E2E ${total}개를 ${KO_NUM[data.devices.length] ?? data.devices.length} 기기에서 돌린 결과입니다. ${runNote(data)} 판정 직후 화면을 함께 남겼고, 화면을 누르면 크게 볼 수 있습니다. AAOS 칸 아래의 <code>PROPERTY[area]=값</code>은 테스트 중에 마지막으로 읽은 차량 값(최대 3개)입니다. 이 결과가 어느 코드로 돈 것인지와 그 뒤 바꾼 코드의 확인 방법은 <a href="readme.html#결과-자료와-검증-시점">결과 자료와 검증 시점</a>에 있습니다.</p>
    <div class="device-cards">${devices}</div>
    <section class="req-banner" id="req-banner" aria-live="polite" hidden>
      <div class="req-copy">
        <p class="req-eyebrow" id="req-eyebrow"></p>
        <p class="req-title" id="req-title"></p>
        <p class="req-note" id="req-note"></p>
      </div>
      <div class="req-actions">
        <a class="req-btn" href="../fit.html">공고 항목 목록</a>
        <button type="button" class="req-btn" id="req-clear">전체 테스트 보기</button>
      </div>
    </section>
    <div class="filters" role="group" aria-label="테스트 거르기">
      <button type="button" class="chip" aria-pressed="true" data-filter="">전체</button>
      ${markers.map((m) => `<button type="button" class="chip" aria-pressed="false" data-filter="${esc(m)}">${esc(MARKER_LABEL[m] || m)}</button>`).join("")}
      <label class="only-bad"><input type="checkbox" id="only-bad"> 실패나 재시도만</label>
      <span class="filter-count" id="filter-count" aria-live="polite"></span>
      <select class="jump" id="jump" aria-label="파일로 이동"><option value="">파일로 이동</option>${toc.map((t) => `<option value="${esc(t.id)}">${esc(t.text)}</option>`).join("")}</select>
    </div>
    <p class="empty-note" id="empty-note" hidden>조건에 맞는 테스트가 없습니다.</p>
    <section class="rfile rlead" id="req-lead" hidden>
      <h2>먼저 볼 근거 <span class="rfile-count"></span></h2>
      <p class="rfile-title">이 항목을 가장 잘 보여 주는 테스트입니다. 나머지 근거는 아래 파일별 목록에 있습니다.</p>
      <div id="req-lead-list"></div>
    </section>
    ${files}
    <p class="generated">결과 기록 ${esc(data.generated)} · <code>ivi-tests/tools/publish_results.py</code></p>
    <dialog id="viewer" aria-label="화면 크게 보기">
      <form method="dialog" class="viewer-bar"><p id="viewer-caption"></p><button class="viewer-close" aria-label="닫기">닫기</button></form>
      <img id="viewer-img" alt="">
    </dialog>`;

  const scripts = `<script>
(() => {
  const viewer = document.getElementById("viewer");
  const img = document.getElementById("viewer-img");
  const cap = document.getElementById("viewer-caption");
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".shot[data-full]");
    if (btn) {
      img.src = btn.dataset.full; img.alt = btn.dataset.caption; cap.textContent = btn.dataset.caption;
      viewer.showModal();
    } else if (e.target === viewer) viewer.close();
  });
  const chips = [...document.querySelectorAll(".chip[data-filter]")];
  const onlyBad = document.getElementById("only-bad");
  const count = document.getElementById("filter-count");
  const empty = document.getElementById("empty-note");
  const banner = document.getElementById("req-banner");
  const REQS = ${JSON.stringify(reqMeta)};
  let filter = "";
  let req = "";
  // 개수는 케이스 단위로 센다 (parametrize 포함, 첫 화면의 'E2E 113개'와 같은 기준)
  function apply() {
    let shown = 0;
    document.querySelectorAll(".rfile").forEach((file) => {
      let inFile = 0;
      file.querySelectorAll(".rtest").forEach((t) => {
        const ok = (!filter || t.dataset.markers.split(" ").includes(filter))
          && (!onlyBad.checked || t.dataset.bad === "1")
          && (!req || t.dataset.reqs.split(" ").includes(req));
        t.hidden = !ok; if (ok) inFile += t.querySelectorAll(".case").length;
      });
      file.hidden = inFile === 0;
      file.querySelector(".rfile-count").textContent = inFile;
      shown += inFile;
    });
    count.textContent = shown + "개 테스트";
    empty.textContent = onlyBad.checked ? "실패하거나 재시도한 테스트가 없습니다." : "조건에 맞는 테스트가 없습니다.";
    empty.hidden = shown > 0;
  }
  function pick(value) {
    filter = value;
    chips.forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.filter === value)));
  }
  chips.forEach((c) => c.addEventListener("click", () => { pick(c.dataset.filter); apply(); }));
  onlyBad.addEventListener("change", apply);
  document.getElementById("jump").addEventListener("change", (e) => {
    if (e.target.value) document.getElementById(e.target.value).scrollIntoView({ behavior: "smooth" });
    e.target.value = "";
  });
  // 항목마다 정한 대표 근거(requirements.mjs 의 lead)를 파일 목록 위로 옮긴다. 파일 이름순이면 대표 사례가 뒤로 밀린다
  const leadList = document.getElementById("req-lead-list");
  const moved = [];
  function placeLeads(names) {
    moved.splice(0).forEach(([el, mark]) => mark.replaceWith(el));
    for (const name of names) {
      const el = document.getElementById(name);
      if (!el || !el.classList.contains("rtest")) continue;
      const mark = document.createComment(name);
      el.replaceWith(mark); leadList.appendChild(el); moved.push([el, mark]);
    }
  }
  // 첫 화면 목차에서 ?req=<id> 로 들어오면 그 항목의 근거 테스트만 보여 준다
  const meta = REQS[new URLSearchParams(location.search).get("req")];
  if (meta) {
    const id = new URLSearchParams(location.search).get("req");
    document.getElementById("req-eyebrow").textContent = meta.eyebrow;
    document.getElementById("req-title").textContent = meta.title;
    document.getElementById("req-note").innerHTML = meta.note;
    if (meta.filter) req = id;
    placeLeads(meta.lead);
    if (meta.chip) pick(meta.chip);
    onlyBad.checked = meta.onlyBad;
    banner.hidden = false;
  }
  document.getElementById("req-clear").addEventListener("click", () => {
    req = ""; pick(""); onlyBad.checked = false; banner.hidden = true; placeLeads([]);
    history.replaceState(null, "", location.pathname + location.hash);
    apply();
  });
  apply();
  if (meta && !location.hash) requestAnimationFrame(() => banner.scrollIntoView({ block: "start" }));
  // 다른 문서에서 #test_이름 으로 들어오면 그 테스트를 잠깐 강조한다
  const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target && target.classList.contains("rtest")) target.classList.add("is-target");
})();
</script>`;
  return shell(page, { title: "테스트 결과", body, scripts, mainClass: "doc results" });
}

// ---------------- 소개 페이지: 요구 역량 목차 · 결과 수치 ----------------

const ARROW = `<svg class="fit-arrow" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M6 3.5 10.5 8 6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

function renderFit({ reqs }) {
  // '완료' 표시와 점수(13 / 16)는 두지 않는다: 공고 항목에 완료 기준이 없어 "무엇을 기준으로 완료인가"만 묻게 된다 (2026-11-18 검토).
  // 오른쪽에는 근거의 종류(테스트 몇 개, 기록)만, 모의 환경이나 개념 적용인 항목은 그 사실만 표시한다
  const row = (r) => {
    if (r.gap) {
      return `<li class="fit-item is-gap"><div class="fit-row">
              <span class="fit-num">${r.num}</span>
              <span class="fit-body"><span class="fit-title">${esc(r.title)}</span></span>
              <span class="fit-side"><span class="fit-state">${esc(r.gap)}</span></span>
            </div></li>`;
    }
    const href = r.link ? r.link.href : `docs/test-results.html?req=${r.id}`;
    const dest = r.link ? r.link.label : r.onlyBad ? `재시도 ${r.count ?? 0}` : `테스트 ${r.count}개`;
    return `<li class="fit-item"><a class="fit-row" href="${esc(href)}">
              <span class="fit-num">${r.num}</span>
              <span class="fit-body"><span class="fit-title">${esc(r.title)}</span><span class="fit-done">${esc(r.done)}</span></span>
              <span class="fit-side">${r.partial ? `<span class="fit-state is-partial">${esc(r.partial)}</span>` : ""}<span class="fit-dest">${esc(dest)}${ARROW}</span></span>
            </a></li>`;
  };
  const group = (g) => {
    const items = reqs.filter((r) => r.group === g.id);
    return `<div class="fit-group">
          <h2 class="fit-group-title">${esc(g.label)} <span>${items.length}개</span></h2>
          <ol class="fit-list">
            ${items.map(row).join("\n            ")}
          </ol>
        </div>`;
  };
  const [duty, ...rest] = GROUPS;
  // 제목과 설명은 fit.html 에 직접 쓴다. 여기서는 목록만 만든다
  return `<section id="fit" class="fit" aria-label="공고 항목">
    <div class="wrap fit-cols">
      <div class="fit-col">
        ${group(duty)}
      </div>
      <div class="fit-col">
        ${rest.map(group).join("\n        ")}
      </div>
    </div>
  </section>`;
}

// 반복 실행한 날짜 (run id 앞 YYYYMMDD): "11-18"
const runDate = (st) => [...new Set(st.run_ids.map((id) => `${id.slice(4, 6)}-${id.slice(6, 8)}`))].join(", ");

// 테스트에서 나온 문제 수: docs/portfolio.md 3장의 표와 GitHub 이슈 #19~#29, 갤럭시 폴드 #42~#44 (결과 자료에는 없는 숫자라 여기 적는다)
const DEFECTS_RECORDED = 14;

// 두 기기를 같은 run id 로 동시에 시작했으면 병렬 실행이다. 끝까지 걸린 시간 = 가장 늦게 끝난 기기
function parallelTimes(data) {
  const devices = repeatDevices(data);
  const sameRun = new Set(devices.map((d) => d.run_id)).size === 1 && devices.length > 1;
  const start = Math.min(...devices.map((d) => Date.parse(d.time)));
  const wall = Math.max(...devices.map((d) => Date.parse(d.time) / 1000 + d.duration)) - start / 1000;
  const serial = devices.reduce((n, d) => n + d.duration, 0);
  return { sameRun, wall, serial };
}
// 첫 화면에는 분 단위로만 적는다. 실행기가 잰 벽시계 시간(10분 51초)과 pytest 시간 합(10분 49초)이 초 단위로 달라서다
const aboutMin = (s) => `약 ${Math.round(s / 60)}`;

function renderStats({ stats }, data) {
  const item = (label, num, unit, note, href) => `<a class="stat" href="${href}">
          <p class="stat-label">${label}</p>
          <p class="stat-num">${num}${unit ? `<small>${unit}</small>` : ""}</p>
          <p class="stat-note">${note}</p>
        </a>`;
  const items = [item("E2E 테스트", stats.total, "개", "두 기기에서 같은 테스트 코드", "docs/test-results.html")];
  const st = stats.stability;
  // 조건(언제, 몇 번)을 숫자 옆에: '실패 0'만 크게 쓰면 조건 없는 주장처럼 읽힌다 (2026-11-19 검토)
  items.push(st
    ? item(`반복 실행 ${st.executions.toLocaleString("en-US")}건`, `실패 ${st.failed}`, "",
        `두 기기 × ${st.rounds}회 (${runDate(st)})<br>재시도로 통과한 것도 ${st.flaky}건`, "docs/flaky-report.html")
    : item("실패와 재시도", stats.bad, "건", `두 기기에서 테스트 ${stats.runs}건, 재시도 ${stats.retries}번`, "docs/test-results.html"));
  const { sameRun, wall, serial } = parallelTimes(data);
  if (sameRun) items.push(item("두 기기 병렬 실행", aboutMin(wall), "분", `차례로 돌리면 ${aboutMin(serial)}분`, "#results"));
  items.push(item("테스트에서 나온 문제", DEFECTS_RECORDED, "건", "원인과 조치를 GitHub 이슈로 기록", "#defects"));
  return `<section class="stats-band" aria-label="주요 수치" data-no-glossary>
      <div class="wrap stats">
        ${items.join("\n        ")}
      </div>
    </section>`;
}

// 기기별 결과를 가로 막대(통과, 건너뜀, 알려진 결함 …)로
function renderDevices(data) {
  const KO = { passed: "통과", skipped: "건너뜀", xfailed: "알려진 결함", flaky: "재시도 후 통과", failed: "실패", error: "오류", xpassed: "알려진 결함 통과", quarantined: "격리" };
  const ORDER = ["passed", "flaky", "xfailed", "xpassed", "quarantined", "failed", "error", "skipped"];
  // 태블릿 숫자가 VHAL 경로까지 증명하는 것처럼 읽히지 않게, 차량 값의 출처를 이름 바로 아래에 둔다
  const ABOUT = {
    aaos: { title: "AAOS 에뮬레이터", text: "CarService와 가상 VHAL을 거칩니다" },
    mock: { title: "Android 태블릿", text: "앱 안의 Mock 차량을 씁니다. AAOS 전용 테스트는 건너뜁니다" },
  };
  // 첫 화면의 기기별 결과는 '두 기기 × 3회' 반복의 마지막 회차만. 따로 돌린 기기(폴드)는 결과 페이지와 폴드 사례에서 보여 준다
  const rows = repeatDevices(data).map((d) => {
    const a = ABOUT[d.kind] ?? { title: d.label, text: "" };
    const parts = ORDER.filter((k) => d.counts[k]).map((k) => [k, d.counts[k]]);
    const said = parts.map(([k, v]) => `${KO[k]} ${v}`).join(", ");
    return `<div class="card run">
          <div class="run-name"><b>${esc(a.title)}</b><span>${esc(a.text)}</span></div>
          <div>
            <div class="stack" role="img" aria-label="${esc(said)}">${parts.map(([k, v]) => `<span class="s-${k}" style="--n: ${v}"></span>`).join("")}</div>
            <ul class="stack-legend">${parts.map(([k, v]) => `<li><i class="s-${k}"></i>${KO[k]} ${v}</li>`).join("")}</ul>
          </div>
          <p class="run-time">${fmtTime(d.duration)}<span>${data.stability ? `${data.stability.rounds}회차` : esc(d.time.slice(0, 10))}</span></p>
        </div>`;
  });
  return `<div class="runs">
        ${rows.join("\n        ")}
      </div>`;
}

// <!-- 이름:start --> ~ <!-- 이름:end --> 사이를 새로 만든 것으로 바꾼다
function fillBlocks(file, blocks) {
  let html = readFileSync(file, "utf8");
  for (const [name, block] of blocks) {
    const re = new RegExp(`(<!-- ${name}:start[^>]*-->)[\\s\\S]*?(\\s*<!-- ${name}:end -->)`);
    if (!re.test(html)) { console.warn(`건너뜀: ${path.basename(file)} 에 <!-- ${name}:start --> 표시가 없다`); continue; }
    html = html.replace(re, (m, a, b) => `${a}\n  ${block}${b}`);
  }
  writeFileSync(file, html, "utf8");
}

function writeIndex() {
  const idx = reqIndex(RESULTS);
  fillBlocks(INDEX, [["stats", renderStats(idx, RESULTS)], ["devices", renderDevices(RESULTS)]]);
  fillBlocks(FIT, [["fit", renderFit(idx)]]);
  console.log("site/results/results.json + site/requirements.mjs → site/index.html (숫자 띠, 기기별 결과), site/fit.html (공고 항목별 근거)");
}

mkdirSync(OUT, { recursive: true });
if (RESULTS) writeIndex();
for (const page of PAGES) {
  if (page.results) {
    if (!RESULTS) { console.warn("건너뜀: site/results/results.json 이 없다 (publish_results.py 를 먼저)"); continue; }
    writeFileSync(path.join(OUT, page.out), renderResults(page), "utf8");
    console.log(`site/results/results.json → site/docs/${page.out}`);
    continue;
  }
  if (!existsSync(path.join(ROOT, page.src))) { console.warn(`건너뜀 (없음): ${page.src}`); continue; }
  writeFileSync(path.join(OUT, page.out), render(page), "utf8");
  console.log(`${page.src} → site/docs/${page.out}`);
}
