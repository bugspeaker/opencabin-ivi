package dev.opencabin.ivi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.opencabin.ivi.ui.IviTheme
import kotlinx.coroutines.delay

/**
 * 가짜 영상 재생 화면 (주의 분산 기능).
 * 매니페스트에서 distractionOptimized 가 아니므로 AAOS 는 주행 중에 시스템이 이 화면을 막는다.
 * 태블릿(Mock)에는 그런 시스템이 없어서 앱이 직접 막는다 → 두 기기 모두 '주행 중 영상 차단' 을 같은 테스트로 본다.
 */
class VideoActivity : ComponentActivity() {
    @OptIn(ExperimentalComposeUiApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val vehicle = (application as IviApp).vehicle
        setContent {
            val state = vehicle.state.collectAsStateWithLifecycle().value
            IviTheme {
                Box(
                    Modifier.fillMaxSize().background(Color.Black).semantics { testTagsAsResourceId = true },
                    contentAlignment = Alignment.Center,
                ) {
                    if (state.restricted) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.testTag("video_blocked")) {
                            Text("주행 중에는 영상을 볼 수 없습니다", color = Color.White, fontSize = 28.sp)
                            Button(onClick = { finish() }, modifier = Modifier.testTag("video_close")) { Text("닫기") }
                        }
                    } else {
                        Player { finish() }
                    }
                }
            }
        }
    }
}

@androidx.compose.runtime.Composable
private fun Player(onClose: () -> Unit) {
    var seconds by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1000)
            seconds++
        }
    }
    Column(
        Modifier.testTag("video_player"),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp()),
    ) {
        Text("▶ 영상 재생 중", color = Color.White, fontSize = 32.sp)
        Text("%02d:%02d".format(seconds / 60, seconds % 60), Modifier.testTag("video_elapsed"), color = Color.LightGray, fontSize = 24.sp)
        Button(onClick = onClose, modifier = Modifier.testTag("video_close")) { Text("닫기") }
    }
}

private fun Int.dp() = androidx.compose.ui.unit.Dp(this.toFloat())
