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


def test_publish_results_reads_test_docs_and_markers():
    """결과 페이지용 메타데이터: 테스트 파일에서 설명(docstring)과 마커를 읽는다."""
    from tools import publish_results

    files = {f["file"]: f for f in publish_results.read_tests()}
    signals = {t["name"]: t for t in files["test_vehicle_signals.py"]["tests"]}
    assert "sanity" in signals["test_max_ac_sets_signal_and_coldest_settings"]["markers"]
    # 여러 줄 docstring 은 한 줄로 이어 붙인다
    assert signals["test_max_ac_sets_signal_and_coldest_settings"]["doc"].startswith("FULL(최대 냉방)을 켜면")
    assert "\n" not in signals["test_low_range_card_starts_guidance_to_nearest_charger"]["doc"]
    assert files["test_smoke.py"]["title"].startswith("빌드가 나오면")


def test_publish_results_markdown_has_anchor_per_test():
    """GitHub 문서(docs/test-results.md)에서 테스트 이름마다 앵커가 있어야 다른 문서의 링크가 닿는다."""
    from tools import publish_results

    data = {"devices": [{"kind": "aaos", "label": "AAOS 에뮬레이터", "model": "m", "time": "2026-11-18T10:00:00",
                         "duration": 75.0, "counts": {"passed": 2}}],
            "files": [{"file": "test_x.py", "title": "제목", "tests": [
                {"name": "test_a", "doc": "설명", "markers": ["sanity"], "cases": [
                    {"param": "up", "results": {"aaos": {"label": "통과", "duration": 1.2, "image": "img/aaos/test_a_up.webp"}}},
                    {"param": "down", "results": {"aaos": {"label": "통과", "duration": 1.1, "image": None}}}]}]}]}
    md = publish_results.markdown(data)
    assert md.count('<a id="test_a"></a>') == 1
    assert "[화면](../site/results/img/aaos/test_a_up.webp)" in md
    assert "1분 15초" in md


def test_recorder_keeps_last_attempt_screenshot():
    """--shots: 끝 화면 경로를 기록에 남긴다. 재시도가 있으면 마지막 시도의 화면이다."""
    rec = Recorder("run", {"serial": "s", "kind": "aaos", "model": "m"})
    rec.add(report("t::a", "call", "rerun", message="boom", props=[("shot", "first.png")]))
    rec.add(report("t::a", "call", "passed", props=[("shot", "second.png")]))
    row = rec.rows()[0]
    assert (row["outcome"], row["shot"]) == ("flaky", "second.png")


def test_publish_results_blurs_only_given_box(tmp_path):
    """번호판 가리기: --blur 로 준 영역만 흐려지고 나머지 화면은 그대로다."""
    from PIL import Image
    from tools import publish_results

    assert publish_results.parse_blur(["aaos/test_x:10,20,30,40", "aaos/test_x:0,0,5,5"]) == {
        "aaos/test_x": [(10, 20, 40, 60), (0, 0, 5, 5)]}

    path = tmp_path / "shot.webp"
    image = Image.new("RGB", (100, 100), "white")
    for x in range(0, 100, 2):  # 세로 줄무늬: 흐리면 회색이 된다
        for y in range(100):
            image.putpixel((x, y), (0, 0, 0))
    image.save(path, "WEBP", lossless=True)

    publish_results.blur(path, [(40, 40, 80, 80)])
    with Image.open(path) as out:
        inside, outside = out.convert("L").getpixel((60, 60)), out.convert("L").getpixel((10, 10))
    assert 60 < inside < 200, "영역 안이 흐려지지 않았다"
    assert outside < 60 or outside > 200, "영역 밖까지 흐려졌다"
