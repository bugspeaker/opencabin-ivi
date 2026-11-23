package dev.opencabin.ivi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.assistant.CabinAssistant
import dev.opencabin.ivi.assistant.Place
import dev.opencabin.ivi.vehicle.Seat
import dev.opencabin.ivi.vehicle.VehicleState
import java.time.format.DateTimeFormatter
import java.util.Locale

/*
 * AI 어시스턴트 (차량 음성 비서의 대화 화면을 본뜸).
 *   - 위: 지금 '어느 좌석에서 듣는 중' 인지 (Zone). 음성 인식 대신 좌석을 골라 말한 사람을 정한다
 *   - 가운데: 대화 내역. 목적지 후보는 번호 카드로 보여 주고 누르면 안내를 시작한다
 *   - 아래: 추천 명령(음성 대신 누른다) + 글자 입력. 주행 중에는 글자 입력(키보드)을 막는다
 * 말 → 동작 규칙은 assistant/CabinAssistant.kt (JVM 단위 테스트로 검증).
 */

val AssistantSuggestions = listOf(
    "22도로 맞춰줘",
    "나 더워",
    "에어컨 켜고 음악 틀어줘",
    "판교 가자",
    "엄마에게 전화해줘",
    "사이드 미러 접어줘",
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun AssistantScreen(state: VehicleState, cockpit: CockpitState, onAsk: (String) -> Unit, onChoose: (Place) -> Unit) {
    LaunchedEffect(Unit) {
        if (cockpit.chat.isEmpty()) cockpit.say(false, "무엇을 도와드릴까요? 아래 추천 명령을 누르거나 직접 입력해 보세요.", null)
    }

    fun send(text: String) {
        if (text.isNotBlank()) onAsk(text.trim())
    }

    Panel(Modifier.fillMaxSize().padding(bottom = 4.dp), padding = 0.dp, verticalArrangement = Arrangement.Top) {
        // 머리: 이름 · 듣는 좌석
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            AppTile(TileColors.Assistant, 30.dp) { Glyph(G.SPARK, Color.White, it) }
            Text("AI 어시스턴트", fontSize = 17.sp, fontWeight = FontWeight.Bold)
            // 좁은 화면(폭 1000dp 미만)에서는 뺀다. 폴드 가로(780dp)에서 '대화 / 내역' 두 줄로 꺾였다 (2026-11-23)
            if (LocalScreenSize.current.compactWidth) Box(Modifier.weight(1f))
            else Text("|  대화 내역", color = IviColors.TextSecondary, fontSize = 15.sp, modifier = Modifier.weight(1f))
            Text(
                "${CabinAssistant.seatName(cockpit.speaker)}에서 듣는 중…",
                Modifier.testTag("assistant_listening").clip(RoundedCornerShape(50)).background(IviColors.Accent).padding(horizontal = 12.dp, vertical = 5.dp),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Row(Modifier.clip(RoundedCornerShape(12.dp)).background(IviColors.SurfaceHigh).padding(3.dp)) {
                Seat.entries.forEach { seat ->
                    val on = cockpit.speaker == seat
                    Text(
                        CabinAssistant.seatName(seat),
                        Modifier
                            .testTag("assistant_zone_${seat.tag}")
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (on) IviColors.SurfaceHigher else Color.Transparent)
                            .clickable { cockpit.speaker = seat }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        fontSize = 14.sp,
                        color = if (on) IviColors.TextPrimary else IviColors.TextSecondary,
                    )
                }
            }
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(IviColors.Line))

        // 대화
        val listState = rememberLazyListState()
        // 마지막 말의 '시작'으로 내린다. 끝으로 내리면 낮은 화면(AAOS 1024x768)에서 후보 카드가 대답 글을 밀어 올려
        // 대답이 화면 밖으로 나간다 (7단계 회귀에서 발견) → 후보 카드는 한 줄로 작게 그려 대답과 같이 보이게 한다.
        // 더 낮은 화면(높이 600dp 미만)에서는 한 줄 카드 세 장도 다 들어가지 않는다. 폴드 가로(513dp)에서 세 번째 카드가
        // 10px 만 보였다 (2026-11-23) → 이때는 후보를 가로로 늘어놓는다
        val short = LocalScreenSize.current.compactHeight
        LaunchedEffect(cockpit.chat.size) { if (cockpit.chat.isNotEmpty()) listState.scrollToItem(cockpit.chat.lastIndex) }
        val lastReply = cockpit.chat.indexOfLast { !it.fromUser }
        LazyColumn(
            Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp),
            state = listState,
            verticalArrangement = Arrangement.spacedBy(10.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = if (short) 8.dp else 12.dp),
        ) {
            itemsIndexed(cockpit.chat, key = { _, m -> m.id }) { index, message ->
                if (message.fromUser) UserBubble(message) else AssistantBubble(message, index == lastReply, short, onChoose)
            }
        }

        // 추천 명령 + 입력
        Column(Modifier.fillMaxWidth().background(IviColors.SurfaceHigh.copy(alpha = 0.5f)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                AssistantSuggestions.forEachIndexed { i, text ->
                    Text(
                        text,
                        Modifier
                            .testTag("assistant_chip_$i")
                            .clip(RoundedCornerShape(50))
                            .border(1.dp, IviColors.Line, RoundedCornerShape(50))
                            .clickable { send(text) }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                        fontSize = 14.sp,
                    )
                }
            }
            var input by remember { mutableStateOf("") }
            val typing = !state.restricted
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(
                    Modifier.weight(1f).height(48.dp).clip(RoundedCornerShape(14.dp)).background(IviColors.Background).padding(horizontal = 14.dp),
                    contentAlignment = Alignment.CenterStart,
                ) {
                    BasicTextField(
                        value = input,
                        onValueChange = { input = it },
                        enabled = typing,
                        singleLine = true,
                        textStyle = TextStyle(color = IviColors.TextPrimary, fontSize = 16.sp),
                        cursorBrush = SolidColor(IviColors.Accent),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = { send(input); input = "" }),
                        modifier = Modifier.testTag("assistant_input").fillMaxWidth(),
                    )
                    if (input.isEmpty()) {
                        Text(
                            if (typing) "말하듯이 입력해 보세요" else "주행 중에는 입력할 수 없습니다. 아래 추천 명령을 눌러 주세요",
                            Modifier.testTag(if (typing) "assistant_hint" else "assistant_input_locked"),
                            color = if (typing) IviColors.TextTertiary else IviColors.Warn,
                            fontSize = 14.sp,
                        )
                    }
                }
                Box(
                    Modifier
                        .testTag("assistant_send")
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(if (typing && input.isNotBlank()) Brush.linearGradient(TileColors.Assistant) else SolidColor(IviColors.SurfaceHigher))
                        .clickable(enabled = typing && input.isNotBlank()) { send(input); input = "" },
                    contentAlignment = Alignment.Center,
                ) { Glyph(G.NAV, Color.White, Modifier.size(22.dp)) }
            }
        }
    }
}

private val timeFormat = DateTimeFormatter.ofPattern("a h:mm", Locale.KOREAN)

@Composable
private fun UserBubble(message: ChatMessage) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.Bottom) {
        Column(horizontalAlignment = Alignment.End, modifier = Modifier.padding(end = 8.dp)) {
            Text(message.time.format(timeFormat), color = IviColors.TextTertiary, fontSize = 11.sp)
            message.seat?.let { Text(CabinAssistant.seatName(it), color = IviColors.TextTertiary, fontSize = 11.sp) }
        }
        Text(
            message.text,
            Modifier
                .testTag("assistant_user_${message.id}")
                .widthIn(max = 380.dp)
                .clip(RoundedCornerShape(18.dp, 18.dp, 4.dp, 18.dp))
                .background(Brush.horizontalGradient(listOf(Color(0xFF2F8CFF), Color(0xFF4FB3FF))))
                .padding(horizontal = 14.dp, vertical = 10.dp),
            fontSize = 15.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun AssistantBubble(message: ChatMessage, latest: Boolean, short: Boolean, onChoose: (dev.opencabin.ivi.assistant.Place) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                message.text,
                Modifier
                    // 가장 최근 대답에만 assistant_reply 태그를 붙여 테스트가 '방금 대답' 을 읽게 한다
                    .then(if (latest) Modifier.testTag("assistant_reply") else Modifier)
                    .widthIn(max = 420.dp)
                    .clip(RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp))
                    .background(IviColors.SurfaceHigh)
                    .border(1.dp, IviColors.Line, RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp))
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                fontSize = 15.sp,
            )
            Text("  ${message.time.format(timeFormat)}", color = IviColors.TextTertiary, fontSize = 11.sp)
        }
        fun tag(i: Int) = if (latest) "assistant_candidate_$i" else "assistant_old_candidate_${message.id}_$i"
        if (short && message.candidates.isNotEmpty()) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                message.candidates.forEachIndexed { i, place ->
                    PlaceCard(place, tag(i), index = i + 1, Modifier.weight(1f)) { onChoose(place) }
                }
            }
        } else {
            message.candidates.forEachIndexed { i, place ->
                Box(Modifier.widthIn(max = 420.dp)) {
                    PlaceRow(place, tag(i), index = i + 1) { onChoose(place) }
                }
            }
        }
    }
}

/** 목적지 후보 한 장 (낮은 화면에서 가로로 늘어놓을 때). 위: 번호 · 이름, 아래: 거리 · 주소. */
@Composable
private fun PlaceCard(place: Place, tag: String, index: Int, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier
            .testTag(tag)
            .clip(RoundedCornerShape(12.dp))
            .background(IviColors.SurfaceHigh)
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                "$index",
                Modifier.size(20.dp).clip(CircleShape).background(IviColors.Accent),
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
            Text(place.name, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(kmText(place.distanceKm), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = IviColors.AccentSoft)
            Text(place.address, fontSize = 13.sp, color = IviColors.TextSecondary, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

/** 목적지 후보 한 줄 (번호 · 이름 · 거리 · 주소). 대답 글과 같이 보이도록 한 줄 높이로 작게. */
@Composable
private fun PlaceRow(place: Place, tag: String, index: Int, onClick: () -> Unit) {
    Row(
        Modifier
            .testTag(tag)
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(IviColors.SurfaceHigh)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "$index",
            Modifier.size(20.dp).clip(CircleShape).background(IviColors.Accent),
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )
        Text(place.name, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
        Text(kmText(place.distanceKm), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = IviColors.AccentSoft)
        Text(place.address, Modifier.weight(1f), fontSize = 13.sp, color = IviColors.TextSecondary, maxLines = 1,
            overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
    }
}
