package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import java.util.Locale

/** 홈: 내비 · 오디오 · 공조 · 전화 카드 (위젯). 카드를 누르면 그 앱으로 간다. */
@Composable
fun HomeScreen(state: VehicleState, settings: Settings, cabin: CabinController, onOpen: (Tab) -> Unit) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Row(Modifier.fillMaxWidth().weight(1.15f), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Panel(Modifier.weight(1.2f).fillMaxHeight().clickable { onOpen(Tab.NAVI) }) {
                Label("내비게이션")
                val dest = cabin.destination
                val summary = when {
                    cabin.guiding && dest != null -> "${dest.name}까지 ${String.format(Locale.US, "%.1f", cabin.remainingKm)} km"
                    cabin.arrived -> "목적지에 도착했습니다"
                    else -> "목적지를 설정하세요"
                }
                Text(summary, Modifier.testTag("home_nav_summary"), fontSize = 20.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                MiniMap(Modifier.fillMaxWidth().weight(1f), cabin.guiding)
            }
            Panel(Modifier.weight(1f).fillMaxHeight().clickable { onOpen(if (cabin.radioOn) Tab.RADIO else Tab.MEDIA) }) {
                val radio = cabin.audioSource == AudioSource.RADIO
                Label(if (radio) "라디오" else "미디어")
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    AlbumArt(if (radio) 4 else cabin.mediaTrack, Modifier.size(64.dp))
                    Column {
                        val title = if (radio) Stations.firstOrNull { it.band == settings.band && it.freq == settings.freq }?.name
                            ?: settings.band.format(settings.freq) else Tracks[cabin.mediaTrack].first
                        Text(title, Modifier.testTag("home_media_title"), fontSize = 20.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            cabin.playbackLabel(if (radio) AudioSource.RADIO else AudioSource.MEDIA),
                            color = IviColors.TextSecondary, fontSize = 15.sp,
                        )
                    }
                }
            }
        }
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Panel(Modifier.weight(1f).fillMaxHeight().clickable { onOpen(Tab.CLIMATE) }) {
                Label("공조")
                Text("운전석 ${tempText(state.driverTempC)}", Modifier.testTag("home_driver_temp"), fontSize = 20.sp)
                Text("조수석 ${tempText(state.passengerTempC)}", Modifier.testTag("home_passenger_temp"), fontSize = 20.sp)
            }
            Panel(Modifier.weight(1f).fillMaxHeight().clickable { onOpen(Tab.PHONE) }) {
                Label("전화")
                Text("내 휴대폰 연결됨", fontSize = 20.sp, color = IviColors.Aqua)
                cabin.recents.firstOrNull()?.let { Text("최근: ${it.name} (${it.kind})", color = IviColors.TextSecondary, fontSize = 15.sp) }
            }
        }
    }
}

/** 홈 카드용 작은 지도 그림 (실제 지도 데이터가 아니다). */
@Composable
fun MiniMap(modifier: Modifier, guiding: Boolean) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        drawRect(IviColors.Map)
        val road = 6.dp.toPx()
        listOf(0.3f, 0.7f).forEach { drawLine(IviColors.Road, androidx.compose.ui.geometry.Offset(0f, h * it), androidx.compose.ui.geometry.Offset(w, h * it), road) }
        listOf(0.25f, 0.6f, 0.85f).forEach { drawLine(IviColors.Road, androidx.compose.ui.geometry.Offset(w * it, 0f), androidx.compose.ui.geometry.Offset(w * it, h), road) }
        if (guiding) {
            val route = androidx.compose.ui.graphics.Path().apply {
                moveTo(w * 0.25f, h); lineTo(w * 0.25f, h * 0.7f); lineTo(w * 0.6f, h * 0.7f); lineTo(w * 0.6f, h * 0.3f); lineTo(w * 0.85f, h * 0.3f)
            }
            drawPath(route, IviColors.Aqua, style = androidx.compose.ui.graphics.drawscope.Stroke(road))
        }
        drawCircle(IviColors.Aqua, radius = 7.dp.toPx(), center = androidx.compose.ui.geometry.Offset(w * 0.25f, h * 0.85f))
    }
}
