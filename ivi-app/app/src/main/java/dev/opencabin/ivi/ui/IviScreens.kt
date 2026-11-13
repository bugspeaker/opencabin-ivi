package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.listSaver
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
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.vehicle.Gear
import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/*
 * 화면 구성은 양산 IVI 의 일반적인 구조를 따른다 (docs/phase5-design.md):
 *   - 왼쪽 '주행 정보' 패널(속도·기어·주행 상태)이 항상 보이고, 오른쪽이 앱 영역
 *   - 아래 '앱 바'로 한 번에 화면을 바꾼다 (홈·공조·미디어)
 *   - 어두운 바탕 + 아쿠아 블루 강조색, 큰 터치 영역(76dp 이상), 주행 중에는 강조 색을 줄이고 애니메이션을 쓰지 않는다
 * 실제 제조사 로고·제품명·전용 글꼴·아이콘은 쓰지 않는다.
 *
 * 테스트 태그는 Appium 에서 resource-id 로 보이게 한다 (testTagsAsResourceId). 이름은 ivi-tests/ivi/screens.py 와 맞춘다.
 */

object IviColors {
    val Background = Color(0xFF070B10)
    val Surface = Color(0xFF111820)
    val SurfaceHigh = Color(0xFF19222C)
    val Line = Color(0xFF243140)
    val Aqua = Color(0xFF34C6D8)
    val AquaDeep = Color(0xFF0B5E6B)
    val TextPrimary = Color(0xFFEAF1F6)
    val TextSecondary = Color(0xFF8796A5)
    val Warn = Color(0xFFFFB547)
    val Cool = Color(0xFF4DA3FF)
    val Warm = Color(0xFFFF7A59)
}

@Composable
fun IviTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = IviColors.Aqua,
            onPrimary = IviColors.Background,
            background = IviColors.Background,
            surface = IviColors.Surface,
            onBackground = IviColors.TextPrimary,
            onSurface = IviColors.TextPrimary,
        ),
    ) {
        // Surface 없이 그리는 Text 는 기본 글자색이 검정이라 어두운 바탕에서 안 보인다 (2단계에서 발견)
        CompositionLocalProvider(LocalContentColor provides IviColors.TextPrimary, content = content)
    }
}

enum class Tab(val label: String, val glyph: String, val tag: String) {
    HOME("홈", "⌂", "nav_home"), CLIMATE("공조", "✻", "nav_climate"), MEDIA("미디어", "♪", "nav_media")
}

val Tracks = listOf(
    "Night Drive" to "Neon Avenue",
    "Coastal Road" to "Blue Hour",
    "City Lights" to "Metro Lines",
    "Morning Commute" to "Daybreak",
    "Long Way Home" to "Last Exit",
)

/** 미디어 재생 상태. 홈 카드와 미디어 화면이 같은 값을 본다. 화면 회전 등에도 유지된다 (Saver). */
class MediaState(current: Int = 0, playing: Boolean = false) {
    var current by mutableIntStateOf(current)
    var playing by mutableStateOf(playing)

    companion object {
        val Saver = listSaver<MediaState, Int>(
            save = { listOf(it.current, if (it.playing) 1 else 0) },
            restore = { MediaState(it[0], it[1] == 1) },
        )
    }
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun IviRoot(
    source: String,
    state: VehicleState,
    onSetTemperature: (Seat, Float) -> Unit,
    onOpenVideo: () -> Unit,
) {
    var tab by rememberSaveable { mutableStateOf(Tab.HOME) }
    val media = rememberSaveable(saver = MediaState.Saver) { MediaState() }

    Column(
        Modifier
            .fillMaxSize()
            .background(IviColors.Background)
            .semantics { testTagsAsResourceId = true },
    ) {
        // AAOS 는 시스템 바가 시계·프로필을 이미 보여 주므로 앱은 태블릿(Mock)에서만 그린다
        StatusBar(source, state, showClock = source != "AAOS")
        Row(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            DrivingPanel(state, Modifier.weight(0.34f).fillMaxHeight())
            Box(Modifier.weight(0.66f).fillMaxHeight()) {
                when (tab) {
                    Tab.HOME -> HomeScreen(state, media, onOpen = { tab = it })
                    Tab.CLIMATE -> ClimateScreen(state, onSetTemperature)
                    Tab.MEDIA -> MediaScreen(state, media, onOpenVideo)
                }
            }
        }
        AppBar(tab, state) { tab = it }
    }
}

// ---------------- 상단 상태 줄 ----------------

@Composable
private fun StatusBar(source: String, state: VehicleState, showClock: Boolean) {
    Row(
        Modifier.fillMaxWidth().height(52.dp).padding(horizontal = 24.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (showClock) Clock()
        Chip(source, IviColors.Aqua, Modifier.testTag("source_badge"))
        if (!state.connected) Chip("차량 연결 안 됨", IviColors.Warn, Modifier.testTag("vehicle_disconnected"))
        state.error?.let { Chip(it, IviColors.Warn, Modifier.testTag("vehicle_error")) }
        Spacer(Modifier.weight(1f))
        if (state.restricted) Chip("주행 중 · 일부 기능 제한", IviColors.Warn, Modifier.testTag("restriction_banner"))
        if (showClock) Text("운전자", color = IviColors.TextSecondary, fontSize = 16.sp)
    }
}

@Composable
private fun Clock() {
    var now by remember { mutableStateOf(LocalTime.now()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = LocalTime.now()
            delay(1_000)
        }
    }
    Text(now.format(DateTimeFormatter.ofPattern("HH:mm")), fontSize = 20.sp, fontWeight = FontWeight.Medium)
}

@Composable
private fun Chip(text: String, color: Color, modifier: Modifier = Modifier) {
    Text(
        text,
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(color.copy(alpha = 0.16f))
            .padding(horizontal = 14.dp, vertical = 5.dp),
        color = color,
        fontSize = 15.sp,
        fontWeight = FontWeight.Medium,
    )
}

// ---------------- 왼쪽 주행 정보 패널 ----------------

@Composable
private fun DrivingPanel(state: VehicleState, modifier: Modifier) {
    Panel(modifier, verticalArrangement = Arrangement.SpaceBetween) {
        Label(if (state.restricted) "주행 중" else if (state.gear == Gear.PARK) "정차 중" else "대기")
        SpeedGauge(state.speedKmh, state.restricted, Modifier.fillMaxWidth().weight(1f))
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            GearSelector(state.gear)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(8.dp).clip(CircleShape).background(if (state.connected) IviColors.Aqua else IviColors.Warn))
                Text(
                    if (state.connected) "  차량 신호 수신 중" else "  차량 신호 없음",
                    color = IviColors.TextSecondary,
                    fontSize = 14.sp,
                )
            }
        }
    }
}

/** 속도 숫자와 그 둘레의 호(0 ~ 200 km/h). 주행 중에는 강조색, 정차 중에는 어두운 호만 보인다. */
@Composable
private fun SpeedGauge(kmh: Float, moving: Boolean, modifier: Modifier) {
    val ratio = (kmh / 200f).coerceIn(0f, 1f)
    Box(modifier.padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxHeight().aspectRatio(1f)) {
            val stroke = 10.dp.toPx()
            val inset = stroke / 2
            val arcSize = Size(size.width - stroke, size.height - stroke)
            drawArc(IviColors.Line, startAngle = 135f, sweepAngle = 270f, useCenter = false,
                topLeft = Offset(inset, inset), size = arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            if (ratio > 0f) {
                drawArc(if (moving) IviColors.Aqua else IviColors.AquaDeep, startAngle = 135f, sweepAngle = 270f * ratio,
                    useCenter = false, topLeft = Offset(inset, inset), size = arcSize, style = Stroke(stroke, cap = StrokeCap.Round))
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                String.format(Locale.US, "%.0f", kmh),
                Modifier.testTag("speed_value"),
                fontSize = 64.sp,
                fontWeight = FontWeight.Light,
                lineHeight = 64.sp,
            )
            Text("km/h", color = IviColors.TextSecondary, fontSize = 16.sp)
        }
    }
}

@Composable
private fun GearSelector(current: Gear) {
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        listOf(Gear.PARK, Gear.REVERSE, Gear.NEUTRAL, Gear.DRIVE).forEach { gear ->
            val on = gear == current
            Box(
                Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (on) IviColors.Aqua else Color.Transparent),
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
            .padding(horizontal = 20.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TempReadout("운전석", state.driverTempC, Modifier.weight(1f), Alignment.Start)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
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
            .width(96.dp)
            .height(64.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(if (on) IviColors.Aqua.copy(alpha = 0.16f) else Color.Transparent)
            .clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(tab.glyph, fontSize = 22.sp, color = if (on) IviColors.Aqua else IviColors.TextPrimary)
        Text(tab.label, fontSize = 14.sp, color = if (on) IviColors.Aqua else IviColors.TextSecondary)
    }
}

/** 앱 바 양 끝의 온도 표시 (읽기 전용. 조절은 공조 화면에서 한다 → 테스트 태그 없음). */
@Composable
private fun TempReadout(label: String, celsius: Float?, modifier: Modifier, align: Alignment.Horizontal) {
    Column(modifier, horizontalAlignment = align) {
        Text(label, color = IviColors.TextSecondary, fontSize = 12.sp)
        Text(celsius?.let { String.format(Locale.US, "%.1f°", it) } ?: "--", fontSize = 22.sp, fontWeight = FontWeight.Medium)
    }
}

// ---------------- 홈 (카드) ----------------

@Composable
private fun HomeScreen(state: VehicleState, media: MediaState, onOpen: (Tab) -> Unit) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        val (title, artist) = Tracks[media.current]
        Panel(
            Modifier.fillMaxWidth().weight(1f).clickable { onOpen(Tab.MEDIA) },
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                AlbumArt(media.current, Modifier.size(96.dp))
                Column {
                    Label("미디어")
                    Text(title, Modifier.testTag("home_media_title"), fontSize = 26.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("$artist · ${if (media.playing) "재생 중" else "일시 정지"}", color = IviColors.TextSecondary, fontSize = 16.sp)
                }
            }
            // 재생 위치 (가짜 미디어라 곡마다 고정 위치)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("1:${12 + media.current * 7}", color = IviColors.TextSecondary, fontSize = 13.sp)
                Box(Modifier.weight(1f).height(4.dp).clip(RoundedCornerShape(2.dp)).background(IviColors.Line)) {
                    Box(Modifier.fillMaxWidth(0.25f + media.current * 0.12f).fillMaxHeight().background(IviColors.Aqua))
                }
                Text("3:4${media.current}", color = IviColors.TextSecondary, fontSize = 13.sp)
            }
        }
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Panel(Modifier.weight(1f).fillMaxHeight().clickable { onOpen(Tab.CLIMATE) }) {
                Label("공조")
                Text("운전석 ${tempText(state.driverTempC)}", Modifier.testTag("home_driver_temp"), fontSize = 22.sp)
                Text("조수석 ${tempText(state.passengerTempC)}", Modifier.testTag("home_passenger_temp"), fontSize = 22.sp)
            }
            Panel(Modifier.weight(1f).fillMaxHeight()) {
                Label("차량 연결")
                Text(if (state.connected) "연결됨" else "연결 안 됨", fontSize = 22.sp, color = if (state.connected) IviColors.Aqua else IviColors.Warn)
                Text(if (state.hvacAvailable) "공조 제어 가능" else "공조 제어 불가", color = IviColors.TextSecondary, fontSize = 15.sp)
            }
        }
    }
}

// ---------------- 공조 ----------------

@Composable
private fun ClimateScreen(state: VehicleState, onSetTemperature: (Seat, Float) -> Unit) {
    if (!state.hvacAvailable) {
        Panel(Modifier.fillMaxWidth().testTag("hvac_unavailable")) {
            Text("공조를 제어할 수 없습니다", fontSize = 24.sp)
            Text("AAOS 에서는 CONTROL_CAR_CLIMATE 권한(시스템 앱)이 필요합니다.", color = IviColors.TextSecondary)
        }
        return
    }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        SeatPanel("운전석", Seat.DRIVER, state.driverTempC, onSetTemperature, Modifier.weight(1f).fillMaxHeight())
        SeatPanel("조수석", Seat.PASSENGER, state.passengerTempC, onSetTemperature, Modifier.weight(1f).fillMaxHeight())
    }
}

@Composable
private fun SeatPanel(title: String, seat: Seat, celsius: Float?, onSet: (Seat, Float) -> Unit, modifier: Modifier) {
    Panel(modifier, verticalArrangement = Arrangement.SpaceBetween) {
        Label(title)
        Text(tempText(celsius), Modifier.testTag("${seat.tag}_temp_value"), fontSize = 52.sp, fontWeight = FontWeight.Light)
        TemperatureBar(celsius)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            RoundButton("−", "${seat.tag}_temp_down", celsius != null && celsius > HvacSpec.MIN_C, IviColors.Cool) {
                onSet(seat, celsius!! - HvacSpec.STEP_C)
            }
            RoundButton("+", "${seat.tag}_temp_up", celsius != null && celsius < HvacSpec.MAX_C, IviColors.Warm) {
                onSet(seat, celsius!! + HvacSpec.STEP_C)
            }
        }
    }
}

/** 설정 온도 위치를 16 ~ 28°C 막대로 보여 준다 (파랑 → 주황). */
@Composable
private fun TemperatureBar(celsius: Float?) {
    val ratio = celsius?.let { (it - HvacSpec.MIN_C) / (HvacSpec.MAX_C - HvacSpec.MIN_C) }?.coerceIn(0f, 1f) ?: 0f
    Box(
        Modifier
            .fillMaxWidth()
            .height(8.dp)
            .clip(RoundedCornerShape(4.dp))
            .background(IviColors.Line),
    ) {
        Box(
            Modifier
                .fillMaxWidth(ratio.coerceAtLeast(0.02f))
                .fillMaxHeight()
                .background(Brush.horizontalGradient(listOf(IviColors.Cool, IviColors.Warm))),
        )
    }
}

@Composable
private fun RoundButton(text: String, tag: String, enabled: Boolean, tint: Color, onClick: () -> Unit) {
    // 차량용 최소 터치 영역 76dp (1단계에서 겹침 결함을 본 SystemUI 버튼과 같은 크기)
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.testTag(tag).size(76.dp),
        shape = CircleShape,
        colors = ButtonDefaults.buttonColors(
            containerColor = tint.copy(alpha = 0.18f),
            contentColor = tint,
            disabledContainerColor = IviColors.SurfaceHigh,
            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.4f),
        ),
    ) { Text(text, fontSize = 30.sp) }
}

// ---------------- 미디어 ----------------

@Composable
private fun MediaScreen(state: VehicleState, media: MediaState, onOpenVideo: () -> Unit) {
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Label("재생 목록")
            LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                itemsIndexed(Tracks) { index, (title, artist) ->
                    val on = index == media.current
                    Row(
                        Modifier
                            .testTag("track_$index")
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (on) IviColors.Aqua.copy(alpha = 0.14f) else Color.Transparent)
                            .clickable { media.current = index; media.playing = true }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(title, fontSize = 17.sp, color = if (on) IviColors.Aqua else IviColors.TextPrimary, modifier = Modifier.weight(1f).testTag("track_${index}_title"))
                        Text(artist, fontSize = 13.sp, color = IviColors.TextSecondary)
                    }
                }
            }
        }
        Panel(Modifier.weight(1f).fillMaxHeight(), verticalArrangement = Arrangement.SpaceBetween) {
            val (title, artist) = Tracks[media.current]
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                AlbumArt(media.current, Modifier.size(72.dp))
                Column {
                    Text(title, Modifier.testTag("now_playing_title"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(artist, color = IviColors.TextSecondary, fontSize = 14.sp)
                    Text(if (media.playing) "재생 중" else "일시 정지", Modifier.testTag("playback_state"), color = IviColors.Aqua, fontSize = 14.sp)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(
                    onClick = { media.playing = !media.playing },
                    modifier = Modifier.testTag("play_pause").size(76.dp),
                    shape = CircleShape,
                    colors = ButtonDefaults.buttonColors(containerColor = IviColors.Aqua, contentColor = IviColors.Background),
                ) { Text(if (media.playing) "❚❚" else "▶", fontSize = 22.sp) }
                Column {
                    Button(
                        onClick = onOpenVideo,
                        enabled = !state.restricted,
                        modifier = Modifier.testTag("open_video").height(52.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = IviColors.SurfaceHigh,
                            contentColor = IviColors.TextPrimary,
                            disabledContainerColor = IviColors.SurfaceHigh.copy(alpha = 0.5f),
                            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.5f),
                        ),
                    ) { Text("영상 보기", fontSize = 16.sp) }
                }
            }
            if (state.restricted) {
                Text("주행 중에는 영상을 볼 수 없습니다", Modifier.testTag("video_restricted_notice"), color = IviColors.Warn, fontSize = 14.sp)
            }
        }
    }
}

@Composable
private fun AlbumArt(index: Int, modifier: Modifier) {
    val palettes = listOf(
        listOf(Color(0xFF1B3A5C), IviColors.Aqua),
        listOf(Color(0xFF3A1B5C), Color(0xFF6C8CFF)),
        listOf(Color(0xFF14343A), Color(0xFF5CE0B0)),
        listOf(Color(0xFF4A2A14), Color(0xFFFFB547)),
        listOf(Color(0xFF2A1430), Color(0xFFFF7A9A)),
    )
    Box(
        modifier
            .aspectRatio(1f)
            .clip(RoundedCornerShape(14.dp))
            .background(Brush.linearGradient(palettes[index % palettes.size])),
        contentAlignment = Alignment.Center,
    ) { Text("♪", fontSize = 28.sp, color = Color.White.copy(alpha = 0.85f)) }
}

// ---------------- 공통 ----------------

@Composable
fun Panel(
    modifier: Modifier = Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.spacedBy(10.dp),
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .clip(RoundedCornerShape(24.dp))
            .background(IviColors.Surface)
            .border(1.dp, IviColors.Line, RoundedCornerShape(24.dp))
            .padding(24.dp),
        verticalArrangement = verticalArrangement,
        content = content,
    )
}

@Composable
fun Label(text: String) = Text(text, color = IviColors.TextSecondary, fontSize = 15.sp, fontWeight = FontWeight.Medium)

fun tempText(celsius: Float?) = celsius?.let { String.format(Locale.US, "%.1f°C", it) } ?: "--"
