import re
import subprocess

AUTOMOTIVE_FEATURE = "android.hardware.type.automotive"


class AdbError(RuntimeError):
    pass


class Adb:
    """기기 하나에 대한 adb 명령. 결과는 줄바꿈을 \\n 으로 맞춘 문자열."""

    def __init__(self, serial):
        self.serial = serial

    def run(self, *args, timeout=30, check=True):
        done = subprocess.run(["adb", "-s", self.serial, *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
        out = done.stdout.replace("\r", "")
        if check and done.returncode != 0:
            raise AdbError(f"adb {' '.join(args)} 실패 ({done.returncode}): {done.stderr.strip() or out.strip()}")
        return out

    def shell(self, *args, timeout=30, check=True):
        return self.run("shell", *args, timeout=timeout, check=check)

    # ---- 기기 정보 ----
    def is_automotive(self):
        return f"feature:{AUTOMOTIVE_FEATURE}" in self.shell("pm", "list", "features")

    def current_user(self):
        """AAOS 는 운전자 화면이 사용자 10 이다. 일반 기기는 0."""
        return int(self.shell("am", "get-current-user").strip())

    def model(self):
        return self.shell("getprop", "ro.product.model").strip()

    # ---- 액티비티 ----
    def start_activity(self, component, user=None, fresh=False, clear_task=False):
        args = ["am", "start", "-W"]
        if fresh:
            args.append("-S")  # 프로세스를 먼저 종료
        if clear_task:
            args.append("--activity-clear-task")  # 프로세스는 두고 이전 화면들만 비운다
        if user is not None:
            args += ["--user", str(user)]
        out = self.shell(*args, "-n", component)
        if "Error" in out:
            raise AdbError(f"{component} 실행 실패: {out.strip()}")
        return out

    def resumed_activities(self):
        """화면(디스플레이)마다 맨 위에 있는 액티비티 목록. AAOS 에뮬레이터는 메인 + 클러스터 2개다."""
        out = self.shell("dumpsys", "activity", "activities")
        # AAOS(API 34): 'topResumedActivity=ActivityRecord{…}' (디스플레이마다)
        # 화웨이(Android 12 기반): 'mResumedActivity: ActivityRecord{…}' 만 나온다 (5단계 재점검에서 발견)
        found = re.findall(r"topResumedActivity=ActivityRecord\{\S+ u\d+ (\S+) t-?\d+\}", out)
        if not found:
            found = re.findall(r"mResumedActivity: ActivityRecord\{\S+ u\d+ (\S+) t-?\d+\}", out)
        return found

    # ---- 로그 ----
    def logcat_clear(self):
        self.run("logcat", "-c", check=False)

    def logcat_dump(self, lines=3000):
        return self.run("logcat", "-d", "-t", str(lines), "-v", "threadtime", check=False, timeout=60)

    def screencap_displays(self):
        out = self.shell("dumpsys", "SurfaceFlinger", "--display-id", check=False)
        return re.findall(r"Display (\d+)", out)
