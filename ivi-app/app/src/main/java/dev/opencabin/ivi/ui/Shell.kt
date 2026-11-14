package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.AmbientColors
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Settings
import dev.opencabin.ivi.state.SettingsStore
import dev.opencabin.ivi.state.VoiceCommands
import dev.opencabin.ivi.vehicle.Gear
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.roundToInt

/*
 * 화면 틀 (Pleos Connect 화면 구조 참고, docs/phase5-design.md):
 *   위 상태 줄 | 왼쪽 주행 정보(항상 보임) + 오른쪽 앱 영역 | 아래 앱 바
 *   그 위에 겹치는 것: 통화 화면, 음성 패널, 후방 카메라(기어 R), 밝기
 * 테스트 태그는 Appium 에서 resource-id 로 보인다 (testTagsAsResourceId). 이름은 ivi-tests/ivi/screens.py 와 맞춘다.
 */

enum class Tab(val label: String, val glyph: String, val tag: String) {
    HOME("홈", "⌂", "nav_home"),
    NAVI("내비", "➤", "nav_navi"),
    RADIO("라디오", "≋", "nav_radio"),
    MEDIA("미디어", "♪", "nav_media"),
    PHONE("전화", "✆", "nav_phone"),
    CLIMATE("공조", "✻", "nav_climate"),
    SETTINGS("설정", "☰", "nav_settings"),
}

val AmbientPalette = listOf(IviColors.Aqua, Color(0xFFE8F0F5), IviColors.Warn, Color(0xFF9B7BFF), IviColors.Ok)

/** 속도 표시: 설정의 단위(km/h·mph)로 바꾼다. */
fun speedDisplay(kmh: Float, mph: Boolean) =
    if (mph) (kmh * 0.621371f).roundToInt().toString() to "mph" else kmh.roundToInt().toString() to "km/h"

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun IviRoot(
    source: String,
    state: VehicleState,
    settings: Settings,
    store: SettingsStore,
    cabin: CabinController,
    onSetTemperature: (Seat, Float) -> Unit,
    onOpenVideo: () -> Unit,
) {
    var tab by rememberSaveable { mutableStateOf(Tab.HOME) }
    var voiceOpen by rememberSaveable { mutableStateOf(false) }
    val speed by rememberUpdatedState(state.speedKmh)

    // 음성 결과 알림은 5초 뒤 사라진다 (명령마다 다시 센다)
    LaunchedEffect(cabin.voiceSeq) {
        if (cabin.voiceResult.isNotEmpty()) {
            delay(5_000)
            cabin.clearVoiceResult()
        }
    }

    // 경로 안내: 1초마다 차량 속도만큼 남은 거리를 줄인다
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            cabin.tick(speed)
        }
    }

    Box(
        Modifier
            .fillMaxSize()
            .background(IviColors.Background)
            .semantics { testTagsAsResourceId = true },
    ) {
        Column(Modifier.fillMaxSize()) {
            // 무드등 색 (설정)
            Box(Modifier.fillMaxWidth().height(3.dp).background(AmbientPalette[settings.ambient % AmbientPalette.size].copy(alpha = 0.7f)))
            StatusBar(source, state, settings, cabin.voiceResult, showClock = source != "AAOS", onVoice = { voiceOpen = true })
            Row(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                DrivingPanel(state, settings.mph, Modifier.weight(0.32f).fillMaxHeight())
                Box(Modifier.weight(0.68f).fillMaxHeight()) {
                    when (tab) {
                        Tab.HOME -> HomeScreen(state, settings, cabin) { tab = it }
                        Tab.NAVI -> NavigationScreen(state, cabin)
                        Tab.RADIO -> RadioScreen(settings, cabin)
                        Tab.MEDIA -> MediaScreen(state, cabin, onOpenVideo)
                        Tab.PHONE -> PhoneScreen(state, cabin)
                        Tab.CLIMATE -> ClimateScreen(state, onSetTemperature)
                        Tab.SETTINGS -> SettingsScreen(settings, store)
                    }
                    cabin.call?.let { CallOverlay(it.name, it.number, it.startedAt) { cabin.endCall() } }
                    if (voiceOpen) {
                        // 명령을 처리하면 패널은 바로 닫는다. 결과는 상태 줄에 잠깐 보인다
                        // (패널이 남아 있으면 안내·통화 화면을 가린다 — 6단계 회귀에서 발견)
                        VoicePanel(onCommand = { index ->
                            when (cabin.runVoice(index)) {
                                "radio" -> tab = Tab.RADIO
                                "navi" -> tab = Tab.NAVI
                            }
                            voiceOpen = false
                        }, onClose = { voiceOpen = false })
                    }
                }
            }
            AppBar(tab, state) { tab = it }
        }
        // 화면 밝기 (설정): 어둡게 덮는다. 터치는 막지 않는다
        val dim = (Settings.BRIGHTNESS_MAX - settings.brightness).coerceAtLeast(0) * 0.025f
        if (dim > 0f) Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = dim)))
        // 후방 카메라: 기어 R 이면 모든 화면 위에 뜬다
        if (state.gear == Gear.REVERSE) RearCamera()
    }
}

// ---------------- 상단 상태 줄 ----------------

@Composable
private fun StatusBar(source: String, state: VehicleState, settings: Settings, voiceResult: String, showClock: Boolean, onVoice: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().height(52.dp).padding(horizontal = 24.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // AAOS 는 시스템 바가 시계·프로필을 보여 주므로 태블릿(Mock)에서만 그린다
        if (showClock) Clock(settings.clock24)
        Chip(source, IviColors.Aqua, Modifier.testTag("source_badge"))
        if (!state.connected) Chip("차량 연결 안 됨", IviColors.Warn, Modifier.testTag("vehicle_disconnected"))
        state.error?.let { Chip(it, IviColors.Warn, Modifier.testTag("vehicle_error")) }
        Spacer(Modifier.weight(1f))
        if (voiceResult.isNotEmpty()) Chip("🎙 $voiceResult", IviColors.Aqua, Modifier.testTag("voice_result"))
        if (state.restricted) Chip("주행 중 · 일부 기능 제한", IviColors.Warn, Modifier.testTag("restriction_banner"))
        Text(
            "🎙 음성",
            Modifier
                .testTag("voice_button")
                .clip(RoundedCornerShape(50))
                .background(IviColors.SurfaceHigh)
                .clickable(onClick = onVoice)
                .padding(horizontal = 16.dp, vertical = 8.dp),
            fontSize = 15.sp,
        )
        if (showClock) Text("운전자", color = IviColors.TextSecondary, fontSize = 16.sp)
    }
}

@Composable
private fun Clock(clock24: Boolean) {
    var now by remember { mutableStateOf(LocalTime.now()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = LocalTime.now()
            delay(1_000)
        }
    }
    val pattern = if (clock24) "HH:mm" else "a h:mm"
    Text(now.format(DateTimeFormatter.ofPattern(pattern, Locale.KOREAN)), Modifier.testTag("status_clock"), fontSize = 20.sp, fontWeight = FontWeight.Medium)
}

// ---------------- 왼쪽 주행 정보 ----------------

@Composable
private fun DrivingPanel(state: VehicleState, mph: Boolean, modifier: Modifier) {
    Panel(modifier, verticalArrangement = Arrangement.SpaceBetween) {
        Label(if (state.restricted) "주행 중" else if (state.gear == Gear.PARK) "정차 중" else "대기")
        SpeedGauge(state.speedKmh, mph, state.restricted, Modifier.fillMaxWidth().weight(1f))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            GearSelector(state.gear)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Dot(if (state.connected) IviColors.Aqua else IviColors.Warn)
                Text(if (state.connected) "  차량 신호 수신 중" else "  차량 신호 없음", color = IviColors.TextSecondary, fontSize = 14.sp)
            }
        }
    }
}

/** 속도 숫자와 둘레의 호(0 ~ 200 km/h). 주행 중에는 강조색. */
@Composable
private fun SpeedGauge(kmh: Float, mph: Boolean, moving: Boolean, modifier: Modifier) {
    val ratio = (kmh / 200f).coerceIn(0f, 1f)
    val (value, unit) = speedDisplay(kmh, mph)
    Box(modifier.padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxHeight().aspectRatio(1f)) {
            val stroke = 10.dp.toPx()
            val inset = stroke / 2
            val arcSize = Size(size.width - stroke, size.height - stroke)
            drawArc(IviColors.Line, 135f, 270f, false, Offset(inset, inset), arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            if (ratio > 0f) {
                drawArc(if (moving) IviColors.Aqua else IviColors.AquaDeep, 135f, 270f * ratio, false, Offset(inset, inset), arcSize,
                    style = Stroke(stroke, cap = StrokeCap.Round))
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(value, Modifier.testTag("speed_value"), fontSize = 60.sp, fontWeight = FontWeight.Light, lineHeight = 60.sp)
            Text(unit, Modifier.testTag("speed_unit"), color = IviColors.TextSecondary, fontSize = 16.sp)
        }
    }
}

@Composable
private fun GearSelector(current: Gear) {
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        listOf(Gear.PARK, Gear.REVERSE, Gear.NEUTRAL, Gear.DRIVE).forEach { gear ->
            val on = gear == current
            Box(
                Modifier.size(44.dp).clip(RoundedCornerShape(10.dp)).background(if (on) IviColors.Aqua else Color.Transparent),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    gear.label,
                    // 테스트는 강조 색 대신, 지금 기어 칸에만 붙은 gear_value 의 글자를 읽는다
                    if (on) Modifier.testTag("gear_value") else Modifier,
                    fontSize = 24.sp,
                    fontWeight = if (on) FontWeight.Bold else FontWeight.Normal,
                    color = if (on) IviColors.Background else IviColors.TextSecondary,
                )
            }
        }
        if (current == Gear.UNKNOWN) {
            Text(current.label, Modifier.testTag("gear_value").padding(start = 8.dp), color = IviColors.Warn, fontSize = 20.sp)
        }
    }
}

// ---------------- 아래 앱 바 ----------------

@Composable
private fun AppBar(selected: Tab, state: VehicleState, onSelect: (Tab) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .height(80.dp)
            .clip(RoundedCornerShape(24.dp))
            .background(IviColors.Surface)
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TempReadout("운전석", state.driverTempC, Modifier.weight(1f), Alignment.Start)
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Tab.entries.forEach { tab -> AppBarButton(tab, tab == selected) { onSelect(tab) } }
        }
        TempReadout("조수석", state.passengerTempC, Modifier.weight(1f), Alignment.End)
    }
}

@Composable
private fun AppBarButton(tab: Tab, on: Boolean, onClick: () -> Unit) {
    Column(
        Modifier
            .testTag(tab.tag)
            .width(76.dp)
            .height(64.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(if (on) IviColors.Aqua.copy(alpha = 0.16f) else Color.Transparent)
            .clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(tab.glyph, fontSize = 20.sp, color = if (on) IviColors.Aqua else IviColors.TextPrimary)
        Text(tab.label, fontSize = 13.sp, color = if (on) IviColors.Aqua else IviColors.TextSecondary)
    }
}

/** 앱 바 양 끝의 온도 표시 (읽기 전용. 조절은 공조 화면에서 → 테스트 태그 없음). */
@Composable
private fun TempReadout(label: String, celsius: Float?, modifier: Modifier, align: Alignment.Horizontal) {
    Column(modifier, horizontalAlignment = align) {
        Text(label, color = IviColors.TextSecondary, fontSize = 12.sp)
        Text(celsius?.let { String.format(Locale.US, "%.1f°", it) } ?: "--", fontSize = 22.sp, fontWeight = FontWeight.Medium)
    }
}

// ---------------- 겹치는 화면 ----------------

@Composable
private fun CallOverlay(name: String, number: String, startedAt: Long, onEnd: () -> Unit) {
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(startedAt) {
        while (true) {
            now = System.currentTimeMillis()
            delay(500)
        }
    }
    val seconds = ((now - startedAt) / 1000).coerceAtLeast(0)
    Row(
        Modifier
            .testTag("phone_call_screen")
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Brush.horizontalGradient(listOf(IviColors.AquaDeep, IviColors.SurfaceHigh)))
            .padding(20.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text(name, Modifier.testTag("phone_call_name"), fontSize = 24.sp, fontWeight = FontWeight.SemiBold)
            Text(number, color = IviColors.TextSecondary, fontSize = 15.sp)
            Text("통화 중 %02d:%02d".format(seconds / 60, seconds % 60), Modifier.testTag("phone_call_timer"), color = IviColors.Aqua, fontSize = 16.sp)
        }
        RoundButton("✕", "phone_end", tint = IviColors.Danger, filled = true, onClick = onEnd)
    }
}

@Composable
private fun VoicePanel(onCommand: (Int) -> Unit, onClose: () -> Unit) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.BottomCenter) {
        Panel(Modifier.fillMaxWidth().testTag("voice_panel")) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🎙  무엇을 도와드릴까요?", fontSize = 20.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
                PillButton("닫기", "voice_close", onClick = onClose)
            }
            Label("말하는 대신 아래 문장을 누르면 인식된 것으로 처리합니다")
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                VoiceCommands.chunked(2).forEachIndexed { row, pair ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        pair.forEachIndexed { col, text ->
                            val index = row * 2 + col
                            PillButton("“$text”", "voice_cmd_$index", Modifier.weight(1f)) { onCommand(index) }
                        }
                    }
                }
            }
        }
    }
}

/** 후방 카메라: 실제 영상 대신 어두운 화면 + 주차 가이드 선. */
@Composable
private fun RearCamera() {
    Box(
        Modifier
            .fillMaxSize()
            .testTag("rear_camera")
            .background(Brush.verticalGradient(listOf(Color(0xFF1A2026), Color(0xFF2B3138)))),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val stroke = 6.dp.toPx()
            val bands = listOf(IviColors.Ok to 0.45f, IviColors.Warn to 0.65f, IviColors.Danger to 0.85f)
            // 양쪽 가이드 선 (원근감으로 위쪽이 좁다)
            val left = Path().apply { moveTo(w * 0.22f, h); lineTo(w * 0.38f, h * 0.35f) }
            val right = Path().apply { moveTo(w * 0.78f, h); lineTo(w * 0.62f, h * 0.35f) }
            drawPath(left, IviColors.Warn, style = Stroke(stroke, cap = StrokeCap.Round))
            drawPath(right, IviColors.Warn, style = Stroke(stroke, cap = StrokeCap.Round))
            bands.forEach { (color, at) ->
                val y = h * at
                val t = (h - y) / (h * 0.65f)
                val x1 = w * (0.22f + 0.16f * t)
                val x2 = w * (0.78f - 0.16f * t)
                drawLine(color, Offset(x1, y), Offset(x1 + w * 0.06f, y), stroke, StrokeCap.Round)
                drawLine(color, Offset(x2, y), Offset(x2 - w * 0.06f, y), stroke, StrokeCap.Round)
            }
        }
        Column(Modifier.padding(24.dp)) {
            Chip("후방 카메라", IviColors.Aqua)
            Spacer(Modifier.height(8.dp))
            Text("주변 안전을 직접 확인하세요", fontSize = 18.sp, color = IviColors.TextPrimary)
        }
    }
}

/** 홈 카드에서 무드등 이름을 쓸 때. */
fun ambientName(index: Int) = AmbientColors[index % AmbientColors.size]
