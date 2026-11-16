package dev.opencabin.ivi.vehicle

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import java.util.Locale

/**
 * CarService 가 없는 일반 Android(태블릿)용 가짜 차량.
 * 테스트는 adb broadcast 로 값을 넣고 읽는다 (debug 빌드에서만 받는다).
 *
 *   쓰기: adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.SET \
 *           --ef speed_kmh 50 --es gear D --ef temp_driver 25 --ef temp_passenger 20
 *         8단계: --ez ac true --ez auto false --ei fan 3 --ez defrost_front false --ez defrost_rear false
 *                --ei heat_driver 0 --ei heat_passenger 0 --ez doors_locked true --ef range_km 320 --ef battery_pct 80 --ef outside_c 18
 *   읽기: adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.GET
 *           → "Broadcast completed: result=0, data="speed_kmh=50.0;gear=D;..."
 *
 * 주행 중 제한 규칙은 AAOS 기본 설정과 맞춘다: P 가 아니고 속도가 0 보다 크면 제한.
 */
class MockVehicleDataSource(private val context: Context, private val acceptAdb: Boolean) : VehicleDataSource {
    override val kind = "Mock"

    private val _state = MutableStateFlow(
        VehicleState(
            driverTempC = 22f, passengerTempC = 22f, hvacAvailable = true, connected = true,
            acOn = true, fanSpeed = 3, doorsLocked = true, rangeKm = 320f, batteryPercent = 80f, outsideTempC = 18f,
        ),
    )
    override val state: StateFlow<VehicleState> = _state

    private var registered = false

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                ACTION_SET -> applyExtras(intent)
                ACTION_GET -> resultData = describe(_state.value)
            }
        }
    }

    override fun start() {
        if (registered || !acceptAdb) return
        val filter = IntentFilter().apply {
            addAction(ACTION_SET)
            addAction(ACTION_GET)
        }
        ContextCompat.registerReceiver(context, receiver, filter, ContextCompat.RECEIVER_EXPORTED)
        registered = true
    }

    override fun stop() {
        if (!registered) return
        context.unregisterReceiver(receiver)
        registered = false
    }

    override fun setTemperature(seat: Seat, celsius: Float) {
        val value = HvacSpec.clamp(celsius)
        _state.update {
            when (seat) {
                Seat.DRIVER -> it.copy(driverTempC = value)
                Seat.PASSENGER -> it.copy(passengerTempC = value)
            }
        }
    }

    override fun setAc(on: Boolean) = _state.update { it.copy(acOn = on) }
    override fun setAuto(on: Boolean) = _state.update { it.copy(autoOn = on) }
    override fun setFanSpeed(level: Int) = _state.update { it.copy(fanSpeed = level.coerceIn(HvacSpec.FAN_MIN, HvacSpec.FAN_MAX)) }
    override fun setDefrost(front: Boolean, on: Boolean) = _state.update { if (front) it.copy(defrostFront = on) else it.copy(defrostRear = on) }
    override fun setSeatHeat(seat: Seat, level: Int) = _state.update {
        val value = level.coerceIn(0, HvacSpec.SEAT_HEAT_MAX)
        if (seat == Seat.DRIVER) it.copy(driverSeatHeat = value) else it.copy(passengerSeatHeat = value)
    }
    override fun setDoorsLocked(locked: Boolean) = _state.update { it.copy(doorsLocked = locked) }

    private fun applyExtras(intent: Intent) {
        _state.update { current ->
            var next = current
            if (intent.hasExtra(EXTRA_SPEED)) next = next.copy(speedKmh = intent.getFloatExtra(EXTRA_SPEED, 0f).coerceAtLeast(0f))
            intent.getStringExtra(EXTRA_GEAR)?.let { next = next.copy(gear = Gear.fromLabel(it)) }
            if (intent.hasExtra(EXTRA_TEMP_DRIVER)) next = next.copy(driverTempC = HvacSpec.clamp(intent.getFloatExtra(EXTRA_TEMP_DRIVER, 22f)))
            if (intent.hasExtra(EXTRA_TEMP_PASSENGER)) next = next.copy(passengerTempC = HvacSpec.clamp(intent.getFloatExtra(EXTRA_TEMP_PASSENGER, 22f)))
            // 8단계 신호 (adb: --ez 불, --ei 정수, --ef 실수)
            if (intent.hasExtra(EXTRA_AC)) next = next.copy(acOn = intent.getBooleanExtra(EXTRA_AC, false))
            if (intent.hasExtra(EXTRA_AUTO)) next = next.copy(autoOn = intent.getBooleanExtra(EXTRA_AUTO, false))
            if (intent.hasExtra(EXTRA_FAN)) next = next.copy(fanSpeed = intent.getIntExtra(EXTRA_FAN, 3).coerceIn(HvacSpec.FAN_MIN, HvacSpec.FAN_MAX))
            if (intent.hasExtra(EXTRA_DEFROST_FRONT)) next = next.copy(defrostFront = intent.getBooleanExtra(EXTRA_DEFROST_FRONT, false))
            if (intent.hasExtra(EXTRA_DEFROST_REAR)) next = next.copy(defrostRear = intent.getBooleanExtra(EXTRA_DEFROST_REAR, false))
            if (intent.hasExtra(EXTRA_HEAT_DRIVER)) next = next.copy(driverSeatHeat = intent.getIntExtra(EXTRA_HEAT_DRIVER, 0).coerceIn(0, HvacSpec.SEAT_HEAT_MAX))
            if (intent.hasExtra(EXTRA_HEAT_PASSENGER)) next = next.copy(passengerSeatHeat = intent.getIntExtra(EXTRA_HEAT_PASSENGER, 0).coerceIn(0, HvacSpec.SEAT_HEAT_MAX))
            if (intent.hasExtra(EXTRA_DOORS_LOCKED)) next = next.copy(doorsLocked = intent.getBooleanExtra(EXTRA_DOORS_LOCKED, true))
            if (intent.hasExtra(EXTRA_RANGE)) next = next.copy(rangeKm = intent.getFloatExtra(EXTRA_RANGE, 0f).coerceAtLeast(0f))
            if (intent.hasExtra(EXTRA_BATTERY)) next = next.copy(batteryPercent = intent.getFloatExtra(EXTRA_BATTERY, 0f).coerceIn(0f, 100f))
            if (intent.hasExtra(EXTRA_OUTSIDE)) next = next.copy(outsideTempC = intent.getFloatExtra(EXTRA_OUTSIDE, 0f))
            next.copy(restricted = next.gear != Gear.PARK && next.speedKmh > 0f)
        }
    }

    private fun describe(s: VehicleState) = listOf(
        "speed_kmh=${fmt(s.speedKmh)}",
        "gear=${s.gear.label}",
        "temp_driver=${s.driverTempC?.let(::fmt) ?: "-"}",
        "temp_passenger=${s.passengerTempC?.let(::fmt) ?: "-"}",
        "restricted=${s.restricted}",
        "$EXTRA_AC=${s.acOn}",
        "$EXTRA_AUTO=${s.autoOn}",
        "$EXTRA_FAN=${s.fanSpeed}",
        "$EXTRA_DEFROST_FRONT=${s.defrostFront}",
        "$EXTRA_DEFROST_REAR=${s.defrostRear}",
        "$EXTRA_HEAT_DRIVER=${s.driverSeatHeat}",
        "$EXTRA_HEAT_PASSENGER=${s.passengerSeatHeat}",
        "$EXTRA_DOORS_LOCKED=${s.doorsLocked}",
        "$EXTRA_RANGE=${s.rangeKm?.let(::fmt) ?: "-"}",
        "$EXTRA_BATTERY=${s.batteryPercent?.let(::fmt) ?: "-"}",
        "$EXTRA_OUTSIDE=${s.outsideTempC?.let(::fmt) ?: "-"}",
    ).joinToString(";")

    private fun fmt(value: Float) = String.format(Locale.US, "%.1f", value)

    companion object {
        const val ACTION_SET = "dev.opencabin.ivi.mock.SET"
        const val ACTION_GET = "dev.opencabin.ivi.mock.GET"
        const val EXTRA_SPEED = "speed_kmh"
        const val EXTRA_GEAR = "gear"
        const val EXTRA_TEMP_DRIVER = "temp_driver"
        const val EXTRA_TEMP_PASSENGER = "temp_passenger"
        const val EXTRA_AC = "ac"
        const val EXTRA_AUTO = "auto"
        const val EXTRA_FAN = "fan"
        const val EXTRA_DEFROST_FRONT = "defrost_front"
        const val EXTRA_DEFROST_REAR = "defrost_rear"
        const val EXTRA_HEAT_DRIVER = "heat_driver"
        const val EXTRA_HEAT_PASSENGER = "heat_passenger"
        const val EXTRA_DOORS_LOCKED = "doors_locked"
        const val EXTRA_RANGE = "range_km"
        const val EXTRA_BATTERY = "battery_pct"
        const val EXTRA_OUTSIDE = "outside_c"
    }
}
