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
    /**
     * 지금 걸린 UX 제한의 종류 (UxRules 비트, CarUxRestrictions 의 활성 제한과 같은 값). 0 이면 제한 없음.
     * 화면은 주행 상태가 아니라 이 비트를 보고 막는다: 영상은 NO_VIDEO, 글자 입력은 NO_KEYBOARD, 키패드는 NO_DIALPAD.
     */
    val uxRestrictions: Int = UxRules.NONE,
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

    /** 무엇이든 UX 제한이 걸려 있는가 (상단 배지). P 가 아니면 멈춰 있어도 영상 제한이 걸린다. */
    val restricted get() = uxRestrictions != UxRules.NONE

    /** 이 종류의 제한이 걸려 있는가. 예: blocks(UxRules.NO_VIDEO) */
    fun blocks(rule: Int) = (uxRestrictions and rule) != 0

    /**
     * 차가 움직이는가 (P 가 아니고 속도 > 0). UX 제한에 없는 앱의 차량 제어 잠금(사이드 미러 접기, 트렁크)과
     * '주행 중' 표시·알림에 쓴다. D 기어로 멈춰 있을 때(신호 대기)는 false 다.
     */
    val moving get() = gear != Gear.PARK && speedKmh > 0f

    /** 주행 가능 거리가 이 값 이하면 충전소 안내를 권한다. */
    val lowRange get() = rangeKm != null && rangeKm <= LOW_RANGE_KM

    companion object {
        const val LOW_RANGE_KM = 30f
    }
}

/**
 * 주행 중 UX 제한의 종류. android.car.drivingstate.CarUxRestrictions 의 UX_RESTRICTIONS_* 와 같은 값이다.
 * AOSP 는 앱이 주행 상태(정차·정지·주행)가 아니라 이 제한 정보를 보고 기능을 막으라고 권한다. 시장마다 제한이 다를 수 있어서다.
 * AAOS 에서는 CarUxRestrictionsManager 가 준 값을 그대로 쓰고, 일반 Android(Mock)는 forDriving() 으로 같은 표를 흉내 낸다.
 * android.car 를 쓰지 않는 순수 Kotlin 이라 JVM 단위 테스트(UxRulesTest)로 표를 확인한다.
 */
object UxRules {
    const val NONE = 0
    const val NO_DIALPAD = 0x1
    const val NO_FILTERING = 0x2
    const val LIMIT_STRING_LENGTH = 0x4
    const val NO_KEYBOARD = 0x8
    const val NO_VIDEO = 0x10
    const val LIMIT_CONTENT = 0x20
    const val NO_SETUP = 0x40
    const val NO_TEXT_MESSAGE = 0x80
    const val NO_VOICE_TRANSCRIPTION = 0x100
    const val FULLY_RESTRICTED = 0x1ff

    /**
     * AAOS 에뮬레이터(sdk_gcar_x86_64, API 34)의 car_ux_restrictions_map 과 같은 표.
     * 2026-11-23 `dumpsys car_service --services CarUxRestrictionsManagerService` 로 확인:
     * parked 0x0, idling(P 아님, 0 km/h) 0x10 (영상만), moving 0xff (0~5 km/h, 5 km/h~ 같은 값).
     */
    const val IDLING = NO_VIDEO
    const val MOVING = 0xff

    fun forDriving(gear: Gear, speedKmh: Float) = when {
        gear == Gear.PARK -> NONE
        speedKmh <= 0f -> IDLING
        else -> MOVING
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
