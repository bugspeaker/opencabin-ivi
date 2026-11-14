package dev.opencabin.ivi.state

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleDataSource
import java.time.LocalTime
import kotlin.math.max

/*
 * 화면이 함께 쓰는 앱 상태. 차량 신호(VehicleDataSource)와 저장 설정(SettingsStore) 사이에서
 * 오디오 소스 하나만 재생, 통화 중 일시 정지, 경로 안내 진행 같은 규칙을 한곳에 둔다.
 */

enum class AudioSource { NONE, RADIO, MEDIA }

val Tracks = listOf(
    "Night Drive" to "Neon Avenue",
    "Coastal Road" to "Blue Hour",
    "City Lights" to "Metro Lines",
    "Morning Commute" to "Daybreak",
    "Long Way Home" to "Last Exit",
)

data class Destination(val name: String, val address: String, val km: Double)

val Destinations = listOf(
    Destination("집", "경기 성남시 분당구", 12.4),
    Destination("회사", "경기 성남시 판교역로", 8.7),
    Destination("판교역", "신분당선 · 경강선", 5.2),
    Destination("서울역", "서울 용산구", 27.9),
    Destination("인천국제공항", "인천 중구", 68.3),
    Destination("편의점", "500m 이내", 0.1),
)

data class Contact(val name: String, val number: String)

/** 가상 연락처 (실제 번호가 아니다). */
val Contacts = listOf(
    Contact("엄마", "010-0000-1001"), Contact("아빠", "010-0000-1002"), Contact("김민수", "010-0000-2001"),
    Contact("이서연", "010-0000-2002"), Contact("박지훈", "010-0000-2003"), Contact("최유진", "010-0000-2004"),
    Contact("정다은", "010-0000-2005"), Contact("강현우", "010-0000-2006"), Contact("조은비", "010-0000-2007"),
    Contact("윤성호", "010-0000-2008"), Contact("장미래", "010-0000-2009"), Contact("임도윤", "010-0000-2010"),
)

/** 주행 중 연락처 목록은 앞의 일부만 보인다 (주의 분산 줄이기). */
const val DRIVING_LIST_LIMIT = 5

data class CallRecord(val name: String, val number: String, val kind: String)

data class ActiveCall(val name: String, val number: String, val startedAt: Long)

val VoiceCommands = listOf("운전석 온도 24도로 맞춰줘", "라디오 켜줘", "집으로 안내해줘", "엄마에게 전화해줘")

class CabinController(
    private val settings: SettingsStore,
    private val vehicle: VehicleDataSource,
) {
    // ---------------- 오디오: 한 번에 하나만 재생 ----------------
    var audioSource by mutableStateOf(AudioSource.NONE)
        private set
    var mediaTrack by mutableIntStateOf(0)
        private set
    val mediaPlaying get() = audioSource == AudioSource.MEDIA
    val radioOn get() = audioSource == AudioSource.RADIO

    fun playMedia(index: Int = mediaTrack) {
        mediaTrack = index
        audioSource = AudioSource.MEDIA
    }

    fun toggleMedia() {
        audioSource = if (mediaPlaying) AudioSource.NONE else AudioSource.MEDIA
    }

    fun setRadio(on: Boolean) {
        audioSource = if (on) AudioSource.RADIO else if (radioOn) AudioSource.NONE else audioSource
    }

    /** 화면에 보이는 재생 상태. 통화 중이면 소리가 멈춘다. */
    fun playbackLabel(source: AudioSource) = when {
        audioSource != source -> if (source == AudioSource.RADIO) "꺼짐" else "일시 정지"
        call != null -> "통화 중"
        else -> "재생 중"
    }

    // ---------------- 라디오 (주파수·프리셋은 저장 설정) ----------------
    fun setBand(band: Band) = settings.update { it.copy(band = band) }

    fun tune(steps: Int) = settings.update { s ->
        val band = s.band
        val next = (s.freq + steps * band.step).let { if (it > band.max) band.min else if (it < band.min) band.max else it }
        if (band == Band.FM) s.copy(fmFreq = next) else s.copy(amFreq = next)
    }

    /** 다음(이전) 방송국으로. 끝에 닿으면 반대쪽 끝에서 이어 찾는다. */
    fun seek(direction: Int) = settings.update { s ->
        val list = Stations.filter { it.band == s.band }.map { it.freq }.sorted()
        val next = if (direction > 0) list.firstOrNull { it > s.freq } ?: list.first() else list.lastOrNull { it < s.freq } ?: list.last()
        if (s.band == Band.FM) s.copy(fmFreq = next) else s.copy(amFreq = next)
    }

    fun recallPreset(slot: Int) = settings.update { s ->
        val freq = s.presets[slot]
        if (s.band == Band.FM) s.copy(fmFreq = freq) else s.copy(amFreq = freq)
    }

    fun savePreset(slot: Int) = settings.update { s ->
        val list = s.presets.toMutableList().also { it[slot] = s.freq }
        if (s.band == Band.FM) s.copy(fmPresets = list) else s.copy(amPresets = list)
    }

    // ---------------- 내비게이션 ----------------
    var destination by mutableStateOf<Destination?>(null)
        private set
    var guiding by mutableStateOf(false)
        private set
    var remainingKm by mutableDoubleStateOf(0.0)
        private set
    val arrived get() = destination != null && !guiding && remainingKm <= 0.0

    fun preview(dest: Destination) {
        destination = dest
        guiding = false
        remainingKm = dest.km
    }

    fun startGuidance(dest: Destination? = destination) {
        dest ?: return
        destination = dest
        remainingKm = dest.km
        guiding = true
    }

    fun stopGuidance() {
        guiding = false
        destination = null
        remainingKm = 0.0
    }

    /** 1초마다 부른다. 차량 속도만큼 남은 거리를 줄인다. */
    fun tick(speedKmh: Float, seconds: Double = 1.0) {
        if (!guiding) return
        remainingKm = max(0.0, remainingKm - speedKmh * seconds / 3600.0)
        if (remainingKm <= 0.0) guiding = false
    }

    fun eta(speedKmh: Float, now: LocalTime = LocalTime.now()): LocalTime {
        val hours = remainingKm / max(speedKmh.toDouble(), 40.0)
        return now.plusSeconds((hours * 3600).toLong())
    }

    /** 다음 안내: 남은 거리 기준으로 800m 마다 바뀌는 가상 경로. */
    fun nextManeuver(): Pair<Int, String> {
        val meters = (remainingKm * 1000).toInt()
        if (meters < 300) return meters to "목적지 부근"
        val steps = listOf("우회전", "직진", "좌회전", "고속도로 진입", "오른쪽 출구")
        return (meters % 800).coerceAtLeast(50) to steps[(meters / 800) % steps.size]
    }

    // ---------------- 전화 (블루투스 핸즈프리, 가상) ----------------
    var call by mutableStateOf<ActiveCall?>(null)
        private set
    var dialNumber by mutableStateOf("")
        private set
    val recents = mutableStateListOf(
        CallRecord("김민수", "010-0000-2001", "부재중"),
        CallRecord("회사", "031-000-0000", "수신"),
        CallRecord("엄마", "010-0000-1001", "발신"),
    )

    fun press(digit: String) {
        if (dialNumber.length < 13) dialNumber += digit
    }

    fun backspace() {
        dialNumber = dialNumber.dropLast(1)
    }

    fun dial(name: String? = null, number: String = dialNumber) {
        if (number.isBlank()) return
        val who = name ?: Contacts.firstOrNull { it.number == number }?.name ?: number
        call = ActiveCall(who, number, System.currentTimeMillis())
        recents.add(0, CallRecord(who, number, "발신"))
        dialNumber = ""
    }

    fun endCall() {
        call = null
    }

    // ---------------- 음성 명령 (인식된 문장을 고르는 것으로 대신한다) ----------------
    var voiceResult by mutableStateOf("")
        private set
    var voiceSeq by mutableIntStateOf(0)
        private set

    fun clearVoiceResult() {
        voiceResult = ""
    }

    /** 실행 후 열어야 할 화면 이름을 돌려준다 (없으면 null). */
    fun runVoice(index: Int): String? {
        voiceSeq++
        return when (index) {
            0 -> {
                vehicle.setTemperature(Seat.DRIVER, 24f)
                voiceResult = "운전석 온도를 24.0°C로 맞출게요"
                null
            }
            1 -> {
                setRadio(true)
                voiceResult = "라디오를 켤게요"
                "radio"
            }
            2 -> {
                startGuidance(Destinations.first { it.name == "집" })
                voiceResult = "집으로 안내를 시작할게요"
                "navi"
            }
            3 -> {
                val mom = Contacts.first { it.name == "엄마" }
                dial(mom.name, mom.number)
                voiceResult = "엄마에게 전화를 걸게요"
                null
            }
            else -> null
        }
    }
}
