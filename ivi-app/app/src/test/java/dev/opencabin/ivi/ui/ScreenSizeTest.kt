package dev.opencabin.ivi.ui

import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Test

/** 기기마다 어느 배치를 쓰는가. 앱 영역 크기는 실제 기기에서 읽은 값이다 (2026-11-23). */
class ScreenSizeTest {

    @Test
    fun `1024dp devices keep the original layout`() {
        // AAOS 에뮬레이터 1024x768 (160dpi, 위 시스템 바를 빼면 높이 약 692dp)
        assertEquals(ScreenSize(compactWidth = false, compactHeight = false), ScreenSize.of(1024.dp, 692.dp))
        // 화웨이 태블릿 2560x1600 (400dpi)
        assertEquals(ScreenSize(compactWidth = false, compactHeight = false), ScreenSize.of(1024.dp, 640.dp))
    }

    @Test
    fun `fold landscape uses the compact layout`() {
        // 갤럭시 폴드 가로: 카메라 컷아웃 104px, 작업 표시줄 126px 을 뺀 2048x1347 (420dpi)
        assertEquals(ScreenSize(compactWidth = true, compactHeight = true), ScreenSize.of(780.dp, 513.dp))
    }

    @Test
    fun `smallest supported screen is compact in both directions`() {
        assertEquals(ScreenSize(compactWidth = true, compactHeight = true), ScreenSize.of(760.dp, 500.dp))
    }

    @Test
    fun `boundaries`() {
        assertEquals(false, ScreenSize.of(1000.dp, 600.dp).compactWidth)
        assertEquals(true, ScreenSize.of(999.dp, 600.dp).compactWidth)
        assertEquals(false, ScreenSize.of(1000.dp, 600.dp).compactHeight)
        assertEquals(true, ScreenSize.of(1000.dp, 599.dp).compactHeight)
    }
}
