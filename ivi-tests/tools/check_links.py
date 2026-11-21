"""문서와 소개 사이트의 내부 링크가 끊기지 않았는지 본다. CI 의 unit job 이 unit/test_links.py 로 돌린다.

    python tools/check_links.py          # 끊긴 링크를 출력하고, 있으면 종료 코드 1

  Markdown  git 이 관리하는 .md (README.md, docs/ ...). [글](경로#앵커) 와 <a href>, <img src> 의 경로가 있는지,
            앵커가 그 문서의 제목(GitHub 규칙으로 만든 id)이나 id 속성에 있는지
  HTML      git 이 관리하는 site/ 아래 .html. href·src 의 경로가 있는지, #앵커가 그 파일의 id 에 있는지
바깥 주소(http, mailto)는 보지 않는다. 코드 블록 안의 글자와 <script> 안(자바스크립트가 만드는 링크)도 보지 않는다.
"""
import html
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent.parent   # 저장소 루트

MD_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
ATTR_LINK = re.compile(r"\b(?:href|src)\s*=\s*\"([^\"]*)\"")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
ID_ATTR = re.compile(r"\b(?:id|name)\s*=\s*\"([^\"]+)\"")
SKIP = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:")


def tracked(*patterns):
    """git 이 관리하는 파일 (만들어지기만 하고 커밋하지 않는 reports/, node_modules/ 를 빼려고)."""
    out = subprocess.run(["git", "ls-files", "-z", *patterns], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    return [ROOT / name for name in out.split("\0") if name]


def slug(text):
    """GitHub 이 제목에 붙이는 id 와 같은 규칙 (site/build-docs.mjs 의 slugger 도 같다)."""
    text = re.sub(r"<[^>]+>", "", text)                  # <abbr> 같은 태그
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # 링크는 글자만
    text = html.unescape(text).lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)                 # 문자, 숫자, 공백, _ , - 만 남긴다 (한글은 \w)
    return text.replace(" ", "-")


def strip_code(text):
    """``` 블록과 `인라인 코드` 를 지운다 (예시로 적은 경로는 링크가 아니다). 줄 수는 그대로 둔다."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "``", text)


def md_anchors(path):
    seen, anchors = {}, set()
    for line in strip_code(path.read_text(encoding="utf-8")).splitlines():
        match = HEADING.match(line)
        if match:
            base = slug(match.group(2))
            count = seen.get(base, 0)
            seen[base] = count + 1
            anchors.add(base if count == 0 else f"{base}-{count}")
        anchors.update(ID_ATTR.findall(line))
    return anchors


def html_anchors(path):
    return set(ID_ATTR.findall(path.read_text(encoding="utf-8")))


def anchors_of(path, cache):
    if path not in cache:
        cache[path] = md_anchors(path) if path.suffix == ".md" else html_anchors(path) if path.suffix == ".html" else None
    return cache[path]


def links_in(path):
    """(줄 번호, 링크) 목록."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        text = strip_code(text)
        patterns = (MD_LINK, ATTR_LINK)
    else:
        text = re.sub(r"<script\b.*?</script>", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S | re.I)
        patterns = (ATTR_LINK,)
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            found.extend((number, html.unescape(link)) for link in pattern.findall(line))
    return found


def check_file(path, cache):
    """끊긴 링크마다 '파일:줄: 링크 (이유)'."""
    problems = []
    for number, link in links_in(path):
        if not link or link.startswith(SKIP) or "${" in link:
            continue
        target, _, anchor = link.partition("#")
        target = unquote(target.split("?", 1)[0])
        anchor = unquote(anchor)
        resolved = path if not target else (path.parent / target).resolve()
        name = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        where = f"{name}:{number}: {link}"
        if target.startswith("/"):
            problems.append(f"{where} (절대 경로는 GitHub 과 사이트에서 가리키는 곳이 다르다)")
            continue
        if not resolved.exists():
            problems.append(f"{where} (파일 없음)")
            continue
        if anchor and resolved.is_file():
            anchors = anchors_of(resolved, cache)
            if anchors is not None and anchor not in anchors and anchor.lower() not in anchors:
                problems.append(f"{where} (앵커 없음)")
    return problems


def check(paths=None):
    if paths is None:
        paths = tracked("*.md") + [p for p in tracked("site/*.html", "site/**/*.html")]
    cache, problems = {}, []
    for path in sorted(set(paths)):
        problems.extend(check_file(path, cache))
    return problems


def main():
    problems = check()
    for problem in problems:
        print(problem)
    print(f"끊긴 링크 {len(problems)}개")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
