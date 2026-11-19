"""Release 게이트(tools/release_gate.py)의 다섯 조건을 기기 없이 검증한다. 조건마다 통과 사례와 막는 사례를 둔다."""
import json

import pytest

from tools import release_gate

KNOWN = "tests/test_spike_aaos.py::test_known | 3 | 플랫폼 결함"
NO_TRACE_GAP = ([], [], [])
CLEAN_QUARANTINE = "# 비어 있음"


def run(run_id, serial, kind, outcomes):
    """outcomes: {nodeid: 판정}"""
    tests = [{"nodeid": nodeid, "outcome": outcome, "reruns": 1 if outcome == "flaky" else 0}
             for nodeid, outcome in outcomes.items()]
    return {"summary": {"run_id": run_id, "serial": serial, "kind": kind}, "tests": tests}


def bench(rounds=2, aaos=None, mock=None):
    """두 기기(AAOS, 태블릿) × rounds 회. 알려진 결함은 AAOS 에서만 돌고 태블릿에서는 건너뛴다."""
    aaos = aaos or {}
    mock = mock or {}
    runs = {}
    for n in range(1, rounds + 1):
        run_id = f"20261118-2000{n:02d}-r{n}"
        runs[run_id] = [
            run(run_id, "emulator-5554", "aaos", {"tests/test_a.py::test_ok": "passed",
                                                   "tests/test_spike_aaos.py::test_known": "xfailed",
                                                   **aaos.get(n, {})}),
            run(run_id, "TABLET", "mock", {"tests/test_a.py::test_ok": "passed",
                                           "tests/test_spike_aaos.py::test_known": "skipped",
                                           **mock.get(n, {})}),
        ]
    return runs


def failing(checks):
    return {check.number: check.problems for check in checks if not check.ok}


def test_clean_release_passes():
    assert failing(release_gate.evaluate(bench(), CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP)) == {}


@pytest.mark.parametrize("outcome", ["failed", "error"])
def test_condition1_failed_or_error_blocks(outcome):
    checks = release_gate.evaluate(bench(mock={2: {"tests/test_a.py::test_ok": outcome}}), CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP)
    assert list(failing(checks)) == [1]
    assert "20261118-200002-r2 TABLET tests/test_a.py::test_ok" in failing(checks)[1][0]


def test_condition1_missing_device_result_blocks():
    runs = bench()
    runs["20261118-200002-r2"].pop()  # 2회차에 태블릿 결과 파일이 없음
    assert failing(release_gate.evaluate(runs, CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP)) == {
        1: ["20261118-200002-r2 TABLET: 결과 파일 없음"]}


def test_condition1_missing_round_blocks():
    # 반복 3회를 시켰는데 결과는 2회뿐 (중간에 멈춘 회차)
    assert failing(release_gate.evaluate(bench(rounds=2), CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP, expected_rounds=3)) == {
        1: ["반복 3회 가운데 결과가 있는 회차는 2회"]}


def test_pick_since_leaves_out_earlier_runs():
    runs = {"20261118-190000": [], "20261119-030500-r1": [], "20261119-031500-r2": []}
    assert list(release_gate.pick(runs, since="20261119-030000")) == ["20261119-030500-r1", "20261119-031500-r2"]
    assert list(release_gate.pick(runs, last=1)) == ["20261119-031500-r2"]


def test_condition2_flaky_in_any_round_blocks():
    checks = release_gate.evaluate(bench(aaos={1: {"tests/test_a.py::test_ok": "flaky"}}), CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP)
    assert list(failing(checks)) == [2]


@pytest.mark.parametrize("text, message", [
    ("t::a | 간헐 실패 | 2026-11-13", "형식"),  # 해제 조건 없음
    ("t::a | x | 2026-11-13 | 20회\nt::b | x | 2026-11-13 | 20회\nt::c | x | 2026-11-13 | 20회", "격리 3개"),
], ids=["missing_release_condition", "more_than_two"])
def test_condition3_quarantine_list_blocks(text, message):
    problems = failing(release_gate.evaluate(bench(), text, KNOWN, NO_TRACE_GAP))
    assert list(problems) == [3] and message in problems[3][0]


def test_condition3_two_complete_entries_pass():
    text = "t::a | x | 2026-11-13 | 20회 연속 통과\nt::b | y | 2026-11-14 | 20회 연속 통과"
    assert failing(release_gate.evaluate(bench(), text, KNOWN, NO_TRACE_GAP)) == {}


def test_condition4_trace_gap_blocks():
    problems = failing(release_gate.evaluate(bench(), CLEAN_QUARANTINE, KNOWN, (["HVAC-09"], ["test_new"], [])))
    assert problems == {4: ["테스트가 없는 요구사항: HVAC-09", "요구사항이 없는 테스트: test_new"]}


def test_condition5_unlisted_xfail_blocks():
    runs = bench(aaos={1: {"tests/test_a.py::test_hidden": "xfailed"}})
    problems = failing(release_gate.evaluate(runs, CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP))
    assert problems == {5: ["목록에 없는 xfail: tests/test_a.py::test_hidden"]}


def test_condition5_known_defect_not_xfailed_blocks():
    # strict xfail 이 XPASS 로 바뀌면 failed 로 기록된다 → 조건 1 과 함께 5 도 막는다 (목록이 낡음)
    runs = bench(aaos={2: {"tests/test_spike_aaos.py::test_known": "failed"}})
    problems = failing(release_gate.evaluate(runs, CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP))
    assert list(problems) == [1, 5] and "알려진 결함 3번이 xfailed 가 아님 (failed)" in problems[5][0]


def test_condition5_known_defect_not_run_blocks():
    runs = bench(aaos={1: {"tests/test_spike_aaos.py::test_known": "skipped"},
                       2: {"tests/test_spike_aaos.py::test_known": "skipped"}})
    problems = failing(release_gate.evaluate(runs, CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP))
    assert problems == {5: ["알려진 결함 3번 테스트가 실행되지 않음: tests/test_spike_aaos.py::test_known"]}


def test_cli_reads_run_files_and_returns_exit_code(tmp_path, capsys):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    for results in bench(rounds=3).values():
        for result in results:
            name = f"{result['summary']['run_id']}-{result['summary']['serial']}.json"
            (runs_dir / name).write_text(json.dumps(result), encoding="utf-8")
    (tmp_path / "quarantine.txt").write_text(CLEAN_QUARANTINE, encoding="utf-8")
    (tmp_path / "known.txt").write_text(KNOWN, encoding="utf-8")
    common = ["--runs-dir", str(runs_dir), "--quarantine", str(tmp_path / "quarantine.txt")]

    # 저장소의 요구사항과 테스트로 추적 검사까지 실제로 돈다 (unit job 과 같은 검사)
    assert release_gate.main(common + ["--known-defects", str(tmp_path / "known.txt"), "--last", "2"]) == 0
    out = capsys.readouterr().out
    assert "Release 게이트: 2회 (20261118-200002-r2, 20261118-200003-r3)" in out and "결과: 통과" in out

    (tmp_path / "empty.txt").write_text("", encoding="utf-8")  # 알려진 결함 목록이 비면 xfail 이 '목록에 없는 xfail' 이 된다
    assert release_gate.main(common + ["--known-defects", str(tmp_path / "empty.txt")]) == 1
    assert "막음 (조건 5)" in capsys.readouterr().out


def test_repository_known_defects_match_strict_xfail_tests():
    """known_defects.txt 가 tests/ 의 xfail(strict=True) 테스트와 같은지 (목록과 코드가 따로 놀지 않게)."""
    import ast
    from pathlib import Path

    tests_dir = Path(release_gate.ROOT) / "tests"
    strict = set()
    for path in tests_dir.glob("test_*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "xfail"
                        and any(k.arg == "strict" and getattr(k.value, "value", False) for k in deco.keywords)):
                    strict.add(f"tests/{path.name}::{node.name}")
    listed = {d.pattern for d in release_gate.parse_known_defects(release_gate.KNOWN_DEFECTS_FILE.read_text(encoding="utf-8"))}
    assert listed == strict
