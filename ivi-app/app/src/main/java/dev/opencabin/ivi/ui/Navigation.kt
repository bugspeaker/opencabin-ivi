package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.assistant.PlaceCategory
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Destination
import dev.opencabin.ivi.state.Destinations
import dev.opencabin.ivi.vehicle.VehicleState
import java.time.format.DateTimeFormatter

/**
 * 내비게이션 (가상 지도, 실제 지도 데이터가 아니다). 6단계 흐름을 그대로 쓰고 모양만 바꿨다:
 *   찾기(지도 위 검색 카드) → 미리 보기 → 안내 (다음 안내 카드 · 아래 경로 바) → 도착
 * 남은 거리는 차량 속도 신호로 줄어든다. 주행 중에는 글자 입력(검색)을 막고 즐겨찾기·목록은 쓰게 한다.
 */
@Composable
fun NavigationPane(state: VehicleState, cabin: CabinController, cockpit: CockpitState, modifier: Modifier) {
    val dest = cabin.destination
    Box(modifier.clip(RoundedCornerShape(22.dp)).border(1.dp, IviColors.Line, RoundedCornerShape(22.dp))) {
        MapCanvas(routed = dest != null, Modifier.fillMaxSize())
        MapLabels()
        MyLocation(Modifier.align(Alignment.BottomCenter).padding(bottom = 104.dp))

        // 오른쪽 위: 분할/단일 화면 전환, 2D/3D 표시
        Column(Modifier.align(Alignment.TopEnd).padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            RoundIconButton("split_toggle", 48.dp, onClick = { cockpit.split = !cockpit.split }) {
                Glyph(G.SPLIT, if (cockpit.split) IviColors.AccentSoft else IviColors.TextPrimary, it)
            }
            Text(
                if (state.restricted) "3D" else "2D",
                Modifier.size(48.dp).clip(RoundedCornerShape(14.dp)).background(IviColors.SurfaceHigh).padding(top = 13.dp),
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }

        when {
            cabin.guiding && dest != null -> Guidance(state, cabin, dest)
            cabin.arrived && dest != null -> Arrived(dest, Modifier.align(Alignment.Center)) { cabin.stopGuidance() }
            dest != null -> Preview(dest, Modifier.align(Alignment.BottomStart), onStart = { cabin.startGuidance() }, onCancel = { cabin.stopGuidance() })
            else -> Search(state.restricted, cockpit.split, Modifier.align(Alignment.BottomStart)) { cabin.preview(it) }
        }
    }
}

// ---------------- 찾기 ----------------

@Composable
private fun Search(restricted: Boolean, narrow: Boolean, modifier: Modifier, onPick: (Destination) -> Unit) {
    var query by remember { mutableStateOf("") }
    var category by remember { mutableStateOf<PlaceCategory?>(null) }
    Column(
        modifier
            .padding(12.dp)
            .widthIn(max = if (narrow) 300.dp else 380.dp)
            .clip(RoundedCornerShape(20.dp))
            .background(IviColors.Surface.copy(alpha = 0.97f))
            .border(1.dp, IviColors.Line, RoundedCornerShape(20.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // 검색 칸 (주행 중 잠금)
        Row(
            Modifier.fillMaxWidth().height(48.dp).clip(RoundedCornerShape(14.dp)).background(IviColors.SurfaceHigh).padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Glyph(G.SEARCH, IviColors.TextSecondary, Modifier.size(20.dp))
            Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
                BasicTextField(
                    value = query,
                    onValueChange = { query = it; category = null },
                    enabled = !restricted,
                    singleLine = true,
                    textStyle = TextStyle(color = IviColors.TextPrimary, fontSize = 17.sp),
                    cursorBrush = SolidColor(IviColors.Accent),
                    modifier = Modifier.fillMaxWidth().testTag("nav_search"),
                )
                if (query.isEmpty()) Text(if (restricted) "주행 중 검색 제한" else "어디로 갈까요?", color = IviColors.TextTertiary, fontSize = 16.sp)
            }
        }
        if (restricted) {
            Text("주행 중에는 검색할 수 없습니다. 즐겨찾기를 이용하세요", Modifier.testTag("nav_search_locked"), color = IviColors.Warn, fontSize = 13.sp)
        }
        // 즐겨찾기 · 분류 (주행 중에도 쓴다)
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Shortcut(G.HOME, "집", "nav_fav_home") { onPick(Destinations[0]) }
            Shortcut(G.BUILDING, "회사", "nav_fav_work") { onPick(Destinations[1]) }
            Shortcut(G.BOLT, "충전소", "nav_cat_charger", category == PlaceCategory.CHARGER) {
                category = if (category == PlaceCategory.CHARGER) null else PlaceCategory.CHARGER
            }
            Shortcut(G.PARKING, "주차", "nav_cat_parking", category == PlaceCategory.PARKING) {
                category = if (category == PlaceCategory.PARKING) null else PlaceCategory.PARKING
            }
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(IviColors.Line))
        Text(category?.let { "${it.label} · 가까운 순" } ?: "최근 · 추천 장소", color = IviColors.TextSecondary, fontSize = 13.sp)
        // 목록: 6단계 계약대로 태그는 전체 목록의 순번 (nav_dest_N)
        val results = Destinations.withIndex().filter { (_, d) ->
            (query.isBlank() || d.name.contains(query.trim())) && (category == null || d.category == category)
        }.let { list -> if (category != null) list.sortedBy { it.value.distanceKm } else list }
        // 지도가 보이도록 목록 높이를 줄인다 (분할 화면이면 더 작게)
        LazyColumn(Modifier.heightIn(max = if (narrow) 170.dp else 230.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(results, key = { it.index }) { (index, d) ->
                Row(
                    Modifier
                        .testTag("nav_dest_$index")
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(IviColors.SurfaceHigh)
                        .clickable { onPick(d) }
                        .padding(horizontal = 12.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Glyph(placeGlyph(d.category), IviColors.AccentSoft, Modifier.size(18.dp))
                    Column(Modifier.weight(1f)) {
                        Text(d.name, Modifier.testTag("nav_dest_${index}_title"), fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                        Text(d.address, fontSize = 12.sp, color = IviColors.TextSecondary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Text(km(d.distanceKm.toDouble()), fontSize = 13.sp, color = IviColors.TextSecondary)
                }
            }
        }
    }
}

fun placeGlyph(category: PlaceCategory) = when (category) {
    PlaceCategory.HOME -> G.HOME
    PlaceCategory.WORK -> G.BUILDING
    PlaceCategory.CHARGER -> G.BOLT
    PlaceCategory.PARKING -> G.PARKING
    PlaceCategory.STORE -> G.BAG
    else -> G.PIN
}

@Composable
private fun Shortcut(g: G, label: String, tag: String, on: Boolean = false, onClick: () -> Unit) {
    Column(
        Modifier.testTag(tag).clip(RoundedCornerShape(12.dp)).background(if (on) IviColors.Accent.copy(alpha = 0.2f) else IviColors.SurfaceHigh)
            .clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Glyph(g, if (on) IviColors.AccentSoft else IviColors.TextPrimary, Modifier.size(22.dp))
        Text(label, fontSize = 11.sp, color = IviColors.TextSecondary)
    }
}

// ---------------- 미리 보기 · 안내 · 도착 ----------------

@Composable
private fun Preview(dest: Destination, modifier: Modifier, onStart: () -> Unit, onCancel: () -> Unit) {
    Column(
        modifier.padding(12.dp).widthIn(max = 440.dp).clip(RoundedCornerShape(20.dp)).background(IviColors.Surface.copy(alpha = 0.97f))
            .border(1.dp, IviColors.Line, RoundedCornerShape(20.dp)).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Glyph(placeGlyph(dest.category), IviColors.AccentSoft, Modifier.size(22.dp))
            Text(dest.name, Modifier.testTag("nav_dest_name"), fontSize = 24.sp, fontWeight = FontWeight.Bold)
        }
        Text("${dest.address} · ${km(dest.distanceKm.toDouble())}", color = IviColors.TextSecondary, fontSize = 14.sp)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            PillButton("안내 시작", "nav_start", selected = true, onClick = onStart)
            PillButton("취소", "nav_cancel", onClick = onCancel)
        }
    }
}

@Composable
private fun Guidance(state: VehicleState, cabin: CabinController, dest: Destination) {
    val (meters, action) = cabin.nextManeuver()
    Box(Modifier.fillMaxSize()) {
        // 다음 안내 (위 왼쪽)
        Column(
            Modifier.padding(12.dp).clip(RoundedCornerShape(18.dp)).background(IviColors.SurfaceHigh.copy(alpha = 0.97f)).padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Glyph(maneuverGlyph(action), IviColors.TextPrimary, Modifier.size(30.dp))
                Text(if (action == "목적지 부근") action else "${meters}m 앞 $action", Modifier.testTag("nav_maneuver"), fontSize = 21.sp, fontWeight = FontWeight.Bold)
            }
            Text("${dest.name} 방면", color = IviColors.TextSecondary, fontSize = 13.sp)
        }
        // 아래 경로 바: 종료 · 목적지 · 도착 예정 · 남은 거리
        Row(
            Modifier
                .align(Alignment.BottomStart)
                .padding(12.dp)
                .widthIn(max = 460.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(IviColors.SurfaceHigh.copy(alpha = 0.97f))
                .padding(8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            RoundIconButton("nav_stop", 48.dp, background = IviColors.SurfaceHigher, onClick = { cabin.stopGuidance() }) { Glyph(G.CLOSE, IviColors.TextPrimary, it) }
            Column(Modifier.padding(end = 10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Glyph(G.PIN, IviColors.AccentSoft, Modifier.size(15.dp))
                    Text(dest.name, Modifier.testTag("nav_dest_name").padding(start = 4.dp), fontSize = 14.sp, color = IviColors.TextSecondary, maxLines = 1)
                }
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        "도착 " + cabin.eta(state.speedKmh).format(DateTimeFormatter.ofPattern("HH:mm")),
                        Modifier.testTag("nav_eta"),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text("  ·  ", color = IviColors.TextTertiary)
                    Text(km(cabin.remainingKm), Modifier.testTag("nav_remaining"), fontSize = 20.sp, fontWeight = FontWeight.Bold, color = IviColors.AccentSoft)
                }
            }
        }
    }
}

@Composable
private fun Arrived(dest: Destination, modifier: Modifier, onDone: () -> Unit) {
    Panel(modifier.widthIn(max = 380.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.size(56.dp).clip(CircleShape).background(IviColors.Green.copy(alpha = 0.2f)), contentAlignment = Alignment.Center) {
            Glyph(G.PIN, IviColors.Green, Modifier.size(30.dp))
        }
        Text("${dest.name}에 도착했습니다", Modifier.testTag("nav_arrived"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        PillButton("확인", "nav_done", selected = true, onClick = onDone)
    }
}

private fun maneuverGlyph(action: String) = when (action) {
    "우회전", "오른쪽 출구" -> G.TURN_RIGHT
    "목적지 부근" -> G.PIN
    else -> G.NAV
}

// ---------------- 지도 ----------------

@Composable
private fun MyLocation(modifier: Modifier) {
    Box(
        modifier.size(46.dp).clip(CircleShape).background(Color.White).padding(4.dp).clip(CircleShape).background(IviColors.Accent),
        contentAlignment = Alignment.Center,
    ) { Glyph(G.NAV, Color.White, Modifier.size(22.dp).rotate(-45f)) }
}

/** 가짜 도시 지도: 강, 공원, 블록, 큰길, 경로. 고정된 그림이라 화면이 흔들리지 않는다. */
@Composable
fun MapCanvas(routed: Boolean, modifier: Modifier) {
    Canvas(modifier.background(IviColors.MapBase)) {
        val w = size.width
        val h = size.height
        val river = Path().apply {
            moveTo(-w * 0.1f, h * 0.30f); cubicTo(w * 0.2f, h * 0.18f, w * 0.35f, h * 0.10f, w * 0.55f, -h * 0.05f)
            lineTo(w * 0.32f, -h * 0.05f); cubicTo(w * 0.2f, h * 0.05f, w * 0.05f, h * 0.12f, -w * 0.1f, h * 0.16f); close()
        }
        drawPath(river, IviColors.MapWater)
        drawRoundRect(IviColors.MapPark, Offset(w * 0.68f, h * 0.62f), Size(w * 0.26f, h * 0.20f), CornerRadius(24f))
        drawRoundRect(IviColors.MapPark, Offset(w * 0.06f, h * 0.52f), Size(w * 0.16f, h * 0.14f), CornerRadius(24f))
        rotate(-16f) {
            val step = 64.dp.toPx()
            var y = -h * 0.3f
            var row = 0
            while (y < h * 1.3f) {
                var x = -w * 0.3f + (row % 2) * step * 0.3f
                while (x < w * 1.3f) {
                    drawRoundRect(IviColors.MapBlock, Offset(x, y), Size(step * 0.78f, step * 0.62f), CornerRadius(6f))
                    x += step
                }
                y += step * 0.82f
                row++
            }
            var gx = -w * 0.3f
            while (gx < w * 1.3f) {
                drawLine(IviColors.MapRoad, Offset(gx - 6f, -h), Offset(gx - 6f, h * 2), strokeWidth = 2.dp.toPx()); gx += step
            }
        }
        val major = 12.dp.toPx()
        drawLine(IviColors.MapMajor, Offset(w * 0.46f, h * 1.05f), Offset(w * 0.58f, -h * 0.05f), strokeWidth = major)
        drawLine(IviColors.MapMajor, Offset(-w * 0.05f, h * 0.44f), Offset(w * 1.05f, h * 0.30f), strokeWidth = major)
        drawLine(IviColors.MapMajor.copy(alpha = 0.7f), Offset(w * 0.15f, h * 1.05f), Offset(w * 1.05f, h * 0.70f), strokeWidth = 8.dp.toPx())

        if (routed) {
            // 내 위치(아래 가운데)에서 큰길을 따라 올라가 오른쪽으로 꺾는 경로. 앞쪽은 원활(초록), 뒤쪽은 서행(노랑)
            val start = Offset(w * 0.5f, h - 104.dp.toPx() - 23.dp.toPx())
            val turn = Offset(w * 0.545f, h * 0.37f)
            val end = Offset(w * 1.05f, h * 0.30f)
            val routeStroke = Stroke(width = 9.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
            drawPath(Path().apply { moveTo(start.x, start.y); lineTo(turn.x, turn.y); lineTo(end.x, end.y) }, Color(0xFF0B3D1F), style = Stroke(width = 14.dp.toPx(), cap = StrokeCap.Round))
            drawPath(Path().apply { moveTo(start.x, start.y); lineTo(turn.x, turn.y) }, IviColors.Green, style = routeStroke)
            drawPath(Path().apply { moveTo(turn.x, turn.y); lineTo(end.x, end.y) }, Color(0xFFF5C542), style = routeStroke)
            drawCircle(Color.White, 7.dp.toPx(), turn)
        }
        listOf(0.30f to 0.62f, 0.72f to 0.48f, 0.84f to 0.18f, 0.24f to 0.84f).forEachIndexed { i, (x, y) ->
            drawCircle(if (i % 2 == 0) IviColors.Accent else IviColors.Green, 9.dp.toPx(), Offset(w * x, h * y))
            drawCircle(IviColors.MapBase, 4.dp.toPx(), Offset(w * x, h * y))
        }
    }
}

@Composable
private fun MapLabels() {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        listOf("판교역" to (0.60f to 0.22f), "탄천" to (0.12f to 0.16f), "정자공원" to (0.72f to 0.70f), "판교로" to (0.30f to 0.40f)).forEach { (name, pos) ->
            Text(name, Modifier.offset(x = maxWidth * pos.first, y = maxHeight * pos.second), color = IviColors.TextSecondary, fontSize = 12.sp)
        }
        Text(
            "분당구 정자동",
            Modifier.align(Alignment.BottomCenter).padding(bottom = 72.dp).clip(RoundedCornerShape(10.dp))
                .background(IviColors.Background.copy(alpha = 0.8f)).padding(horizontal = 10.dp, vertical = 3.dp),
            fontSize = 13.sp,
        )
    }
}
