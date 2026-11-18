"""요구사항과 테스트를 양쪽으로 잇는 추적표를 만든다.

    python tools/trace_report.py            # docs/traceability.md

  요구사항   docs/requirements.md 의 표 (| ID | 요구사항 | 출처 |)
  테스트     tests/*.py 의 @pytest.mark.req("ID", ...)
  결과       site/results/results.json (publish_results.py 가 만든 최신 결과)

A-SPICE 의 검증 단계가 요구하는 '요구사항과 시험 사이의 양방향 추적'을 흉내 낸 것이다.
unit/test_operations.py 가 '테스트가 없는 요구사항'과 '요구사항이 없는 테스트'가 없는지 CI 에서 확인한다.
"""
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # ivi-tests/
REPO = ROOT.parent
REQUIREMENTS = REPO / "docs" / "requirements.md"
OUT = REPO / "docs" / "traceability.md"
RESULTS = REPO / "site" / "results" / "results.json"
KINDS = {"aaos": "AAOS 에뮬레이터", "mock": "태블릿"}


def read_requirements(path=REQUIREMENTS):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        found = re.match(r"^\|\s*([A-Z]+-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if found:
            rows.append({"id": found.group(1), "text": found.group(2), "source": found.group(3)})
    return rows


def read_test_reqs(tests_dir=ROOT / "tests"):
    """테스트 함수 이름 → (파일, 요구사항 ID 목록)."""
    found = {}
    for path in sorted(tests_dir.glob("test_*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
                continue
            ids = []
            for deco in node.decorator_list:
                if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr == "req":
                    ids += [a.value for a in deco.args if isinstance(a, ast.Constant)]
            found[node.name] = (path.name, ids)
    return found


def read_results(path=RESULTS):
    """테스트 함수 이름 → {기기 종류: [판정, ...]} (parametrize 케이스마다 하나)."""
    if not path.exists():
        return {}, []
    data = json.loads(path.read_text(encoding="utf-8"))
    outcomes = defaultdict(lambda: defaultdict(list))
    for f in data["files"]:
        for t in f["tests"]:
            for case in t["cases"]:
                for kind, r in case["results"].items():
                    outcomes[t["name"]][kind].append(r["outcome"])
    return outcomes, [d["kind"] for d in data["devices"]]


def check(requirements, tests):
    """(테스트가 없는 요구사항, 요구사항이 없는 테스트, 없는 ID 를 가리키는 테스트)"""
    ids = {r["id"] for r in requirements}
    used = {i for _, reqs in tests.values() for i in reqs}
    untested = sorted(ids - used)
    untraced = sorted(name for name, (_, reqs) in tests.items() if not reqs)
    unknown = sorted(f"{name}: {i}" for name, (_, reqs) in tests.items() for i in reqs if i not in ids)
    return untested, untraced, unknown


def verdict(outcome_lists):
    flat = [o for outcomes in outcome_lists for o in outcomes]
    if not flat:
        return "결과 없음"
    passed = sum(o == "passed" for o in flat)
    parts = [f"{passed}/{len(flat)} 통과"]
    for outcome, label in (("xfailed", "알려진 결함"), ("skipped", "건너뜀"), ("failed", "실패"), ("error", "오류"), ("flaky", "재시도 후 통과")):
        n = sum(o == outcome for o in flat)
        if n:
            parts.append(f"{label} {n}")
    return ", ".join(parts)


def markdown(requirements, tests, outcomes, kinds):
    untested, untraced, unknown = check(requirements, tests)
    by_req = defaultdict(list)
    for name, (_, reqs) in tests.items():
        for i in reqs:
            by_req[i].append(name)
    lines = [
        "# 요구사항 추적표",
        "",
        "[요구사항](requirements.md)마다 그것을 확인하는 테스트와 최신 결과를 이었습니다. 테스트 코드의 `@pytest.mark.req`를 읽어 `ivi-tests/tools/trace_report.py`가 만듭니다.",
        "A-SPICE의 검증 단계에서 요구하는 요구사항과 시험 사이의 양방향 추적을 흉내 낸 것이고, 표준 인증이나 심사를 받은 것은 아닙니다.",
        "",
        "| 항목 | 개수 |",
        "|---|---|",
        f"| 요구사항 | {len(requirements)}개 |",
        f"| 테스트가 있는 요구사항 | {len(requirements) - len(untested)}개 |",
        f"| 테스트 함수 | {len(tests)}개 |",
        f"| 요구사항이 없는 테스트 | {len(untraced)}개 |",
        "",
        "결과 열은 parametrize 케이스까지 센 것입니다. 알려진 결함은 일부러 남겨 둔 결함이고, 건너뜀은 그 기기에서 의미가 없는 테스트입니다.",
        "",
        "## 요구사항에서 테스트로",
        "",
        "| ID | 요구사항 | 출처 | 테스트 | " + " | ".join(KINDS[k] for k in kinds) + " |",
        "|---|---|---|---|" + "---|" * len(kinds),
    ]
    for r in requirements:
        names = sorted(by_req.get(r["id"], []))
        cells = "<br>".join(f"`{n}`" for n in names) or "없음"
        results = [verdict([outcomes.get(n, {}).get(k, []) for n in names]) for k in kinds]
        lines.append(f"| {r['id']} | {r['text']} | {r['source']} | {cells} | " + " | ".join(results) + " |")
    lines += ["", "## 테스트에서 요구사항으로", "", "| 테스트 파일 | 테스트 수 | 요구사항 |", "|---|---|---|"]
    by_file = defaultdict(list)
    for name, (file, reqs) in tests.items():
        by_file[file].append(reqs)
    for file in sorted(by_file):
        ids = sorted({i for reqs in by_file[file] for i in reqs})
        lines.append(f"| `{file}` | {len(by_file[file])}개 | {', '.join(ids)} |")
    if untested or untraced or unknown:
        lines += ["", "## 빠진 곳", ""]
        lines += [f"- 테스트가 없는 요구사항: {i}" for i in untested]
        lines += [f"- 요구사항이 없는 테스트: `{n}`" for n in untraced]
        lines += [f"- 없는 요구사항을 가리킴: {u}" for u in unknown]
    return "\n".join(lines) + "\n"


def main():
    requirements, tests = read_requirements(), read_test_reqs()
    outcomes, kinds = read_results()
    OUT.write_text(markdown(requirements, tests, outcomes, kinds or list(KINDS)), encoding="utf-8", newline="\n")
    untested, untraced, unknown = check(requirements, tests)
    print(f"요구사항 {len(requirements)}개, 테스트 {len(tests)}개 → {OUT}")
    if untested or untraced or unknown:
        print(f"빠진 곳: 테스트 없는 요구사항 {untested}, 요구사항 없는 테스트 {untraced}, 없는 ID {unknown}")


if __name__ == "__main__":
    main()
