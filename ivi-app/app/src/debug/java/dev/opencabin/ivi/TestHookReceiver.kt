package dev.opencabin.ivi

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * 테스트 훅 (debug 빌드만). 테스트마다 저장 설정(볼륨·단위·라디오 프리셋 등)을 기본값으로 되돌린다.
 *   adb shell am broadcast --user <운전자> -f 0x20 -n dev.opencabin.ivi/.TestHookReceiver -a dev.opencabin.ivi.test.RESET
 * 매니페스트에 선언한 수신기라 앱이 꺼져 있어도 받는다 (-f 0x20 = 멈춘 앱에도 전달).
 */
class TestHookReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_RESET) {
            (context.applicationContext as IviApp).settings.reset()
            resultData = "reset"
        }
    }

    companion object {
        const val ACTION_RESET = "dev.opencabin.ivi.test.RESET"
    }
}
