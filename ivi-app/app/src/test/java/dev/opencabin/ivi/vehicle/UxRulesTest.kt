package dev.opencabin.ivi.vehicle

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 기어·속도에서 UX 제한 종류를 정하는 표 (태블릿 Mock 이 쓰고, AAOS 에뮬레이터의 car_ux_restrictions_map 과 같아야 한다).
 * 값은 android.car.drivingstate.CarUxRestrictions 의 UX_RESTRICTIONS_* 와 같다. 기기 없이 JVM 에서 돈다.
 */
class UxRulesTest {

    @Test
    fun `P 는 속도와 관계없이 제한이 없다`() {
        assertEquals(UxRules.NONE, UxRules.forDriving(Gear.PARK, 0f))
        assertEquals(UxRules.NONE, UxRules.forDriving(Gear.PARK, 3f))
    }

    @Test
    fun `P 가 아니고 멈춰 있으면 영상만 막는다`() {
        for (gear in listOf(Gear.DRIVE, Gear.REVERSE, Gear.NEUTRAL)) {
            assertEquals(gear.label, UxRules.NO_VIDEO, UxRules.forDriving(gear, 0f))
        }
    }

    @Test
    fun `속도가 0 보다 크면 전부 막는다`() {
        assertEquals(0xff, UxRules.forDriving(Gear.DRIVE, 0.1f))
        assertEquals(0xff, UxRules.forDriving(Gear.DRIVE, 120f))
        assertEquals(0xff, UxRules.forDriving(Gear.REVERSE, 5f))
    }

    @Test
    fun `안드로이드 상수와 같은 값을 쓴다`() {
        // CarUxRestrictions: NO_DIALPAD 1, NO_FILTERING 2, LIMIT_STRING_LENGTH 4, NO_KEYBOARD 8, NO_VIDEO 16,
        // LIMIT_CONTENT 32, NO_SETUP 64, NO_TEXT_MESSAGE 128, NO_VOICE_TRANSCRIPTION 256, FULLY_RESTRICTED 511
        assertEquals(listOf(1, 2, 4, 8, 16, 32, 64, 128, 256, 511), listOf(
            UxRules.NO_DIALPAD, UxRules.NO_FILTERING, UxRules.LIMIT_STRING_LENGTH, UxRules.NO_KEYBOARD, UxRules.NO_VIDEO,
            UxRules.LIMIT_CONTENT, UxRules.NO_SETUP, UxRules.NO_TEXT_MESSAGE, UxRules.NO_VOICE_TRANSCRIPTION, UxRules.FULLY_RESTRICTED,
        ))
    }

    @Test
    fun `멈춘 D 기어에서는 영상만 막히고 글자 입력과 키패드는 열려 있다`() {
        val idling = VehicleState(gear = Gear.DRIVE, speedKmh = 0f, uxRestrictions = UxRules.forDriving(Gear.DRIVE, 0f))
        assertTrue(idling.restricted)
        assertTrue(idling.blocks(UxRules.NO_VIDEO))
        assertFalse(idling.blocks(UxRules.NO_KEYBOARD))
        assertFalse(idling.blocks(UxRules.NO_DIALPAD))
        assertFalse(idling.moving)
    }

    @Test
    fun `주행 중에는 영상, 글자 입력, 키패드, 목록 길이가 모두 막힌다`() {
        val moving = VehicleState(gear = Gear.DRIVE, speedKmh = 1f, uxRestrictions = UxRules.forDriving(Gear.DRIVE, 1f))
        for (rule in listOf(UxRules.NO_VIDEO, UxRules.NO_KEYBOARD, UxRules.NO_DIALPAD, UxRules.LIMIT_CONTENT)) {
            assertTrue(rule.toString(), moving.blocks(rule))
        }
        assertTrue(moving.moving)
    }
}
