"""기기 하나: 종류 판별, 앱 실행, Appium 설정, 기기마다 다른 판정."""
import os
from dataclasses import dataclass, field

from appium.options.android import UiAutomator2Options

from ivi.adb import Adb
from ivi.vehicle import PACKAGE, AaosVehicle, MockVehicle, VehicleController

MAIN = f"{PACKAGE}/.MainActivity"
VIDEO = f"{PACKAGE}/.VideoActivity"
AAOS_BLOCKING = "ActivityBlockingActivity"
SLOW_INJECTION_BRANDS = {"HUAWEI", "HONOR"}


@dataclass
class Device:
    serial: str
    adb: Adb
    automotive: bool
    user: int
    model: str
    brand: str
    vehicle: VehicleController = field(repr=False)

    @classmethod
    def connect(cls, serial):
        adb = Adb(serial)
        automotive = adb.is_automotive()
        vehicle = AaosVehicle(adb) if automotive else MockVehicle(adb)
        brand = adb.shell("getprop", "ro.product.brand").strip()
        return cls(serial, adb, automotive, adb.current_user(), adb.model(), brand, vehicle)

    @property
    def kind(self):
        return self.vehicle.kind

    @property
    def label(self):
        return f"{self.kind}:{self.model}"

    def appium_options(self):
        opts = UiAutomator2Options()
        opts.udid = self.serial
        opts.no_reset = True  # 앱 데이터·보조 앱을 지우지 않는다 (화웨이는 재설치마다 기기 승인이 필요)
        opts.new_command_timeout = 300
        opts.set_capability("appium:uiautomator2ServerInstallTimeout", 120_000)
        opts.set_capability("appium:adbExecTimeout", 60_000)
        if self.automotive:
            # AAOS: 운전자 사용자(10)의 화면을 다루고, Appium Settings 앱 초기화를 건너뛴다 (docs/phase1-spike.md)
            opts.set_capability("appium:userProfile", self.user)
            opts.set_capability("appium:skipDeviceInitialization", True)
        return opts

    @property
    def tap_mode(self):
        """요소를 누르는 방법. IVI_TAP=appium|adb 로 바꿀 수 있다.
        화웨이·아너는 UiAutomator 로 넣는 터치(click, W3C actions, clickGesture)가 한 번에 약 10초 걸린다
        (2026-11-13, DBY-W09: click 10.1s / adb input tap 0.12s). 그래서 기본을 adb 로 둔다."""
        forced = os.environ.get("IVI_TAP")
        if forced in ("appium", "adb"):
            return forced
        return "adb" if self.brand.upper() in SLOW_INJECTION_BRANDS else "appium"

    def tapper(self):
        if self.tap_mode == "appium":
            return None

        def tap(element):
            rect = element.rect
            self.adb.shell("input", "tap", str(rect["x"] + rect["width"] // 2), str(rect["y"] + rect["height"] // 2))

        return tap

    def launch(self, component=MAIN, reset=False, fresh=False):
        """reset: 앱 프로세스는 두고 태스크만 비운 뒤 새 화면으로 시작 (--activity-clear-task). 테스트마다 쓰는 기본.
        fresh: 프로세스까지 종료 후 시작 (-S). 화웨이는 짧은 간격으로 반복하면 iAware 가 앱을 죽이므로 세션 시작 때만 쓴다."""
        self.adb.start_activity(component, user=self.user, fresh=fresh, clear_task=reset)

    def reset_app_state(self):
        """저장 설정(볼륨·단위·라디오 프리셋 등)을 기본값으로. debug 빌드의 TestHookReceiver 를 부른다.
        AAOS 에뮬레이터는 앱이 꺼져 있어도 받지만(-f 0x20), 화웨이는 꺼진 앱에 전달하지 않는다 → 앱을 띄운 뒤에 부른다."""
        out = self.adb.shell("am", "broadcast", "--user", str(self.user), "-f", "0x20",
                             "-n", f"{PACKAGE}/.TestHookReceiver", "-a", f"{PACKAGE}.test.RESET")
        if 'data="reset"' not in out:
            raise RuntimeError(f"앱 상태 초기화 실패 (debug 빌드인지 확인): {out.strip()[-200:]}")

    def stop_app(self):
        self.adb.shell("am", "force-stop", "--user", str(self.user), PACKAGE, check=False)

    def video_blocked(self, video_screen):
        """주행 중 영상 차단 판정. AAOS 는 OS 가 막고(ActivityBlockingActivity), Mock 기기는 앱이 막는다(video_blocked)."""
        if self.automotive:
            return any(AAOS_BLOCKING in activity for activity in self.adb.resumed_activities())
        return video_screen.blocked()
