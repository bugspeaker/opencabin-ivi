"""전체 실행 결과를 소개 사이트(site/)와 문서(docs/test-results.md)로 옮긴다.

    python -m pytest --serial emulator-5554 --shots          # 기기마다 --shots 로 전체 실행
    python -m pytest --serial W3VBB22125209573 --shots
    python tools/publish_results.py                         # 기기 종류(aaos/mock)마다 가장 최근 --shots 실행을 고른다
    python tools/publish_results.py --runs reports/runs/A.json reports/runs/B.json
    cd ../site && npm run build-docs                         # 결과 페이지(site/docs/test-results.html) 다시 만들기

만드는 것
  site/results/results.json      테스트마다 기기별 판정 · 시간 · 메시지 · 화면 경로 (사이트 결과 페이지의 원자료)
  site/results/img/<kind>/*.webp 끝 화면. 가로 960px WebP 로 줄여 저장소에 넣을 수 있는 크기로 (한 장 약 30~60 KB)
  docs/test-results.md           GitHub 에서 보는 같은 내용의 표 (테스트 이름마다 앵커)

테스트 설명과 마커는 tests/*.py 의 docstring · @pytest.mark 에서 읽는다 (설명을 따로 적지 않는다).
"""
import argparse
import ast
import json
import re
import shutil
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent          # ivi-tests/
REPO = ROOT.parent
RUNS = ROOT / "reports" / "runs"
SITE_RESULTS = REPO / "site" / "results"
DOC = REPO / "docs" / "test-results.md"

KINDS = {"aaos": "AAOS 에뮬레이터", "mock": "태블릿 (Mock)"}
OUTCOME_LABEL = {
    "passed": "통과", "flaky": "재시도 후 통과", "failed": "실패", "error": "오류",
    "skipped": "건너뜀", "xfailed": "알려진 결함", "xpassed": "알려진 결함 통과", "quarantined": "격리",
}
MARKERS = ("smoke", "sanity", "regression", "spike", "aaos")
IMAGE_WIDTH = 960


def read_tests():
    """tests/*.py 에서 파일 설명, 테스트 함수 순서 · 설명 · 마커를 읽는다."""
    files = []
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"))
        title = (ast.get_docstring(module) or "").strip().split("\n")[0]
        module_marks = _marks_from_assign(module)
        tests = []
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                doc = " ".join((ast.get_docstring(node) or "").split())
                marks = [m for m in _marks(node.decorator_list) if m in MARKERS]
                tests.append({"name": node.name, "doc": doc, "markers": sorted(set(marks + module_marks), key=MARKERS.index)})
        files.append({"file": path.name, "title": title, "tests": tests})
    return files


def _marks(decorators):
    for deco in decorators:
        target = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Attribute) and target.value.attr == "mark":
            yield target.attr


def _marks_from_assign(module):
    """pytestmark = [pytest.mark.x, ...] / pytest.mark.x"""
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
            values = node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
            return [m for m in _marks(values) if m in MARKERS]
    return []


def pick_runs(explicit):
    """기기 종류마다 실행 하나. 지정하지 않으면 화면이 있는 가장 최근 실행."""
    if explicit:
        runs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in explicit]
        return {run["summary"]["kind"]: run for run in runs}
    chosen = {}
    for path in sorted(RUNS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        run = json.loads(path.read_text(encoding="utf-8"))
        kind = run["summary"]["kind"]
        if kind not in chosen and any(t.get("shot") for t in run["tests"]):
            chosen[kind] = run
    return chosen


def slug(nodeid):
    return re.sub(r"[^\w.\-]+", "_", nodeid.split("::", 1)[-1]).strip("_")


def convert(src, dest):
    with Image.open(src) as image:
        image = image.convert("RGB")
        if image.width > IMAGE_WIDTH:
            image = image.resize((IMAGE_WIDTH, round(image.height * IMAGE_WIDTH / image.width)), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "WEBP", quality=72, method=6)


def build(runs):
    files = read_tests()
    by_name = {t["name"]: t for f in files for t in f["tests"]}
    cases = {}  # 함수 이름 → {케이스 id → {"param", "results"}}

    if SITE_RESULTS.exists():
        shutil.rmtree(SITE_RESULTS / "img", ignore_errors=True)
    devices = []
    for kind in KINDS:
        run = runs.get(kind)
        if not run:
            continue
        summary = run["summary"]
        first_time = min((t["time"] for t in run["tests"]), default="")
        devices.append({
            "kind": kind, "label": KINDS[kind], "model": summary.get("model", ""), "serial": summary.get("serial", ""),
            "run_id": summary["run_id"], "time": first_time, "duration": summary["duration"],
            "counts": summary["counts"], "gate": summary["gate"],
        })
        for test in run["tests"]:
            nodeid = test["nodeid"]
            func = nodeid.split("::", 1)[-1].split("[", 1)[0]
            param = nodeid.split("[", 1)[1].rstrip("]") if "[" in nodeid else ""
            image = None
            shot = test.get("shot")
            if shot and Path(shot).exists():
                image = f"img/{kind}/{slug(nodeid)}.webp"
                convert(shot, SITE_RESULTS / image)
            entry = cases.setdefault(func, {}).setdefault(param, {"param": param, "results": {}})
            entry["results"][kind] = {
                "outcome": test["outcome"], "label": OUTCOME_LABEL.get(test["outcome"], test["outcome"]),
                "duration": round(test["duration"], 1), "message": test.get("message", ""), "image": image,
                "reruns": test.get("reruns", 0),
            }

    for f in files:
        for t in f["tests"]:
            t["cases"] = list(cases.get(t["name"], {}).values())
        f["tests"] = [t for t in f["tests"] if t["cases"]]
    files = [f for f in files if f["tests"]]
    missing = sorted(set(cases) - set(by_name))
    data = {"generated": time.strftime("%Y-%m-%d %H:%M"), "devices": devices, "files": files}
    SITE_RESULTS.mkdir(parents=True, exist_ok=True)
    (SITE_RESULTS / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    DOC.write_text(markdown(data), encoding="utf-8", newline="\n")
    return data, missing


def markdown(data):
    lines = [
        "# 테스트 결과",
        "",
        "기기별 전체 E2E 실행 결과와 테스트마다 끝 화면입니다. `ivi-tests/tools/publish_results.py`가 실행 기록에서 만듭니다.",
        "소개 사이트에서는 같은 내용을 화면 미리 보기와 함께 볼 수 있습니다 (`site/docs/test-results.html`).",
        "",
        "| 기기 | 실행 | 결과 | 시간 |",
        "|---|---|---|---|",
    ]
    for d in data["devices"]:
        counts = ", ".join(f"{k} {v}" for k, v in sorted(d["counts"].items()))
        lines.append(f"| {d['label']} ({d['model']}) | {d['time'].replace('T', ' ')} | {counts} | {fmt_time(d['duration'])} |")
    kinds = [d["kind"] for d in data["devices"]]
    for f in data["files"]:
        lines += ["", f"## {f['file']}", "", f["title"], ""]
        lines.append("| 테스트 | " + " | ".join(KINDS[k] for k in kinds) + " |")
        lines.append("|---|" + "---|" * len(kinds))
        for t in f["tests"]:
            for i, case in enumerate(t["cases"]):
                name = f"`{t['name']}`" + (f" `[{case['param']}]`" if case["param"] else "")
                anchor = f'<a id="{t["name"]}"></a>' if i == 0 else ""
                desc = f"<br>{t['doc']}" if i == 0 and t["doc"] else ""
                cells = []
                for k in kinds:
                    r = case["results"].get(k)
                    if not r:
                        cells.append("-")
                        continue
                    cell = f"{r['label']} · {r['duration']}초"
                    if r["image"]:
                        cell += f" · [화면](../site/results/{r['image']})"
                    cells.append(cell)
                lines.append(f"| {anchor}{name}{desc} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def fmt_time(seconds):
    return f"{int(seconds // 60)}분 {int(seconds % 60)}초"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", nargs="*", help="reports/runs/*.json (기기 종류마다 하나)")
    args = parser.parse_args()
    runs = pick_runs(args.runs)
    if not runs:
        sys.exit("화면이 있는 실행 기록이 없습니다. pytest 를 --shots 로 돌리세요.")
    data, missing = build(runs)
    images = sum(1 for _ in (SITE_RESULTS / "img").rglob("*.webp"))
    size = sum(p.stat().st_size for p in (SITE_RESULTS / "img").rglob("*.webp")) / 1024 / 1024
    for d in data["devices"]:
        print(f"{d['label']}: {d['run_id']} ({d['time']}) {d['counts']}")
    print(f"화면 {images}장, {size:.1f} MB → {SITE_RESULTS}")
    print(f"문서 → {DOC}")
    if missing:
        print(f"주의: 테스트 파일에서 찾지 못한 이름 {missing}")


if __name__ == "__main__":
    main()
