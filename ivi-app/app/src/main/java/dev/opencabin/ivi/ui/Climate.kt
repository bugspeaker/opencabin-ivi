package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState

// ---------------- 공조 (전 좌석 공조 패널) ----------------

@Composable
fun ClimateScreen(
    state: VehicleState,
    cockpit: CockpitState,
    setTemperature: (Seat, Float, Boolean) -> Unit,
    setSync: (Boolean) -> Unit,
) {
    if (!state.hvacAvailable) {
        Panel(Modifier.fillMaxWidth().testTag("hvac_unavailable")) {
            Text("공조를 제어할 수 없습니다", fontSize = 24.sp)
            Text("AAOS 에서는 CONTROL_CAR_CLIMATE 권한(시스템 앱)이 필요합니다.", color = IviColors.TextSecondary)
        }
        return
    }
    Row(Modifier.fillMaxSize().padding(bottom = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        SeatPanel("운전석", Seat.DRIVER, state.driverTempC, cockpit, setTemperature, Modifier.weight(1f).fillMaxHeight())
        Panel(Modifier.weight(1.05f).fillMaxHeight(), padding = 16.dp, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Label("공조")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Toggle("A/C", "climate_ac", cockpit.ac, Modifier.weight(1f)) { cockpit.ac = !cockpit.ac }
                Toggle("AUTO", "climate_auto", cockpit.autoMode, Modifier.weight(1f)) { cockpit.autoMode = !cockpit.autoMode }
                Toggle("SYNC", "climate_sync", cockpit.sync, Modifier.weight(1f)) { setSync(!cockpit.sync) }
            }
            Label("풍량")
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StepButton("−", "climate_fan_down", cockpit.fan > 1) { cockpit.fan-- }
                Row(Modifier.weight(1f).height(28.dp), horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.Bottom) {
                    (1..8).forEach { level ->
                        Box(
                            Modifier.weight(1f).fillMaxHeight(0.3f + level * 0.0875f).clip(RoundedCornerShape(3.dp))
                                .background(if (level <= cockpit.fan) IviColors.AccentSoft else IviColors.Line),
                        )
                    }
                }
                Text("${cockpit.fan}", Modifier.testTag("climate_fan_level"), fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                StepButton("+", "climate_fan_up", cockpit.fan < 8) { cockpit.fan++ }
            }
            Label("김서림 제거")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                IconToggle(G.DEFROST_FRONT, "앞", "climate_defrost_front", cockpit.defrostFront, IviColors.Warn, Modifier.weight(1f)) { cockpit.defrostFront = !cockpit.defrostFront }
                IconToggle(G.DEFROST_REAR, "뒤", "climate_defrost_rear", cockpit.defrostRear, IviColors.Warn, Modifier.weight(1f)) { cockpit.defrostRear = !cockpit.defrostRear }
            }
        }
        SeatPanel("조수석", Seat.PASSENGER, state.passengerTempC, cockpit, setTemperature, Modifier.weight(1f).fillMaxHeight())
    }
}

@Composable
private fun SeatPanel(
    title: String,
    seat: Seat,
    celsius: Float?,
    cockpit: CockpitState,
    setTemperature: (Seat, Float, Boolean) -> Unit,
    modifier: Modifier,
) {
    Panel(modifier, padding = 16.dp, verticalArrangement = Arrangement.SpaceBetween, horizontalAlignment = Alignment.CenterHorizontally) {
        Label(title)
        Text(tempText(celsius), Modifier.testTag("${seat.tag}_temp_value"), fontSize = 40.sp, fontWeight = FontWeight.Light)
        TemperatureBar(celsius)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TempButton("−", "${seat.tag}_temp_down", celsius != null && celsius > HvacSpec.MIN_C, IviColors.Cool) {
                setTemperature(seat, celsius!! - HvacSpec.STEP_C, true)
            }
            TempButton("+", "${seat.tag}_temp_up", celsius != null && celsius < HvacSpec.MAX_C, IviColors.Warm) {
                setTemperature(seat, celsius!! + HvacSpec.STEP_C, true)
            }
        }
        val heat = cockpit.seatHeat[seat] == true
        IconToggle(G.SEAT_HEAT, "열선", "seat_heat_${seat.tag}", heat, IviColors.Warm, Modifier.fillMaxWidth()) { cockpit.seatHeat[seat] = !heat }
    }
}

/** 설정 온도 위치를 16 ~ 28°C 막대로 보여 준다 (파랑 → 빨강). */
@Composable
private fun TemperatureBar(celsius: Float?) {
    val ratio = celsius?.let { (it - HvacSpec.MIN_C) / (HvacSpec.MAX_C - HvacSpec.MIN_C) }?.coerceIn(0f, 1f) ?: 0f
    Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(IviColors.Line)) {
        Box(Modifier.fillMaxWidth(ratio.coerceAtLeast(0.02f)).fillMaxHeight().background(Brush.horizontalGradient(listOf(IviColors.Cool, IviColors.Warm))))
    }
}

@Composable
private fun TempButton(text: String, tag: String, enabled: Boolean, tint: Color, onClick: () -> Unit) {
    // 차량용 최소 터치 영역 76dp → 분할 화면 폭에 맞춰 68dp (구글 자동차 가이드 최소 76px@160dpi 이상)
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.testTag(tag).size(68.dp),
        shape = CircleShape,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = tint.copy(alpha = 0.18f),
            contentColor = tint,
            disabledContainerColor = IviColors.SurfaceHigh,
            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.4f),
        ),
    ) { Text(text, fontSize = 30.sp) }
}

@Composable
private fun Toggle(label: String, tag: String, on: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Box(
        modifier.testTag(tag).height(52.dp).outlined(on).clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = if (on) IviColors.Green else IviColors.TextSecondary)
    }
}

@Composable
private fun IconToggle(g: G, label: String, tag: String, on: Boolean, onColor: Color, modifier: Modifier, onClick: () -> Unit) {
    Row(
        modifier.testTag(tag).height(52.dp).outlined(on).clickable(onClick = onClick).padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
    ) {
        Glyph(g, if (on) onColor else IviColors.TextSecondary, Modifier.size(24.dp))
        Text(label, fontSize = 15.sp, color = if (on) onColor else IviColors.TextSecondary)
    }
}

@Composable
private fun StepButton(text: String, tag: String, enabled: Boolean, onClick: () -> Unit) {
    Box(
        Modifier.testTag(tag).size(48.dp).outlined().clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Text(text, fontSize = 24.sp, color = if (enabled) IviColors.TextPrimary else IviColors.TextTertiary) }
}

// ---------------- 차량 · 빠른 제어 ----------------

@Composable
fun VehicleScreen(state: VehicleState, cockpit: CockpitState) {
    val driving = state.restricted
    Panel(Modifier.fillMaxSize().padding(bottom = 4.dp), padding = 18.dp, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("빠른 제어", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
            if (driving) Text("주행 중에는 사이드 미러 · 트렁크를 조작할 수 없습니다", Modifier.testTag("qc_restricted_notice"), color = IviColors.Warn, fontSize = 13.sp)
        }
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            QuickTile(if (cockpit.doorsLocked) G.LOCK else G.UNLOCK, "도어", if (cockpit.doorsLocked) "잠김" else "열림", "qc_door_lock", cockpit.doorsLocked, true, Modifier.weight(1f)) {
                cockpit.doorsLocked = !cockpit.doorsLocked
            }
            // 사이드 미러: 주행 중에는 접을 수 없다 (펴는 것은 된다)
            QuickTile(G.MIRROR, "사이드 미러", if (cockpit.mirrorsFolded) "접힘" else "펼침", "qc_mirror", cockpit.mirrorsFolded, !driving || cockpit.mirrorsFolded, Modifier.weight(1f)) {
                cockpit.mirrorsFolded = !cockpit.mirrorsFolded
            }
            QuickTile(G.TRUNK, "트렁크", if (cockpit.trunkOpen) "열림" else "닫힘", "qc_trunk", cockpit.trunkOpen, !driving, Modifier.weight(1f)) {
                cockpit.trunkOpen = !cockpit.trunkOpen
            }
        }
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            QuickTile(G.CHILD, "차일드 락", if (cockpit.childLock) "켜짐" else "꺼짐", "qc_child_lock", cockpit.childLock, true, Modifier.weight(1f)) {
                cockpit.childLock = !cockpit.childLock
            }
            QuickTile(G.LIGHT, "실내등", if (cockpit.interiorLight) "켜짐" else "꺼짐", "qc_interior_light", cockpit.interiorLight, true, Modifier.weight(1f)) {
                cockpit.interiorLight = !cockpit.interiorLight
            }
            QuickTile(G.SEAT_HEAT, "운전석 열선", if (cockpit.seatHeat[Seat.DRIVER] == true) "켜짐" else "꺼짐", "qc_seat_heat", cockpit.seatHeat[Seat.DRIVER] == true, true, Modifier.weight(1f)) {
                cockpit.seatHeat[Seat.DRIVER] = cockpit.seatHeat[Seat.DRIVER] != true
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("전조등", fontSize = 16.sp, modifier = Modifier.padding(end = 12.dp))
            LightMode.entries.forEach { mode ->
                val on = cockpit.lights == mode
                Box(
                    Modifier.testTag(mode.tag).size(width = 88.dp, height = 48.dp).outlined(on).clickable { cockpit.lights = mode },
                    contentAlignment = Alignment.Center,
                ) { Text(mode.label, fontSize = 15.sp, color = if (on) IviColors.AccentSoft else IviColors.TextSecondary, fontWeight = FontWeight.Medium) }
            }
            androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
            PillButton("차량 설정", "vehicle_settings") { cockpit.open(Tab.SETTINGS) }
        }
    }
}

@Composable
private fun QuickTile(g: G, title: String, value: String, tag: String, on: Boolean, enabled: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier
            .testTag(tag)
            .fillMaxHeight()
            .clip(RoundedCornerShape(16.dp))
            .background(if (on) IviColors.AccentDeep else IviColors.SurfaceHigh)
            .border(1.dp, if (on) IviColors.Accent else IviColors.Line, RoundedCornerShape(16.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(14.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        val tint = when { !enabled -> IviColors.TextTertiary; on -> IviColors.TextPrimary; else -> IviColors.TextSecondary }
        Glyph(g, tint, Modifier.size(30.dp))
        Column {
            Text(title, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = if (enabled) IviColors.TextPrimary else IviColors.TextTertiary)
            Text(value, Modifier.testTag("${tag}_value"), fontSize = 13.sp, color = if (enabled) IviColors.TextSecondary else IviColors.TextTertiary)
        }
    }
}

// ---------------- 앱 목록 (앱 라이브러리) ----------------

private data class AppEntry(val id: String, val name: String, val colors: List<Color>, val glyph: G, val tab: Tab?)

@Composable
fun AppsScreen(state: VehicleState, cockpit: CockpitState, onOpenVideo: () -> Unit) {
    val apps = listOf(
        AppEntry("navigation", "내비게이션", TileColors.Navigation, G.NAV, Tab.HOME),
        AppEntry("media", "미디어", TileColors.Media, G.MUSIC, Tab.MEDIA),
        AppEntry("radio", "라디오", TileColors.Radio, G.RADIO, Tab.RADIO),
        AppEntry("phone", "전화", TileColors.Phone, G.PHONE, Tab.PHONE),
        AppEntry("climate", "공조", TileColors.Climate, G.FAN, Tab.CLIMATE),
        AppEntry("assistant", "AI 어시스턴트", TileColors.Assistant, G.SPARK, Tab.ASSISTANT),
        AppEntry("vehicle", "차량", TileColors.Vehicle, G.CAR, Tab.VEHICLE),
        AppEntry("settings", "설정", TileColors.Settings, G.GEAR, Tab.SETTINGS),
        AppEntry("video", "영상", TileColors.Video, G.VIDEO, null),
        AppEntry("market", "앱 마켓", TileColors.Market, G.BAG, null),
    )
    Panel(Modifier.fillMaxSize().padding(bottom = 4.dp), padding = 20.dp, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("앱", fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
        apps.chunked(5).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                row.forEach { app ->
                    // 영상은 주행 중 막고, 앱 마켓은 이 데모에 없다 (준비 중)
                    val enabled = when (app.id) { "video" -> !state.restricted; "market" -> false; else -> true }
                    Column(
                        Modifier
                            .testTag("app_${app.id}")
                            .clip(RoundedCornerShape(16.dp))
                            .clickable(enabled = enabled) { if (app.tab != null) cockpit.open(app.tab) else if (app.id == "video") onOpenVideo() }
                            .padding(10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            AppTile(app.colors, 64.dp) { Glyph(app.glyph, Color.White, it) }
                            if (!enabled) Box(Modifier.size(64.dp).clip(RoundedCornerShape(18.dp)).background(Color.Black.copy(alpha = 0.55f)))
                        }
                        Text(app.name, fontSize = 14.sp, textAlign = TextAlign.Center, color = if (enabled) IviColors.TextPrimary else IviColors.TextTertiary)
                        if (!enabled) Text(if (app.id == "video") "주행 중 제한" else "준비 중", fontSize = 11.sp, color = IviColors.TextTertiary)
                    }
                }
            }
        }
    }
}
