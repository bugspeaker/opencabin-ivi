"""결함 주입 실험의 결과 파일을 결함마다 다시 세어 탐지 여부를 낸다.

    python tools/fault_report.py ../docs/evidence/2026-11-25-fault-injection
    python tools/fault_report.py <폴더> --json        # 기계가 읽을 꼴

폴더 구성
  faults.json  결함 목록. 대조군은 id "F00" 이다.
               [{"id": "F01", "area": "공조", "title": "...", "devices": ["aaos"]}, ...]
               devices 는 그 결함이 지나가는 경로의 기기 종류다 (aaos = CarVehicleDataSource, mock = 태블릿 Mock)
  runs/        결과 파일 (conftest 의 Recorder 가 만든 그대로).
               run id 는 fi-<결함>-<기기 종류>[-<접미>] 다. 접미가 없는 실행이 처음 실행(테스트 그대로)이고,
               접미가 있는 실행은 빈 곳을 막는 테스트를 더한 뒤 다시 확인한 것 같은 따로 세는 실행이다.

판정 (실행 하나마다)
  탐지     재시도 뒤에도 실패(failed·error)한 테스트가 하나 이상 있고, 그 테스트가 같은 기기의 대조군에서 통과했다
  흔들림   최종 실패는 없지만 재시도로 통과(flaky)한 테스트가 있다. Release 게이트는 막지만 탐지로 세지 않는다
  놓침     실패도 흔들림도 없다
  무효     실행이 끝나지 않았거나(pytest 종료 코드 2 이상), 설치된 APK 버전에 그 결함 id 가 없다
대조군에서 실패한 테스트는 탐지 근거에서 뺀다 (환경 문제를 결함 탐지로 세지 않게).
대조군은 결함이 없는 빌드면 되므로 버전 이름을 보지 않는다 (태블릿은 설치 승인을 줄이려고 이미 설치된 main 빌드로 돌렸다).
'N개 중 M개'는 기기 종류마다 그 기기에 해당하는 결함의 처음 실행만 센다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CONTROL = "F00"
FAILED = ("failed", "error")
RUN_ID = re.compile(r"^fi-(F\d+)-(aaos|mock)(?:-(.+))?$")
KIND_LABEL = {"aaos": "AAOS 에뮬레이터", "mock": "태블릿(Mock)"}
VERDICTS = ("탐지", "흔들림", "놓침", "무효")
SUFFIX_LABEL = {"gap": "보강 테스트로 다시"}  # 빈 곳을 막는 테스트를 더한 뒤 다시 확인한 실행


def load(folder):
    folder = Path(folder)
    faults = json.loads((folder / "faults.json").read_text(encoding="utf-8"))
    runs = []
    for path in sorted((folder / "runs").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found = RUN_ID.match(data["summary"]["run_id"])
        if found:
            runs.append({"fault": found[1], "kind": found[2], "suffix": found[3] or "", "file": path.name, **data})
    return faults, runs


def failed_tests(run):
    return [t for t in run["tests"] if t["outcome"] in FAILED]


def judge(run, control):
    """(판정, 근거 테스트 목록). control 은 같은 기기 대조군 실행(없으면 None)."""
    summary = run["summary"]
    version = (summary.get("app") or {}).get("version", "")
    wrong_apk = run["fault"] != CONTROL and f"fi.{run['fault']}" not in version
    if summary.get("exitstatus", 0) >= 2 or wrong_apk:
        return "무효", []
    excluded = {t["nodeid"] for t in failed_tests(control)} if control and run is not control else set()
    caught = [t for t in failed_tests(run) if t["nodeid"] not in excluded]
    if caught:
        return "탐지", caught
    flaky = [t for t in run["tests"] if t["outcome"] == "flaky"]
    return ("흔들림", flaky) if flaky else ("놓침", [])


def evaluate(faults, runs):
    controls = {r["kind"]: r for r in runs if r["fault"] == CONTROL and not r["suffix"]}
    titles = {f["id"]: f for f in faults}
    rows = []
    for run in sorted(runs, key=lambda r: (r["fault"], r["kind"], r["suffix"])):
        verdict, evidence = judge(run, controls.get(run["kind"]))
        rows.append({
            "fault": run["fault"], "kind": run["kind"], "suffix": run["suffix"], "file": run["file"],
            "title": titles.get(run["fault"], {}).get("title", ""), "verdict": verdict,
            "counts": run["summary"].get("counts", {}), "app": (run["summary"].get("app") or {}).get("version", ""),
            "tests": [{"nodeid": t["nodeid"], "outcome": t["outcome"], "message": (t.get("message") or "").splitlines()[0][:160]}
                      for t in evidence],
        })
    totals = {}
    for kind in KIND_LABEL:
        applicable = [f["id"] for f in faults if f["id"] != CONTROL and kind in f.get("devices", [])]
        first = {r["fault"]: r for r in rows if r["kind"] == kind and not r["suffix"] and r["fault"] in applicable}
        if not first:
            continue
        totals[kind] = {
            "applicable": len(applicable), "ran": len(first),
            "caught": sorted(fid for fid, r in first.items() if r["verdict"] == "탐지"),
            "missed": sorted(fid for fid, r in first.items() if r["verdict"] != "탐지"),
            "not_run": sorted(set(applicable) - set(first)),
        }
    control_ok = {kind: (r["verdict"] in ("놓침",)) for kind, r in
                  ((r["kind"], r) for r in rows if r["fault"] == CONTROL and not r["suffix"])}
    return {"rows": rows, "totals": totals, "control_clean": control_ok}


def markdown(result):
    lines = ["| 결함 | 기기 | 실행 | 판정 | 실패한 테스트 |", "|---|---|---|---|---|"]
    for row in result["rows"]:
        control = row["fault"] == CONTROL
        name = "F00 (대조군)" if control else row["fault"]
        verdict = "실패 없음" if control and row["verdict"] == "놓침" else row["verdict"]
        tests = "<br>".join(t["nodeid"].split("::")[-1] for t in row["tests"]) or "-"
        run = SUFFIX_LABEL.get(row["suffix"], row["suffix"]) or "처음"
        lines.append(f"| {name} | {KIND_LABEL[row['kind']]} | {run} | {verdict} | {tests} |")
    lines.append("")
    for kind, total in result["totals"].items():
        line = f"{KIND_LABEL[kind]}: 해당 결함 {total['applicable']}개 중 {total['ran']}개 실행, {len(total['caught'])}개 탐지"
        if total["missed"]:
            line += f" (놓침·흔들림: {', '.join(total['missed'])})"
        if total["not_run"]:
            line += f" (실행 안 함: {', '.join(total['not_run'])})"
        lines.append(line)
    for kind, clean in result["control_clean"].items():
        if not clean:
            lines.append(f"주의: {KIND_LABEL[kind]} 대조군에 실패나 흔들림이 있습니다. 그 테스트는 탐지 근거에서 뺐습니다.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    faults, runs = load(args.folder)
    if not runs:
        sys.exit(f"결과 파일이 없습니다: {Path(args.folder) / 'runs'}")
    result = evaluate(faults, runs)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else markdown(result))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
