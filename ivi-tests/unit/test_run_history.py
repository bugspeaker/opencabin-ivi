"""전체 실행 기록(tools/run_history.py)을 기기 없이 검증한다.

근거 자료에 결과 파일이 늘었는데 기록을 다시 만들지 않았거나, 실패·오류·재시도 통과에 원인을 적지 않았으면 여기서 실패한다
(원인 없는 실패가 숫자로만 남지 않게)."""
import json

from tools import run_history as rh


def test_history_matches_evidence_and_every_failure_has_a_cause():
    h = rh.summarize(rh.load(rh.REPO / "docs" / "evidence"))
    assert h["missing"]["purpose"] == [], "근거 폴더의 목적을 tools/run_history.py 의 PURPOSE 에 적으세요"
    assert h["missing"]["cause"] == [], "실패·오류·재시도 통과의 원인을 tools/run_history.py 의 CAUSES 에 적으세요"
    md, js = rh.render(h)
    assert (rh.REPO / "docs" / "run-history.md").read_text(encoding="utf-8") == md, "tools/run_history.py 로 다시 만드세요"
    assert (rh.REPO / "site" / "results" / "history.json").read_text(encoding="utf-8") == js, "tools/run_history.py 로 다시 만드세요"


def _run(path, run_id, outcomes, model="DBY-W09"):
    path.parent.mkdir(parents=True, exist_ok=True)
    tests = [{"nodeid": f"tests/test_a.py::test_{i}", "outcome": o, "reruns": 1 if o == "flaky" else 0, "time": f"2026-11-24T10:00:0{i}"}
             for i, o in enumerate(outcomes)]
    path.write_text(json.dumps({"summary": {"run_id": run_id, "serial": "S1", "kind": "mock", "model": model,
                                            "counts": {}, "duration": 1.0}, "tests": tests}), encoding="utf-8")


def test_totals_skip_intentional_runs_and_count_each_run_once(tmp_path, monkeypatch):
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-24-a/runs": ("반복", False), "2026-11-24-a/copy": ("복사본", False),
                                        "2026-11-24-a/probe": ("판정 확인", True)})
    monkeypatch.setattr(rh, "CAUSES", {"20261124-r1": ("환경", "USB 창"), "20261124-probe": ("확인용", "일부러 죽임")})
    _run(tmp_path / "2026-11-24-a/runs/r1.json", "20261124-r1", ["passed", "flaky", "error", "skipped"])
    _run(tmp_path / "2026-11-24-a/copy/r1.json", "20261124-r1", ["passed", "flaky", "error", "skipped"])  # 같은 실행
    _run(tmp_path / "2026-11-24-a/probe/p.json", "20261124-probe", ["failed"])

    h = rh.summarize(rh.load(tmp_path))

    assert h["total"]["sessions"] == 1 and h["total"]["executed"] == 3
    assert (h["total"]["passed"], h["total"]["flaky"], h["total"]["bad"]) == (1, 1, 1)
    assert [p["outcome"] for p in h["problems"]] == ["재시도 후 통과", "오류", "실패"]  # 일부러 만든 실패도 표에는 남긴다
    assert h["missing"] == {"purpose": [], "cause": []}


def test_date_comes_from_test_time_when_run_id_has_no_date(tmp_path, monkeypatch):
    """결함 주입 실행(fi-F01-aaos)처럼 run id 가 날짜로 시작하지 않으면 테스트 시각에서 날짜를 읽는다."""
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-25-fi/runs": ("결함 주입", True)})
    monkeypatch.setattr(rh, "CAUSES", {})
    _run(tmp_path / "2026-11-25-fi/runs/f.json", "fi-F01-aaos", ["failed"])
    _run(tmp_path / "2026-11-25-fi/runs/d.json", "20261123-r1", ["passed"])
    h = rh.summarize(rh.load(tmp_path))
    assert [p["date"] for p in h["problems"]] == ["11-24"]
    assert h["total"]["sessions"] == 0  # 결함을 일부러 넣은 실행은 합계에서 뺀다
    # 결함 주입 빌드의 실패는 결함 때문에 난 것이라 원인이 저절로 붙는다
    assert h["problems"][0]["kind"] == "확인용" and "F01" in h["problems"][0]["why"]
    assert h["missing"]["cause"] == []


def test_test_cause_overrides_fault_build_cause_and_intro_names_skipped_runs(tmp_path, monkeypatch):
    """결함 빌드에서도 결함과 상관없는 실패(adb 끊김 등)는 테스트마다 적은 원인이 먼저 붙는다.
    머리말은 합계에서 뺀 실행을 종류별 횟수로 적는다."""
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-25-fi/runs": ("결함 주입", True), "2026-11-21-k/runs": ("크래시 확인", True)})
    monkeypatch.setattr(rh, "INTENTIONAL_NAME", {"2026-11-25-fi/runs": "결함 주입 실행"})
    monkeypatch.setattr(rh, "CAUSES", {"20261121-k": ("확인용", "일부러 죽임")})
    monkeypatch.setattr(rh, "TEST_CAUSES", {("fi-F01-aaos", "tests/test_a.py::test_0"): ("환경", "adb 끊김")})
    _run(tmp_path / "2026-11-25-fi/runs/f.json", "fi-F01-aaos", ["flaky", "failed"])
    _run(tmp_path / "2026-11-25-fi/runs/g.json", "fi-F02-aaos", ["failed"])
    _run(tmp_path / "2026-11-21-k/runs/k.json", "20261121-k", ["failed"])
    h = rh.summarize(rh.load(tmp_path))
    why = {(p["run_id"], p["test"]): (p["kind"], p["why"]) for p in h["problems"]}
    assert why[("fi-F01-aaos", "test_0")] == ("환경", "adb 끊김")
    assert why[("fi-F01-aaos", "test_1")][0] == "확인용"
    md, _ = rh.render(h)
    assert "결함 주입 실행 2회" in md and "크래시 확인 1회" in md


def test_control_failure_in_fault_injection_still_needs_a_cause(tmp_path, monkeypatch):
    """대조군(F00)은 결함이 없는 빌드라 실패하면 원인을 따로 적어야 한다."""
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-25-fi/runs": ("결함 주입", True)})
    monkeypatch.setattr(rh, "CAUSES", {})
    _run(tmp_path / "2026-11-25-fi/runs/c.json", "fi-F00-aaos", ["failed"])
    assert rh.summarize(rh.load(tmp_path))["missing"]["cause"] == ["fi-F00-aaos tests/test_a.py::test_0"]


def test_failure_without_cause_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-24-a/runs": ("반복", False)})
    monkeypatch.setattr(rh, "CAUSES", {})
    _run(tmp_path / "2026-11-24-a/runs/r1.json", "20261124-r1", ["failed"])
    assert rh.summarize(rh.load(tmp_path))["missing"]["cause"] == ["20261124-r1 tests/test_a.py::test_0"]
