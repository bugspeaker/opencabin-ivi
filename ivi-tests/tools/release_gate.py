"""Release 게이트: 릴리스 후보 반복 실행의 결과로 docs/portfolio.md 4-1 의 다섯 조건을 확인한다.

    python tools/release_gate.py --last 3                          # reports/runs 의 최근 3회
    python tools/release_gate.py --runs 20261118-195509-r1 20261118-200531-r2
    python tools/release_gate.py --runs-dir ../docs/evidence/2026-11-18-repeat5/runs --last 5
    python tools/release_gate.py --since 20261119-030000 --expect 3   # CI: 이번 job 이 시작한 뒤의 실행만

조건 (하나라도 어기면 이유를 출력하고 종료 코드 1)
  1. 모든 회차, 모든 기기에서 failed·error 0. 회차마다 모든 기기의 결과 파일이 있어야 한다
  2. 모든 회차에서 flaky 0. 비교 기준(직전 Nightly 등)을 따로 두지 않고, 이번 Release 반복 안에서
     재시도로 통과한 테스트가 하나도 없어야 한다
  3. 격리 목록(quarantine.txt)의 모든 줄에 이유, 등록일, 해제 조건이 있고 MAX_ENTRIES(2)줄 이하
  4. 요구사항 추적 누락 0 (tools/trace_report.check, unit job 과 같은 검사)
  5. xfailed 가 된 테스트 = 알려진 결함 목록(known_defects.txt).
     목록에 없는 xfail, 목록에 있는데 xfailed 가 아니거나 실행되지 않은 테스트가 있으면 막는다
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ivi import quarantine  # noqa: E402
from tools import trace_report  # noqa: E402

RUNS_DIR = ROOT / "reports" / "runs"
QUARANTINE_FILE = ROOT / "quarantine.txt"
KNOWN_DEFECTS_FILE = ROOT / "known_defects.txt"


@dataclass(frozen=True)
class KnownDefect:
    pattern: str
    defect: str
    reason: str

    def matches(self, nodeid):
        return nodeid == self.pattern or nodeid.startswith(self.pattern + "[") or nodeid.startswith(self.pattern + "::")


@dataclass
class Check:
    number: int
    title: str
    problems: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.problems


def parse_known_defects(text):
    defects = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3 or not all(parts):
            raise ValueError(f"known_defects.txt {number}번째 줄: '<nodeid> | <결함 번호> | <사유>' 형식이 아니다: {raw!r}")
        defects.append(KnownDefect(*parts))
    return defects


def load_runs(runs_dir):
    """run id → [실행 결과 (기기 하나)] (reports/runs/<run>-<serial>.json, conftest 의 Recorder 가 쓴 파일)."""
    runs = {}
    for path in sorted(Path(runs_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        runs.setdefault(data["summary"]["run_id"], []).append(data)
    return runs


def pick(runs, run_ids=None, last=0, since=""):
    """run_ids 를 주면 그것만. 아니면 since(run id 앞의 시각 'YYYYMMDD-HHMMSS') 이후 가운데 최근 last 회."""
    if run_ids:
        missing = [run_id for run_id in run_ids if run_id not in runs]
        if missing:
            raise SystemExit(f"결과가 없는 run id: {', '.join(missing)}")
        return {run_id: runs[run_id] for run_id in run_ids}
    chosen = [run_id for run_id in sorted(runs) if run_id >= since]
    chosen = chosen[-last:] if last else chosen
    return {run_id: runs[run_id] for run_id in chosen}


def evaluate(runs, quarantine_text, known_text, trace, expected_rounds=None):
    """runs: run id → [실행 결과]. trace: trace_report.check 의 (테스트 없는 요구사항, 요구사항 없는 테스트, 없는 ID).
    expected_rounds: 반복 횟수. 결과가 이보다 적으면(중간에 멈춘 회차) 막는다."""
    serials = sorted({run["summary"]["serial"] for results in runs.values() for run in results})
    checks = [Check(1, "모든 회차, 모든 기기 failed·error 0"), Check(2, "이번 반복 안에서 flaky 0"),
              Check(3, f"격리 목록: 네 칸 모두 있고 {quarantine.MAX_ENTRIES}줄 이하"),
              Check(4, "요구사항 추적 누락 0"), Check(5, "xfailed = 알려진 결함 목록")]
    gate, flaky, quarantine_check, trace_check, known_check = checks

    if not runs:
        gate.problems.append("확인할 실행 결과가 없다")
    elif expected_rounds and len(runs) != expected_rounds:
        gate.problems.append(f"반복 {expected_rounds}회 가운데 결과가 있는 회차는 {len(runs)}회")
    for run_id, results in runs.items():
        present = {run["summary"]["serial"] for run in results}
        gate.problems += [f"{run_id} {serial}: 결과 파일 없음" for serial in serials if serial not in present]
        for run in results:
            serial = run["summary"]["serial"]
            for test in run["tests"]:
                if test["outcome"] in ("failed", "error"):
                    gate.problems.append(f"{run_id} {serial} {test['nodeid']}: {test['outcome']}")
                elif test["outcome"] == "flaky":
                    flaky.problems.append(f"{run_id} {serial} {test['nodeid']}: 재시도 {test.get('reruns', 1)}번 뒤 통과")

    try:
        entries = quarantine.parse(quarantine_text)
        if len(entries) > quarantine.MAX_ENTRIES:
            quarantine_check.problems.append(f"격리 {len(entries)}개 (최대 {quarantine.MAX_ENTRIES}개): "
                                             + ", ".join(entry.pattern for entry in entries))
    except ValueError as err:
        quarantine_check.problems.append(str(err))

    untested, untraced, unknown = trace
    trace_check.problems += [f"테스트가 없는 요구사항: {req}" for req in untested]
    trace_check.problems += [f"요구사항이 없는 테스트: {name}" for name in untraced]
    trace_check.problems += [f"없는 요구사항 ID: {item}" for item in unknown]

    try:
        defects = parse_known_defects(known_text)
    except ValueError as err:
        known_check.problems.append(str(err))
        defects = []
    seen = {}  # nodeid → 실행된 판정들 (건너뜀 제외)
    for results in runs.values():
        for run in results:
            for test in run["tests"]:
                if test["outcome"] != "skipped":
                    seen.setdefault(test["nodeid"], set()).add(test["outcome"])
    for nodeid, outcomes in sorted(seen.items()):
        defect = next((d for d in defects if d.matches(nodeid)), None)
        if "xfailed" in outcomes and defect is None:
            known_check.problems.append(f"목록에 없는 xfail: {nodeid}")
        if defect is not None and outcomes != {"xfailed"}:
            others = ", ".join(sorted(outcomes - {"xfailed"}))
            known_check.problems.append(f"알려진 결함 {defect.defect}번이 xfailed 가 아님 ({others}): {nodeid}. "
                                        "고쳐졌다면 xfail 과 목록에서 함께 지운다")
    for defect in defects:
        if not any(defect.matches(nodeid) for nodeid in seen):
            known_check.problems.append(f"알려진 결함 {defect.defect}번 테스트가 실행되지 않음: {defect.pattern}")
    return checks


def render(runs, checks):
    serials = sorted({run["summary"]["serial"] for results in runs.values() for run in results})
    lines = [f"Release 게이트: {len(runs)}회 ({', '.join(runs)}), 기기 {len(serials)}대 ({', '.join(serials)})"]
    for check in checks:
        lines.append(f"  {'✓' if check.ok else '✗'} {check.number}. {check.title}")
        lines += [f"       - {problem}" for problem in check.problems[:20]]
        if len(check.problems) > 20:
            lines.append(f"       … 외 {len(check.problems) - 20}건")
    failed = [str(check.number) for check in checks if not check.ok]
    lines.append(f"결과: {'통과' if not failed else '막음 (조건 ' + ', '.join(failed) + ')'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", help="확인할 run id. 비우면 --last")
    parser.add_argument("--last", type=int, default=0, help="최근 N회 (run id 순). 0 이면 전부")
    parser.add_argument("--since", default="", help="이 시각(YYYYMMDD-HHMMSS) 이후에 시작한 실행만. CI 에서 이번 job 의 실행만 고를 때")
    parser.add_argument("--expect", type=int, help="반복 횟수. 결과가 있는 회차가 이보다 적으면 막는다")
    parser.add_argument("--runs-dir", default=str(RUNS_DIR))
    parser.add_argument("--quarantine", default=str(QUARANTINE_FILE))
    parser.add_argument("--known-defects", default=str(KNOWN_DEFECTS_FILE))
    args = parser.parse_args(argv)

    runs = pick(load_runs(args.runs_dir), args.runs, args.last, args.since)
    read = lambda path: Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""  # noqa: E731
    trace = trace_report.check(trace_report.read_requirements(), trace_report.read_test_reqs())
    checks = evaluate(runs, read(args.quarantine), read(args.known_defects), trace, args.expect)
    sys.stdout.reconfigure(encoding="utf-8")
    print(render(runs, checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
