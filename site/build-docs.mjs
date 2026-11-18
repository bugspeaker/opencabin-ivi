// docs/*.md 와 README.md 를 사이트 디자인(DESIGN.md 토큰)에 맞춘 HTML 로 바꾼다.
// file:// 로 열면 브라우저가 .md 를 읽어 올 수 없어서, 미리 HTML 로 만들어 둔다.
//
//   cd site && npm install && npm run build-docs
//
// 결과: site/docs/*.html (커밋한다. 문서를 고치면 다시 실행)
// 테스트 결과 페이지(test-results.html)는 site/results/results.json 으로 만든다
// (ivi-tests/tools/publish_results.py 가 실행 기록과 끝 화면에서 만든다).
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";

const SITE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SITE, "..");
const OUT = path.join(SITE, "docs");
const RESULTS_JSON = path.join(SITE, "results", "results.json");

// 사이드바 순서. src 는 저장소 루트 기준
const PAGES = [
  { src: "docs/portfolio.md", out: "portfolio.html", nav: "포트폴리오" },
  { src: "docs/test-results.md", out: "test-results.html", nav: "테스트 결과", results: true },
  { src: "README.md", out: "readme.html", nav: "README" },
  { src: "docs/phase1-spike.md", out: "phase1-spike.html", nav: "1. 기술 검증" },
  { src: "docs/phase2-app.md", out: "phase2-app.html", nav: "2. 앱" },
  { src: "docs/phase3-framework.md", out: "phase3-framework.html", nav: "3. 테스트 프레임워크" },
  { src: "docs/phase4-operations.md", out: "phase4-operations.html", nav: "4. 운영 · CI" },
  { src: "docs/phase5-design.md", out: "phase5-design.html", nav: "5. 재점검과 디자인" },
  { src: "docs/phase6-features.md", out: "phase6-features.html", nav: "6. 기능 확장" },
  { src: "docs/phase7-pleos.md", out: "phase7-pleos.html", nav: "7. 3영역 화면 개편" },
  { src: "docs/phase8-signals.md", out: "phase8-signals.html", nav: "8. 차량 신호 확장" },
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
<meta name="theme-color" content="#010102">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="doc.css">${head}
</head>
<body>
<a class="skip" href="#content">본문으로 건너뛰기</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark" aria-hidden="true"></span>OpenCabin IVI</a>
  <span class="crumb">문서 · ${esc(page.nav)}</span>
  <a class="src" href="${esc(path.posix.relative("site/docs", page.src))}">원문 .md</a>
</header>
<div class="layout${mainClass.includes("results") ? " wide" : ""}">
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
  renderer.table = (header, body) => `<div class="table"><table><thead>${header}</thead><tbody>${body}</tbody></table></div>\n`;

  let body = marked.parse(md, { renderer, gfm: true });
  // 원문 HTML(<details> 안의 이미지 등)에 남은 상대 경로도 바꾼다
  // (renderer.image 가 만든 것은 data-md 표시가 있어 건너뛴다. 두 번 바꾸면 경로가 깨진다)
  body = body.replace(/<img(?![^>]*\sdata-md)([^>]*\ssrc=")([^"]+)(")/g, (m, a, src, b) => `<img${a}${rewrite(src, srcDir)}${b}`);
  // ✅ ❌ ⚠️ 를 상태 배지처럼
  body = body.replace(/✅/g, '<span class="ok">✅</span>').replace(/❌/g, '<span class="no">❌</span>');
  body = linkTests(body);

  const scripts = body.includes('class="mermaid"') ? `<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: true, theme: "base", themeVariables: {
  darkMode: true, background: "#0f1011", primaryColor: "#18191a", primaryTextColor: "#f7f8f8",
  primaryBorderColor: "#5e6ad2", lineColor: "#8a8f98", secondaryColor: "#141516", tertiaryColor: "#141516",
  clusterBkg: "#0f1011", clusterBorder: "#34343a", edgeLabelBackground: "#0f1011",
  fontFamily: "Inter, system-ui, sans-serif", fontSize: "14px" } });
</script>` : "";
  return shell(page, { title, body, toc, scripts });
}

// ---------------- 테스트 결과 페이지 ----------------

const BAD = new Set(["failed", "error", "flaky", "xpassed"]);
const MARKER_LABEL = { smoke: "smoke", sanity: "sanity", regression: "regression", spike: "spike", aaos: "AAOS 전용" };
const fmtTime = (s) => `${Math.floor(s / 60)}분 ${Math.round(s % 60)}초`;

function countsLine(counts) {
  const order = ["passed", "flaky", "failed", "error", "skipped", "xfailed", "xpassed", "quarantined"];
  const label = { passed: "통과", flaky: "재시도 후 통과", failed: "실패", error: "오류", skipped: "건너뜀", xfailed: "알려진 결함", xpassed: "알려진 결함 통과", quarantined: "격리" };
  return order.filter((k) => counts[k]).map((k) =>
    `<span class="pill p-${k}">${label[k]} ${counts[k]}</span>`).join("");
}

function renderResults(page) {
  const data = RESULTS;
  const kinds = data.devices.map((d) => d.kind);
  const devices = data.devices.map((d) => `
      <section class="device-card">
        <p class="eyebrow">${esc(d.label)}</p>
        <p class="device-model">${esc(d.model)}</p>
        <div class="pills">${countsLine(d.counts)}</div>
        <dl>
          <div><dt>실행</dt><dd>${esc(d.time.replace("T", " ").slice(0, 16))}</dd></div>
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
          if (!r) return `<div class="shot-cell is-empty"><span class="cell-device">${esc(dev.label)}</span><p class="cell-note">이 기기에서는 돌리지 않음</p></div>`;
          const caption = `${t.name}${c.param ? ` [${c.param}]` : ""} · ${dev.label} · ${r.label} · ${r.duration}초`;
          const media = r.image
            ? `<button type="button" class="shot shot-${k}" data-full="../results/${esc(r.image)}" data-caption="${esc(caption)}" aria-label="${esc(dev.label)} 화면 크게 보기">
                <img src="../results/${esc(r.image)}" alt="${esc(dev.label)}에서 ${esc(t.name)} 이 끝난 화면" loading="lazy" decoding="async">
              </button>`
            : `<div class="shot shot-${k} no-shot"><p>${esc(r.message || "화면 없음")}</p></div>`;
          return `<div class="shot-cell">
              ${media}
              <div class="cell-meta"><span class="cell-device">${esc(dev.label)}</span><span class="pill p-${r.outcome}">${esc(r.label)}</span><span class="cell-time">${r.duration}초</span></div>
            </div>`;
        }).join("");
        return `<div class="case">${c.param ? `<p class="case-param"><code>[${esc(c.param)}]</code></p>` : ""}<div class="case-shots">${cells}</div></div>`;
      }).join("");
      const marks = t.markers.map((m) => `<span class="mark-chip">${esc(MARKER_LABEL[m] || m)}</span>`).join("");
      return `<article class="rtest" id="${esc(t.name)}" data-markers="${esc(t.markers.join(" "))}" data-bad="${bad ? 1 : 0}">
          <div class="rtest-text">
            <header class="rtest-head"><a class="rtest-name" href="#${esc(t.name)}"><code>${esc(t.name)}</code></a>${marks}</header>
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

  const markers = [...new Set(data.files.flatMap((f) => f.tests.flatMap((t) => t.markers)))];
  const body = `
    <h1 id="테스트-결과">테스트 결과</h1>
    <p class="lead">E2E ${total}개를 기기마다 한 번씩 돌린 결과입니다. 테스트마다 판정이 난 직후의 화면을 남겼고, 화면을 누르면 크게 볼 수 있습니다.</p>
    <div class="device-cards">${devices}</div>
    <div class="filters" role="group" aria-label="테스트 거르기">
      <button type="button" class="chip" aria-pressed="true" data-filter="">전체</button>
      ${markers.map((m) => `<button type="button" class="chip" aria-pressed="false" data-filter="${esc(m)}">${esc(MARKER_LABEL[m] || m)}</button>`).join("")}
      <label class="only-bad"><input type="checkbox" id="only-bad"> 실패·재시도만</label>
      <span class="filter-count" id="filter-count" aria-live="polite"></span>
      <select class="jump" id="jump" aria-label="파일로 이동"><option value="">파일로 이동</option>${toc.map((t) => `<option value="${esc(t.id)}">${esc(t.text)}</option>`).join("")}</select>
    </div>
    <p class="empty-note" id="empty-note" hidden>조건에 맞는 테스트가 없습니다.</p>
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
  let filter = "";
  function apply() {
    let shown = 0;
    document.querySelectorAll(".rfile").forEach((file) => {
      let any = false;
      file.querySelectorAll(".rtest").forEach((t) => {
        const ok = (!filter || t.dataset.markers.split(" ").includes(filter)) && (!onlyBad.checked || t.dataset.bad === "1");
        t.hidden = !ok; if (ok) { any = true; shown++; }
      });
      file.hidden = !any;
    });
    count.textContent = shown + "개 테스트";
    empty.hidden = shown > 0;
  }
  chips.forEach((c) => c.addEventListener("click", () => {
    filter = c.dataset.filter;
    chips.forEach((x) => x.setAttribute("aria-pressed", String(x === c)));
    apply();
  }));
  onlyBad.addEventListener("change", apply);
  document.getElementById("jump").addEventListener("change", (e) => {
    if (e.target.value) document.getElementById(e.target.value).scrollIntoView({ behavior: "smooth" });
    e.target.value = "";
  });
  apply();
  // 다른 문서에서 #test_이름 으로 들어오면 그 테스트를 잠깐 강조한다
  const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target && target.classList.contains("rtest")) target.classList.add("is-target");
})();
</script>`;
  return shell(page, { title: "테스트 결과", body, scripts, mainClass: "doc results" });
}

mkdirSync(OUT, { recursive: true });
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
