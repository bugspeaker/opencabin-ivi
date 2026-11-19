"""격리 목록 (quarantine.txt).

자주 흔들리는(flaky) 테스트를 원인 분석 동안 게이트에서 빼되, **계속 돌려서 데이터는 모은다.**
격리된 테스트는 xfail(strict=False) 로 바뀌어 실패해도 빌드를 막지 않고, 결과 기록에는 'quarantined' 로 남는다.

형식 (한 줄에 하나, # 은 주석). 네 칸 모두 있어야 한다. 하나라도 비면 목록을 읽을 때 실패한다:
    <nodeid 또는 앞부분> | <이유> | <등록일 YYYY-MM-DD> | <해제 조건>
    tests/test_media.py::test_play_pause_toggles | 화웨이에서 간헐 실패, 원인 분석 중 | 2026-11-13 | 원인 수정 뒤 20회 연속 통과
nodeid 앞부분만 쓰면 매개변수가 다른 경우(…[driver], …[passenger])까지 함께 격리된다.
격리가 게이트를 우회하는 통로가 되지 않게, Release 게이트(tools/release_gate.py)는 이 목록이 MAX_ENTRIES 줄을 넘으면 막는다.
"""
import re
from dataclasses import dataclass
from pathlib import Path

FORMAT = "<nodeid> | <이유> | <등록일 YYYY-MM-DD> | <해제 조건>"
MAX_ENTRIES = 2  # Release 게이트에서 허용하는 격리 개수 (docs/portfolio.md 4-1)


@dataclass(frozen=True)
class Entry:
    pattern: str
    reason: str
    since: str
    release: str

    def matches(self, nodeid):
        return nodeid == self.pattern or nodeid.startswith(self.pattern + "[") or nodeid.startswith(self.pattern + "::")


def parse(text):
    entries = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 4 or not all(parts):
            raise ValueError(f"quarantine.txt {number}번째 줄: '{FORMAT}' 형식이 아니다 (네 칸 모두 필요): {raw!r}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[2]):
            raise ValueError(f"quarantine.txt {number}번째 줄: 등록일은 YYYY-MM-DD 로 쓴다: {parts[2]!r}")
        entries.append(Entry(*parts))
    return entries


def load(path):
    path = Path(path)
    return parse(path.read_text(encoding="utf-8")) if path.exists() else []


def find(entries, nodeid):
    return next((entry for entry in entries if entry.matches(nodeid)), None)
