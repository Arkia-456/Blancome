import ctypes
import logging
import sys
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QFrame, QHeaderView, QAbstractItemView, QSlider, QSizePolicy,
    QStyledItemDelegate, QStackedWidget, QListWidget, QListWidgetItem, QLineEdit,
    QScrollArea, QScroller,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QIcon, QBrush, QRadialGradient, QFont, QPixmap

from assistant.music_service import music_service
from assistant.shopping_service import shopping_service
from assistant.calendar_service import calendar_service
from assistant.microsoft_calendar_service import microsoft_calendar_service

_PLUM       = "#2E1B33"
_PLUM_SOFT  = "#4A3052"
_PEARL      = "#F6F2E9"
_PEARL_DEEP = "#ECE5D4"
_GOLD       = "#D9A227"
_RUBY       = "#D6213F"
_RUBY_DEEP  = "#9E1B33"
_AZURE_DEEP = "#2776BE"
_CARD       = "#FFFDF7"
_DATE_FG    = "#CBB9D6"
_MUTED      = "#A2929F"
_ACTIVE_BG  = "#D0E8FA"

_ICON = Path(__file__).parent.parent / "assets" / "icon.ico"
_PLAYLIST_FILETYPES = "Fichiers playlist (*.m3u *.m3u8 *.txt);;Tous les fichiers (*.*)"

_FR_DAYS   = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
_FR_MONTHS = ["janvier","février","mars","avril","mai","juin",
              "juillet","août","septembre","octobre","novembre","décembre"]

_FRILL_RAW = [
    (0,8),(30,19),(90,9),(160,21),(230,11),(300,24),
    (370,9),(445,22),(515,10),(585,23),(660,8),(730,21),
    (805,11),(880,24),(950,10),(1020,22),(1095,9),(1155,20),(1200,8),
]
_FRILL_STOPS = [(0.0,"#8C2347"),(0.45,"#3D9DEB"),(0.75,"#8C2347"),(1.0,"#3D9DEB")]


def _fmt_time(s: float) -> str:
    s = int(max(0, s))
    return f"{s // 60}:{s % 60:02d}"


def _hex_lerp(h1: str, h2: str, t: float) -> str:
    h1 = h1.lstrip("#"); h2 = h2.lstrip("#")
    r = lambda h, i: int(h[i:i+2], 16)
    return "#{:02x}{:02x}{:02x}".format(
        round(r(h1,0) + (r(h2,0) - r(h1,0)) * t),
        round(r(h1,2) + (r(h2,2) - r(h1,2)) * t),
        round(r(h1,4) + (r(h2,4) - r(h1,4)) * t),
    )


def _frill_color(t: float) -> str:
    for i in range(len(_FRILL_STOPS) - 1):
        t0, c0 = _FRILL_STOPS[i]; t1, c1 = _FRILL_STOPS[i+1]
        if t <= t1:
            return _hex_lerp(c0, c1, (t - t0) / (t1 - t0))
    return _FRILL_STOPS[-1][1]


def _hsep() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {_PEARL_DEEP}; border: none;")
    return f


def _vsep() -> QFrame:
    f = QFrame()
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {_PEARL_DEEP}; border: none;")
    return f


class FrillWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        s = w / 1200
        sy = h / 26
        pts = [(int(x * s), int(y * sy)) for x, y in _FRILL_RAW]

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(w, 0)
        for x, y in reversed(pts):
            path.lineTo(x, y)
        path.closeSubpath()
        p.fillPath(path, QColor(_PLUM))

        n = len(pts)
        for i in range(n - 1):
            pen = QPen(QColor(_frill_color(i / (n - 2))), 3,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])


_STYLESHEET = f"""
QMainWindow, QWidget#central, QWidget#content {{
    background-color: {_PEARL};
}}
QWidget#body {{
    background-color: {_CARD};
}}

/* ── Header ────────────────────────────────────────────── */
QFrame#header {{
    background-color: {_PLUM};
    border: none;
}}
QLabel#app_name {{
    color: {_PEARL};
    font-family: Georgia;
    font-size: 28pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#tagline {{
    color: {_GOLD};
    font-family: "Segoe UI";
    font-size: 12pt;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#clock {{
    color: {_PEARL};
    font-family: Consolas;
    font-size: 48pt;
    background: transparent;
}}
QLabel#date_lbl {{
    color: {_DATE_FG};
    font-family: "Segoe UI";
    font-size: 20pt;
    background: transparent;
}}

/* ── Sidebar ────────────────────────────────────────────── */
QWidget#sidebar {{
    background-color: {_PEARL};
}}
QWidget#card_area {{
    background-color: {_PEARL};
}}

/* ── Card ──────────────────────────────────────────────── */
QFrame#card {{
    background-color: {_CARD};
    border: 1px solid {_PEARL_DEEP};
}}
QFrame#card_head {{
    background-color: {_CARD};
    border: none;
}}
QLabel#hearth_eye {{
    color: {_GOLD};
    font-family: "Segoe UI";
    font-size: 13pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#music_title {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 26pt;
    font-weight: bold;
    background: transparent;
}}
QPushButton#load_btn {{
    background-color: {_PEARL};
    color: {_PLUM_SOFT};
    border: 1px solid {_PEARL_DEEP};
    border-radius: 4px;
    padding: 6px 15px;
    font-family: "Segoe UI";
    font-size: 13pt;
}}
QPushButton#load_btn:hover {{
    background-color: {_PEARL_DEEP};
}}

/* ── Now playing ───────────────────────────────────────── */
QLabel#now_playing_lbl {{
    color: {_AZURE_DEEP};
    font-family: "Segoe UI";
    font-size: 13pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#track_title {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 25pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#track_artist {{
    color: {_PLUM_SOFT};
    font-family: "Segoe UI";
    font-size: 16pt;
    background: transparent;
}}
QLabel#track_album {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 13pt;
    font-style: italic;
    background: transparent;
}}
QLabel#time_lbl {{
    color: {_PLUM_SOFT};
    font-family: Consolas;
    font-size: 14pt;
    background: transparent;
    min-width: 54px;
}}

/* ── Progress slider ────────────────────────────────────── */
QSlider#progress::groove:horizontal {{
    background: {_PEARL_DEEP};
    height: 6px;
    border-radius: 3px;
    margin: 0px;
}}
QSlider#progress::sub-page:horizontal {{
    background: {_GOLD};
    height: 6px;
    border-radius: 3px;
}}
QSlider#progress::handle:horizontal {{
    background: {_GOLD};
    border: 3px solid {_CARD};
    width: 18px;
    height: 18px;
    margin: -6px 0px;
    border-radius: 9px;
}}

/* ── Controls (custom-painted — no QSS needed) ──────────── */

/* ── Queue ──────────────────────────────────────────────── */
QTreeWidget#queue {{
    background: {_CARD};
    border: none;
    outline: 0;
    font-family: "Segoe UI";
    font-size: 14pt;
    color: {_PLUM};
    show-decoration-selected: 0;
}}
QTreeWidget#queue::item {{
    height: 42px;
    border: none;
    padding: 0px 6px;
}}
QTreeWidget#queue::item:selected,
QTreeWidget#queue::item:selected:active {{
    background: transparent;
    color: {_PLUM};
}}
QHeaderView::section {{
    background-color: {_CARD};
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 12pt;
    border: none;
    border-bottom: 1px solid {_PEARL_DEEP};
    padding: 3px 6px;
}}

/* ── Shopping ───────────────────────────────────────────── */
QListWidget#shopping_list {{
    background: {_CARD};
    border: none;
    outline: 0;
    font-family: "Segoe UI";
    font-size: 14pt;
    color: {_PLUM};
}}
QListWidget#shopping_list::item {{
    height: 48px;
    border-bottom: 1px solid {_PEARL_DEEP};
    padding: 0px 6px;
}}
QListWidget#shopping_list::item:selected,
QListWidget#shopping_list::item:selected:active {{
    background: {_ACTIVE_BG};
    color: {_PLUM};
}}
QLineEdit#product_input {{
    background: {_PEARL};
    color: {_PLUM};
    border: 1px solid {_PEARL_DEEP};
    border-radius: 4px;
    padding: 6px 12px;
    font-family: "Segoe UI";
    font-size: 13pt;
}}
QLineEdit#product_input:focus {{
    border-color: {_GOLD};
    outline: none;
}}
QPushButton#remove_btn {{
    background: transparent;
    color: {_MUTED};
    border: none;
    border-radius: 15px;
    font-family: "Segoe UI";
    font-size: 19pt;
    font-weight: bold;
    padding: 0px;
}}
QPushButton#remove_btn:hover {{
    color: {_RUBY};
}}

/* ── Calendar ───────────────────────────────────────────── */
QPushButton#cal_nav {{
    background: transparent;
    border: none;
    color: {_PLUM};
    font-family: "Segoe UI";
    font-size: 24pt;
    font-weight: bold;
    padding: 0px 12px;
    min-width: 42px;
}}
QPushButton#cal_nav:hover {{
    color: {_GOLD};
}}
QLabel#cal_month {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 19pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#cal_day_header {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 13pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#cal_day {{
    color: {_PLUM};
    font-family: "Segoe UI";
    font-size: 14pt;
    background: transparent;
    border-radius: 24px;
}}
QLabel#cal_day:hover {{
    background: {_PEARL_DEEP};
}}

QLabel#cal_day_selected {{
    color: {_PLUM};
    font-family: "Segoe UI";
    font-size: 14pt;
    font-weight: bold;
    background: {_PEARL_DEEP};
    border-radius: 24px;
}}
QLabel#cal_detail_date {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 14pt;
    font-weight: bold;
    background: transparent;
}}

/* ── Calendar events panel ───────────────────────────────── */
QLabel#cal_events_title {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 12pt;
    font-weight: bold;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#cal_event_group {{
    color: {_GOLD};
    font-family: "Segoe UI";
    font-size: 12pt;
    font-weight: bold;
    background: transparent;
    padding-top: 18px;
    padding-bottom: 3px;
}}
QLabel#cal_event_name {{
    color: {_PLUM};
    font-family: "Segoe UI";
    font-size: 13pt;
    background: transparent;
}}
QLabel#cal_event_time {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 12pt;
    background: transparent;
}}
QLabel#cal_placeholder {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 13pt;
    background: transparent;
}}

/* ── Scrollbar ──────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {_PEARL};
    width: 12px;
    border: none;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {_PEARL_DEEP};
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
    border: none;
}}
"""


class PlayButton(QPushButton):
    """Circular ruby button with a gold-glow halo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing = False
        self.setFixedSize(120, 120)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_playing(self, playing: bool):
        if self._playing != playing:
            self._playing = playing
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r_btn, r_glow = 60, 60, 45, 57

        # Gold halo
        glow = QRadialGradient(float(cx), float(cy), float(r_glow))
        edge = r_btn / r_glow
        glow.setColorAt(max(0.0, edge - 0.12), QColor(217, 162, 39, 0))
        glow.setColorAt(edge,                   QColor(217, 162, 39, 170))
        glow.setColorAt(min(1.0, edge + 0.15),  QColor(217, 162, 39, 50))
        glow.setColorAt(1.0,                    QColor(217, 162, 39, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - r_glow, cy - r_glow, r_glow * 2, r_glow * 2)

        # Circle
        fill = QColor(_RUBY_DEEP) if self.underMouse() else QColor(_RUBY)
        p.setPen(QPen(QColor(_GOLD), 3.5))
        p.setBrush(QBrush(fill))
        p.drawEllipse(cx - r_btn, cy - r_btn, r_btn * 2, r_btn * 2)

        # Icon — drawn as shapes so they're crisp and perfectly centred
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("white")))
        if self._playing:
            # Pause: two vertical bars (centred at 60,60)
            p.drawRoundedRect(48, 45, 8, 30, 3, 3)
            p.drawRoundedRect(65, 45, 8, 30, 3, 3)
        else:
            # Play: right-pointing triangle (shifted +1 px right for visual balance)
            tri = QPainterPath()
            tri.moveTo(53, 45)
            tri.lineTo(53, 75)
            tri.lineTo(78, 60)
            tri.closeSubpath()
            p.drawPath(tri)


class SkipButton(QPushButton):
    """Compact skip button drawn as a filled triangle + bar."""

    def __init__(self, forward: bool, parent=None):
        super().__init__(parent)
        self._forward = forward
        self.setFixedSize(66, 66)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.isEnabled():
            color = QColor(_MUTED)
        elif self.underMouse():
            color = QColor(_AZURE_DEEP)
        else:
            color = QColor(_PLUM)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))

        # Icon: scaled 1.5× centred in 66×66 widget
        # y band: 23→44  |  x band: 21→46
        bw, bh, tw, gap = 5, 21, 16, 3  # bar width/height, triangle width, gap
        x0 = 21  # left edge

        if self._forward:
            tri = QPainterPath()
            tri.moveTo(x0,        23)
            tri.lineTo(x0,        44)
            tri.lineTo(x0 + tw,   33)
            tri.closeSubpath()
            p.drawPath(tri)
            p.drawRect(x0 + tw + gap, 23, bw, bh)
        else:
            p.drawRect(x0, 23, bw, bh)
            tri = QPainterPath()
            tri.moveTo(x0 + bw + gap + tw, 23)
            tri.lineTo(x0 + bw + gap + tw, 44)
            tri.lineTo(x0 + bw + gap,      33)
            tri.closeSubpath()
            p.drawPath(tri)


class NavButton(QPushButton):
    """Sidebar navigation button with a custom-painted icon."""

    def __init__(self, section: str, parent=None):
        super().__init__(parent)
        self._section = section
        self.setFixedSize(84, 84)
        self.setCheckable(True)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r = self.width() // 2, self.height() // 2, 33
        p.setPen(Qt.PenStyle.NoPen)
        if self.isChecked():
            p.setBrush(QBrush(QColor("#C8BA95")))
        elif self.underMouse():
            p.setBrush(QBrush(QColor("#D4C9A0")))
        else:
            p.setBrush(QBrush(QColor("#E0D5AE")))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        color = QColor(_PLUM)
        if self._section == "music":
            self._draw_music(p, color)
        elif self._section == "calendar":
            self._draw_calendar(p, color)
        else:
            self._draw_shopping(p, color)

    def _draw_music(self, p: QPainter, color: QColor):
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        # Note head 1 (left)
        p.save(); p.translate(32, 56); p.rotate(-20)
        p.drawEllipse(-9, -6, 18, 12)
        p.restore()
        # Note head 2 (right)
        p.save(); p.translate(54, 51); p.rotate(-20)
        p.drawEllipse(-9, -6, 18, 12)
        p.restore()
        # Stems + connecting beam
        pen = QPen(color, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(39, 51, 39, 27)
        p.drawLine(62, 47, 62, 23)
        p.drawLine(39, 27, 62, 23)

    def _draw_shopping(self, p: QPainter, color: QColor):
        pen = QPen(color, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Document outline
        p.drawRoundedRect(26, 24, 33, 36, 3, 3)
        # Three list lines
        p.drawLine(33, 35, 51, 35)
        p.drawLine(33, 44, 51, 44)
        p.drawLine(33, 53, 45, 53)

    def _draw_calendar(self, p: QPainter, color: QColor):
        pen = QPen(color, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Calendar outline
        p.drawRoundedRect(23, 27, 39, 33, 3, 3)
        # Header band
        p.drawLine(23, 36, 62, 36)
        # Ring hooks
        p.drawLine(32, 23, 32, 32)
        p.drawLine(53, 23, 53, 32)
        # Grid dots (2x2)
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        for col in (33, 45):
            for row in (44, 53):
                p.drawEllipse(col, row, 5, 5)


_PLANE_ICON = Path(__file__).parent.parent / "assets" / "plane-icon.png"


class _SmsButton(QPushButton):
    """Icon-only button using the plane-icon.png asset."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Envoyer par SMS")
        src = QPixmap(str(_PLANE_ICON)).scaled(
            40, 40,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._icon_normal = self._tint(src, QColor(_PLUM_SOFT))
        self._icon_hover  = self._tint(src, QColor(_GOLD))

    @staticmethod
    def _tint(src: "QPixmap", color: QColor) -> "QPixmap":
        result = QPixmap(src.size())
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.drawPixmap(0, 0, src)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(result.rect(), color)
        p.end()
        return result

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        px = self._icon_hover if self.underMouse() else self._icon_normal
        x = (self.width()  - px.width())  // 2
        y = (self.height() - px.height()) // 2
        p.drawPixmap(x, y, px)


class _QueueDelegate(QStyledItemDelegate):
    """Paints queue cells manually so QSS can't override per-item backgrounds."""

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)  # populates option.font / backgroundBrush

        painter.save()

        bg = option.backgroundBrush
        painter.fillRect(
            option.rect,
            bg if bg.style() != Qt.BrushStyle.NoBrush else QBrush(QColor(_CARD)),
        )

        painter.setFont(option.font)

        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        painter.setPen(fg.color() if fg else QColor(_PLUM))

        text  = index.data(Qt.ItemDataRole.DisplayRole) or ""
        align = index.data(Qt.ItemDataRole.TextAlignmentRole)
        if not align:
            align = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        painter.drawText(option.rect.adjusted(4, 0, -4, 0), align, text)

        painter.restore()


_DOT_PURPLE = "#9B59B6"
_DOT_YELLOW = "#F1E20F"
_DOT_ORDER  = [_DOT_PURPLE, _DOT_YELLOW, _GOLD]  # display order: most specific first


def _event_dot_color(summary: str) -> str:
    name = summary.lower()
    if "repos" in name or "congés" in name or "conges" in name:
        return _DOT_PURPLE
    if "hdom" in name:
        return _DOT_YELLOW
    return _GOLD


class _DayLabel(QLabel):
    """Day cell that paints a small colored dot and emits a click signal."""

    clicked = pyqtSignal(object)  # datetime.date

    def __init__(self, text: str, date: datetime.date,
                 dot_colors: set | None = None, parent=None):
        super().__init__(text, parent)
        self._date       = date
        self._dot_colors = dot_colors or set()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._date)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        colors = [c for c in _DOT_ORDER if c in self._dot_colors]
        if not colors:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        dot, gap = 6, 3
        total    = len(colors) * dot + (len(colors) - 1) * gap
        x        = self.width() // 2 - total // 2
        y        = self.height() - 10
        for c in colors:
            p.setBrush(QBrush(QColor(c)))
            p.drawEllipse(x, y, dot, dot)
            x += dot + gap
        p.end()


class CalendarWidget(QWidget):
    month_changed = pyqtSignal(int, int)   # year, month
    day_selected  = pyqtSignal(object)     # datetime.date

    _MONTHS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    _DAYS_FR   = ["L", "M", "M", "J", "V", "S", "D"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._today       = datetime.date.today()
        self._year        = self._today.year
        self._month       = self._today.month
        self._event_dates:   dict                  = {}
        self._selected_date: datetime.date | None  = None
        self._setup_ui()

    def set_event_dates(self, date_colors: dict):
        self._event_dates = date_colors
        self._rebuild()

    def _setup_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 24, 18, 24)
        v.setSpacing(15)

        nav = QHBoxLayout()
        self._prev_btn = QPushButton("‹")
        self._prev_btn.setObjectName("cal_nav")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_month)
        self._month_label = QLabel()
        self._month_label.setObjectName("cal_month")
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._next_btn = QPushButton("›")
        self._next_btn.setObjectName("cal_nav")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_month)
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._month_label, stretch=1)
        nav.addWidget(self._next_btn)
        v.addLayout(nav)

        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(3)
        self._grid.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._grid_container)
        v.addStretch()

        self._rebuild()

    def _rebuild(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._month_label.setText(f"{self._MONTHS_FR[self._month - 1]} {self._year}")

        for col, name in enumerate(self._DAYS_FR):
            lbl = QLabel(name)
            lbl.setObjectName("cal_day_header")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(69, 36)
            self._grid.addWidget(lbl, 0, col)

        first_day = datetime.date(self._year, self._month, 1)
        start_col = first_day.weekday()
        next_month_first = (
            datetime.date(self._year + 1, 1, 1) if self._month == 12
            else datetime.date(self._year, self._month + 1, 1)
        )
        days_in_month = (next_month_first - datetime.timedelta(days=1)).day

        row, col = 1, start_col
        for day in range(1, days_in_month + 1):
            cell_date = datetime.date(self._year, self._month, day)
            is_sel    = (cell_date == self._selected_date)
            dot_colors = self._event_dates.get(cell_date)
            lbl = _DayLabel(str(day), cell_date, dot_colors=dot_colors)
            if is_sel:
                lbl.setObjectName("cal_day_selected")
            else:
                lbl.setObjectName("cal_day")
            lbl.clicked.connect(self._on_day_clicked)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedSize(69, 51)
            self._grid.addWidget(lbl, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def _on_day_clicked(self, date: datetime.date):
        self._selected_date = date
        self._rebuild()
        self.day_selected.emit(date)

    def _prev_month(self):
        self._month -= 1
        if self._month < 1:
            self._month = 12
            self._year -= 1
        self._rebuild()
        self.month_changed.emit(self._year, self._month)

    def _next_month(self):
        self._month += 1
        if self._month > 12:
            self._month = 1
            self._year += 1
        self._rebuild()
        self.month_changed.emit(self._year, self._month)


class _CalendarFetcher(QObject):
    done  = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, start: datetime.date, end: datetime.date, parent=None):
        super().__init__(parent)
        self._start = start
        self._end   = end

    def run(self):
        all_events: list = []
        errors: list     = []
        for name, svc in [("Google", calendar_service), ("Microsoft", microsoft_calendar_service)]:
            try:
                all_events.extend(svc.get_events(self._start, self._end))
            except Exception as e:
                logger.warning("%s Calendar fetch skipped: %s", name, e)
                errors.append(f"{name} : {e}")

        if not all_events and errors:
            self.error.emit("\n".join(errors))
            return

        all_events.sort(key=lambda e: (
            e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
        ))
        self.done.emit(all_events)


class MainWindow(QMainWindow):
    def __init__(self, on_close):
        super().__init__()
        self._on_close = on_close
        self._last_queue_key = None

        self.setWindowTitle("Blancome")
        self.setMinimumSize(800, 600)
        self.resize(800, 600)
        if _ICON.exists():
            self.setWindowIcon(QIcon(str(_ICON)))

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_header())
        root.addWidget(FrillWidget())
        root.addWidget(self._make_content(), stretch=1)

        self._last_shopping_key: tuple | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(100)

        self._shopping_timer = QTimer(self)
        self._shopping_timer.timeout.connect(self._refresh_shopping)
        self._shopping_timer.start(2000)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(10_000)
        self._tick_clock()

        self._events_timer = QTimer(self)
        self._events_timer.timeout.connect(self._refresh_all_calendar)
        self._events_timer.start(300_000)  # refresh every 5 minutes
        QTimer.singleShot(0, self._refresh_all_calendar)  # initial load after UI is ready

    # ── Build helpers ────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")

        h = QHBoxLayout(header)
        h.setContentsMargins(60, 33, 60, 33)

        left = QVBoxLayout()
        left.setSpacing(6)
        app_name = QLabel("Blancome")
        app_name.setObjectName("app_name")
        tagline = QLabel("YOUR HOME, ATTENDED")
        tagline.setObjectName("tagline")
        left.addWidget(app_name)
        left.addWidget(tagline)

        right = QVBoxLayout()
        right.setSpacing(5)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._clock_lbl = QLabel()
        self._clock_lbl.setObjectName("clock")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._date_lbl = QLabel()
        self._date_lbl.setObjectName("date_lbl")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self._clock_lbl)
        right.addWidget(self._date_lbl)

        h.addLayout(left)
        h.addStretch()
        h.addLayout(right)
        return header

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(84)
        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 12, 0, 12)
        v.setSpacing(6)
        self._nav_music = NavButton("music")
        self._nav_music.setChecked(True)
        self._nav_shopping = NavButton("shopping")
        self._nav_calendar = NavButton("calendar")
        v.addWidget(self._nav_music)
        v.addWidget(self._nav_shopping)
        v.addWidget(self._nav_calendar)
        v.addStretch()
        return sidebar

    def _make_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("content")

        h = QHBoxLayout(content)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._make_sidebar())

        card_area = QWidget()
        card_area.setObjectName("card_area")
        ca = QHBoxLayout(card_area)
        ca.setContentsMargins(36, 24, 36, 24)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_card())
        self._stack.addWidget(self._make_shopping_card())
        self._stack.addWidget(self._make_calendar_card())
        ca.addWidget(self._stack)
        h.addWidget(card_area, stretch=1)

        self._nav_music.clicked.connect(lambda: self._switch_page(0))
        self._nav_shopping.clicked.connect(lambda: self._switch_page(1))
        self._nav_calendar.clicked.connect(lambda: self._switch_page(2))

        return content

    def _switch_page(self, index: int):
        self._stack.setCurrentIndex(index)
        self._nav_music.setChecked(index == 0)
        self._nav_shopping.setChecked(index == 1)
        self._nav_calendar.setChecked(index == 2)
        if index == 1:
            self._refresh_shopping()

    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(400)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        gold_band = QFrame()
        gold_band.setFixedHeight(6)
        gold_band.setStyleSheet(f"background: {_GOLD}; border: none;")
        v.addWidget(gold_band)
        v.addWidget(self._make_card_head())
        v.addWidget(_hsep())
        v.addWidget(self._make_body(), stretch=1)
        return card

    def _make_shopping_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(400)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        gold_band = QFrame()
        gold_band.setFixedHeight(6)
        gold_band.setStyleSheet(f"background: {_GOLD}; border: none;")
        v.addWidget(gold_band)

        head = QFrame()
        head.setObjectName("card_head")
        hh = QHBoxLayout(head)
        hh.setContentsMargins(30, 21, 30, 21)
        title = QLabel("Liste de courses")
        title.setObjectName("music_title")
        hh.addWidget(title)
        hh.addStretch()
        send_btn = _SmsButton()
        send_btn.clicked.connect(self._send_shopping_list)
        hh.addWidget(send_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        v.addWidget(head)

        v.addWidget(_hsep())

        body = QWidget()
        body.setObjectName("body")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(30, 24, 30, 24)
        bv.setSpacing(0)

        self._shopping_list = QListWidget()
        self._shopping_list.setObjectName("shopping_list")
        bv.addWidget(self._shopping_list, stretch=1)

        bv.addSpacing(15)
        bv.addWidget(_hsep())
        bv.addSpacing(15)

        add_row = QHBoxLayout()
        add_row.setSpacing(12)
        self._product_input = QLineEdit()
        self._product_input.setObjectName("product_input")
        self._product_input.setPlaceholderText("Nom du produit…")
        self._product_input.returnPressed.connect(self._add_product)
        add_btn = QPushButton("Ajouter")
        add_btn.setObjectName("load_btn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_product)
        add_row.addWidget(self._product_input, stretch=1)
        add_row.addWidget(add_btn)
        bv.addLayout(add_row)

        v.addWidget(body, stretch=1)
        return card

    def _make_calendar_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(500)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        gold_band = QFrame()
        gold_band.setFixedHeight(6)
        gold_band.setStyleSheet(f"background: {_GOLD}; border: none;")
        v.addWidget(gold_band)

        head = QFrame()
        head.setObjectName("card_head")
        hh = QHBoxLayout(head)
        hh.setContentsMargins(30, 21, 30, 21)
        title = QLabel("Calendrier")
        title.setObjectName("music_title")
        hh.addWidget(title)
        hh.addStretch()
        v.addWidget(head)

        v.addWidget(_hsep())

        body = QWidget()
        body.setObjectName("body")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)

        top = QWidget()
        top.setStyleSheet("background: transparent;")
        bh = QHBoxLayout(top)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(0)

        self._cal_widget = CalendarWidget()
        self._cal_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._cal_widget.month_changed.connect(self._on_calendar_month_changed)
        self._cal_widget.day_selected.connect(self._on_day_selected)
        events_panel = self._make_events_panel()
        events_panel.setMinimumWidth(200)
        bh.addWidget(self._cal_widget, stretch=2)
        bh.addWidget(_vsep())
        bh.addWidget(events_panel, stretch=1)

        bv.addWidget(top, stretch=1)
        bv.addWidget(_hsep())
        bv.addWidget(self._make_day_detail_panel())

        v.addWidget(body, stretch=1)
        return card

    def _make_events_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("body")
        v = QVBoxLayout(panel)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(0)

        title = QLabel("À VENIR")
        title.setObjectName("cal_events_title")
        v.addWidget(title)
        v.addSpacing(12)
        v.addWidget(_hsep())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        self._events_container = QWidget()
        self._events_container.setStyleSheet("background: transparent;")
        self._events_layout = QVBoxLayout(self._events_container)
        self._events_layout.setContentsMargins(0, 6, 6, 0)
        self._events_layout.setSpacing(0)
        self._events_layout.addStretch()
        scroll.setWidget(self._events_container)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)

        v.addWidget(scroll, stretch=1)
        return panel

    def _clear_events_panel(self):
        while self._events_layout.count() > 1:
            item = self._events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_all_calendar(self):
        self._refresh_calendar_events()
        self._refresh_month_dots(self._cal_widget._year, self._cal_widget._month)

    def _refresh_calendar_events(self):
        if hasattr(self, "_cal_thread") and self._cal_thread.isRunning():
            return
        self._clear_events_panel()
        loading = QLabel("Chargement…")
        loading.setObjectName("cal_placeholder")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._events_layout.insertWidget(0, loading)

        today = datetime.date.today()
        self._cal_fetcher = _CalendarFetcher(today, today + datetime.timedelta(days=30))
        self._cal_thread  = QThread(self)
        self._cal_fetcher.moveToThread(self._cal_thread)
        self._cal_thread.started.connect(self._cal_fetcher.run)
        self._cal_fetcher.done.connect(self._on_events_fetched)
        self._cal_fetcher.error.connect(self._on_events_error)
        self._cal_fetcher.done.connect(self._cal_thread.quit)
        self._cal_fetcher.error.connect(self._cal_thread.quit)
        self._cal_thread.finished.connect(self._cal_fetcher.deleteLater)
        self._cal_thread.start()

    def _on_events_fetched(self, events: list):
        self._clear_events_panel()
        if not events:
            lbl = QLabel("Aucun événement\nà venir")
            lbl.setObjectName("cal_placeholder")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._events_layout.insertWidget(0, lbl)
            return

        today    = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        _day_fr  = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."]
        _mon_fr  = ["jan.", "fév.", "mar.", "avr.", "mai", "juin",
                    "juil.", "août", "sep.", "oct.", "nov.", "déc."]

        current_date = None
        pos = 0
        for event in events:
            start  = event.get("start", {})
            dt_str = start.get("dateTime", start.get("date", ""))
            if not dt_str:
                continue
            try:
                if "T" in dt_str:
                    dt         = datetime.datetime.fromisoformat(dt_str)
                    event_date = dt.date()
                    time_str   = dt.strftime("%H:%M")
                    end_str    = event.get("end", {}).get("dateTime", "")
                    if end_str:
                        time_str += " – " + datetime.datetime.fromisoformat(end_str).strftime("%H:%M")
                else:
                    event_date = datetime.date.fromisoformat(dt_str)
                    time_str   = "Toute la journée"
            except ValueError:
                continue

            if event_date != current_date:
                current_date = event_date
                if event_date == today:
                    group_text = "Aujourd'hui"
                elif event_date == tomorrow:
                    group_text = "Demain"
                else:
                    group_text = (f"{_day_fr[event_date.weekday()]} "
                                  f"{event_date.day} {_mon_fr[event_date.month - 1]}")
                grp = QLabel(group_text)
                grp.setObjectName("cal_event_group")
                self._events_layout.insertWidget(pos, grp)
                pos += 1

            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rh = QHBoxLayout(row)
            rh.setContentsMargins(0, 3, 0, 3)
            rh.setSpacing(6)

            dot_lbl = QLabel("●")
            dot_lbl.setFixedWidth(15)
            dot_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            dot_lbl.setStyleSheet(
                f"color: {_event_dot_color(event.get('summary', ''))};"
                "background: transparent; font-size: 10pt; padding-top: 2px;"
            )

            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            rv = QVBoxLayout(inner)
            rv.setContentsMargins(0, 0, 0, 0)
            rv.setSpacing(1)
            time_lbl = QLabel(time_str)
            time_lbl.setObjectName("cal_event_time")
            name_lbl = QLabel(event.get("summary", "(Sans titre)"))
            name_lbl.setObjectName("cal_event_name")
            name_lbl.setWordWrap(True)
            rv.addWidget(time_lbl)
            rv.addWidget(name_lbl)

            rh.addWidget(dot_lbl)
            rh.addWidget(inner, stretch=1)
            self._events_layout.insertWidget(pos, row)
            pos += 1

    def _on_events_error(self, message: str):
        self._clear_events_panel()
        lbl = QLabel(message)
        lbl.setObjectName("cal_placeholder")
        lbl.setWordWrap(True)
        retry_btn = QPushButton("Réessayer")
        retry_btn.setObjectName("load_btn")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._refresh_calendar_events)
        self._events_layout.insertWidget(0, retry_btn)
        self._events_layout.insertWidget(0, lbl)

    def _refresh_month_dots(self, year: int, month: int):
        if hasattr(self, "_dots_thread") and self._dots_thread.isRunning():
            return
        start = datetime.date(year, month, 1)
        end   = (datetime.date(year + 1, 1, 1) if month == 12
                 else datetime.date(year, month + 1, 1)) - datetime.timedelta(days=1)
        self._dots_fetcher = _CalendarFetcher(start, end)
        self._dots_thread  = QThread(self)
        self._dots_fetcher.moveToThread(self._dots_thread)
        self._dots_thread.started.connect(self._dots_fetcher.run)
        self._dots_fetcher.done.connect(self._on_dots_fetched)
        self._dots_fetcher.done.connect(self._dots_thread.quit)
        self._dots_fetcher.error.connect(self._dots_thread.quit)
        self._dots_thread.finished.connect(self._dots_fetcher.deleteLater)
        self._dots_thread.start()

    def _on_dots_fetched(self, events: list):
        self._cached_month_events = events
        date_colors: dict = {}
        for ev in events:
            s  = ev.get("start", {})
            ds = s.get("dateTime", s.get("date", ""))
            try:
                d = (datetime.datetime.fromisoformat(ds).date() if "T" in ds
                     else datetime.date.fromisoformat(ds))
            except ValueError:
                continue
            date_colors.setdefault(d, set()).add(_event_dot_color(ev.get("summary", "")))
        self._cal_widget.set_event_dates(date_colors)

    def _on_calendar_month_changed(self, year: int, month: int):
        self._cached_month_events = []
        self._detail_date_lbl.setText("")
        while self._detail_events_layout.count() > 1:
            item = self._detail_events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._refresh_month_dots(year, month)

    def _make_day_detail_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedHeight(150)
        panel.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(30, 15, 30, 15)
        outer.setSpacing(6)

        self._detail_date_lbl = QLabel("")
        self._detail_date_lbl.setObjectName("cal_detail_date")
        outer.addWidget(self._detail_date_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        self._detail_events_container = QWidget()
        self._detail_events_container.setStyleSheet("background: transparent;")
        self._detail_events_layout = QVBoxLayout(self._detail_events_container)
        self._detail_events_layout.setContentsMargins(0, 0, 6, 0)
        self._detail_events_layout.setSpacing(0)
        self._detail_events_layout.addStretch()
        scroll.setWidget(self._detail_events_container)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)

        outer.addWidget(scroll, stretch=1)
        return panel

    def _on_day_selected(self, date: datetime.date):
        _day_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        _mon_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                   "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        self._detail_date_lbl.setText(
            f"{_day_fr[date.weekday()]} {date.day} {_mon_fr[date.month - 1]} {date.year}"
        )

        while self._detail_events_layout.count() > 1:
            item = self._detail_events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        day_events = []
        for ev in getattr(self, "_cached_month_events", []):
            s  = ev.get("start", {})
            ds = s.get("dateTime", s.get("date", ""))
            try:
                d = (datetime.datetime.fromisoformat(ds).date() if "T" in ds
                     else datetime.date.fromisoformat(ds))
                if d == date:
                    day_events.append(ev)
            except ValueError:
                pass

        if not day_events:
            lbl = QLabel("Aucun événement")
            lbl.setObjectName("cal_placeholder")
            self._detail_events_layout.insertWidget(0, lbl)
            return

        for i, ev in enumerate(day_events):
            s  = ev.get("start", {})
            ds = s.get("dateTime", s.get("date", ""))
            try:
                if "T" in ds:
                    dt       = datetime.datetime.fromisoformat(ds)
                    time_str = dt.strftime("%H:%M")
                    end_ds   = ev.get("end", {}).get("dateTime", "")
                    if end_ds:
                        time_str += " – " + datetime.datetime.fromisoformat(end_ds).strftime("%H:%M")
                else:
                    time_str = "Toute la journée"
            except ValueError:
                time_str = ""

            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rv = QHBoxLayout(row)
            rv.setContentsMargins(0, 1, 0, 1)
            rv.setSpacing(6)

            dot_lbl = QLabel("●")
            dot_lbl.setFixedWidth(15)
            dot_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            dot_lbl.setStyleSheet(
                f"color: {_event_dot_color(ev.get('summary', ''))};"
                "background: transparent; font-size: 10pt;"
            )

            time_lbl = QLabel(time_str)
            time_lbl.setObjectName("cal_event_time")
            time_lbl.setFixedWidth(150)
            name_lbl = QLabel(ev.get("summary", "(Sans titre)"))
            name_lbl.setObjectName("cal_event_name")
            name_lbl.setWordWrap(True)

            rv.addWidget(dot_lbl)
            rv.addWidget(time_lbl)
            rv.addWidget(name_lbl, stretch=1)
            self._detail_events_layout.insertWidget(i, row)

    def _make_card_head(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card_head")

        h = QHBoxLayout(frame)
        h.setContentsMargins(30, 21, 30, 21)

        title = QLabel("Musique")
        title.setObjectName("music_title")

        left = QHBoxLayout()
        left.setSpacing(10)
        left.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        left.addWidget(title)

        load_btn = QPushButton("Charger une playlist")
        load_btn.setObjectName("load_btn")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._open_playlist)

        h.addLayout(left)
        h.addStretch()
        h.addWidget(load_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        return frame

    def _make_body(self) -> QWidget:
        body = QWidget()
        body.setObjectName("body")

        outer = QHBoxLayout(body)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left: now-playing info + controls ──────────────────
        left_widget = QWidget()
        left_widget.setObjectName("body")
        v = QVBoxLayout(left_widget)
        v.setContentsMargins(30, 24, 30, 24)
        v.setSpacing(0)

        now_lbl = QLabel("EN COURS")
        now_lbl.setObjectName("now_playing_lbl")
        v.addWidget(now_lbl)

        self._title_lbl = QLabel("—")
        self._title_lbl.setObjectName("track_title")
        self._title_lbl.setWordWrap(True)
        v.addWidget(self._title_lbl)
        v.addSpacing(6)

        self._artist_lbl = QLabel("—")
        self._artist_lbl.setObjectName("track_artist")
        self._artist_lbl.setWordWrap(True)
        v.addWidget(self._artist_lbl)
        v.addSpacing(3)

        self._album_lbl = QLabel()
        self._album_lbl.setObjectName("track_album")
        self._album_lbl.setWordWrap(True)
        v.addWidget(self._album_lbl)
        v.addSpacing(18)

        v.addLayout(self._make_progress_row())
        v.addSpacing(12)
        v.addLayout(self._make_controls_row())
        v.addStretch()

        outer.addWidget(left_widget, stretch=1)
        outer.addWidget(_vsep())

        # ── Right: queue ────────────────────────────────────────
        right_widget = QWidget()
        right_widget.setObjectName("body")
        qv = QVBoxLayout(right_widget)
        qv.setContentsMargins(0, 0, 0, 0)
        qv.setSpacing(0)
        qv.addWidget(self._make_queue())

        outer.addWidget(right_widget, stretch=1)
        return body

    def _make_progress_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(15)

        self._cur_lbl = QLabel("0:00")
        self._cur_lbl.setObjectName("time_lbl")
        self._cur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._cur_lbl.setFixedWidth(54)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("progress")
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setEnabled(False)  # display-only until seek is implemented

        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setObjectName("time_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._dur_lbl.setFixedWidth(54)

        h.addWidget(self._cur_lbl)
        h.addWidget(self._slider)
        h.addWidget(self._dur_lbl)
        return h

    def _make_controls_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        h.setSpacing(12)

        self._prev_btn = SkipButton(forward=False)
        self._prev_btn.clicked.connect(music_service.previous)

        self._play_btn = PlayButton()
        self._play_btn.clicked.connect(music_service.toggle_pause)

        self._next_btn = SkipButton(forward=True)
        self._next_btn.clicked.connect(music_service.next)

        h.addWidget(self._prev_btn)
        h.addWidget(self._play_btn)
        h.addWidget(self._next_btn)
        return h

    def _make_queue(self) -> QTreeWidget:
        tv = QTreeWidget()
        tv.setObjectName("queue")
        tv.setColumnCount(3)
        tv.setHeaderHidden(True)
        tv.header().setMinimumSectionSize(0)
        tv.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        tv.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tv.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        tv.header().setStretchLastSection(False)
        tv.setColumnWidth(0, 54)
        tv.setColumnWidth(2, 78)
        tv.setRootIsDecorated(False)
        tv.setUniformRowHeights(True)
        tv.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tv.setItemDelegate(_QueueDelegate(tv))
        tv.itemClicked.connect(self._on_queue_click)
        self._queue_tv = tv
        return tv

    # ── Slots ────────────────────────────────────────────────────────────

    def _open_playlist(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une playlist", "", _PLAYLIST_FILETYPES)
        if path:
            music_service.load_playlist(path)

    def _add_product(self):
        text = self._product_input.text().strip()
        if text:
            shopping_service.add_item(text)
            self._product_input.clear()
            self._refresh_shopping()

    def _send_shopping_list(self):
        shopping_service.send_list()
        self._refresh_shopping()

    def _remove_product(self, text: str):
        shopping_service.remove_item(text)
        self._refresh_shopping()

    def _refresh_shopping(self):
        items = shopping_service.get_items()
        key = tuple(items)
        if key != self._last_shopping_key:
            self._last_shopping_key = key
            self._shopping_list.clear()
            for text in items:
                self._add_list_row(text)

    def _add_list_row(self, text: str):
        item = QListWidgetItem(self._shopping_list)
        item.setSizeHint(QSize(0, 54))

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 0, 6, 0)
        h.setSpacing(12)

        btn = QPushButton("×")
        btn.setObjectName("remove_btn")
        btn.setFixedSize(33, 33)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, t=text: self._remove_product(t))
        h.addWidget(btn)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {_PLUM}; font-family: 'Segoe UI'; font-size: 14pt; background: transparent;"
        )
        h.addWidget(lbl, stretch=1)

        self._shopping_list.setItemWidget(item, row)

    def _on_queue_click(self, item: QTreeWidgetItem, _col: int):
        idx = self._queue_tv.indexOfTopLevelItem(item)
        if idx >= 0:
            music_service.play_track(idx)

    def _tick_clock(self):
        now = datetime.datetime.now()
        self._clock_lbl.setText(now.strftime("%H:%M"))
        day   = _FR_DAYS[now.weekday()].capitalize()
        month = _FR_MONTHS[now.month - 1]
        self._date_lbl.setText(f"{day} {now.day} {month}")

    def _update(self):
        info = music_service.current_track_info()
        self._title_lbl.setText(info.get("title") or "—")
        self._artist_lbl.setText(info.get("artist") or "—")
        self._album_lbl.setText(info.get("album") or "")

        cur, dur = music_service.get_position()
        self._cur_lbl.setText(_fmt_time(cur))
        self._dur_lbl.setText(_fmt_time(dur))
        self._slider.blockSignals(True)
        self._slider.setValue(int(cur / dur * 1000) if dur > 0 else 0)
        self._slider.blockSignals(False)

        self._play_btn.set_playing(music_service.is_playing())

        active = music_service.is_playing() or music_service.is_paused()
        self._prev_btn.setEnabled(active)
        self._next_btn.setEnabled(active)

        tracks, idx = music_service.get_queue()
        key = (tuple(t["name"] for t in tracks), idx)
        if key != self._last_queue_key:
            self._last_queue_key = key
            tv = self._queue_tv
            tv.clear()
            active_brush = QBrush(QColor(_ACTIVE_BG))
            active_fg    = QBrush(QColor(_AZURE_DEEP))
            for i, t in enumerate(tracks):
                title   = t.get("title") or t["name"]
                artist  = t.get("artist") or ""
                display = f"{title}  —  {artist}" if artist else title
                dur_t   = t.get("duration")
                dur_str = _fmt_time(dur_t) if dur_t else "—"

                item = QTreeWidgetItem([str(i + 1), display, dur_str])
                item.setTextAlignment(0, Qt.AlignmentFlag.AlignRight  | Qt.AlignmentFlag.AlignVCenter)
                item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight  | Qt.AlignmentFlag.AlignVCenter)
                if i == idx:
                    for col in range(3):
                        item.setBackground(col, active_brush)
                    for col in (0, 1):
                        item.setForeground(col, active_fg)
                        f = item.font(col)
                        f.setBold(True)
                        item.setFont(col, f)
                tv.addTopLevelItem(item)

            if 0 <= idx < tv.topLevelItemCount():
                tv.scrollToItem(tv.topLevelItem(idx))

    def closeEvent(self, event):
        self._timer.stop()
        self._clock_timer.stop()
        self._shopping_timer.stop()
        self._on_close()
        event.accept()


def run(on_close):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("blancome.app")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLESHEET)

    window = MainWindow(on_close)
    window.show()
    app.exec()
