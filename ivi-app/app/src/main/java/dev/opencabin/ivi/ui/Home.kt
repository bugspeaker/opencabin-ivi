package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
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
import dev.opencabin.ivi.state.Settings
import dev.opencabin.ivi.state.Stations
import dev.opencabin.ivi.state.Tracks
import dev.opencabin.ivi.vehicle.VehicleState

/*
 * 홈 = 내비게이션. 분할 화면이면 오른쪽에 지금 오디오(블루투스 음악 또는 라디오) 카드를 같이 보여 준다.
 * 지도 오른쪽 위 버튼(split_toggle)으로 단일 ↔ 분할을 바꾼다.
 */
@Composable
fun HomeScreen(state: VehicleState, settings: Settings, cabin: CabinController, cockpit: CockpitState) {
    Row(Modifier.fillMaxSize().padding(bottom = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        NavigationPane(state, cabin, cockpit, Modifier.weight(if (cockpit.split) 1.2f else 1f).fillMaxHeight())
        if (cockpit.split) AudioCard(settings, cabin, cockpit, Modifier.weight(0.8f).fillMaxHeight())
    }
}

@Composable
private fun AudioCard(settings: Settings, cabin: CabinController, cockpit: CockpitState, modifier: Modifier) {
    val radio = cabin.audioSource == AudioSource.RADIO
    Panel(
        modifier.testTag("home_audio").clickable { cockpit.open(if (radio) Tab.RADIO else Tab.MEDIA) },
        padding = 16.dp,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            AppTile(if (radio) TileColors.Radio else TileColors.Media, 30.dp) { Glyph(if (radio) G.RADIO else G.MUSIC, Color.White, it) }
            Text(if (radio) "라디오" else "블루투스 오디오", fontSize = 15.sp, fontWeight = FontWeight.Medium)
        }
        if (radio) {
            val station = Stations.firstOrNull { it.band == settings.band && it.freq == settings.freq }
            Box(
                Modifier.fillMaxWidth(0.5f).aspectRatio(1f).clip(RoundedCornerShape(16.dp)).background(Brush.linearGradient(TileColors.Radio)),
                contentAlignment = Alignment.Center,
            ) { Glyph(G.RADIO, Color.White, Modifier.fillMaxSize(0.4f)) }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(station?.name ?: settings.band.format(settings.freq), Modifier.testTag("home_media_title"), fontSize = 21.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Text("${settings.band.format(settings.freq)} · ${cabin.playbackLabel(AudioSource.RADIO)}", color = IviColors.TextSecondary, fontSize = 14.sp)
            }
            Spacer(Modifier.height(4.dp))
            Controls(playing = cabin.radioOn, prefix = "home_", onPrev = { cabin.seek(-1) }, onToggle = { cabin.setRadio(!cabin.radioOn) }, onNext = { cabin.seek(1) })
        } else {
            val (title, artist) = Tracks[cabin.mediaTrack]
            AlbumArt(cabin.mediaTrack, Modifier.fillMaxWidth(0.5f))
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(title, Modifier.testTag("home_media_title"), fontSize = 21.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("$artist · ${cabin.playbackLabel(AudioSource.MEDIA)}", color = IviColors.TextSecondary, fontSize = 14.sp)
            }
            ProgressRow(cabin.mediaTrack)
            Controls(playing = cabin.mediaPlaying, prefix = "home_", onPrev = { cabin.previousTrack() }, onToggle = { cabin.toggleMedia() }, onNext = { cabin.nextTrack() })
        }
    }
}

/** 재생 위치 (가짜 미디어라 곡마다 고정 위치). */
@Composable
fun ProgressRow(track: Int) {
    Column(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)).background(IviColors.Line)) {
            Box(Modifier.fillMaxWidth(0.25f + track * 0.12f).fillMaxHeight().background(IviColors.TextSecondary))
        }
        Row(Modifier.fillMaxWidth().padding(top = 4.dp)) {
            Text("1:${12 + track * 7}", color = IviColors.TextSecondary, fontSize = 12.sp)
            Spacer(Modifier.weight(1f))
            Text("3:4$track", color = IviColors.TextSecondary, fontSize = 12.sp)
        }
    }
}

/** 이전 · 재생/일시 정지 · 다음. prefix 로 홈 카드("home_")와 미디어 화면("")의 태그를 나눈다. */
@Composable
fun Controls(playing: Boolean, prefix: String, onPrev: () -> Unit, onToggle: () -> Unit, onNext: () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(18.dp)) {
        RoundIconButton("${prefix}prev", 54.dp, background = Color.Transparent, onClick = onPrev) { Glyph(G.PREV, IviColors.TextPrimary, it) }
        Box(
            Modifier.testTag("${prefix}play_pause").size(68.dp).clip(CircleShape).background(IviColors.TextPrimary).clickable(onClick = onToggle),
            contentAlignment = Alignment.Center,
        ) { Glyph(if (playing) G.PAUSE else G.PLAY, IviColors.Background, Modifier.size(26.dp)) }
        RoundIconButton("${prefix}next", 54.dp, background = Color.Transparent, onClick = onNext) { Glyph(G.NEXT, IviColors.TextPrimary, it) }
    }
}

@Composable
fun AlbumArt(index: Int, modifier: Modifier) {
    val palettes = listOf(
        listOf(Color(0xFF1B3A5C), Color(0xFF4BA3FF)),
        listOf(Color(0xFF3A1B5C), Color(0xFFA35BFF)),
        listOf(Color(0xFF14343A), Color(0xFF3DD68C)),
        listOf(Color(0xFF4A2A14), Color(0xFFFFB547)),
        listOf(Color(0xFF2A1430), Color(0xFFFF6A8B)),
    )
    Box(
        modifier.aspectRatio(1f).clip(RoundedCornerShape(16.dp)).background(Brush.linearGradient(palettes[index % palettes.size])),
        contentAlignment = Alignment.Center,
    ) { Glyph(G.MUSIC, Color.White.copy(alpha = 0.85f), Modifier.fillMaxSize(0.36f)) }
}
