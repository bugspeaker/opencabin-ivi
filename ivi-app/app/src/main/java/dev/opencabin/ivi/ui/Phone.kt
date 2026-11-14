package dev.opencabin.ivi.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.opencabin.ivi.state.CabinController
import dev.opencabin.ivi.state.Contacts
import dev.opencabin.ivi.state.DRIVING_LIST_LIMIT
import dev.opencabin.ivi.vehicle.VehicleState

private enum class PhoneTab(val label: String, val tag: String) {
    RECENT("최근 통화", "phone_tab_recent"), CONTACTS("연락처", "phone_tab_contacts"), KEYPAD("키패드", "phone_tab_keypad")
}

/**
 * 전화 (블루투스 핸즈프리, 가상): 최근 통화 · 연락처 · 키패드.
 * 주행 중에는 키패드를 막고 연락처는 앞의 일부만 보인다 (주의 분산 줄이기). 통화 중에는 오디오가 멈춘다.
 */
@Composable
fun PhoneScreen(state: VehicleState, cabin: CabinController) {
    var tab by rememberSaveable { mutableStateOf(PhoneTab.RECENT) }
    Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Panel(Modifier.weight(0.42f).fillMaxHeight()) {
            Label("블루투스")
            Text("내 휴대폰", Modifier.testTag("phone_device"), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
            Text("연결됨 · 핸즈프리", color = IviColors.Aqua, fontSize = 15.sp)
            PhoneTab.entries.forEach { t ->
                PillButton(t.label, t.tag, Modifier.fillMaxWidth(), selected = tab == t) { tab = t }
            }
        }
        Panel(Modifier.weight(0.58f).fillMaxHeight()) {
            when (tab) {
                PhoneTab.RECENT -> Recent(cabin)
                PhoneTab.CONTACTS -> ContactList(state.restricted, cabin)
                PhoneTab.KEYPAD -> Keypad(state.restricted, cabin)
            }
        }
    }
}

@Composable
private fun Recent(cabin: CabinController) {
    Label("최근 통화")
    LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        itemsIndexed(cabin.recents) { index, record ->
            Row(
                Modifier
                    .testTag("phone_recent_$index")
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .clickable { cabin.dial(record.name, record.number) }
                    .padding(horizontal = 12.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(record.name, Modifier.weight(1f).testTag("phone_recent_${index}_name"), fontSize = 17.sp,
                    color = if (record.kind == "부재중") IviColors.Danger else IviColors.TextPrimary)
                Text(record.kind, fontSize = 13.sp, color = IviColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun ContactList(restricted: Boolean, cabin: CabinController) {
    Label("연락처")
    if (restricted) {
        Text("주행 중에는 연락처를 ${DRIVING_LIST_LIMIT}개까지만 보여 줍니다", Modifier.testTag("phone_list_limited"), color = IviColors.Warn, fontSize = 14.sp)
    }
    val shown = if (restricted) Contacts.take(DRIVING_LIST_LIMIT) else Contacts
    LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        itemsIndexed(shown) { index, contact ->
            Row(
                Modifier
                    .testTag("phone_contact_$index")
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .clickable { cabin.dial(contact.name, contact.number) }
                    .padding(horizontal = 12.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(contact.name, Modifier.weight(1f).testTag("phone_contact_${index}_name"), fontSize = 17.sp)
                Text(contact.number, fontSize = 13.sp, color = IviColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun Keypad(restricted: Boolean, cabin: CabinController) {
    if (restricted) {
        Text("주행 중에는 번호를 직접 누를 수 없습니다", Modifier.testTag("phone_keypad_locked"), color = IviColors.Warn, fontSize = 14.sp)
    }
    Text(cabin.dialNumber.ifEmpty { " " }, Modifier.testTag("phone_dial_number").fillMaxWidth(), fontSize = 28.sp, fontWeight = FontWeight.Light)
    val keys = listOf("1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#")
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        keys.chunked(3).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                row.forEach { key ->
                    val tag = when (key) { "*" -> "phone_key_star"; "#" -> "phone_key_hash"; else -> "phone_key_$key" }
                    RoundButton(key, tag, enabled = !restricted, size = 52.dp) { cabin.press(key) }
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            RoundButton("⌫", "phone_backspace", enabled = !restricted && cabin.dialNumber.isNotEmpty(), size = 52.dp) { cabin.backspace() }
            RoundButton("✆", "phone_call", enabled = !restricted && cabin.dialNumber.isNotEmpty(), tint = IviColors.Ok, filled = true, size = 52.dp) { cabin.dial() }
        }
    }
}
