package dev.opencabin.ivi

import android.app.Application
import android.content.pm.PackageManager
import dev.opencabin.ivi.vehicle.CarVehicleDataSource
import dev.opencabin.ivi.vehicle.MockVehicleDataSource
import dev.opencabin.ivi.vehicle.VehicleDataSource

/** 기기 종류에 따라 차량 데이터 소스를 고른다. AAOS 면 실제 CarService, 아니면 Mock. */
class IviApp : Application() {
    lateinit var vehicle: VehicleDataSource
        private set

    override fun onCreate() {
        super.onCreate()
        vehicle = if (packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE)) {
            CarVehicleDataSource(this)
        } else {
            MockVehicleDataSource(this, acceptAdb = BuildConfig.DEBUG)
        }
        vehicle.start()
    }
}
