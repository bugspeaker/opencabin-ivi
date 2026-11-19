"""실행 결과 기록: 테스트마다 최종 판정·재시도·앱 재실행·시간을 모은다. flaky 통계(tools/flaky_report.py)의 원자료.

판정
  passed       한 번에 통과
  flaky        실패 후 재시도에서 통과 (pytest-rerunfailures 의 'rerun' 이 1번 이상)
  failed       재시도까지 실패
  error        준비(setup)·정리(teardown) 실패
  skipped      건너뜀 (AAOS 전용 등)
  xfailed      알려진 결함으로 예상대로 실패
  xpassed      알려진 결함인데 통과 (strict 면 failed 로 온다)
  quarantined  격리 목록에 있는 테스트 (돌리기는 하지만 게이트를 막지 않는다)
"""
import json
import time
from pathlib import Path

QUARANTINE_KEYWORD = "quarantined"


def junit_name(run_id, kind, serial):
    """JUnit 결과 파일 이름. run id 를 넣는다: --repeat 로 돌리면 회차마다 같은 이름에 덮어써서
    Release 반복의 앞 회차 실패 기록이 사라지던 문제 (2026-11-19 검토에서 발견)."""
    return f"junit-{run_id}-{kind}-{serial}.xml"


def _reason(report):
    """실패 한 줄 요약: assert 메시지 (없으면 traceback 끝부분)."""
    crash = getattr(report.longrepr, "reprcrash", None)
    if crash is not None and crash.message:
        return _short(crash.message, 300)
    return _short(report.longreprtext, 300)


def _short(text, limit=600):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit // 2] + "\n…\n" + text[-limit // 2:]


class Recorder:
    def __init__(self, run_id, device):
        self.run_id = run_id
        self.device = device  # {"serial", "kind", "model"}
        self.records = {}
        self.started = time.time()

    def _record(self, report):
        return self.records.setdefault(report.nodeid, {
            "nodeid": report.nodeid,
            "outcome": None,
            "reruns": 0,
            "relaunches": 0,
            "infra_retries": 0,
            "duration": 0.0,
            "message": "",
            "first_error": "",
            "quarantined": QUARANTINE_KEYWORD in report.keywords,
        })

    def pytest_runtest_logreport(self, report):
        """pytest 플러그인으로 등록되면 보고서마다 불린다."""
        self.add(report)

    def add(self, report):
        """setup / call / teardown 보고서 하나 (재시도 포함)."""
        rec = self._record(report)
        rec["duration"] = round(rec["duration"] + report.duration, 3)
        relaunches = sum(1 for key, _ in report.user_properties if key == "app_relaunch")
        rec["relaunches"] = max(rec["relaunches"], relaunches)
        retries = sum(1 for key, _ in report.user_properties if key == "vhal_retry")
        rec["infra_retries"] = max(rec["infra_retries"], retries)
        signals = [value for key, value in report.user_properties if key == "vhal"]
        if signals:  # 판정에 쓴 차량 값. 재시도면 마지막 시도 것
            rec["signals"] = signals
        for key, value in report.user_properties:
            if key == "shot":  # 끝 화면 (--shots). 재시도면 마지막 시도 것
                rec["shot"] = value
            elif key.endswith("_seconds"):  # 테스트가 잰 시간 (부팅, 카메라 표시 등). 결과 페이지에 보여 준다
                rec.setdefault("measures", {})[key] = value

        if report.outcome == "rerun":
            rec["reruns"] += 1
            rec["first_error"] = rec["first_error"] or _reason(report)
            return

        if report.when == "setup":
            if report.failed:
                rec["outcome"] = "error"
                rec["message"] = _reason(report)
            elif report.skipped:
                rec["outcome"] = "xfailed" if hasattr(report, "wasxfail") else "skipped"
                rec["message"] = _skip_reason(report)
        elif report.when == "call":
            if hasattr(report, "wasxfail"):
                rec["outcome"] = "xfailed" if report.skipped else "xpassed"
                rec["message"] = report.wasxfail
            elif report.passed:
                rec["outcome"] = "flaky" if rec["reruns"] else "passed"
            elif report.failed:
                rec["outcome"] = "failed"
                rec["message"] = _reason(report)
            elif report.skipped:
                rec["outcome"] = "skipped"
                rec["message"] = _skip_reason(report)
        elif report.when == "teardown" and report.failed:
            rec["outcome"] = "error"
            rec["message"] = _reason(report)

        if rec["quarantined"] and rec["outcome"] in ("xfailed", "xpassed"):
            # 격리 중에도 실제 결과는 남긴다 (해제 판단: 연속 통과 횟수)
            rec["quarantine_result"] = "passed" if rec["outcome"] == "xpassed" else "failed"
            rec["outcome"] = "quarantined"

    def rows(self):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.started))
        return [{"run_id": self.run_id, "time": stamp, **self.device, **rec} for rec in self.records.values()]

    def summary(self):
        counts = {}
        for rec in self.records.values():
            counts[rec["outcome"]] = counts.get(rec["outcome"], 0) + 1
        return {
            "run_id": self.run_id,
            **self.device,
            "duration": round(time.time() - self.started, 1),
            "counts": counts,
            "relaunches": sum(rec["relaunches"] for rec in self.records.values()),
            "infra_retries": sum(rec["infra_retries"] for rec in self.records.values()),
            "gate": "fail" if counts.get("failed") or counts.get("error") else "pass",
        }

    def write(self, report_dir):
        report_dir = Path(report_dir)
        history = report_dir / "history" / "results.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open("a", encoding="utf-8") as out:
            for row in self.rows():
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary = self.summary()
        run_file = report_dir / "runs" / f"{self.run_id}-{self.device['serial']}.json"
        run_file.parent.mkdir(parents=True, exist_ok=True)
        run_file.write_text(json.dumps({"summary": summary, "tests": self.rows()}, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary, run_file


def _skip_reason(report):
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return str(longrepr or "")
