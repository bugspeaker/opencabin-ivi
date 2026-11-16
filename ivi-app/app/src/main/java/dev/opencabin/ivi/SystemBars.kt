package dev.opencabin.ivi

import android.app.Activity
import android.content.pm.PackageManager
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat

/**
 * AAOS: 앱이 떠 있는 동안 아래 시스템 바(CarSystemUI 내비게이션 바)를 숨긴다.
 *
 * 왜: 앱이 자체 하단 줄(앱 아이콘 + 운전석·조수석 공조)을 그린다. 시스템 바에도 같은 공조 온도가 나와 정보가 겹치고,
 *     1024x768(160dpi) 에뮬레이터에서는 시스템 바의 온도 글자가 홈·마이크 아이콘과 겹쳐 보인다.
 *     실제 OEM IVI 도 자체 독(dock)을 쓰고 기본 내비게이션 바는 내린다. 위 상태 바(시계·사용자)는 그대로 둔다.
 * 숨긴 바는 아래 가장자리에서 밀어 올리면 잠깐 나온다. 태블릿(Mock)은 건드리지 않는다.
 */
fun Activity.hideCarNavigationBar() {
    if (!packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE)) return
    WindowCompat.getInsetsController(window, window.decorView).apply {
        systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        hide(WindowInsetsCompat.Type.navigationBars())
    }
}
