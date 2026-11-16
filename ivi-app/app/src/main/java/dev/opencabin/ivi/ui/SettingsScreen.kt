package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.BuildConfig
import dev.opencabin.ivi.state.AmbientColors
import dev.opencabin.ivi.state.Settings
import dev.opencabin.ivi.state.SettingsStore

/** 설정: 소리 · 화면 · 차량 · 시스템. 모두 저장되어 앱을 다시 켜도 남는다. */
@Composable
fun SettingsScreen(settings: Settings, store: SettingsStore) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Label("소리 · 화면")
            StepperRow("볼륨", "settings_volume", settings.volume.toString(),
                canDecrease = settings.volume > 0, canIncrease = settings.volume < Settings.VOLUME_MAX,
                onDecrease = { store.update { it.copy(volume = it.volume - 1) } },
                onIncrease = { store.update { it.copy(volume = it.volume + 1) } })
            StepperRow("밝기", "settings_brightness", settings.brightness.toString(),
                canDecrease = settings.brightness > 1, canIncrease = settings.brightness < Settings.BRIGHTNESS_MAX,
                onDecrease = { store.update { it.copy(brightness = it.brightness - 1) } },
                onIncrease = { store.update { it.copy(brightness = it.brightness + 1) } })
            ToggleRow("24시간 시계", "settings_clock24", settings.clock24) { on -> store.update { it.copy(clock24 = on) } }
            Label("시스템")
            InfoRow("계정", DRIVER_NAME, "settings_account")
            InfoRow("블루투스", "내 휴대폰 · 연결됨", "settings_bluetooth")
            InfoRow("소프트웨어", BuildConfig.VERSION_NAME, "settings_version")
        }
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Label("차량")
            ToggleRow("속도 단위 mph", "settings_unit_mph", settings.mph) { on -> store.update { it.copy(mph = on) } }
            ToggleRow("도어 자동 잠금", "settings_autolock", settings.autoLock) { on -> store.update { it.copy(autoLock = on) } }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("무드등", fontSize = 17.sp, modifier = Modifier.weight(1f))
                Text(AmbientColors[settings.ambient], Modifier.testTag("settings_ambient_value"), fontSize = 15.sp, color = IviColors.TextSecondary)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                AmbientPalette.forEachIndexed { index, color ->
                    Swatch(color, index == settings.ambient, "settings_ambient_$index") { store.update { it.copy(ambient = index) } }
                }
            }
            Box(Modifier.weight(1f))
            PillButton("설정 초기화", "settings_reset", Modifier.fillMaxWidth()) { store.reset() }
        }
    }
}

/** 읽기 전용 한 줄: 이름은 왼쪽, 값은 오른쪽 (무드등 줄과 같은 모양). */
@Composable
private fun InfoRow(label: String, value: String, tag: String) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 17.sp, modifier = Modifier.weight(1f))
        Text(value, Modifier.testTag(tag), fontSize = 15.sp, color = IviColors.TextSecondary)
    }
}

@Composable
private fun Swatch(color: Color, selected: Boolean, tag: String, onClick: () -> Unit) {
    Box(
        Modifier
            .testTag(tag)
            .size(52.dp)
            .clip(CircleShape)
            .border(3.dp, if (selected) IviColors.TextPrimary else Color.Transparent, CircleShape)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.size(36.dp).clip(CircleShape).background(color))
    }
}
