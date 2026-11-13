"""누적 실행 기록(reports/history/results.jsonl)으로 flaky 통계를 낸다.

    python tools/flaky_report.py                      # 전체 기록
    python tools/flaky_report.py --last 10            # 기기별 최근 10회 실행만
    python tools/flaky_report.py --out reports/flaky-report.md

불안정 = flaky(재시도에서 통과) + failed/error. 판단 기준
  격리 후보: 최근 실행 중 불안정 비율이 --threshold 이상 (실행 --min-runs 회 이상)
  해제 후보: 격리 중인 테스트가 최근 --release-streak 회 연속 실제 통과
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ivi import quarantine  # noqa: E402

UNSTABLE = ("flaky", "failed", "error")
COUNTED = ("passed", "flaky", "failed", "error", "quarantined")


def load(path):
    rows = []
    with Path(path).open(encoding="utf-8") as src:
        for line in src:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def keep_last_runs(rows, last):
    """기기 종류별로 최근 last 번의 실행만 남긴다."""
    if not last:
        return rows
    runs_by_kind = defaultdict(list)
    for row in rows:
        key = (row["run_id"], row["serial"])
        if key not in runs_by_kind[row["kind"]]:
            runs_by_kind[row["kind"]].append(key)
    keep = {key for keys in runs_by_kind.values() for key in sorted(keys)[-last:]}
    return [row for row in rows if (row["run_id"], row["serial"]) in keep]


def p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def analyze(rows, threshold=0.1, min_runs=5, release_streak=20, quarantined=()):
    tests = defaultdict(list)
    runs = defaultdict(dict)
    for row in sorted(rows, key=lambda r: (r["time"], r["run_id"])):
        tests[(row["kind"], row["nodeid"])].append(row)
        run = runs[row["kind"]].setdefault((row["run_id"], row["serial"]), {"gate": "pass", "duration": 0.0})
        run["duration"] += row["duration"]
        if row["outcome"] in ("failed", "error"):
            run["gate"] = "fail"

    stats = []
    for (kind, nodeid), history in tests.items():
        counted = [r for r in history if r["outcome"] in COUNTED]
        if not counted:
            continue
        outcomes = [r["outcome"] for r in counted]
        unstable = sum(o in UNSTABLE for o in outcomes)
        durations = [r["duration"] for r in counted]
        streak = 0
        for r in reversed(counted):
            ok = r["outcome"] == "passed" or r.get("quarantine_result") == "passed"
            if not ok:
                break
            streak += 1
        is_quarantined = any(entry.matches(nodeid) for entry in quarantined) or counted[-1]["outcome"] == "quarantined"
        stats.append({
            "kind": kind,
            "nodeid": nodeid,
            "runs": len(counted),
            "passed": outcomes.count("passed"),
            "flaky": outcomes.count("flaky"),
            "failed": outcomes.count("failed") + outcomes.count("error"),
            "unstable_rate": unstable / len(counted),
            "avg": sum(durations) / len(durations),
            "p95": p95(durations),
            "relaunches": sum(r.get("relaunches", 0) for r in counted),
            "infra_retries": sum(r.get("infra_retries", 0) for r in counted),
            "streak": streak,
            "quarantined": is_quarantined,
            "last_error": next((r.get("first_error") or r.get("message") for r in reversed(counted)
                                if r["outcome"] in UNSTABLE), ""),
        })

    candidates = [s for s in stats if not s["quarantined"] and s["runs"] >= min_runs and s["unstable_rate"] >= threshold]
    releases = [s for s in stats if s["quarantined"] and s["streak"] >= release_streak]
    run_summary = {
        kind: {
            "runs": len(items),
            "gate_pass": sum(1 for r in items.values() if r["gate"] == "pass"),
            "avg_duration": sum(r["duration"] for r in items.values()) / len(items),
        }
        for kind, items in runs.items()
    }
    return run_summary, stats, candidates, releases


def render(run_summary, stats, candidates, releases, threshold, min_runs, release_streak):
    lines = ["# Flaky 리포트", ""]
    lines += ["## 실행 요약", "", "| 기기 | 실행 | 게이트 통과 | 평균 테스트 시간 합 |", "|---|---|---|---|"]
    for kind, s in sorted(run_summary.items()):
        lines.append(f"| {kind} | {s['runs']} | {s['gate_pass']}/{s['runs']} ({s['gate_pass'] / s['runs']:.0%}) | {s['avg_duration']:.0f}s |")

    unstable = sorted((s for s in stats if s["unstable_rate"] > 0 or s["relaunches"] or s["infra_retries"]),
                      key=lambda s: (-s["unstable_rate"], -s["relaunches"], s["nodeid"]))
    lines += ["", "## 불안정 테스트", ""]
    if unstable:
        lines += ["| 기기 | 테스트 | 실행 | flaky | 실패 | 불안정 | 앱 재실행 | 신호 재시도 | 평균/p95 | 마지막 원인 |", "|---|---|---|---|---|---|---|---|---|---|"]
        for s in unstable:
            reason = s["last_error"].splitlines()[0][:80] if s["last_error"] else ""
            lines.append(f"| {s['kind']} | `{s['nodeid']}` | {s['runs']} | {s['flaky']} | {s['failed']} | {s['unstable_rate']:.0%} | "
                         f"{s['relaunches']} | {s['infra_retries']} | {s['avg']:.1f}/{s['p95']:.1f}s | {reason} |")
    else:
        lines.append("없음 (모든 테스트가 매번 한 번에 통과)")

    lines += ["", f"## 격리 후보 (불안정 {threshold:.0%} 이상, {min_runs}회 이상 실행)", ""]
    lines += [f"- `{s['nodeid']}` ({s['kind']}, {s['unstable_rate']:.0%})" for s in candidates] or ["없음"]
    lines += ["", f"## 격리 해제 후보 (최근 {release_streak}회 연속 통과)", ""]
    lines += [f"- `{s['nodeid']}` ({s['kind']}, 연속 {s['streak']}회)" for s in releases] or ["없음"]

    slow = sorted(stats, key=lambda s: -s["p95"])[:5]
    lines += ["", "## 느린 테스트 (p95 상위 5)", "", "| 기기 | 테스트 | 평균 | p95 |", "|---|---|---|---|"]
    lines += [f"| {s['kind']} | `{s['nodeid']}` | {s['avg']:.1f}s | {s['p95']:.1f}s |" for s in slow]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", default=str(ROOT / "reports" / "history" / "results.jsonl"))
    parser.add_argument("--last", type=int, default=0, help="기기 종류별 최근 N회 실행만")
    parser.add_argument("--threshold", type=float, default=0.1)
    parser.add_argument("--min-runs", type=int, default=5)
    parser.add_argument("--release-streak", type=int, default=20)
    parser.add_argument("--out", help="마크다운 파일로 저장")
    args = parser.parse_args(argv)

    rows = keep_last_runs(load(args.history), args.last)
    result = analyze(rows, args.threshold, args.min_runs, args.release_streak, quarantine.load(ROOT / "quarantine.txt"))
    text = render(*result, args.threshold, args.min_runs, args.release_streak)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 1 if result[2] else 0  # 격리 후보가 있으면 1 (CI 에서 알림용)


if __name__ == "__main__":
    sys.exit(main())
