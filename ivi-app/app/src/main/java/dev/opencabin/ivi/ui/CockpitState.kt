package dev.opencabin.ivi.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import dev.opencabin.ivi.assistant.Place
import dev.opencabin.ivi.vehicle.Seat
import java.time.LocalTime

/**
 * 앱 화면. 태그는 ivi-tests/ivi/screens.py 와 맞춘다.
 *  - 아래 바에 고정: 공조 · 미디어 · 전화 · 내비(HOME) · AI · 앱 목록, 왼쪽 끝 차량
 *  - 라디오 · 설정은 앱 목록(또는 '이전 실행 앱' 칸)에서 연다
 * HOME 은 내비게이션 화면이다. 분할 화면이면 오른쪽에 오디오 카드가 같이 보인다.
 */
enum class Tab(val label: String, val tag: String) {
    HOME("내비게이션", "nav_home"),
    RADIO("라디오", "nav_radio"),
    MEDIA("미디어", "nav_media"),
    PHONE("전화", "nav_phone"),
    CLIMATE("공조", "nav_climate"),
    SETTINGS("설정", "nav_settings"),
    ASSISTANT("AI 어시스턴트", "nav_assistant"),
    VEHICLE("차량", "nav_vehicle"),
    APPS("앱", "nav_apps"),
}

enum class LightMode(val label: String, val tag: String) { OFF("끔", "qc_lights_off"), AUTO("자동", "qc_lights_auto"), ON("켬", "qc_lights_on") }

data class ClimateSnapshot(val driverTempC: Float?, val passengerTempC: Float?, val fanSpeed: Int, val acOn: Boolean, val autoOn: Boolean)

data class Notice(val id: Int, val title: String, val body: String, val time: LocalTime)

data class ChatMessage(
    val id: Int,
    val fromUser: Boolean,
    val text: String,
    val seat: Seat?,
    val time: LocalTime,
    val candidates: List<Place> = emptyList(),
)

/**
 * 화면 틀(Shell)이 가진 상태. 오디오·내비·전화는 6단계 CabinController 가, 저장 설정은 SettingsStore 가 가진다.
 * 테스트는 매번 액티비티를 새로 띄우므로(--activity-clear-task) 이 상태도 매번 처음 값으로 돌아간다.
 *
 * 8단계부터 공조(A/C·AUTO·풍량·김서림·열선)와 도어 잠금은 차량 신호(VehicleState)다. 여기 남은 것은
 * 에뮬레이터 VHAL 에 없는 것(사이드 미러 접기 · 트렁크 · 차일드 락 · 실내등 · 전조등)과 화면만의 상태다.
 * 동기화(SYNC)는 운전석 온도를 조수석에도 차량 신호로 쓴다 (Shell.setTemperature).
 */
class CockpitState {
    var tab by mutableStateOf(Tab.HOME)
        private set

    /** 아래 바 '이전 실행 앱'. 아래 바에 늘 있는 앱은 넣지 않는다. */
    var recent by mutableStateOf<Tab?>(null)
        private set

    fun open(next: Tab) {
        if (next != tab) {
            if (tab in listOf(Tab.RADIO, Tab.SETTINGS)) recent = tab
            tab = next
        }
        notificationsOpen = false
    }

    // 분할 화면 (내비 + 오디오)
    var split by mutableStateOf(true)

    // 공조 동기화 (앱 규칙. 값 자체는 차량 신호)
    var sync by mutableStateOf(false)

    /** 최대 냉방(FULL)을 켜기 직전의 공조 값. 버튼으로 끄면 이 값으로 되돌린다. 온도나 풍량을 직접 바꿔서 풀리면 버린다. */
    var beforeMaxAc: ClimateSnapshot? = null

    // 차량 빠른 제어 중 VHAL 에 없는 것 (화면 상태)
    var mirrorsFolded by mutableStateOf(false)
    var trunkOpen by mutableStateOf(false)
    var childLock by mutableStateOf(false)
    var interiorLight by mutableStateOf(false)
    var lights by mutableStateOf(LightMode.AUTO)

    // 현 주행 정보 (속도 신호를 1초마다 더한다)
    var tripKm by mutableFloatStateOf(0f)
    var tripSeconds by mutableLongStateOf(0L)
    var widgetPage by mutableIntStateOf(0)

    fun averageKmh(): Float = if (tripSeconds == 0L) 0f else tripKm / (tripSeconds / 3600f)

    // 알림
    val notices = mutableStateListOf<Notice>()
    var unread by mutableIntStateOf(0)
    var notificationsOpen by mutableStateOf(false)
    private var nextNoticeId = 0

    fun notify(title: String, body: String) {
        notices.add(0, Notice(nextNoticeId++, title, body, LocalTime.now()))
        if (notices.size > 20) notices.removeAt(notices.lastIndex)
        if (!notificationsOpen) unread++
    }

    // 음성 패널 · AI 어시스턴트
    var voiceOpen by mutableStateOf(false)
    var speaker by mutableStateOf(Seat.DRIVER)
    val chat = mutableStateListOf<ChatMessage>()
    private var nextChatId = 0

    fun say(fromUser: Boolean, text: String, seat: Seat?, candidates: List<Place> = emptyList()) {
        chat.add(ChatMessage(nextChatId++, fromUser, text, seat, LocalTime.now(), candidates))
    }
}
