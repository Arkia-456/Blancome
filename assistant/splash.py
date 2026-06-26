import json
import random
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont

_PLUM  = "#2E1B33"
_PEARL = "#F6F2E9"
_GOLD  = "#D9A227"
_MUTED = "#A2929F"

_W, _H = 500, 260

_MESSAGES_FILE = (
    Path(sys._MEIPASS) / "loading_messages.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).parent.parent / "loading_messages.json"
)

def _load_steps() -> dict:
    try:
        data = json.loads(_MESSAGES_FILE.read_text(encoding="utf-8"))
        return {int(k): v for k, v in data.items()}
    except Exception:
        return {}

_STEPS = _load_steps()


class AppSplash(QSplashScreen):
    def __init__(self):
        super().__init__(self._make_base(), Qt.WindowType.WindowStaysOnTopHint)
        self._value = 0
        self._msg = ""
        self.setEnabled(False)

    @staticmethod
    def _make_base() -> QPixmap:
        px = QPixmap(_W, _H)
        px.fill(QColor(_PLUM))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        f = QFont("Georgia", 34)
        p.setFont(f)
        p.setPen(QColor(_PEARL))
        p.drawText(QRect(0, 48, _W, 64), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "Blancome")

        f2 = QFont("Segoe UI", 9)
        f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        p.setFont(f2)
        p.setPen(QColor(_MUTED))
        p.drawText(QRect(0, 118, _W, 24), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "YOUR HOME, ATTENDED")

        p.end()
        return px

    def step(self, value: int):
        pool = _STEPS.get(value, ["…"])
        self._msg = random.choice(pool)
        self._value = value
        self.repaint()
        app = QApplication.instance()
        if app:
            app.processEvents()

    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        f = QFont("Segoe UI", 9)
        painter.setFont(f)
        painter.setPen(QColor(_MUTED))
        painter.drawText(
            QRect(0, _H - 58, _W, 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            self._msg,
        )

        bx, by, bw, bh = 60, _H - 30, _W - 120, 4
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 35))
        painter.drawRoundedRect(bx, by, bw, bh, 2, 2)

        fill_w = int(bw * self._value / 100)
        if fill_w > 0:
            painter.setBrush(QColor(_GOLD))
            painter.drawRoundedRect(bx, by, fill_w, bh, 2, 2)
