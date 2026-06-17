import os, sys, traceback

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from .style import stylesheet
from .window import Obsyde

def _excepthook(tp, val, tb):
    traceback.print_exception(tp, val, tb)
    sys.stderr.flush()
sys.excepthook = _excepthook

def main():
    if not os.environ.get("OBSYDE_DEBUG"):
        os.environ.setdefault(
            "QT_LOGGING_RULES",
            "*.debug=false;*.info=false;*.warning=false;qt.multimedia.*=false;qt.*.warning=false",
        )
    app = QApplication(sys.argv)
    app.setApplicationName("obsyde")
    app.setQuitOnLastWindowClosed(False)
    f = QFont("Segoe UI", 10)
    try:
        f.setFamilies(["Inter", "SF Pro Display", "Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "Helvetica Neue", "Arial"])
    except Exception:
        f.setFamily("Segoe UI")
    try:
        f.setWeight(QFont.Weight.DemiBold)
    except Exception:
        f.setBold(True)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(f)
    w = Obsyde()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
