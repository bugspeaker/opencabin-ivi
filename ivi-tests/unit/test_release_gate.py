"""Release 게이트(tools/release_gate.py)의 여섯 조건을 기기 없이 검증한다. 조건마다 통과 사례와 막는 사례를 둔다.

조건 1(실행 완전성)은 '실패가 없다'와 '정한 검증을 끝까지 했다'를 가르는 조건이라 막는 사례를 가장 많이 둔다:
기기 하나가 통째로 빠짐, 일부만 돌림(-m smoke), 중간에 멈춤(종료 코드 2), 기기 전용이 아닌 건너뜀, 다른 커밋의 결과."""
import json
import os
import subprocess
import sys

import pytest

from tools import release_gate

KNOWN = "tests/test_spike_aaos.py::test_known | 3 | 플랫폼 결함"
NO_TRACE_GAP = ([], [], [])
CLEAN_QUARANTINE = "# 비어 있음"
OK = "tests/test_a.py::test_ok"
KNOWN_ID = "tests/test_spike_aaos.py::test_known"
CLOCK = "tests/test_settings.py::test_clock_on_tablet"
# 지금 코드에서 수집한 테스트 (tools/collect_tests.collect 와 같은 꼴): 알려진 결함은 AAOS 전용, 시계는 태블릿 전용
INVENTORY = {OK: {"smoke"}, KNOWN_ID: {"aaos", "spike"}, CLOCK: {"tablet", "regression"}}
COMMIT = "a" * 40
APP = {"version": "1.0 (1)", "apk_sha256": "c" * 64}


def run(run_id, serial, kind, outcomes, **summary):
    """outcomes: {nodeid: 판정}"""
    tests = [{"nodeid": nodeid, "outcome": outcome, "reruns": 1 if outcome == "flaky" else 0, "message": ""}
             for nodeid, outcome in outcomes.items()]
    return {"summary": {"run_id": run_id, "serial": serial, "kind": kind, "exitstatus": 0, "commit": COMMIT,
                        "dirty": False, "app": APP, **summary}, "tests": tests}


def bench(rounds=2, aaos=None, mock=None, aaos_summary=None, mock_summary=None):
    """두 기기(AAOS, 태블릿) × rounds 회. 기기 전용 테스트는 다른 기기에서 건너뛴다."""
    aaos, mock = aaos or {}, mock or {}
    runs = {}
    for n in range(1, rounds + 1):
        run_id = f"20261118-2000{n:02d}-r{n}"
        runs[run_id] = [
            run(run_id, "emulator-5554", "aaos", {OK: "passed", KNOWN_ID: "xfailed", CLOCK: "skipped", **aaos.get(n, {})},
                **(aaos_summary or {}).get(n, {})),
            run(run_id, "TABLET", "mock", {OK: "passed", KNOWN_ID: "skipped", CLOCK: "passed", **mock.get(n, {})},
                **(mock_summary or {}).get(n, {})),
        ]
    return runs


def evaluate(runs, quarantine_text=CLEAN_QUARANTINE, known=KNOWN, trace=NO_TRACE_GAP, **kwargs):
    return release_gate.evaluate(runs, quarantine_text, known, trace, inventory=kwargs.pop("inventory", INVENTORY), **kwargs)


def failing(checks):
    return {check.number: check.problems for check in checks if not check.ok}


def test_clean_release_passes():
    checks = evaluate(bench())
    assert failing(checks) == {}
    assert all(not check.notes for check in checks)


# ---------------- 조건 1: 실행 완전성 ----------------

def test_condition1_missing_device_result_in_one_round_blocks():
    runs = bench()
    runs["20261118-200002-r2"].pop()  # 2회차에 태블릿 결과 파일이 없음
    assert failing(evaluate(runs)) == {1: ["20261118-200002-r2 mock: 결과 파일 없음 (필수 기기)"]}


def test_condition1_device_missing_in_every_round_blocks():
    """태블릿이 처음부터 연결되지 않아 AAOS 결과만 있는 경우. 기기 목록을 결과 파일에서 유추하면 통과해 버린다."""
    runs = {run_id: [results[0]] for run_id, results in bench().items()}
    problems = failing(evaluate(runs))
    assert problems == {1: ["20261118-200001-r1 mock: 결과 파일 없음 (필수 기기)",
                            "20261118-200002-r2 mock: 결과 파일 없음 (필수 기기)"]}
    assert failing(evaluate(runs, kinds=("aaos",))) == {}  # 한 기기만 확인하겠다고 정했으면 통과


def test_condition1_missing_round_blocks():
    # 반복 3회를 시켰는데 결과는 2회뿐 (중간에 멈춘 회차)
    assert failing(evaluate(bench(rounds=2), expected_rounds=3)) == {1: ["반복 3회 가운데 결과가 있는 회차는 2회"]}


def test_condition1_partial_selection_blocks():
    """Release 범위(전체) 대신 일부만 돌린 결과 (-m smoke). 돈 것은 모두 통과지만 검증을 다 하지 않았다."""
    runs = bench()
    for results in runs.values():
        for result in results:
            result["tests"] = [test for test in result["tests"] if test["nodeid"] == OK]
    problems = failing(evaluate(runs))
    assert list(problems) == [1, 6]  # 알려진 결함 테스트도 돌지 않았다
    assert "20261118-200001-r1 emulator-5554: 지금 코드의 테스트 2개가 돌지 않음" in problems[1][0]


@pytest.mark.parametrize("exitstatus, name", [(2, "중단됨"), (3, "pytest 내부 오류"), (5, "수집된 테스트 없음")])
def test_condition1_abnormal_exit_blocks_even_if_every_test_passed(exitstatus, name):
    """판정이 모두 통과여도 pytest 가 비정상으로 끝났으면 막는다 (예: Appium 세션이 끊겨 conftest 가 멈춘 실행)."""
    problems = failing(evaluate(bench(aaos_summary={2: {"exitstatus": exitstatus}})))
    assert problems == {1: [f"20261118-200002-r2 emulator-5554: pytest 종료 코드 {exitstatus} ({name})"]}


def test_condition1_exit_code_1_with_failures_is_left_to_condition2():
    runs = bench(mock={1: {OK: "failed"}}, mock_summary={1: {"exitstatus": 1}})
    assert list(failing(evaluate(runs))) == [2]


def test_condition1_test_without_outcome_blocks():
    problems = failing(evaluate(bench(aaos={1: {OK: None}})))
    assert problems == {1: [f"20261118-200001-r1 emulator-5554: 판정 없이 끝난 테스트 1개 ({OK})"]}


def test_condition1_skip_that_is_not_device_only_blocks():
    """기기 전용 마커가 아닌 이유로 건너뛴 테스트 (예: 기기에 주행 영상이 없어 영상 테스트가 skip). 검증 누락이다."""
    problems = failing(evaluate(bench(mock={2: {OK: "skipped"}})))
    assert problems == {1: [f"20261118-200002-r2 TABLET: 기기 전용이 아닌데 건너뛴 테스트 1개 ({OK})"]}


def test_condition1_results_from_other_code_block():
    runs = bench(aaos={1: {"tests/test_a.py::test_renamed_long_ago": "passed"}})
    problems = failing(evaluate(runs))
    assert problems == {1: ["20261118-200001-r1 emulator-5554: 지금 코드에 없는 테스트 1개의 결과. 다른 코드로 돈 결과다 "
                            "(tests/test_a.py::test_renamed_long_ago)"]}


def test_condition1_commit_checks():
    other = "b" * 40
    assert failing(evaluate(bench(), commit=COMMIT[:7])) == {}
    problems = failing(evaluate(bench(mock_summary={2: {"commit": other}}), commit=COMMIT))
    assert problems[1] == ["20261118-200002-r2 TABLET: 커밋 bbbbbbb 에서 돈 결과 (확인할 커밋 aaaaaaa)",
                           "회차·기기마다 다른 커밋에서 돈 결과가 섞였다: aaaaaaa, bbbbbbb"]
    problems = failing(evaluate(bench(aaos_summary={1: {"dirty": True}})))
    assert problems[1] == ["20261118-200001-r1 emulator-5554: 커밋하지 않은 변경이 있는 코드로 돈 결과 (aaaaaaa+)"]


def test_condition1_legacy_result_files_pass_with_notes():
    """2026-11-19 이전 결과 파일에는 종료 코드와 커밋이 없다. 테스트 목록 대조로 끝까지 돌았는지 보고, 참고로 알린다."""
    legacy = {n: {"exitstatus": None, "commit": None} for n in (1, 2)}
    runs = bench(aaos_summary=legacy, mock_summary=legacy)
    for results in runs.values():
        for result in results:
            del result["summary"]["exitstatus"], result["summary"]["commit"]
    checks = evaluate(runs)
    assert failing(checks) == {}
    assert any("종료 코드가 없는 결과 파일 4개" in note for note in checks[0].notes)
    # 커밋을 정해 확인하라고 하면, 커밋이 없는 결과로는 확인할 수 없으니 막는다
    assert "커밋 aaaaaaa 에서 돈 결과인지 확인할 수 없다" in failing(evaluate(runs, commit=COMMIT))[1][0]


def test_condition1_one_test_missing_in_one_round_blocks():
    """한 회차, 한 기기에서 일반 테스트 하나만 빠진 결과. 다른 회차에 있다고 넘어가지 않는다."""
    runs = bench()
    runs["20261118-200002-r2"][1]["tests"] = [t for t in runs["20261118-200002-r2"][1]["tests"] if t["nodeid"] != OK]
    assert failing(evaluate(runs)) == {1: [f"20261118-200002-r2 TABLET: 지금 코드의 테스트 1개가 돌지 않음 ({OK})"]}


def test_condition1_duplicate_results_block():
    runs = bench()
    runs["20261118-200001-r1"].append(runs["20261118-200001-r1"][1])  # 같은 회차에 태블릿 결과가 둘
    runs["20261118-200002-r2"][0]["tests"].append(dict(runs["20261118-200002-r2"][0]["tests"][0]))  # 같은 테스트 두 번
    problems = failing(evaluate(runs))[1]
    assert "20261118-200001-r1 mock: 같은 회차에 결과가 2개 (중복)" in problems
    assert f"20261118-200002-r2 emulator-5554: 같은 테스트의 결과가 두 번 이상 ({OK})" in problems


def test_condition1_different_apk_blocks():
    """회차·기기마다 같은 빌드여야 한다. 결과 파일의 APK sha256 으로 본다."""
    other = {"version": "1.0 (2)", "apk_sha256": "d" * 64}
    problems = failing(evaluate(bench(mock_summary={2: {"app": other}})))
    assert problems == {1: [f"회차·기기마다 다른 APK 로 돈 결과가 섞였다: {'c' * 12}, {'d' * 12}"]}


def test_condition1_without_inventory_blocks():
    checks = release_gate.evaluate(bench(), CLEAN_QUARANTINE, KNOWN, NO_TRACE_GAP)
    assert "지금 코드의 테스트 목록이 없어" in failing(checks)[1][0]


def test_pick_since_leaves_out_earlier_runs():
    runs = {"20261118-190000": [], "20261119-030500-r1": [], "20261119-031500-r2": []}
    assert list(release_gate.pick(runs, since="20261119-030000")) == ["20261119-030500-r1", "20261119-031500-r2"]
    assert list(release_gate.pick(runs, last=1)) == ["20261119-031500-r2"]


# ---------------- 조건 2~6 ----------------

@pytest.mark.parametrize("outcome", ["failed", "error", "xpassed"])
def test_condition2_failed_error_or_xpassed_blocks(outcome):
    checks = evaluate(bench(mock={2: {OK: outcome}}))
    assert list(failing(checks)) == [2]
    assert f"20261118-200002-r2 TABLET {OK}" in failing(checks)[2][0]


def test_condition3_flaky_in_any_round_blocks():
    assert list(failing(evaluate(bench(aaos={1: {OK: "flaky"}})))) == [3]


@pytest.mark.parametrize("text, message", [
    ("t::a | 간헐 실패 | 2026-11-13", "형식"),  # 해제 조건 없음
    ("t::a | x | 2026-11-13 | 20회\nt::b | x | 2026-11-13 | 20회\nt::c | x | 2026-11-13 | 20회", "격리 3개"),
], ids=["missing_release_condition", "more_than_two"])
def test_condition4_quarantine_list_blocks(text, message):
    problems = failing(evaluate(bench(), text))
    assert list(problems) == [4] and message in problems[4][0]


def test_condition4_two_complete_entries_pass():
    text = "t::a | x | 2026-11-13 | 20회 연속 통과\nt::b | y | 2026-11-14 | 20회 연속 통과"
    assert failing(evaluate(bench(), text)) == {}


def test_condition5_trace_gap_blocks():
    problems = failing(evaluate(bench(), trace=(["HVAC-09"], ["test_new"], [])))
    assert problems == {5: ["테스트가 없는 요구사항: HVAC-09", "요구사항이 없는 테스트: test_new"]}


def test_condition6_unlisted_xfail_blocks():
    hidden = "tests/test_a.py::test_hidden"
    runs = bench(aaos={n: {hidden: "xfailed"} for n in (1, 2)}, mock={n: {hidden: "passed"} for n in (1, 2)})
    problems = failing(evaluate(runs, inventory={**INVENTORY, hidden: set()}))
    assert problems == {6: ["목록에 없는 xfail: tests/test_a.py::test_hidden "
                            "(20261118-200001-r1 emulator-5554, 20261118-200002-r2 emulator-5554)"]}


def test_condition6_known_defect_not_xfailed_blocks():
    # strict xfail 이 XPASS 로 바뀌면 failed 로 기록된다 → 조건 2 와 함께 6 도 막는다 (목록이 낡음)
    problems = failing(evaluate(bench(aaos={2: {KNOWN_ID: "failed"}})))
    assert list(problems) == [2, 6] and "알려진 결함 3번이 xfailed 가 아님 (failed)" in problems[6][0]
    # 회차마다 따로 본다: 1회차에서 xfailed 였어도 2회차는 그 회차만 짚는다
    assert "(20261118-200002-r2 emulator-5554)" in problems[6][0] and "r1" not in problems[6][0]


@pytest.mark.parametrize("missing, condition, message", [
    ("quarantine", 4, "격리 목록 파일(quarantine.txt)이 없다"),
    ("known", 6, "알려진 결함 목록 파일(known_defects.txt)이 없다"),
])
def test_missing_policy_file_blocks(missing, condition, message):
    """정책 파일이 없으면 빈 목록으로 조용히 바꾸지 않는다 (빈 격리 목록은 통과, 빈 결함 목록은 엉뚱한 이유로 막힌다)."""
    texts = {"quarantine": CLEAN_QUARANTINE, "known": KNOWN, missing: None}
    problems = failing(evaluate(bench(), texts["quarantine"], texts["known"]))
    assert message in problems[condition][0]


def test_condition6_known_defect_not_run_blocks():
    problems = failing(evaluate(bench(aaos={1: {KNOWN_ID: "skipped"}, 2: {KNOWN_ID: "skipped"}})))
    # AAOS 전용 테스트를 AAOS 에서 건너뛴 것이라 조건 1 도 막는다
    assert list(problems) == [1, 6] and problems[6] == [
        f"알려진 결함 3번 테스트가 실행되지 않음: {KNOWN_ID} (20261118-200001-r1 emulator-5554, 20261118-200002-r2 emulator-5554)"]


def test_cli_reads_run_files_and_returns_exit_code(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(release_gate.collect_tests, "collect", lambda: INVENTORY)  # 실제 수집은 아래 따로 확인
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
    assert "막음 (조건 6)" in capsys.readouterr().out

    # 태블릿 결과를 지우면 (기기가 연결되지 않은 Release) 조건 1 로 막는다
    for path in runs_dir.glob("*-TABLET.json"):
        path.unlink()
    assert release_gate.main(common + ["--known-defects", str(tmp_path / "known.txt")]) == 1
    assert "막음 (조건 1)" in capsys.readouterr().out

    # 정책 파일 경로가 틀려 파일이 없으면 막는다
    assert release_gate.main(["--runs-dir", str(runs_dir), "--quarantine", str(tmp_path / "없음.txt"),
                              "--known-defects", str(tmp_path / "known.txt")]) == 1
    assert "격리 목록 파일(quarantine.txt)이 없다" in capsys.readouterr().out


def test_repository_known_defects_match_strict_xfail_tests():
    """known_defects.txt 가 tests/ 의 xfail(strict=True) 테스트와 같은지 (목록과 코드가 따로 놀지 않게).
    그리고 모든 xfail 에 raises 가 있는지: 없으면 버튼을 못 찾은 오류나 세션 끊김까지 '알려진 결함'으로 삼켜진다."""
    import ast
    from pathlib import Path

    tests_dir = Path(release_gate.ROOT) / "tests"
    strict, without_raises = set(), set()
    for path in tests_dir.glob("test_*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "xfail"
                        and any(k.arg == "strict" and getattr(k.value, "value", False) for k in deco.keywords)):
                    strict.add(f"tests/{path.name}::{node.name}")
                if isinstance(deco, ast.Call) and getattr(deco.func, "attr", "") == "xfail" \
                        and not any(k.arg == "raises" for k in deco.keywords):
                    without_raises.add(f"tests/{path.name}::{node.name}")
    listed = {d.pattern for d in release_gate.parse_known_defects(release_gate.KNOWN_DEFECTS_FILE.read_text(encoding="utf-8"))}
    assert listed == strict
    assert without_raises == set()


KNOWN_DEFECT_DEMO = """
import pytest
from selenium.common.exceptions import NoSuchElementException
from ivi.defects import DefectReproduced

KNOWN = pytest.mark.xfail(strict=True, raises=DefectReproduced, reason="알려진 결함")

@KNOWN
def test_symptom():
    raise DefectReproduced("두 버튼이 72x76px 겹친다")

@KNOWN
def test_element_missing():
    raise NoSuchElementException("버튼이 없다")

@KNOWN
def test_fixed():
    pass
"""


def test_known_defect_xfail_does_not_swallow_other_failures(tmp_path):
    """raises=DefectReproduced 로 건 알려진 결함은 증상일 때만 xfailed 다. 요소를 못 찾은 실패는 failed 로 남고,
    결함이 고쳐져 통과하면 strict 라 failed 가 된다. (pytest 를 따로 띄워 실제 판정을 본다)"""
    (tmp_path / "test_demo.py").write_text(KNOWN_DEFECT_DEMO, encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider", str(tmp_path)],
                          cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(release_gate.ROOT), "PYTHONIOENCODING": "utf-8"},
                          capture_output=True, text=True, encoding="utf-8")
    out = proc.stdout
    assert "XFAIL test_demo.py::test_symptom" in out
    assert "FAILED test_demo.py::test_element_missing" in out
    assert "FAILED test_demo.py::test_fixed" in out and "XPASS(strict)" in out


def test_collect_tests_matches_repository():
    """tools/collect_tests 가 기기 없이 tests/ 를 수집하고, 기기 전용 마커를 읽는다. 함수는 모두 매개변수 조합까지 나온다."""
    from tools import collect_tests, trace_report

    inventory = collect_tests.collect()
    assert "tablet" in inventory["tests/test_settings.py::test_12_hour_clock_on_tablet"]
    assert "aaos" in inventory["tests/test_power.py::test_power_cycle_brings_back_app_and_cabin_defaults"]
    functions = {nodeid.split("::")[1].split("[")[0] for nodeid in inventory}
    assert functions == set(trace_report.read_test_reqs())
