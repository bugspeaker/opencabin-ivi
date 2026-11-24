"""지금 코드의 E2E 테스트 목록과 마커를 기기 없이 모은다. Release 게이트가 '무엇을 돌렸어야 하는가'의 기준으로 쓴다.

    python tools/collect_tests.py          # {"nodeid": ["마커", ...], ...} JSON

결과 파일(reports/runs/*.json)만 보면 실행이 고른 범위(-m smoke, 파일 하나 등)나 중간에 멈춘 실행을 알 수 없다.
그래서 결과와 상관없이 tests/ 를 다시 수집해 기준 목록을 만든다. conftest 는 --collect-only 일 때 기기에 붙지 않는다.
수집은 따로 띄운 pytest 프로세스에서 한다. 같은 프로세스에서 하면 unit/ 과 tests/ 의 같은 이름 모듈(test_can_gateway)이 부딪힌다.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_ENV = "IVI_INVENTORY_OUT"


def pytest_collection_finish(session):
    """-p tools.collect_tests 로 붙었을 때만 불린다. 수집된 테스트와 마커 이름을 OUT_ENV 파일에 쓴다."""
    out = os.environ.get(OUT_ENV)
    if out:
        inventory = {item.nodeid: sorted({mark.name for mark in item.iter_markers()}) for item in session.items}
        Path(out).write_text(json.dumps(inventory, ensure_ascii=False, indent=1), encoding="utf-8")


def collect(tests="tests"):
    """tests/ 의 모든 테스트 (매개변수 조합까지) → 마커 이름 집합."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "inventory.json"
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", tests, "--collect-only", "-q", "-p", "tools.collect_tests"],
            cwd=ROOT, env={**os.environ, OUT_ENV: str(out), "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        )
        if proc.returncode != 0 or not out.exists():
            tail = (proc.stdout + proc.stderr).strip()[-1500:]
            raise RuntimeError(f"테스트 수집 실패 (종료 코드 {proc.returncode}):\n{tail}")
        return {nodeid: set(marks) for nodeid, marks in json.loads(out.read_text(encoding="utf-8")).items()}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({nodeid: sorted(marks) for nodeid, marks in collect().items()}, ensure_ascii=False, indent=1))
