import sys, os, json, random, time, traceback
from pathlib import Path
from dataclasses import asdict
from typing import Optional, List

from PyQt6.QtCore import (
    Qt, QSize, QUrl, QTimer, QRect, QRectF, QPoint, QPointF, QEvent,
    QPropertyAnimation, QEasingCurve, QAbstractAnimation,
)
from PyQt6.QtGui import (
    QIcon, QPainter, QColor, QBrush, QPen, QPainterPath, QAction, QCursor,
    QGuiApplication, QPixmap, QPalette, QFont,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QFrame, QStackedWidget,
    QScrollArea, QSlider, QToolButton, QSizePolicy, QMessageBox, QFileDialog,
    QSystemTrayIcon, QMenu, QInputDialog, QGraphicsOpacityEffect, QWidgetAction,
    QComboBox,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from .constants import (
    CONFIG_DIR, PL_DIR,
    C_BG, C_BG2, C_SURFACE, C_SURFACE2, C_BORDER, C_TEXT, C_TEXT_DIM,
    C_ACCENT, C_ACCENT2, C_LIKE,
)
from .style import _CSS_TEMPLATE, stylesheet
from .icons import (
    icon_app, icon_home, icon_search, icon_heart, icon_sparkle, icon_plus,
    icon_play, icon_pause, icon_prev, icon_next, icon_shuffle, icon_trash,
    icon_close, icon_min, icon_max, icon_eq,
)
from .models import Track, Library, History, Settings, LIB, HIST, SETTINGS
from .api import API, SearchWorker, StreamWorker, MixWorker
from .eq import EqualizerProcessor, EQStreamPlayer
from .widgets import EqualizerIndicator, BgEffect, TrackRow
from .dialogs import TitleBar, AboutDialog, SettingsDialog, EqualizerDialog

class Obsyde(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("obsyde")
        self.setWindowIcon(icon_app())
        try:
            w, h = [int(x) for x in str(SETTINGS.get("resolution") or "1080x680").split("x")]
        except Exception:
            w, h = 1080, 680
        self.resize(w, h)
        self.setMinimumSize(860, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self._drag_pos = None
        self._resize_edge = None
        self._resize_geo = None
        self._resize_start = None

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self._eq_processor = EqualizerProcessor(sample_rate=44100, channels=2)
        saved = SETTINGS.get("eq_gains")
        if saved and len(saved) == len(self._eq_processor.gains):
            self._eq_processor.gains = [max(-12, min(12, g)) for g in saved]
            self._eq_processor._dirty = True
        self._eq_player = EQStreamPlayer(self._eq_processor, self)
        self._eq_player.stateChanged.connect(self._on_eq_state)
        self._eq_player.errorOccurred.connect(self._on_eq_error)
        self._eq_dialog: Optional[EqualizerDialog] = None
        self._eq_active = False
        self._set_volume_curve(SETTINGS.get("default_volume"))

        self.queue: list[Track] = []
        self.current_index: int = -1
        self.search_results: list[Track] = []
        self.mix_tracks: list[Track] = []
        self.current_view: str = "home"
        self.current_playlist: Optional[str] = None
        self._search_worker: Optional[SearchWorker] = None
        self._stream_worker: Optional[StreamWorker] = None
        self._mix_worker: Optional[MixWorker] = None
        self._user_seeking = False
        self._old_workers: list = []
        self.tray: Optional[QSystemTrayIcon] = None

        self._build_menus()
        self._build_ui()
        self._build_tray()
        self._connect_signals()
        self._install_shortcuts()
        self._restore_queue()
        self._show_view("home")
        self.setStyleSheet(self._stylesheet())

    def _set_volume_curve(self, v):
        x = max(0, min(100, int(v))) / 100.0
        self.audio.setVolume(x ** 3)
        if hasattr(self, "_eq_player"):
            self._eq_player.set_volume(x ** 3 * 0.7)

    def toggle_max(self):
        if self.isMaximized():
            self.showNormal()

    def _on_eq_toggled(self, checked: bool):
        try:
            if checked:
                self._ensure_eq_dialog()
                self._position_eq_dialog()
                self._eq_active = True
                self._eq_dialog.show()
                self._eq_dialog.raise_()
                if self._current_track() and not self._eq_processor.bypassed:
                    QTimer.singleShot(200, self._on_stream_url_current)
            else:
                self._eq_active = False
                if self._eq_dialog:
                    self._eq_dialog.hide()
                if self._eq_player.is_playing():
                    self._eq_player.stop()
                    cur = self._current_track()
                    if cur is not None:
                        self.play_at(self.current_index)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка EQ", f"Ошибка при включении EQ: {ex}")

    def _ensure_eq_dialog(self):
        if self._eq_dialog is None:
            self._eq_dialog = EqualizerDialog(self._eq_processor, self)
            self._eq_dialog.gainChanged.connect(self._on_eq_gain)
            self._eq_dialog.bypassToggled.connect(self._on_eq_bypass)
            self._eq_dialog.resetClicked.connect(self._on_eq_reset)
            self._eq_player.positionChanged.connect(self._on_eq_pos)
            self._eq_player.trackEnded.connect(self._on_eq_track_ended)
        return self._eq_dialog

    def _position_eq_dialog(self):
        if self._eq_dialog is None:
            return
        btn_center = self.btn_eq.mapToGlobal(self.btn_eq.rect().center())
        dlg_w = self._eq_dialog.width()
        x = btn_center.x() - dlg_w // 2
        screen = QGuiApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            x = max(sg.left() + 8, min(x, sg.right() - dlg_w - 8))
        y = btn_center.y() - self._eq_dialog.height() - 16
        if y < 100:
            y = self.mapToGlobal(self.rect().topLeft()).y() + 60
        self._eq_dialog.move(x, int(max(50, y)))

    def _on_eq_gain(self, band_idx: int, gain_db: float):
        self._eq_processor.set_gain(band_idx, gain_db)
        SETTINGS.set("eq_gains", self._eq_processor.gains.copy())

    def _on_eq_bypass(self, bypassed: bool):
        self._eq_player.processor.bypassed = bypassed
        if bypassed:
            if self._eq_player.is_playing():
                self._eq_player.stop()
                cur = self._current_track()
                if cur is not None:
                    self.play_at(self.current_index)
        else:
            if (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                    and self._current_track()):
                self._on_stream_url_current()

    def _on_eq_reset(self):
        self._eq_processor.reset()
        SETTINGS.set("eq_gains", self._eq_processor.gains.copy())

    def _on_eq_pos(self, ms):
        if self._user_seeking:
            return
        tr = self._current_track()
        d = tr.duration_ms if tr else 0
        if d > 0:
            self.progress.setValue(int(ms / d * 1000))
        self.pos_lbl.setText(self._fmt_ms(ms))

    def _on_eq_state(self, state: str):
        if state == "playing":
            self.btn_play.setIcon(icon_pause("#0f0f17"))
            tr = self._current_track()
            if tr and tr.duration_ms:
                self.dur_lbl.setText(self._fmt_ms(tr.duration_ms))
        elif state in ("stopped", "paused"):
            self.btn_play.setIcon(icon_play("#0f0f17"))

    def _on_eq_track_ended(self):
        if SETTINGS.get("autoplay_next"):
            self.play_next()

    def _on_eq_error(self, msg: str):
        QMessageBox.warning(self, "Проигрывание", msg)

    def _build_menus(self):
        self.m_file = QMenu(self); self.m_file.setObjectName("AppMenu")
        a_import = QAction("\u0418\u043c\u043f\u043e\u0440\u0442 \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u0430\u2026", self); a_import.triggered.connect(self.import_playlist); self.m_file.addAction(a_import)
        a_export = QAction("\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0442\u0435\u043a\u0443\u0449\u0435\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430\u2026", self); a_export.triggered.connect(self.export_current_list); self.m_file.addAction(a_export)
        self.m_file.addSeparator()
        a_settings = QAction("\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438\u2026", self); a_settings.setShortcut("Ctrl+,"); a_settings.triggered.connect(self.open_settings); self.m_file.addAction(a_settings)
        self.m_file.addSeparator()
        a_quit = QAction("\u0412\u044b\u0445\u043e\u0434", self); a_quit.setShortcut("Ctrl+Q"); a_quit.triggered.connect(self._quit_app); self.m_file.addAction(a_quit)

        self.m_lib = QMenu(self); self.m_lib.setObjectName("AppMenu")
        a_home = QAction("\u0413\u043b\u0430\u0432\u043d\u0430\u044f", self); a_home.triggered.connect(lambda: self._show_view("home")); self.m_lib.addAction(a_home)
        a_new = QAction("\u041d\u043e\u0432\u044b\u0439 \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u2026", self); a_new.setShortcut("Ctrl+N"); a_new.triggered.connect(self.create_playlist_dialog); self.m_lib.addAction(a_new)
        a_liked = QAction("\u041b\u044e\u0431\u0438\u043c\u044b\u0435", self); a_liked.triggered.connect(lambda: self._show_view("liked")); self.m_lib.addAction(a_liked)

    def open_about(self):
        d = AboutDialog(self)
        d.exec()

    def _build_ui(self):
        self.container = QWidget()
        self.container.setObjectName("WinContainer")
        self.container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(self.container)

        cl = QVBoxLayout(self.container); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)

        self.titlebar = TitleBar(self)
        cl.addWidget(self.titlebar)

        cl.addWidget(self._build_topbar())

        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0)
        self.sidebar = self._build_playlists_panel()
        body.addWidget(self.sidebar)
        self.stack = QStackedWidget(); self.stack.setObjectName("Stack")
        body.addWidget(self.stack, 1)
        self.page_home = self._build_home_page()
        self.page_search = self._build_search_page()
        self.page_list = self._build_list_page()
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_search)
        self.stack.addWidget(self.page_list)
        body_wrap = QWidget(); body_wrap.setLayout(body)
        cl.addWidget(body_wrap, 1)

        cl.addWidget(self._build_player_bar())

        self.bg_fx = BgEffect(self.container, kind=str(SETTINGS.get("bg_effect") or "rain"))
        self.bg_fx.lower()
        self._update_bg_geom()

    def _update_bg_geom(self):
        if hasattr(self, "bg_fx") and hasattr(self, "container"):
            self.bg_fx.setGeometry(0, 0, self.container.width(), self.container.height())

    def _build_topbar(self):
        w = QWidget(); w.setObjectName("TopBar")
        h = QHBoxLayout(w); h.setContentsMargins(20, 12, 20, 10); h.setSpacing(10)
        self.btn_home = QPushButton("  \u0413\u043b\u0430\u0432\u043d\u0430\u044f")
        self.btn_home.setIcon(icon_home(C_TEXT)); self.btn_home.setIconSize(QSize(18, 18))
        self.btn_search = QPushButton("  \u041f\u043e\u0438\u0441\u043a")
        self.btn_search.setIcon(icon_search(C_TEXT)); self.btn_search.setIconSize(QSize(18, 18))
        self.btn_liked = QPushButton("\u041b\u044e\u0431\u0438\u043c\u044b\u0435")
        for b in (self.btn_home, self.btn_search, self.btn_liked):
            b.setCheckable(True); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setObjectName("NavBtn"); b.setMinimumHeight(40); b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h.addWidget(self.btn_home); h.addWidget(self.btn_search); h.addWidget(self.btn_liked)
        h.addStretch(1)
        return w

    def _build_playlists_panel(self):
        w = QWidget(); w.setObjectName("Sidebar")
        w.setFixedWidth(220)
        l = QVBoxLayout(w); l.setContentsMargins(14, 14, 14, 12); l.setSpacing(4)
        row = QHBoxLayout(); row.setContentsMargins(6, 4, 6, 6)
        cap = QLabel("\u041f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u044b")
        cap.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; letter-spacing: 1.2px; font-weight: 600;")
        row.addWidget(cap, 1)
        add_pl = QToolButton(); add_pl.setIcon(icon_plus(C_TEXT_DIM)); add_pl.setIconSize(QSize(16, 16))
        add_pl.setAutoRaise(True); add_pl.setCursor(Qt.CursorShape.PointingHandCursor)
        add_pl.setToolTip("\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442"); add_pl.clicked.connect(self.create_playlist_dialog)
        row.addWidget(add_pl)
        l.addLayout(row)
        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("PlaylistList")
        self.playlist_list.setFrameShape(QFrame.Shape.NoFrame)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_context_menu)
        self.playlist_list.itemClicked.connect(self._on_playlist_clicked)
        l.addWidget(self.playlist_list, 1)
        self._refresh_playlist_list()
        return w

    def _build_home_page(self):
        page = QWidget()
        v = QVBoxLayout(page); v.setContentsMargins(28, 22, 28, 14); v.setSpacing(16)

        hero = QWidget()
        hl = QVBoxLayout(hero); hl.setContentsMargins(0, 0, 0, 0); hl.setSpacing(2)
        eyebrow = QLabel("\u0414\u041e\u0411\u0420\u041e \u041f\u041e\u0416\u0410\u041b\u041e\u0412\u0410\u0422\u042c")
        eyebrow.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; letter-spacing: 3px; font-weight: 700;")
        title_h = QLabel("obsyde")
        title_h.setStyleSheet(f"color: {C_TEXT}; font-size: 32px; font-weight: 800;")
        hl.addWidget(eyebrow); hl.addWidget(title_h)
        v.addWidget(hero)

        mix_head = QWidget()
        mh = QHBoxLayout(mix_head); mh.setContentsMargins(0, 6, 0, 0); mh.setSpacing(8)
        mt = QLabel("\u041c\u043e\u0439 \u043c\u0438\u043a\u0441")
        mt.setStyleSheet(f"color: {C_TEXT}; font-size: 20px; font-weight: 700;")
        mh.addWidget(mt)
        self.mix_status = QLabel(""); self.mix_status.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px;")
        mh.addWidget(self.mix_status); mh.addStretch(1)
        self.btn_mix_refresh = QPushButton("  \u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c")
        self.btn_mix_refresh.setIcon(icon_shuffle()); self.btn_mix_refresh.setIconSize(QSize(16, 16))
        self.btn_mix_refresh.setToolTip("\u041f\u043e\u0434\u043e\u0431\u0440\u0430\u0442\u044c \u0434\u0440\u0443\u0433\u0438\u0435 \u0442\u0440\u0435\u043a\u0438")
        self.btn_mix_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mix_refresh.setObjectName("MixRefresh")
        self.btn_mix_refresh.clicked.connect(self.refresh_mix)
        mh.addWidget(self.btn_mix_refresh)
        self.btn_mix_play = QPushButton("  \u0418\u0433\u0440\u0430\u0442\u044c \u0432\u0441\u0451")
        self.btn_mix_play.setIcon(icon_play("#0f0f17")); self.btn_mix_play.setIconSize(QSize(14, 14))
        self.btn_mix_play.setObjectName("AccentBtn"); self.btn_mix_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mix_play.clicked.connect(self.play_mix_from_start)
        mh.addWidget(self.btn_mix_play)
        v.addWidget(mix_head)

        self.mix_scroll = QScrollArea(); self.mix_scroll.setWidgetResizable(True)
        self.mix_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.mix_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.mix_scroll.viewport().setAutoFillBackground(False)
        self.mix_holder = QWidget()
        self.mix_holder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.mix_holder.setAutoFillBackground(False)
        self.mix_layout = QVBoxLayout(self.mix_holder); self.mix_layout.setContentsMargins(0, 0, 0, 0); self.mix_layout.setSpacing(2)
        self.mix_layout.addStretch(1)
        self.mix_scroll.setWidget(self.mix_holder)
        v.addWidget(self.mix_scroll, 1)
        return page

    def _build_search_page(self):
        page = QWidget()
        v = QVBoxLayout(page); v.setContentsMargins(28, 22, 28, 14); v.setSpacing(12)
        head = QLabel("\u041f\u043e\u0438\u0441\u043a")
        head.setStyleSheet(f"color: {C_TEXT}; font-size: 24px; font-weight: 700;")
        v.addWidget(head)
        bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0442\u0440\u0435\u043a\u0430 \u0438\u043b\u0438 \u0441\u0441\u044b\u043b\u043a\u0430\u2026")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(38)
        bar.addWidget(self.search_input, 1)
        self.search_go = QPushButton("  \u041d\u0430\u0439\u0442\u0438")
        self.search_go.setIcon(icon_search("#0f0f17")); self.search_go.setIconSize(QSize(16, 16))
        self.search_go.setObjectName("AccentBtn"); self.search_go.setCursor(Qt.CursorShape.PointingHandCursor)
        bar.addWidget(self.search_go)
        v.addLayout(bar)
        self.search_status = QLabel("")
        self.search_status.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px;")
        v.addWidget(self.search_status)
        self.search_scroll = QScrollArea(); self.search_scroll.setWidgetResizable(True)
        self.search_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.search_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.search_scroll.viewport().setAutoFillBackground(False)
        self.search_holder = QWidget()
        self.search_holder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.search_holder.setAutoFillBackground(False)
        self.search_layout = QVBoxLayout(self.search_holder); self.search_layout.setContentsMargins(0,0,0,0); self.search_layout.setSpacing(2)
        self.search_layout.addStretch(1)
        self.search_scroll.setWidget(self.search_holder)
        v.addWidget(self.search_scroll, 1)
        return page

    def _build_list_page(self):
        page = QWidget()
        v = QVBoxLayout(page); v.setContentsMargins(28, 22, 28, 14); v.setSpacing(10)
        head = QHBoxLayout()
        self.list_title = QLabel("")
        self.list_title.setStyleSheet(f"color: {C_TEXT}; font-size: 24px; font-weight: 700;")
        head.addWidget(self.list_title); head.addStretch(1)
        self.btn_list_play = QPushButton("  \u0418\u0433\u0440\u0430\u0442\u044c")
        self.btn_list_play.setIcon(icon_play("#0f0f17")); self.btn_list_play.setIconSize(QSize(14, 14))
        self.btn_list_play.setObjectName("AccentBtn"); self.btn_list_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_list_play.clicked.connect(self.play_list_from_start)
        head.addWidget(self.btn_list_play)
        self.btn_list_shuffle = QToolButton()
        self.btn_list_shuffle.setIcon(icon_shuffle()); self.btn_list_shuffle.setIconSize(QSize(18, 18))
        self.btn_list_shuffle.setToolTip("\u041f\u0435\u0440\u0435\u043c\u0435\u0448\u0430\u0442\u044c \u0438 \u0438\u0433\u0440\u0430\u0442\u044c"); self.btn_list_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_list_shuffle.setAutoRaise(True)
        self.btn_list_shuffle.clicked.connect(self.shuffle_current_list_and_play)
        head.addWidget(self.btn_list_shuffle)
        v.addLayout(head)
        self.list_scroll = QScrollArea(); self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.list_scroll.viewport().setAutoFillBackground(False)
        self.list_holder = QWidget()
        self.list_holder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.list_holder.setAutoFillBackground(False)
        self.list_layout = QVBoxLayout(self.list_holder); self.list_layout.setContentsMargins(0,0,0,0); self.list_layout.setSpacing(2)
        self.list_layout.addStretch(1)
        self.list_scroll.setWidget(self.list_holder)
        v.addWidget(self.list_scroll, 1)
        return page

    def _build_player_bar(self):
        w = QWidget(); w.setObjectName("PlayerBar")
        w.setFixedHeight(86)
        h = QHBoxLayout(w); h.setContentsMargins(18, 10, 18, 12); h.setSpacing(14)
        info = QVBoxLayout(); info.setSpacing(2)
        self.now_title = QLabel("\u2014"); self.now_title.setStyleSheet(f"color: {C_TEXT}; font-weight: 600;")
        self.now_artist = QLabel(""); self.now_artist.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px;")
        info.addWidget(self.now_title); info.addWidget(self.now_artist)
        info_w = QWidget(); info_w.setLayout(info); info_w.setMinimumWidth(180); info_w.setMaximumWidth(280)
        h.addWidget(info_w)
        center = QVBoxLayout(); center.setSpacing(4)
        ctr = QHBoxLayout(); ctr.setSpacing(10); ctr.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.btn_prev = QToolButton(); self.btn_prev.setIcon(icon_prev()); self.btn_prev.setIconSize(QSize(16, 16))
        self.btn_prev.setObjectName("SideBtn"); self.btn_prev.setFixedSize(32, 32); self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_play = QToolButton(); self.btn_play.setIcon(icon_play("#0f0f17")); self.btn_play.setIconSize(QSize(18, 18))
        self.btn_play.setObjectName("PlayBtn"); self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setFixedSize(38, 38); self.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_next = QToolButton(); self.btn_next.setIcon(icon_next()); self.btn_next.setIconSize(QSize(16, 16))
        self.btn_next.setObjectName("SideBtn"); self.btn_next.setFixedSize(32, 32); self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ctr.addWidget(self.btn_prev); ctr.addWidget(self.btn_play); ctr.addWidget(self.btn_next)
        center.addLayout(ctr)
        prow = QHBoxLayout(); prow.setSpacing(8)
        self.pos_lbl = QLabel("0:00"); self.pos_lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 10px;"); self.pos_lbl.setFixedWidth(34)
        self.progress = QSlider(Qt.Orientation.Horizontal); self.progress.setRange(0, 1000)
        self.dur_lbl = QLabel("0:00"); self.dur_lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 10px;"); self.dur_lbl.setFixedWidth(34); self.dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        prow.addWidget(self.pos_lbl); prow.addWidget(self.progress, 1); prow.addWidget(self.dur_lbl)
        center.addLayout(prow)
        cw = QWidget(); cw.setLayout(center)
        h.addWidget(cw, 1)
        vol_w = QHBoxLayout(); vol_w.setSpacing(8)
        vlbl = QLabel("\u266a"); vlbl.setStyleSheet(f"color: {C_TEXT_DIM};")
        self.volume = QSlider(Qt.Orientation.Horizontal); self.volume.setRange(0, 100); self.volume.setFixedWidth(120)
        self.volume.setValue(int(SETTINGS.get("default_volume")))
        vol_w.addWidget(vlbl); vol_w.addWidget(self.volume)

        self.btn_eq = QToolButton()
        self.btn_eq.setIcon(icon_eq(C_ACCENT)); self.btn_eq.setIconSize(QSize(18, 18))
        self.btn_eq.setObjectName("EqBtn")
        self.btn_eq.setCheckable(True)
        self.btn_eq.setToolTip("Эквалайзер")
        self.btn_eq.setFixedSize(32, 32)
        self.btn_eq.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eq.toggled.connect(self._on_eq_toggled)
        vol_w.addWidget(self.btn_eq)

        vol_box = QWidget(); vol_box.setLayout(vol_w); vol_box.setMaximumWidth(170)
        h.addWidget(vol_box)
        return w

    def _build_tray(self):
        try:
            self.tray = QSystemTrayIcon(icon_app(), self)
        except Exception:
            self.tray = None
            return
        self.tray.setToolTip("obsyde")
        m = QMenu(); m.setObjectName("AppMenu")
        a_show = QAction("\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c", self); a_show.triggered.connect(self._show_window); m.addAction(a_show)
        m.addSeparator()
        a_pp = QAction("Play / Pause", self); a_pp.triggered.connect(self.toggle_play); m.addAction(a_pp)
        a_n = QAction("\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439", self); a_n.triggered.connect(self.play_next); m.addAction(a_n)
        a_p = QAction("\u041f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0438\u0439", self); a_p.triggered.connect(self.play_prev); m.addAction(a_p)
        m.addSeparator()
        a_q = QAction("\u0412\u044b\u0439\u0442\u0438", self); a_q.triggered.connect(self._quit_app); m.addAction(a_q)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self._show_window() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _show_window(self):
        self.show(); self.raise_(); self.activateWindow()

    def _install_shortcuts(self):
        for keyseq, fn in (("Space", self.toggle_play), ("Ctrl+Right", self.play_next), ("Ctrl+Left", self.play_prev), ("Ctrl+,", self.open_settings), ("Ctrl+N", self.create_playlist_dialog), ("Ctrl+Q", self._quit_app)):
            a = QAction(self); a.setShortcut(keyseq); a.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            a.triggered.connect(fn); self.addAction(a)

    def _connect_signals(self):
        self.btn_home.clicked.connect(lambda: self._show_view("home"))
        self.btn_search.clicked.connect(lambda: self._show_view("search"))
        self.btn_liked.clicked.connect(lambda: self._show_view("liked"))
        self.search_input.returnPressed.connect(self.do_search)
        self.search_go.clicked.connect(self.do_search)
        self.btn_prev.clicked.connect(self.play_prev)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(self.play_next)
        self.volume.valueChanged.connect(self._set_volume_curve)
        self.progress.sliderPressed.connect(lambda: setattr(self, "_user_seeking", True))
        self.progress.sliderReleased.connect(self._seek_released)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_play_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)

    def _fade_to(self, target):
        if self.stack.currentWidget() is target:
            return
        self.stack.setCurrentWidget(target)

    def _show_view(self, view, playlist_name=None):
        self.current_view = view
        self.current_playlist = playlist_name
        for b, v in ((self.btn_home, "home"), (self.btn_search, "search"), (self.btn_liked, "liked")):
            b.setChecked(view == v)
        if view != "playlist":
            self.playlist_list.clearSelection()
        if view == "home":
            self._fade_to(self.page_home)
            self._render_mix()
            if not self.mix_tracks and self._mix_worker is None and (HIST.tracks or LIB.liked):
                QTimer.singleShot(200, self.refresh_mix)
        elif view == "search":
            self._fade_to(self.page_search)
            self._render_results()
            self.search_input.setFocus()
        elif view == "liked":
            self._fade_to(self.page_list)
            self.list_title.setText("\u041b\u044e\u0431\u0438\u043c\u044b\u0435")
            self._render_list(LIB.liked, source="liked")
        elif view == "playlist":
            self._fade_to(self.page_list)
            self.list_title.setText(playlist_name or "")
            self._render_list(LIB.playlists.get(playlist_name, []), source="playlist", playlist_name=playlist_name)

    def _clear_layout(self, layout):
        while layout.count() > 1:
            it = layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None); w.deleteLater()

    def _render_mix(self):
        self._clear_layout(self.mix_layout)
        if not self.mix_tracks:
            self.mix_layout.insertWidget(0, self._empty_widget("mix"))
            self.mix_status.setText("")
            return
        self.mix_status.setText(f"\u2022 {len(self.mix_tracks)} \u0442\u0440\u0435\u043a\u043e\u0432")
        for i, tr in enumerate(self.mix_tracks):
            row = self._make_row(tr, i, source="mix")
            self.mix_layout.insertWidget(i, row)
        self._refresh_now_playing_in(self.mix_layout, self.mix_tracks)

    def _render_results(self):
        self._clear_layout(self.search_layout)
        if not self.search_results:
            return
        for i, tr in enumerate(self.search_results):
            row = self._make_row(tr, i, source="search")
            self.search_layout.insertWidget(i, row)
        self._refresh_now_playing_in(self.search_layout, self.search_results)

    def _render_list(self, items, source, playlist_name=None):
        self._clear_layout(self.list_layout)
        if not items:
            self.list_layout.insertWidget(0, self._empty_widget(source))
            return
        for i, tr in enumerate(items):
            row = self._make_row(tr, i, source=source, playlist_name=playlist_name)
            self.list_layout.insertWidget(i, row)
        self._refresh_now_playing_in(self.list_layout, items)

    def _refresh_now_playing_in(self, layout, items):
        cur = self._current_track()
        if not cur: return
        for i in range(layout.count() - 1):
            w = layout.itemAt(i).widget()
            if isinstance(w, TrackRow):
                w.set_playing(items[i].permalink_url == cur.permalink_url if i < len(items) else False)

    def _make_row(self, tr, idx, source, playlist_name=None):
        row = TrackRow(tr, idx)
        row.play_clicked.connect(lambda t, s=source, pn=playlist_name: self._row_play(t, s, pn))
        row.like_toggled.connect(self._row_like)
        row.add_clicked.connect(self._row_add)
        row.menu_clicked.connect(lambda t, gp, s=source, pn=playlist_name: self._row_menu(t, gp, s, pn))
        return row

    def _row_play(self, tr, source, playlist_name):
        if source == "search":
            idx = next((i for i, t in enumerate(self.search_results) if t.permalink_url == tr.permalink_url), -1)
            if idx >= 0: self.play_list_from_index(self.search_results, idx)
        elif source == "mix":
            idx = next((i for i, t in enumerate(self.mix_tracks) if t.permalink_url == tr.permalink_url), -1)
            if idx >= 0: self.play_list_from_index(self.mix_tracks, idx)
        elif source == "liked":
            idx = next((i for i, t in enumerate(LIB.liked) if t.permalink_url == tr.permalink_url), -1)
            if idx >= 0: self.play_list_from_index(LIB.liked, idx)
        elif source == "playlist" and playlist_name:
            items = LIB.playlists.get(playlist_name, [])
            idx = next((i for i, t in enumerate(items) if t.permalink_url == tr.permalink_url), -1)
            if idx >= 0: self.play_list_from_index(items, idx)

    def _row_like(self, tr):
        LIB.toggle_like(tr)
        self._refresh_current_view()

    def _row_add(self, tr):
        if not LIB.playlists:
            r = QMessageBox.question(self, "obsyde", "\u041f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442. \u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043d\u043e\u0432\u044b\u0439?")
            if r == QMessageBox.StandardButton.Yes:
                self.create_playlist_dialog(initial_track=tr)
            return
        m = QMenu(self); m.setObjectName("AppMenu")
        for name in LIB.playlists:
            a = QAction(name, self); a.triggered.connect(lambda _=False, n=name, t=tr: (LIB.add_to_playlist(n, t), self._refresh_current_view())); m.addAction(a)
        m.addSeparator()
        ann = QAction("+ \u041d\u043e\u0432\u044b\u0439 \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u2026", self); ann.triggered.connect(lambda _=False, t=tr: self.create_playlist_dialog(initial_track=t)); m.addAction(ann)
        m.exec(QCursor.pos())

    def _row_menu(self, tr, gp, source, playlist_name):
        m = QMenu(self); m.setObjectName("AppMenu")
        a_now = QAction("\u0412\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0441\u0435\u0439\u0447\u0430\u0441", self); a_now.triggered.connect(lambda: self._play_track_now(tr)); m.addAction(a_now)
        a_q = QAction("\u0412 \u043e\u0447\u0435\u0440\u0435\u0434\u044c", self); a_q.triggered.connect(lambda: self._add_to_queue(tr)); m.addAction(a_q)
        m.addSeparator()
        liked = LIB.is_liked(tr)
        a_l = QAction("\u0423\u0431\u0440\u0430\u0442\u044c \u0438\u0437 \u043b\u044e\u0431\u0438\u043c\u044b\u0445" if liked else "\u0412 \u043b\u044e\u0431\u0438\u043c\u044b\u0435", self); a_l.triggered.connect(lambda: (LIB.toggle_like(tr), self._refresh_current_view())); m.addAction(a_l)
        if source == "playlist" and playlist_name:
            a_rm = QAction(f"\u0423\u0431\u0440\u0430\u0442\u044c \u0438\u0437 \u00ab{playlist_name}\u00bb", self); a_rm.triggered.connect(lambda: (LIB.remove_from_playlist(playlist_name, tr), self._refresh_current_view())); m.addAction(a_rm)
        if source == "liked":
            a_rm = QAction("\u0423\u0431\u0440\u0430\u0442\u044c \u0438\u0437 \u043b\u044e\u0431\u0438\u043c\u044b\u0445", self); a_rm.triggered.connect(lambda: (LIB.toggle_like(tr), self._refresh_current_view())); m.addAction(a_rm)
        m.exec(gp)

    def _empty_widget(self, source):
        if source == "mix":
            if self._mix_worker is not None:
                title_text = "\u041f\u043e\u0434\u0431\u0438\u0440\u0430\u044e \u0442\u0440\u0435\u043a\u0438\u2026"
                hint_text = "\u0421\u043f\u0440\u0430\u0448\u0438\u0432\u0430\u044e \u043f\u043e\u0445\u043e\u0436\u0438\u0435 \u043f\u0435\u0441\u043d\u0438 \u043f\u043e \u0438\u0441\u0442\u043e\u0440\u0438\u0438 \u0438 \u0442\u0432\u043e\u0438\u043c \u043b\u0430\u0439\u043a\u0430\u043c"
                btn_label = ""; on_click = None
            elif not HIST.tracks and not LIB.liked:
                title_text = "\u0421\u043b\u0443\u0448\u0430\u0439 \u043c\u0443\u0437\u044b\u043a\u0443 \u2014 \u044f \u043f\u043e\u0434\u0431\u0435\u0440\u0443 \u043f\u043e\u0445\u043e\u0436\u0435\u0435"
                hint_text = "\u041f\u043e\u0441\u043b\u0443\u0448\u0430\u0439 \u0438\u043b\u0438 \u043b\u0430\u0439\u043a\u043d\u0438 \u043b\u044e\u0431\u043e\u0439 \u0442\u0440\u0435\u043a \u0438 \u0432\u0435\u0440\u043d\u0438\u0441\u044c \u0441\u044e\u0434\u0430"
                btn_label = "  \u041d\u0430\u0439\u0442\u0438 \u043f\u0435\u0441\u043d\u044e"; on_click = lambda: self._show_view("search")
            else:
                title_text = "\u041c\u0438\u043a\u0441 \u0435\u0449\u0451 \u043d\u0435 \u0441\u043e\u0431\u0440\u0430\u043d"
                hint_text = "\u041d\u0430\u0436\u043c\u0438 \u00ab\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c\u00bb, \u0447\u0442\u043e\u0431\u044b \u0441\u043e\u0431\u0440\u0430\u0442\u044c \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438"
                btn_label = "  \u0421\u043e\u0431\u0440\u0430\u0442\u044c \u043c\u0438\u043a\u0441"; on_click = self.refresh_mix
        elif source == "liked":
            title_text = "\u041b\u044e\u0431\u0438\u043c\u044b\u0445 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442"; hint_text = "\u041d\u0430\u0436\u043c\u0438 \u0441\u0435\u0440\u0434\u0435\u0447\u043a\u043e \u0432 \u043b\u044e\u0431\u043e\u043c \u0442\u0440\u0435\u043a\u0435 \u2014 \u043e\u043d \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u0437\u0434\u0435\u0441\u044c"
            btn_label = "  \u041d\u0430\u0439\u0442\u0438 \u043f\u0435\u0441\u043d\u044e"; on_click = lambda: self._show_view("search")
        elif source == "playlist":
            title_text = "\u041f\u043b\u0435\u0439\u043b\u0438\u0441\u0442 \u043f\u0443\u0441\u0442"; hint_text = "\u041d\u0430\u0439\u0434\u0438 \u043f\u0435\u0441\u043d\u044e \u0432 \u043f\u043e\u0438\u0441\u043a\u0435 \u0438 \u043d\u0430\u0436\u043c\u0438 \u00ab+\u00bb"
            btn_label = "  \u041d\u0430\u0439\u0442\u0438 \u043f\u0435\u0441\u043d\u044e"; on_click = lambda: self._show_view("search")
        else:
            title_text = "\u041f\u0443\u0441\u0442\u043e"; hint_text = ""; btn_label = ""; on_click = None
        w = QWidget()
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        w.setMinimumHeight(280)
        v = QVBoxLayout(w); v.setContentsMargins(28, 56, 28, 56); v.setSpacing(18)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addStretch(1)
        t = QLabel(title_text)
        t.setStyleSheet(f"color: {C_TEXT}; font-size: 20px; font-weight: 600; letter-spacing: 0.3px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        t.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        v.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
        if hint_text:
            hl = QLabel(hint_text)
            hl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 13px; line-height: 150%;")
            hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.setWordWrap(True)
            hl.setMinimumWidth(420)
            hl.setMaximumWidth(520)
            hl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
            hl.adjustSize()
            v.addWidget(hl, 0, Qt.AlignmentFlag.AlignHCenter)
        if btn_label and on_click:
            b = QPushButton(btn_label); b.setObjectName("AccentBtn")
            b.setCursor(Qt.CursorShape.PointingHandCursor); b.setFixedWidth(220); b.setMinimumHeight(38)
            b.clicked.connect(on_click); v.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addStretch(1)
        return w

    def _refresh_current_view(self):
        view = self.current_view
        if view == "home": self._render_mix()
        elif view == "search": self._render_results()
        elif view == "liked": self._render_list(LIB.liked, source="liked")
        elif view == "playlist":
            self._render_list(LIB.playlists.get(self.current_playlist, []), source="playlist", playlist_name=self.current_playlist)

    def _refresh_playlist_list(self):
        self.playlist_list.clear()
        for name in LIB.playlists:
            it = QListWidgetItem(f"\u266a  {name}")
            it.setData(Qt.ItemDataRole.UserRole, name)
            self.playlist_list.addItem(it)

    def _on_playlist_clicked(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        if name: self._show_view("playlist", playlist_name=name)

    def _playlist_context_menu(self, pos):
        item = self.playlist_list.itemAt(pos)
        if not item: return
        name = item.data(Qt.ItemDataRole.UserRole)
        m = QMenu(self); m.setObjectName("AppMenu")
        a_o = QAction("\u041e\u0442\u043a\u0440\u044b\u0442\u044c", self); a_o.triggered.connect(lambda: self._show_view("playlist", playlist_name=name)); m.addAction(a_o)
        a_r = QAction("\u041f\u0435\u0440\u0435\u0438\u043c\u0435\u043d\u043e\u0432\u0430\u0442\u044c\u2026", self); a_r.triggered.connect(lambda: self._rename_playlist(name)); m.addAction(a_r)
        m.addSeparator()
        a_d = QAction("\u0423\u0434\u0430\u043b\u0438\u0442\u044c", self); a_d.triggered.connect(lambda: self._delete_playlist(name)); m.addAction(a_d)
        m.exec(self.playlist_list.mapToGlobal(pos))

    def _rename_playlist(self, name):
        new, ok = QInputDialog.getText(self, "obsyde", "\u041d\u043e\u0432\u043e\u0435 \u0438\u043c\u044f \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u0430:", text=name)
        if ok and new.strip():
            LIB.rename_playlist(name, new.strip())
            self._refresh_playlist_list()
            if self.current_view == "playlist" and self.current_playlist == name:
                self._show_view("playlist", playlist_name=new.strip())

    def _delete_playlist(self, name):
        if QMessageBox.question(self, "obsyde", f"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442 \u00ab{name}\u00bb?") == QMessageBox.StandardButton.Yes:
            LIB.delete_playlist(name)
            self._refresh_playlist_list()
            if self.current_view == "playlist" and self.current_playlist == name:
                self._show_view("home")

    def create_playlist_dialog(self, initial_track=None):
        name, ok = QInputDialog.getText(self, "obsyde", "\u0418\u043c\u044f \u043d\u043e\u0432\u043e\u0433\u043e \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u0430:")
        if not (ok and name.strip()): return
        name = name.strip()
        LIB.add_playlist(name)
        if isinstance(initial_track, Track):
            LIB.add_to_playlist(name, initial_track)
        self._refresh_playlist_list()
        self._show_view("playlist", playlist_name=name)

    def do_search(self):
        q = self.search_input.text().strip()
        if not q: return
        self.search_status.setText("\u0418\u0449\u0443\u2026")
        self.search_results = []
        self._render_results()
        old = self._search_worker
        if old is not None and old.isRunning():
            try:
                old.requestInterruption()
                old.wait(1500)
            except Exception:
                pass
        w = SearchWorker(q)
        w.done.connect(self._on_search_done)
        w.failed.connect(lambda e: self.search_status.setText(f"\u041e\u0448\u0438\u0431\u043a\u0430: {e}"))
        w.finished.connect(w.deleteLater)
        self._search_worker = w
        w.start()

    def _on_search_done(self, tracks):
        self.search_results = tracks
        self.search_status.setText(f"\u041d\u0430\u0439\u0434\u0435\u043d\u043e: {len(tracks)}" if tracks else "\u041d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
        self._render_results()

    def refresh_mix(self):
        if self._mix_worker is not None: return
        seeds = []
        seen = set()
        for lst in (HIST.tracks, LIB.liked):
            for t in lst:
                if t.permalink_url and t.permalink_url not in seen:
                    seeds.append(t); seen.add(t.permalink_url)
        seeds = seeds[:20]
        if not seeds:
            self.mix_tracks = []
            self._render_mix(); return
        self.mix_status.setText("\u041f\u043e\u0434\u0431\u0438\u0440\u0430\u044e\u2026")
        if hasattr(self, "btn_mix_refresh"):
            self.btn_mix_refresh.setEnabled(False)
        w = MixWorker(seeds, target=int(SETTINGS.get("mix_size")))
        w.done.connect(self._on_mix_done)
        w.failed.connect(lambda e: self._on_mix_done([]))
        w.finished.connect(w.deleteLater)
        w.finished.connect(self._on_mix_finished)
        self._mix_worker = w
        w.start()
        self._render_mix()

    def _on_mix_done(self, tracks):
        self.mix_tracks = tracks
        if hasattr(self, "btn_mix_refresh"):
            self.btn_mix_refresh.setEnabled(True)
        self._render_mix()

    def _on_mix_finished(self):
        self._mix_worker = None

    def play_mix_from_start(self):
        if self.mix_tracks:
            self.play_list_from_index(self.mix_tracks, 0)

    def play_list_from_start(self):
        items = self._current_list_items()
        if items:
            self.play_list_from_index(items, 0)

    def shuffle_current_list_and_play(self):
        items = self._current_list_items()
        if not items: return
        shuffled = list(items); random.shuffle(shuffled)
        self.queue = list(shuffled)
        self._save_queue()
        self.play_at(0)

    def _current_list_items(self):
        if self.current_view == "liked": return LIB.liked
        if self.current_view == "playlist" and self.current_playlist:
            return LIB.playlists.get(self.current_playlist, [])
        if self.current_view == "home": return self.mix_tracks
        return []

    def play_list_from_index(self, items, idx):
        if not items: return
        self.queue = list(items)
        self._save_queue()
        self.play_at(idx)

    def play_at(self, idx):
        if not (0 <= idx < len(self.queue)): return
        self.current_index = idx
        tr = self.queue[idx]
        self.now_title.setText(tr.title or "\u2014")
        self.now_artist.setText(tr.artist or "")
        HIST.push(tr)
        self._refresh_current_view()
        if self._eq_player.is_playing():
            self._eq_player.stop()
        old = self._stream_worker
        self._stream_worker = None
        if old is not None:
            try:
                if old.isRunning():
                    old.requestInterruption()
                    old.wait(1500)
            except (RuntimeError, Exception):
                pass
        w = StreamWorker(tr)
        w.got.connect(self._on_stream_url)
        w.failed.connect(lambda e: None)
        def _on_worker_finished(_w=w):
            try:
                if self._stream_worker is _w:
                    self._stream_worker = None
            except Exception:
                pass
            try:
                _w.deleteLater()
            except Exception:
                pass
        w.finished.connect(_on_worker_finished)
        self._stream_worker = w
        w.start()

    def _on_stream_url(self, url):
        if self._eq_active and not self._eq_processor.bypassed:
            self.player.stop()
            self._eq_player.play(url)
        else:
            self._eq_player.stop()
            self.player.setSource(QUrl(url))
            self.player.play()

    def _on_stream_url_current(self):
        tr = self._current_track()
        if tr is None:
            return
        old = self._stream_worker
        self._stream_worker = None
        if old is not None:
            try:
                if old.isRunning():
                    old.requestInterruption()
            except (RuntimeError, Exception):
                pass
            self._keep_worker(old)

        w = StreamWorker(tr)
        w.got.connect(self._on_stream_url)
        w.failed.connect(lambda e: None)
        def _on_worker_finished(_w=w):
            try:
                if self._stream_worker is _w:
                    self._stream_worker = None
            except Exception:
                pass
            try:
                _w.deleteLater()
            except Exception:
                pass
        w.finished.connect(_on_worker_finished)
        self._stream_worker = w
        w.start()

    def _keep_worker(self, w):
        self._old_workers.append(w)
        def _clean():
            try:
                if w in self._old_workers:
                    self._old_workers.remove(w)
                w.deleteLater()
            except Exception:
                pass
        try:
            w.finished.connect(_clean)
        except Exception:
            pass

    def _play_track_now(self, tr):
        self.queue.append(tr)
        self._save_queue()
        self.play_at(len(self.queue) - 1)

    def _add_to_queue(self, tr):
        self.queue.append(tr)
        self._save_queue()

    def play_next(self):
        if self.current_index + 1 < len(self.queue):
            self.play_at(self.current_index + 1)

    def play_prev(self):
        if self.current_index > 0:
            self.play_at(self.current_index - 1)

    def toggle_play(self):
        if self._eq_player.is_playing():
            self._eq_player.toggle_pause()
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty() and self.current_index < 0 and self.queue:
                self.play_at(0)
            else:
                self.player.play()

    def _on_pos(self, ms):
        if self._user_seeking: return
        d = self.player.duration() or 0
        if d > 0:
            self.progress.setValue(int(ms / d * 1000))
        self.pos_lbl.setText(self._fmt_ms(ms))

    def _on_dur(self, ms):
        self.dur_lbl.setText(self._fmt_ms(ms))

    def _on_play_state(self, st):
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setIcon(icon_pause("#0f0f17"))
        else:
            self.btn_play.setIcon(icon_play("#0f0f17"))

    def _on_media_status(self, st):
        if st == QMediaPlayer.MediaStatus.EndOfMedia:
            if SETTINGS.get("autoplay_next"):
                self.play_next()

    def _seek_released(self):
        self._user_seeking = False
        if self._eq_active and not self._eq_processor.bypassed and self._eq_player.is_playing():
            tr = self._current_track()
            d = tr.duration_ms if tr else 0
            if d > 0:
                target = int(self.progress.value() / 1000 * d)
                self._eq_player.seek(target)
                self.pos_lbl.setText(self._fmt_ms(target))
                self.progress.setValue(int(target / d * 1000))
            return
        d = self.player.duration() or 0
        if d > 0:
            self.player.setPosition(int(self.progress.value() / 1000 * d))

    def _fmt_ms(self, ms):
        s = max(0, ms // 1000)
        return f"{s//60}:{s%60:02d}"

    def _current_track(self):
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def _save_queue(self):
        try:
            (CONFIG_DIR/"queue.json").write_text(json.dumps({"queue": [asdict(t) for t in self.queue], "index": self.current_index}, ensure_ascii=False), "utf-8")
        except Exception: pass

    def _restore_queue(self):
        f = CONFIG_DIR/"queue.json"
        if not f.exists(): return
        try:
            d = json.loads(f.read_text("utf-8"))
            self.queue = [Track(**x) for x in d.get("queue", [])]
        except Exception: pass

    def open_settings(self):
        d = SettingsDialog(self); d.exec()

    def apply_runtime_settings(self):
        try:
            w, h = [int(x) for x in str(SETTINGS.get("resolution") or "1080x680").split("x")]
            if not self.isMaximized():
                self.resize(w, h)
        except Exception:
            pass
        self._set_volume_curve(SETTINGS.get("default_volume"))
        self.volume.setValue(int(SETTINGS.get("default_volume")))
        if hasattr(self, "bg_fx"):
            self.bg_fx.set_kind(str(SETTINGS.get("bg_effect") or "rain"))
        try:
            self.setWindowOpacity(max(0.4, float(SETTINGS.get("window_opacity") or 100) / 100.0))
        except Exception:
            pass

    def import_playlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "\u0418\u043c\u043f\u043e\u0440\u0442 \u043f\u043b\u0435\u0439\u043b\u0438\u0441\u0442\u0430", str(Path.home()), "JSON (*.json)")
        if not path: return
        try:
            data = json.loads(Path(path).read_text("utf-8"))
            name = Path(path).stem
            LIB.playlists[name] = [Track(**t) for t in data]
            LIB.save_playlist(name)
            self._refresh_playlist_list()
            self._show_view("playlist", playlist_name=name)
        except Exception as e:
            QMessageBox.critical(self, "obsyde", f"\u041e\u0448\u0438\u0431\u043a\u0430:\n{e}")

    def export_current_list(self):
        items = self._current_list_items()
        if not items:
            QMessageBox.information(self, "obsyde", "\u041d\u0435\u0442 \u0442\u0440\u0435\u043a\u043e\u0432 \u0434\u043b\u044f \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430."); return
        path, _ = QFileDialog.getSaveFileName(self, "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0441\u043f\u0438\u0441\u043a\u0430", str(Path.home()/"obsyde-list.json"), "JSON (*.json)")
        if not path: return
        try:
            Path(path).write_text(json.dumps([asdict(t) for t in items], ensure_ascii=False, indent=2), "utf-8")
        except Exception as e:
            QMessageBox.critical(self, "obsyde", f"\u041e\u0448\u0438\u0431\u043a\u0430:\n{e}")

    def _quit_app(self):
        if self.tray: self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e):
        if SETTINGS.get("minimize_to_tray") and self.tray and self.tray.isVisible():
            self.hide(); e.ignore()
            return
        self._stop_all_workers()
        try:
            self.player.stop()
        except Exception:
            pass
        if self._eq_dialog:
            self._eq_dialog.hide()
        if self.tray: self.tray.hide()
        e.accept()

    def _stop_all_workers(self):
        for attr in ("_mix_worker", "_search_worker", "_stream_worker"):
            w = getattr(self, attr, None)
            if w is None:
                continue
            try:
                w.requestInterruption()
                w.wait(1500)
            except Exception:
                pass
            setattr(self, attr, None)
        try:
            self._eq_player.stop()
        except Exception:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_bg_geom()
        self._update_mask()

    def showEvent(self, e):
        super().showEvent(e)
        self._update_bg_geom()
        self._update_mask()
        self._enable_win_blur()
        if self._eq_active and self._eq_dialog:
            self._position_eq_dialog()
            self._eq_dialog.show()
            self._eq_dialog.raise_()

    def hideEvent(self, e):
        super().hideEvent(e)
        if self._eq_dialog and self._eq_dialog.isVisible():
            self._eq_dialog.hide()

    def _update_mask(self):
        try:
            from PyQt6.QtGui import QRegion
            radius = 0 if self.isMaximized() else 18
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), radius, radius)
            self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        except Exception:
            pass

    def _enable_win_blur(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes, byref, sizeof, c_int, Structure
            hwnd = int(self.winId())
            dark = c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), 20, byref(dark), sizeof(dark))
            for code in (3, 2):
                v = c_int(code)
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), 38, byref(v), sizeof(v))
                if res == 0:
                    break
            class MARGINS(Structure):
                _fields_ = [("l", c_int), ("r", c_int), ("t", c_int), ("b", c_int)]
            m = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd), byref(m))
        except Exception:
            pass

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 0 if self.isMaximized() else 18
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QBrush(QColor(20, 18, 42, 248)))
        pen = QPen(QColor(255, 255, 255, 55))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.drawRoundedRect(rect, radius, radius)
        inner = rect.adjusted(1.5, 1.5, -1.5, -1.5)
        pen2 = QPen(QColor(255, 255, 255, 22))
        pen2.setWidthF(1.0)
        p.setPen(pen2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inner, max(1, radius - 1.5), max(1, radius - 1.5))
        p.end()

    def _edge(self, pos):
        if self.isMaximized(): return None
        m = 0
        r = self.rect()
        x, y = pos.x(), pos.y()
        L = x <= m + 6; R = x >= r.width() - m - 6
        T = y <= m + 6; B = y >= r.height() - m - 6
        if T and L: return "tl"
        if T and R: return "tr"
        if B and L: return "bl"
        if B and R: return "br"
        if L: return "l"
        if R: return "r"
        if T: return "t"
        if B: return "b"
        return None

    def moveEvent(self, e):
        try:
            old = e.oldPos(); new = e.pos()
            dx = new.x() - old.x(); dy = new.y() - old.y()
            if hasattr(self, "bg_fx") and self.bg_fx is not None:
                self.bg_fx.apply_shake(dx, dy)
        except Exception:
            pass
        super().moveEvent(e)

    def mouseMoveEvent(self, e):
        if self._resize_edge and (e.buttons() & Qt.MouseButton.LeftButton):
            self._do_resize(e.globalPosition().toPoint()); return
        edge = self._edge(e.position().toPoint())
        cur = {
            "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
            "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
            "tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
        }.get(edge, Qt.CursorShape.ArrowCursor)
        self.setCursor(cur)
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            edge = self._edge(e.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_geo = QRect(self.geometry())
                self._resize_start = e.globalPosition().toPoint()
                return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self._resize_edge:
            self._resize_edge = None
        super().mouseReleaseEvent(e)

    def _do_resize(self, gpos):
        g = self._resize_geo
        d = gpos - self._resize_start
        dx, dy = d.x(), d.y()
        minw, minh = self.minimumWidth(), self.minimumHeight()
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        e = self._resize_edge
        if "l" in e:
            nx = x + dx; nw = w - dx
            if nw < minw: nx = x + (w - minw); nw = minw
            x, w = nx, nw
        if "r" in e: w = max(minw, w + dx)
        if "t" in e:
            ny = y + dy; nh = h - dy
            if nh < minh: ny = y + (h - minh); nh = minh
            y, h = ny, nh
        if "b" in e: h = max(minh, h + dy)
        self.setGeometry(x, y, w, h)

    def _stylesheet(self):
        return (_CSS_TEMPLATE
                .replace("__TEXT__", C_TEXT)
                .replace("__TEXTDIM__", C_TEXT_DIM)
                .replace("__BORDER__", C_BORDER)
                .replace("__ACCENT__", C_ACCENT))
