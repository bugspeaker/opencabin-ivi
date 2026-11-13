package dev.opencabin.ivi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.opencabin.ivi.ui.IviColors
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
                    Modifier
                        .fillMaxSize()
                        .background(IviColors.Background)
                        .semantics { testTagsAsResourceId = true },
                ) {
                    if (state.restricted) Blocked { finish() } else Player { finish() }
                }
            }
        }
    }
}

@Composable
private fun Blocked(onClose: () -> Unit) {
    Column(
        Modifier.fillMaxSize().testTag("video_blocked"),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterVertically),
    ) {
        Text("⏸", fontSize = 48.sp, color = IviColors.Warn)
        Text("주행 중에는 영상을 볼 수 없습니다", fontSize = 28.sp, fontWeight = FontWeight.Medium)
        Text("차를 세우면 이어서 볼 수 있습니다", color = IviColors.TextSecondary, fontSize = 18.sp)
        CloseButton(onClose)
    }
}

@Composable
private fun Player(onClose: () -> Unit) {
    var seconds by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            seconds++
        }
    }
    val length = 3 * 60 + 24
    Column(Modifier.fillMaxSize().padding(24.dp).testTag("video_player"), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Coastal Road — 주행 영상", fontSize = 20.sp, fontWeight = FontWeight.Medium)
            Spacer(Modifier.weight(1f))
            CloseButton(onClose)
        }
        // 영상 자리: 실제 영상 대신 그라데이션 화면 (재생 시간만 흐른다)
        Box(
            Modifier
                .fillMaxWidth()
                .weight(1f)
                .clip(RoundedCornerShape(20.dp))
                .background(Brush.linearGradient(listOf(IviColors.AquaDeep, IviColors.Background))),
            contentAlignment = Alignment.Center,
        ) {
            Text("▶  영상 재생 중", fontSize = 30.sp, fontWeight = FontWeight.Light)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(clock(seconds), Modifier.testTag("video_elapsed"), fontSize = 18.sp)
            Box(
                Modifier
                    .weight(1f)
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(IviColors.Line),
            ) {
                Box(
                    Modifier
                        .fillMaxWidth((seconds % length).toFloat() / length)
                        .fillMaxHeight()
                        .background(IviColors.Aqua),
                )
            }
            Text(clock(length), color = IviColors.TextSecondary, fontSize = 18.sp)
        }
    }
}

@Composable
private fun CloseButton(onClose: () -> Unit) {
    Button(
        onClick = onClose,
        modifier = Modifier.testTag("video_close").height(56.dp).width(120.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = IviColors.SurfaceHigh, contentColor = IviColors.TextPrimary),
    ) { Text("닫기", fontSize = 18.sp) }
}

private fun clock(seconds: Int) = "%02d:%02d".format(seconds / 60, seconds % 60)
