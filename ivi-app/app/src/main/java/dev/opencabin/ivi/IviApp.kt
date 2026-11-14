package dev.opencabin.ivi

import android.app.Application
import android.content.pm.PackageManager
import dev.opencabin.ivi.state.SettingsStore
import dev.opencabin.ivi.vehicle.CarVehicleDataSource
import dev.opencabin.ivi.vehicle.MockVehicleDataSource
import dev.opencabin.ivi.vehicle.VehicleDataSource

/** 앱 전체에서 하나씩 쓰는 것: 차량 데이터 소스(AAOS 면 CarService, 아니면 Mock)와 저장 설정. */
class IviApp : Application() {
    lateinit var vehicle: VehicleDataSource
        private set
    lateinit var settings: SettingsStore
        private set

    override fun onCreate() {
        super.onCreate()
        settings = SettingsStore(this)
        vehicle = if (packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE)) {
            CarVehicleDataSource(this)
        } else {
            MockVehicleDataSource(this, acceptAdb = BuildConfig.DEBUG)
        }
        vehicle.start()
    }
}
