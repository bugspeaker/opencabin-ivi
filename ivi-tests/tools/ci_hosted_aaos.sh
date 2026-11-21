#!/usr/bin/env bash
# GitHub 호스트 러너(ubuntu-latest)에서 AAOS 에뮬레이터를 새로 띄우고, 앱을 priv-app 으로 넣고, smoke 를 돌린다.
# ivi-ci.yml 의 e2e-hosted job 이 부른다. 태블릿과 전체 회귀는 Test Bench(e2e job, 작업 PC)에서 돈다.
#
#   bash ivi-tests/tools/ci_hosted_aaos.sh <app-debug.apk>
#
# 작업 PC 와 같은 시스템 이미지(android-34-ext9, android-automotive)와 같은 화면(automotive_1024p_landscape)을 쓴다.
# 매번 새 에뮬레이터라 priv-app 설치(재부팅 2번 포함)부터 한다. 결과는 ivi-tests/reports/ 아래에 남고 job 이 올린다.
set -euo pipefail

APK="$(realpath "$1")"
IMAGE="system-images;android-34-ext9;android-automotive;x86_64"
SERIAL=emulator-5554
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/ivi-tests/reports/hosted"
mkdir -p "$OUT"
SDK="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
BIN="$SDK/cmdline-tools/latest/bin"
export PATH="$SDK/platform-tools:$SDK/emulator:$PATH"

wait_for() {  # wait_for <초> <설명> <명령...>: 명령이 성공할 때까지 5초 간격
  local limit=$1 what=$2; shift 2
  local started=$SECONDS
  until "$@" > /dev/null 2>&1; do
    if (( SECONDS - started > limit )); then echo "::error::$what: ${limit}초 안에 되지 않음"; return 1; fi
    sleep 5
  done
  echo "$what: $(( SECONDS - started ))초"
}
booted() { [ "$(adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; }
driver_user() { [ "$(adb -s "$SERIAL" shell am get-current-user 2>/dev/null | tr -d '\r')" -ge 10 ]; }
appium_ready() { curl -sf http://127.0.0.1:4723/status | grep -q '"ready":true'; }

echo "::group::시스템 이미지와 AVD"
yes | "$BIN/sdkmanager" --licenses > /dev/null || true
"$BIN/sdkmanager" "emulator" "platform-tools" "$IMAGE" > "$OUT/sdkmanager.log"
echo "no" | "$BIN/avdmanager" create avd -n aaos -k "$IMAGE" -d automotive_1024p_landscape --force
printf 'hw.ramSize=4096\nhw.cpu.ncore=4\ndisk.dataPartition.size=6G\n' >> "$HOME/.android/avd/aaos.avd/config.ini"
echo "::endgroup::"

echo "::group::에뮬레이터 부팅"
# 창 없이 켠다 (호스트 러너에는 화면이 없다. 작업 PC 의 전원 테스트도 같은 이유로 -no-window, ivi/power.py)
emulator -avd aaos -port 5554 -writable-system -no-window -no-audio -no-boot-anim -no-snapshot \
  -gpu swiftshader_indirect -accel on > "$OUT/emulator.log" 2>&1 &
wait_for 600 "부팅" booted
echo "::endgroup::"

echo "::group::priv-app 설치"
python "$ROOT/ivi-app/privileged/install_priv_app.py" "$APK" --serial "$SERIAL"
wait_for 300 "운전자 사용자(10)로 전환" driver_user
echo "::endgroup::"

echo "::group::Appium"
appium --address 127.0.0.1 --port 4723 > "$OUT/appium.log" 2>&1 &
wait_for 120 "Appium 준비" appium_ready
echo "::endgroup::"

cd "$ROOT/ivi-tests"
set +e
python -m pytest -m smoke --serial "$SERIAL" --reruns 1 --junitxml=reports/junit-smoke-hosted.xml
code=$?
set -e
adb -s "$SERIAL" logcat -d -v threadtime > "$OUT/logcat.txt" 2>&1 || true
exit $code
