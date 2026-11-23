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
 *
 * 8단계에서 더한 신호 (권한):
 *   공조 A/C · AUTO · 최대 냉방 · 풍량 · 김서림 · 좌석 열선   구독 + 쓰기   CONTROL_CAR_CLIMATE (signature|privileged)
 *   도어 잠금 DOOR_LOCK                          구독 + 쓰기   CONTROL_CAR_DOORS   (signature|privileged)
 *   주행 가능 거리 · 배터리 잔량                   구독         CAR_ENERGY          (dangerous)
 *   배터리 용량 · 외기 온도                        읽기/구독     CAR_INFO · CAR_EXTERIOR_ENVIRONMENT (normal)
 * 권한이 없는 신호는 구독이 실패하고(SecurityException) 화면에는 '값 없음' 으로 남는다. 앱은 죽지 않는다.
 */
// registerCallback·unregisterCallback·CarPropertyValue.status 는 API 35 에서 deprecated 다.
// 대상 기기(AAOS 에뮬레이터)가 API 34 라 대체 API(subscribePropertyEvents, propertyStatus)를 쓸 수 없어 그대로 둔다.
@Suppress("DEPRECATION")
class CarVehicleDataSource(private val context: Context) : VehicleDataSource {
    override val kind = "AAOS"

    private val _state = MutableStateFlow(VehicleState())
    override val state: StateFlow<VehicleState> = _state

    private var car: Car? = null
    private var properties: CarPropertyManager? = null
    private var uxRestrictions: CarUxRestrictionsManager? = null
    private var batteryCapacityWh = 0f

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

    // ---- 8단계: 쓰기 ----
    override fun setAc(on: Boolean) = writeAll(VehiclePropertyIds.HVAC_AC_ON, on)

    override fun setAuto(on: Boolean) = writeAll(VehiclePropertyIds.HVAC_AUTO_ON, on)

    override fun setMaxAc(on: Boolean) = writeAll(VehiclePropertyIds.HVAC_MAX_AC_ON, on)

    override fun setFanSpeed(level: Int) = writeAll(VehiclePropertyIds.HVAC_FAN_SPEED, level.coerceIn(HvacSpec.FAN_MIN, HvacSpec.FAN_MAX))

    override fun setDefrost(front: Boolean, on: Boolean) =
        writeAll(VehiclePropertyIds.HVAC_DEFROSTER, on, only = if (front) WINDOW_FRONT else WINDOW_REAR)

    override fun setSeatHeat(seat: Seat, level: Int) =
        writeAll(VehiclePropertyIds.HVAC_SEAT_TEMPERATURE, level.coerceIn(0, HvacSpec.SEAT_HEAT_MAX), only = seat.areaId)

    override fun setDoorsLocked(locked: Boolean) = writeAll(VehiclePropertyIds.DOOR_LOCK, locked)

    /**
     * property 의 모든 area(좌석·문)에 같은 값을 쓴다. only 를 주면 그 좌석(창)을 포함하는 area 에만 쓴다.
     * area 구성은 차마다 다르므로 CarPropertyConfig 에서 읽는다 (에뮬레이터: 좌석 5개가 각각 한 area).
     */
    private fun writeAll(propertyId: Int, value: Any, only: Int? = null) {
        val manager = properties ?: return
        try {
            val areas = manager.getCarPropertyConfig(propertyId)?.areaIds ?: return
            for (area in areas) {
                if (only != null && area and only == 0) continue
                when (value) {
                    is Boolean -> manager.setBooleanProperty(propertyId, area, value)
                    is Int -> manager.setIntProperty(propertyId, area, value)
                }
            }
        } catch (e: SecurityException) {
            _state.update { it.copy(error = "쓰기 권한 없음: ${VehiclePropertyIds.toString(propertyId)}") }
        } catch (e: RuntimeException) {
            Log.w(TAG, "쓰기 실패 ${VehiclePropertyIds.toString(propertyId)}", e)
            _state.update { it.copy(error = "쓰기 실패: ${e.javaClass.simpleName}") }
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

        // 8단계 신호: 구독하고, 이벤트가 오기 전까지 비어 보이지 않게 지금 값을 한 번 읽는다
        if (hvac) {
            for (id in HVAC_EXTRA) {
                if (!subscribe(manager, id, CarPropertyManager.SENSOR_RATE_ONCHANGE)) continue
                val isInt = id == VehiclePropertyIds.HVAC_FAN_SPEED || id == VehiclePropertyIds.HVAC_SEAT_TEMPERATURE
                manager.getCarPropertyConfig(id)?.areaIds?.forEach { area ->
                    readOnce {
                        if (isInt) apply(manager.getProperty(Int::class.javaObjectType, id, area))
                        else apply(manager.getProperty(Boolean::class.javaObjectType, id, area))
                    }
                }
            }
        }
        if (subscribe(manager, VehiclePropertyIds.DOOR_LOCK, CarPropertyManager.SENSOR_RATE_ONCHANGE)) {
            readOnce { apply(manager.getProperty(Boolean::class.javaObjectType, VehiclePropertyIds.DOOR_LOCK, DOOR_DRIVER)) }
        }
        readOnce { batteryCapacityWh = manager.getFloatProperty(VehiclePropertyIds.INFO_EV_BATTERY_CAPACITY, 0) }
        for (id in SENSORS) {
            if (subscribe(manager, id, CarPropertyManager.SENSOR_RATE_NORMAL)) {
                readOnce { apply(manager.getProperty(Float::class.javaObjectType, id, 0)) }
            }
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
            // 전 좌석에 같은 값을 쓰는 신호는 운전석 area 의 값을 화면에 쓴다
            VehiclePropertyIds.HVAC_AC_ON -> if (value.isFor(Seat.DRIVER)) _state.update { it.copy(acOn = value.value as Boolean) }
            VehiclePropertyIds.HVAC_AUTO_ON -> if (value.isFor(Seat.DRIVER)) _state.update { it.copy(autoOn = value.value as Boolean) }
            VehiclePropertyIds.HVAC_MAX_AC_ON -> if (value.isFor(Seat.DRIVER)) _state.update { it.copy(maxAcOn = value.value as Boolean) }
            VehiclePropertyIds.HVAC_FAN_SPEED -> if (value.isFor(Seat.DRIVER)) _state.update { it.copy(fanSpeed = value.value as Int) }
            VehiclePropertyIds.HVAC_SEAT_TEMPERATURE -> {
                val level = (value.value as Int).coerceAtLeast(0) // 음수(통풍)는 열선 꺼짐으로 본다
                if (value.isFor(Seat.DRIVER)) _state.update { it.copy(driverSeatHeat = level) }
                if (value.isFor(Seat.PASSENGER)) _state.update { it.copy(passengerSeatHeat = level) }
            }
            VehiclePropertyIds.HVAC_DEFROSTER -> {
                val on = value.value as Boolean
                if (value.areaId and WINDOW_FRONT != 0) _state.update { it.copy(defrostFront = on) }
                if (value.areaId and WINDOW_REAR != 0) _state.update { it.copy(defrostRear = on) }
            }
            VehiclePropertyIds.DOOR_LOCK ->
                if (value.areaId and DOOR_DRIVER != 0) _state.update { it.copy(doorsLocked = value.value as Boolean) }
            VehiclePropertyIds.RANGE_REMAINING -> _state.update { it.copy(rangeKm = (value.value as Float) / 1000f) }
            VehiclePropertyIds.EV_BATTERY_LEVEL -> if (batteryCapacityWh > 0f) {
                _state.update { it.copy(batteryPercent = ((value.value as Float) / batteryCapacityWh * 100f).coerceIn(0f, 100f)) }
            }
            VehiclePropertyIds.ENV_OUTSIDE_TEMPERATURE -> _state.update { it.copy(outsideTempC = value.value as Float) }
        }
    }

    private fun CarPropertyValue<*>.isFor(seat: Seat) = areaId and seat.areaId != 0

    /**
     * 플랫폼이 정한 제한 종류를 그대로 쓴다. 예전에는 requiresDistractionOptimization 하나만 보고 모든 기능을 막아서,
     * D 기어로 멈춰 있을 때(플랫폼은 영상만 막음, 0x10) 검색·키패드까지 막았다 (2026-11-23 찾은 결함).
     */
    private fun applyRestrictions(restrictions: CarUxRestrictions) {
        val active = if (restrictions.isRequiresDistractionOptimization) restrictions.activeRestrictions else UxRules.NONE
        _state.update { it.copy(uxRestrictions = active) }
    }

    private companion object {
        const val TAG = "OpenCabin.Car"
        const val MPS_TO_KMH = 3.6f

        // VehicleAreaWindow · VehicleAreaDoor
        const val WINDOW_FRONT = 0x1
        const val WINDOW_REAR = 0x2
        const val DOOR_DRIVER = 0x1

        val HVAC_EXTRA = intArrayOf(
            VehiclePropertyIds.HVAC_AC_ON, VehiclePropertyIds.HVAC_AUTO_ON, VehiclePropertyIds.HVAC_MAX_AC_ON, VehiclePropertyIds.HVAC_FAN_SPEED,
            VehiclePropertyIds.HVAC_SEAT_TEMPERATURE, VehiclePropertyIds.HVAC_DEFROSTER,
        )
        val SENSORS = intArrayOf(
            VehiclePropertyIds.RANGE_REMAINING, VehiclePropertyIds.EV_BATTERY_LEVEL, VehiclePropertyIds.ENV_OUTSIDE_TEMPERATURE,
        )
    }
}
