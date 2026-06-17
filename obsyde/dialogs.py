from pathlib import Path
import math

from PyQt6.QtCore import Qt, QSize, QPoint, QPointF, QRectF, QUrl, QEvent, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QColor, QFont, QCursor, QPixmap, QPainter, QIcon, QPainterPath, QBrush, QPen, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QDialog, QFrame, QPushButton, QToolButton, QLabel,
    QHBoxLayout, QVBoxLayout, QSlider, QSpinBox, QComboBox, QCheckBox,
    QDialogButtonBox, QMessageBox, QSizePolicy, QGraphicsDropShadowEffect,
)

from .constants import C_TEXT, C_TEXT_DIM, C_ACCENT, C_BORDER, C_BG, CONFIG_DIR
from .icons import icon_min, icon_max, icon_close, icon_telegram, icon_trash
from .models import SETTINGS, HIST
from .eq import EqualizerProcessor

class TitleBar(QWidget):
    def __init__(self, owner: "Obsyde"):
        super().__init__(owner)
        self.owner = owner
        self.setObjectName("TitleBar")
        self.setFixedHeight(44)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        h = QHBoxLayout(self); h.setContentsMargins(18, 0, 8, 0); h.setSpacing(2)
        logo_txt = QLabel("obsyde")
        logo_txt.setStyleSheet(f"color: {C_TEXT}; font-weight: 700; font-size: 14px; letter-spacing: 1.2px;")
        h.addWidget(logo_txt)
        h.addSpacing(22)
        self.btn_file = self._mb("\u0424\u0430\u0439\u043b")
        self.btn_lib = self._mb("\u0411\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0430")
        self.btn_about = self._mb("\u041e \u043d\u0430\u0441")
        for b in (self.btn_file, self.btn_lib, self.btn_about):
            h.addWidget(b)
        h.addStretch(1)
        self.btn_min = self._winbtn(icon_min(C_TEXT), "WinBtn")
        self.btn_max = self._winbtn(icon_max(C_TEXT), "WinBtn")
        self.btn_close = self._winbtn(icon_close(C_TEXT), "WinClose")
        h.addWidget(self.btn_min); h.addWidget(self.btn_max); h.addWidget(self.btn_close)
        self.btn_min.clicked.connect(self.owner.showMinimized)
        self.btn_max.clicked.connect(self.owner.toggle_max)
        self.btn_close.clicked.connect(self.owner.close)
        self.btn_file.clicked.connect(lambda: self._popup(self.owner.m_file, self.btn_file))
        self.btn_lib.clicked.connect(lambda: self._popup(self.owner.m_lib, self.btn_lib))
        self.btn_about.clicked.connect(self.owner.open_about)
        self._drag = None

    def _mb(self, text):
        b = QPushButton(text)
        b.setObjectName("MenuBtn")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFlat(True)
        b.setMinimumHeight(30)
        return b

    def _winbtn(self, icon, name):
        b = QToolButton()
        b.setIcon(icon); b.setIconSize(QSize(14, 14))
        b.setFixedSize(40, 30); b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setObjectName(name); b.setAutoRaise(True)
        return b

    def _popup(self, menu, btn):
        gp = btn.mapToGlobal(QPoint(0, btn.height() + 6))
        menu.exec(gp)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.owner.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt.MouseButton.LeftButton) and self._drag is not None:
            if self.owner.isMaximized():
                self.owner.showNormal()
            self.owner.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.owner.toggle_max()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AboutDialog")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 200)
        root = QVBoxLayout(self); root.setContentsMargins(18, 18, 18, 18); root.setSpacing(0)
        self.card = QFrame(); self.card.setObjectName("AboutCard")
        root.addWidget(self.card)
        v = QVBoxLayout(self.card); v.setContentsMargins(26, 22, 26, 22); v.setSpacing(14)
        head = QHBoxLayout(); head.setSpacing(10)
        title = QLabel("\u041e \u043d\u0430\u0441")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 18px; font-weight: 700; letter-spacing: 0.4px;")
        head.addWidget(title); head.addStretch(1)
        x = QToolButton(); x.setIcon(icon_close(C_TEXT_DIM)); x.setIconSize(QSize(12, 12))
        x.setObjectName("AboutClose"); x.setFixedSize(26, 26); x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.clicked.connect(self.accept); head.addWidget(x)
        v.addLayout(head)
        v.addStretch(1)
        row = QHBoxLayout(); row.setSpacing(12); row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic = QLabel(); ic.setPixmap(icon_telegram(size=26).pixmap(26, 26))
        row.addWidget(ic)
        link = QLabel("Telegram: <b style='color:#e9e9f2;'>@heavenly0x</b>")
        link.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 15px;")
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(link)
        v.addLayout(row)
        v.addStretch(1)
        ok = QPushButton("\u041e\u041a"); ok.setObjectName("AccentBtn")
        ok.setCursor(Qt.CursorShape.PointingHandCursor); ok.setFixedHeight(34)
        ok.clicked.connect(self.accept)
        v.addWidget(ok)
        if isinstance(parent, QWidget):
            self.setStyleSheet(parent.styleSheet())
        self._drag = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt.MouseButton.LeftButton) and self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("obsyde")
        self.setMinimumWidth(400)
        self.setMaximumWidth(460)
        self.setObjectName("SettingsDialog")
        v = QVBoxLayout(self); v.setContentsMargins(16, 14, 16, 12); v.setSpacing(7)
        title = QLabel("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 17px; font-weight: 800;")
        v.addWidget(title)

        v.addWidget(self._section("\u0417\u0432\u0443\u043a"))
        row = QHBoxLayout()
        lbl = QLabel("\u0413\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u044c \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e"); lbl.setStyleSheet(f"color: {C_TEXT};")
        row.addWidget(lbl); row.addStretch(1)
        self.s_volume = QSlider(Qt.Orientation.Horizontal)
        self.s_volume.setRange(0, 100); self.s_volume.setFixedWidth(160)
        self.s_volume.setValue(int(SETTINGS.get("default_volume")))
        self.lbl_vol = QLabel(f"{int(SETTINGS.get('default_volume'))}%")
        self.lbl_vol.setStyleSheet(f"color: {C_TEXT_DIM};"); self.lbl_vol.setFixedWidth(46)
        self.s_volume.valueChanged.connect(lambda x: self.lbl_vol.setText(f"{x}%"))
        row.addWidget(self.s_volume); row.addWidget(self.lbl_vol)
        v.addLayout(row)
        self.cb_autoplay = QCheckBox("\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u0432\u043a\u043b\u044e\u0447\u0430\u0442\u044c \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0442\u0440\u0435\u043a")
        self.cb_autoplay.setChecked(bool(SETTINGS.get("autoplay_next")))
        v.addWidget(self.cb_autoplay)

        v.addWidget(self._section("\u041c\u043e\u0439 \u043c\u0438\u043a\u0441"))
        row2 = QHBoxLayout()
        l2 = QLabel("\u0420\u0430\u0437\u043c\u0435\u0440 \u043c\u0438\u043a\u0441\u0430"); l2.setStyleSheet(f"color: {C_TEXT};")
        row2.addWidget(l2); row2.addStretch(1)
        self.spin_mix = QSpinBox()
        self.spin_mix.setRange(10, 50)
        self.spin_mix.setValue(int(SETTINGS.get("mix_size")))
        self.spin_mix.setSuffix(" \u0442\u0440\u0435\u043a\u043e\u0432"); self.spin_mix.setFixedWidth(120)
        row2.addWidget(self.spin_mix)
        v.addLayout(row2)

        v.addWidget(self._section("\u041e\u043a\u043d\u043e"))
        row3 = QHBoxLayout()
        l3 = QLabel("\u0420\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u043e\u043a\u043d\u0430"); l3.setStyleSheet(f"color: {C_TEXT};")
        row3.addWidget(l3); row3.addStretch(1)
        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["960x600", "1080x680", "1280x800", "1440x900", "1600x900", "1920x1080"])
        cur = str(SETTINGS.get("resolution") or "1080x680")
        i = self.cmb_res.findText(cur)
        if i < 0:
            self.cmb_res.addItem(cur); i = self.cmb_res.count() - 1
        self.cmb_res.setCurrentIndex(i); self.cmb_res.setFixedWidth(130)
        row3.addWidget(self.cmb_res)
        v.addLayout(row3)

        row4 = QHBoxLayout()
        l4 = QLabel("\u042d\u0444\u0444\u0435\u043a\u0442 \u0444\u043e\u043d\u0430"); l4.setStyleSheet(f"color: {C_TEXT};")
        row4.addWidget(l4); row4.addStretch(1)
        self.cmb_fx = QComboBox()
        self._fx = [("none", "\u041d\u0435\u0442"), ("rain", "\u0414\u043e\u0436\u0434\u044c"), ("snow", "\u0421\u043d\u0435\u0433"), ("stars", "\u0417\u0432\u0451\u0437\u0434\u044b"), ("bubbles", "\u041f\u0443\u0437\u044b\u0440\u044c\u043a\u0438")]
        for k, lab in self._fx:
            self.cmb_fx.addItem(lab, k)
        cur_fx = str(SETTINGS.get("bg_effect") or "rain")
        for idx, (k, _) in enumerate(self._fx):
            if k == cur_fx:
                self.cmb_fx.setCurrentIndex(idx); break
        self.cmb_fx.setFixedWidth(130)
        row4.addWidget(self.cmb_fx)
        v.addLayout(row4)

        row_op = QHBoxLayout()
        lop = QLabel("\u041f\u0440\u043e\u0437\u0440\u0430\u0447\u043d\u043e\u0441\u0442\u044c \u043e\u043a\u043d\u0430")
        lop.setStyleSheet(f"color: {C_TEXT};")
        row_op.addWidget(lop); row_op.addStretch(1)
        self.s_opacity = QSlider(Qt.Orientation.Horizontal)
        self.s_opacity.setRange(60, 100); self.s_opacity.setFixedWidth(160)
        self.s_opacity.setValue(int(SETTINGS.get("window_opacity") or 100))
        self.lbl_op = QLabel(f"{int(SETTINGS.get('window_opacity') or 100)}%")
        self.lbl_op.setStyleSheet(f"color: {C_TEXT_DIM};"); self.lbl_op.setFixedWidth(46)
        self.s_opacity.valueChanged.connect(lambda x: self.lbl_op.setText(f"{x}%"))
        self.s_opacity.valueChanged.connect(self._live_opacity)
        row_op.addWidget(self.s_opacity); row_op.addWidget(self.lbl_op)
        v.addLayout(row_op)

        self.cb_tray = QCheckBox("\u0421\u0432\u043e\u0440\u0430\u0447\u0438\u0432\u0430\u0442\u044c \u0432 \u0442\u0440\u0435\u0439 \u043f\u0440\u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u0438\u0438")
        self.cb_tray.setChecked(bool(SETTINGS.get("minimize_to_tray")))
        v.addWidget(self.cb_tray)

        v.addWidget(self._section("\u0414\u0430\u043d\u043d\u044b\u0435"))
        clr = QHBoxLayout(); clr.setSpacing(8)
        self.b_hist = QPushButton(f"  \u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0438\u0441\u0442\u043e\u0440\u0438\u044e ({len(HIST.tracks)})")
        self.b_hist.setIcon(icon_trash()); self.b_hist.setIconSize(QSize(16,16))
        self.b_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_hist.clicked.connect(self._clear_hist)
        clr.addWidget(self.b_hist); clr.addStretch(1)
        v.addLayout(clr)

        info = QLabel(f"\u041a\u043e\u043d\u0444\u0438\u0433: {CONFIG_DIR}")
        info.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 10px;")
        info.setWordWrap(True)
        v.addWidget(info)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Save).setText("\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("\u041e\u0442\u043c\u0435\u043d\u0430")
        bb.button(QDialogButtonBox.StandardButton.Save).setObjectName("AccentBtn")
        bb.button(QDialogButtonBox.StandardButton.Save).setCursor(Qt.CursorShape.PointingHandCursor)
        bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        if isinstance(parent, QWidget):
            self.setStyleSheet(parent.styleSheet())

    def _section(self, label):
        l = QLabel(label.upper())
        l.setStyleSheet(f"color: {C_TEXT}; font-size: 10px; letter-spacing: 1.8px; font-weight: 800; padding-top: 3px;")
        return l

    def _live_opacity(self, v):
        try:
            parent = self.parent()
            if parent is not None:
                parent.setWindowOpacity(max(0.4, float(v) / 100.0))
        except Exception:
            pass

    def _clear_hist(self):
        if QMessageBox.question(self, "obsyde", "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0438\u0441\u0442\u043e\u0440\u0438\u044e?") == QMessageBox.StandardButton.Yes:
            HIST.clear()
            self.b_hist.setText(f"  \u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0438\u0441\u0442\u043e\u0440\u0438\u044e ({len(HIST.tracks)})")

    def _save(self):
        SETTINGS.set("default_volume", int(self.s_volume.value()))
        SETTINGS.set("mix_size", int(self.spin_mix.value()))
        SETTINGS.set("minimize_to_tray", bool(self.cb_tray.isChecked()))
        SETTINGS.set("autoplay_next", bool(self.cb_autoplay.isChecked()))
        SETTINGS.set("resolution", self.cmb_res.currentText())
        SETTINGS.set("bg_effect", self.cmb_fx.currentData())
        SETTINGS.set("window_opacity", int(self.s_opacity.value()))
        parent = self.parent()
        if parent is not None and hasattr(parent, "apply_runtime_settings"):
            parent.apply_runtime_settings()
        self.accept()


class FrequencyCurveWidget(QWidget):
    fixedHeight = 110

    def __init__(self, processor: EqualizerProcessor, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.setFixedHeight(self.fixedHeight)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        bg = QColor(C_TEXT_DIM); bg.setAlpha(18)
        p.setBrush(bg); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        bypassed = self.processor.bypassed
        freqs = EqualizerProcessor.BAND_FREQUENCIES
        gains = self.processor.gains
        min_f = 20.0
        max_f = 20000.0

        normal_color = QColor(C_ACCENT) if not bypassed else QColor(C_TEXT_DIM)
        fill_color = QColor(C_ACCENT) if not bypassed else QColor(C_TEXT_DIM)

        pts = []
        margin = 18
        draw_w = w - margin * 2

        for i in range(200):
            t = i / 199.0
            freq = min_f * (max_f / min_f) ** t
            x = margin + t * draw_w

            if freq < freqs[0]:
                gain = gains[0]
            elif freq > freqs[-1]:
                gain = gains[-1]
            else:
                for j in range(len(freqs) - 1):
                    if freqs[j] <= freq <= freqs[j + 1]:
                        f0, f1 = freqs[j], freqs[j + 1]
                        g0, g1 = gains[j], gains[j + 1]
                        l0, l1 = math.log10(f0), math.log10(f1)
                        lf = math.log10(freq)
                        frac = (lf - l0) / (l1 - l0) if l1 != l0 else 0
                        gain = g0 + (g1 - g0) * frac
                        break

            db_range = 24.0
            y_norm = (gain + 12.0) / db_range
            y = h - 12 - y_norm * (h - 24)
            pts.append(QPointF(x, y))

        path = QPainterPath()
        if pts:
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)

        pen = QPen(normal_color)
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(path)

        fill_path = QPainterPath(path)
        if pts:
            fill_path.lineTo(pts[-1].x(), h - 12)
            fill_path.lineTo(pts[0].x(), h - 12)
            fill_path.closeSubpath()
        fill_color.setAlpha(30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill_color)
        p.drawPath(fill_path)

        zero_y = h - 12 - (12.0 / 24.0) * (h - 24)
        zero_pen = QPen(QColor(C_TEXT_DIM))
        zero_pen.setWidthF(0.7)
        zero_pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(zero_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(margin, zero_y), QPointF(w - margin, zero_y))
        p.end()


class EqualizerDialog(QDialog):
    gainChanged = pyqtSignal(int, float)
    bypassToggled = pyqtSignal(bool)
    resetClicked = pyqtSignal()

    def __init__(self, processor: EqualizerProcessor, parent=None):
        super().__init__(parent)
        self.processor = processor
        self._drag_pos = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 390)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("EqCard")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("Эквалайзер")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 14px; font-weight: 700;")
        top.addWidget(title)
        top.addStretch(1)
        self.btn_bypass = QPushButton("Отключить")
        self.btn_bypass.setObjectName("EqBypassOn")
        self.btn_bypass.setCheckable(True)
        self.btn_bypass.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bypass.toggled.connect(self._on_bypass)
        top.addWidget(self.btn_bypass)
        self.btn_reset = QPushButton("Сброс")
        self.btn_reset.setFixedSize(64, 26)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"color: {C_TEXT_DIM}; border:1px solid {C_BORDER}; border-radius:6px; font-size:11px; background:transparent;")
        self.btn_reset.clicked.connect(lambda: self.resetClicked.emit())
        top.addWidget(self.btn_reset)
        x_btn = QToolButton()
        x_btn.setIcon(icon_close(C_TEXT_DIM))
        x_btn.setIconSize(QSize(12, 12))
        x_btn.setFixedSize(24, 24)
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.setAutoRaise(True)
        x_btn.clicked.connect(self.accept)
        top.addWidget(x_btn)
        cv.addLayout(top)

        self.curve_widget = FrequencyCurveWidget(processor, self)
        cv.addWidget(self.curve_widget)

        bands_w = QWidget()
        bands_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        bh = QHBoxLayout(bands_w)
        bh.setContentsMargins(4, 0, 4, 0)
        bh.setSpacing(2)

        self.sliders = []
        self.labels = []
        for i, name in enumerate(EqualizerProcessor.BAND_NAMES):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl = QLabel("0")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(32)
            lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 9px; font-weight: 600;")
            col.addWidget(lbl)
            self.labels.append(lbl)

            sl = QSlider(Qt.Orientation.Vertical)
            sl.setRange(-120, 120)
            sl.setValue(0)
            sl.setFixedSize(28, 110)
            sl.setObjectName("EqSlider")
            sl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            sl.valueChanged.connect(lambda v, idx=i: self._on_slider(idx, v))
            col.addWidget(sl)
            self.sliders.append(sl)

            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 9px;")
            name_lbl.setFixedWidth(32)
            col.addWidget(name_lbl)

            bh.addLayout(col)

        cv.addWidget(bands_w)
        root.addWidget(card)

        if isinstance(parent, QWidget):
            self.setStyleSheet(parent.styleSheet())

    def _on_slider(self, idx, value):
        gain_db = value / 10.0
        self.labels[idx].setText(f"{gain_db:+.1f}")
        if abs(gain_db) > 1.0:
            self.labels[idx].setStyleSheet(f"color: {C_ACCENT}; font-size: 9px; font-weight: 700;")
        else:
            self.labels[idx].setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 9px; font-weight: 600;")
        self.gainChanged.emit(idx, gain_db)

    def _on_bypass(self, checked):
        self.processor.bypassed = checked
        if checked:
            self.btn_bypass.setText("Включить")
            self.btn_bypass.setObjectName("EqBypassOff")
        else:
            self.btn_bypass.setText("Отключить")
            self.btn_bypass.setObjectName("EqBypassOn")
        self.btn_bypass.style().unpolish(self.btn_bypass)
        self.btn_bypass.style().polish(self.btn_bypass)
        self.curve_widget.update()
        self.bypassToggled.emit(checked)

    def load_gains(self, gains):
        for i, g in enumerate(gains):
            clamped = max(-12.0, min(12.0, g))
            self.sliders[i].setValue(int(round(clamped * 10)))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt.MouseButton.LeftButton) and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

