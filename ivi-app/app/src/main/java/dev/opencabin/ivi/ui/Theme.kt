package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

/*
 * 7단계 디자인 (docs/phase7-pleos.md): 차세대 양산 IVI(Pleos Connect) 공개 화면의 톤을 따른다.
 *   - 거의 검정 바탕 위에 둥근 회색 카드, 파란 강조색. 공조 화살표는 파랑(내림)·빨강(올림), A/C·SYNC·READY 같은 상태 글자는 초록
 *   - 앱 아이콘은 색 타일 + 단순한 흰 기호 (기호는 직접 그린다: Glyphs.kt)
 * 제조사 로고·제품명·전용 글꼴·아이콘 파일은 쓰지 않는다.
 */
object IviColors {
    val Background = Color(0xFF0A0B0D)
    val Surface = Color(0xFF17191D)
    val SurfaceHigh = Color(0xFF22252B)
    val SurfaceHigher = Color(0xFF2C3037)
    val Line = Color(0xFF2A2E35)
    val Accent = Color(0xFF2F8CFF)
    val AccentSoft = Color(0xFF5AB0FF)
    val AccentDeep = Color(0xFF123A6B)
    val TextPrimary = Color(0xFFF2F4F7)
    val TextSecondary = Color(0xFF8C939D)
    val TextTertiary = Color(0xFF5D636C)
    val Green = Color(0xFF3DD68C)
    val Warn = Color(0xFFFFB547)
    val Red = Color(0xFFFF4D4F)
    val Cool = Color(0xFF3D8BFF)
    val Warm = Color(0xFFFF5A4E)
    val MapBase = Color(0xFF15181C)
    val MapBlock = Color(0xFF1F2328)
    val MapRoad = Color(0xFF2E333A)
    val MapMajor = Color(0xFF454B55)
    val MapWater = Color(0xFF15253A)
    val MapPark = Color(0xFF19281F)

    // 5·6단계 이름 (라디오·전화·설정·영상 화면이 쓴다)
    val Aqua get() = Accent
    val AquaDeep get() = AccentDeep
    val Ok get() = Green
    val Danger get() = Red
}

/** 앱 타일 색 (아래 바·앱 목록에서 같은 앱은 같은 색). */
object TileColors {
    val Climate = listOf(Color(0xFF5B6068), Color(0xFF41454C))
    val Media = listOf(Color(0xFFA35BFF), Color(0xFF6E3CF0))
    val Navigation = listOf(Color(0xFF4BA3FF), Color(0xFF1F6FEB))
    val Assistant = listOf(Color(0xFF2ED3F0), Color(0xFF6C5CFF))
    val Vehicle = listOf(Color(0xFF3A3F47), Color(0xFF2A2E35))
    val Video = listOf(Color(0xFFFF6A8B), Color(0xFFE6337A))
    val Phone = listOf(Color(0xFF3CD3A0), Color(0xFF1FA77A))
    val Radio = listOf(Color(0xFFFF6FB5), Color(0xFFE23A8C))
    val Settings = listOf(Color(0xFF8A9099), Color(0xFF5B6068))
    val Market = listOf(Color(0xFFFFC44D), Color(0xFFF08A24))
}

@Composable
fun IviTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = IviColors.Accent,
            onPrimary = Color.White,
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

/** 앱 화면의 카드. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.spacedBy(10.dp),
    padding: Dp = 18.dp,
    horizontalAlignment: Alignment.Horizontal = Alignment.Start,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .clip(RoundedCornerShape(22.dp))
            .background(IviColors.Surface)
            .border(1.dp, IviColors.Line, RoundedCornerShape(22.dp))
            .padding(padding),
        verticalArrangement = verticalArrangement,
        horizontalAlignment = horizontalAlignment,
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
            .padding(horizontal = 12.dp, vertical = 4.dp),
        color = color,
        fontSize = 14.sp,
        fontWeight = FontWeight.Medium,
        maxLines = 1,
    )
}

/** 원형 버튼. 차량용 터치 영역 (기본 76dp, 1단계에서 겹침 결함을 본 SystemUI 버튼과 같은 크기). */
@Composable
fun RoundButton(
    text: String,
    tag: String,
    enabled: Boolean = true,
    tint: Color = IviColors.Accent,
    size: Dp = 76.dp,
    filled: Boolean = false,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.testTag(tag).size(size),
        shape = CircleShape,
        contentPadding = PaddingValues(0.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (filled) tint else tint.copy(alpha = 0.18f),
            contentColor = if (filled) Color.White else tint,
            disabledContainerColor = IviColors.SurfaceHigh,
            disabledContentColor = IviColors.TextSecondary.copy(alpha = 0.4f),
        ),
    ) { Text(text, fontSize = if (size >= 64.dp) 28.sp else 20.sp) }
}

/** 글자 버튼 (높이 52dp). selected 면 강조색. */
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
        modifier = modifier.testTag(tag).height(52.dp),
        shape = RoundedCornerShape(14.dp),
        contentPadding = PaddingValues(horizontal = 16.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (selected) IviColors.Accent else IviColors.SurfaceHigh,
            contentColor = IviColors.TextPrimary,
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
            colors = SwitchDefaults.colors(checkedTrackColor = IviColors.Accent, checkedThumbColor = Color.White),
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
            textAlign = TextAlign.Center)
        RoundButton("+", "${tag}_up", canIncrease, size = 56.dp, onClick = onIncrease)
    }
}

@Composable
fun Dot(color: Color, size: Dp = 8.dp) {
    Spacer(Modifier.size(size).clip(CircleShape).background(color))
}

/** 색 타일 위의 흰 기호 (앱 아이콘). */
@Composable
fun AppTile(colors: List<Color>, size: Dp, modifier: Modifier = Modifier, glyph: @Composable (Modifier) -> Unit) {
    Box(
        modifier
            .size(size)
            .clip(RoundedCornerShape(size * 0.28f))
            .background(Brush.linearGradient(colors)),
        contentAlignment = Alignment.Center,
    ) { glyph(Modifier.size(size * 0.56f)) }
}

/** 둥근 네모 기호 버튼 (지도 위 버튼, 닫기 등). */
@Composable
fun RoundIconButton(
    tag: String?,
    size: Dp = 48.dp,
    enabled: Boolean = true,
    background: Color = IviColors.SurfaceHigh,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
    glyph: @Composable (Modifier) -> Unit,
) {
    Box(
        (if (tag != null) modifier.testTag(tag) else modifier)
            .size(size)
            .clip(RoundedCornerShape(size * 0.3f))
            .background(background)
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { glyph(Modifier.size(size * 0.5f)) }
}

/** 테두리가 있는 토글 모양. */
fun Modifier.outlined(on: Boolean = false, radius: Dp = 14.dp) =
    this.clip(RoundedCornerShape(radius))
        .background(if (on) IviColors.Accent.copy(alpha = 0.18f) else IviColors.SurfaceHigh)
        .border(1.dp, if (on) IviColors.Accent else IviColors.Line, RoundedCornerShape(radius))

fun tempText(celsius: Float?) = celsius?.let { String.format(Locale.US, "%.1f°C", it) } ?: "--"

fun tempShort(celsius: Float?) = celsius?.let { String.format(Locale.US, "%.1f°", it) } ?: "--"

fun kmText(km: Float) = String.format(Locale.US, "%.1fkm", km)

/** 6단계 내비 표시 형식 ("12.4 km"). 테스트가 앞의 숫자를 읽는다. */
fun km(value: Double) = String.format(Locale.US, "%.1f km", value)
