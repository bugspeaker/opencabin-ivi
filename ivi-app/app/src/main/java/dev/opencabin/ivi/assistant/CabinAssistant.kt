package dev.opencabin.ivi.assistant

import dev.opencabin.ivi.vehicle.HvacSpec
import dev.opencabin.ivi.vehicle.Seat
import java.util.Locale

/*
 * 차량 음성 비서의 '말 → 동작' 부분 (docs/phase7-layout.md 의 AI 어시스턴트).
 *
 * 참고한 기능 (공개 자료 기준, LLM 대신 규칙 기반으로 단순화):
 *   - 한 번에 여러 명령 ("에어컨 켜고 음악 틀어줘")
 *   - 말한 좌석 인식 (Zone): 좌석을 말하지 않으면 '말한 사람의 좌석'에 적용한다. "나 더워" → 말한 좌석만 내린다
 *   - 간접 표현 ("더워", "추워") → 온도 조절
 *   - 목적지 후보가 여럿이면 고르게 한다
 *   - 주행 상황에 따라 제한 (주행 중 영상·사이드 미러 접기는 거절)
 *
 * 화면(Compose)과 분리된 순수 Kotlin 이라 JVM 단위 테스트로 검증한다 (src/test).
 */

enum class PlaceCategory(val label: String) { HOME("집"), WORK("회사"), STATION("역"), CHARGER("충전소"), PARKING("주차장"), STORE("편의점"), PLACE("장소") }

data class Place(val id: String, val name: String, val address: String, val distanceKm: Float, val category: PlaceCategory)

/**
 * 데모용 장소 목록 (내비게이션 검색 목록과 비서가 같이 쓴다). 실제 지도·검색 서비스 대신 쓴다.
 * 앞의 6곳은 6단계 내비게이션의 목록·순서·거리 그대로다 (E2E 테스트가 nav_dest_N 순서와 거리를 본다).
 * 뒤의 충전소·주차장은 이름에 '역'이 들어가지 않게 했다 ('역' 검색 결과 = 판교역, 서울역).
 */
object Places {
    val all = listOf(
        Place("home", "집", "경기 성남시 분당구", 12.4f, PlaceCategory.HOME),
        Place("work", "회사", "판교 업무지구 (가상 주소)", 8.7f, PlaceCategory.WORK),
        Place("pangyo_station", "판교역", "신분당선 · 경강선", 5.2f, PlaceCategory.STATION),
        Place("seoul_station", "서울역", "서울 용산구", 27.9f, PlaceCategory.STATION),
        Place("airport", "인천국제공항", "인천 중구", 68.3f, PlaceCategory.PLACE),
        Place("store", "편의점", "500m 이내", 0.1f, PlaceCategory.STORE),
        Place("pangyo_charger", "판교 급속 충전소", "경기 성남시 대왕판교로", 1.8f, PlaceCategory.CHARGER),
        Place("jeongja_charger", "정자 급속 충전소", "경기 성남시 정자일로", 4.6f, PlaceCategory.CHARGER),
        Place("pangyo_parking", "판교 공영주차장", "경기 성남시 판교로", 2.0f, PlaceCategory.PARKING),
        Place("jeongja_parking", "정자 공영주차장", "경기 성남시 정자동", 4.1f, PlaceCategory.PARKING),
    )

    fun byId(id: String) = all.firstOrNull { it.id == id }

    fun byCategory(category: PlaceCategory) = all.filter { it.category == category }.sortedBy { it.distanceKm }

    /**
     * 이름으로 찾는다 (가까운 순).
     *   "판교역" → 판교역 (이름이 같으면 그것만)    "판교" → 판교역, 판교 급속 충전소, 판교역 공영주차장
     *   "판교 충전소" → 판교 급속 충전소 (낱말이 모두 들어 있는 이름)    "가까운 충전소" → 분류로 찾는다
     */
    fun search(query: String): List<Place> {
        val q = query.replace(" ", "")
        if (q.isEmpty()) return emptyList()
        val exact = all.filter { it.name.replace(" ", "") == q }
        if (exact.isNotEmpty()) return exact
        val words = query.trim().split(Regex("\\s+"))
        val byName = all.filter { place -> words.all { place.name.contains(it) } }
        if (byName.isNotEmpty()) return byName.sortedBy { it.distanceKm }
        val bare = q.removePrefix("가까운").removePrefix("근처").removePrefix("주변")
        return PlaceCategory.entries.firstOrNull { it != PlaceCategory.PLACE && bare == it.label }?.let(::byCategory) ?: emptyList()
    }
}

/** 비서가 할 수 있는 동작. 문장 하나(절)가 동작 하나가 된다. */
sealed interface Action {
    data class SetTemp(val seats: List<Seat>, val celsius: Float) : Action
    data class AdjustTemp(val seats: List<Seat>, val delta: Float, val reason: String? = null) : Action
    data class SetAc(val on: Boolean) : Action
    data class SetSync(val on: Boolean) : Action
    data class SeatHeat(val seats: List<Seat>, val on: Boolean) : Action
    data object Play : Action
    data object Pause : Action
    data object Next : Action
    data class Navigate(val query: String) : Action
    data object CancelRoute : Action
    data object OpenVideo : Action
    data class FoldMirrors(val fold: Boolean) : Action
    data class Radio(val on: Boolean) : Action
    data class Call(val who: String) : Action
    data class Unknown(val text: String) : Action
}

/** 비서가 차를 움직이는 경계. 화면 쪽(IviRoot)이 구현한다. */
interface CabinControls {
    /** 영상을 막는 UX 제한이 걸려 있는가 (P 가 아니면 멈춰 있어도 true) */
    val videoBlocked: Boolean
    /** 차가 움직이는가 (사이드 미러 접기를 막는다) */
    val moving: Boolean
    val hvacAvailable: Boolean
    fun temperature(seat: Seat): Float?
    fun setTemperature(seat: Seat, celsius: Float)
    fun setAc(on: Boolean)
    fun setSync(on: Boolean)
    fun setSeatHeat(seat: Seat, on: Boolean)
    fun play()
    fun pause()
    fun next(): String
    fun navigate(place: Place)
    fun cancelRoute(): Boolean
    fun openVideo()
    fun foldMirrors(fold: Boolean)
    fun setRadio(on: Boolean)

    /** 연락처 이름으로 전화를 건다. 찾은 이름을 돌려주고, 없으면 null. */
    fun call(who: String): String?
}

/** 비서의 대답. 목적지 후보가 여럿이면 [candidates] 로 화면에 카드로 보여 준다. */
data class Reply(val text: String, val candidates: List<Place> = emptyList(), val understood: Boolean = true)

object IntentParser {

    /** "에어컨 켜고 음악 틀어줘" → ["에어컨 켜", "음악 틀어줘"]. '그리고', 쉼표, '…고 ' 로 나눈다. */
    fun split(utterance: String): List<String> =
        utterance
            // 마침표는 문장 끝(뒤에 공백)일 때만. "22.5도" 의 소수점은 나누지 않는다
            .split(Regex("\\s*(?:그리고|,|\\.\\s|하고\\s)\\s*|(?<=[켜꺼끄틀춰려어아추리접열])고\\s+"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }

    fun parse(clause: String, speaker: Seat): Action {
        val c = clause.replace(" ", "")
        val seats = seatsIn(c, speaker)

        // 순서가 중요하다: '영상 틀어줘' 는 '틀어' 가 있어도 음악이 아니고, '안내 종료' 는 목적지가 아니다
        if (c.containsAny("영상", "동영상", "비디오", "유튜브")) return Action.OpenVideo
        if (c.contains("미러")) return Action.FoldMirrors(fold = !c.containsAny("펴", "펼"))
        if (c.containsAny("안내종료", "안내취소", "경로취소", "길안내그만", "안내그만", "안내꺼")) return Action.CancelRoute

        Regex("(\\d{2}(?:\\.\\d)?)도").find(c)?.let { return Action.SetTemp(seats, it.groupValues[1].toFloat()) }
        if (c.containsAny("에어컨", "A/C", "냉방")) return Action.SetAc(on = !c.containsAny("꺼", "끄", "off"))
        if (c.containsAny("동기화", "싱크")) return Action.SetSync(on = !c.containsAny("해제", "꺼", "끄", "풀"))
        if (c.containsAny("열선", "시트히터", "엉뜨", "히터")) return Action.SeatHeat(seats, on = !c.containsAny("꺼", "끄"))
        if (c.containsAny("더워", "덥", "더운")) return Action.AdjustTemp(seats, -1.0f, "더우시군요")
        if (c.containsAny("추워", "춥", "추운", "쌀쌀")) return Action.AdjustTemp(seats, +1.0f, "추우시군요")
        if (c.contains("온도")) {
            val step = if (c.containsAny("많이", "확")) 1.0f else HvacSpec.STEP_C
            if (c.containsAny("올려", "높여", "따뜻")) return Action.AdjustTemp(seats, step)
            if (c.containsAny("내려", "낮춰", "시원")) return Action.AdjustTemp(seats, -step)
        }

        if (c.contains("라디오")) return Action.Radio(on = !c.containsAny("꺼", "끄", "그만"))
        Regex("^(.+?)(에게|한테|께)?전화").find(c)?.let { return Action.Call(it.groupValues[1]) }

        if (c.containsAny("다음곡", "다음노래", "넘겨")) return Action.Next
        if (c.containsAny("음악", "노래", "재생")) {
            return if (c.containsAny("멈춰", "정지", "그만", "꺼", "끄")) Action.Pause else Action.Play
        }
        if (c.containsAny("일시정지", "멈춰")) return Action.Pause

        if (c.containsAny("가자", "가줘", "안내", "길찾", "찾아줘", "데려다", "가고싶")) {
            val query = clause
                .replace(Regex("(으로|로|에|까지)?\\s*(가자|가줘|안내해\\s*줘|안내|길\\s*찾아\\s*줘|찾아\\s*줘|데려다\\s*줘|가고\\s*싶어).*$"), "")
                .replace(Regex("^(글쎄|음|그럼|거기\\s*말고)\\s*"), "")
                .replace(Regex("에\\s*있는\\s*(데|곳)$"), "")
                .trim()
            if (query.isNotEmpty()) return Action.Navigate(query)
        }
        return Action.Unknown(clause)
    }

    private fun seatsIn(c: String, speaker: Seat): List<Seat> = when {
        c.containsAny("모두", "전체", "다같이", "모든좌석", "양쪽", "전좌석") -> Seat.entries.toList()
        c.contains("운전석") -> listOf(Seat.DRIVER)
        c.containsAny("조수석", "동승석", "옆자리") -> listOf(Seat.PASSENGER)
        else -> listOf(speaker) // 좌석을 말하지 않으면 말한 사람의 좌석 (Zone 인식)
    }

    private fun String.containsAny(vararg words: String) = words.any { contains(it, ignoreCase = true) }
}

class CabinAssistant(private val controls: CabinControls) {

    /** 한 번 말한 것을 처리한다. 여러 명령은 차례로 실행하고 대답을 이어 붙인다. */
    fun handle(utterance: String, speaker: Seat): Reply {
        val clauses = IntentParser.split(utterance)
        if (clauses.isEmpty()) return Reply(HELP, understood = false)
        val parts = mutableListOf<String>()
        var candidates = emptyList<Place>()
        var understood = true
        for (clause in clauses) {
            val result = run(IntentParser.parse(clause, speaker))
            parts += result.text
            if (result.candidates.isNotEmpty()) candidates = result.candidates
            if (!result.understood) understood = false
        }
        return Reply(parts.joinToString(" "), candidates, understood)
    }

    /** 목적지 후보 카드를 눌렀을 때. */
    fun choose(place: Place): Reply {
        controls.navigate(place)
        return Reply("${place.name}${josa(place.name, "으로", "로")} 안내를 시작할게요. ${fmtKm(place.distanceKm)}예요.")
    }

    private fun run(action: Action): Reply = when (action) {
        is Action.SetTemp -> hvac {
            val target = HvacSpec.clamp(snap(action.celsius))
            action.seats.forEach { controls.setTemperature(it, target) }
            val note = if (target != action.celsius) "설정할 수 있는 온도는 ${fmt(HvacSpec.MIN_C)}~${fmt(HvacSpec.MAX_C)}°C예요. " else ""
            Reply("$note${seatNames(action.seats)} 온도를 ${fmt(target)}°C로 맞췄어요.")
        }
        is Action.AdjustTemp -> hvac {
            val now = action.seats.associateWith { controls.temperature(it) }
            if (now.values.any { it == null }) {
                Reply("지금 온도를 알 수 없어요.", understood = false)
            } else {
                val targets = now.mapValues { (_, c) -> HvacSpec.clamp(c!! + action.delta) }
                targets.forEach { (seat, target) -> controls.setTemperature(seat, target) }
                val prefix = action.reason?.let { "$it. " } ?: ""
                val verb = if (action.delta < 0) "낮춰" else "높여"
                val values = targets.values.distinct().joinToString("/") { "${fmt(it)}°C" }
                Reply("$prefix${seatNames(action.seats)} 온도를 ${values}로 $verb 드렸어요.")
            }
        }
        is Action.SetAc -> hvac { controls.setAc(action.on); Reply(if (action.on) "에어컨을 켰어요." else "에어컨을 껐어요.") }
        is Action.SetSync -> hvac {
            controls.setSync(action.on)
            Reply(if (action.on) "조수석 온도를 운전석과 맞춰 둘게요." else "좌석별 온도 조절로 바꿨어요.")
        }
        is Action.SeatHeat -> hvac {
            action.seats.forEach { controls.setSeatHeat(it, action.on) }
            Reply("${seatNames(action.seats)} 열선을 ${if (action.on) "켰어요" else "껐어요"}.")
        }
        Action.Play -> { controls.play(); Reply("음악을 재생할게요.") }
        Action.Pause -> { controls.pause(); Reply("음악을 멈췄어요.") }
        Action.Next -> Reply("다음 곡 '${controls.next()}'을 재생할게요.")
        is Action.Navigate -> {
            val found = Places.search(action.query)
            when {
                found.isEmpty() -> Reply("'${action.query}'${josa(action.query, "을", "를")} 찾지 못했어요.", understood = false)
                found.size == 1 -> choose(found.first())
                else -> Reply("${action.query} 검색 결과가 ${found.size}곳이에요. 어디로 안내할까요?", candidates = found)
            }
        }
        Action.CancelRoute -> Reply(if (controls.cancelRoute()) "경로 안내를 종료했어요." else "지금 안내 중인 경로가 없어요.")
        Action.OpenVideo ->
            if (controls.videoBlocked) Reply(if (controls.moving) "주행 중에는 영상을 볼 수 없어요. 차를 세우고 P로 바꾸면 열어 드릴게요." else "P 기어에서만 영상을 볼 수 있어요. P로 바꾸면 열어 드릴게요.")
            else { controls.openVideo(); Reply("영상을 열게요.") }
        is Action.FoldMirrors ->
            if (controls.moving && action.fold) Reply("주행 중에는 사이드 미러를 접을 수 없어요.")
            else { controls.foldMirrors(action.fold); Reply(if (action.fold) "사이드 미러를 접었어요." else "사이드 미러를 폈어요.") }
        is Action.Radio -> { controls.setRadio(action.on); Reply(if (action.on) "라디오를 켤게요." else "라디오를 껐어요.") }
        is Action.Call -> controls.call(action.who)?.let { Reply("${it}에게 전화를 걸게요.") }
            ?: Reply("연락처에서 '${action.who}'${josa(action.who, "을", "를")} 찾지 못했어요.", understood = false)
        is Action.Unknown -> Reply("'${action.text}'${josa(action.text, "은", "는")} 아직 이해하지 못했어요. $HELP", understood = false)
    }

    private inline fun hvac(block: () -> Reply): Reply =
        if (!controls.hvacAvailable) Reply("지금은 공조를 제어할 수 없어요.", understood = false) else block()

    companion object {
        /**
         * 받침에 맞는 조사를 고른다: josa("판교역", "으로", "로") = "으로", josa("회사", "을", "를") = "를".
         * '(으)로'는 ㄹ 받침 뒤에서 '로'다 (서울로). 한글로 끝나지 않으면 받침 없는 쪽을 쓴다.
         */
        fun josa(word: String, withFinal: String, withoutFinal: String): String {
            val last = word.trimEnd().lastOrNull() ?: return withoutFinal
            if (last !in '가'..'힣') return withoutFinal
            val final = (last - '가') % 28
            if (final == 0) return withoutFinal
            return if (final == 8 && withFinal == "으로") withoutFinal else withFinal
        }

        const val HELP = "\"22도로 맞춰줘\", \"더워\", \"라디오 켜줘\", \"판교역 가자\"처럼 말해 보세요."

        fun seatName(seat: Seat) = when (seat) { Seat.DRIVER -> "운전석"; Seat.PASSENGER -> "조수석" }

        fun seatNames(seats: List<Seat>) = if (seats.size == Seat.entries.size) "전 좌석" else seats.joinToString("·") { seatName(it) }

        /** 0.5°C 단위로 맞춘다 (VHAL 설정 단위). */
        fun snap(celsius: Float) = Math.round(celsius / HvacSpec.STEP_C) * HvacSpec.STEP_C

        fun fmt(celsius: Float): String = String.format(Locale.US, "%.1f", celsius)

        fun fmtKm(km: Float): String = String.format(Locale.US, "%.1fkm", km)
    }
}
