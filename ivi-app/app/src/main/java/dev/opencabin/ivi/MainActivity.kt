package dev.opencabin.ivi

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.remember
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.opencabin.ivi.state.CabinController
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
        val app = application as IviApp
        val vehicle = app.vehicle
        val store = app.settings
        setContent {
            val state = vehicle.state.collectAsStateWithLifecycle().value
            val settings = store.settings.collectAsStateWithLifecycle().value
            // 화면 상태(오디오·안내·통화)는 이 화면과 함께 산다. --activity-clear-task 로 다시 열면 처음부터
            val cabin = remember { CabinController(store, vehicle) }
            IviTheme {
                IviRoot(
                    source = vehicle.kind,
                    state = state,
                    settings = settings,
                    store = store,
                    cabin = cabin,
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
