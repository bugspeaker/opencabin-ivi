package dev.opencabin.ivi

import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
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
import androidx.compose.runtime.mutableLongStateOf
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
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player as Media3Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import dev.opencabin.ivi.ui.IviColors
import dev.opencabin.ivi.ui.IviTheme
import kotlinx.coroutines.delay

/**
 * 영상 재생 화면 (주의 분산 기능).
 * 매니페스트에서 distractionOptimized 가 아니므로 AAOS 는 주행 중에 시스템이 이 화면을 막는다.
 * 태블릿(Mock)에는 그런 시스템이 없어서 앱이 직접 막는다 → 두 기기 모두 '주행 중 영상 차단' 을 같은 테스트로 본다.
 *
 * 재생할 영상: 앱 전용 폴더 files/drive/ 의 mp4 (블랙박스 영상, tools/push_drive_videos.py 로 올린다).
 * 영상이 없으면 가짜 재생 화면(재생 시간만 흐른다)을 보여 준다. 테스트 태그는 둘 다 같다.
 * 주행으로 바뀌어 막히면 멈추고, 정차하면 그 자리에서 이어서 재생한다.
 */
class VideoActivity : ComponentActivity() {
    private var player: ExoPlayer? = null
    private var started = false

    @OptIn(ExperimentalComposeUiApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val vehicle = (application as IviApp).vehicle
        player = driveClips().takeIf { it.isNotEmpty() }?.let { clips ->
            ExoPlayer.Builder(this).build().apply {
                setMediaItems(clips.map { MediaItem.fromUri(Uri.fromFile(it)) })
                repeatMode = Media3Player.REPEAT_MODE_ALL
                volume = 0f  // 음성은 올릴 때 지웠지만, 다른 영상이 들어와도 소리는 내지 않는다
                prepare()
            }
        }
        setContent {
            val state = vehicle.state.collectAsStateWithLifecycle().value
            // 태블릿: 같은 화면 안에서 차단 ↔ 재생이 바뀐다. 차단 중에는 멈춘다
            LaunchedEffect(state.restricted) { updatePlayback(state.restricted) }
            IviTheme {
                Box(
                    Modifier
                        .fillMaxSize()
                        .background(IviColors.Background)
                        .semantics { testTagsAsResourceId = true },
                ) {
                    val p = player
                    when {
                        state.restricted -> Blocked { finish() }
                        p != null -> DrivePlayer(p) { finish() }
                        else -> FakePlayer { finish() }
                    }
                }
            }
        }
    }

    // AAOS: OS 가 막으면 이 화면은 onStop 을 받고, 풀리면 onStart 로 돌아온다
    override fun onStart() {
        super.onStart()
        started = true
        updatePlayback((application as IviApp).vehicle.state.value.restricted)
    }

    override fun onResume() {
        super.onResume()
        hideCarNavigationBar()
    }

    override fun onStop() {
        started = false
        player?.playWhenReady = false
        super.onStop()
    }

    override fun onDestroy() {
        player?.release()
        player = null
        super.onDestroy()
    }

    private fun updatePlayback(restricted: Boolean) {
        player?.playWhenReady = started && !restricted
    }

    private fun driveClips(): List<java.io.File> =
        getExternalFilesDir("drive")
            ?.listFiles { f -> f.isFile && f.extension.equals("mp4", ignoreCase = true) }
            ?.sortedBy { it.name }
            .orEmpty()
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

/** 기기에 올린 블랙박스 영상을 재생한다. 영상 면은 16:9 로 맞추고 둥근 모서리로 자른다. */
@Composable
private fun DrivePlayer(player: ExoPlayer, onClose: () -> Unit) {
    var position by remember { mutableLongStateOf(0L) }
    var duration by remember { mutableLongStateOf(0L) }
    var index by remember { mutableIntStateOf(0) }
    LaunchedEffect(player) {
        while (true) {
            position = player.currentPosition
            duration = player.duration.takeIf { it != C.TIME_UNSET } ?: 0L
            index = player.currentMediaItemIndex
            delay(250)
        }
    }
    val count = player.mediaItemCount
    PlayerFrame(
        title = "주행 영상",
        subtitle = if (count > 1) "${index + 1} / $count" else null,
        elapsedSeconds = (position / 1000).toInt(),
        lengthSeconds = (duration / 1000).toInt(),
        onNext = if (count > 1) ({ player.seekToNextMediaItem() }) else null,
        onClose = onClose,
    ) {
        AndroidView(
            factory = { context ->
                (LayoutInflater.from(context).inflate(R.layout.drive_player, null) as PlayerView).also { it.player = player }
            },
            onRelease = { it.player = null },
            modifier = Modifier.fillMaxSize().testTag("video_surface"),
        )
    }
}

/** 영상 파일이 없을 때: 그라데이션 화면에 재생 시간만 흐른다. */
@Composable
private fun FakePlayer(onClose: () -> Unit) {
    var seconds by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            seconds++
        }
    }
    val length = 3 * 60 + 24
    PlayerFrame(
        title = "Coastal Road — 주행 영상",
        subtitle = null,
        elapsedSeconds = seconds % length,
        lengthSeconds = length,
        onNext = null,
        onClose = onClose,
    ) {
        Box(
            Modifier.fillMaxSize().background(Brush.linearGradient(listOf(IviColors.AquaDeep, IviColors.Background))),
            contentAlignment = Alignment.Center,
        ) {
            Text("▶  영상 재생 중", fontSize = 30.sp, fontWeight = FontWeight.Light)
        }
    }
}

@Composable
private fun PlayerFrame(
    title: String,
    subtitle: String?,
    elapsedSeconds: Int,
    lengthSeconds: Int,
    onNext: (() -> Unit)?,
    onClose: () -> Unit,
    video: @Composable () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(24.dp).testTag("video_player"), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(title, fontSize = 20.sp, fontWeight = FontWeight.Medium)
            if (subtitle != null) Text(subtitle, Modifier.testTag("video_index"), color = IviColors.TextSecondary, fontSize = 16.sp)
            Spacer(Modifier.weight(1f))
            if (onNext != null) {
                Button(
                    onClick = onNext,
                    modifier = Modifier.testTag("video_next").height(56.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = IviColors.SurfaceHigh, contentColor = IviColors.TextPrimary),
                ) { Text("다음 영상", fontSize = 18.sp) }
            }
            CloseButton(onClose)
        }
        // 남는 자리 안에서 16:9 를 가장 크게: 영상과 둥근 테두리가 딱 맞아 위아래·좌우 띠가 생기지 않는다
        Box(Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) {
            Box(
                Modifier
                    .aspectRatio(16f / 9f)
                    .clip(RoundedCornerShape(20.dp))
                    .background(IviColors.Surface),
            ) { video() }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(clock(elapsedSeconds), Modifier.testTag("video_elapsed"), fontSize = 18.sp)
            Box(
                Modifier
                    .weight(1f)
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(IviColors.Line),
            ) {
                val fraction = if (lengthSeconds > 0) (elapsedSeconds.toFloat() / lengthSeconds).coerceIn(0f, 1f) else 0f
                Box(
                    Modifier
                        .fillMaxWidth(fraction)
                        .fillMaxHeight()
                        .background(IviColors.Aqua),
                )
            }
            Text(clock(lengthSeconds), color = IviColors.TextSecondary, fontSize = 18.sp)
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
