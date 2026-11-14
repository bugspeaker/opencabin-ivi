package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.vehicle.Gear
import dev.opencabin.ivi.vehicle.VehicleState
import java.util.Locale

/*
 * 주행 정보 화면 (왼쪽, 항상 보임). 공개된 양산 화면의 구성:
 *   속도 · 변속 위치 · 운전자 보조 표시 · 3D 주행 뷰(주변 차선·차량) · 변속 표시(P R N D) · 유틸리티 위젯(현 주행 정보 등)
 * 주행 뷰는 실제 센서 대신 속도·기어 신호로 그리는 연출이다 (주변 차량 위치는 고정). 애니메이션은 쓰지 않는다.
 */

/** 운전자 보조(차로 유지) 표시를 켜는 조건. 화면 연출용 (실제 ADAS 신호가 아니다). */
fun adasActive(state: VehicleState) = state.gear == Gear.DRIVE && state.speedKmh >= 30f

@Composable
fun Cluster(state: VehicleState, mph: Boolean, cabin: CabinController, cockpit: CockpitState, modifier: Modifier) {
    val (speed, unit) = speedDisplay(state.speedKmh, mph)
    Column(modifier.padding(start = 20.dp, top = 10.dp, end = 12.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.Top) {
            Column {
                Text(
                    speed,
                    Modifier.testTag("speed_value"),
                    fontSize = 64.sp,
                    fontWeight = FontWeight.SemiBold,
                    lineHeight = 64.sp,
                )
                Text(unit, Modifier.testTag("speed_unit"), color = IviColors.TextSecondary, fontSize = 16.sp)
            }
            Spacer(Modifier.weight(1f))
            Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    state.gear.label,
                    fontSize = 34.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (state.gear == Gear.REVERSE) IviColors.Red else IviColors.TextPrimary,
                )
                Text(
                    if (state.connected) "READY" else "NO SIGNAL",
                    color = if (state.connected) IviColors.Green else IviColors.Warn,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        AdasRow(state)
        // 경로 안내 중이면 주행 정보에도 목적지와 남은 거리를 보여 준다 (앱 화면이 다른 앱이어도 보이게)
        val dest = cabin.destination
        if (cabin.guiding && dest != null) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Glyph(G.NAV, IviColors.AccentSoft, Modifier.size(16.dp))
                Text("${dest.name}까지 ${km(cabin.remainingKm)}", Modifier.testTag("cluster_route"), color = IviColors.AccentSoft, fontSize = 14.sp, maxLines = 1)
            }
        }
        DrivingView(state, Modifier.weight(1f).fillMaxWidth())
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) { GearSelector(state.gear) }
        UtilityWidget(cabin, cockpit)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(7.dp).clip(CircleShape).background(if (state.connected) IviColors.Green else IviColors.Warn))
            Text(
                if (state.connected) "  차량 신호 수신 중" else "  차량 신호 없음",
                color = IviColors.TextSecondary,
                fontSize = 13.sp,
                modifier = Modifier.weight(1f),
            )
            Text(
                when {
                    state.restricted -> "주행 중"
                    state.gear == Gear.PARK -> "정차 중"
                    state.gear == Gear.REVERSE -> "후진"
                    else -> "대기"
                },
                color = IviColors.TextSecondary,
                fontSize = 13.sp,
            )
        }
    }
}

@Composable
private fun AdasRow(state: VehicleState) {
    val on = adasActive(state)
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Glyph(G.LANE, if (on) IviColors.Green else IviColors.TextTertiary, Modifier.size(22.dp))
        Text(
            if (on) "차로 유지 보조 작동" else "차로 유지 보조 대기",
            Modifier.testTag("adas_state"),
            color = if (on) IviColors.Green else IviColors.TextTertiary,
            fontSize = 13.sp,
        )
    }
}

/** 변속 위치. 지금 기어 칸에 테스트 태그(gear_value)가 붙는다 (5단계 계약 유지). */
@Composable
private fun GearSelector(current: Gear) {
    Row(
        Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(IviColors.Surface)
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        listOf(Gear.PARK, Gear.REVERSE, Gear.NEUTRAL, Gear.DRIVE).forEach { gear ->
            val on = gear == current
            val color = if (gear == Gear.REVERSE) IviColors.Red else IviColors.TextPrimary
            Box(
                Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .then(if (on) Modifier.border(2.dp, color, RoundedCornerShape(8.dp)) else Modifier),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    gear.label,
                    if (on) Modifier.testTag("gear_value") else Modifier,
                    fontSize = 20.sp,
                    fontWeight = if (on) FontWeight.Bold else FontWeight.Normal,
                    color = if (on) color else IviColors.TextTertiary,
                )
            }
        }
        if (current == Gear.UNKNOWN) {
            Text(current.label, Modifier.testTag("gear_value").padding(horizontal = 8.dp), color = IviColors.Warn, fontSize = 20.sp)
        }
    }
}

/** 원근 도로 + 내 차 + 주변 차. 주행(D)이면 차선·주변 차, 후진(R)이면 뒤쪽 붉은 빛, 정차(P)면 내 차만 크게. */
@Composable
private fun DrivingView(state: VehicleState, modifier: Modifier) {
    val moving = state.speedKmh > 0f
    val adas = adasActive(state)
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val cx = w / 2
        val horizonY = h * 0.04f
        val bottomY = h * 0.98f
        val laneBottom = w * 0.30f

        fun xAt(lane: Float, t: Float) = cx + lane * laneBottom * (1f - t * 0.88f)
        fun yAt(t: Float) = bottomY - (bottomY - horizonY) * t

        drawRect(Brush.verticalGradient(listOf(Color.Transparent, IviColors.Surface.copy(alpha = 0.6f))))

        if (state.gear != Gear.PARK) {
            // 차선: 바깥 실선, 안쪽 점선. 차로 유지 보조가 작동하면 내 차로 경계를 초록으로
            listOf(-1.5f, -0.5f, 0.5f, 1.5f).forEach { lane ->
                val ego = lane == -0.5f || lane == 0.5f
                val color = when {
                    ego && adas -> IviColors.Green
                    else -> Color.White.copy(alpha = if (ego) 0.55f else 0.28f)
                }
                drawLine(
                    color,
                    Offset(xAt(lane, 0f), yAt(0f)),
                    Offset(xAt(lane, 0.95f), yAt(0.95f)),
                    strokeWidth = if (ego) 4.dp.toPx() else 3.dp.toPx(),
                    pathEffect = if (ego) null else PathEffect.dashPathEffect(floatArrayOf(18.dp.toPx(), 16.dp.toPx())),
                )
            }
        }

        if (state.gear == Gear.REVERSE) {
            drawRect(
                Brush.verticalGradient(listOf(Color.Transparent, IviColors.Red.copy(alpha = 0.35f)), startY = h * 0.55f, endY = h),
                topLeft = Offset(0f, h * 0.55f),
                size = Size(w, h * 0.45f),
            )
        }

        if (moving && state.gear == Gear.DRIVE) {
            // 주변 차량 (차로, 거리)
            listOf(-1f to 0.55f, 0f to 0.40f, 1f to 0.28f, -1f to 0.18f).forEach { (lane, t) ->
                car(xAt(lane, t), yAt(t), (1f - t * 0.88f) * w * 0.14f, Color(0xFF7D8B93), Color(0xFF59656C))
            }
        }

        // 내 차 (CarArt.kt): 정차(P)면 옆모습을 크게, 주행·후진이면 위에서 본 모습
        val body = Color(0xFFE9ECF0)
        val shade = Color(0xFFA9B0B9)
        if (state.gear == Gear.PARK) {
            val length = minOf(w * 0.88f, h * 1.9f)
            val ground = h * 0.5f + length * 0.19f
            drawCircle(Brush.radialGradient(listOf(IviColors.Accent.copy(alpha = 0.16f), Color.Transparent), center = Offset(cx, ground - length * 0.15f), radius = w * 0.45f), w * 0.45f, Offset(cx, ground - length * 0.15f))
            ioniq3Side(cx, ground, length, body, shade)
        } else {
            val length = w * 0.15f * 1.9f
            ioniq3Top(cx, yAt(0.08f) - length / 2, length, body, shade, braking = state.gear == Gear.REVERSE)
        }
    }
}

/** 위에서 본 차. (x, y) 는 차 중심, width 는 차 폭. */
private fun DrawScope.car(x: Float, y: Float, width: Float, body: Color, shade: Color) {
    val length = width * 1.9f
    val left = x - width / 2
    val top = y - length / 2
    drawRoundRect(Color.Black.copy(alpha = 0.35f), Offset(left + width * 0.06f, top + length * 0.04f), Size(width, length), CornerRadius(width * 0.32f))
    drawRoundRect(Brush.horizontalGradient(listOf(shade, body, shade), startX = left, endX = left + width), Offset(left, top), Size(width, length), CornerRadius(width * 0.32f))
    // 앞 유리 · 뒤 유리 · 지붕
    drawRoundRect(Color(0xFF1C232A), Offset(left + width * 0.12f, top + length * 0.24f), Size(width * 0.76f, length * 0.16f), CornerRadius(width * 0.12f))
    drawRoundRect(Color(0xFF1C232A), Offset(left + width * 0.14f, top + length * 0.70f), Size(width * 0.72f, length * 0.12f), CornerRadius(width * 0.10f))
    drawRoundRect(body.copy(alpha = 0.9f), Offset(left + width * 0.16f, top + length * 0.41f), Size(width * 0.68f, length * 0.28f), CornerRadius(width * 0.10f))
}

/** 유틸리티 위젯: 누를 때마다 다음 쪽 (현 주행 정보 → 경로 → 타이어 공기압). */
@Composable
private fun UtilityWidget(cabin: CabinController, cockpit: CockpitState) {
    val pages = 3
    Column(
        Modifier
            .testTag("utility_widget")
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(IviColors.Surface)
            .clickable { cockpit.widgetPage = (cockpit.widgetPage + 1) % pages }
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                when (cockpit.widgetPage) { 0 -> "현 주행 정보"; 1 -> "경로"; else -> "타이어 공기압" },
                Modifier.weight(1f).testTag("utility_title"),
                fontSize = 13.sp,
                color = IviColors.TextSecondary,
                fontWeight = FontWeight.Medium,
            )
            repeat(pages) { i ->
                Box(Modifier.padding(start = 4.dp).size(if (i == cockpit.widgetPage) 14.dp else 5.dp, 5.dp).clip(CircleShape)
                    .background(if (i == cockpit.widgetPage) IviColors.TextPrimary else IviColors.TextTertiary))
            }
        }
        when (cockpit.widgetPage) {
            0 -> Row(Modifier.fillMaxWidth()) {
                Metric("거리", String.format(Locale.US, "%.1f", cockpit.tripKm), "km", "trip_distance", Modifier.weight(1f))
                Metric("시간", duration(cockpit.tripSeconds), "", "trip_time", Modifier.weight(1f))
                Metric("평균", String.format(Locale.US, "%.0f", cockpit.averageKmh()), "km/h", "trip_avg_speed", Modifier.weight(1f))
            }
            1 -> {
                val dest = cabin.destination
                if (dest == null || !cabin.guiding) {
                    Text("경로 안내 없음", Modifier.height(40.dp), color = IviColors.TextTertiary, fontSize = 15.sp)
                } else {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Glyph(G.PIN, IviColors.AccentSoft, Modifier.size(20.dp))
                        Text(" ${dest.name}", Modifier.weight(1f), fontSize = 16.sp, maxLines = 1)
                        Text(km(cabin.remainingKm), fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
            else -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                listOf("앞 왼쪽" to 36, "앞 오른쪽" to 36, "뒤 왼쪽" to 35, "뒤 오른쪽" to 35).forEach { (where, psi) ->
                    Metric(where, psi.toString(), "psi", null, Modifier.width(60.dp))
                }
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String, unit: String, tag: String?, modifier: Modifier) {
    Column(modifier) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(value, if (tag != null) Modifier.testTag(tag) else Modifier, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            if (unit.isNotEmpty()) Text(" $unit", color = IviColors.TextSecondary, fontSize = 11.sp, modifier = Modifier.padding(bottom = 3.dp))
        }
        Text(label, color = IviColors.TextTertiary, fontSize = 11.sp)
    }
}

private fun duration(seconds: Long) =
    if (seconds < 3600) String.format(Locale.US, "%d:%02d", seconds / 60, seconds % 60)
    else String.format(Locale.US, "%d:%02d:%02d", seconds / 3600, seconds / 60 % 60, seconds % 60)
