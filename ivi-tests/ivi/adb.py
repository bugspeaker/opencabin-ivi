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

    def app_identity(self, package):
        """설치된 앱의 식별값: {"version": versionName (versionCode), "apk_sha256": 기기에 있는 APK 의 sha256}.
        결과 파일에 남겨 '어느 빌드를 시험한 결과인지'를 잇는다. tools/install_app.py 가 같은 해시로 설치를 건너뛴다.
        읽지 못하면 빈 값 (결과 기록 때문에 실행이 실패하지 않게)."""
        identity = {"version": "", "apk_sha256": ""}
        try:
            path = self.shell("pm", "path", package, check=False).strip().splitlines()
            if path and path[0].startswith("package:"):
                out = self.shell("sha256sum", path[0].removeprefix("package:"), check=False).split()
                identity["apk_sha256"] = out[0] if out and len(out[0]) == 64 else ""
            dump = self.shell("dumpsys", "package", package, check=False)
            name = re.search(r"versionName=(\S+)", dump)
            code = re.search(r"versionCode=(\d+)", dump)
            if name:
                identity["version"] = name.group(1) + (f" ({code.group(1)})" if code else "")
        except (AdbError, OSError, subprocess.SubprocessError):
            pass
        return identity

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
    def log_mark(self):
        """지금 기기 시각을 logcat -T 가 받는 형식('초.밀리초', epoch)으로. 테스트를 시작할 때 찍어 두고 실패 자료를 이 시각부터 모은다.
        예전에는 테스트마다 logcat -c 로 버퍼를 지웠는데, 여러 사람·도구가 같은 기기를 쓰는 벤치에서는 남의 로그까지 지운다."""
        return self.shell("date", "+%s", check=False).strip() + ".000"

    def logcat_dump(self, since=None, lines=3000):
        """since(log_mark 값) 이후의 로그. 버퍼는 지우지 않는다. since 가 없으면 마지막 lines 줄."""
        if since:
            out = self.run("logcat", "-d", "-v", "threadtime", "-T", since, check=False, timeout=60)
            return "".join(out.splitlines(keepends=True)[-lines:])
        return self.run("logcat", "-d", "-t", str(lines), "-v", "threadtime", check=False, timeout=60)

    def screencap_displays(self):
        out = self.shell("dumpsys", "SurfaceFlinger", "--display-id", check=False)
        return re.findall(r"Display (\d+)", out)
