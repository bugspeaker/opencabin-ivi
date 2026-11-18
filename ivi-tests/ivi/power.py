"""Test Bench 기기 전원 제어.

실제 벤치에서는 헤드 유닛 전원을 프로그래머블 전원 공급기나 스마트 릴레이로 끊고 다시 넣는다.
이 프로젝트에는 그런 장비가 없어서, 같은 인터페이스(PowerController) 아래에 세 가지 구현을 둔다.

  EmulatorPower   AAOS 에뮬레이터 프로세스를 끄고(adb emu kill) 같은 설정으로 다시 켠다 (콜드 부트). 테스트에서 실제로 쓴다
  AdbRebootPower  실기기를 adb 로 재부팅한다. 끄기만 되고(reboot -p) 원격으로 켜지는 못한다
  HttpRelayPower  HTTP 로 켜고 끄는 스마트 릴레이(예: Tasmota `cm?cmnd=Power On`). 실제 벤치에 붙일 자리. 단위 테스트는 가짜 서버로 한다

cycle() 은 끄고, 켜고, 부팅이 끝날 때까지 기다린 뒤 부팅에 걸린 초를 돌려준다.
"""
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

from ivi.waits import wait_until


class PowerError(RuntimeError):
    pass


class NotSupported(PowerError):
    """이 구현으로는 할 수 없는 동작 (예: 실기기를 원격으로 켜기)."""


class PowerController(ABC):
    name = ""
    off_seconds = 2.0  # 껐다 켤 때 전원을 빼 두는 시간 (실제 벤치의 off 시간과 같은 뜻)

    @abstractmethod
    def off(self): ...

    @abstractmethod
    def on(self): ...

    @abstractmethod
    def is_on(self):
        """전원이 들어와 있고 adb 로 기기가 보이는지."""

    def wait_booted(self, timeout=180.0):
        """부팅이 끝날 때까지. 기본 구현은 is_on 만 본다."""
        wait_until(self.is_on, timeout=timeout, interval=1.0, what=f"{self.name} 켜짐")

    def cycle(self, timeout=180.0):
        """전원을 껐다 켜고 부팅이 끝날 때까지 기다린다. 켜기 시작부터 부팅 완료까지 걸린 초를 돌려준다."""
        self.off()
        time.sleep(self.off_seconds)
        started = time.monotonic()
        self.on()
        self.wait_booted(timeout=timeout)
        return time.monotonic() - started


def _adb(serial, *args, timeout=30, check=False):
    done = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    if check and done.returncode != 0:
        raise PowerError(f"adb {' '.join(args)} 실패: {(done.stdout + done.stderr).strip()[-200:]}")
    return done.returncode, (done.stdout + done.stderr).replace("\r", "").strip()


def boot_completed(serial):
    code, out = _adb(serial, "shell", "getprop", "sys.boot_completed", timeout=10)
    return code == 0 and out.strip() == "1"


class EmulatorPower(PowerController):
    """AAOS 에뮬레이터를 끄고 같은 AVD 와 같은 포트로 다시 켠다 (콜드 부트, 스냅숏 없이).

    다시 켤 때 -writable-system 을 준다. priv-app 으로 넣은 앱과 VHAL 초기값 덮어쓰기가 시스템 이미지에 남아 있어야 하기 때문이다.
    AVD 이름은 끄기 전에 `adb emu avd name` 으로 읽어 둔다.
    """
    name = "AAOS 에뮬레이터"

    def __init__(self, serial, sdk_root=None, avd_home=None, extra_args=("-writable-system", "-no-snapshot", "-no-boot-anim"),
                 log_dir=None):
        if not serial.startswith("emulator-"):
            raise PowerError(f"에뮬레이터가 아니다: {serial}")
        self.serial = serial
        self.port = serial.split("-", 1)[1]
        self.sdk_root = Path(sdk_root or os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or r"C:\android")
        self.avd_home = Path(avd_home or os.environ.get("ANDROID_AVD_HOME") or self.sdk_root / "avd")
        self.extra_args = list(extra_args)
        self.log_dir = Path(log_dir) if log_dir else None
        self.avd = None

    def avd_name(self):
        code, out = _adb(self.serial, "emu", "avd", "name", timeout=10)
        name = out.splitlines()[0].strip() if code == 0 and out else ""
        if not name or name.upper().startswith("KO"):
            raise PowerError(f"AVD 이름을 읽지 못했다: {out[-200:]}")
        return name

    def command(self):
        exe = self.sdk_root / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")
        return [str(exe), "-avd", self.avd, "-port", self.port, *self.extra_args]

    def off(self):
        if self.is_on():
            self.avd = self.avd or self.avd_name()
            _adb(self.serial, "emu", "kill", timeout=20)
        wait_until(lambda: not self._listed(), timeout=60, interval=1.0, what="에뮬레이터 꺼짐")

    def on(self):
        if not self.avd:
            raise PowerError("AVD 이름을 모른다. 켜져 있는 에뮬레이터에서 off() 를 먼저 부른다")
        env = dict(os.environ, ANDROID_SDK_ROOT=str(self.sdk_root), ANDROID_AVD_HOME=str(self.avd_home))
        out = subprocess.DEVNULL
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            out = open(self.log_dir / f"emulator-{self.port}.log", "ab")  # noqa: SIM115 - 에뮬레이터가 계속 쓴다
        flags = 0
        if os.name == "nt":  # 테스트 프로세스가 끝나도 에뮬레이터는 계속 돈다
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(self.command(), env=env, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=flags, close_fds=True)

    def _listed(self):
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        return any(line.startswith(self.serial + "\t") for line in out.splitlines())

    def is_on(self):
        return self._listed() and _adb(self.serial, "get-state", timeout=10)[1] == "device"

    def wait_booted(self, timeout=180.0):
        wait_until(lambda: self.is_on() and boot_completed(self.serial), timeout=timeout, interval=1.0,
                   what="에뮬레이터 부팅 완료")


class AdbRebootPower(PowerController):
    """실기기. 원격으로 켤 수 없어서 cycle 은 `adb reboot` 로 대신한다."""
    name = "adb 재부팅"

    def __init__(self, serial, run=_adb):
        self.serial = serial
        self._run = run

    def off(self):
        self._run(self.serial, "reboot", "-p", check=True)

    def on(self):
        raise NotSupported("실기기는 원격으로 켤 수 없다 (전원 릴레이가 필요하다)")

    def is_on(self):
        return self._run(self.serial, "get-state", timeout=10)[1] == "device"

    def wait_booted(self, timeout=180.0):
        wait_until(lambda: self.is_on() and boot_completed(self.serial), timeout=timeout, interval=1.0,
                   what="기기 부팅 완료")

    def cycle(self, timeout=180.0):
        started = time.monotonic()
        self._run(self.serial, "reboot", check=True)
        wait_until(lambda: not self.is_on(), timeout=60, interval=0.5, what="재부팅 시작")
        self.wait_booted(timeout=timeout)
        return time.monotonic() - started


class HttpRelayPower(PowerController):
    """HTTP 로 제어하는 스마트 릴레이. Tasmota 형식: GET {base}/cm?cmnd=Power%20On → {"POWER":"ON"}"""
    name = "HTTP 릴레이"

    def __init__(self, base_url, timeout=5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _command(self, command):
        url = f"{self.base_url}/cm?cmnd={urllib.parse.quote(command)}"
        with urllib.request.urlopen(url, timeout=self.timeout) as response:  # noqa: S310 - 벤치 내부 주소
            return json.loads(response.read().decode("utf-8"))

    def off(self):
        if self._command("Power Off").get("POWER") != "OFF":
            raise PowerError("릴레이가 꺼지지 않았다")

    def on(self):
        if self._command("Power On").get("POWER") != "ON":
            raise PowerError("릴레이가 켜지지 않았다")

    def is_on(self):
        return self._command("Power").get("POWER") == "ON"
