package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.AudioSource
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Tracks
import dev.opencabin.ivi.vehicle.VehicleState

/** 미디어(USB 음악, 가상): 곡 목록 · 지금 재생 · 영상. 라디오를 켜면 일시 정지된다 (오디오 소스는 하나). */
@Composable
fun MediaScreen(state: VehicleState, cabin: CabinController, onOpenVideo: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Label("USB 음악")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                itemsIndexed(Tracks) { index, (title, artist) ->
                    val on = index == cabin.mediaTrack
                    Row(
                        Modifier
                            .testTag("track_$index")
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (on) IviColors.Aqua.copy(alpha = 0.14f) else Color.Transparent)
                            .clickable { cabin.playMedia(index) }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(title, Modifier.weight(1f).testTag("track_${index}_title"), fontSize = 17.sp, color = if (on) IviColors.Aqua else IviColors.TextPrimary)
                        Text(artist, fontSize = 13.sp, color = IviColors.TextSecondary)
                    }
                }
            }
        }
        Panel(Modifier.weight(1f).fillMaxHeight(), verticalArrangement = Arrangement.SpaceBetween) {
            val (title, artist) = Tracks[cabin.mediaTrack]
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                AlbumArt(cabin.mediaTrack, Modifier.size(72.dp))
                Column {
                    Text(title, Modifier.testTag("now_playing_title"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(artist, color = IviColors.TextSecondary, fontSize = 14.sp)
                    Text(cabin.playbackLabel(AudioSource.MEDIA), Modifier.testTag("playback_state"), color = IviColors.Aqua, fontSize = 14.sp)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                RoundButton(if (cabin.mediaPlaying) "❚❚" else "▶", "play_pause", filled = true) { cabin.toggleMedia() }
                PillButton("영상 보기", "open_video", enabled = !state.restricted, onClick = onOpenVideo)
            }
            if (state.restricted) {
                Text("주행 중에는 영상을 볼 수 없습니다", Modifier.testTag("video_restricted_notice"), color = IviColors.Warn, fontSize = 14.sp)
            }
        }
    }
}

@Composable
fun AlbumArt(index: Int, modifier: Modifier) {
    val palettes = listOf(
        listOf(Color(0xFF1B3A5C), IviColors.Aqua),
        listOf(Color(0xFF3A1B5C), Color(0xFF6C8CFF)),
        listOf(Color(0xFF14343A), Color(0xFF5CE0B0)),
        listOf(Color(0xFF4A2A14), Color(0xFFFFB547)),
        listOf(Color(0xFF2A1430), Color(0xFFFF7A9A)),
    )
    Box(
        modifier.aspectRatio(1f).clip(RoundedCornerShape(14.dp)).background(Brush.linearGradient(palettes[index % palettes.size])),
        contentAlignment = Alignment.Center,
    ) { Text("♪", fontSize = 26.sp, color = Color.White.copy(alpha = 0.85f)) }
}
