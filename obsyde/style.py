from .constants import C_TEXT, C_TEXT_DIM, C_BORDER, C_ACCENT

_CSS_TEMPLATE = r"""
QMainWindow { background: transparent; }
* { font-family: 'Inter', 'SF Pro Text', 'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif; }
QWidget { color: __TEXT__; font-family: 'Inter', 'SF Pro Text', 'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif; font-size: 13px; font-weight: 600; }
QLabel, QPushButton, QToolButton, QLineEdit, QComboBox, QSpinBox, QCheckBox, QMenu, QListWidget { font-family: 'Inter', 'SF Pro Text', 'Segoe UI Variable Text', 'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif; font-weight: 600; }
QWidget#WinContainer { background: transparent; }

* { outline: 0; }
QToolButton:focus, QPushButton:focus, QLineEdit:focus, QSlider:focus, QComboBox:focus, QSpinBox:focus, QCheckBox:focus, QListWidget:focus, QListWidget::item:focus { outline: 0; }
QWidget#TitleBar {
    background: rgba(255,255,255,0.035);
    border-bottom: 1px solid __BORDER__;
}
QPushButton#MenuBtn {
    background: transparent;
    color: __TEXTDIM__;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 6px 16px;
    font-size: 12.5px;
    font-weight: 600;
    margin: 0 3px;
}
QPushButton#MenuBtn:hover {
    background: rgba(255,255,255,0.08);
    color: __TEXT__;
    border: 1px solid rgba(255,255,255,0.10);
}
QPushButton#MenuBtn:pressed {
    background: rgba(180,139,255,0.20);
    border: 1px solid rgba(180,139,255,0.50);
    color: __TEXT__;
}
QToolButton#WinBtn { background: transparent; border: 1px solid transparent; border-radius: 7px; margin: 0 1px; }
QToolButton#WinBtn:hover { background: rgba(255,255,255,0.14); border: 1px solid rgba(0,0,0,0.70); }
QToolButton#WinBtn:pressed { background: rgba(255,255,255,0.22); border: 1px solid rgba(0,0,0,0.85); }
QToolButton#WinClose { background: transparent; border: 1px solid transparent; border-radius: 7px; margin: 0 1px; }
QToolButton#WinClose:hover { background: rgba(255,255,255,0.18); border: 1px solid rgba(0,0,0,0.75); }
QToolButton#WinClose:pressed { background: rgba(255,255,255,0.28); border: 1px solid rgba(0,0,0,0.9); }
QWidget#TopBar { background: transparent; border-bottom: 1px solid __BORDER__; }
QPushButton#NavBtn {
    background: rgba(20,18,40,0.55);
    color: __TEXT__;
    border: 1px solid rgba(0,0,0,0.65);
    border-radius: 14px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 700;
    text-align: left;
}
QPushButton#NavBtn:hover { background: rgba(255,255,255,0.10); border-color: rgba(0,0,0,0.8); }
QPushButton#NavBtn:checked {
    background: rgba(180,139,255,0.24);
    border: 1px solid rgba(0,0,0,0.85);
    color: __TEXT__;
}
QPushButton#NavBtn:checked:hover {
    background: rgba(180,139,255,0.32);
}
QWidget#Sidebar { background: rgba(255,255,255,0.022); border-right: 1px solid __BORDER__; }
QListWidget#PlaylistList { background: transparent; border: none; }
QListWidget#PlaylistList::item { padding: 8px 10px; border-radius: 8px; color: __TEXT__; border: 1px solid transparent; }
QListWidget#PlaylistList::item:hover { background: rgba(255,255,255,0.06); border: 1px solid rgba(0,0,0,0.55); }
QListWidget#PlaylistList::item:selected { background: rgba(255,255,255,0.14); color: __TEXT__; border: 1px solid rgba(0,0,0,0.75); }
QStackedWidget#Stack { background: transparent; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QAbstractScrollArea { background: transparent; }
QAbstractScrollArea::viewport { background: transparent; }
QStackedWidget { background: transparent; }
QStackedWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.14); border-radius: 4px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.24); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 4px; }
QScrollBar::handle:horizontal { background: rgba(255,255,255,0.14); border-radius: 4px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: rgba(255,255,255,0.24); }
QWidget#TrackRow { background: rgba(15,13,28,0.42); border-radius: 9px; border: 1px solid rgba(0,0,0,0.55); }
QWidget#TrackRow:hover { background: rgba(255,255,255,0.06); border: 1px solid rgba(0,0,0,0.75); }

QLineEdit {
    background: rgba(255,255,255,0.05);
    color: __TEXT__;
    border: 1px solid __BORDER__;
    border-radius: 10px;
    padding: 6px 12px;
    selection-background-color: __ACCENT__;
}
QLineEdit:focus { border-color: __ACCENT__; }
QPushButton#AccentBtn {
    background: __ACCENT__;
    color: #0f0f17;
    border: 1px solid rgba(0,0,0,0.75);
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 800;
}
QPushButton#AccentBtn:hover { background: #c6a3ff; }
QPushButton#AccentBtn:pressed { background: #9d76e0; }
QPushButton#MixRefresh {
    background: rgba(255,255,255,0.08);
    color: __TEXT__;
    border: 1px solid rgba(0,0,0,0.65);
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: 700;
}
QPushButton#MixRefresh:hover { background: rgba(255,255,255,0.16); border-color: rgba(0,0,0,0.85); }
QPushButton#MixRefresh:disabled { background: rgba(255,255,255,0.04); color: __TEXTDIM__; border-color: __BORDER__; }
QToolButton { background: transparent; border: none; border-radius: 8px; padding: 4px; }
QToolButton:hover { background: rgba(255,255,255,0.08); }
QToolButton#PlayBtn {
    background: __ACCENT__;
    border-radius: 19px;
    border: 1px solid rgba(0,0,0,0.85);
    padding: 0px;
    margin: 0px;
}
QToolButton#PlayBtn:hover { background: #c6a3ff; }
QToolButton#PlayBtn:pressed { background: #9d76e0; }
QToolButton#SideBtn {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(0,0,0,0.55);
    border-radius: 16px;
    padding: 0px;
}
QToolButton#SideBtn:hover { background: rgba(255,255,255,0.12); border-color: rgba(0,0,0,0.8); }
QToolButton#SideBtn:pressed { background: rgba(255,255,255,0.18); }
QToolButton#AboutClose { background: rgba(255,255,255,0.04); border-radius: 6px; }
QToolButton#AboutClose:hover { background: rgba(255,255,255,0.14); }
QWidget#PlayerBar { background: rgba(255,255,255,0.03); border-top: 1px solid __BORDER__; }
QSlider::groove:horizontal { background: rgba(255,255,255,0.10); height: 4px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: __ACCENT__; border-radius: 2px; }
QSlider::handle:horizontal { background: __TEXT__; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
QSlider::handle:horizontal:hover { background: #ffffff; }
QMenu, QMenu#AppMenu {
    background: #16152a;
    color: __TEXT__;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 12px;
    padding: 8px;
}
QMenu::item {
    padding: 9px 22px 9px 18px;
    border-radius: 8px;
    color: __TEXT__;
    margin: 1px 2px;
    font-size: 12.5px;
    font-weight: 500;
}
QMenu::item:selected {
    background: rgba(180,139,255,0.22);
    color: #ffffff;
}
QMenu::item:disabled { color: __TEXTDIM__; }
QMenu::separator { height: 1px; background: rgba(255,255,255,0.10); margin: 6px 10px; }
QDialog#SettingsDialog { background: #11101e; }
QDialog#AboutDialog { background: #11101e; }
QFrame#AboutCard {
    background: #181530;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 16px;
}
QComboBox, QSpinBox {
    background: rgba(255,255,255,0.05);
    color: __TEXT__;
    border: 1px solid __BORDER__;
    border-radius: 8px;
    padding: 6px 10px;
}
QComboBox:focus, QSpinBox:focus { border-color: __ACCENT__; }
QComboBox QAbstractItemView {
    background: #181828;
    color: __TEXT__;
    border: 1px solid __BORDER__;
    border-radius: 8px;
    selection-background-color: rgba(180,139,255,0.30);
    padding: 4px;
    outline: 0;
}
QCheckBox { color: __TEXT__; spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid __BORDER__; background: rgba(255,255,255,0.04); }
QCheckBox::indicator:checked { background: __ACCENT__; border-color: __ACCENT__; }
QLabel { color: __TEXT__; }
QMessageBox { background: #11101e; }
QMessageBox QLabel { color: __TEXT__; }
QMessageBox QPushButton {
    background: rgba(255,255,255,0.06);
    color: __TEXT__;
    border: 1px solid __BORDER__;
    border-radius: 8px;
    padding: 6px 14px;
    min-width: 72px;
}
QMessageBox QPushButton:hover { background: rgba(255,255,255,0.14); }
QWidget#EqCard {
    background: rgba(15,13,28,0.94);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
}
QSlider#EqSlider::groove:vertical {
    background: rgba(255,255,255,0.08);
    width: 4px;
    border-radius: 2px;
}
QSlider#EqSlider::handle:vertical {
    background: __ACCENT__;
    height: 10px;
    width: 16px;
    margin: 0 -6px;
    border-radius: 4px;
}
QSlider#EqSlider::handle:vertical:hover {
    background: #c6a3ff;
}
QSlider#EqSlider::sub-page:vertical {
    background: __ACCENT__;
    border-radius: 2px;
    width: 4px;
}
QSlider#EqSlider::add-page:vertical {
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
    width: 4px;
}
QPushButton#EqBypassOn {
    background: rgba(180,139,255,0.20);
    color: __ACCENT__;
    border: 1px solid __ACCENT__;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#EqBypassOn:hover {
    background: rgba(180,139,255,0.30);
}
QPushButton#EqBypassOff {
    background: rgba(255,91,91,0.15);
    color: #ff5b5b;
    border: 1px solid #ff5b5b;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#EqBypassOff:hover {
    background: rgba(255,91,91,0.25);
}
QToolButton#EqBtn {
    background: rgba(180,139,255,0.12);
    border: 1px solid rgba(180,139,255,0.25);
    border-radius: 8px;
}
QToolButton#EqBtn:hover {
    background: rgba(180,139,255,0.22);
}
QToolButton#EqBtn:checked {
    background: __ACCENT__;
    border-color: __ACCENT__;
}
QToolButton#EqBtn:checked:hover {
    background: #c6a3ff;
}
"""


def stylesheet():
    return (_CSS_TEMPLATE
            .replace("__TEXT__", C_TEXT)
            .replace("__TEXTDIM__", C_TEXT_DIM)
            .replace("__BORDER__", C_BORDER)
            .replace("__ACCENT__", C_ACCENT))
