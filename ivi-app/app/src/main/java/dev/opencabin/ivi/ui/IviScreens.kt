package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.vehicle.Gear
import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState
import java.util.Locale

private val Accent = Color(0xFF4FC3F7)
private val Warn = Color(0xFFFFB74D)
private val Panel = Color(0xFF1B2128)
private val Muted = Color(0xFF8A96A3)

private val OnDark = Color(0xFFE8EDF2)

@Composable
fun IviTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = darkColorScheme(primary = Accent, background = Color(0xFF101418), onBackground = OnDark)) {
        // Surface 없이 그리는 Text 는 기본 글자색이 검정이라 어두운 배경에서 안 보인다 (에뮬레이터에서 속도 숫자가 안 보였음)
        CompositionLocalProvider(LocalContentColor provides OnDark, content = content)
    }
}

/**
 * 테스트 태그는 Appium 에서 resource-id 로 보이게 한다 (testTagsAsResourceId).
 * 태그 이름은 ivi-tests/screens.py 와 맞춘다.
 */
@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun IviRoot(
    source: String,
    state: VehicleState,
    onSetTemperature: (Seat, Float) -> Unit,
    onOpenVideo: () -> Unit,
) {
    var tab by rememberSaveable { mutableStateOf(Tab.HOME) }
    Row(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .semantics { testTagsAsResourceId = true },
    ) {
        NavRail(tab) { tab = it }
        Column(Modifier.fillMaxSize().padding(24.dp)) {
            StatusBar(source, state)
            Spacer(Modifier.height(20.dp))
            when (tab) {
                Tab.HOME -> HomeScreen(state)
                Tab.CLIMATE -> ClimateScreen(state, onSetTemperature)
                Tab.MEDIA -> MediaScreen(state, onOpenVideo)
            }
        }
    }
}

enum class Tab(val label: String, val tag: String) {
    HOME("홈", "nav_home"), CLIMATE("공조", "nav_climate"), MEDIA("미디어", "nav_media")
}

@Composable
private fun NavRail(selected: Tab, onSelect: (Tab) -> Unit) {
    Column(
        Modifier.fillMaxHeight().width(120.dp).background(Panel).padding(vertical = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("OpenCabin", color = Accent, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(12.dp))
        Tab.entries.forEach { tab ->
            val on = tab == selected
            Box(
                Modifier
                    .testTag(tab.tag)
                    .width(96.dp)
                    .height(64.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(if (on) Accent.copy(alpha = 0.2f) else Color.Transparent)
                    .clickable { onSelect(tab) },
                contentAlignment = Alignment.Center,
            ) {
                Text(tab.label, color = if (on) Accent else Color.White, fontSize = 20.sp)
            }
        }
    }
}

@Composable
private fun StatusBar(source: String, state: VehicleState) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Chip(source, Accent, Modifier.testTag("source_badge"))
        if (!state.connected) Chip("차량 연결 안 됨", Warn, Modifier.testTag("vehicle_disconnected"))
        if (state.restricted) Chip("주행 중 · 일부 기능 제한", Warn, Modifier.testTag("restriction_banner"))
        state.error?.let { Chip(it, Warn, Modifier.testTag("vehicle_error")) }
    }
}

@Composable
private fun Chip(text: String, color: Color, modifier: Modifier = Modifier) {
    Text(
        text,
        modifier = modifier.clip(RoundedCornerShape(50)).background(color.copy(alpha = 0.18f)).padding(horizontal = 14.dp, vertical = 6.dp),
        color = color,
        fontSize = 16.sp,
    )
}

// ---------------- 홈 ----------------

@Composable
private fun HomeScreen(state: VehicleState) {
    Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        Card(Modifier.weight(1f)) {
            Label("속도")
            Row(verticalAlignment = Alignment.Bottom) {
                Text(String.format(Locale.US, "%.0f", state.speedKmh), Modifier.testTag("speed_value"), fontSize = 72.sp, fontWeight = FontWeight.Bold)
                Text(" km/h", color = Muted, fontSize = 22.sp, modifier = Modifier.padding(bottom = 14.dp))
            }
            Spacer(Modifier.height(12.dp))
            Label("기어")
            GearRow(state.gear)
        }
        Card(Modifier.weight(1f)) {
            Label("공조")
            Text("운전석 ${tempText(state.driverTempC)}", Modifier.testTag("home_driver_temp"), fontSize = 28.sp)
            Text("조수석 ${tempText(state.passengerTempC)}", Modifier.testTag("home_passenger_temp"), fontSize = 28.sp)
        }
    }
}

@Composable
private fun GearRow(current: Gear) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
        listOf(Gear.PARK, Gear.REVERSE, Gear.NEUTRAL, Gear.DRIVE).forEach { gear ->
            val on = gear == current
            Text(
                gear.label,
                fontSize = 32.sp,
                fontWeight = if (on) FontWeight.Bold else FontWeight.Normal,
                color = if (on) Accent else Muted,
            )
        }
        // 테스트는 강조 색 대신 이 값을 읽는다
        Text(current.label, Modifier.testTag("gear_value").padding(start = 12.dp), color = Muted, fontSize = 14.sp)
    }
}

// ---------------- 공조 ----------------

@Composable
private fun ClimateScreen(state: VehicleState, onSetTemperature: (Seat, Float) -> Unit) {
    if (!state.hvacAvailable) {
        Card(Modifier.fillMaxWidth().testTag("hvac_unavailable")) {
            Text("공조를 제어할 수 없습니다", fontSize = 24.sp)
            Text("AAOS 에서는 CONTROL_CAR_CLIMATE 권한(시스템 앱)이 필요합니다.", color = Muted)
        }
        return
    }
    Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        SeatPanel("운전석", Seat.DRIVER, state.driverTempC, onSetTemperature, Modifier.weight(1f))
        SeatPanel("조수석", Seat.PASSENGER, state.passengerTempC, onSetTemperature, Modifier.weight(1f))
    }
}

@Composable
private fun SeatPanel(title: String, seat: Seat, celsius: Float?, onSet: (Seat, Float) -> Unit, modifier: Modifier) {
    Card(modifier) {
        Label(title)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            StepButton("−", "${seat.tag}_temp_down", celsius != null && celsius > HvacSpec.MIN_C) {
                onSet(seat, celsius!! - HvacSpec.STEP_C)
            }
            Text(tempText(celsius), Modifier.testTag("${seat.tag}_temp_value").width(150.dp), fontSize = 40.sp, fontWeight = FontWeight.Bold)
            StepButton("+", "${seat.tag}_temp_up", celsius != null && celsius < HvacSpec.MAX_C) {
                onSet(seat, celsius!! + HvacSpec.STEP_C)
            }
        }
        Text("${HvacSpec.MIN_C.toInt()} ~ ${HvacSpec.MAX_C.toInt()}°C, ${HvacSpec.STEP_C}°C 단위", color = Muted, fontSize = 14.sp)
    }
}

@Composable
private fun StepButton(text: String, tag: String, enabled: Boolean, onClick: () -> Unit) {
    // 차량용 터치 영역: 최소 76dp (1단계에서 겹침 결함을 본 SystemUI 버튼과 같은 크기)
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.testTag(tag).size(76.dp), shape = RoundedCornerShape(16.dp)) {
        Text(text, fontSize = 28.sp)
    }
}

// ---------------- 미디어 ----------------

private val Tracks = listOf("Night Drive", "Coastal Road", "City Lights", "Morning Commute", "Long Way Home")

@Composable
private fun MediaScreen(state: VehicleState, onOpenVideo: () -> Unit) {
    var current by rememberSaveable { mutableIntStateOf(0) }
    var playing by rememberSaveable { mutableStateOf(false) }
    Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        Card(Modifier.weight(1f)) {
            Label("재생 목록")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                itemsIndexed(Tracks) { index, title ->
                    Text(
                        title,
                        Modifier
                            .testTag("track_$index")
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (index == current) Accent.copy(alpha = 0.15f) else Color.Transparent)
                            .clickable { current = index; playing = true }
                            .padding(12.dp),
                        fontSize = 20.sp,
                    )
                }
            }
        }
        Card(Modifier.weight(1f)) {
            Label("지금 재생")
            Text(Tracks[current], Modifier.testTag("now_playing_title"), fontSize = 28.sp, fontWeight = FontWeight.Bold)
            Text(if (playing) "재생 중" else "일시 정지", Modifier.testTag("playback_state"), color = Muted)
            Button(onClick = { playing = !playing }, modifier = Modifier.testTag("play_pause").height(64.dp)) {
                Text(if (playing) "일시 정지" else "재생", fontSize = 20.sp)
            }
            Spacer(Modifier.height(16.dp))
            Label("영상")
            Button(
                onClick = onOpenVideo,
                enabled = !state.restricted,
                modifier = Modifier.testTag("open_video").height(64.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Accent),
            ) { Text("영상 보기", fontSize = 20.sp) }
            if (state.restricted) {
                Text("주행 중에는 영상을 볼 수 없습니다", Modifier.testTag("video_restricted_notice"), color = Warn)
            }
        }
    }
}

// ---------------- 공통 ----------------

@Composable
fun Card(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(20.dp)).background(Panel).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) { content() }
}

@Composable
private fun Label(text: String) = Text(text, color = Muted, fontSize = 16.sp)

fun tempText(celsius: Float?) = celsius?.let { String.format(Locale.US, "%.1f°C", it) } ?: "--"
