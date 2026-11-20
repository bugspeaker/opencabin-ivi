"""Release 게이트: 릴리스 후보 반복 실행의 결과로 docs/portfolio.md 4-1 의 여섯 조건을 확인한다.

    python tools/release_gate.py --last 3                          # reports/runs 의 최근 3회
    python tools/release_gate.py --runs 20261118-195509-r1 20261118-200531-r2
    python tools/release_gate.py --runs-dir ../docs/evidence/2026-11-18-repeat5/runs --last 5
    python tools/release_gate.py --since 20261119-030000 --expect 3 --commit <sha>   # CI: 이번 job 의 실행만, 이 커밋으로

'실패한 테스트가 없다'와 '정한 검증을 끝까지 했다'는 다르다. 조건 1 이 뒤쪽을 본다. 기기 하나가 통째로 빠지거나,
-m smoke 로 일부만 돌렸거나, 중간에 멈춘 실행은 failed 가 0 이어도 막는다.

조건 (하나라도 어기면 이유를 출력하고 종료 코드 1)
  1. 실행 완전성. 회차마다 필수 기기 종류(기본 aaos, mock)의 결과가 모두 있고, 각 결과에 지금 코드에서 수집한
     테스트(tools/collect_tests.py)가 빠짐없이 판정과 함께 있으며, pytest 종료 코드가 0 이다.
     건너뜀은 기기 전용 마커(태블릿의 aaos, AAOS 의 tablet)로 정해 둔 것만 허용한다. --commit 을 주면 모든 결과가
     그 커밋에서, 커밋하지 않은 변경 없이 돈 것이어야 한다
  2. 모든 회차, 모든 기기에서 failed·error·xpassed 0
  3. 모든 회차에서 flaky 0. 비교 기준(직전 Nightly 등)을 따로 두지 않고, 이번 Release 반복 안에서
     재시도로 통과한 테스트가 하나도 없어야 한다
  4. 격리 목록(quarantine.txt)의 모든 줄에 이유, 등록일, 해제 조건이 있고 MAX_ENTRIES(2)줄 이하
  5. 요구사항 추적 누락 0 (tools/trace_report.check, unit job 과 같은 검사)
  6. xfailed 가 된 테스트 = 알려진 결함 목록(known_defects.txt).
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
from ivi.results import EXIT_CODES, code_version  # noqa: E402
from tools import collect_tests, trace_report  # noqa: E402

RUNS_DIR = ROOT / "reports" / "runs"
QUARANTINE_FILE = ROOT / "quarantine.txt"
KNOWN_DEFECTS_FILE = ROOT / "known_defects.txt"
REQUIRED_KINDS = ("aaos", "mock")
# 기기 종류 → 그 기기에서 건너뛰어도 되는 테스트의 마커 (conftest 가 이 마커로 건너뛴다). 그 밖의 건너뜀은 검증 누락이다
DEVICE_ONLY_SKIP = {"aaos": "tablet", "mock": "aaos"}
OUTCOMES = {"passed", "flaky", "failed", "error", "skipped", "xfailed", "xpassed", "quarantined"}
EXAMPLES = 3  # 문제 한 줄에 보여 줄 테스트 이름 수


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
    notes: list = field(default_factory=list)  # 막지는 않지만 읽는 사람이 알아야 할 것 (예: 옛 형식 결과 파일)

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


def _examples(nodeids):
    nodeids = sorted(nodeids)
    more = f" 외 {len(nodeids) - EXAMPLES}개" if len(nodeids) > EXAMPLES else ""
    return ", ".join(nodeids[:EXAMPLES]) + more


def check_completeness(check, runs, inventory, expected_rounds, kinds, commit):
    """조건 1. 결과 파일에 적힌 판정이 아니라 '돌았어야 하는 것'을 기준으로 본다."""
    if not runs:
        check.problems.append("확인할 실행 결과가 없다")
        return
    if expected_rounds and len(runs) != expected_rounds:
        check.problems.append(f"반복 {expected_rounds}회 가운데 결과가 있는 회차는 {len(runs)}회")
    legacy_exit, legacy_commit, commits = 0, 0, set()
    for run_id, results in runs.items():
        present = {run["summary"].get("kind") for run in results}
        check.problems += [f"{run_id} {kind}: 결과 파일 없음 (필수 기기)" for kind in kinds if kind not in present]
        for run in results:
            summary, label = run["summary"], f"{run_id} {run['summary']['serial']}"
            outcomes = {test["nodeid"]: test["outcome"] for test in run["tests"]}
            failed_inside = any(outcome in ("failed", "error") for outcome in outcomes.values())

            if "exitstatus" not in summary:
                legacy_exit += 1
            elif summary["exitstatus"] != 0 and not (summary["exitstatus"] == 1 and failed_inside):
                code = summary["exitstatus"]
                check.problems.append(f"{label}: pytest 종료 코드 {code} ({EXIT_CODES.get(code, '알 수 없음')})")

            unfinished = [nodeid for nodeid, outcome in outcomes.items() if outcome not in OUTCOMES]
            if unfinished:
                check.problems.append(f"{label}: 판정 없이 끝난 테스트 {len(unfinished)}개 ({_examples(unfinished)})")

            missing = set(inventory) - set(outcomes)
            if missing:
                check.problems.append(f"{label}: 지금 코드의 테스트 {len(missing)}개가 돌지 않음 ({_examples(missing)})")
            extra = set(outcomes) - set(inventory)
            if extra:
                check.problems.append(f"{label}: 지금 코드에 없는 테스트 {len(extra)}개의 결과. 다른 코드로 돈 결과다 "
                                      f"({_examples(extra)})")
            allowed_skip = DEVICE_ONLY_SKIP.get(summary.get("kind"))
            unexpected = [nodeid for nodeid, outcome in outcomes.items()
                          if outcome == "skipped" and allowed_skip not in inventory.get(nodeid, set())]
            if unexpected:
                check.problems.append(f"{label}: 기기 전용이 아닌데 건너뛴 테스트 {len(unexpected)}개 ({_examples(unexpected)})")

            if not summary.get("commit"):
                legacy_commit += 1
                continue
            commits.add(summary["commit"])
            if summary.get("dirty"):
                check.problems.append(f"{label}: 커밋하지 않은 변경이 있는 코드로 돈 결과 ({summary['commit'][:7]}+)")
            if commit and not summary["commit"].startswith(commit):
                check.problems.append(f"{label}: 커밋 {summary['commit'][:7]} 에서 돈 결과 (확인할 커밋 {commit[:7]})")
    if len(commits) > 1:
        check.problems.append("회차·기기마다 다른 커밋에서 돈 결과가 섞였다: " + ", ".join(sorted(c[:7] for c in commits)))
    if legacy_exit:
        check.notes.append(f"종료 코드가 없는 결과 파일 {legacy_exit}개 (2026-11-19 이전 형식). "
                           "지금 코드의 테스트 목록과 하나씩 맞춰 끝까지 돌았는지 본다")
    if legacy_commit:
        message = f"커밋이 적히지 않은 결과 파일 {legacy_commit}개 (2026-11-19 이전 형식)"
        if commit:
            check.problems.append(message + f". 커밋 {commit[:7]} 에서 돈 결과인지 확인할 수 없다")
        else:
            check.notes.append(message + ". 어느 커밋의 결과인지는 실행 시각과 커밋 기록으로만 맞출 수 있다")


def evaluate(runs, quarantine_text, known_text, trace, expected_rounds=None, inventory=None,
             kinds=REQUIRED_KINDS, commit=None):
    """runs: run id → [실행 결과]. trace: trace_report.check 의 (테스트 없는 요구사항, 요구사항 없는 테스트, 없는 ID).
    inventory: 지금 코드의 테스트 nodeid → 마커 이름 집합 (tools/collect_tests.collect).
    expected_rounds: 반복 횟수. 결과가 이보다 적으면(중간에 멈춘 회차) 막는다.
    kinds: 회차마다 반드시 있어야 하는 기기 종류. commit: 결과가 모두 이 커밋에서 돈 것이어야 한다."""
    checks = [Check(1, "실행 완전성: 필수 기기 모두, 지금 코드의 테스트 전부, 정상 종료"),
              Check(2, "모든 회차, 모든 기기 failed·error 0"), Check(3, "이번 반복 안에서 flaky 0"),
              Check(4, f"격리 목록: 네 칸 모두 있고 {quarantine.MAX_ENTRIES}줄 이하"),
              Check(5, "요구사항 추적 누락 0"), Check(6, "xfailed = 알려진 결함 목록")]
    complete, gate, flaky, quarantine_check, trace_check, known_check = checks

    if inventory is None:
        complete.problems.append("지금 코드의 테스트 목록이 없어 무엇이 돌았어야 하는지 확인할 수 없다")
        inventory = {}
    check_completeness(complete, runs, inventory, expected_rounds, kinds, commit)
    for run_id, results in runs.items():
        for run in results:
            serial = run["summary"]["serial"]
            for test in run["tests"]:
                if test["outcome"] in ("failed", "error", "xpassed"):
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
            others = ", ".join(sorted(str(o) for o in outcomes - {"xfailed"}))
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
        lines += [f"       참고: {note}" for note in check.notes]
    failed = [str(check.number) for check in checks if not check.ok]
    lines.append(f"결과: {'통과' if not failed else '막음 (조건 ' + ', '.join(failed) + ')'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", help="확인할 run id. 비우면 --last")
    parser.add_argument("--last", type=int, default=0, help="최근 N회 (run id 순). 0 이면 전부")
    parser.add_argument("--since", default="", help="이 시각(YYYYMMDD-HHMMSS) 이후에 시작한 실행만. CI 에서 이번 job 의 실행만 고를 때")
    parser.add_argument("--expect", type=int, help="반복 횟수. 결과가 있는 회차가 이보다 적으면 막는다")
    parser.add_argument("--kinds", default=",".join(REQUIRED_KINDS), help="회차마다 꼭 있어야 하는 기기 종류 (쉼표)")
    parser.add_argument("--commit", help="결과가 모두 이 커밋에서 돈 것이어야 한다. HEAD 는 지금 체크아웃한 커밋")
    parser.add_argument("--runs-dir", default=str(RUNS_DIR))
    parser.add_argument("--quarantine", default=str(QUARANTINE_FILE))
    parser.add_argument("--known-defects", default=str(KNOWN_DEFECTS_FILE))
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")
    runs = pick(load_runs(args.runs_dir), args.runs, args.last, args.since)
    read = lambda path: Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""  # noqa: E731
    trace = trace_report.check(trace_report.read_requirements(), trace_report.read_test_reqs())
    try:
        inventory = collect_tests.collect()
    except RuntimeError as err:
        print(f"Release 게이트: {err}\n결과: 막음 (무엇이 돌았어야 하는지 정할 수 없다)")
        return 1
    commit = code_version(ROOT)["commit"] if args.commit == "HEAD" else args.commit
    kinds = tuple(kind.strip() for kind in args.kinds.split(",") if kind.strip())
    checks = evaluate(runs, read(args.quarantine), read(args.known_defects), trace, args.expect,
                      inventory=inventory, kinds=kinds, commit=commit)
    print(render(runs, checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
