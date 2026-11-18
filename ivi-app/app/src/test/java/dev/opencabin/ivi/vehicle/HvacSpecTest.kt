package dev.opencabin.ivi.vehicle

import org.junit.Assert.assertEquals
import org.junit.Test

/** 온도 버튼 한 칸의 계산. 기기 없이 JVM 에서 돈다 (./gradlew testDebugUnitTest). */
class HvacSpecTest {

    @Test
    fun `0_5 단위 값에서는 한 칸씩 움직인다`() {
        assertEquals(22.5f, HvacSpec.stepUp(22.0f), 0f)
        assertEquals(21.5f, HvacSpec.stepDown(22.0f), 0f)
    }

    @Test
    fun `단위가 어긋난 차량 값은 가까운 0_5 단위로 맞춘다`() {
        assertEquals(22.5f, HvacSpec.stepUp(22.3f), 0f)
        assertEquals(22.0f, HvacSpec.stepDown(22.3f), 0f)
    }

    @Test
    fun `범위 끝과 범위 밖에서는 끝값을 넘지 않는다`() {
        assertEquals(16.0f, HvacSpec.stepDown(16.5f), 0f)
        assertEquals(16.0f, HvacSpec.stepDown(16.0f), 0f)
        assertEquals(28.0f, HvacSpec.stepUp(27.5f), 0f)
        assertEquals(16.0f, HvacSpec.stepUp(15.5f), 0f)
        assertEquals(28.0f, HvacSpec.stepDown(28.5f), 0f)
    }
}
