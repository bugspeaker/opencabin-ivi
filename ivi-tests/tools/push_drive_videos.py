"""블랙박스 원본 영상을 앱용으로 다듬어 기기에 올린다. 앱의 영상 화면(VideoActivity)이 이 파일들을 재생한다.

    python tools/push_drive_videos.py [--src ../.drive] [--devices emulator-5554,W3VB...] [--ffmpeg path]

하는 일
  1. 다듬기 (ffmpeg): 하단 오버레이 줄(날짜 · 블랙박스 이름 · GPS 좌표 · 속도)을 잘라 내고, 오른쪽 거치대를 조금 덜어 16:9 로 맞춘다.
     H.265 → H.264 1280x720 (에뮬레이터는 HEVC 를 소프트웨어로 풀어 끊긴다), 음성 제거 (실내 대화), 메타데이터 제거.
     결과는 <src>/out/drive_01.mp4 ... 원본은 건드리지 않는다.
  2. 올리기 (adb): 기기의 '현재 사용자' 앱 전용 폴더 /storage/emulated/<user>/Android/data/dev.opencabin.ivi/files/drive/
     AAOS 에뮬레이터는 현재 사용자가 10 이라 /sdcard(=사용자 0) 로 올리면 앱이 못 본다.

영상은 개인 자료(번호판 · 위치)라 저장소에 넣지 않는다 (.gitignore 의 .drive/).
파일이 없으면 앱은 예전처럼 가짜 재생 화면을 보여 주므로 테스트는 영상 유무와 상관없이 돈다.
ffmpeg 가 PATH 에 없으면 `pip install imageio-ffmpeg` 의 바이너리를 쓴다.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = "dev.opencabin.ivi"
ROOT = Path(__file__).resolve().parents[2]
# 원본 1920x1080 기준: 아래 81px (오버레이 줄 y≈1015~1060) 와 오른쪽 144px 를 버린다 → 1776x999 ≈ 16:9
CROP = "crop=1776:999:0:0,scale=1280:720,setsar=1"


def find_ffmpeg(given):
    if given:
        return given
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("ffmpeg 가 없다. PATH 에 넣거나 `pip install imageio-ffmpeg` 후 다시 실행한다.")


def adb(serial, *args, timeout=600):
    done = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return done.returncode, (done.stdout + done.stderr).replace("\r", "").strip()


def encode(ffmpeg, sources, out_dir):
    out_dir.mkdir(exist_ok=True)
    made = []
    for i, src in enumerate(sources, 1):
        dst = out_dir / f"drive_{i:02d}.mp4"
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            print(f"  {dst.name}: 이미 있음 ({src.name})")
        else:
            print(f"  {dst.name} ← {src.name} 변환 중...")
            subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(src), "-vf", CROP, "-r", "30",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-an", "-map_metadata", "-1", "-movflags", "+faststart", str(dst)],
                           check=True)
        made.append(dst)
    return made


def push(serial, files):
    code, user = adb(serial, "shell", "am", "get-current-user")
    if code != 0 or not user.isdigit():
        raise SystemExit(f"{serial}: 현재 사용자를 알 수 없다 ({user})")
    if user == "0":
        # 일반 기기: 셸이 앱 전용 폴더에 바로 쓸 수 있다
        target = f"/storage/emulated/0/Android/data/{PACKAGE}/files/drive"
        adb(serial, "shell", "mkdir", "-p", target)
        owner = None
    else:
        # AAOS: 셸(사용자 0)은 /storage/emulated/10 에 못 쓴다 → root 로 실제 저장 위치 /data/media/10 에 넣고
        # 소유자를 앱 폴더와 같게 맞춘다. 폴더는 앱이 만들어야 소유자·SELinux 라벨이 맞으므로 영상 화면을 한 번 띄운다
        adb(serial, "root")
        adb(serial, "wait-for-device")
        target = f"/data/media/{user}/Android/data/{PACKAGE}/files/drive"
        code, _ = adb(serial, "shell", "test", "-d", target)
        if code != 0:
            adb(serial, "shell", "am", "start", "-W", "--user", user, "-n", f"{PACKAGE}/.VideoActivity")
            adb(serial, "shell", "am", "force-stop", "--user", user, PACKAGE)
        code, owner = adb(serial, "shell", "stat", "-c", "%u:%g", target)
        if code != 0:
            raise SystemExit(f"{serial}: 앱 폴더가 없다 ({target}). 앱이 설치돼 있는지 확인한다")
    adb(serial, "shell", f"rm -f {target}/*.mp4")
    for f in files:
        code, out = adb(serial, "push", str(f), f"{target}/{f.name}")
        if code != 0:
            raise SystemExit(f"{serial}: {f.name} 올리기 실패: {out[-300:]}")
    if owner:
        adb(serial, "shell", f"chown {owner} {target}/*.mp4 && chmod 660 {target}/*.mp4 && restorecon {target}/*.mp4")
    print(f"  {serial}: {len(files)}개 → {target}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=ROOT / ".drive", help="원본 mp4 가 있는 폴더")
    parser.add_argument("--devices", help="쉼표로 구분한 serial (기본: adb devices 전부)")
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()

    sources = sorted(p for p in args.src.glob("*.mp4"))
    if not sources:
        raise SystemExit(f"{args.src} 에 mp4 가 없다")
    print("다듬기")
    files = encode(find_ffmpeg(args.ffmpeg), sources, args.src / "out")

    if args.devices:
        serials = args.devices.split(",")
    else:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        serials = [line.split()[0] for line in out.splitlines()[1:] if line.strip().endswith("device")]
    if not serials:
        raise SystemExit("연결된 기기가 없다")
    print("올리기")
    for serial in serials:
        push(serial, files)


if __name__ == "__main__":
    sys.exit(main())
