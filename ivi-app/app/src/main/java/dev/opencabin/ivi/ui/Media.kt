package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.AudioSource
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Tracks
import dev.opencabin.ivi.vehicle.UxRules
import dev.opencabin.ivi.vehicle.VehicleState

/** 미디어(블루투스 음악, 가상): 곡 목록 · 지금 재생 · 영상. 라디오를 켜면 일시 정지된다 (오디오 소스는 하나). */
@Composable
fun MediaScreen(state: VehicleState, cabin: CabinController, onOpenVideo: () -> Unit) {
    Row(Modifier.fillMaxSize().padding(bottom = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Panel(Modifier.weight(1f).fillMaxHeight(), padding = 16.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AppTile(TileColors.Media, 30.dp) { Glyph(G.MUSIC, Color.White, it) }
                Text("재생 목록", fontSize = 16.sp, fontWeight = FontWeight.Medium)
            }
            LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                itemsIndexed(Tracks) { index, (title, artist) ->
                    val on = index == cabin.mediaTrack
                    Row(
                        Modifier
                            .testTag("track_$index")
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (on) IviColors.Accent.copy(alpha = 0.16f) else Color.Transparent)
                            .clickable { cabin.playMedia(index) }
                            .padding(horizontal = 10.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        AlbumArt(index, Modifier.size(40.dp))
                        Column(Modifier.weight(1f)) {
                            Text(title, Modifier.testTag("track_${index}_title"), fontSize = 16.sp, color = if (on) IviColors.AccentSoft else IviColors.TextPrimary, maxLines = 1)
                            Text(artist, fontSize = 13.sp, color = IviColors.TextSecondary)
                        }
                    }
                }
            }
        }
        Panel(Modifier.weight(1f).fillMaxHeight(), padding = 16.dp, verticalArrangement = Arrangement.SpaceBetween, horizontalAlignment = Alignment.CenterHorizontally) {
            val (title, artist) = Tracks[cabin.mediaTrack]
            AlbumArt(cabin.mediaTrack, Modifier.fillMaxWidth(0.38f))
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(title, Modifier.testTag("now_playing_title"), fontSize = 22.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(artist, color = IviColors.TextSecondary, fontSize = 14.sp)
                Text(cabin.playbackLabel(AudioSource.MEDIA), Modifier.testTag("playback_state"), color = IviColors.AccentSoft, fontSize = 14.sp)
            }
            ProgressRow(cabin.mediaTrack)
            Controls(playing = cabin.mediaPlaying, prefix = "", onPrev = { cabin.previousTrack() }, onToggle = { cabin.toggleMedia() }, onNext = { cabin.nextTrack() })
            Button(
                onClick = onOpenVideo,
                enabled = !state.blocks(UxRules.NO_VIDEO),
                modifier = Modifier.testTag("open_video").height(46.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = IviColors.SurfaceHigh,
                    contentColor = IviColors.TextPrimary,
                    disabledContainerColor = IviColors.SurfaceHigh.copy(alpha = 0.5f),
                    disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.5f),
                ),
            ) {
                Glyph(G.VIDEO, if (state.blocks(UxRules.NO_VIDEO)) IviColors.TextTertiary else IviColors.TextPrimary, Modifier.size(20.dp))
                Text("  영상 보기", fontSize = 15.sp)
            }
            if (state.blocks(UxRules.NO_VIDEO)) {
                // D 기어로 멈춰 있을 때도 영상은 막힌다 (플랫폼 UX 제한 idling = NO_VIDEO)
                Text(if (state.moving) "주행 중에는 영상을 볼 수 없습니다" else "P 기어에서만 영상을 볼 수 있습니다", Modifier.testTag("video_restricted_notice"), color = IviColors.Warn, fontSize = 13.sp)
            }
        }
    }
}
