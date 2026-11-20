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

실행 하나의 게이트(summary["gate"])는 테스트 판정만 보지 않는다. pytest 종료 코드가 0 이 아니거나(중단, 내부 오류, 수집 0개),
수집한 테스트보다 판정이 적으면(중간에 멈춤) 'fail' 이다. '실패한 테스트가 없다'와 '정한 검증을 끝까지 했다'는 다르다.
"""
import json
import subprocess
import time
from pathlib import Path

QUARANTINE_KEYWORD = "quarantined"

# pytest 종료 코드 (pytest.ExitCode). 0 이 아니면 결과 파일의 판정이 모두 통과여도 실행을 믿지 않는다
EXIT_CODES = {0: "정상 종료", 1: "실패한 테스트 있음", 2: "중단됨", 3: "pytest 내부 오류", 4: "명령 사용 오류", 5: "수집된 테스트 없음"}


def code_version(root):
    """결과 파일에 남길 코드 버전: {"commit": 커밋 해시, "dirty": 커밋하지 않은 변경이 있는가}. git 이 없으면 빈 값."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip()
    try:
        commit = git("rev-parse", "HEAD")
        # 실행 중에 생기는 reports/ 는 .gitignore 에 있어 여기에 잡히지 않는다
        dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    except (OSError, subprocess.SubprocessError):
        return {"commit": "", "dirty": False}
    return {"commit": commit, "dirty": dirty and bool(commit)}


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
    def __init__(self, run_id, device, code=None):
        self.run_id = run_id
        self.device = device  # {"serial", "kind", "model"}
        self.code = code or {}  # {"commit", "dirty"} (code_version). 요약에만 남긴다
        self.records = {}
        self.started = time.time()

    def _record(self, report):
        return self.records.setdefault(report.nodeid, {
            "nodeid": report.nodeid,
            "outcome": None,
            "reruns": 0,
            "relaunches": 0,
            "infra_retries": 0,
            "session_restarts": 0,
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
        restarts = [value for key, value in report.user_properties if key == "session_restart"]
        if restarts:  # Appium 세션을 다시 붙인 일 (ivi/session.py). 이유는 마지막 것
            rec["session_restarts"] = max(rec["session_restarts"], len(restarts))
            rec["session_restart_reason"] = restarts[-1]
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
            if rec["outcome"] in ("failed", "error"):
                # 준비·본문에서 이미 실패했으면 그 원인을 지우지 않는다 (정리 실패는 대개 앞 실패의 결과다)
                rec["message"] = f"{rec['message']}\n(정리 단계도 실패: {_reason(report)})"
            else:
                rec["outcome"] = "error"
                rec["message"] = f"정리 단계 실패: {_reason(report)}"

        if rec["quarantined"] and rec["outcome"] in ("xfailed", "xpassed"):
            # 격리 중에도 실제 결과는 남긴다 (해제 판단: 연속 통과 횟수)
            rec["quarantine_result"] = "passed" if rec["outcome"] == "xpassed" else "failed"
            rec["outcome"] = "quarantined"

    def rows(self):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.started))
        return [{"run_id": self.run_id, "time": stamp, **self.device, **rec} for rec in self.records.values()]

    def summary(self, exitstatus=None, collected=None):
        """exitstatus: pytest 종료 코드, collected: 이번 실행이 고른 테스트 수. 둘 다 None 이면(단위 테스트) 판정만 본다."""
        counts = {}
        for rec in self.records.values():
            counts[str(rec["outcome"])] = counts.get(str(rec["outcome"]), 0) + 1
        problems = []
        if counts.get("failed") or counts.get("error"):
            problems.append(f"failed {counts.get('failed', 0)}, error {counts.get('error', 0)}")
        unfinished = [rec["nodeid"] for rec in self.records.values() if rec["outcome"] is None]
        if unfinished:
            problems.append(f"판정 없이 끝난 테스트 {len(unfinished)}개 (예: {unfinished[0]})")
        if collected is not None and len(self.records) < collected:
            problems.append(f"고른 테스트 {collected}개 가운데 {len(self.records)}개만 돌았다")
        if exitstatus not in (None, 0) and not (exitstatus == 1 and problems):
            problems.append(f"pytest 종료 코드 {exitstatus} ({EXIT_CODES.get(exitstatus, '알 수 없음')})")
        return {
            "run_id": self.run_id,
            **self.device,
            **self.code,
            "duration": round(time.time() - self.started, 1),
            "counts": counts,
            "relaunches": sum(rec["relaunches"] for rec in self.records.values()),
            "infra_retries": sum(rec["infra_retries"] for rec in self.records.values()),
            "session_restarts": sum(rec["session_restarts"] for rec in self.records.values()),
            **({"exitstatus": exitstatus} if exitstatus is not None else {}),
            **({"collected": collected} if collected is not None else {}),
            "gate": "fail" if problems else "pass",
            **({"problems": problems} if problems else {}),
        }

    def write(self, report_dir, exitstatus=None, collected=None):
        report_dir = Path(report_dir)
        history = report_dir / "history" / "results.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open("a", encoding="utf-8") as out:
            for row in self.rows():
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary = self.summary(exitstatus, collected)
        run_file = report_dir / "runs" / f"{self.run_id}-{self.device['serial']}.json"
        run_file.parent.mkdir(parents=True, exist_ok=True)
        run_file.write_text(json.dumps({"summary": summary, "tests": self.rows()}, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary, run_file


def _skip_reason(report):
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return str(longrepr or "")
