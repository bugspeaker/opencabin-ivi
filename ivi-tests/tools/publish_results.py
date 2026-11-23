"""전체 실행 결과를 소개 사이트(site/)와 문서(docs/test-results.md)로 옮긴다.

    python -m pytest --serial emulator-5554 --shots          # 기기마다 --shots 로 전체 실행
    python -m pytest --serial W3VBB22125209573 --shots
    python tools/publish_results.py                         # 기기 칸(aaos/mock/fold)마다 가장 최근 --shots 실행을 고른다
    python tools/publish_results.py --runs reports/runs/A.json reports/runs/B.json
    python tools/publish_results.py --add --runs reports/runs/C.json   # 지금 결과는 그대로 두고 그 기기 칸만 넣거나 바꾸기
    python tools/publish_results.py --blur aaos/test_video_resumes_where_it_stopped:800,455,60,28   # 번호판 가리기
    python tools/publish_results.py --repeat-runs "reports/runs/20261118-2*-r*.json"   # 반복 실행 통계도 함께 (사이트 지표 카드)
    python tools/publish_results.py --refresh-docs           # 결과는 그대로 두고 테스트 설명·마커만 다시 읽어 넣기
    cd ../site && npm run build-docs                         # 결과 페이지(site/docs/test-results.html) 다시 만들기

만드는 것
  site/results/results.json      테스트마다 기기별 판정 · 시간 · 메시지 · 화면 경로 (사이트 결과 페이지의 원자료)
  site/results/img/<칸>/*.webp  끝 화면. 가로 960px WebP 로 줄여 저장소에 넣을 수 있는 크기로 (한 장 약 30~60 KB)
  docs/test-results.md           GitHub 에서 보는 같은 내용의 표 (테스트 이름마다 앵커)

테스트 설명과 마커는 tests/*.py 의 docstring · @pytest.mark 에서 읽는다 (설명을 따로 적지 않는다).

영상 화면에는 직접 찍은 블랙박스 영상이 나온다. 다른 차 번호판이 읽히는 화면은 --blur 로 그 부분을 흐리게 해서 올린다.
좌표는 올리는 이미지(가로 960px) 기준 x,y,너비,높이. 실행마다 화면이 다르므로 새로 올릴 때마다 결과 화면을 보고 정한다.
"""
import argparse
import ast
import json
import re
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent          # ivi-tests/
REPO = ROOT.parent
RUNS = ROOT / "reports" / "runs"
SITE_RESULTS = REPO / "site" / "results"
DOC = REPO / "docs" / "test-results.md"

# 결과 표의 기기 칸. 같은 종류(mock)라도 모델이 다르면 칸을 나눈다 (태블릿과 폴드가 서로 덮어쓰지 않게)
COLUMNS = {"aaos": "AAOS 에뮬레이터", "mock": "태블릿 (Mock)", "fold": "갤럭시 폴드 (Mock)"}
COLUMN_BY_MODEL = {"SM-F900F": "fold"}
NAMES = {"aaos": "AAOS 에뮬레이터", "mock": "태블릿", "fold": "갤럭시 폴드"}  # 문장 안에서 부르는 이름
OUTCOME_LABEL = {
    "passed": "통과", "flaky": "재시도 후 통과", "failed": "실패", "error": "오류",
    "skipped": "건너뜀", "xfailed": "알려진 결함", "xpassed": "알려진 결함 통과", "quarantined": "격리",
}
MARKERS = ("smoke", "sanity", "regression", "spike", "aaos", "tablet")
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


def column(run):
    """실행 기록이 들어갈 칸. 모델로 정한 칸이 없으면 기기 종류(aaos/mock)."""
    summary = run["summary"]
    return COLUMN_BY_MODEL.get(summary.get("model", ""), summary["kind"])


def pick_runs(explicit):
    """기기 칸마다 실행 하나. 지정하지 않으면 화면이 있는 가장 최근 실행."""
    if explicit:
        runs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in explicit]
        return {column(run): run for run in runs}
    chosen = {}
    for path in sorted(RUNS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        run = json.loads(path.read_text(encoding="utf-8"))
        key = column(run)
        if key not in chosen and any(t.get("shot") for t in run["tests"]):
            chosen[key] = run
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


def parse_blur(items):
    """["aaos/test_x:800,455,60,28", ...] → {"aaos/test_x": [(800, 455, 860, 483)]}"""
    boxes = {}
    for item in items or []:
        key, _, nums = item.rpartition(":")
        x, y, w, h = (int(n) for n in nums.split(","))
        boxes.setdefault(key, []).append((x, y, x + w, y + h))
    return boxes


def blur(path, boxes):
    with Image.open(path) as image:
        image = image.convert("RGB")
        for box in boxes:
            image.paste(image.crop(box).filter(ImageFilter.GaussianBlur(6)), box[:2])
        image.save(path, "WEBP", quality=72, method=6)


def stability(paths):
    """반복 실행(run_bench.py --repeat) 기록에서 안정성 통계를 낸다. 사이트 첫 화면의 '반복 실행' 카드에 쓴다."""
    runs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]
    if not runs:
        return None
    tests = [t for run in runs for t in run["tests"] if t["outcome"] != "skipped"]
    by_kind = {}
    for run in runs:
        kind = run["summary"]["kind"]
        by_kind[kind] = by_kind.get(kind, 0) + sum(1 for t in run["tests"] if t["outcome"] != "skipped")
    flaky = sorted({t["nodeid"].split("::", 1)[-1] for t in tests if t["outcome"] == "flaky"})
    failed = sorted({t["nodeid"].split("::", 1)[-1] for t in tests if t["outcome"] in ("failed", "error")})
    return {
        "rounds": len({r["summary"]["run_id"] for r in runs}),
        "devices": len({r["summary"]["serial"] for r in runs}),
        "run_ids": sorted({r["summary"]["run_id"] for r in runs}),
        "executions": len(tests),
        "executions_by_kind": dict(sorted(by_kind.items())),  # 태블릿(Mock)은 VHAL 경로를 보지 않으므로 기기별로 따로 보여 준다
        "flaky": sum(1 for t in tests if t["outcome"] == "flaky"),
        "failed": sum(1 for t in tests if t["outcome"] in ("failed", "error")),
        "reruns": sum(t.get("reruns", 0) for t in tests),
        "flaky_tests": flaky,
        "failed_tests": failed,
    }


def build(runs, blur_boxes=None, repeat=None, base=None):
    """runs: {칸: 실행 기록}. base 를 주면 (--add) 그 결과에서 runs 에 없는 칸의 판정과 화면은 그대로 둔다."""
    blur_boxes = blur_boxes or {}
    files = read_tests()
    by_name = {t["name"]: t for f in files for t in f["tests"]}
    cases = {}  # 함수 이름 → {케이스 id → {"param", "results"}}

    kept = {d["kind"]: {"type": d["kind"], **d} for d in (base or {}).get("devices", []) if d["kind"] not in runs}
    for f in (base or {}).get("files", []):
        for t in f["tests"]:
            for c in t["cases"]:
                entry = cases.setdefault(t["name"], {}).setdefault(c["param"], {"param": c["param"], "results": {}})
                entry["results"].update({k: v for k, v in c["results"].items() if k in kept})
    if SITE_RESULTS.exists():
        for stale in ([SITE_RESULTS / "img" / key for key in runs] if base else [SITE_RESULTS / "img"]):
            shutil.rmtree(stale, ignore_errors=True)
    devices = []
    for kind in COLUMNS:
        if kind in kept:
            devices.append(kept[kind])
            continue
        run = runs.get(kind)
        if not run:
            continue
        summary = run["summary"]
        first_time = min((t["time"] for t in run["tests"]), default="")
        devices.append({
            # kind 는 결과 표의 칸(aaos/mock/fold), type 은 기기 종류(aaos/mock)
            "kind": kind, "type": summary["kind"], "label": COLUMNS[kind], "model": summary.get("model", ""), "serial": summary.get("serial", ""),
            "run_id": summary["run_id"], "time": first_time, "duration": summary["duration"],
            "counts": summary["counts"], "gate": summary["gate"],
            # 어느 코드로 돈 결과인지 (2026-11-20 부터 결과 파일에 남는다. 그 전 실행은 빈 값)
            "commit": summary.get("commit", ""), "dirty": summary.get("dirty", False),
            "app": summary.get("app", {}), "command": summary.get("launcher") or summary.get("command", ""),
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
                key = f"{kind}/{slug(nodeid)}"
                if key in blur_boxes:
                    blur(SITE_RESULTS / image, blur_boxes.pop(key))
            entry = cases.setdefault(func, {}).setdefault(param, {"param": param, "results": {}})
            entry["results"][kind] = {
                "outcome": test["outcome"], "label": OUTCOME_LABEL.get(test["outcome"], test["outcome"]),
                "duration": round(test["duration"], 1), "message": test.get("message", ""), "image": image,
                "reruns": test.get("reruns", 0), "measures": test.get("measures", {}),
                "signals": test.get("signals", []),
            }

    for f in files:
        for t in f["tests"]:
            t["cases"] = list(cases.get(t["name"], {}).values())
        f["tests"] = [t for t in f["tests"] if t["cases"]]
    files = [f for f in files if f["tests"]]
    missing = sorted(set(cases) - set(by_name))
    data = {"generated": time.strftime("%Y-%m-%d %H:%M"), "devices": devices, "files": files}
    repeat = repeat or (base or {}).get("stability")
    if repeat:
        data["stability"] = repeat
    SITE_RESULTS.mkdir(parents=True, exist_ok=True)
    (SITE_RESULTS / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    DOC.write_text(markdown(data), encoding="utf-8", newline="\n")
    return data, missing


def markdown(data):
    lines = [
        "# 테스트 결과",
        "",
        "기기마다 E2E 전체를 돌린 결과와 판정 직후 화면입니다. 실행 기록을 바탕으로 `ivi-tests/tools/publish_results.py`가 만듭니다. "
        + run_note(data, "flaky-report.md"),
        "AAOS 칸 아래의 `PROPERTY[area]=값`은 테스트 중에 CarService로 마지막으로 읽은 차량 값(최대 3개)입니다. 판정 직전에 읽은 값이 맨 뒤에 옵니다.",
        "소개 사이트(`site/docs/test-results.html`)에서는 같은 내용을 화면과 함께 볼 수 있습니다.",
        "판정과 화면은 아래 표의 실행에서 나온 것입니다. 그 뒤 바꾼 코드를 무엇으로 확인했는지는 별도 기록인 [README의 '결과 자료와 검증 시점'](../README.md#결과-자료와-검증-시점)에 있습니다.",
        "",
        "| 기기 | 실행 | 코드 | 앱 (APK sha256) | 결과 | 시간 |",
        "|---|---|---|---|---|---|",
    ]
    for d in data["devices"]:
        counts = ", ".join(f"{OUTCOME_LABEL.get(k, k)} {v}" for k, v in sorted(d["counts"].items()))
        code = (f"`{d['commit'][:7]}`" + (" (커밋 안 한 변경 있음)" if d.get("dirty") else "")) if d.get("commit") \
            else "기록 없음 (커밋을 남기기 전 형식)"
        app = d.get("app") or {}
        apk = f"{app.get('version') or '버전 미기록'}, `{app['apk_sha256'][:12]}`" if app.get("apk_sha256") else "기록 없음"
        lines.append(f"| {d['label']} ({d['model']}) | {d['time'].replace('T', ' ')} | {code} | {apk} | {counts} | {fmt_time(d['duration'])} |")
    lines += ["", device_note(data)]
    kinds = [d["kind"] for d in data["devices"]]
    for f in data["files"]:
        lines += ["", f"## {f['file']}", "", f["title"], ""]
        lines.append("| 테스트 | " + " | ".join(COLUMNS[k] for k in kinds) + " |")
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
                    cell = f"{r['label']}, {r['duration']}초"
                    if r["image"]:
                        cell += f", [화면](../site/results/{r['image']})"
                    if r.get("signals"):
                        cell += "<br>" + "<br>".join(f"`{s}`" for s in r["signals"])
                    cells.append(cell)
                lines.append(f"| {anchor}{name}{desc} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _josa(word, with_final, without_final):
    """받침이 있으면 앞의 것(은, 과), 없으면 뒤의 것(는, 와)."""
    last = ord(word[-1])
    return with_final if 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 else without_final


def _names(devices, topic=True):
    """['AAOS 에뮬레이터', '태블릿'] → 'AAOS 에뮬레이터와 태블릿은'"""
    names = [NAMES.get(d["kind"], d["label"]) for d in devices]
    joined = "".join(n + _josa(n, "과 ", "와 ") for n in names[:-1]) + names[-1]
    return joined + (_josa(names[-1], "은", "는") if topic else "")


def _app(devices):
    versions = sorted({(d.get("app") or {}).get("version") or "버전 미기록" for d in devices})
    return "앱 " + ", ".join(versions)


def run_note(data, stats_link):
    """어느 실행의 결과인지. 반복 실행의 마지막 회차인 기기와 따로 돌린 기기를 나눠 적는다."""
    st = data.get("stability")
    repeat = [d for d in data["devices"] if st and d["run_id"] in st["run_ids"]]
    parts = []
    if repeat:
        parts.append(f"{_names(repeat)} {st['rounds']}회 반복한 실행의 마지막 회차({_app(repeat)})이고, "
                     f"반복 전체의 통계는 [반복 실행 통계]({stats_link})에 있습니다.")
    for d in data["devices"]:
        if d not in repeat:
            parts.append(f"{_names([d])} {d['time'][:10]}에 따로 돌린 실행({_app([d])})입니다.")
    return " ".join(parts)


def device_note(data):
    mock = [d for d in data["devices"] if d.get("type", d["kind"]) == "mock"]
    note = ""
    if mock:
        note = (f"{_names(mock)} 화면 동작과 실기기에서만 나는 문제(터치 지연, 백그라운드 강제 종료, 좁은 화면의 배치)를 보는 기기입니다. "
                "차량 값은 앱 안의 Mock이라, VHAL 경로는 AAOS 열에서만 확인합니다. ")
    return note + ("건너뜀은 그 기기에 해당하지 않는 테스트입니다(태블릿 종류는 AAOS 전용, AAOS는 태블릿 전용 시계). "
                   "Release 게이트는 이 밖의 건너뜀을 막습니다.")


def refresh_docs(path=SITE_RESULTS / "results.json"):
    """결과는 그대로 두고 테스트 설명(docstring)과 마커만 지금 코드에서 다시 읽는다. 기기 없이 문구를 고칠 때 쓴다."""
    data = json.loads(path.read_text(encoding="utf-8"))
    current = {t["name"]: (f, t) for f in read_tests() for t in f["tests"]}
    for f in data["files"]:
        for t in f["tests"]:
            if t["name"] in current:
                source_file, source = current[t["name"]]
                f["title"] = source_file["title"]
                t.update({key: value for key, value in source.items() if key != "cases"})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    DOC.write_text(markdown(data), encoding="utf-8", newline="\n")
    return data


def fmt_time(seconds):
    return f"{int(seconds // 60)}분 {int(seconds % 60)}초"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", nargs="*", help="reports/runs/*.json (기기 칸마다 하나)")
    parser.add_argument("--add", action="store_true",
                        help="지금 results.json 의 다른 칸(판정, 화면, 반복 통계)은 그대로 두고 --runs 의 칸만 넣거나 바꾼다")
    parser.add_argument("--repeat-runs", metavar="GLOB", help="반복 실행 기록 (reports/runs/*-r*.json). 안정성 통계를 results.json 에 넣는다")
    parser.add_argument("--blur", action="append", metavar="KIND/TEST:X,Y,W,H",
                        help="흐리게 할 영역 (번호판 등). 올리는 이미지(가로 960px) 기준. 여러 번 줄 수 있다")
    parser.add_argument("--refresh-docs", action="store_true", help="결과는 그대로, 테스트 설명과 마커만 다시 읽는다")
    args = parser.parse_args()
    if args.refresh_docs:
        refresh_docs()
        print(f"설명과 마커만 다시 읽음 → {SITE_RESULTS / 'results.json'}, {DOC}")
        return
    if args.add and not args.runs:
        sys.exit("--add 는 --runs 와 함께 씁니다.")
    runs = pick_runs(args.runs)
    if not runs:
        sys.exit("화면이 있는 실행 기록이 없습니다. pytest 를 --shots 로 돌리세요.")
    boxes = parse_blur(args.blur)
    repeat = stability(sorted(ROOT.glob(args.repeat_runs))) if args.repeat_runs else None
    base = json.loads((SITE_RESULTS / "results.json").read_text(encoding="utf-8")) if args.add else None
    data, missing = build(runs, boxes, repeat, base)
    if boxes:
        print(f"주의: 해당하는 화면이 없어 흐리게 하지 못한 항목 {sorted(boxes)}")
    images = sum(1 for _ in (SITE_RESULTS / "img").rglob("*.webp"))
    size = sum(p.stat().st_size for p in (SITE_RESULTS / "img").rglob("*.webp")) / 1024 / 1024
    for d in data["devices"]:
        print(f"{d['label']}: {d['run_id']} ({d['time']}) {d['counts']}")
    print(f"화면 {images}장, {size:.1f} MB → {SITE_RESULTS}")
    print(f"문서 → {DOC}")
    if repeat:
        print(f"반복 실행: {repeat['rounds']}회 × {repeat['devices']}대, 테스트 {repeat['executions']}건, flaky {repeat['flaky']}, 실패 {repeat['failed']}")
    if missing:
        print(f"주의: 테스트 파일에서 찾지 못한 이름 {missing}")


if __name__ == "__main__":
    main()
