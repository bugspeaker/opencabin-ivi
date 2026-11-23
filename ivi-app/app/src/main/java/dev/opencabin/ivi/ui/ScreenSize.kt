package dev.opencabin.ivi.ui

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/*
 * 화면 크기 등급 (2026-11-23, 갤럭시 폴드를 세 번째 기기로 붙이며 정함).
 *   - 앱은 가로 전용이다 (AndroidManifest 의 sensorLandscape). 지원하는 최소 앱 영역은 760×500dp
 *   - 폭 1000dp 이상은 7단계 배치 그대로다. AAOS 에뮬레이터와 화웨이 태블릿이 둘 다 폭 1024dp 다
 *     (7단계 아래 바는 '이전 앱' 버튼까지 있으면 폭 약 975dp 가 있어야 넘치지 않는다)
 *   - 그보다 좁으면(폴드 가로 780dp) 아래 바·상단 바·라디오 버튼을 줄인 배치를 쓴다
 *   - 높이 600dp 미만(폴드 가로 513dp)이면 AI 어시스턴트의 목적지 후보를 가로로 늘어놓는다
 *     (태블릿 640dp, 에뮬레이터 약 692dp 는 원래대로)
 */
@Immutable
data class ScreenSize(val compactWidth: Boolean, val compactHeight: Boolean) {
    companion object {
        val WIDE_FROM = 1000.dp
        val TALL_FROM = 600.dp

        /** 앱 영역(시스템 바·카메라 컷아웃·작업 표시줄을 뺀 크기)으로 등급을 정한다. */
        fun of(width: Dp, height: Dp) = ScreenSize(compactWidth = width < WIDE_FROM, compactHeight = height < TALL_FROM)
    }
}

val LocalScreenSize = staticCompositionLocalOf { ScreenSize(compactWidth = false, compactHeight = false) }
