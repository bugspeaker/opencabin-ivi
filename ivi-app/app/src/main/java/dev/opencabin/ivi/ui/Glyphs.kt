package dev.opencabin.ivi.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.dp

/*
 * 화면에 쓰는 기호를 Canvas 로 직접 그린다 (아이콘 파일·외부 아이콘 세트·이모지를 쓰지 않는다).
 * 이모지는 AAOS 에뮬레이터 글꼴에 없으면 네모로 보인다. 모든 기호는 0~1 좌표로 그려 크기에 맞게 늘어난다.
 */

enum class G {
    CAR, FAN, MUSIC, NAV, GRID, SPARK, MIC, SEARCH, BELL, PROFILE, SIGNAL, VOLUME,
    SEAT_HEAT, DEFROST_FRONT, DEFROST_REAR, SPLIT, HOME, BUILDING, STAR, BOLT, PARKING,
    CLOSE, REFRESH, PLAY, PAUSE, PREV, NEXT, LOCK, UNLOCK, MIRROR, TRUNK, LIGHT, CHILD, PHONE, VIDEO, BAG,
    CHEVRON_LEFT, CHEVRON_RIGHT, TURN_RIGHT, PIN, LANE, RADIO, GEAR, CAMERA,
}

@Composable
fun Glyph(g: G, color: Color, modifier: Modifier = Modifier.size(24.dp)) {
    Canvas(modifier) { draw(g, color) }
}

private fun DrawScope.p(x: Float, y: Float) = Offset(size.width * x, size.height * y)

private fun DrawScope.path(vararg pts: Pair<Float, Float>, close: Boolean = false) = Path().apply {
    pts.forEachIndexed { i, (x, y) -> if (i == 0) moveTo(size.width * x, size.height * y) else lineTo(size.width * x, size.height * y) }
    if (close) close()
}

private fun DrawScope.draw(g: G, c: Color) {
    val w = size.minDimension
    val stroke = Stroke(width = w * 0.09f, cap = StrokeCap.Round, join = StrokeJoin.Round)
    val thin = Stroke(width = w * 0.07f, cap = StrokeCap.Round, join = StrokeJoin.Round)
    fun line(x1: Float, y1: Float, x2: Float, y2: Float, s: Stroke = stroke) =
        drawLine(c, p(x1, y1), p(x2, y2), strokeWidth = s.width, cap = StrokeCap.Round)
    fun rrect(x: Float, y: Float, rw: Float, rh: Float, r: Float, fill: Boolean = false) =
        drawRoundRect(c, p(x, y), Size(size.width * rw, size.height * rh), CornerRadius(w * r), style = if (fill) androidx.compose.ui.graphics.drawscope.Fill else stroke)

    when (g) {
        G.CAR -> {
            drawPath(path(0.08f to 0.62f, 0.14f to 0.46f, 0.30f to 0.42f, 0.40f to 0.28f, 0.66f to 0.28f, 0.78f to 0.42f, 0.92f to 0.48f, 0.92f to 0.66f, 0.08f to 0.66f, close = true), c)
            drawCircle(c, w * 0.10f, p(0.28f, 0.70f)); drawCircle(c, w * 0.10f, p(0.74f, 0.70f))
            drawCircle(Color.Black.copy(alpha = 0.55f), w * 0.045f, p(0.28f, 0.70f)); drawCircle(Color.Black.copy(alpha = 0.55f), w * 0.045f, p(0.74f, 0.70f))
        }
        G.FAN -> {
            repeat(4) { i ->
                rotate(i * 90f + 20f) { drawOval(c, p(0.40f, 0.06f), Size(size.width * 0.24f, size.height * 0.42f)) }
            }
            drawCircle(Color.Black.copy(alpha = 0.35f), w * 0.09f, center)
        }
        G.MUSIC -> {
            line(0.38f, 0.72f, 0.38f, 0.20f); line(0.80f, 0.62f, 0.80f, 0.12f)
            drawPath(path(0.38f to 0.20f, 0.80f to 0.12f, 0.80f to 0.26f, 0.38f to 0.34f, close = true), c)
            drawOval(c, p(0.16f, 0.64f), Size(size.width * 0.26f, size.height * 0.20f))
            drawOval(c, p(0.58f, 0.54f), Size(size.width * 0.26f, size.height * 0.20f))
        }
        G.NAV -> drawPath(path(0.88f to 0.12f, 0.52f to 0.90f, 0.44f to 0.56f, 0.10f to 0.48f, close = true), c)
        G.GRID -> listOf(0.10f to 0.10f, 0.56f to 0.10f, 0.10f to 0.56f, 0.56f to 0.56f).forEach { (x, y) -> rrect(x, y, 0.34f, 0.34f, 0.12f, fill = true) }
        G.SPARK -> {
            drawPath(path(0.50f to 0.04f, 0.60f to 0.40f, 0.96f to 0.50f, 0.60f to 0.60f, 0.50f to 0.96f, 0.40f to 0.60f, 0.04f to 0.50f, 0.40f to 0.40f, close = true), c)
        }
        G.MIC -> {
            rrect(0.36f, 0.08f, 0.28f, 0.50f, 0.14f, fill = true)
            drawArc(c, 180f, -180f, false, p(0.22f, 0.24f), Size(size.width * 0.56f, size.height * 0.52f), style = stroke)
            line(0.5f, 0.76f, 0.5f, 0.92f)
        }
        G.SEARCH -> { drawCircle(c, w * 0.30f, p(0.42f, 0.42f), style = stroke); line(0.64f, 0.64f, 0.88f, 0.88f) }
        G.BELL -> {
            drawPath(path(0.18f to 0.74f, 0.26f to 0.62f, 0.26f to 0.42f, 0.36f to 0.22f, 0.50f to 0.16f, 0.64f to 0.22f, 0.74f to 0.42f, 0.74f to 0.62f, 0.82f to 0.74f, close = true), c)
            drawCircle(c, w * 0.08f, p(0.5f, 0.84f)); drawCircle(c, w * 0.05f, p(0.5f, 0.12f))
        }
        G.PROFILE -> {
            drawCircle(c, w * 0.18f, p(0.5f, 0.36f))
            drawArc(c, 180f, 180f, true, p(0.18f, 0.60f), Size(size.width * 0.64f, size.height * 0.56f))
        }
        G.SIGNAL -> listOf(0.62f, 0.46f, 0.30f, 0.14f).forEachIndexed { i, top -> line(0.18f + i * 0.21f, 0.86f, 0.18f + i * 0.21f, top) }
        G.VOLUME -> {
            drawPath(path(0.10f to 0.38f, 0.28f to 0.38f, 0.50f to 0.18f, 0.50f to 0.82f, 0.28f to 0.62f, 0.10f to 0.62f, close = true), c)
            drawArc(c, -45f, 90f, false, p(0.40f, 0.30f), Size(size.width * 0.30f, size.height * 0.40f), style = thin)
            drawArc(c, -50f, 100f, false, p(0.36f, 0.16f), Size(size.width * 0.52f, size.height * 0.68f), style = thin)
        }
        G.SEAT_HEAT -> {
            drawPath(path(0.20f to 0.10f, 0.34f to 0.10f, 0.40f to 0.60f, 0.74f to 0.60f, 0.78f to 0.78f, 0.30f to 0.78f, close = true), c)
            listOf(0.56f, 0.70f, 0.84f).forEach { x ->
                drawPath(path(x to 0.48f, x - 0.05f to 0.38f, x to 0.28f, x - 0.05f to 0.18f), c, style = thin)
            }
        }
        G.DEFROST_FRONT -> {
            drawArc(c, 200f, 140f, false, p(0.08f, 0.12f), Size(size.width * 0.84f, size.height * 0.84f), style = stroke)
            line(0.14f, 0.80f, 0.86f, 0.80f)
            listOf(0.34f, 0.5f, 0.66f).forEach { x -> drawPath(path(x to 0.70f, x - 0.05f to 0.58f, x to 0.46f, x - 0.05f to 0.34f), c, style = thin) }
        }
        G.DEFROST_REAR -> {
            rrect(0.10f, 0.16f, 0.80f, 0.56f, 0.10f)
            listOf(0.34f, 0.5f, 0.66f).forEach { x -> drawPath(path(x to 0.92f, x - 0.05f to 0.82f, x to 0.72f), c, style = thin) }
            line(0.24f, 0.36f, 0.76f, 0.36f, thin); line(0.24f, 0.52f, 0.76f, 0.52f, thin)
        }
        G.SPLIT -> { rrect(0.08f, 0.16f, 0.84f, 0.68f, 0.12f); line(0.5f, 0.18f, 0.5f, 0.82f) }
        G.HOME -> drawPath(path(0.12f to 0.48f, 0.50f to 0.14f, 0.88f to 0.48f, 0.80f to 0.48f, 0.80f to 0.88f, 0.60f to 0.88f, 0.60f to 0.64f, 0.40f to 0.64f, 0.40f to 0.88f, 0.20f to 0.88f, 0.20f to 0.48f, close = true), c)
        G.BUILDING -> {
            rrect(0.18f, 0.10f, 0.64f, 0.80f, 0.06f, fill = true)
            listOf(0.30f, 0.56f).forEach { x -> listOf(0.22f, 0.40f, 0.58f).forEach { y -> drawRect(Color.Black.copy(alpha = 0.55f), p(x, y), Size(size.width * 0.14f, size.height * 0.10f)) } }
        }
        G.STAR -> drawPath(path(0.50f to 0.06f, 0.62f to 0.36f, 0.94f to 0.38f, 0.69f to 0.58f, 0.78f to 0.90f, 0.50f to 0.72f, 0.22f to 0.90f, 0.31f to 0.58f, 0.06f to 0.38f, 0.38f to 0.36f, close = true), c)
        G.BOLT -> drawPath(path(0.58f to 0.04f, 0.20f to 0.56f, 0.46f to 0.56f, 0.40f to 0.96f, 0.80f to 0.40f, 0.54f to 0.40f, close = true), c)
        G.PARKING -> {
            line(0.30f, 0.12f, 0.30f, 0.88f)
            drawPath(path(0.30f to 0.14f, 0.58f to 0.14f), c, style = stroke)
            drawArc(c, -90f, 180f, false, p(0.40f, 0.14f), Size(size.width * 0.36f, size.height * 0.40f), style = stroke)
            line(0.30f, 0.54f, 0.58f, 0.54f)
        }
        G.CLOSE -> { line(0.22f, 0.22f, 0.78f, 0.78f); line(0.78f, 0.22f, 0.22f, 0.78f) }
        G.REFRESH -> {
            drawArc(c, -60f, 290f, false, p(0.16f, 0.16f), Size(size.width * 0.68f, size.height * 0.68f), style = stroke)
            drawPath(path(0.66f to 0.08f, 0.86f to 0.22f, 0.64f to 0.34f, close = true), c)
        }
        G.PLAY -> drawPath(path(0.24f to 0.12f, 0.86f to 0.50f, 0.24f to 0.88f, close = true), c)
        G.PAUSE -> { rrect(0.20f, 0.12f, 0.20f, 0.76f, 0.06f, fill = true); rrect(0.60f, 0.12f, 0.20f, 0.76f, 0.06f, fill = true) }
        G.PREV -> { rrect(0.12f, 0.16f, 0.12f, 0.68f, 0.04f, fill = true); drawPath(path(0.86f to 0.16f, 0.30f to 0.50f, 0.86f to 0.84f, close = true), c) }
        G.NEXT -> { rrect(0.76f, 0.16f, 0.12f, 0.68f, 0.04f, fill = true); drawPath(path(0.14f to 0.16f, 0.70f to 0.50f, 0.14f to 0.84f, close = true), c) }
        G.LOCK, G.UNLOCK -> {
            rrect(0.18f, 0.44f, 0.64f, 0.48f, 0.10f, fill = true)
            val right = if (g == G.LOCK) 0.68f else 0.80f
            drawArc(c, 180f, 180f, false, p(0.32f, 0.12f), Size(size.width * 0.36f, size.height * 0.40f), style = stroke)
            line(0.32f, 0.32f, 0.32f, 0.46f); line(right, if (g == G.LOCK) 0.32f else 0.20f, right, if (g == G.LOCK) 0.46f else 0.30f)
        }
        G.MIRROR -> {
            drawPath(path(0.10f to 0.30f, 0.80f to 0.20f, 0.90f to 0.72f, 0.18f to 0.78f, close = true), c, style = stroke)
            line(0.14f, 0.54f, 0.04f, 0.56f)
        }
        G.TRUNK -> {
            drawPath(path(0.10f to 0.78f, 0.10f to 0.50f, 0.26f to 0.30f, 0.74f to 0.30f, 0.90f to 0.50f, 0.90f to 0.78f, close = true), c, style = stroke)
            line(0.10f, 0.50f, 0.90f, 0.50f, thin); line(0.40f, 0.64f, 0.60f, 0.64f, thin)
        }
        G.LIGHT -> {
            drawArc(c, 90f, 180f, false, p(0.10f, 0.22f), Size(size.width * 0.50f, size.height * 0.56f), style = stroke)
            line(0.35f, 0.22f, 0.35f, 0.78f)
            listOf(0.30f, 0.50f, 0.70f).forEach { y -> line(0.56f, y, 0.90f, y, thin) }
        }
        G.CHILD -> {
            drawCircle(c, w * 0.14f, p(0.5f, 0.22f))
            drawPath(path(0.30f to 0.88f, 0.36f to 0.44f, 0.64f to 0.44f, 0.70f to 0.88f, close = true), c)
        }
        G.PHONE -> {
            drawPath(path(0.18f to 0.14f, 0.36f to 0.10f, 0.44f to 0.32f, 0.34f to 0.42f, 0.58f to 0.66f, 0.68f to 0.56f, 0.90f to 0.64f, 0.86f to 0.82f, 0.72f to 0.90f, 0.40f to 0.74f, 0.16f to 0.48f, 0.10f to 0.28f, close = true), c)
        }
        G.VIDEO -> { rrect(0.06f, 0.22f, 0.62f, 0.56f, 0.10f, fill = true); drawPath(path(0.70f to 0.42f, 0.94f to 0.26f, 0.94f to 0.74f, 0.70f to 0.58f, close = true), c) }
        G.BAG -> {
            rrect(0.14f, 0.32f, 0.72f, 0.58f, 0.10f, fill = true)
            drawArc(c, 180f, 180f, false, p(0.32f, 0.12f), Size(size.width * 0.36f, size.height * 0.40f), style = stroke)
        }
        G.CHEVRON_LEFT -> drawPath(path(0.64f to 0.16f, 0.30f to 0.50f, 0.64f to 0.84f), c, style = stroke)
        G.CHEVRON_RIGHT -> drawPath(path(0.36f to 0.16f, 0.70f to 0.50f, 0.36f to 0.84f), c, style = stroke)
        G.TURN_RIGHT -> {
            drawPath(path(0.26f to 0.92f, 0.26f to 0.44f, 0.30f to 0.36f, 0.70f to 0.36f), c, style = stroke)
            drawPath(path(0.58f to 0.18f, 0.84f to 0.36f, 0.58f to 0.54f, close = true), c)
        }
        G.PIN -> {
            drawCircle(c, w * 0.30f, p(0.5f, 0.40f))
            drawPath(path(0.24f to 0.50f, 0.50f to 0.94f, 0.76f to 0.50f, close = true), c)
            drawCircle(Color.Black.copy(alpha = 0.5f), w * 0.11f, p(0.5f, 0.40f))
        }
        G.RADIO -> {
            drawCircle(c, w * 0.10f, p(0.5f, 0.46f))
            drawArc(c, 135f, 270f, false, p(0.26f, 0.22f), Size(size.width * 0.48f, size.height * 0.48f), style = thin)
            drawArc(c, 135f, 270f, false, p(0.08f, 0.04f), Size(size.width * 0.84f, size.height * 0.84f), style = thin)
            line(0.5f, 0.56f, 0.5f, 0.94f)
        }
        G.GEAR -> {
            repeat(8) { i -> rotate(i * 45f) { drawRect(c, p(0.42f, 0.04f), Size(size.width * 0.16f, size.height * 0.22f)) } }
            drawCircle(c, w * 0.32f, center)
            drawCircle(Color.Black.copy(alpha = 0.55f), w * 0.13f, center)
        }
        G.CAMERA -> {
            rrect(0.06f, 0.26f, 0.88f, 0.60f, 0.12f, fill = true)
            rrect(0.32f, 0.14f, 0.30f, 0.16f, 0.06f, fill = true)
            drawCircle(Color.Black.copy(alpha = 0.55f), w * 0.17f, p(0.5f, 0.56f))
        }
        G.LANE -> {
            drawPath(path(0.20f to 0.90f, 0.38f to 0.10f), c, style = stroke)
            drawPath(path(0.80f to 0.90f, 0.62f to 0.10f), c, style = stroke)
            drawPath(path(0.38f to 0.80f, 0.40f to 0.52f, 0.62f to 0.52f, 0.62f to 0.80f, close = true), c)
        }
    }
}
