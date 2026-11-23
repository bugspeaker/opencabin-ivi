"""결과 게시 도구(tools/publish_results.py)의 기기 칸 나누기와 --add 를 기기 없이 검증한다.

태블릿과 갤럭시 폴드는 둘 다 Mock 기기라, 기기 종류로만 묶으면 한쪽 결과가 다른 쪽을 덮어쓴다."""
import json

from tools import publish_results as pr

FILES = [{"file": "test_a.py", "title": "A", "tests": [{"name": "test_ok", "doc": "", "markers": ["smoke"]}]}]
STABILITY = {"rounds": 3, "devices": 2, "run_ids": ["r1", "r2", "r3"], "executions": 6, "flaky": 0, "failed": 0}


def device(kind, run_id, version, time="2026-11-21T12:36:11"):
    return {"kind": kind, "type": "aaos" if kind == "aaos" else "mock", "label": pr.COLUMNS[kind], "model": "", "serial": kind, "run_id": run_id, "time": time,
            "duration": 600.0, "counts": {"passed": 1}, "gate": "pass", "commit": "a" * 40, "dirty": False,
            "app": {"version": version, "apk_sha256": "c" * 64}, "command": ""}


def result(outcome="passed"):
    return {"outcome": outcome, "label": pr.OUTCOME_LABEL[outcome], "duration": 1.0, "message": "", "image": None,
            "reruns": 0, "measures": {}, "signals": []}


def fold_run():
    return {"summary": {"kind": "mock", "model": "SM-F900F", "serial": "R38M309YKQY", "run_id": "fold-after",
                        "duration": 710.8, "counts": {"passed": 1}, "gate": "pass", "commit": "b" * 40,
                        "dirty": False, "app": {"version": "0.4.1 (5)", "apk_sha256": "d" * 64}},
            "tests": [{"nodeid": "tests/test_a.py::test_ok", "outcome": "passed", "duration": 2.0,
                       "time": "2026-11-23T14:00:00"}]}


def test_fold_gets_its_own_column_apart_from_the_tablet():
    assert pr.column(fold_run()) == "fold"
    assert pr.column({"summary": {"kind": "mock", "model": "DBY-W09"}}) == "mock"
    assert pr.column({"summary": {"kind": "aaos", "model": "Car on x86_64 emulator"}}) == "aaos"


def test_add_keeps_other_columns_images_and_stability(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "SITE_RESULTS", tmp_path / "results")
    monkeypatch.setattr(pr, "DOC", tmp_path / "test-results.md")
    monkeypatch.setattr(pr, "read_tests", lambda: json.loads(json.dumps(FILES)))
    kept_image = tmp_path / "results" / "img" / "aaos" / "test_ok.webp"
    kept_image.parent.mkdir(parents=True)
    kept_image.write_bytes(b"webp")
    base = {"devices": [device("aaos", "r3", "0.4.0 (4)"), device("mock", "r3", "0.4.0 (4)")],
            "files": [{**FILES[0], "tests": [{**FILES[0]["tests"][0],
                                              "cases": [{"param": "", "results": {"aaos": result(), "mock": result()}}]}]}],
            "stability": STABILITY}

    data, missing = pr.build({"fold": fold_run()}, base=base)

    assert [d["kind"] for d in data["devices"]] == ["aaos", "mock", "fold"]
    assert [d["type"] for d in data["devices"]] == ["aaos", "mock", "mock"]
    assert set(data["files"][0]["tests"][0]["cases"][0]["results"]) == {"aaos", "mock", "fold"}
    assert data["stability"] == STABILITY
    assert kept_image.exists()
    assert missing == []
    doc = pr.DOC.read_text(encoding="utf-8")
    assert "| 테스트 | AAOS 에뮬레이터 | 태블릿 (Mock) | 갤럭시 폴드 (Mock) |" in doc


def test_note_says_which_run_each_device_comes_from():
    data = {"devices": [device("aaos", "r3", "0.4.0 (4)"), device("mock", "r3", "0.4.0 (4)"),
                        device("fold", "fold-after", "0.4.1 (5)", time="2026-11-23T14:00:00")],
            "stability": STABILITY}
    note = pr.run_note(data, "flaky-report.md")
    assert note.startswith("AAOS 에뮬레이터와 태블릿은 3회 반복한 실행의 마지막 회차(앱 0.4.0 (4))이고")
    assert note.endswith("갤럭시 폴드는 2026-11-23에 따로 돌린 실행(앱 0.4.1 (5))입니다.")
    assert pr.device_note(data).startswith("태블릿과 갤럭시 폴드는 ")
