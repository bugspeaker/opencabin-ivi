package dev.opencabin.ivi.assistant

import dev.opencabin.ivi.vehicle.Seat
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** 비서의 '말 → 동작' 규칙. 기기 없이 JVM 에서 돈다 (./gradlew testDebugUnitTest). */
class CabinAssistantTest {

    private class FakeCar(override val hvacAvailable: Boolean = true) : CabinControls {
        override var videoBlocked = false
        override var moving = false

        /** 주행: 영상과 미러 접기 모두 막힘 */
        fun drive() { videoBlocked = true; moving = true }
        /** D 기어로 멈춤 (신호 대기): 플랫폼은 영상만 막는다 */
        fun idle() { videoBlocked = true; moving = false }
        fun park() { videoBlocked = false; moving = false }
        val temps = mutableMapOf(Seat.DRIVER to 22f, Seat.PASSENGER to 22f)
        var acOn = false
        var syncOn = false
        val heat = mutableMapOf<Seat, Boolean>()
        var playing = false
        var route: Place? = null
        var videoOpened = false
        var mirrorsFolded = false
        var radioOn = false
        var calling: String? = null

        override fun temperature(seat: Seat) = temps[seat]
        override fun setTemperature(seat: Seat, celsius: Float) { temps[seat] = celsius }
        override fun setAc(on: Boolean) { acOn = on }
        override fun setSync(on: Boolean) { syncOn = on }
        override fun setSeatHeat(seat: Seat, on: Boolean) { heat[seat] = on }
        override fun play() { playing = true }
        override fun pause() { playing = false }
        override fun next(): String { playing = true; return "Coastal Road" }
        override fun navigate(place: Place) { route = place }
        override fun cancelRoute(): Boolean = (route != null).also { route = null }
        override fun openVideo() { videoOpened = true }
        override fun foldMirrors(fold: Boolean) { mirrorsFolded = fold }
        override fun setRadio(on: Boolean) { radioOn = on }
        override fun call(who: String) = listOf("엄마", "김민수").firstOrNull { it == who }?.also { calling = it }
    }

    private val car = FakeCar()
    private val assistant = CabinAssistant(car)

    @Test fun `숫자 온도는 말한 사람의 좌석에만 적용된다`() {
        assistant.handle("22.5도로 맞춰줘", Seat.PASSENGER)
        assertEquals(22.5f, car.temps[Seat.PASSENGER])
        assertEquals(22f, car.temps[Seat.DRIVER])
    }

    @Test fun `좌석을 말하면 그 좌석, 모두라고 하면 전 좌석`() {
        assistant.handle("운전석 25도로 해줘", Seat.PASSENGER)
        assertEquals(25f, car.temps[Seat.DRIVER])
        assertEquals(22f, car.temps[Seat.PASSENGER])

        val reply = assistant.handle("모두 20도로 맞춰줘", Seat.DRIVER)
        assertEquals(20f, car.temps[Seat.DRIVER])
        assertEquals(20f, car.temps[Seat.PASSENGER])
        assertTrue(reply.text, reply.text.contains("전 좌석"))
    }

    @Test fun `간접 표현 - 더워는 1도 내리고 추워는 1도 올린다`() {
        assistant.handle("나 더워", Seat.DRIVER)
        assertEquals(21f, car.temps[Seat.DRIVER])
        assistant.handle("좀 추운데", Seat.PASSENGER)
        assertEquals(23f, car.temps[Seat.PASSENGER])
    }

    @Test fun `온도 올려는 한 단계(0점5도)`() {
        assistant.handle("온도 올려줘", Seat.DRIVER)
        assertEquals(22.5f, car.temps[Seat.DRIVER])
        assistant.handle("온도 많이 내려줘", Seat.DRIVER)
        assertEquals(21.5f, car.temps[Seat.DRIVER])
    }

    @Test fun `범위 밖 온도는 경계로 맞추고 알려 준다`() {
        val reply = assistant.handle("35도로 맞춰줘", Seat.DRIVER)
        assertEquals(28f, car.temps[Seat.DRIVER])
        assertTrue(reply.text, reply.text.contains("16.0~28.0"))
    }

    @Test fun `여러 명령을 한 번에 차례로 실행한다`() {
        val reply = assistant.handle("에어컨 켜고 음악 틀어줘 그리고 판교역으로 가자", Seat.DRIVER)
        assertTrue(car.acOn)
        assertTrue(car.playing)
        assertEquals("pangyo_station", car.route?.id)
        assertTrue(reply.understood)
    }

    @Test fun `문장 나누기`() {
        assertEquals(listOf("에어컨 켜", "음악 틀어줘"), IntentParser.split("에어컨 켜고 음악 틀어줘"))
        assertEquals(listOf("22도로 맞추고", "열선 켜줘"), IntentParser.split("22도로 맞추고, 열선 켜줘"))
        assertEquals(listOf("거기 말고 서울에 있는 데로 가자"), IntentParser.split("거기 말고 서울에 있는 데로 가자"))
    }

    @Test fun `목적지 후보가 여럿이면 고르게 한다`() {
        val reply = assistant.handle("판교 가자", Seat.DRIVER)
        assertEquals(null, car.route)
        assertEquals(listOf("pangyo_charger", "pangyo_parking", "pangyo_station"), reply.candidates.map { it.id })

        assistant.choose(reply.candidates.last())
        assertEquals("pangyo_station", car.route?.id)
    }

    @Test fun `목적지 말 바꾸기와 분류 검색`() {
        assistant.handle("거기 말고 서울에 있는 데로 가자", Seat.DRIVER)
        assertEquals("seoul_station", car.route?.id)
        assertEquals(listOf("pangyo_charger", "jeongja_charger"), assistant.handle("가까운 충전소 찾아줘", Seat.DRIVER).candidates.map { it.id })
        assistant.handle("집으로 가자", Seat.DRIVER)
        assertEquals("home", car.route?.id)
        assistant.handle("안내 종료", Seat.DRIVER)
        assertEquals(null, car.route)
    }

    @Test fun `주행 중에는 영상과 사이드 미러 접기를 거절한다`() {
        car.drive()
        assertTrue(assistant.handle("영상 틀어줘", Seat.DRIVER).text.contains("주행 중"))
        assertFalse(car.videoOpened)
        assertTrue(assistant.handle("사이드 미러 접어줘", Seat.PASSENGER).text.contains("주행 중"))
        assertFalse(car.mirrorsFolded)

        car.park()
        assistant.handle("영상 틀어줘", Seat.DRIVER)
        assertTrue(car.videoOpened)
    }

    @Test fun `D 기어로 멈춰 있으면 영상만 거절하고 사이드 미러는 접는다`() {
        car.idle()
        assertTrue(assistant.handle("영상 틀어줘", Seat.DRIVER).text.contains("P 기어"))
        assertFalse(car.videoOpened)
        assistant.handle("사이드 미러 접어줘", Seat.PASSENGER)
        assertTrue(car.mirrorsFolded)
    }

    @Test fun `영상 틀어줘는 음악이 아니다`() {
        assertEquals(Action.OpenVideo, IntentParser.parse("영상 틀어줘", Seat.DRIVER))
        assertEquals(Action.Play, IntentParser.parse("노래 틀어줘", Seat.DRIVER))
        assertEquals(Action.Pause, IntentParser.parse("음악 꺼줘", Seat.DRIVER))
    }

    @Test fun `열선과 동기화`() {
        assistant.handle("내 자리 열선 켜줘", Seat.PASSENGER)
        assertEquals(true, car.heat[Seat.PASSENGER])
        assertEquals(null, car.heat[Seat.DRIVER])
        assistant.handle("온도 동기화해줘", Seat.DRIVER)
        assertTrue(car.syncOn)
    }

    @Test fun `6단계 음성 명령 4개가 그대로 동작한다`() {
        assertTrue(assistant.handle("운전석 온도 24도로 맞춰줘", Seat.PASSENGER).text.contains("24.0"))
        assertEquals(24f, car.temps[Seat.DRIVER])
        assistant.handle("라디오 켜줘", Seat.DRIVER)
        assertTrue(car.radioOn)
        assistant.handle("집으로 안내해줘", Seat.DRIVER)
        assertEquals("home", car.route?.id)
        assertEquals("엄마에게 전화를 걸게요.", assistant.handle("엄마에게 전화해줘", Seat.DRIVER).text)
        assertEquals("엄마", car.calling)
    }

    @Test fun `없는 연락처와 라디오 끄기`() {
        assertFalse(assistant.handle("홍길동한테 전화 걸어줘", Seat.DRIVER).understood)
        car.radioOn = true
        assistant.handle("라디오 꺼줘", Seat.DRIVER)
        assertFalse(car.radioOn)
    }

    @Test fun `내비 목록 검색 - 역은 판교역과 서울역만`() {
        assertEquals(listOf("판교역", "서울역"), Places.all.filter { it.name.contains("역") }.map { it.name })
    }

    @Test fun `공조를 쓸 수 없으면 거절한다`() {
        val noHvac = CabinAssistant(FakeCar(hvacAvailable = false))
        val reply = noHvac.handle("22도로 맞춰줘", Seat.DRIVER)
        assertFalse(reply.understood)
    }

    @Test fun `모르는 말은 예시를 알려 준다`() {
        val reply = assistant.handle("오늘 기분 어때", Seat.DRIVER)
        assertFalse(reply.understood)
        assertTrue(reply.text.contains("22도로 맞춰줘"))
    }

    @Test fun `받침에 맞는 조사를 붙인다`() {
        assertEquals("으로", CabinAssistant.josa("판교역", "으로", "로"))
        assertEquals("로", CabinAssistant.josa("회사", "으로", "로"))
        assertEquals("로", CabinAssistant.josa("서울", "으로", "로"))   // ㄹ 받침 뒤는 '로'
        assertEquals("을", CabinAssistant.josa("집", "을", "를"))
        assertEquals("를", CabinAssistant.josa("엄마", "을", "를"))
        assertEquals("는", CabinAssistant.josa("ABC", "은", "는"))      // 한글이 아니면 받침 없는 쪽
    }

    @Test fun `안내 대답에 조사 괄호 표기가 없다`() {
        val reply = assistant.handle("판교역 가자", Seat.DRIVER)
        assertTrue(reply.text, reply.text.startsWith("판교역으로 안내를 시작할게요"))
        assertFalse(reply.text.contains("(으)"))
    }
}
