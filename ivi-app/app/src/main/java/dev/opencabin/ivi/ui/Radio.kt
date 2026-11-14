package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.AudioSource
import dev.opencabin.ivi.state.Band
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Settings
import dev.opencabin.ivi.state.Stations

/**
 * 라디오 (가상 방송): FM/AM, 미세 조정(tune), 방송국 찾기(seek), 프리셋 6개.
 * 대역·주파수·프리셋은 저장 설정이라 앱을 다시 켜도 남는다. 켜면 미디어가 일시 정지된다.
 */
@Composable
fun RadioScreen(settings: Settings, cabin: CabinController) {
    var saving by remember { mutableStateOf(false) }
    val station = Stations.firstOrNull { it.band == settings.band && it.freq == settings.freq }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(1.1f).fillMaxHeight(), verticalArrangement = Arrangement.SpaceBetween) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PillButton("FM", "radio_band_fm", selected = settings.band == Band.FM) { cabin.setBand(Band.FM) }
                PillButton("AM", "radio_band_am", selected = settings.band == Band.AM) { cabin.setBand(Band.AM) }
            }
            Column {
                Text(settings.band.format(settings.freq), Modifier.testTag("radio_freq"), fontSize = 48.sp, fontWeight = FontWeight.Light)
                Text(station?.name ?: "방송 없음", Modifier.testTag("radio_station"), fontSize = 20.sp, color = if (station != null) IviColors.Aqua else IviColors.TextSecondary)
                Text(cabin.playbackLabel(AudioSource.RADIO), Modifier.testTag("radio_state"), color = IviColors.TextSecondary, fontSize = 15.sp)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                RoundButton("⏮", "radio_seek_down", size = 56.dp) { cabin.seek(-1) }
                RoundButton("−", "radio_tune_down", size = 56.dp) { cabin.tune(-1) }
                RoundButton(if (cabin.radioOn) "■" else "▶", "radio_power", filled = cabin.radioOn) { cabin.setRadio(!cabin.radioOn) }
                RoundButton("+", "radio_tune_up", size = 56.dp) { cabin.tune(1) }
                RoundButton("⏭", "radio_seek_up", size = 56.dp) { cabin.seek(1) }
            }
        }
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Label("프리셋", Modifier.weight(1f))
                PillButton(if (saving) "취소" else "현재 주파수 저장", "radio_save", selected = saving) { saving = !saving }
            }
            if (saving) Text("저장할 칸을 누르세요", Modifier.testTag("radio_save_hint"), color = IviColors.Warn, fontSize = 14.sp)
            settings.presets.chunked(2).forEachIndexed { row, pair ->
                Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    pair.forEachIndexed { col, freq ->
                        val slot = row * 2 + col
                        val on = freq == settings.freq
                        Column(
                            Modifier
                                .testTag("radio_preset_$slot")
                                .weight(1f)
                                .fillMaxHeight()
                                .clip(RoundedCornerShape(14.dp))
                                .background(if (on) IviColors.Aqua.copy(alpha = 0.16f) else IviColors.SurfaceHigh)
                                .border(1.dp, if (saving) IviColors.Warn else Color.Transparent, RoundedCornerShape(14.dp))
                                .clickable {
                                    if (saving) {
                                        cabin.savePreset(slot)
                                        saving = false
                                    } else {
                                        cabin.recallPreset(slot)
                                    }
                                }
                                .padding(horizontal = 12.dp),
                            verticalArrangement = Arrangement.Center,
                        ) {
                            Text(settings.band.format(freq), Modifier.testTag("radio_preset_${slot}_freq"), fontSize = 16.sp,
                                color = if (on) IviColors.Aqua else IviColors.TextPrimary)
                            Text(Stations.firstOrNull { it.band == settings.band && it.freq == freq }?.name ?: "", fontSize = 12.sp,
                                color = IviColors.TextSecondary, modifier = Modifier.height(16.dp))
                        }
                    }
                }
            }
        }
    }
}
