"""운영 기능(결과 판정, 격리 목록, flaky 통계)을 기기 없이 검증한다."""
import json
from types import SimpleNamespace

import pytest

from ivi import quarantine
from ivi.results import Recorder
from tools import flaky_report


def report(nodeid, when, outcome, duration=1.0, keywords=(), wasxfail=None, message="", props=()):
    rep = SimpleNamespace(
        nodeid=nodeid, when=when, outcome=outcome, duration=duration,
        passed=outcome == "passed", failed=outcome == "failed", skipped=outcome == "skipped",
        keywords={k: 1 for k in keywords}, user_properties=list(props),
        longrepr=SimpleNamespace(reprcrash=SimpleNamespace(message=message)) if message else None,
        longreprtext=message,
    )
    if wasxfail is not None:
        rep.wasxfail = wasxfail
    return rep


def run(recorder, nodeid, *phases):
    for when, outcome, extra in phases:
        recorder.add(report(nodeid, when, outcome, **extra))


@pytest.fixture
def recorder():
    return Recorder("run1", {"serial": "s1", "kind": "mock", "model": "m"})


def test_outcomes_are_classified(recorder):
    ok, none = ("passed", {}), {}
    run(recorder, "t::pass", ("setup", "passed", none), ("call", "passed", none), ("teardown", "passed", none))
    run(recorder, "t::flaky",
        ("setup", "passed", none), ("call", "rerun", {"message": "AssertionError: 첫 시도"}), ("teardown", "passed", none),
        ("setup", "passed", none), ("call", "passed", none), ("teardown", "passed", none))
    run(recorder, "t::fail", ("setup", "passed", none), ("call", "failed", {"message": "boom"}), ("teardown", "passed", none))
    run(recorder, "t::setup_error", ("setup", "failed", {"message": "앱이 안 뜸"}), ("teardown", "passed", none))
    run(recorder, "t::known", ("setup", "passed", none), ("call", "skipped", {"wasxfail": "알려진 결함"}), ("teardown", "passed", none))
    run(recorder, "t::quarantined",
        ("setup", "passed", {"keywords": ["quarantined"]}),
        ("call", "passed", {"keywords": ["quarantined"], "wasxfail": "격리"}),
        ("teardown", "passed", {"keywords": ["quarantined"]}))

    got = {rec["nodeid"]: rec for rec in recorder.records.values()}
    assert got["t::pass"]["outcome"] == "passed"
    assert got["t::flaky"]["outcome"] == "flaky" and got["t::flaky"]["reruns"] == 1
    assert got["t::flaky"]["first_error"] == "AssertionError: 첫 시도"
    assert got["t::fail"]["outcome"] == "failed"
    assert got["t::setup_error"]["outcome"] == "error"
    assert got["t::known"]["outcome"] == "xfailed"
    assert got["t::quarantined"]["outcome"] == "quarantined"
    assert got["t::quarantined"]["quarantine_result"] == "passed"
    assert recorder.summary()["gate"] == "fail"  # failed·error 가 있으면 게이트 실패


def test_relaunch_is_counted_once_per_test(recorder):
    props = [("app_relaunch", "1회차에 앱이 화면에 없음")]
    run(recorder, "t::r", ("setup", "passed", {"props": props}), ("call", "passed", {"props": props}),
        ("teardown", "passed", {"props": props}))
    assert recorder.records["t::r"]["relaunches"] == 1
    assert recorder.summary()["gate"] == "pass"


def test_quarantine_parse_and_match():
    entries = quarantine.parse("""
        # 주석
        tests/test_media.py::test_play | 화웨이 간헐 실패 | 2026-11-13
        tests/test_climate.py::test_limits[passenger] | 한 조합만 | 2026-11-13   # 줄 끝 주석
    """)
    assert len(entries) == 2
    assert quarantine.find(entries, "tests/test_media.py::test_play")
    assert quarantine.find(entries, "tests/test_media.py::test_play[up]")       # 매개변수 전체
    assert not quarantine.find(entries, "tests/test_media.py::test_play_pause")  # 이름 앞부분만 같은 다른 테스트
    assert quarantine.find(entries, "tests/test_climate.py::test_limits[passenger]")
    assert not quarantine.find(entries, "tests/test_climate.py::test_limits[driver]")


def test_quarantine_rejects_entry_without_reason():
    with pytest.raises(ValueError, match="형식"):
        quarantine.parse("tests/test_x.py::test_y")


def _rows(kind, nodeid, outcomes, start=0):
    return [{"run_id": f"r{start + i:02d}", "time": f"2026-11-13T10:{start + i:02d}:00", "serial": "s", "kind": kind,
             "model": "m", "nodeid": nodeid, "outcome": o, "duration": 2.0, "relaunches": 0,
             "first_error": "AssertionError: x" if o in ("flaky", "failed") else "", "message": "",
             **({"quarantine_result": "passed"} if o == "quarantined" else {})} for i, o in enumerate(outcomes)]


def test_flaky_report_finds_candidates_and_releases():
    rows = (_rows("mock", "t::stable", ["passed"] * 10)
            + _rows("mock", "t::shaky", ["passed", "flaky", "passed", "passed", "failed", "passed", "passed", "passed", "passed", "passed"])
            + _rows("aaos", "t::fixed", ["quarantined"] * 20))
    entries = quarantine.parse("t::fixed | 고침 | 2026-11-01")
    run_summary, stats, candidates, releases = flaky_report.analyze(rows, threshold=0.1, min_runs=5, release_streak=20,
                                                                    quarantined=entries)
    assert [s["nodeid"] for s in candidates] == ["t::shaky"]
    assert [s["nodeid"] for s in releases] == ["t::fixed"]
    shaky = next(s for s in stats if s["nodeid"] == "t::shaky")
    assert shaky["flaky"] == 1 and shaky["failed"] == 1 and shaky["unstable_rate"] == pytest.approx(0.2)
    assert run_summary["mock"]["runs"] == 10 and run_summary["mock"]["gate_pass"] == 9


def test_flaky_report_keep_last_runs():
    rows = _rows("mock", "t::a", ["failed"] * 5 + ["passed"] * 5)
    recent = flaky_report.keep_last_runs(rows, 5)
    assert {r["outcome"] for r in recent} == {"passed"}


def test_flaky_report_cli_writes_markdown(tmp_path):
    history = tmp_path / "results.jsonl"
    history.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in _rows("mock", "t::a", ["passed"] * 3)), encoding="utf-8")
    out = tmp_path / "report.md"
    assert flaky_report.main(["--history", str(history), "--out", str(out)]) == 0
    assert "# Flaky 리포트" in out.read_text(encoding="utf-8")


def test_vhal_retry_is_counted(recorder):
    props = [("vhal_retry", "VHAL --set 0x11600207=0.0: 2번째에 성공")]
    run(recorder, "t::v", ("setup", "passed", {}), ("call", "passed", {}), ("teardown", "passed", {"props": props}))
    assert recorder.records["t::v"]["infra_retries"] == 1
    assert recorder.records["t::v"]["outcome"] == "passed"
    assert recorder.summary()["infra_retries"] == 1
