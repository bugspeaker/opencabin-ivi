"""conftest 의 차량 픽스처 흐름을 기기 없이 확인한다: 준비가 중간에 실패하면 실패 자료 → 정리 → 재시도 기록 순서로 돌고,
정리가 실패해도 재시도 기록은 남으며, 다음 테스트는 준비에서 처음 상태로 돌아간다.

진짜 tests/conftest.py 의 vehicle 픽스처와 _cleanup_vehicle 을 그대로 가져다 쓰고, 기기(device)만 가짜로 바꾼다.
pytest 를 따로 띄워 실제 setup/teardown 순서를 본다 (픽스처 순서는 pytest 가 정하므로 흉내로는 확인할 수 없다)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFTEST = '''
import importlib.util, json, os
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("ivi_e2e_conftest", os.environ["IVI_REAL_CONFTEST"])
real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real)
vehicle = real.vehicle   # 진짜 픽스처 (정리를 준비보다 먼저 등록하는 코드)

EVENTS, REPORTS, CURRENT = [], [], {}


class FakeVehicle:
    """준비는 정차 → 재시도 기록 → (실패할 수 있는) 두 번째 쓰기 순서. 상태는 events 에 남긴다."""
    def __init__(self, fail_prepare=False, fail_cleanup=False):
        self.fail_prepare, self.fail_cleanup = fail_prepare, fail_cleanup
        self.retried, self.state = [], {"speed": 50.0, "temp": 25.0}   # 앞 테스트가 남긴 주행 상태

    def prepare(self):
        self.state["speed"] = 0.0
        self.retried.append("VHAL --set 0x11600207=0.0: 2번째에 성공")
        if self.fail_prepare:
            EVENTS.append(("prepare_failed", dict(self.state)))
            raise RuntimeError("VHAL --set HVAC_TEMPERATURE_SET 실패 (두 번째 쓰기)")
        self.state["temp"] = 22.0
        EVENTS.append(("prepared", dict(self.state)))

    def cleanup(self):
        EVENTS.append(("cleanup", dict(self.state)))
        if self.fail_cleanup:
            raise RuntimeError("정차로 되돌리기 실패")
        self.state = {"speed": 0.0, "temp": 22.0}


class FakeDevice:
    def __init__(self, vehicle):
        self.vehicle = vehicle


@pytest.fixture
def device(request):
    marks = {m.name for m in request.node.iter_markers()}
    CURRENT["device"] = FakeDevice(FakeVehicle("fail_prepare" in marks, "fail_cleanup" in marks))
    return CURRENT["device"]   # 진짜 conftest 처럼 실패 자료는 config 쪽 기기를 본다 (funcargs 는 준비 실패 때 비어 있다)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed and report.when == "setup":
        EVENTS.append(("evidence", dict(CURRENT["device"].vehicle.state)))
    REPORTS.append({"test": item.name, "when": report.when, "outcome": report.outcome,
                    "message": str(call.excinfo.value) if call.excinfo else "",
                    "props": [list(p) for p in report.user_properties]})


def pytest_sessionfinish(session):
    Path(os.environ["IVI_FLOW_OUT"]).write_text(json.dumps({"events": EVENTS, "reports": REPORTS}), encoding="utf-8")
'''

TESTS = '''
import pytest

@pytest.mark.fail_prepare
def test_a_prepare_fails_midway(vehicle):
    pass

@pytest.mark.fail_cleanup
def test_b_cleanup_fails(vehicle):
    pass

def test_c_next_test_starts_clean(vehicle):
    assert vehicle.state == {"speed": 0.0, "temp": 22.0}
'''


def run_flow(tmp_path):
    (tmp_path / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    (tmp_path / "test_flow.py").write_text(TESTS, encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers =\n    fail_prepare\n    fail_cleanup\n", encoding="utf-8")
    out = tmp_path / "flow.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT), "IVI_REAL_CONFTEST": str(ROOT / "tests" / "conftest.py"),
           "IVI_FLOW_OUT": str(out), "PYTHONIOENCODING": "utf-8"}  # 자식 출력을 utf-8 로 읽는다 (Python 3.12 Windows 기본은 cp949)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
                          cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8")
    assert out.exists(), proc.stdout + proc.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def test_prepare_failure_keeps_evidence_then_cleans_up_and_keeps_retries(tmp_path):
    flow = run_flow(tmp_path)
    events = [name for name, _ in flow["events"]]
    # 준비 실패 → 실패 자료(그 순간 상태) → 정리. 자료를 남기기 전에 정리가 돌면 실패 순간의 차량 상태가 사라진다
    assert events[:3] == ["prepare_failed", "evidence", "cleanup"]
    assert flow["events"][1][1] == {"speed": 0.0, "temp": 25.0}   # 자료에는 반쯤 준비된 상태가 그대로 남는다

    reports = {(r["test"], r["when"]): r for r in flow["reports"]}
    assert reports[("test_a_prepare_fails_midway", "setup")]["outcome"] == "failed"
    assert "두 번째 쓰기" in reports[("test_a_prepare_fails_midway", "setup")]["message"]
    # 준비 중의 신호 재시도 기록이 버려지지 않고 그 테스트의 결과로 간다
    assert ["vhal_retry", "VHAL --set 0x11600207=0.0: 2번째에 성공"] in reports[("test_a_prepare_fails_midway", "teardown")]["props"]


def test_cleanup_failure_still_records_retries_and_next_test_is_isolated(tmp_path):
    flow = run_flow(tmp_path)
    reports = {(r["test"], r["when"]): r for r in flow["reports"]}
    teardown = reports[("test_b_cleanup_fails", "teardown")]
    assert teardown["outcome"] == "failed" and "정차로 되돌리기 실패" in teardown["message"]
    assert any(p[0] == "vhal_retry" for p in teardown["props"])   # 정리가 실패해도 재시도 기록은 옮긴다
    # 정리가 실패해도 다음 테스트는 자기 준비에서 처음 상태로 돌아간다 (준비가 신호 전체를 기준값으로 쓴다)
    assert reports[("test_c_next_test_starts_clean", "call")]["outcome"] == "passed"
