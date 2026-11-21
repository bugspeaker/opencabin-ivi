"""앱이 테스트 도중 죽었는지(크래시, ANR) logcat 으로 판정한다.

화면만 보면 앱이 죽었다가 다시 떠도 알 수 없다. 다음 테스트의 am start 가 앱을 다시 띄우기 때문이다.
그래서 테스트마다 시작 시각(conftest 의 ivi_log_since) 이후의 crash·system 버퍼에서 이 앱의
  - FATAL EXCEPTION (자바·코틀린 예외로 프로세스가 죽음, AndroidRuntime)
  - Fatal signal    (네이티브 크래시, libc. 줄 끝에 '(프로세스 이름)')
  - ANR in <앱>     (응답 없음, ActivityManager)
을 찾고, 있으면 그 테스트를 실패로 한다(AppCrashed). 다른 앱(예: Appium 의 UiAutomator2 서버)의 크래시는 보지 않는다.

시작 시각은 초 단위라, 앞 테스트의 마지막 1초 안에 난 크래시가 다음 테스트에 잡힐 수 있다.
"""
import re

# logcat -v threadtime: '11-19 09:55:03.956  6475  6499 E AndroidRuntime: FATAL EXCEPTION: main'
LINE = re.compile(r"^\d\d-\d\d \d\d:\d\d:\d\d\.\d+\s+(\d+)\s+\d+\s+[VDIWEFA]\s+(.*?)\s*: (.*)$")
BLOCK_LINES = 40     # 크래시 하나에 남기는 줄 수 (스택 앞부분)
SCAN_LINES = 400     # FATAL EXCEPTION 뒤로 같은 프로세스의 줄을 찾는 범위 (다른 프로세스 로그가 끼어든다)


class AppCrashed(AssertionError):
    """테스트 도중 앱이 죽었거나 응답하지 않았다(logcat). 알려진 결함의 증상(DefectReproduced)이 아니므로 xfail 로 받지 않는다."""


def _is_app(process, package):
    """'dev.opencabin.ivi' 와 그 하위 프로세스 'dev.opencabin.ivi:remote' 는 이 앱, 'dev.opencabin.ivi.test' 는 다른 앱."""
    return process == package or process.startswith(package + ":")


def find_app_crashes(log, package):
    """log(logcat -v threadtime 출력)에서 package 의 크래시와 ANR 을 찾는다. 하나에 한 덩어리(여러 줄 문자열)씩 돌려준다."""
    lines = log.splitlines()
    found = []
    for index, line in enumerate(lines):
        match = LINE.match(line)
        if not match:
            continue
        pid, tag, message = match.groups()
        if message.startswith("FATAL EXCEPTION"):
            block = [line]
            for later in lines[index + 1:index + 1 + SCAN_LINES]:
                other = LINE.match(later)
                if not other or other.group(1) != pid or other.group(2) != tag:
                    continue
                if other.group(3).startswith("FATAL EXCEPTION"):
                    break
                block.append(later)
                if len(block) >= BLOCK_LINES:
                    break
            process = re.search(r"Process: ([^,\s]+)", "\n".join(block[:3]))
            if process and _is_app(process.group(1), package):
                found.append("\n".join(block))
        elif anr := re.match(r"ANR in (\S+)", message):
            if _is_app(anr.group(1), package):
                found.append(line)
        elif "Fatal signal" in message:
            process = re.search(r"\(([^()\s]+)\)\s*$", message)
            if process and _is_app(process.group(1), package):
                found.append(line)
    return found


def crash_message(crashes):
    """실패 메시지: 몇 건인지와 첫 덩어리의 앞부분."""
    head = "\n".join(crashes[0].splitlines()[:8])
    return f"테스트 도중 앱이 죽었거나 응답하지 않았다 (logcat {len(crashes)}건, 전체는 실패 자료의 app_crash.txt):\n{head}"
