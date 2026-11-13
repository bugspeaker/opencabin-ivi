"""격리 목록 (quarantine.txt).

자주 흔들리는(flaky) 테스트를 원인 분석 동안 게이트에서 빼되, **계속 돌려서 데이터는 모은다.**
격리된 테스트는 xfail(strict=False) 로 바뀌어 실패해도 빌드를 막지 않고, 결과 기록에는 'quarantined' 로 남는다.

형식 (한 줄에 하나, # 은 주석):
    <nodeid 또는 앞부분> | <이유> | <등록일>
    tests/test_media.py::test_play_pause_toggles | 화웨이에서 간헐 실패, 원인 분석 중 | 2026-11-13
nodeid 앞부분만 쓰면 매개변수가 다른 경우(…[driver], …[passenger])까지 함께 격리된다.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    pattern: str
    reason: str
    since: str

    def matches(self, nodeid):
        return nodeid == self.pattern or nodeid.startswith(self.pattern + "[") or nodeid.startswith(self.pattern + "::")


def parse(text):
    entries = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(f"quarantine.txt {number}번째 줄: '<nodeid> | <이유> | <등록일>' 형식이 아니다: {raw!r}")
        entries.append(Entry(parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return entries


def load(path):
    path = Path(path)
    return parse(path.read_text(encoding="utf-8")) if path.exists() else []


def find(entries, nodeid):
    return next((entry for entry in entries if entry.matches(nodeid)), None)
