package dev.opencabin.ivi

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.opencabin.ivi.ui.IviRoot
import dev.opencabin.ivi.ui.IviTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestCarPermissions()
        val vehicle = (application as IviApp).vehicle
        setContent {
            val state = vehicle.state.collectAsStateWithLifecycle().value
            IviTheme {
                IviRoot(
                    source = vehicle.kind,
                    state = state,
                    onSetTemperature = vehicle::setTemperature,
                    onOpenVideo = { startActivity(Intent(this, VideoActivity::class.java)) },
                )
            }
        }
    }

    /** CAR_SPEED 는 dangerous 권한이라 실행 중에 요청한다. 자동화에서는 adb 로 미리 준다 (pm grant). */
    private fun requestCarPermissions() {
        if (!packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE)) return
        if (checkSelfPermission(CAR_SPEED) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(CAR_SPEED), 1)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        // 권한을 받은 뒤 속도 구독을 다시 하도록 연결을 새로 만든다
        val vehicle = (application as IviApp).vehicle
        vehicle.stop()
        vehicle.start()
    }

    private companion object {
        const val CAR_SPEED = "android.car.permission.CAR_SPEED"
    }
}
