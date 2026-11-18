package dev.opencabin.ivi.vehicle

import kotlinx.coroutines.flow.StateFlow
import kotlin.math.ceil
import kotlin.math.floor

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

    // ---- 8단계: 화면 상태였던 것을 차량 신호로 (docs/phase8-signals.md) ----
    /** HVAC_AC_ON */
    val acOn: Boolean = false,
    /** HVAC_MAX_AC_ON: 최대 냉방. 화면에는 FULL 로 표시한다 */
    val maxAcOn: Boolean = false,
    /** HVAC_AUTO_ON */
    val autoOn: Boolean = false,
    /** HVAC_FAN_SPEED (1 ~ 7) */
    val fanSpeed: Int = HvacSpec.FAN_MIN,
    /** HVAC_DEFROSTER 앞 유리 / 뒤 유리 */
    val defrostFront: Boolean = false,
    val defrostRear: Boolean = false,
    /** HVAC_SEAT_TEMPERATURE: 0 꺼짐, 1 ~ 2 열선 단계 (에뮬레이터 범위 -2 ~ 2, 음수는 통풍이라 쓰지 않는다) */
    val driverSeatHeat: Int = 0,
    val passengerSeatHeat: Int = 0,
    /** DOOR_LOCK (운전석 문 기준). null 이면 읽을 수 없다: AAOS 에서 CONTROL_CAR_DOORS(signature|privileged) 권한이 없을 때 */
    val doorsLocked: Boolean? = null,
    /** RANGE_REMAINING (m → km). null 이면 값 없음 (CAR_ENERGY 권한 없음 등) */
    val rangeKm: Float? = null,
    /** EV_BATTERY_LEVEL / INFO_EV_BATTERY_CAPACITY (Wh → %) */
    val batteryPercent: Float? = null,
    /** ENV_OUTSIDE_TEMPERATURE (°C) */
    val outsideTempC: Float? = null,
) {
    fun seatHeat(seat: Seat) = if (seat == Seat.DRIVER) driverSeatHeat else passengerSeatHeat

    /** 주행 가능 거리가 이 값 이하면 충전소 안내를 권한다. */
    val lowRange get() = rangeKm != null && rangeKm <= LOW_RANGE_KM

    companion object {
        const val LOW_RANGE_KM = 30f
    }
}

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

    /**
     * 온도 버튼 한 칸. 0.5°C 단위에 맞춘 바로 위(아래) 값이고, 범위 밖이면 끝값이다.
     * 차량 쪽에서 22.3°C 처럼 단위가 어긋난 값이 오면 + 는 22.5, - 는 22.0 (2026-11-18 경계값 테스트에서 찾은 결함:
     * 전에는 22.3 ± 0.5 = 22.8 / 21.8 을 그대로 차량에 썼다).
     */
    fun stepUp(celsius: Float) = clamp(floor(celsius / STEP_C + EPS) * STEP_C + STEP_C)
    fun stepDown(celsius: Float) = clamp(ceil(celsius / STEP_C - EPS) * STEP_C - STEP_C)
    private const val EPS = 1e-3f

    /** HVAC_FAN_SPEED 범위 (에뮬레이터 config: 1 ~ 7). */
    const val FAN_MIN = 1
    const val FAN_MAX = 7

    /** 좌석 열선 단계 (HVAC_SEAT_TEMPERATURE 의 양수 쪽: 에뮬레이터 config 최대 2). */
    const val SEAT_HEAT_MAX = 2

    /** 열선 버튼을 누를 때마다: 꺼짐 → 2단 → 1단 → 꺼짐 (양산차의 일반적인 순서). */
    fun nextSeatHeat(level: Int) = if (level <= 0) SEAT_HEAT_MAX else level - 1
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

    // 8단계: 아래 값은 모든 좌석(문) area 에 같은 값을 쓴다 (전 좌석 공조 · 전 도어 잠금)
    fun setAc(on: Boolean)
    fun setAuto(on: Boolean)
    fun setMaxAc(on: Boolean)
    fun setFanSpeed(level: Int)
    fun setDefrost(front: Boolean, on: Boolean)
    fun setSeatHeat(seat: Seat, level: Int)
    fun setDoorsLocked(locked: Boolean)
}
