import math, random

from PyQt6.QtCore import Qt, QSize, QRect, QRectF, QPoint, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QRadialGradient, QFontMetrics, QFont
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QSizePolicy, QPushButton, QFrame

from .constants import C_TEXT, C_TEXT_DIM, C_ACCENT, C_ACCENT2, C_LIKE, C_SURFACE, C_BORDER, C_BG
from .icons import icon_heart, icon_plus, icon_play
from .models import Track, LIB

class EqualizerIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.phase = [random.random()*6.28 for _ in range(3)]
        self._active = False
        self.t = QTimer(self); self.t.timeout.connect(self._tick); self.t.start(80)
    def setActive(self, v):
        self._active = v; self.update()
    def _tick(self):
        if self._active:
            for i in range(3):
                self.phase[i] += 0.35 + i*0.07
            self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(C_ACCENT)); p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            h = (math.sin(self.phase[i])*0.4 + 0.6) * 13 if self._active else 4
            p.drawRoundedRect(QRectF(2+i*5, (18-h)/2, 3, h), 1.2, 1.2)
        p.end()


class BgEffect(QWidget):
    def __init__(self, parent=None, kind="rain"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.kind = kind
        self.particles = []
        self._init_particles()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(45)
    def set_kind(self, kind):
        self.kind = kind
        self._init_particles()
        self.update()
    def apply_shake(self, dx, dy):
        if self.kind != "bubbles" or not self.particles:
            return
        mag = (dx * dx + dy * dy) ** 0.5
        if mag < 1.5:
            return
        sx = max(-32.0, min(32.0, -float(dx) * 0.45))
        sy = max(-32.0, min(32.0, -float(dy) * 0.45))
        for p in self.particles:
            scale = 0.55 + (float(p.get("s", 1.0)) / 12.0) + random.uniform(-0.12, 0.12)
            p["vx"] = p.get("vx", 0.0) + sx * scale
            p["vy"] = p.get("vy", 0.0) + sy * scale
    def _init_particles(self):
        w = max(self.width(), 800); h = max(self.height(), 500)
        self.particles = []
        n = {"none":0, "rain":110, "snow":70, "stars":90, "bubbles":35}.get(self.kind, 0)
        for _ in range(n):
            base_v = random.uniform(4, 9) if self.kind == "rain" else random.uniform(0.4, 1.8)
            self.particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "v": base_v,
                "s": random.uniform(1, 3 if self.kind != "bubbles" else 6),
                "a": random.randint(40, 160),
                "drift": random.uniform(-0.3, 0.3),
                "phase": random.uniform(0, 6.28),
                "vx": 0.0,
                "vy": 0.0,
            })
    def resizeEvent(self, e):
        self._init_particles()
        super().resizeEvent(e)
    def _tick(self):
        if self.kind == "none" or not self.particles:
            return
        w, h = self.width(), self.height()
        for p in self.particles:
            k = self.kind
            if k == "rain":
                p["y"] += p["v"]; p["x"] += p["drift"]
                if p["y"] > h: p["y"] = -10; p["x"] = random.uniform(0, w)
            elif k == "snow":
                p["y"] += p["v"] * 0.6; p["x"] += math.sin(p["phase"]) * 0.6; p["phase"] += 0.03
                if p["y"] > h: p["y"] = -10; p["x"] = random.uniform(0, w)
            elif k == "stars":
                p["phase"] = p.get("phase", 0.0) + 0.14 + (p.get("s", 1.0) * 0.012)
                p["a"] = int(120 + 100 * math.sin(p["phase"]))
                p["x"] += math.cos(p["phase"] * 0.45) * 0.9 + p.get("drift", 0.0) * 0.4
                p["y"] -= 0.45 + (p.get("s", 1.0) * 0.18)
                if p["y"] < -10:
                    p["y"] = h + 10
                    p["x"] = random.uniform(0, w)
                if p["x"] < -10: p["x"] = w + 6
                elif p["x"] > w + 10: p["x"] = -6
            elif k == "bubbles":
                p["y"] -= p["v"] * 0.6; p["x"] += math.sin(p["phase"]) * 0.4; p["phase"] += 0.02
                p["x"] += p.get("vx", 0.0); p["y"] += p.get("vy", 0.0)
                p["vx"] = p.get("vx", 0.0) * 0.86
                p["vy"] = p.get("vy", 0.0) * 0.86
                if p["x"] < -40: p["x"] = w + 20
                elif p["x"] > w + 40: p["x"] = -20
                if p["y"] < -20: p["y"] = h + 10; p["x"] = random.uniform(0, w)
                elif p["y"] > h + 40: p["y"] = -10
        self.update()
    def paintEvent(self, e):
        if self.kind == "none" or not self.particles:
            return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for prt in self.particles:
            k = self.kind
            if k == "rain":
                pen = QPen(QColor(180, 200, 255, prt["a"])); pen.setWidthF(prt["s"]*0.7)
                p.setPen(pen)
                p.drawLine(QPointF(prt["x"], prt["y"]), QPointF(prt["x"]-2, prt["y"]+10))
            elif k == "snow":
                p.setBrush(QColor(255,255,255, prt["a"])); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(prt["x"], prt["y"]), prt["s"], prt["s"])
            elif k == "stars":
                a = max(20, min(255, int(prt["a"])))
                r = prt["s"] * 0.7 + 0.45 * math.sin(prt["phase"] * 0.85)
                if r < 0.4: r = 0.4
                p.setBrush(QColor(255,255,255, a)); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(prt["x"], prt["y"]), r, r)
                if prt["s"] > 1.6:
                    pen = QPen(QColor(255,255,255, max(20, a // 3))); pen.setWidthF(0.7)
                    p.setPen(pen)
                    spike = r * 2.6
                    p.drawLine(QPointF(prt["x"]-spike, prt["y"]), QPointF(prt["x"]+spike, prt["y"]))
                    p.drawLine(QPointF(prt["x"], prt["y"]-spike), QPointF(prt["x"], prt["y"]+spike))
            elif k == "bubbles":
                p.setBrush(QColor(180, 139, 255, int(prt["a"]*0.3)))
                p.setPen(QPen(QColor(255,255,255, prt["a"]//2)))
                r = prt["s"]*3
                p.drawEllipse(QPointF(prt["x"], prt["y"]), r, r)
        p.end()


class TrackRow(QWidget):
    play_clicked = pyqtSignal(object)
    like_toggled = pyqtSignal(object)
    add_clicked = pyqtSignal(object)
    menu_clicked = pyqtSignal(object, object)

    def __init__(self, tr: Track, index: int, parent=None):
        super().__init__(parent)
        self.tr = tr; self.index = index
        self.is_playing = False
        self.setObjectName("TrackRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        h = QHBoxLayout(self); h.setContentsMargins(12, 8, 12, 8); h.setSpacing(12)
        self.idx_lbl = QLabel(str(index + 1))
        self.idx_lbl.setFixedWidth(22)
        self.idx_lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px;")
        self.idx_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.eq = EqualizerIndicator()
        self.eq.setVisible(False)
        h.addWidget(self.idx_lbl); h.addWidget(self.eq)
        col = QVBoxLayout(); col.setSpacing(2)
        self.title = QLabel(tr.title or "\u2014")
        self.title.setStyleSheet(f"color: {C_TEXT}; font-size: 13px; font-weight: 500;")
        self.artist = QLabel(tr.artist or "")
        self.artist.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        col.addWidget(self.title); col.addWidget(self.artist)
        h.addLayout(col, 1)
        self.dur = QLabel(self._fmt(tr.duration_ms))
        self.dur.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        h.addWidget(self.dur)
        self.btn_like = QToolButton(); self.btn_like.setAutoRaise(True)
        self.btn_like.setIconSize(QSize(18, 18))
        self.btn_like.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_like_icon()
        self.btn_like.clicked.connect(lambda: self.like_toggled.emit(self.tr))
        h.addWidget(self.btn_like)
        self.btn_add = QToolButton(); self.btn_add.setAutoRaise(True)
        self.btn_add.setIcon(icon_plus(C_TEXT_DIM)); self.btn_add.setIconSize(QSize(18, 18))
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(lambda: self.add_clicked.emit(self.tr))
        h.addWidget(self.btn_add)
        self.btn_play = QToolButton(); self.btn_play.setAutoRaise(True)
        self.btn_play.setIcon(icon_play(C_TEXT)); self.btn_play.setIconSize(QSize(18, 18))
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(lambda: self.play_clicked.emit(self.tr))
        h.addWidget(self.btn_play)

    def contextMenuEvent(self, e):
        self.menu_clicked.emit(self.tr, e.globalPos())

    def _fmt(self, ms):
        s = max(0, ms // 1000)
        return f"{s//60}:{s%60:02d}"

    def set_playing(self, playing):
        if bool(playing) == bool(self.is_playing):
            return
        self.is_playing = playing
        try:
            self.eq.setVisible(playing)
            self.eq.setActive(playing)
            self.idx_lbl.setVisible(not playing)
        except Exception:
            pass
        if playing:
            self.setStyleSheet("QWidget#TrackRow { background: rgba(180,139,255,0.20); border: 2px solid rgba(0,0,0,0.85); border-radius: 10px; }")
        else:
            self.setStyleSheet("")

    def _refresh_like_icon(self):
        liked = LIB.is_liked(self.tr)
        self.btn_like.setIcon(icon_heart(liked, C_LIKE if liked else C_TEXT_DIM))

