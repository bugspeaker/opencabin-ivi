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


def test_failure_without_cause_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(rh, "PURPOSE", {"2026-11-24-a/runs": ("반복", False)})
    monkeypatch.setattr(rh, "CAUSES", {})
    _run(tmp_path / "2026-11-24-a/runs/r1.json", "20261124-r1", ["failed"])
    assert rh.summarize(rh.load(tmp_path))["missing"]["cause"] == ["20261124-r1 tests/test_a.py::test_0"]
