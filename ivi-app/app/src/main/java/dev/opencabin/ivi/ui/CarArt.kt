package dev.opencabin.ivi.ui

import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate

/*
 * 내 차 그림: 소형 전기 해치백 (공개된 양산 해치백의 제원과 비율을 참고해 직접 그린다. 사진·제조사 이미지 파일은 쓰지 않는다.
 *   참고 자료는 docs/phase7-layout.md 의 '참고한 것').
 *   제원: 길이 4,155 · 폭 1,800 · 높이 1,505 · 휠베이스 2,680 mm (19인치 휠 225/45 R19 → 바퀴 지름 약 685 mm)
 *   특징: 앞에서 뒤까지 곧게 이어지다 리어 스포일러로 떨어지는 '에어로 해치' 지붕선,
 *         앞·뒤 픽셀 조명, 엠블럼 자리의 점 4개(모스 부호 H), 넓은 유리 지붕
 * 좌표는 차 길이 L 에 대한 비율로 둔다 (그래서 어느 크기로도 같은 비율).
 */

private const val LENGTH_MM = 4155f
private const val WIDTH_RATIO = 1800f / LENGTH_MM
private const val HEIGHT_RATIO = 1505f / LENGTH_MM
private const val AXLE = (LENGTH_MM - 2680f) / 2f / LENGTH_MM // 앞(뒤) 차축 위치 ≈ 0.177
private const val WHEEL_R = 685f / 2f / LENGTH_MM

private val Glass = Color(0xFF141A21)
private val PixelWhite = Color(0xFFEAF6FF)
private val PixelRed = Color(0xFFFF3B3B)

/**
 * 위에서 본 내 차 (앞이 위). (cx, cy) 는 차 중심, length 는 화면에서의 차 길이.
 * braking=true 면(후진 등) 뒤 픽셀 조명을 밝게 그린다.
 */
fun DrawScope.hatchbackTop(cx: Float, cy: Float, length: Float, body: Color, shade: Color, braking: Boolean = false) {
    val l = length
    val w = l * WIDTH_RATIO
    val left = cx - w / 2
    val top = cy - l / 2
    fun at(fx: Float, fy: Float) = Offset(left + w * fx, top + l * fy)

    // 그림자 · 바퀴 (차체 밖으로 살짝 보인다)
    drawRoundRect(Color.Black.copy(alpha = 0.4f), Offset(left + w * 0.05f, top + l * 0.02f), Size(w, l), CornerRadius(w * 0.3f))
    listOf(AXLE, 1f - AXLE).forEach { fy ->
        listOf(-0.04f, 0.88f).forEach { fx ->
            drawRoundRect(Color(0xFF0D0F12), at(fx, fy - 0.07f), Size(w * 0.16f, l * 0.14f), CornerRadius(w * 0.05f))
        }
    }
    // 차체: 앞은 둥글고 뒤는 각진 해치
    val bodyPath = Path().apply {
        moveTo(left + w * 0.18f, top)
        quadraticBezierTo(left + w * 0.5f, top - l * 0.012f, left + w * 0.82f, top)
        quadraticBezierTo(left + w, top + l * 0.02f, left + w, top + l * 0.14f)
        lineTo(left + w, top + l * 0.93f)
        quadraticBezierTo(left + w, top + l, left + w * 0.86f, top + l)
        lineTo(left + w * 0.14f, top + l)
        quadraticBezierTo(left, top + l, left, top + l * 0.93f)
        lineTo(left, top + l * 0.14f)
        quadraticBezierTo(left, top + l * 0.02f, left + w * 0.18f, top)
        close()
    }
    drawPath(bodyPath, Brush.horizontalGradient(listOf(shade, body, body, shade), startX = left, endX = left + w))
    // 사이드 미러
    drawRoundRect(shade, at(-0.10f, 0.285f), Size(w * 0.13f, l * 0.035f), CornerRadius(w * 0.04f))
    drawRoundRect(shade, at(0.97f, 0.285f), Size(w * 0.13f, l * 0.035f), CornerRadius(w * 0.04f))
    // 앞 유리 → 넓은 유리 지붕 → 뒤 유리 (하나로 이어진 어두운 면, 가운데 지붕 골조)
    val glass = Path().apply {
        moveTo(at(0.14f, 0.36f).x, at(0.14f, 0.36f).y)
        quadraticBezierTo(at(0.5f, 0.24f).x, at(0.5f, 0.24f).y, at(0.86f, 0.36f).x, at(0.86f, 0.36f).y)
        lineTo(at(0.88f, 0.78f).x, at(0.88f, 0.78f).y)
        quadraticBezierTo(at(0.5f, 0.84f).x, at(0.5f, 0.84f).y, at(0.12f, 0.78f).x, at(0.12f, 0.78f).y)
        close()
    }
    drawPath(glass, Brush.verticalGradient(listOf(Glass, Color(0xFF26313C), Glass), startY = top + l * 0.3f, endY = top + l * 0.82f))
    drawLine(body.copy(alpha = 0.55f), at(0.13f, 0.40f), at(0.87f, 0.40f), strokeWidth = l * 0.012f)
    drawLine(body.copy(alpha = 0.55f), at(0.12f, 0.62f), at(0.88f, 0.62f), strokeWidth = l * 0.010f)
    // 리어 스포일러 끝선
    drawLine(shade, at(0.10f, 0.865f), at(0.90f, 0.865f), strokeWidth = l * 0.012f)
    // 앞 픽셀 조명 + 가운데 점 4개 (모스 부호 H)
    pixelRow(at(0.08f, 0.012f), w * 0.84f, l * 0.018f, 12, PixelWhite)
    repeat(4) { i -> drawCircle(PixelWhite.copy(alpha = 0.9f), l * 0.006f, at(0.41f + i * 0.06f, 0.06f)) }
    // 뒤 픽셀 조명
    pixelRow(at(0.08f, 0.968f), w * 0.84f, l * 0.018f, 12, if (braking) PixelRed else PixelRed.copy(alpha = 0.65f))
}

/** 옆에서 본 내 차 (앞이 왼쪽). 정차(P) 화면에서 크게 보여 준다. (cx, groundY) 는 차 가운데 아래(바닥), length 는 차 길이. */
fun DrawScope.hatchbackSide(cx: Float, groundY: Float, length: Float, body: Color, shade: Color) {
    val l = length
    val x0 = cx - l / 2
    fun p(fx: Float, fy: Float) = Offset(x0 + l * fx, groundY - l * fy) // fy: 바닥에서 위로 (L 비율)
    val roof = HEIGHT_RATIO

    // 바닥 그림자
    drawOval(Brush.radialGradient(listOf(Color.Black.copy(alpha = 0.55f), Color.Transparent), center = p(0.5f, 0f), radius = l * 0.55f),
        topLeft = p(-0.04f, 0.035f), size = Size(l * 1.08f, l * 0.07f))

    // 차체 실루엣: 짧은 앞, 곧은 지붕선, 스포일러로 떨어지는 뒤
    val bodyPath = Path().apply {
        moveTo(p(0.01f, 0.07f).x, p(0.01f, 0.07f).y)
        cubicTo(p(-0.005f, 0.11f).x, p(-0.005f, 0.11f).y, p(0.0f, 0.17f).x, p(0.0f, 0.17f).y, p(0.03f, 0.19f).x, p(0.03f, 0.19f).y)
        lineTo(p(0.27f, 0.235f).x, p(0.27f, 0.235f).y) // 보닛 끝 (앞 유리 시작)
        cubicTo(p(0.36f, 0.30f).x, p(0.36f, 0.30f).y, p(0.42f, roof).x, p(0.42f, roof).y, p(0.50f, roof).x, p(0.50f, roof).y)
        lineTo(p(0.70f, roof - 0.006f).x, p(0.70f, roof - 0.006f).y) // 곧은 지붕
        cubicTo(p(0.80f, roof - 0.012f).x, p(0.80f, roof - 0.012f).y, p(0.90f, 0.31f).x, p(0.90f, 0.31f).y, p(0.975f, 0.285f).x, p(0.975f, 0.285f).y) // 스포일러로 떨어지는 지붕
        lineTo(p(0.99f, 0.282f).x, p(0.99f, 0.282f).y) // 스포일러 끝
        lineTo(p(0.972f, 0.262f).x, p(0.972f, 0.262f).y)
        cubicTo(p(0.985f, 0.20f).x, p(0.985f, 0.20f).y, p(1.0f, 0.15f).x, p(1.0f, 0.15f).y, p(0.995f, 0.09f).x, p(0.995f, 0.09f).y)
        lineTo(p(0.975f, 0.06f).x, p(0.975f, 0.06f).y)
        close()
    }
    drawPath(bodyPath, Brush.verticalGradient(listOf(body, body, shade), startY = groundY - l * roof, endY = groundY))
    // 아래 검은 하단 (휠 아치 · 사이드 실)
    drawRoundRect(Color(0xFF16191D), p(0.02f, 0.085f), Size(l * 0.96f, l * 0.03f), CornerRadius(l * 0.01f))

    // 옆 유리 (B 필러로 나눔)
    val window = Path().apply {
        moveTo(p(0.32f, 0.245f).x, p(0.32f, 0.245f).y)
        cubicTo(p(0.38f, 0.29f).x, p(0.38f, 0.29f).y, p(0.44f, roof - 0.022f).x, p(0.44f, roof - 0.022f).y, p(0.51f, roof - 0.022f).x, p(0.51f, roof - 0.022f).y)
        lineTo(p(0.69f, roof - 0.028f).x, p(0.69f, roof - 0.028f).y)
        cubicTo(p(0.77f, roof - 0.034f).x, p(0.77f, roof - 0.034f).y, p(0.84f, 0.29f).x, p(0.84f, 0.29f).y, p(0.87f, 0.258f).x, p(0.87f, 0.258f).y)
        lineTo(p(0.32f, 0.245f).x, p(0.32f, 0.245f).y)
        close()
    }
    drawPath(window, Brush.horizontalGradient(listOf(Glass, Color(0xFF2B3743), Glass), startX = x0 + l * 0.3f, endX = x0 + l * 0.9f))
    drawLine(body, p(0.60f, roof - 0.02f), p(0.60f, 0.25f), strokeWidth = l * 0.012f)
    // 문 경계 · 손잡이 · 허리선
    drawLine(shade.copy(alpha = 0.7f), p(0.33f, 0.235f), p(0.33f, 0.11f), strokeWidth = l * 0.003f)
    drawLine(shade.copy(alpha = 0.7f), p(0.60f, 0.245f), p(0.60f, 0.11f), strokeWidth = l * 0.003f)
    drawLine(shade.copy(alpha = 0.8f), p(0.05f, 0.175f), p(0.97f, 0.215f), strokeWidth = l * 0.003f)
    drawRoundRect(shade, p(0.44f, 0.205f), Size(l * 0.05f, l * 0.008f), CornerRadius(l * 0.004f))
    drawRoundRect(shade, p(0.70f, 0.21f), Size(l * 0.05f, l * 0.008f), CornerRadius(l * 0.004f))
    // 사이드 미러
    drawRoundRect(shade, p(0.30f, 0.27f), Size(l * 0.045f, l * 0.025f), CornerRadius(l * 0.01f))

    // 앞 픽셀 조명 · 뒤 픽셀 조명
    repeat(4) { i -> drawRect(PixelWhite, p(0.008f + i * 0.012f, 0.185f - i * 0.002f), Size(l * 0.008f, l * 0.008f)) }
    repeat(4) { i -> drawRect(PixelRed, p(0.952f + i * 0.01f, 0.245f - i * 0.004f), Size(l * 0.007f, l * 0.007f)) }

    // 바퀴 (에어로 휠)
    listOf(AXLE, 1f - AXLE).forEach { fx ->
        val c = p(fx, WHEEL_R)
        drawCircle(Color(0xFF0B0D10), l * (WHEEL_R + 0.012f), p(fx, WHEEL_R + 0.004f)) // 휠 아치 그늘
        drawCircle(Color(0xFF1A1D21), l * WHEEL_R, c)
        drawCircle(Brush.radialGradient(listOf(Color(0xFFB8BEC6), Color(0xFF6B7179)), center = c, radius = l * WHEEL_R * 0.66f), l * WHEEL_R * 0.66f, c)
        repeat(5) { k ->
            rotate(k * 72f, c) {
                drawLine(Color(0xFF3A3F46), c, Offset(c.x, c.y - l * WHEEL_R * 0.62f), strokeWidth = l * 0.012f)
            }
        }
        drawCircle(Color(0xFF2A2E34), l * WHEEL_R * 0.16f, c)
        drawCircle(Color(0xFF8C939D), l * WHEEL_R * 0.66f, c, style = Stroke(l * 0.004f))
    }
}

private fun DrawScope.pixelRow(start: Offset, width: Float, size: Float, count: Int, color: Color) {
    val gap = (width - size * count) / (count - 1)
    repeat(count) { i -> drawRect(color, Offset(start.x + i * (size + gap), start.y), Size(size, size)) }
}
