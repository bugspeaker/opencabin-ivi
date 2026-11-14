package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Destination
import dev.opencabin.ivi.state.Destinations
import dev.opencabin.ivi.vehicle.VehicleState
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * 내비게이션 (가상 지도, 실제 지도 데이터가 아니다):
 *   찾기 → 미리 보기 → 안내 (다음 안내, 남은 거리, 도착 예정) → 도착
 * 남은 거리는 차량 속도 신호로 줄어든다. 주행 중에는 글자 입력(검색)을 막고 즐겨찾기만 쓰게 한다.
 */
@Composable
fun NavigationScreen(state: VehicleState, cabin: CabinController) {
    val dest = cabin.destination
    when {
        cabin.guiding && dest != null -> Guidance(state, cabin, dest)
        cabin.arrived && dest != null -> Arrived(dest) { cabin.stopGuidance() }
        dest != null -> Preview(dest, onStart = { cabin.startGuidance() }, onCancel = { cabin.stopGuidance() })
        else -> Search(state.restricted) { cabin.preview(it) }
    }
}

@Composable
private fun Search(restricted: Boolean, onPick: (Destination) -> Unit) {
    var query by remember { mutableStateOf("") }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(1.3f).fillMaxHeight()) {
            Label("목적지 검색")
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                enabled = !restricted,
                singleLine = true,
                placeholder = { Text("장소 이름") },
                modifier = Modifier.fillMaxWidth().testTag("nav_search"),
            )
            if (restricted) {
                Text("주행 중에는 검색할 수 없습니다. 즐겨찾기를 이용하세요", Modifier.testTag("nav_search_locked"), color = IviColors.Warn, fontSize = 14.sp)
            }
            val results = Destinations.withIndex().filter { query.isBlank() || it.value.name.contains(query.trim()) }
            LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                items(results, key = { it.index }) { (index, d) ->
                    Row(
                        Modifier
                            .testTag("nav_dest_$index")
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .clickable(enabled = !restricted) { onPick(d) }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(d.name, Modifier.testTag("nav_dest_${index}_title"), fontSize = 17.sp)
                            Text(d.address, fontSize = 12.sp, color = IviColors.TextSecondary)
                        }
                        Text(km(d.km), fontSize = 14.sp, color = IviColors.TextSecondary)
                    }
                }
            }
        }
        Panel(Modifier.weight(1f).fillMaxHeight()) {
            Label("즐겨찾기 (주행 중에도 사용)")
            PillButton("⌂  집", "nav_fav_home", Modifier.fillMaxWidth()) { onPick(Destinations[0]) }
            PillButton("▣  회사", "nav_fav_work", Modifier.fillMaxWidth()) { onPick(Destinations[1]) }
            MiniMap(Modifier.fillMaxWidth().weight(1f).clip(RoundedCornerShape(16.dp)), guiding = false)
        }
    }
}

@Composable
private fun Preview(dest: Destination, onStart: () -> Unit, onCancel: () -> Unit) {
    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        MapView(Modifier.fillMaxWidth().weight(1f), guiding = true)
        Panel {
            Text(dest.name, Modifier.testTag("nav_dest_name"), fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
            Text("${dest.address} · ${km(dest.km)}", color = IviColors.TextSecondary, fontSize = 15.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PillButton("안내 시작", "nav_start", selected = true, onClick = onStart)
                PillButton("취소", "nav_cancel", onClick = onCancel)
            }
        }
    }
}

@Composable
private fun Guidance(state: VehicleState, cabin: CabinController, dest: Destination) {
    val (meters, action) = cabin.nextManeuver()
    Box(Modifier.fillMaxSize()) {
        MapView(Modifier.fillMaxSize().clip(RoundedCornerShape(24.dp)), guiding = true)
        // 다음 안내 (위 왼쪽 떠 있는 카드)
        Column(
            Modifier
                .padding(16.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(IviColors.AquaDeep)
                .padding(horizontal = 20.dp, vertical = 14.dp),
        ) {
            Text(maneuverArrow(action), fontSize = 28.sp)
            Text(if (action == "목적지 부근") action else "${meters}m 앞 $action", Modifier.testTag("nav_maneuver"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        }
        // 남은 거리·도착 예정 (아래 떠 있는 카드)
        Row(
            Modifier
                .align(Alignment.BottomCenter)
                .padding(16.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(18.dp))
                .background(IviColors.Surface)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            Column(Modifier.weight(1f)) {
                Text(dest.name, Modifier.testTag("nav_dest_name"), fontSize = 18.sp, fontWeight = FontWeight.Medium)
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text(km(cabin.remainingKm), Modifier.testTag("nav_remaining"), fontSize = 20.sp, color = IviColors.Aqua)
                    Text("도착 " + cabin.eta(state.speedKmh).format(DateTimeFormatter.ofPattern("HH:mm")), Modifier.testTag("nav_eta"), fontSize = 20.sp)
                }
            }
            PillButton("안내 종료", "nav_stop") { cabin.stopGuidance() }
        }
    }
}

@Composable
private fun Arrived(dest: Destination, onDone: () -> Unit) {
    Panel(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically)) {
        Text("🏁", fontSize = 40.sp)
        Text("${dest.name}에 도착했습니다", Modifier.testTag("nav_arrived"), fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
        PillButton("확인", "nav_done", onClick = onDone)
    }
}

/** 지도 그림: 도로 격자 + 경로 + 내 차 위치. */
@Composable
private fun MapView(modifier: Modifier, guiding: Boolean) {
    Canvas(modifier.background(IviColors.Map)) {
        val w = size.width
        val h = size.height
        val road = 10.dp.toPx()
        listOf(0.2f, 0.45f, 0.75f).forEach { drawLine(IviColors.Road, Offset(0f, h * it), Offset(w, h * it), road) }
        listOf(0.15f, 0.4f, 0.65f, 0.9f).forEach { drawLine(IviColors.Road, Offset(w * it, 0f), Offset(w * it, h), road) }
        drawLine(IviColors.Road, Offset(0f, h), Offset(w, 0f), road * 1.4f)
        if (guiding) {
            val route = Path().apply {
                moveTo(w * 0.4f, h); lineTo(w * 0.4f, h * 0.75f); lineTo(w * 0.65f, h * 0.75f)
                lineTo(w * 0.65f, h * 0.45f); lineTo(w * 0.9f, h * 0.45f); lineTo(w * 0.9f, h * 0.2f)
            }
            drawPath(route, IviColors.Aqua, style = Stroke(road * 0.8f, cap = StrokeCap.Round))
            drawCircle(IviColors.Warn, radius = 10.dp.toPx(), center = Offset(w * 0.9f, h * 0.2f))
        }
        drawCircle(IviColors.TextPrimary, radius = 13.dp.toPx(), center = Offset(w * 0.4f, h * 0.88f))
        drawCircle(IviColors.Aqua, radius = 9.dp.toPx(), center = Offset(w * 0.4f, h * 0.88f))
    }
}

private fun maneuverArrow(action: String) = when (action) {
    "우회전", "오른쪽 출구" -> "↱"
    "좌회전" -> "↰"
    "목적지 부근" -> "◎"
    else -> "↑"
}

fun km(value: Double) = String.format(Locale.US, "%.1f km", value)
