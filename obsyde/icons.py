from PyQt6.QtCore import Qt, QSize, QPoint, QPointF, QRect, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath, QLinearGradient

from .constants import C_TEXT, C_TEXT_DIM, C_ACCENT, C_LIKE

def _make_icon(draw_fn, size=24):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(p, size)
    p.end()
    return QIcon(pm)


def icon_app(size=64):
    pm = QPixmap(size, size); pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor(235, 220, 255))
    grad.setColorAt(0.45, QColor(180, 139, 255))
    grad.setColorAt(1.0, QColor(95, 65, 175))
    body = QPainterPath()
    body.moveTo(s*0.50, s*0.08)
    body.lineTo(s*0.86, s*0.40)
    body.lineTo(s*0.66, s*0.92)
    body.lineTo(s*0.34, s*0.92)
    body.lineTo(s*0.14, s*0.40)
    body.closeSubpath()
    p.setBrush(QBrush(grad)); p.setPen(QPen(QColor(255,255,255,225), max(1.5, s*0.03)))
    p.drawPath(body)
    facet = QPen(QColor(255,255,255,140), max(1.0, s*0.018))
    p.setPen(facet); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(s*0.14, s*0.40), QPointF(s*0.86, s*0.40))
    p.drawLine(QPointF(s*0.50, s*0.08), QPointF(s*0.50, s*0.92))
    p.drawLine(QPointF(s*0.34, s*0.92), QPointF(s*0.50, s*0.40))
    p.drawLine(QPointF(s*0.66, s*0.92), QPointF(s*0.50, s*0.40))
    hi = QPainterPath()
    hi.moveTo(s*0.50, s*0.10)
    hi.lineTo(s*0.66, s*0.30)
    hi.lineTo(s*0.50, s*0.40)
    hi.lineTo(s*0.34, s*0.30)
    hi.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255,255,255,90))
    p.drawPath(hi)
    p.end()
    return QIcon(pm)


def _stroke(p, color, w=1.8):
    pen = QPen(QColor(color)); pen.setWidthF(w); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin); p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)


def icon_home(color=C_TEXT, size=24):
    def d(p, s):
        _stroke(p, color)
        path = QPainterPath()
        path.moveTo(4, 11); path.lineTo(12, 4); path.lineTo(20, 11)
        path.moveTo(6, 10); path.lineTo(6, 20); path.lineTo(18, 20); path.lineTo(18, 10)
        p.drawPath(path)
        p.drawRect(QRectF(10, 14, 4, 6))
    return _make_icon(d, size)


def icon_search(color=C_TEXT, size=24):
    def d(p, s):
        _stroke(p, color, 2.0)
        p.drawEllipse(QRectF(4, 4, 12, 12))
        p.drawLine(QPointF(14.5, 14.5), QPointF(20, 20))
    return _make_icon(d, size)


def icon_heart(filled=False, color=C_LIKE, size=24):
    def d(p, s):
        path = QPainterPath()
        path.moveTo(12, 20)
        path.cubicTo(2, 14, 4, 5, 12, 9)
        path.cubicTo(20, 5, 22, 14, 12, 20)
        if filled:
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color)); p.drawPath(path)
        else:
            _stroke(p, color, 1.8); p.drawPath(path)
    return _make_icon(d, size)


def icon_sparkle(color=C_LIKE, size=24):
    def d(p, s):
        p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
        big = QPainterPath()
        big.moveTo(12, 3); big.lineTo(14, 10); big.lineTo(21, 12); big.lineTo(14, 14)
        big.lineTo(12, 21); big.lineTo(10, 14); big.lineTo(3, 12); big.lineTo(10, 10)
        big.closeSubpath()
        p.drawPath(big)
        small = QPainterPath()
        small.moveTo(19.5, 4.5); small.lineTo(20.2, 6.3); small.lineTo(22, 7)
        small.lineTo(20.2, 7.7); small.lineTo(19.5, 9.5); small.lineTo(18.8, 7.7)
        small.lineTo(17, 7); small.lineTo(18.8, 6.3)
        small.closeSubpath()
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawPath(small)
    return _make_icon(d, size)


def icon_headphones(color=C_ACCENT, size=24):
    def d(p, s):
        pen = QPen(QColor(color)); pen.setWidthF(2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        band = QPainterPath()
        band.moveTo(4.5, 14.5)
        band.cubicTo(4.5, 4.5, 19.5, 4.5, 19.5, 14.5)
        p.drawPath(band)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(3.0, 13.0, 5.0, 7.5), 2.0, 2.0)
        p.drawRoundedRect(QRectF(16.0, 13.0, 5.0, 7.5), 2.0, 2.0)
    return _make_icon(d, size)


def icon_plus(color=C_TEXT, size=24):
    def d(p, s):
        _stroke(p, color, 2.0)
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    return _make_icon(d, size)


def icon_play(color="#0f0f17", size=24):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
        path = QPainterPath(); path.moveTo(7, 5); path.lineTo(19, 12); path.lineTo(7, 19); path.closeSubpath()
        p.drawPath(path)
    return _make_icon(d, size)


def icon_pause(color="#0f0f17", size=24):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(6, 5, 4, 14), 1.2, 1.2)
        p.drawRoundedRect(QRectF(14, 5, 4, 14), 1.2, 1.2)
    return _make_icon(d, size)


def icon_prev(color=C_TEXT, size=24):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(5, 6, 2.5, 12), 1, 1)
        path = QPainterPath(); path.moveTo(19, 5); path.lineTo(9, 12); path.lineTo(19, 19); path.closeSubpath()
        p.drawPath(path)
    return _make_icon(d, size)


def icon_next(color=C_TEXT, size=24):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(16.5, 6, 2.5, 12), 1, 1)
        path = QPainterPath(); path.moveTo(5, 5); path.lineTo(15, 12); path.lineTo(5, 19); path.closeSubpath()
        p.drawPath(path)
    return _make_icon(d, size)


def icon_shuffle(color=C_TEXT, size=24):
    def d(p, s):
        _stroke(p, color, 1.9)
        p.drawLine(QPointF(4, 7), QPointF(8, 7))
        path = QPainterPath()
        path.moveTo(8, 7); path.cubicTo(13, 7, 11, 17, 16, 17)
        p.drawPath(path)
        p.drawLine(QPointF(16, 17), QPointF(20, 17))
        p.drawLine(QPointF(18, 15), QPointF(20, 17)); p.drawLine(QPointF(18, 19), QPointF(20, 17))
        path2 = QPainterPath()
        path2.moveTo(4, 17); path2.cubicTo(9, 17, 7, 7, 12, 7)
        p.drawPath(path2)
        p.drawLine(QPointF(18, 5), QPointF(20, 7)); p.drawLine(QPointF(18, 9), QPointF(20, 7))
        p.drawLine(QPointF(16, 7), QPointF(20, 7))
    return _make_icon(d, size)


def icon_trash(color=C_TEXT, size=24):
    def d(p, s):
        _stroke(p, color, 1.8)
        p.drawLine(QPointF(4, 7), QPointF(20, 7))
        p.drawLine(QPointF(10, 4), QPointF(14, 4))
        path = QPainterPath()
        path.moveTo(6, 7); path.lineTo(7, 20); path.lineTo(17, 20); path.lineTo(18, 7)
        p.drawPath(path)
        p.drawLine(QPointF(10, 10), QPointF(10, 17))
        p.drawLine(QPointF(14, 10), QPointF(14, 17))
    return _make_icon(d, size)


def icon_close(color=C_TEXT, size=16):
    def d(p, s):
        _stroke(p, color, 1.6)
        p.drawLine(QPointF(4, 4), QPointF(s-4, s-4))
        p.drawLine(QPointF(s-4, 4), QPointF(4, s-4))
    return _make_icon(d, size)


def icon_min(color=C_TEXT, size=16):
    def d(p, s):
        _stroke(p, color, 1.6)
        p.drawLine(QPointF(4, s-5), QPointF(s-4, s-5))
    return _make_icon(d, size)


def icon_max(color=C_TEXT, size=16):
    def d(p, s):
        _stroke(p, color, 1.4)
        p.drawRect(QRectF(4, 4, s-8, s-8))
    return _make_icon(d, size)


def icon_telegram(color=C_ACCENT, size=22):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen)
        grad = QLinearGradient(0, 0, s, s)
        grad.setColorAt(0, QColor(122, 162, 255))
        grad.setColorAt(1, QColor(180, 139, 255))
        p.setBrush(QBrush(grad))
        p.drawEllipse(1, 1, s-2, s-2)
        pen = QPen(QColor(255,255,255,235)); pen.setWidthF(1.6); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(5, 11.5); path.lineTo(17, 6.5); path.lineTo(14.5, 17); path.lineTo(11, 13.5); path.lineTo(8.5, 15.5)
        p.drawPath(path)
    return _make_icon(d, size)


def icon_eq(color=C_ACCENT, size=22):
    def d(p, s):
        p.setPen(Qt.PenStyle.NoPen)
        c = QColor(color)
        p.setBrush(c)
        bar_count = 10
        gap = 1.5
        bar_w = (s - gap * (bar_count - 1)) / bar_count
        heights = [3, 5, 9, 13, 16, 18, 16, 12, 7, 4]
        for i, h in enumerate(heights):
            x = i * (bar_w + gap)
            y = s - h
            p.drawRoundedRect(QRectF(x, y, bar_w, h), 1.2, 1.2)
    return _make_icon(d, size)

