// README.md 의 약어와 전문 용어에 <abbr title="뜻"> 를 넣는다. GitHub 에서 마우스를 올리면 뜻이 보인다(점선 밑줄, 링크 아님).
//
//   cd site && npm run annotate-readme
//
// 용어와 뜻은 glossary.js 하나에서 가져온다 (소개 사이트와 같은 목록). 절(##)마다 처음 나올 때 한 번만 감싼다.
// 코드(`…`, ``` 블록), 링크 글자, 제목, HTML 태그 안은 건드리지 않는다. 이미 감싼 용어는 그대로 두므로 여러 번 돌려도 같다.
import { readFileSync, writeFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const here = new URL(".", import.meta.url);
const readme = new URL("../README.md", here);

const sandbox = {};
runInNewContext(readFileSync(new URL("glossary.js", here), "utf8"), sandbox);
const { pattern, meaning } = sandbox.IVI_GLOSSARY;

// 건드리지 않는 조각: 코드, 링크([글자](주소)), 이미 넣은 abbr, HTML 태그, 맨 주소
const PROTECTED = /(`+[^`]*`+)|(\[[^\]]*\]\([^)]*\))|(<abbr\b[^>]*>[\s\S]*?<\/abbr>)|(<[^>]+>)|(https?:\/\/\S+)/g;

const attr = (text) => text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

function annotatePlain(text, used) {
  return text.replace(new RegExp(pattern.source, "g"), (whole, term) => {
    if (used.has(term)) return whole;
    used.add(term);
    return `<abbr title="${attr(meaning[term])}">${term}</abbr>`;
  });
}

function annotateLine(line, used) {
  let out = "", last = 0;
  for (const match of line.matchAll(PROTECTED)) {
    out += annotatePlain(line.slice(last, match.index), used);
    if (match[3]) used.add(match[3].replace(/<[^>]+>/g, "").trim());   // 이미 감싼 용어는 이 절에서 쓴 것으로 센다
    out += match[0];
    last = match.index + match[0].length;
  }
  return out + annotatePlain(line.slice(last), used);
}

const lines = readFileSync(readme, "utf8").split("\n");
let fenced = false;
let used = new Set();
let wrapped = 0;
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (/^\s*(```|~~~)/.test(line)) { fenced = !fenced; continue; }
  if (fenced) continue;
  if (/^#{1,6}\s/.test(line)) {
    if (/^##\s/.test(line)) used = new Set();
    continue;
  }
  if (/^\s*<(img|details|summary|\/)/.test(line)) continue;
  const next = annotateLine(line, used);
  wrapped += (next.match(/<abbr /g) || []).length - (line.match(/<abbr /g) || []).length;
  lines[i] = next;
}
writeFileSync(readme, lines.join("\n"));
console.log(`README.md: 용어 ${wrapped}곳을 새로 감쌌다`);
