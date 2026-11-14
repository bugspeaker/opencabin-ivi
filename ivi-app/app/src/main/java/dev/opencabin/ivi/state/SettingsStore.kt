package dev.opencabin.ivi.state

import android.content.Context
import androidx.core.content.edit
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** 라디오 대역. 주파수는 정수로 다룬다: FM = MHz × 10 (예: 89.1 → 891), AM = kHz. */
enum class Band(val label: String, val min: Int, val max: Int, val step: Int) {
    FM("FM", 875, 1080, 1), AM("AM", 531, 1602, 9);

    fun format(freq: Int) = if (this == FM) "${freq / 10}.${freq % 10} MHz" else "$freq kHz"
}

data class Station(val band: Band, val freq: Int, val name: String)

/** 가상 방송국 (실제 방송사 이름을 쓰지 않는다). */
val Stations = listOf(
    Station(Band.FM, 891, "뉴스 FM"), Station(Band.FM, 919, "음악 FM"), Station(Band.FM, 959, "교통 방송"),
    Station(Band.FM, 999, "클래식 FM"), Station(Band.FM, 1035, "팝 라디오"), Station(Band.FM, 1077, "영어 방송"),
    Station(Band.AM, 711, "AM 뉴스"), Station(Band.AM, 837, "AM 교통"), Station(Band.AM, 972, "AM 음악"),
)

val AmbientColors = listOf("아쿠아", "화이트", "앰버", "퍼플", "그린")

/** 차에 저장되는 사용자 설정. 앱을 다시 켜도 유지된다. */
data class Settings(
    val volume: Int = 15,
    val brightness: Int = 16,
    val clock24: Boolean = true,
    val mph: Boolean = false,
    val autoLock: Boolean = true,
    val ambient: Int = 0,
    val band: Band = Band.FM,
    val fmFreq: Int = 891,
    val amFreq: Int = 711,
    val fmPresets: List<Int> = listOf(891, 919, 959, 999, 1035, 1077),
    val amPresets: List<Int> = listOf(711, 837, 972, 711, 837, 972),
) {
    val freq get() = if (band == Band.FM) fmFreq else amFreq
    val presets get() = if (band == Band.FM) fmPresets else amPresets

    companion object {
        const val VOLUME_MAX = 35
        const val BRIGHTNESS_MAX = 20
    }
}

/**
 * SharedPreferences 에 저장하고 StateFlow 로 알린다.
 * 테스트는 debug 빌드의 TestHookReceiver 로 reset() 을 불러 테스트마다 기본값에서 시작한다.
 */
class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
    private val _settings = MutableStateFlow(load())
    val settings: StateFlow<Settings> = _settings

    fun update(transform: (Settings) -> Settings) {
        val next = transform(_settings.value)
        save(next)
        _settings.value = next
    }

    fun reset() {
        prefs.edit(commit = true) { clear() }
        _settings.value = Settings()
    }

    private fun load(): Settings {
        val d = Settings()
        return Settings(
            volume = prefs.getInt("volume", d.volume),
            brightness = prefs.getInt("brightness", d.brightness),
            clock24 = prefs.getBoolean("clock24", d.clock24),
            mph = prefs.getBoolean("mph", d.mph),
            autoLock = prefs.getBoolean("autoLock", d.autoLock),
            ambient = prefs.getInt("ambient", d.ambient),
            band = runCatching { Band.valueOf(prefs.getString("band", d.band.name)!!) }.getOrDefault(d.band),
            fmFreq = prefs.getInt("fmFreq", d.fmFreq),
            amFreq = prefs.getInt("amFreq", d.amFreq),
            fmPresets = prefs.getString("fmPresets", null)?.toInts() ?: d.fmPresets,
            amPresets = prefs.getString("amPresets", null)?.toInts() ?: d.amPresets,
        )
    }

    private fun save(s: Settings) = prefs.edit {
        putInt("volume", s.volume)
        putInt("brightness", s.brightness)
        putBoolean("clock24", s.clock24)
        putBoolean("mph", s.mph)
        putBoolean("autoLock", s.autoLock)
        putInt("ambient", s.ambient)
        putString("band", s.band.name)
        putInt("fmFreq", s.fmFreq)
        putInt("amFreq", s.amFreq)
        putString("fmPresets", s.fmPresets.joinToString(","))
        putString("amPresets", s.amPresets.joinToString(","))
    }

    private fun String.toInts() = split(",").mapNotNull { it.trim().toIntOrNull() }.takeIf { it.size == 6 }
}
