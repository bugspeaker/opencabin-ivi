package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState

/** 공조: 좌석별 설정 온도. 값은 차량 신호(HVAC_TEMPERATURE_SET)에서 오고, 버튼은 차량 신호를 쓴다. */
@Composable
fun ClimateScreen(state: VehicleState, onSetTemperature: (Seat, Float) -> Unit) {
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
    Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(IviColors.Line)) {
        Box(
            Modifier
                .fillMaxWidth(ratio.coerceAtLeast(0.02f))
                .fillMaxHeight()
                .background(Brush.horizontalGradient(listOf(IviColors.Cool, IviColors.Warm))),
        )
    }
}
