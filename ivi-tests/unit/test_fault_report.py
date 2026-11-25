"""결함 주입 집계(tools/fault_report.py)를 기기 없이 검증한다. 문서의 'N개 중 M개'가 이 집계에서 나온다."""
import json

from tools import fault_report

OK = "tests/test_a.py::test_ok"
AC = "tests/test_vehicle_signals.py::test_ac_toggle_reaches_every_seat"
NOISY = "tests/test_b.py::test_noisy"


def run(fault, kind, outcomes, suffix="", version=None, exitstatus=None):
    run_id = f"fi-{fault}-{kind}" + (f"-{suffix}" if suffix else "")
    failed = any(o in ("failed", "error") for o in outcomes.values())
    return {"summary": {"run_id": run_id, "kind": kind, "exitstatus": 1 if failed else 0 if exitstatus is None else exitstatus,
                        "app": {"version": version or f"0.4.2-fi.{fault} (6)"}, "counts": {}},
            "tests": [{"nodeid": n, "outcome": o, "message": "AssertionError: 값이 다릅니다\n자세히"} for n, o in outcomes.items()]}


def write(tmp_path, faults, runs):
    (tmp_path / "runs").mkdir()
    (tmp_path / "faults.json").write_text(json.dumps(faults, ensure_ascii=False), encoding="utf-8")
    for r in runs:
        name = f"{r['summary']['run_id']}-dev.json"
        (tmp_path / "runs" / name).write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    return tmp_path


FAULTS = [
    {"id": "F00", "title": "대조군", "devices": ["aaos", "mock"]},
    {"id": "F01", "title": "A/C 운전석만", "devices": ["aaos"]},
    {"id": "F02", "title": "화면 갱신 누락", "devices": ["aaos", "mock"]},
]


def result(tmp_path, runs, faults=FAULTS):
    return fault_report.evaluate(*fault_report.load(write(tmp_path, faults, runs)))


def verdicts(res):
    return {(r["fault"], r["kind"], r["suffix"]): r["verdict"] for r in res["rows"]}


def test_failed_test_counts_as_caught_and_missed_is_reported(tmp_path):
    res = result(tmp_path, [
        run("F00", "aaos", {OK: "passed", AC: "passed"}),
        run("F01", "aaos", {OK: "passed", AC: "failed"}),
        run("F02", "aaos", {OK: "passed", AC: "passed"}),
    ])
    assert verdicts(res) == {("F00", "aaos", ""): "놓침", ("F01", "aaos", ""): "탐지", ("F02", "aaos", ""): "놓침"}
    assert res["totals"]["aaos"] == {"applicable": 2, "ran": 2, "caught": ["F01"], "missed": ["F02"], "not_run": []}
    caught = next(r for r in res["rows"] if r["fault"] == "F01")
    assert caught["tests"] == [{"nodeid": AC, "outcome": "failed", "message": "AssertionError: 값이 다릅니다"}]
    assert res["control_clean"] == {"aaos": True}


def test_failure_also_seen_in_control_is_not_counted(tmp_path):
    """대조군에서도 실패한 테스트(환경 문제)는 결함을 잡은 근거가 아니다."""
    res = result(tmp_path, [
        run("F00", "aaos", {OK: "passed", NOISY: "failed"}),
        run("F02", "aaos", {OK: "passed", NOISY: "failed"}),
    ])
    assert verdicts(res)[("F02", "aaos", "")] == "놓침"
    assert res["control_clean"] == {"aaos": False}
    assert "대조군에 실패나 흔들림" in fault_report.markdown(res)


def test_flaky_only_is_not_caught(tmp_path):
    res = result(tmp_path, [run("F00", "aaos", {OK: "passed"}), run("F02", "aaos", {OK: "flaky"})])
    assert verdicts(res)[("F02", "aaos", "")] == "흔들림"
    assert res["totals"]["aaos"]["caught"] == []


def test_wrong_apk_or_unfinished_run_is_invalid(tmp_path):
    """설치된 APK 버전에 결함 id 가 없으면 그 결함을 돌린 것이 아니다. 중간에 멈춘 실행도 판정하지 않는다."""
    res = result(tmp_path, [
        run("F00", "aaos", {OK: "passed"}),
        run("F01", "aaos", {AC: "failed"}, version="0.4.2 (6)"),
        run("F02", "aaos", {OK: "passed"}, exitstatus=2),
    ])
    assert verdicts(res)[("F01", "aaos", "")] == "무효"
    assert verdicts(res)[("F02", "aaos", "")] == "무효"


def test_control_may_be_the_main_build(tmp_path):
    """대조군은 결함이 없는 빌드면 된다. 태블릿은 이미 설치된 main 빌드(버전 0.4.2)로 돌렸다."""
    res = result(tmp_path, [run("F00", "mock", {OK: "passed"}, version="0.4.2 (6)"), run("F02", "mock", {OK: "failed"})])
    assert verdicts(res) == {("F00", "mock", ""): "놓침", ("F02", "mock", ""): "탐지"}
    assert res["control_clean"] == {"mock": True}


def test_totals_count_first_runs_per_device_only(tmp_path):
    """다시 확인한 실행(접미)은 처음 실행의 'N개 중 M개'를 바꾸지 않는다. 해당하지 않는 기기와 돌리지 않은 결함도 구분한다."""
    res = result(tmp_path, [
        run("F00", "aaos", {OK: "passed"}),
        run("F00", "mock", {OK: "passed"}),
        run("F02", "aaos", {OK: "passed"}),
        run("F02", "aaos", {OK: "failed"}, suffix="after"),
        run("F01", "mock", {AC: "failed"}),  # F01 은 태블릿에 해당하지 않는다
    ])
    assert verdicts(res)[("F02", "aaos", "after")] == "탐지"
    assert res["totals"]["aaos"] == {"applicable": 2, "ran": 1, "caught": [], "missed": ["F02"], "not_run": ["F01"]}
    assert "mock" not in res["totals"]  # 태블릿에 해당하는 결함(F02)을 태블릿에서 돌리지 않았다
    text = fault_report.markdown(res)
    assert "AAOS 에뮬레이터: 해당 결함 2개 중 1개 실행, 0개 탐지 (놓침·흔들림: F02) (실행 안 함: F01)" in text


def test_main_prints_markdown(tmp_path, capsys):
    folder = write(tmp_path, FAULTS, [run("F00", "aaos", {OK: "passed"}), run("F01", "aaos", {AC: "failed"})])
    fault_report.main([str(folder)])
    out = capsys.readouterr().out
    assert "| F01 | AAOS 에뮬레이터 | 처음 | 탐지 | test_ac_toggle_reaches_every_seat |" in out
