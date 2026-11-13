package dev.opencabin.ivi

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.opencabin.ivi.ui.IviRoot
import dev.opencabin.ivi.ui.IviTheme

class MainActivity : ComponentActivity() {

    /** 권한을 받으면 속도 구독을 다시 하도록 CarService 연결을 새로 만든다. */
    private val carPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            val vehicle = (application as IviApp).vehicle
            vehicle.stop()
            vehicle.start()
        }
    }

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

    /** CAR_SPEED 는 dangerous 권한이라 실행 중에 요청한다. 자동화에서는 adb 로 미리 준다 (pm grant --user 10). */
    private fun requestCarPermissions() {
        if (!packageManager.hasSystemFeature(PackageManager.FEATURE_AUTOMOTIVE)) return
        if (checkSelfPermission(CAR_SPEED) != PackageManager.PERMISSION_GRANTED) {
            carPermission.launch(CAR_SPEED)
        }
    }

    private companion object {
        const val CAR_SPEED = "android.car.permission.CAR_SPEED"
    }
}
