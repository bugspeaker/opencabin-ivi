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
 *   읽기: adb shell am broadcast -p dev.opencabin.ivi -a dev.opencabin.ivi.mock.GET
 *           → "Broadcast completed: result=0, data="speed_kmh=50.0;gear=D;..."
 *
 * 주행 중 제한 규칙은 AAOS 기본 설정과 맞춘다: P 가 아니고 속도가 0 보다 크면 제한.
 */
class MockVehicleDataSource(private val context: Context, private val acceptAdb: Boolean) : VehicleDataSource {
    override val kind = "Mock"

    private val _state = MutableStateFlow(
        VehicleState(driverTempC = 22f, passengerTempC = 22f, hvacAvailable = true, connected = true),
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

    private fun applyExtras(intent: Intent) {
        _state.update { current ->
            var next = current
            if (intent.hasExtra(EXTRA_SPEED)) next = next.copy(speedKmh = intent.getFloatExtra(EXTRA_SPEED, 0f).coerceAtLeast(0f))
            intent.getStringExtra(EXTRA_GEAR)?.let { next = next.copy(gear = Gear.fromLabel(it)) }
            if (intent.hasExtra(EXTRA_TEMP_DRIVER)) next = next.copy(driverTempC = HvacSpec.clamp(intent.getFloatExtra(EXTRA_TEMP_DRIVER, 22f)))
            if (intent.hasExtra(EXTRA_TEMP_PASSENGER)) next = next.copy(passengerTempC = HvacSpec.clamp(intent.getFloatExtra(EXTRA_TEMP_PASSENGER, 22f)))
            next.copy(restricted = next.gear != Gear.PARK && next.speedKmh > 0f)
        }
    }

    private fun describe(s: VehicleState) = listOf(
        "speed_kmh=${fmt(s.speedKmh)}",
        "gear=${s.gear.label}",
        "temp_driver=${s.driverTempC?.let(::fmt) ?: "-"}",
        "temp_passenger=${s.passengerTempC?.let(::fmt) ?: "-"}",
        "restricted=${s.restricted}",
    ).joinToString(";")

    private fun fmt(value: Float) = String.format(Locale.US, "%.1f", value)

    companion object {
        const val ACTION_SET = "dev.opencabin.ivi.mock.SET"
        const val ACTION_GET = "dev.opencabin.ivi.mock.GET"
        const val EXTRA_SPEED = "speed_kmh"
        const val EXTRA_GEAR = "gear"
        const val EXTRA_TEMP_DRIVER = "temp_driver"
        const val EXTRA_TEMP_PASSENGER = "temp_passenger"
    }
}
