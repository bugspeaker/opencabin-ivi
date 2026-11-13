package dev.opencabin.ivi.vehicle

import kotlinx.coroutines.flow.StateFlow

/** 화면이 보는 차량 상태. 단위는 화면 기준(km/h, °C)으로 맞춘다. */
data class VehicleState(
    val speedKmh: Float = 0f,
    val gear: Gear = Gear.PARK,
    val driverTempC: Float? = null,
    val passengerTempC: Float? = null,
    /** 공조 값을 읽고 쓸 수 있는가. AAOS 에서는 CONTROL_CAR_CLIMATE(signature|privileged) 권한이 있어야 true. */
    val hvacAvailable: Boolean = false,
    /** 주행 중 UX 제한. true 면 영상 등 주의 분산 기능을 막는다. */
    val restricted: Boolean = false,
    val connected: Boolean = false,
    val error: String? = null,
)

/** VHAL GEAR_SELECTION 값 (VehicleGear). */
enum class Gear(val vhal: Int, val label: String) {
    NEUTRAL(1, "N"), REVERSE(2, "R"), PARK(4, "P"), DRIVE(8, "D"), UNKNOWN(0, "-");

    companion object {
        fun fromVhal(value: Int) = entries.firstOrNull { it.vhal == value } ?: UNKNOWN
        fun fromLabel(label: String) = entries.firstOrNull { it.label.equals(label, ignoreCase = true) } ?: UNKNOWN
    }
}

/** HVAC 좌석 area (VehicleAreaSeat). AAOS 에뮬레이터의 HVAC_TEMPERATURE_SET 설정과 맞춘다. */
enum class Seat(val areaId: Int, val tag: String) {
    DRIVER(0x1, "driver"), PASSENGER(0x4, "passenger");
}

/** HVAC_TEMPERATURE_SET 범위 (에뮬레이터 config: 16.0 ~ 28.0°C, 0.5 단위). */
object HvacSpec {
    const val MIN_C = 16f
    const val MAX_C = 28f
    const val STEP_C = 0.5f

    fun clamp(celsius: Float) = celsius.coerceIn(MIN_C, MAX_C)
}

/**
 * 차량 신호를 주고받는 경계.
 * - AAOS: [CarVehicleDataSource] (CarPropertyManager + CarUxRestrictionsManager)
 * - 일반 Android: [MockVehicleDataSource] (adb broadcast 로 값을 넣는다)
 * 화면과 테스트는 이 인터페이스만 본다.
 */
interface VehicleDataSource {
    val kind: String
    val state: StateFlow<VehicleState>
    fun start()
    fun stop()
    fun setTemperature(seat: Seat, celsius: Float)
}
