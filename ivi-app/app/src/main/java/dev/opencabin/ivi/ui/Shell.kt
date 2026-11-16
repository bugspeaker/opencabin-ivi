package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.assistant.CabinAssistant
import dev.opencabin.ivi.assistant.CabinControls
import dev.opencabin.ivi.assistant.Place
import dev.opencabin.ivi.assistant.Reply
import dev.opencabin.ivi.state.AmbientColors
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Contacts
import dev.opencabin.ivi.state.Settings
import dev.opencabin.ivi.state.SettingsStore
import dev.opencabin.ivi.state.VoiceCommands
import dev.opencabin.ivi.vehicle.Gear
import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleDataSource
import dev.opencabin.ivi.vehicle.VehicleState
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.roundToInt

/*
 * 화면 틀 (docs/phase7-pleos.md) — 차세대 양산 IVI(Pleos Connect)의 3영역 구조:
 *   ┌──────────────┬───────────────────────────────────────────┐
 *   │ 주행 정보     │ 상단 바: 검색 · 알림 · 데이터 소스 · 상태 · AI · 시계 │
 *   │ 속도·기어·    ├───────────────────────────────────────────┤
 *   │ 주행 뷰·      │ 앱 화면 (단일 / 분할: 내비 + 오디오)              │
 *   │ 유틸리티 위젯 │   위에 겹치는 것: 음성 팝업 · 통화 · 알림 · 후방 카메라 │
 *   ├──────────────┴───────────────────────────────────────────┤
 *   │ 하단 바: 차량 · ‹운전석 온도› · 열선 | 공조 미디어 전화 내비 AI 앱 | 이전 앱 | 열선 · ‹조수석 온도› │
 *   └──────────────────────────────────────────────────────────┘
 * 앱 화면은 주행 정보 영역을 침범하지 않는다 (후방 카메라도 앱 화면 위에만 뜬다).
 * 테스트 태그는 Appium 에서 resource-id 로 보인다 (testTagsAsResourceId). 이름은 ivi-tests/ivi/screens.py 와 맞춘다.
 */

val AmbientPalette = listOf(IviColors.Accent, Color(0xFFE8F0F5), IviColors.Warn, Color(0xFF9B7BFF), IviColors.Green)

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
    vehicle: VehicleDataSource,
    onOpenVideo: () -> Unit,
) {
    val cockpit = remember { CockpitState() }
    val current by rememberUpdatedState(state)

    /** 동기화(SYNC) 중이면 운전석 값을 조수석에도 쓴다. 조수석을 직접 바꾸면 동기화가 풀린다 (일반적인 차량 동작). */
    fun setTemperature(seat: Seat, celsius: Float, direct: Boolean) {
        val value = HvacSpec.clamp(celsius)
        vehicle.setTemperature(seat, value)
        if (cockpit.sync && seat == Seat.DRIVER) vehicle.setTemperature(Seat.PASSENGER, value)
        if (cockpit.sync && seat == Seat.PASSENGER && direct) cockpit.sync = false
    }

    fun setSync(on: Boolean) {
        cockpit.sync = on
        if (on) current.driverTempC?.let { vehicle.setTemperature(Seat.PASSENGER, it) }
    }

    // AI 어시스턴트가 차를 움직이는 길. 오디오·내비·전화는 6단계 CabinController 를 그대로 쓴다
    val assistant = remember {
        CabinAssistant(object : CabinControls {
            override val restricted get() = current.restricted
            override val hvacAvailable get() = current.hvacAvailable
            override fun temperature(seat: Seat) = when (seat) { Seat.DRIVER -> current.driverTempC; Seat.PASSENGER -> current.passengerTempC }
            override fun setTemperature(seat: Seat, celsius: Float) = setTemperature(seat, celsius, direct = false)
            override fun setAc(on: Boolean) = vehicle.setAc(on)
            override fun setSync(on: Boolean) = setSync(on)
            override fun setSeatHeat(seat: Seat, on: Boolean) = vehicle.setSeatHeat(seat, if (on) HvacSpec.SEAT_HEAT_MAX else 0)
            override fun play() = cabin.playMedia()
            override fun pause() = cabin.pauseMedia()
            override fun next() = cabin.nextTrack()
            override fun navigate(place: Place) { cabin.startGuidance(place); cockpit.open(Tab.HOME) }
            override fun cancelRoute() = (cabin.destination != null).also { cabin.stopGuidance() }
            override fun openVideo() = onOpenVideo()
            override fun foldMirrors(fold: Boolean) { cockpit.mirrorsFolded = fold }
            override fun setRadio(on: Boolean) { cabin.setRadio(on); if (on) cockpit.open(Tab.RADIO) }
            override fun call(who: String) = Contacts.firstOrNull { it.name == who }?.let { cabin.dial(it.name, it.number); it.name }
        })
    }

    /** 말 한 번: 대화 내역에 남기고 대답을 돌려준다. 음성 팝업과 AI 어시스턴트 화면이 같이 쓴다. */
    fun ask(text: String): Reply {
        cockpit.say(true, text, cockpit.speaker)
        val reply = assistant.handle(text, cockpit.speaker)
        cockpit.say(false, reply.text, null, reply.candidates)
        return reply
    }

    ShellEffects(state, cabin, cockpit)

    Box(
        Modifier
            .fillMaxSize()
            .background(IviColors.Background)
            .semantics { testTagsAsResourceId = true },
    ) {
        Column(Modifier.fillMaxSize()) {
            // 무드등 색 (설정)
            Box(Modifier.fillMaxWidth().height(3.dp).background(AmbientPalette[settings.ambient % AmbientPalette.size].copy(alpha = 0.7f)))
            Row(Modifier.weight(1f).fillMaxWidth()) {
                Cluster(state, settings.mph, cabin, cockpit, Modifier.weight(0.31f).fillMaxHeight())
                Column(Modifier.weight(0.69f).fillMaxHeight().padding(end = 12.dp)) {
                    TopBar(source, state, settings, cabin, cockpit, showClock = source != "AAOS")
                    Box(Modifier.weight(1f).fillMaxWidth()) {
                        when (cockpit.tab) {
                            Tab.HOME -> HomeScreen(state, settings, cabin, cockpit)
                            Tab.RADIO -> RadioScreen(settings, cabin)
                            Tab.MEDIA -> MediaScreen(state, cabin, onOpenVideo)
                            Tab.PHONE -> PhoneScreen(state, cabin)
                            Tab.CLIMATE -> ClimateScreen(state, cockpit, vehicle, ::setTemperature, ::setSync)
                            Tab.SETTINGS -> SettingsScreen(settings, store)
                            Tab.ASSISTANT -> AssistantScreen(state, cockpit, onAsk = ::ask) { place ->
                                cockpit.say(false, assistant.choose(place).text, null)
                            }
                            Tab.VEHICLE -> VehicleScreen(state, cockpit, vehicle)
                            Tab.APPS -> AppsScreen(state, cockpit, onOpenVideo)
                        }
                        cabin.call?.let { CallOverlay(it.name, it.number, it.startedAt) { cabin.endCall() } }
                        if (cockpit.voiceOpen) {
                            // 명령을 처리하면 팝업은 바로 닫는다. 결과는 상단 바에 잠깐 보인다
                            // (팝업이 남아 있으면 안내·통화 화면을 가린다 — 6단계 회귀에서 발견)
                            VoicePopup(cockpit, onCommand = { index ->
                                cabin.showVoiceResult(ask(VoiceCommands[index]).text)
                                cockpit.voiceOpen = false
                            }, onOpenAssistant = { cockpit.voiceOpen = false; cockpit.open(Tab.ASSISTANT) }, onClose = { cockpit.voiceOpen = false })
                        }
                        if (cockpit.notificationsOpen) NotificationPanel(cockpit, Modifier.align(Alignment.TopEnd))
                        // 후방 카메라: 기어 R 이면 앱 화면 위에 뜬다 (주행 정보는 그대로 보인다)
                        if (state.gear == Gear.REVERSE) RearCamera()
                    }
                }
            }
            BottomBar(state, cockpit, vehicle, ::setTemperature)
        }
        // 화면 밝기 (설정): 어둡게 덮는다. 터치는 막지 않는다
        val dim = (Settings.BRIGHTNESS_MAX - settings.brightness).coerceAtLeast(0) * 0.025f
        if (dim > 0f) Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = dim)))
    }
}

/** 1초 주기 일(경로 진행·현 주행 정보)과 알림을 만드는 일. */
@Composable
private fun ShellEffects(state: VehicleState, cabin: CabinController, cockpit: CockpitState) {
    val speed by rememberUpdatedState(state.speedKmh)
    // 경로 안내·현 주행 정보: 1초마다 차량 속도만큼 진행. 정차 중에는 화면을 바꾸지 않는다 (UiAutomator 대기에 영향 없게)
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            cabin.tick(speed)
            if (speed > 0f) {
                cockpit.tripKm += speed / 3600f
                cockpit.tripSeconds += 1
            }
        }
    }
    // 음성 결과 알림은 5초 뒤 사라진다 (명령마다 다시 센다)
    LaunchedEffect(cabin.voiceSeq) {
        if (cabin.voiceResult.isNotEmpty()) {
            delay(5_000)
            cabin.clearVoiceResult()
        }
    }
    // 알림 센터에 남길 것: 주행 제한 시작/해제, 경로 안내 시작/도착, 전화
    var previousRestricted by remember { mutableStateOf<Boolean?>(null) }
    LaunchedEffect(state.restricted) {
        val before = previousRestricted
        if (before != null && before != state.restricted) {
            if (state.restricted) cockpit.notify("주행 중 제한", "영상 · 글자 입력 · 일부 차량 제어가 제한됩니다.")
            else cockpit.notify("주행 제한 해제", "정차했어요. 모든 기능을 쓸 수 있습니다.")
        }
        previousRestricted = state.restricted
    }
    LaunchedEffect(cabin.guiding, cabin.arrived) {
        val dest = cabin.destination ?: return@LaunchedEffect
        if (cabin.guiding) cockpit.notify("경로 안내 시작", "${dest.name} · ${km(dest.distanceKm.toDouble())}")
        else if (cabin.arrived) cockpit.notify("목적지 도착", "${dest.name}에 도착했어요.")
    }
    // 차량 신호 RANGE_REMAINING 이 기준 이하로 내려가면 한 번 알린다 (내비 화면에는 충전소 안내 카드가 뜬다)
    LaunchedEffect(state.lowRange) {
        if (state.lowRange) cockpit.notify("주행 가능 거리 부족", "가까운 충전소를 안내할 수 있어요.")
    }
    LaunchedEffect(cabin.call?.startedAt) {
        cabin.call?.let { cockpit.notify("통화 연결", "${it.name} · 핸즈프리") }
    }
}

// ---------------- 상단 바 (상태 표시 영역) ----------------

@Composable
private fun TopBar(source: String, state: VehicleState, settings: Settings, cabin: CabinController, cockpit: CockpitState, showClock: Boolean) {
    Row(
        Modifier.fillMaxWidth().height(56.dp).padding(start = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        BarIcon(G.SEARCH, "top_search") { cockpit.open(Tab.HOME) }
        Box {
            BarIcon(G.BELL, "top_notifications") {
                cockpit.notificationsOpen = !cockpit.notificationsOpen
                if (cockpit.notificationsOpen) cockpit.unread = 0
            }
            if (cockpit.unread > 0) {
                Text(
                    cockpit.unread.toString(),
                    Modifier
                        .testTag("notification_badge")
                        .align(Alignment.TopEnd)
                        .offset(x = 2.dp, y = (-2).dp)
                        .clip(CircleShape)
                        .background(IviColors.Red)
                        .padding(horizontal = 6.dp),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        Chip(source, IviColors.AccentSoft, Modifier.testTag("source_badge"))
        if (!state.connected) Chip("차량 연결 안 됨", IviColors.Warn, Modifier.testTag("vehicle_disconnected"))
        state.error?.let { Chip(it, IviColors.Warn, Modifier.testTag("vehicle_error")) }
        Spacer(Modifier.weight(1f))
        if (cabin.voiceResult.isNotEmpty()) Chip(cabin.voiceResult, IviColors.AccentSoft, Modifier.testTag("voice_result").widthIn(max = 320.dp))
        if (state.restricted) Chip("주행 중 · 일부 기능 제한", IviColors.Warn, Modifier.testTag("restriction_banner"))
        Glyph(G.SIGNAL, IviColors.TextPrimary, Modifier.size(20.dp))
        Glyph(G.VOLUME, IviColors.TextPrimary, Modifier.size(22.dp))
        // 음성 호출 버튼 (실제 차량의 음성 버튼 자리). 누르면 '듣는 중' 팝업
        Row(
            Modifier
                .testTag("voice_button")
                .height(38.dp)
                .clip(RoundedCornerShape(19.dp))
                .background(Brush.horizontalGradient(TileColors.Assistant))
                .clickable { cockpit.voiceOpen = true }
                .padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Glyph(G.MIC, Color.White, Modifier.size(18.dp))
            Text("AI", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
        Box(Modifier.size(34.dp).clip(CircleShape).background(IviColors.SurfaceHigher), contentAlignment = Alignment.Center) {
            Glyph(G.PROFILE, IviColors.TextSecondary, Modifier.size(22.dp))
        }
        // AAOS 는 시스템 바가 시계를 이미 보여 주므로 앱은 태블릿(Mock)에서만 그린다
        if (showClock) Clock(settings.clock24)
    }
}

@Composable
private fun BarIcon(g: G, tag: String, onClick: () -> Unit) {
    Box(
        Modifier.testTag(tag).size(44.dp).clip(CircleShape).clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Glyph(g, IviColors.TextPrimary, Modifier.size(24.dp)) }
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
    Text(now.format(DateTimeFormatter.ofPattern(pattern, Locale.KOREAN)), Modifier.testTag("status_clock"), fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
}

// ---------------- 알림 패널 ----------------

@Composable
private fun NotificationPanel(cockpit: CockpitState, modifier: Modifier) {
    Panel(modifier.testTag("notification_panel").width(360.dp).fillMaxHeight(0.92f), padding = 16.dp) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("알림", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
            Text(
                "모두 지우기",
                Modifier.testTag("notification_clear").clip(RoundedCornerShape(10.dp)).clickable { cockpit.notices.clear() }.padding(8.dp),
                color = IviColors.AccentSoft,
                fontSize = 14.sp,
            )
        }
        if (cockpit.notices.isEmpty()) {
            Text("새 알림이 없습니다", Modifier.testTag("notification_empty"), color = IviColors.TextSecondary, fontSize = 15.sp)
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(cockpit.notices, key = { _, n -> n.id }) { index, notice ->
                Column(
                    Modifier
                        .testTag("notification_$index")
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .background(IviColors.SurfaceHigh)
                        .padding(12.dp),
                ) {
                    Row {
                        Text(notice.title, Modifier.weight(1f).testTag("notification_${index}_title"), fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                        Text(notice.time.format(DateTimeFormatter.ofPattern("HH:mm")), color = IviColors.TextTertiary, fontSize = 12.sp)
                    }
                    Text(notice.body, color = IviColors.TextSecondary, fontSize = 13.sp)
                }
            }
        }
    }
}

// ---------------- 하단 바 (컨트롤 영역) ----------------

@Composable
private fun BottomBar(state: VehicleState, cockpit: CockpitState, vehicle: VehicleDataSource, setTemperature: (Seat, Float, Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().height(84.dp).padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            BarToggle(G.CAR, "nav_vehicle", cockpit.tab == Tab.VEHICLE, IviColors.AccentSoft) { cockpit.open(Tab.VEHICLE) }
            BarTemperature(Seat.DRIVER, state, state.acOn, "A/C", setTemperature)
            SeatHeatButton(Seat.DRIVER, state, vehicle)
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            AppButton(Tab.CLIMATE, cockpit)
            AppButton(Tab.MEDIA, cockpit)
            AppButton(Tab.PHONE, cockpit)
            AppButton(Tab.HOME, cockpit)
            AppButton(Tab.ASSISTANT, cockpit)
            BarToggle(G.GRID, "nav_apps", cockpit.tab == Tab.APPS, IviColors.TextPrimary) { cockpit.open(Tab.APPS) }
            cockpit.recent?.let { recent ->
                Box(Modifier.width(1.dp).height(36.dp).background(IviColors.Line))
                AppButton(recent, cockpit, tag = "nav_recent")
            }
        }
        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp, Alignment.End)) {
            SeatHeatButton(Seat.PASSENGER, state, vehicle)
            BarTemperature(Seat.PASSENGER, state, cockpit.sync, "SYNC", setTemperature)
        }
    }
}

fun tileColors(tab: Tab) = when (tab) {
    Tab.CLIMATE -> TileColors.Climate
    Tab.MEDIA -> TileColors.Media
    Tab.HOME -> TileColors.Navigation
    Tab.ASSISTANT -> TileColors.Assistant
    Tab.PHONE -> TileColors.Phone
    Tab.RADIO -> TileColors.Radio
    Tab.SETTINGS -> TileColors.Settings
    Tab.VEHICLE, Tab.APPS -> TileColors.Vehicle
}

fun tileGlyph(tab: Tab) = when (tab) {
    Tab.CLIMATE -> G.FAN
    Tab.MEDIA -> G.MUSIC
    Tab.HOME -> G.NAV
    Tab.ASSISTANT -> G.SPARK
    Tab.PHONE -> G.PHONE
    Tab.RADIO -> G.RADIO
    Tab.SETTINGS -> G.GEAR
    Tab.VEHICLE -> G.CAR
    Tab.APPS -> G.GRID
}

@Composable
private fun AppButton(tab: Tab, cockpit: CockpitState, tag: String = tab.tag) {
    val on = cockpit.tab == tab
    Box(
        Modifier
            .testTag(tag)
            .size(58.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(if (on) IviColors.SurfaceHigher else Color.Transparent)
            .clickable { cockpit.open(tab) },
        contentAlignment = Alignment.Center,
    ) { AppTile(tileColors(tab), 44.dp) { Glyph(tileGlyph(tab), Color.White, it) } }
}

@Composable
private fun BarToggle(g: G, tag: String, on: Boolean, onColor: Color, size: Dp = 50.dp, onClick: () -> Unit) {
    Box(
        Modifier
            .testTag(tag)
            .size(size)
            .clip(RoundedCornerShape(16.dp))
            .background(if (on) onColor.copy(alpha = 0.16f) else Color.Transparent)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Glyph(g, if (on) onColor else IviColors.TextPrimary, Modifier.size(28.dp)) }
}

/** 아래 바의 좌석 열선: 누를 때마다 꺼짐 → 2단 → 1단 → 꺼짐. 차량 신호 HVAC_SEAT_TEMPERATURE 를 쓰고, 단계 숫자를 옆에 보여 준다. */
@Composable
private fun SeatHeatButton(seat: Seat, state: VehicleState, vehicle: VehicleDataSource) {
    val level = state.seatHeat(seat)
    val on = level > 0
    Box(
        Modifier
            .testTag("bar_seat_heat_${seat.tag}")
            .size(50.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(if (on) IviColors.Warm.copy(alpha = 0.16f) else Color.Transparent)
            .clickable(enabled = state.hvacAvailable) { vehicle.setSeatHeat(seat, HvacSpec.nextSeatHeat(level)) },
        contentAlignment = Alignment.Center,
    ) {
        Glyph(G.SEAT_HEAT, if (on) IviColors.Warm else IviColors.TextPrimary, Modifier.size(28.dp))
        Text(
            if (on) level.toString() else "",
            Modifier.testTag("bar_seat_heat_${seat.tag}_level").align(Alignment.BottomEnd).padding(end = 5.dp, bottom = 2.dp),
            color = IviColors.Warm,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

/** 아래 바의 좌석 온도: ‹ 22.0° › 와 상태 글자(A/C, SYNC). 실제 차량 신호(HVAC_TEMPERATURE_SET)를 바꾼다. */
@Composable
private fun BarTemperature(seat: Seat, state: VehicleState, flag: Boolean, flagLabel: String, setTemperature: (Seat, Float, Boolean) -> Unit) {
    val celsius = if (seat == Seat.DRIVER) state.driverTempC else state.passengerTempC
    val usable = state.hvacAvailable && celsius != null
    Row(verticalAlignment = Alignment.CenterVertically) {
        Chevron(G.CHEVRON_LEFT, "bar_${seat.tag}_temp_down", usable && celsius!! > HvacSpec.MIN_C, IviColors.Cool) {
            setTemperature(seat, celsius!! - HvacSpec.STEP_C, true)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(72.dp)) {
            Text(tempShort(celsius), Modifier.testTag("bar_${seat.tag}_temp"), fontSize = 25.sp, fontWeight = FontWeight.Medium)
            Text(flagLabel, color = if (flag) IviColors.Green else IviColors.TextTertiary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        }
        Chevron(G.CHEVRON_RIGHT, "bar_${seat.tag}_temp_up", usable && celsius!! < HvacSpec.MAX_C, IviColors.Warm) {
            setTemperature(seat, celsius!! + HvacSpec.STEP_C, true)
        }
    }
}

@Composable
private fun Chevron(g: G, tag: String, enabled: Boolean, color: Color, onClick: () -> Unit) {
    Box(
        Modifier.testTag(tag).size(width = 40.dp, height = 60.dp).clip(RoundedCornerShape(12.dp)).clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Glyph(g, if (enabled) color else IviColors.TextTertiary.copy(alpha = 0.5f), Modifier.size(22.dp)) }
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
            .clip(RoundedCornerShape(22.dp))
            .background(IviColors.SurfaceHigh)
            .border(1.dp, IviColors.Line, RoundedCornerShape(22.dp))
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        AppTile(TileColors.Phone, 52.dp) { Glyph(G.PHONE, Color.White, it) }
        Column(Modifier.weight(1f)) {
            Text(name, Modifier.testTag("phone_call_name"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
            Text(number, color = IviColors.TextSecondary, fontSize = 14.sp)
            Text("통화 중 %02d:%02d".format(seconds / 60, seconds % 60), Modifier.testTag("phone_call_timer"), color = IviColors.Green, fontSize = 15.sp)
        }
        RoundButton("✕", "phone_end", tint = IviColors.Red, size = 64.dp, filled = true, onClick = onEnd)
    }
}

/** 음성 호출 팝업: '어느 좌석에서 듣는 중' + 인식된 문장 대신 누르는 명령 + AI 어시스턴트 대화로 가기. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun VoicePopup(cockpit: CockpitState, onCommand: (Int) -> Unit, onOpenAssistant: () -> Unit, onClose: () -> Unit) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.BottomCenter) {
        Panel(Modifier.fillMaxWidth().testTag("voice_panel"), padding = 16.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                AppTile(TileColors.Assistant, 36.dp) { Glyph(G.SPARK, Color.White, it) }
                Text(
                    "${CabinAssistant.seatName(cockpit.speaker)}에서 듣는 중…",
                    Modifier.clip(RoundedCornerShape(50)).background(IviColors.Accent).padding(horizontal = 12.dp, vertical = 5.dp),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.weight(1f))
                PillButton("대화 열기", "voice_open_assistant", onClick = onOpenAssistant)
                PillButton("닫기", "voice_close", onClick = onClose)
            }
            Label("말하는 대신 아래 문장을 누르면 인식된 것으로 처리합니다")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                VoiceCommands.forEachIndexed { index, text ->
                    Text(
                        "“$text”",
                        Modifier
                            .testTag("voice_cmd_$index")
                            .clip(RoundedCornerShape(14.dp))
                            .background(IviColors.SurfaceHigh)
                            .clickable { onCommand(index) }
                            .padding(horizontal = 16.dp, vertical = 14.dp),
                        fontSize = 16.sp,
                    )
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
            .clip(RoundedCornerShape(22.dp))
            .background(Brush.verticalGradient(listOf(Color(0xFF1A2026), Color(0xFF2B3138)))),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val stroke = 6.dp.toPx()
            val bands = listOf(IviColors.Green to 0.45f, IviColors.Warn to 0.65f, IviColors.Red to 0.85f)
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
        Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Glyph(G.CAMERA, IviColors.TextPrimary, Modifier.size(24.dp))
            Text("후방 카메라 · 주변 안전을 직접 확인하세요", fontSize = 17.sp)
        }
    }
}

/** 설정 화면에서 무드등 이름을 쓸 때. */
fun ambientName(index: Int) = AmbientColors[index % AmbientColors.size]
