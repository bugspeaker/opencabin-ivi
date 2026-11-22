"""요구사항과 테스트를 양쪽으로 잇는 추적표를 만든다.

    python tools/trace_report.py            # docs/traceability.md

  요구사항   docs/requirements.md 의 표 (| ID | 요구사항 | 출처 |)
  조건       docs/requirements.md 의 복합 요구사항 표 (| ID.n | 내용 | 테스트 | 그 조건을 보는 확인 |)
  테스트     tests/*.py 의 @pytest.mark.req("ID", ...)
  결과       site/results/results.json (publish_results.py 가 만든 최신 결과)

A-SPICE 가 요구하는 요구사항–시험 양방향 추적을 개인 프로젝트 규모로 적용해 본 것이다.
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


def read_conditions(path=REQUIREMENTS):
    """복합 요구사항의 조건 행: [{"id": "HVAC-02.1", "req": "HVAC-02", "text", "tests": [이름...], "how"}].
    ID 뒤에 '.n' 이 붙어 read_requirements 의 정규식에는 걸리지 않는다. 테스트 칸이 '확인하지 않음'이면 tests 는 빈 목록."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        found = re.match(r"^\|\s*(([A-Z]+-\d+)\.\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if found:
            rows.append({"id": found.group(1), "req": found.group(2), "text": found.group(3),
                         "tests": re.findall(r"`(test_\w+)`", found.group(4)), "how": found.group(5),
                         "cell": found.group(4)})
    return rows


def check_conditions(conditions, tests):
    """조건 표가 코드와 맞는지: 없는 테스트, 그 요구사항 ID 를 달지 않은 테스트, 테스트도 '확인하지 않음'도 아닌 행."""
    problems = []
    for row in conditions:
        if not row["tests"] and "확인하지 않음" not in row["cell"]:
            problems.append(f"{row['id']}: 테스트 칸에 테스트 이름도 '확인하지 않음'도 없다")
        for name in row["tests"]:
            if name not in tests:
                problems.append(f"{row['id']}: 없는 테스트 {name}")
            elif row["req"] not in tests[name][1]:
                problems.append(f"{row['id']}: {name} 에 @pytest.mark.req(\"{row['req']}\") 가 없다")
    return problems


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
    return "<br>".join(parts)   # 좁은 칸에서 아무 데서나 접히지 않게 항목마다 줄을 나눈다


def markdown(requirements, tests, outcomes, kinds, conditions=()):
    untested, untraced, unknown = check(requirements, tests)
    by_req = defaultdict(list)
    for name, (_, reqs) in tests.items():
        for i in reqs:
            by_req[i].append(name)
    lines = [
        "# 요구사항 추적표",
        "",
        "[요구사항](requirements.md)마다 그것을 확인하는 테스트와 최신 결과를 이었습니다. 테스트 코드의 `@pytest.mark.req`를 읽어 `ivi-tests/tools/trace_report.py`가 만듭니다.",
        "A-SPICE가 요구하는 요구사항–시험 양방향 추적을 개인 프로젝트 규모로 적용해 본 것이고, 표준 인증이나 심사를 받은 것은 아닙니다.",
        "",
        "| 항목 | 개수 |",
        "|---|---|",
        f"| 요구사항 | {len(requirements)}개 |",
        f"| 테스트가 있는 요구사항 | {len(requirements) - len(untested)}개 |",
        f"| 테스트 함수 | {len(tests)}개 |",
        f"| 요구사항이 없는 테스트 | {len(untraced)}개 |",
        "",
        "'요구사항이 없는 테스트 0개', '테스트가 있는 요구사항 26개'는 요구사항 ID 연결이 빠지지 않았다는 수치입니다. 조건별 검증이 충분하다거나 표준(ISO 26262, A-SPICE)을 지켰다는 뜻은 아닙니다. 조건별로 어디까지 확인했는지는 아래 '복합 요구사항' 표에 있습니다.",
        "",
        "결과 열은 parametrize 케이스까지 센 것입니다. 알려진 결함은 플랫폼(AAOS SystemUI) 쪽 문제라 xfail로 걸어 둔 결함이고, 건너뜀은 그 기기에서 의미가 없는 테스트입니다.",
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
    if conditions:
        gaps = sum(not row["tests"] for row in conditions)
        lines += ["", "## 복합 요구사항: 조건마다 확인하는 곳", "",
                  f"조건이 여럿인 요구사항은 조건마다 어느 확인이 그 조건을 보는지 [요구사항](requirements.md#복합-요구사항-조건마다-확인하는-곳)에 적었습니다. "
                  f"조건 {len(conditions)}개 가운데 테스트가 없는 조건은 {gaps}개입니다.", "",
                  "| 조건 | 내용 | 테스트 | 그 조건을 보는 확인 | " + " | ".join(KINDS[k] for k in kinds) + " |",
                  "|---|---|---|---|" + "---|" * len(kinds)]
        for row in conditions:
            results = [verdict([outcomes.get(n, {}).get(k, []) for n in row["tests"]]) if row["tests"] else "확인하지 않음"
                       for k in kinds]
            lines.append(f"| {row['id']} | {row['text']} | {row['cell']} | {row['how']} | " + " | ".join(results) + " |")
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
    requirements, tests, conditions = read_requirements(), read_test_reqs(), read_conditions()
    outcomes, kinds = read_results()
    OUT.write_text(markdown(requirements, tests, outcomes, kinds or list(KINDS), conditions), encoding="utf-8", newline="\n")
    for problem in check_conditions(conditions, tests):
        print(f"조건 표: {problem}")
    untested, untraced, unknown = check(requirements, tests)
    print(f"요구사항 {len(requirements)}개, 테스트 {len(tests)}개 → {OUT}")
    if untested or untraced or unknown:
        print(f"빠진 곳: 테스트 없는 요구사항 {untested}, 요구사항 없는 테스트 {untraced}, 없는 ID {unknown}")


if __name__ == "__main__":
    main()
