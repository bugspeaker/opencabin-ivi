"""원자료가 남은 E2E 실행을 모두 합친 기록을 만든다 (docs/run-history.md, site/results/history.json).

    python tools/run_history.py                 # docs/evidence 아래 결과 파일 전부
    python tools/run_history.py --check         # 만들지 않고, 지금 파일과 다르면 실패 (CI)

docs/evidence 아래의 결과 파일(summary + tests 를 가진 JSON)을 모두 읽는다. 같은 실행(run id, 기기)이 두 번 있으면 한 번만 센다.
폴더마다 무엇을 확인한 실행인지(PURPOSE), 실패·오류·재시도 통과마다 원인(CAUSES)을 아래 표에 적어 두고 함께 보여 준다.
원인을 적지 않은 실패가 있거나 목적을 적지 않은 폴더가 있으면 --check 가 실패한다 (원인 없는 실패를 숫자로만 남기지 않게).
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # ivi-tests/
REPO = ROOT.parent

DEVICE = {"aaos": "AAOS 에뮬레이터", "DBY-W09": "태블릿", "SM-F900F": "갤럭시 폴드"}
BAD = ("failed", "error")

# docs/evidence 아래 폴더 → 무엇을 확인한 실행인가. intentional: 확인하려고 일부러 실패나 끊김을 만든 실행
PURPOSE = {
    "2026-11-18-repeat5/runs": ("반복 5회 (129개)", False),
    "2026-11-19-after-review/runs": ("대기 방식을 바꾼 뒤 전체 1회", False),
    "2026-11-20-session-recovery/runs": ("세션 복구 확인 (A·B는 세션을 일부러 끊은 실행)", False),
    "2026-11-21-main/attempt1/runs": ("반복 3회의 첫 시도 (1회차에서 멈춤)", False),
    "2026-11-21-main/crash-check": ("앱 크래시 판정 확인 (앱을 일부러 죽인 실행)", True),
    "2026-11-21-main/runs": ("반복 3회 (129개)", False),
    "2026-11-23-fold/runs": ("갤럭시 폴드 첫 실행 (배치 수정 전)", False),
    "2026-11-23-fold/runs-after": ("배치 수정 후 세 기기", False),
    "2026-11-23-coverage/runs-new-tests": ("새 테스트 11개 첫 확인", False),
    "2026-11-23-coverage/runs-min760": ("가장 작은 화면 760×500dp 전체", False),
    "2026-11-23-coverage/runs": ("반복 3회 (140개)", False),
    "2026-11-23-coverage/runs-fold": ("폴드 1회 (140개)", False),
    "2026-11-23-idling/runs-first": ("정지 상태 수정 첫 확인", False),
    "2026-11-23-idling/runs": ("반복 3회 (144개)", False),
    "2026-11-23-idling/runs-fold": ("폴드 1회 (144개)", False),
    "2026-11-24-driving-state/runs-first": ("주행 상태 읽기 수정 첫 확인", False),
    "2026-11-24-driving-state/attempt1/runs": ("반복 3회의 첫 시도 (1회차 태블릿 실패)", False),
    "2026-11-24-driving-state/runs": ("반복 3회 (144개)", False),
    "2026-11-24-driving-state/runs-fold": ("폴드 1회 (144개)", False),
    "2026-11-24-concurrency/runs-first": ("동시 조작 테스트 첫 확인 (커밋 전)", False),
    "2026-11-24-concurrency/probe": ("빠른 누름 간격 줄여 보기 (저장소에 넣지 않은 임시 테스트)", False),
    "2026-11-24-concurrency/runs": ("반복 3회 (150개)", False),
    "2026-11-24-concurrency/runs-fold": ("폴드 1회 (150개)", False),
    "2026-11-25-fault-injection/runs": ("결함 주입 실험 (결함을 하나씩 일부러 넣은 빌드와 대조군)", True),
}

# 실행 id → 그 실행의 실패·오류·재시도 통과의 원인. 원인 분류는 사이트의 결함 분류와 같은 말을 쓴다
CAUSES = {
    "20261120-session-a": ("확인용", "실행 120초에 UiAutomator2 서버를 일부러 강제 종료했습니다. 세션을 다시 붙이고 재시도에서 통과했습니다."),
    "20261120-session-b": ("확인용", "실행 45초에 Appium 서버를 일부러 껐다 켰습니다. 세션을 다시 붙이고 재시도에서 통과했습니다."),
    "20261121-115127-r1": ("환경", "PC 화면이 꺼진 상태에서 창 모드로 다시 켠 에뮬레이터가 멈췄습니다. 창 없이 켜게 고치고 처음부터 다시 돌렸습니다."),
    "20261121-probe2": ("확인용", "앱 크래시 판정을 확인하려고 테스트 도중 앱을 일부러 죽였습니다."),
    "20261121-probe5": ("확인용", "앱 크래시 판정을 확인하려고 테스트 도중 앱을 일부러 죽였습니다."),
    "20261123-fold-full-portrait": ("앱 결함", "좁고 낮은 폴드 화면에서 배치가 넘쳤습니다(#42, #43, #44). 앱 0.4.1에서 고쳤습니다."),
    "20261123-min760": ("플랫폼", "1024×768에서만 나는 SystemUI 겹침(#21)이 760×500dp에서는 재현되지 않아, 알려진 결함 표시(xfail strict)가 실패로 뒤집혔습니다."),
    "20261123-new-aaos": ("테스트 도구", "막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상). 그 테스트만 다시 돌려 통과했습니다."),
    "20261123-ux-aaos": ("테스트 도구", "막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상)."),
    "20261124-driving-state-aaos": ("테스트 도구", "막 켠 에뮬레이터에서 UiAutomator2 계측 프로세스가 죽었습니다(#29와 같은 현상)."),
    "20261124-110716-r1": ("환경", "실행을 시작할 무렵 USB를 연결해 태블릿에 뜬 시스템 창(USB 연결 방식 선택)이 앱을 가렸습니다. 첫 시도로 남기고 3회를 다시 돌렸습니다."),
    "20261124-153908": ("테스트 도구", "AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. adb input tap으로 바꿔 통과했습니다."),
    "20261124-154050": ("테스트 도구", "AAOS 에뮬레이터에서 빠른 누름을 Appium W3C 동작으로 보내자 UiAutomator2의 MOVE 이벤트 주입이 실패했습니다. 누름 사이 대기를 빼도 같아서 adb input tap으로 바꿨습니다."),
}


# (실행 id, 테스트) → 원인. 한 실행 안에서 테스트마다 원인이 다를 때 CAUSES 보다 먼저 본다
TEST_CAUSES = {
    ("fi-F01-aaos", "tests/test_climate.py::test_signal_is_shown_on_climate_and_home[passenger]"): (
        "환경", "결함과 상관없는 테스트입니다. adb 서버 연결이 잠깐 끊겨(cannot connect to daemon) 실패하고 재시도에서 통과했습니다. 끊긴 원인은 확인하지 못했습니다."),
}

# 결함 주입 실험의 실행(run id fi-<결함>-<기기>). 결함을 넣은 빌드의 실패는 결함 때문에 난 것이라 실행마다 따로 적지 않는다.
# 결함을 잡았는지는 대조군과 견주어 tools/fault_report.py 가 판정한다. 대조군(F00)의 실패는 결함이 없는데 난 실패라 따로 적어야 한다
FAULT_RUN = re.compile(r"^fi-(F\d+)-")

# 합계에서 뺀 실행(intentional)을 머리말에서 부르는 이름. 없으면 PURPOSE 의 설명을 쓴다
INTENTIONAL_NAME = {
    "2026-11-21-main/crash-check": "앱을 일부러 죽인 실행",
    "2026-11-25-fault-injection/runs": "결함을 하나씩 넣은 결함 주입 실행과 그 대조군",
}


def cause_of(run_id, nodeid=""):
    if (run_id, nodeid) in TEST_CAUSES:
        return TEST_CAUSES[(run_id, nodeid)]
    if run_id in CAUSES:
        return CAUSES[run_id]
    found = FAULT_RUN.match(run_id)
    if found and found[1] != "F00":
        return ("확인용", f"결함 주입 빌드({found[1]})에서 난 실패입니다. 결함을 잡았는지는 대조군과 견주어 결함 주입 기록(evidence/2026-11-25-fault-injection/README.md)에서 판정합니다.")
    return ("", "")


def load(evidence):
    """evidence 아래 결과 파일을 읽는다. 같은 (run id, 기기)는 한 번만."""
    runs, seen = [], set()
    for path in sorted(evidence.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or "summary" not in data or "tests" not in data:
            continue
        s = data["summary"]
        key = (s["run_id"], s.get("serial", ""))
        if key in seen:
            continue
        seen.add(key)
        folder = path.parent.relative_to(evidence).as_posix()
        runs.append({"folder": folder, "summary": s, "tests": data["tests"], "path": path.relative_to(evidence.parent.parent).as_posix()})
    return runs


def device_of(s):
    return DEVICE.get(s.get("model", ""), DEVICE.get(s.get("kind", ""), s.get("model", "") or s.get("kind", "")))


def run_date(run_id, test):
    """월-일. run id 가 날짜(YYYYMMDD)로 시작하지 않으면(결함 주입 fi-F01-aaos 등) 테스트를 시작한 시각에서 읽는다."""
    if run_id[:8].isdigit():
        return f"{run_id[4:6]}-{run_id[6:8]}"
    return (test.get("time") or "")[5:10]


def outcome_counts(tests):
    c = Counter(t["outcome"] for t in tests)
    return {
        "executed": sum(v for k, v in c.items() if k != "skipped"),
        "passed": c["passed"], "flaky": c["flaky"], "bad": sum(c[k] for k in BAD),
        "xfailed": c["xfailed"], "skipped": c["skipped"],
        "reruns": sum(t.get("reruns", 0) for t in tests),
    }


def summarize(runs):
    total = Counter()
    by_device = defaultdict(Counter)
    groups = []
    problems = []
    missing = {"purpose": sorted({r["folder"] for r in runs if r["folder"] not in PURPOSE}), "cause": []}
    by_folder = defaultdict(list)
    for r in runs:
        by_folder[r["folder"]].append(r)
    def started(folder):  # 같은 날은 먼저 돈 실행부터 (run id 는 이름이 제각각이라 테스트 시각으로 줄 세운다)
        return min((t.get("time") or "") for r in by_folder[folder] for t in r["tests"]) or folder

    for folder in sorted(by_folder, key=lambda f: (f[:10], started(f))):
        group = by_folder[folder]
        purpose, intentional = PURPOSE.get(folder, (folder, False))
        g = Counter()
        for r in group:
            s, counts = r["summary"], outcome_counts(r["tests"])
            g.update(counts)
            g["sessions"] += 1
            if not intentional:
                total.update(counts)
                total["sessions"] += 1
                by_device[device_of(s)].update(counts)
                by_device[device_of(s)]["sessions"] += 1
            for t in r["tests"]:
                if t["outcome"] in BAD or t["outcome"] == "flaky":
                    run_id = s["run_id"]
                    kind, why = cause_of(run_id, t["nodeid"])
                    if not why:
                        missing["cause"].append(f"{run_id} {t['nodeid']}")
                    problems.append({
                        "date": run_date(run_id, t), "run_id": run_id, "device": device_of(s),
                        "test": t["nodeid"].split("::", 1)[-1], "outcome": "재시도 후 통과" if t["outcome"] == "flaky" else "실패" if t["outcome"] == "failed" else "오류",
                        "kind": kind, "why": why, "intentional": intentional,
                    })
        commits = sorted({(r["summary"].get("commit") or "")[:7] for r in group} - {""})
        groups.append({
            "folder": folder, "purpose": purpose, "intentional": intentional,
            "date": folder[5:10], "commits": commits, "devices": sorted({device_of(r["summary"]) for r in group}),
            **{k: g[k] for k in ("sessions", "executed", "passed", "flaky", "bad", "xfailed")},
        })
    return {
        "total": {k: total[k] for k in ("sessions", "executed", "passed", "flaky", "bad", "xfailed", "skipped", "reruns")},
        "by_device": {d: {k: c[k] for k in ("sessions", "executed", "passed", "flaky", "bad", "xfailed")} for d, c in sorted(by_device.items())},
        "groups": groups, "problems": problems, "missing": missing,
        "first": min((g["date"] for g in groups), default=""), "last": max((g["date"] for g in groups), default=""),
    }


def skipped_runs(groups):
    """합계에서 뺀 실행을 이름별 횟수로. 예: '앱을 일부러 죽인 실행 2회, 결함 주입 실행 24회'"""
    count = Counter()
    for g in groups:
        count[INTENTIONAL_NAME.get(g["folder"], g["purpose"])] += g["sessions"]
    return ", ".join(f"{name} {n}회" for name, n in count.items())


def markdown(h):
    t = h["total"]
    intentional = [g for g in h["groups"] if g["intentional"]]
    lines = [
        "# 전체 실행 기록",
        "",
        f"[근거 자료](evidence/README.md)에 결과 파일(원자료)이 남은 E2E 실행을 모두 합친 기록입니다(2026년 {h['first']}부터 {h['last']}까지). "
        "`ivi-tests/tools/run_history.py`가 결과 파일에서 다시 세어 만듭니다. 결과 파일을 남기기 전인 11-13부터 11-17까지의 실행은 들어 있지 않습니다.",
        "",
        "실패, 오류, 재시도 후 통과는 하나도 빼지 않고 원인과 함께 적었습니다. "
        + (f"다만 판정 기능이나 테스트의 탐지력을 확인하려고 일부러 실패를 만든 실행({skipped_runs(intentional)})은 합계에서 빼고 아래 표에만 둡니다. " if intentional else "")
        + "세션을 일부러 끊은 실행은 그 상황에서도 끝까지 통과하는지 본 것이라 합계에 넣었습니다.",
        "",
        "## 합계",
        "",
        "| 실행 | 테스트 실행 | 통과 | 재시도 후 통과 | 실패·오류 | 알려진 결함 |",
        "|---|---|---|---|---|---|",
        f"| {t['sessions']}회 | {t['executed']:,}건 | {t['passed']:,}건 | {t['flaky']}건 | {t['bad']}건 | {t['xfailed']}건 |",
        "",
        "- 테스트 실행은 건너뜀을 뺀 수입니다. 알려진 결함은 플랫폼 결함 하나(#21)를 `xfail(strict=True)`로 걸어 둔 것입니다.",
        "- 실패·오류와 재시도 후 통과의 원인은 아래 '나온 곳' 표에 있습니다.",
        "",
        "## 기기별",
        "",
        "| 기기 | 실행 | 테스트 실행 | 통과 | 재시도 후 통과 | 실패·오류 |",
        "|---|---|---|---|---|---|",
    ]
    for d, c in h["by_device"].items():
        lines.append(f"| {d} | {c['sessions']}회 | {c['executed']:,}건 | {c['passed']:,}건 | {c['flaky']}건 | {c['bad']}건 |")
    lines += ["", "## 날짜별", "", "| 날짜 | 무엇을 확인했나 | 코드 | 기기 | 테스트 실행 | 실패·오류 | 재시도 후 통과 |", "|---|---|---|---|---|---|---|"]
    for g in h["groups"]:
        code = ", ".join(f"`{c}`" for c in g["commits"]) or "기록 없음"
        lines.append(f"| {g['date']} | [{g['purpose']}](evidence/{g['folder'].split('/')[0]}/README.md) | {code} | {', '.join(g['devices'])} | {g['executed']:,}건 | {g['bad']}건 | {g['flaky']}건 |")
    lines += ["", "## 실패, 오류, 재시도 후 통과가 나온 곳", "", "| 날짜 | 실행 | 기기 | 테스트 | 결과 | 원인 |", "|---|---|---|---|---|---|"]
    for p in h["problems"]:
        why = (f"**{p['kind']}** " if p["kind"] else "") + p["why"]
        lines.append(f"| {p['date']} | `{p['run_id']}` | {p['device']} | `{p['test']}` | {p['outcome']} | {why} |")
    lines += ["", "다시 만드는 방법 (`ivi-tests`에서):", "", "```powershell", ".venv\\Scripts\\python tools\\run_history.py", "```", ""]
    return "\n".join(lines)


def render(h):
    """(docs/run-history.md 내용, site/results/history.json 내용)"""
    return markdown(h), json.dumps({k: v for k, v in h.items() if k != "missing"}, ensure_ascii=False, indent=1) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", type=Path, default=REPO, help="저장소 위치 (기본: 이 파일의 두 단계 위)")
    parser.add_argument("--check", action="store_true", help="만들지 않고, 지금 파일과 다르거나 원인·목적이 빠졌으면 실패")
    args = parser.parse_args()
    evidence = args.repo / "docs" / "evidence"
    h = summarize(load(evidence))
    md, js = render(h)
    md_path, js_path = args.repo / "docs" / "run-history.md", args.repo / "site" / "results" / "history.json"
    problems = [f"목적이 없는 폴더: {f}" for f in h["missing"]["purpose"]] + [f"원인이 없는 결과: {c}" for c in h["missing"]["cause"]]
    if args.check:
        for path, text in ((md_path, md), (js_path, js)):
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                problems.append(f"{path.relative_to(args.repo)}가 결과 파일과 다릅니다. tools/run_history.py 로 다시 만드세요.")
        for p in problems:
            print(f"✗ {p}")
        sys.exit(1 if problems else 0)
    md_path.write_text(md, encoding="utf-8", newline="\n")
    js_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(js, encoding="utf-8", newline="\n")
    t = h["total"]
    print(f"실행 {t['sessions']}회, 테스트 {t['executed']}건: 통과 {t['passed']}, 재시도 후 통과 {t['flaky']}, 실패·오류 {t['bad']}, 알려진 결함 {t['xfailed']}")
    for p in problems:
        print(f"주의: {p}")


if __name__ == "__main__":
    main()
