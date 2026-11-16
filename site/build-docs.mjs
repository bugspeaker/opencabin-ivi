// docs/*.md 와 README.md 를 사이트 디자인(DESIGN.md 토큰)에 맞춘 HTML 로 바꾼다.
// file:// 로 열면 브라우저가 .md 를 읽어 올 수 없어서, 미리 HTML 로 만들어 둔다.
//
//   cd site && npm install && npm run build-docs
//
// 결과: site/docs/*.html (커밋한다. 문서를 고치면 다시 실행)
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";

const SITE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SITE, "..");
const OUT = path.join(SITE, "docs");

// 사이드바 순서. src 는 저장소 루트 기준
const PAGES = [
  { src: "docs/portfolio.md", out: "portfolio.html", nav: "포트폴리오" },
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

  const nav = PAGES.map((p) =>
    `<a href="${p.out}"${p.out === page.out ? ' aria-current="page"' : ""}>${esc(p.nav)}</a>`).join("\n        ");
  const tocHtml = toc.filter((t) => t.level === 2).length > 1
    ? `<nav class="toc" aria-label="이 문서의 목차"><p class="eyebrow">이 문서</p>${toc.map((t) =>
        `<a class="l${t.level}" href="#${esc(t.id)}">${esc(t.text)}</a>`).join("")}</nav>`
    : "";
  const hasMermaid = body.includes('class="mermaid"');

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
<link rel="stylesheet" href="doc.css">
</head>
<body>
<a class="skip" href="#content">본문으로 건너뛰기</a>
<header class="top">
  <a class="brand" href="../index.html"><span class="mark" aria-hidden="true"></span>OpenCabin IVI</a>
  <span class="crumb">문서 · ${esc(page.nav)}</span>
  <a class="src" href="${esc(path.posix.relative("site/docs", page.src))}">원문 .md</a>
</header>
<div class="layout">
  <aside class="side">
    <nav aria-label="문서 목록">
        ${nav}
    </nav>
  </aside>
  <main id="content" class="doc">
${body}
  </main>
  ${tocHtml}
</div>
${hasMermaid ? `<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: true, theme: "base", themeVariables: {
  darkMode: true, background: "#0f1011", primaryColor: "#18191a", primaryTextColor: "#f7f8f8",
  primaryBorderColor: "#5e6ad2", lineColor: "#8a8f98", secondaryColor: "#141516", tertiaryColor: "#141516",
  clusterBkg: "#0f1011", clusterBorder: "#34343a", edgeLabelBackground: "#0f1011",
  fontFamily: "Inter, system-ui, sans-serif", fontSize: "14px" } });
</script>` : ""}
</body>
</html>
`;
}

mkdirSync(OUT, { recursive: true });
for (const page of PAGES) {
  if (!existsSync(path.join(ROOT, page.src))) { console.warn(`건너뜀 (없음): ${page.src}`); continue; }
  writeFileSync(path.join(OUT, page.out), render(page), "utf8");
  console.log(`${page.src} → site/docs/${page.out}`);
}
