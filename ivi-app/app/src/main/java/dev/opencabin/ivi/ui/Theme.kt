package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

/*
 * 공통 색·부품. 양산 IVI 의 일반적인 방향을 따른다 (docs/phase5-design.md):
 * 거의 검정 바탕 + 아쿠아 블루 강조, 큰 터치 영역(76dp), 주의는 주황.
 * 제조사 로고·제품명·전용 글꼴·아이콘은 쓰지 않는다.
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
    val Danger = Color(0xFFFF5A5F)
    val Ok = Color(0xFF4CD39B)
    val Cool = Color(0xFF4DA3FF)
    val Warm = Color(0xFFFF7A59)
    val Map = Color(0xFF0C141C)
    val Road = Color(0xFF1E2A36)
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

@Composable
fun Panel(
    modifier: Modifier = Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.spacedBy(10.dp),
    padding: Dp = 22.dp,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .clip(RoundedCornerShape(24.dp))
            .background(IviColors.Surface)
            .border(1.dp, IviColors.Line, RoundedCornerShape(24.dp))
            .padding(padding),
        verticalArrangement = verticalArrangement,
        content = content,
    )
}

@Composable
fun Label(text: String, modifier: Modifier = Modifier) =
    Text(text, modifier, color = IviColors.TextSecondary, fontSize = 15.sp, fontWeight = FontWeight.Medium)

@Composable
fun Chip(text: String, color: Color, modifier: Modifier = Modifier) {
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

/** 원형 버튼. 차량용 최소 터치 영역 76dp (1단계에서 겹침 결함을 본 SystemUI 버튼과 같은 크기). */
@Composable
fun RoundButton(
    text: String,
    tag: String,
    enabled: Boolean = true,
    tint: Color = IviColors.Aqua,
    size: Dp = 76.dp,
    filled: Boolean = false,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.testTag(tag).size(size),
        shape = CircleShape,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (filled) tint else tint.copy(alpha = 0.18f),
            contentColor = if (filled) IviColors.Background else tint,
            disabledContainerColor = IviColors.SurfaceHigh,
            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.4f),
        ),
    ) { Text(text, fontSize = if (size >= 64.dp) 28.sp else 20.sp) }
}

/** 글자 버튼 (높이 56dp). selected 면 강조색. */
@Composable
fun PillButton(
    text: String,
    tag: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    selected: Boolean = false,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.testTag(tag).height(56.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (selected) IviColors.Aqua else IviColors.SurfaceHigh,
            contentColor = if (selected) IviColors.Background else IviColors.TextPrimary,
            disabledContainerColor = IviColors.SurfaceHigh.copy(alpha = 0.5f),
            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.5f),
        ),
    ) { Text(text, fontSize = 16.sp, maxLines = 1) }
}

/** 설정 한 줄: 이름 + 스위치. 스위치의 checked 를 Appium 이 읽는다. */
@Composable
fun ToggleRow(label: String, tag: String, checked: Boolean, onToggle: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().height(56.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 17.sp, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = onToggle,
            modifier = Modifier.testTag(tag),
            colors = SwitchDefaults.colors(checkedTrackColor = IviColors.Aqua, checkedThumbColor = IviColors.Background),
        )
    }
}

/** 설정 한 줄: 이름 + − 값 + (값은 tag_value, 버튼은 tag_down / tag_up). */
@Composable
fun StepperRow(label: String, tag: String, value: String, canDecrease: Boolean, canIncrease: Boolean, onDecrease: () -> Unit, onIncrease: () -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 17.sp, modifier = Modifier.weight(1f))
        RoundButton("−", "${tag}_down", canDecrease, size = 56.dp, onClick = onDecrease)
        Text(value, Modifier.testTag("${tag}_value").width(64.dp).padding(horizontal = 8.dp), fontSize = 20.sp, fontWeight = FontWeight.Medium,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center)
        RoundButton("+", "${tag}_up", canIncrease, size = 56.dp, onClick = onIncrease)
    }
}

@Composable
fun Dot(color: Color, size: Dp = 8.dp) {
    Spacer(Modifier.size(size).clip(CircleShape).background(color))
}

fun tempText(celsius: Float?) = celsius?.let { String.format(Locale.US, "%.1f°C", it) } ?: "--"
