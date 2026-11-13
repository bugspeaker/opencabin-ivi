package dev.opencabin.ivi.vehicle

import android.car.Car
import android.car.VehiclePropertyIds
import android.car.drivingstate.CarUxRestrictions
import android.car.drivingstate.CarUxRestrictionsManager
import android.car.hardware.CarPropertyValue
import android.car.hardware.property.CarPropertyManager
import android.content.Context
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

/**
 * AAOS 의 CarService 와 연결한다.
 * 속도·기어는 구독만, 공조 온도는 구독 + 쓰기. 주행 중 제한은 CarUxRestrictionsManager 를 그대로 따른다.
 */
class CarVehicleDataSource(private val context: Context) : VehicleDataSource {
    override val kind = "AAOS"

    private val _state = MutableStateFlow(VehicleState())
    override val state: StateFlow<VehicleState> = _state

    private var car: Car? = null
    private var properties: CarPropertyManager? = null
    private var uxRestrictions: CarUxRestrictionsManager? = null

    private val propertyCallback = object : CarPropertyManager.CarPropertyEventCallback {
        override fun onChangeEvent(value: CarPropertyValue<*>) = apply(value)
        override fun onErrorEvent(propertyId: Int, areaId: Int) {
            Log.w(TAG, "property error ${propertyId.toString(16)} area ${areaId.toString(16)}")
        }
    }

    private val uxListener = CarUxRestrictionsManager.OnUxRestrictionsChangedListener { applyRestrictions(it) }

    override fun start() {
        if (car != null) return
        car = Car.createCar(context, null, Car.CAR_WAIT_TIMEOUT_WAIT_FOREVER) { connected, ready ->
            if (ready) onConnected(connected) else onDisconnected()
        }
    }

    override fun stop() {
        properties?.unregisterCallback(propertyCallback)
        uxRestrictions?.unregisterListener()
        car?.disconnect()
        car = null
        properties = null
        uxRestrictions = null
        _state.update { it.copy(connected = false) }
    }

    override fun setTemperature(seat: Seat, celsius: Float) {
        val manager = properties ?: return
        try {
            manager.setFloatProperty(VehiclePropertyIds.HVAC_TEMPERATURE_SET, seat.areaId, HvacSpec.clamp(celsius))
        } catch (e: SecurityException) {
            _state.update { it.copy(hvacAvailable = false, error = "공조 쓰기 권한 없음") }
        } catch (e: RuntimeException) {
            Log.w(TAG, "HVAC 쓰기 실패", e)
            _state.update { it.copy(error = "공조 쓰기 실패: ${e.javaClass.simpleName}") }
        }
    }

    private fun onConnected(connected: Car) {
        val manager = connected.getCarManager(Car.PROPERTY_SERVICE) as CarPropertyManager
        properties = manager
        _state.update { it.copy(connected = true, error = null) }

        subscribe(manager, VehiclePropertyIds.PERF_VEHICLE_SPEED, CarPropertyManager.SENSOR_RATE_UI)
        subscribe(manager, VehiclePropertyIds.GEAR_SELECTION, CarPropertyManager.SENSOR_RATE_ONCHANGE)
        val hvac = subscribe(manager, VehiclePropertyIds.HVAC_TEMPERATURE_SET, CarPropertyManager.SENSOR_RATE_ONCHANGE)
        _state.update { it.copy(hvacAvailable = hvac) }

        // 구독 직후 이벤트가 오기 전까지 비어 보이지 않게 현재 값을 한 번 읽는다
        readOnce { apply(manager.getProperty(Float::class.javaObjectType, VehiclePropertyIds.PERF_VEHICLE_SPEED, 0)) }
        readOnce { apply(manager.getProperty(Int::class.javaObjectType, VehiclePropertyIds.GEAR_SELECTION, 0)) }
        if (hvac) Seat.entries.forEach { seat ->
            readOnce { apply(manager.getProperty(Float::class.javaObjectType, VehiclePropertyIds.HVAC_TEMPERATURE_SET, seat.areaId)) }
        }

        val ux = connected.getCarManager(Car.CAR_UX_RESTRICTION_SERVICE) as CarUxRestrictionsManager
        uxRestrictions = ux
        ux.registerListener(uxListener)
        applyRestrictions(ux.currentCarUxRestrictions)
    }

    private fun onDisconnected() {
        properties = null
        uxRestrictions = null
        _state.update { it.copy(connected = false, error = "CarService 연결 끊김") }
    }

    /** 권한이 없으면 SecurityException. 공조처럼 권한이 높은 값은 false 를 돌려 화면이 '권한 없음'을 보여 주게 한다. */
    private fun subscribe(manager: CarPropertyManager, propertyId: Int, rate: Float): Boolean = try {
        manager.registerCallback(propertyCallback, propertyId, rate)
    } catch (e: SecurityException) {
        Log.w(TAG, "구독 권한 없음: ${VehiclePropertyIds.toString(propertyId)}")
        false
    } catch (e: IllegalArgumentException) {
        Log.w(TAG, "지원하지 않는 property: ${VehiclePropertyIds.toString(propertyId)}")
        false
    }

    private inline fun readOnce(block: () -> Unit) {
        try {
            block()
        } catch (e: RuntimeException) {
            Log.w(TAG, "초기 값 읽기 실패: ${e.message}")
        }
    }

    private fun apply(value: CarPropertyValue<*>) {
        if (value.status != CarPropertyValue.STATUS_AVAILABLE) return
        when (value.propertyId) {
            VehiclePropertyIds.PERF_VEHICLE_SPEED ->
                _state.update { it.copy(speedKmh = (value.value as Float) * MPS_TO_KMH) }
            VehiclePropertyIds.GEAR_SELECTION ->
                _state.update { it.copy(gear = Gear.fromVhal(value.value as Int)) }
            VehiclePropertyIds.HVAC_TEMPERATURE_SET -> {
                val celsius = value.value as Float
                when (value.areaId) {
                    Seat.DRIVER.areaId -> _state.update { it.copy(driverTempC = celsius) }
                    Seat.PASSENGER.areaId -> _state.update { it.copy(passengerTempC = celsius) }
                }
            }
        }
    }

    private fun applyRestrictions(restrictions: CarUxRestrictions) {
        _state.update { it.copy(restricted = restrictions.isRequiresDistractionOptimization) }
    }

    private companion object {
        const val TAG = "OpenCabin.Car"
        const val MPS_TO_KMH = 3.6f
    }
}
