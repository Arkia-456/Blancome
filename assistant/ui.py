import ctypes
import logging
import ssl
import sys
import threading
import datetime
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QFrame, QHeaderView, QAbstractItemView, QSlider, QSizePolicy,
    QStyledItemDelegate, QStackedWidget, QListWidget, QListWidgetItem, QLineEdit,
    QScrollArea, QScroller, QMenu, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, QObject, QPoint, QPropertyAnimation, pyqtSignal, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QIcon, QBrush, QRadialGradient, QFont, QPixmap

import qtawesome as qta

from assistant.music_service import music_service
from assistant.shopping_service import shopping_service
from assistant.settings_service import settings_service
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
    padding-top: 6px;
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

/* ── Settings ───────────────────────────────────────────── */
QLabel#settings_section {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 10pt;
    font-weight: bold;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#settings_field_label {{
    color: {_PLUM_SOFT};
    font-family: "Segoe UI";
    font-size: 12pt;
    background: transparent;
}}
QLineEdit#settings_input {{
    background: {_PEARL};
    color: {_PLUM};
    border: 1px solid {_PEARL_DEEP};
    border-radius: 4px;
    padding: 6px 12px;
    font-family: "Segoe UI";
    font-size: 12pt;
}}
QLineEdit#settings_input:focus {{
    border-color: {_GOLD};
    outline: none;
}}
QLineEdit#settings_input:read-only {{
    color: {_PLUM_SOFT};
}}
QPushButton#save_btn {{
    background-color: {_PLUM};
    color: {_PEARL};
    border: none;
    border-radius: 4px;
    padding: 9px 28px;
    font-family: "Segoe UI";
    font-size: 12pt;
    font-weight: bold;
}}
QPushButton#save_btn:hover {{
    background-color: {_PLUM_SOFT};
}}
QPushButton#save_btn:disabled {{
    background-color: {_MUTED};
}}
QPushButton#add_playlist_btn {{
    background: transparent;
    color: {_GOLD};
    border: 1px dashed {_GOLD};
    border-radius: 4px;
    padding: 5px 14px;
    font-family: "Segoe UI";
    font-size: 11pt;
}}
QPushButton#add_playlist_btn:hover {{
    background-color: {_PEARL};
}}

/* ── Tooltip ────────────────────────────────────────────── */
QToolTip {{
    background-color: white;
    color: {_PLUM};
    border: 1px solid {_PEARL_DEEP};
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Segoe UI";
    font-size: 11pt;
}}

/* ── Settings scroll area ───────────────────────────────── */
QScrollArea#settings_scroll {{
    background: {_CARD};
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
        self._px_play  = qta.icon('fa6s.play',  color='white').pixmap(QSize(40, 40))
        self._px_pause = qta.icon('fa6s.pause', color='white').pixmap(QSize(40, 40))

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

        # Icon
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        px = self._px_pause if self._playing else self._px_play
        # play icon is visually left-heavy — nudge 2 px right for optical balance
        ox = 2 if not self._playing else 0
        dpr = px.devicePixelRatio()
        x = (self.width()  - px.width()  / dpr) / 2 + ox
        y = (self.height() - px.height() / dpr) / 2
        p.drawPixmap(int(x), int(y), px)


class _IconButton(QPushButton):
    """Transparent icon-only button using a qtawesome glyph."""

    def __init__(self, icon_name, btn_size, icon_size, color, hover_color,
                 disabled_color=None, active_color=None, tooltip='', parent=None):
        super().__init__(parent)
        self._active = False
        self.setFixedSize(btn_size, btn_size)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self._px          = qta.icon(icon_name, color=color).pixmap(QSize(icon_size, icon_size))
        self._px_hover    = qta.icon(icon_name, color=hover_color).pixmap(QSize(icon_size, icon_size))
        self._px_disabled = qta.icon(icon_name, color=disabled_color or _MUTED).pixmap(QSize(icon_size, icon_size))
        self._px_active   = qta.icon(icon_name, color=active_color or hover_color).pixmap(QSize(icon_size, icon_size))

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not self.isEnabled():
            px = self._px_disabled
        elif self._active:
            px = self._px_active
        elif self.underMouse():
            px = self._px_hover
        else:
            px = self._px
        dpr = px.devicePixelRatio()
        x = (self.width()  - px.width()  / dpr) / 2
        y = (self.height() - px.height() / dpr) / 2
        p.drawPixmap(int(x), int(y), px)


class NavButton(QPushButton):
    """Sidebar navigation button with a qtawesome icon on a painted circle."""

    _ICONS = {
        'music':    'fa6s.music',
        'shopping': 'fa6s.cart-shopping',
        'calendar': 'fa6s.calendar-days',
        'settings': 'fa6s.gear',
    }

    def __init__(self, section: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(84, 84)
        self.setCheckable(True)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._px = qta.icon(self._ICONS[section], color=_PLUM).pixmap(QSize(36, 36))

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
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        dpr = self._px.devicePixelRatio()
        x = (self.width()  - self._px.width()  / dpr) / 2
        y = (self.height() - self._px.height() / dpr) / 2
        p.drawPixmap(int(x), int(y), self._px)


class _SeekSlider(QSlider):
    """QSlider that jumps to the clicked position instead of page-stepping."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ratio = max(0.0, min(1.0, event.position().x() / self.width()))
            value = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
            self.setValue(value)
        super().mousePressEvent(event)


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


_AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".wma", ".opus"}


class _DroppableQueueWidget(QTreeWidget):
    """QTreeWidget that accepts audio file drops from the OS file explorer."""

    def __init__(self, on_drop):
        super().__init__()
        self.setAcceptDrops(True)
        self._on_drop = on_drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
            if any(p.suffix.lower() in _AUDIO_EXTENSIONS for p in paths):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [
            Path(u.toLocalFile())
            for u in event.mimeData().urls()
            if Path(u.toLocalFile()).suffix.lower() in _AUDIO_EXTENSIONS
        ]
        if paths:
            self._on_drop(paths)
        event.acceptProposedAction()


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


def _event_day_occurrences(event: dict) -> list:
    """Return a list of (date, time_str) for every calendar day the event covers.

    All-day events use an exclusive end date (Google/Microsoft convention), so
    an event with end=2026-06-20 appears on June 18 and 19 only.
    Timed events are inclusive on both ends (e.g. 22:00→06:00 covers two days).
    """
    start = event.get("start", {})
    end   = event.get("end",   {})
    ds    = start.get("dateTime", start.get("date", ""))
    de    = end.get("dateTime",   end.get("date", ""))
    if not ds:
        return []
    try:
        if "T" in ds:
            start_dt   = datetime.datetime.fromisoformat(ds)
            start_date = start_dt.date()
            time_str   = start_dt.strftime("%H:%M")
            if de:
                end_dt   = datetime.datetime.fromisoformat(de)
                end_date = end_dt.date()
                time_str += " – " + end_dt.strftime("%H:%M")
            else:
                end_date = start_date
        else:
            start_date = datetime.date.fromisoformat(ds)
            time_str   = "Toute la journée"
            if de:
                end_date = datetime.date.fromisoformat(de) - datetime.timedelta(days=1)
            else:
                end_date = start_date
    except ValueError:
        return []

    result = []
    day = start_date
    while day <= end_date:
        result.append((day, time_str))
        day += datetime.timedelta(days=1)
    return result


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
        v.setContentsMargins(18, 8, 18, 8)
        v.setSpacing(6)

        nav = QHBoxLayout()
        self._prev_btn = _IconButton('fa6s.angle-left',  42, 20, _PLUM_SOFT, _GOLD)
        self._prev_btn.clicked.connect(self._prev_month)
        self._month_label = QLabel()
        self._month_label.setObjectName("cal_month")
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._next_btn = _IconButton('fa6s.angle-right', 42, 20, _PLUM_SOFT, _GOLD)
        self._next_btn.clicked.connect(self._next_month)
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._month_label, stretch=1)
        nav.addWidget(self._next_btn)
        v.addLayout(nav)

        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setHorizontalSpacing(3)
        self._grid.setVerticalSpacing(1)
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
            lbl.setFixedSize(69, 14)
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

    def __init__(self, start: datetime.date, end: datetime.date, stop_event, parent=None):
        super().__init__(parent)
        self._start = start
        self._end   = end
        self._stop  = stop_event

    def run(self):
        all_events: list = []
        errors: list     = []
        for name, svc in [("Google", calendar_service), ("Microsoft", microsoft_calendar_service)]:
            for attempt in range(3):
                if self._stop.is_set():
                    return
                try:
                    all_events.extend(svc.get_events(self._start, self._end))
                    break
                except Exception as e:
                    transient = (
                        isinstance(e, (ssl.SSLError, TimeoutError))
                        or "timed out" in str(e).lower()
                        or "eof occurred" in str(e).lower()
                    )
                    if attempt < 2 and transient:
                        logger.warning("%s Calendar transient error (attempt %d/3), retrying: %s", name, attempt + 1, e)
                        if self._stop.wait(2 ** attempt):
                            return
                    else:
                        logger.warning("%s Calendar fetch skipped: %s", name, e)
                        errors.append(f"{name} : {e}")
                        break

        if not all_events and errors:
            self.error.emit("\n".join(errors))
            return

        all_events.sort(key=lambda e: (
            e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
        ))
        self.done.emit(all_events)


_TOAST_W  = 280
_TOAST_MS = 4000
_FADE_MS  = 600


class _CalendarToast(QWidget):
    _BAR_H  = 5
    _TEXT_H = 50

    def __init__(self, message: str, parent):
        super().__init__(parent)
        self.setFixedSize(_TOAST_W, self._TEXT_H + self._BAR_H)

        msg_lower = message.lower()
        if "timed out" in msg_lower or "timeout" in msg_lower:
            self._text = "Délai de connexion dépassé"
        elif "ssl" in msg_lower or "eof occurred" in msg_lower:
            self._text = "Erreur SSL"
        else:
            self._text = "Erreur de connexion"

        self._ratio = 1.0
        self._alpha = 1.0

        self._prog = QPropertyAnimation(self, b"bar_ratio", self)
        self._prog.setDuration(_TOAST_MS)
        self._prog.setStartValue(1.0)
        self._prog.setEndValue(0.0)
        QTimer.singleShot(0, self._prog.start)

        self._fade = QPropertyAnimation(self, b"opacity_val", self)
        self._fade.setDuration(_FADE_MS)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self.deleteLater)
        QTimer.singleShot(_TOAST_MS, self._fade.start)

    def _get_ratio(self): return self._ratio
    def _set_ratio(self, v):
        self._ratio = max(0.0, min(1.0, v))
        self.update()
    bar_ratio = pyqtProperty(float, _get_ratio, _set_ratio)

    def _get_alpha(self): return self._alpha
    def _set_alpha(self, v):
        self._alpha = max(0.0, min(1.0, v))
        self.update()
    opacity_val = pyqtProperty(float, _get_alpha, _set_alpha)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._alpha)

        clip = QPainterPath()
        clip.addRoundedRect(0.5, 0.5, self.width() - 1, self.height() - 1, 6, 6)
        p.setClipPath(clip)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_CARD))
        p.drawPath(clip)

        if self._ratio > 0:
            bar_w = int(self.width() * self._ratio)
            p.setBrush(QColor(_PLUM))
            p.drawRect(self.width() - bar_w, self.height() - self._BAR_H, bar_w, self._BAR_H)

        p.setClipping(False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(_PLUM_SOFT), 1))
        p.drawPath(clip)

        p.setPen(QColor(_PLUM))
        p.setFont(QFont("Segoe UI", 11))
        fm = p.fontMetrics()
        ty = (self._TEXT_H - fm.height()) // 2 + fm.ascent()
        p.drawText(12, ty, self._text)


class _UnsavedChangesDialog(QDialog):
    """Frameless confirmation dialog matching the app's card style."""

    QUIT          = 1
    SAVE_AND_QUIT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(430)
        self.action = self.QUIT
        self._setup_ui()

    def _setup_ui(self):
        # _PEARL_DEEP background bleeds through the 1-px margin as the border;
        # the inner frame's border-radius creates the rounded-corner effect.
        self.setStyleSheet(f"QDialog {{ background: {_PEARL_DEEP}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        inner = QFrame()
        inner.setStyleSheet(f"QFrame {{ background: {_CARD}; border: none; border-radius: 3px; }}")
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(0)

        band = QFrame()
        band.setFixedHeight(5)
        band.setStyleSheet(
            f"background: {_GOLD}; border: none;"
            " border-top-left-radius: 3px; border-top-right-radius: 3px;"
        )
        iv.addWidget(band)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(30, 24, 30, 18)
        bv.setSpacing(10)

        title_lbl = QLabel("Modifications non enregistrées")
        title_lbl.setStyleSheet(
            f"color: {_PLUM}; font-family: Georgia; font-size: 15pt;"
            " font-weight: bold; background: transparent;"
        )
        title_lbl.setWordWrap(True)

        msg_lbl = QLabel(
            "Vous avez des modifications non enregistrées dans les paramètres.\n"
            "Voulez-vous quitter sans enregistrer ?"
        )
        msg_lbl.setStyleSheet(
            f"color: {_PLUM_SOFT}; font-family: 'Segoe UI'; font-size: 12pt;"
            " background: transparent;"
        )
        msg_lbl.setWordWrap(True)

        bv.addWidget(title_lbl)
        bv.addSpacing(4)
        bv.addWidget(msg_lbl)
        iv.addWidget(body)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_PEARL_DEEP}; border: none;")
        iv.addWidget(sep)

        btn_bar = QWidget()
        btn_bar.setStyleSheet("background: transparent;")
        bh = QHBoxLayout(btn_bar)
        bh.setContentsMargins(24, 16, 24, 20)
        bh.setSpacing(10)

        quit_btn = QPushButton("Quitter")
        quit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_MUTED};
                border: 1px solid {_PEARL_DEEP};
                border-radius: 4px;
                padding: 8px 14px;
                font-family: "Segoe UI";
                font-size: 11pt;
            }}
            QPushButton:hover {{
                color: {_RUBY};
                border-color: {_RUBY};
                background: transparent;
            }}
        """)
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self._on_quit)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_PLUM};
                border: 1px solid {_PLUM};
                border-radius: 4px;
                padding: 8px 14px;
                font-family: "Segoe UI";
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background: {_PLUM};
                color: {_PEARL};
            }}
        """)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        save_quit_btn = QPushButton("Enregistrer et quitter")
        save_quit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_PLUM};
                color: {_PEARL};
                border: none;
                border-radius: 4px;
                padding: 8px 22px;
                font-family: "Segoe UI";
                font-size: 11pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {_PLUM_SOFT};
            }}
        """)
        save_quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_quit_btn.setDefault(True)
        save_quit_btn.clicked.connect(self._on_save_and_quit)

        bh.addWidget(quit_btn)
        bh.addStretch()
        bh.addWidget(cancel_btn)
        bh.addWidget(save_quit_btn)
        iv.addWidget(btn_bar)

        outer.addWidget(inner)

    def _on_quit(self):
        self.action = self.QUIT
        self.accept()

    def _on_save_and_quit(self):
        self.action = self.SAVE_AND_QUIT
        self.accept()


class VoiceLoaderThread(QThread):
    ready  = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, listener, parent=None):
        super().__init__(parent)
        self._listener = listener

    def run(self):
        try:
            self._listener.load_model()
            self.ready.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class VoiceStatusWidget(QWidget):
    retry_requested = pyqtSignal()

    _STATES = {
        "loading": (_GOLD,       "fa5s.microphone",       "Voix : chargement…"),
        "ready":   (_AZURE_DEEP, "fa5s.microphone",       "Voix : active"),
        "failed":  (_RUBY,       "fa5s.microphone-slash", "Voix : erreur  ↺"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "loading"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)

        self._icon_lbl = QLabel()
        self._text_lbl = QLabel()

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._text_lbl)
        layout.addStretch()

        self._effect = QGraphicsOpacityEffect(self)
        self._pulse  = QPropertyAnimation(self._effect, b"opacity", self)
        self._pulse.setDuration(1400)
        self._pulse.setKeyValueAt(0.0, 1.0)
        self._pulse.setKeyValueAt(0.5, 0.25)
        self._pulse.setKeyValueAt(1.0, 1.0)
        self._pulse.setLoopCount(-1)
        self.setGraphicsEffect(self._effect)

        self.set_state("loading")

    def set_state(self, state: str):
        self._state = state
        color, icon_name, text = self._STATES[state]
        self._icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(QSize(14, 14)))
        self._text_lbl.setText(text)
        self._text_lbl.setStyleSheet(
            f"color: {color}; font-family: 'Segoe UI'; font-size: 11px; background: transparent;"
        )
        if state == "loading":
            self._pulse.start()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("Chargement du modèle vocal…")
        else:
            self._pulse.stop()
            self._effect.setOpacity(1.0)
            if state == "failed":
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.setToolTip("Échec du chargement — cliquer pour réessayer")
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.setToolTip("Reconnaissance vocale opérationnelle")

    def mousePressEvent(self, event):
        if self._state == "failed":
            self.retry_requested.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, listener, on_close, on_progress=None):
        super().__init__()
        self._listener = listener
        self._on_close = on_close
        self._last_queue_key = None
        self._voice_started = False

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

        if on_progress: on_progress(55)
        root.addWidget(self._make_header())
        root.addWidget(FrillWidget())

        root.addWidget(self._make_content(on_progress=on_progress), stretch=1)

        self._last_shopping_key: tuple | None = None

        if on_progress: on_progress(93)
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

        self._voice_thread = VoiceLoaderThread(listener, parent=self)
        self._voice_thread.ready.connect(self._on_voice_ready)
        self._voice_thread.failed.connect(self._on_voice_failed)
        self._voice_thread.start()

        if on_progress: on_progress(100)

    # ── Build helpers ────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")

        h = QHBoxLayout(header)
        h.setContentsMargins(60, 16, 60, 12)

        left = QVBoxLayout()
        left.setSpacing(6)
        app_name = QLabel("Blancome")
        app_name.setObjectName("app_name")
        tagline = QLabel("YOUR HOME, ATTENDED")
        tagline.setObjectName("tagline")
        left.addWidget(app_name)
        left.addWidget(tagline)

        self._voice_widget = VoiceStatusWidget()
        self._voice_widget.retry_requested.connect(self._retry_voice)
        left.addWidget(self._voice_widget)

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

    # ── Voice loading ────────────────────────────────────────────────────

    def _on_voice_ready(self):
        self._voice_widget.set_state("ready")
        if not self._voice_started:
            self._voice_started = True
            threading.Thread(target=self._listener.start, daemon=True).start()

    def _on_voice_failed(self, error_msg: str):
        self._voice_widget.set_state("failed")
        logger.error("Voice model failed to load: %s", error_msg)

    def _retry_voice(self):
        self._voice_widget.set_state("loading")
        self._voice_thread = VoiceLoaderThread(self._listener, parent=self)
        self._voice_thread.ready.connect(self._on_voice_ready)
        self._voice_thread.failed.connect(self._on_voice_failed)
        self._voice_thread.start()

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(102)
        v = QVBoxLayout(sidebar)
        v.setContentsMargins(9, 12, 0, 12)
        v.setSpacing(6)
        v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._nav_music = NavButton("music")
        self._nav_music.setChecked(True)
        self._nav_shopping = NavButton("shopping")
        self._nav_calendar = NavButton("calendar")
        self._nav_settings = NavButton("settings")
        v.addWidget(self._nav_music, alignment=Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(self._nav_shopping, alignment=Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(self._nav_calendar, alignment=Qt.AlignmentFlag.AlignHCenter)
        v.addStretch()
        v.addWidget(self._nav_settings, alignment=Qt.AlignmentFlag.AlignHCenter)
        return sidebar

    def _make_content(self, on_progress=None) -> QWidget:
        content = QWidget()
        content.setObjectName("content")

        h = QHBoxLayout(content)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._make_sidebar())

        card_area = QWidget()
        card_area.setObjectName("card_area")
        ca = QHBoxLayout(card_area)
        ca.setContentsMargins(9, 12, 18, 12)
        self._stack = QStackedWidget()
        if on_progress: on_progress(62)
        self._stack.addWidget(self._make_card())
        if on_progress: on_progress(72)
        self._stack.addWidget(self._make_shopping_card())
        if on_progress: on_progress(80)
        self._stack.addWidget(self._make_calendar_card())
        if on_progress: on_progress(88)
        self._stack.addWidget(self._make_settings_card())
        ca.addWidget(self._stack)
        h.addWidget(card_area, stretch=1)

        self._nav_music.clicked.connect(lambda: self._switch_page(0))
        self._nav_shopping.clicked.connect(lambda: self._switch_page(1))
        self._nav_calendar.clicked.connect(lambda: self._switch_page(2))
        self._nav_settings.clicked.connect(lambda: self._switch_page(3))

        return content

    def _switch_page(self, index: int):
        if self._stack.currentIndex() == 3 and index != 3 and self._settings_has_changes():
            dlg = _UnsavedChangesDialog(self)
            dlg.adjustSize()
            geo = self.geometry()
            dlg.move(
                geo.x() + (geo.width()  - dlg.width())  // 2,
                geo.y() + (geo.height() - dlg.height()) // 2,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # Annuler — restore nav state and stay on settings
                self._nav_music.setChecked(False)
                self._nav_shopping.setChecked(False)
                self._nav_calendar.setChecked(False)
                self._nav_settings.setChecked(True)
                return
            if dlg.action == _UnsavedChangesDialog.SAVE_AND_QUIT:
                self._save_settings()

        self._stack.setCurrentIndex(index)
        self._nav_music.setChecked(index == 0)
        self._nav_shopping.setChecked(index == 1)
        self._nav_calendar.setChecked(index == 2)
        self._nav_settings.setChecked(index == 3)
        if index == 1:
            self._refresh_shopping()
        elif index == 3:
            self._refresh_settings()

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
        import config as _cfg
        self._shopping_send_btn = _IconButton('fa6s.paper-plane', 34, 28, _PLUM_SOFT, _GOLD, tooltip='Envoyer par SMS')
        self._shopping_send_btn.clicked.connect(self._send_shopping_list)
        self._shopping_send_btn.setVisible(bool(_cfg.FREE_MOBILE_USER and _cfg.FREE_MOBILE_API_KEY))
        hh.addWidget(self._shopping_send_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        v.addWidget(head)

        v.addWidget(_hsep())

        body = QWidget()
        body.setObjectName("body")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(30, 24, 30, 24)
        bv.setSpacing(0)

        self._shopping_list = QListWidget()
        self._shopping_list.setObjectName("shopping_list")
        self._shopping_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        QScroller.grabGesture(self._shopping_list.viewport(), QScroller.ScrollerGestureType.TouchGesture)
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
        add_btn = _IconButton('fa6s.plus', 34, 20, _PLUM_SOFT, _GOLD, tooltip='Ajouter')
        add_btn.clicked.connect(self._add_product)
        add_row.addWidget(self._product_input, stretch=1)
        add_row.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        bv.addLayout(add_row)

        v.addWidget(body, stretch=1)
        return card

    def _make_calendar_card(self) -> QFrame:
        self._last_events: list = []
        card = QFrame()
        card.setObjectName("card")
        self._calendar_card = card
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
        _danger_icon = Path(__file__).parent.parent / "assets" / "danger-icon.png"
        self._cal_error_icon = QLabel()
        self._cal_error_icon.setPixmap(
            QPixmap(str(_danger_icon)).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self._cal_error_icon.setToolTip("La dernière mise à jour du calendrier a échoué")
        self._cal_error_icon.hide()
        hh.addWidget(self._cal_error_icon)
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

        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bh2 = QHBoxLayout(bottom)
        bh2.setContentsMargins(0, 0, 0, 0)
        bh2.setSpacing(0)
        bh2.addWidget(self._make_day_detail_panel(), stretch=2)
        bh2.addWidget(_vsep())
        bh2.addWidget(self._make_legend_panel(), stretch=1)
        bv.addWidget(bottom)

        v.addWidget(body, stretch=1)
        return card

    def _make_events_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("body")
        v = QVBoxLayout(panel)
        v.setContentsMargins(24, 12, 24, 24)
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

    def _make_legend_panel(self) -> QWidget:
        self._hidden_colors: set = set()
        panel = QWidget()
        panel.setObjectName("body")
        v = QVBoxLayout(panel)
        v.setContentsMargins(24, 16, 24, 16)
        v.setSpacing(8)
        self._legend_items: list = []
        for color, label in [
            (_DOT_YELLOW, "Télétravail"),
            (_DOT_PURPLE, "Congés"),
            (_GOLD,       "Autres"),
        ]:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            rh = QHBoxLayout(row)
            rh.setSpacing(8)
            rh.setContentsMargins(0, 0, 0, 0)

            dot = QLabel("●")
            dot.setStyleSheet(
                f"color: {color}; background: transparent; font-size: 10pt;"
            )
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "color: #1a1a1a; font-family: 'Segoe UI'; font-size: 11pt;"
                " background: transparent;"
            )
            rh.addWidget(dot)
            rh.addWidget(lbl)
            rh.addStretch()
            v.addWidget(row)

            self._legend_items.append((color, dot, lbl))

            def _make_handler(c, d, lb):
                def handler(ev):
                    if ev.button() != Qt.MouseButton.LeftButton:
                        return
                    if c in self._hidden_colors:
                        self._hidden_colors.discard(c)
                        d.setStyleSheet(
                            f"color: {c}; background: transparent; font-size: 10pt;"
                        )
                        lb.setStyleSheet(
                            "color: #1a1a1a; font-family: 'Segoe UI'; font-size: 11pt;"
                            " background: transparent;"
                        )
                    else:
                        self._hidden_colors.add(c)
                        d.setStyleSheet(
                            "color: transparent; background: transparent; font-size: 10pt;"
                        )
                        lb.setStyleSheet(
                            f"color: {_MUTED}; font-family: 'Segoe UI'; font-size: 11pt;"
                            " background: transparent;"
                        )
                    self._apply_dot_filter()
                return handler

            row.mousePressEvent = _make_handler(color, dot, lbl)

        v.addStretch()
        return panel

    def _apply_dot_filter(self):
        date_colors: dict = {}
        for ev in getattr(self, "_cached_month_events", []):
            c = _event_dot_color(ev.get("summary", ""))
            if c in self._hidden_colors:
                continue
            for d, _ in _event_day_occurrences(ev):
                date_colors.setdefault(d, set()).add(c)
        self._cal_widget.set_event_dates(date_colors)

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
        if not self._last_events:
            self._clear_events_panel()
            loading = QLabel("Chargement…")
            loading.setObjectName("cal_placeholder")
            loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._events_layout.insertWidget(0, loading)

        today = datetime.date.today()
        self._cal_stop    = threading.Event()
        self._cal_fetcher = _CalendarFetcher(today, today + datetime.timedelta(days=30), self._cal_stop)
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
        self._last_events = events
        self._cal_error_icon.hide()
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

        rows: list = []
        for event in events:
            for event_date, time_str in _event_day_occurrences(event):
                rows.append((event_date, time_str, event))
        rows.sort(key=lambda r: r[0])

        current_date = None
        pos = 0
        for event_date, time_str, event in rows:
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
        self._cal_error_icon.show()
        if self._last_events:
            self._show_cal_toast(message)
            return
        self._clear_events_panel()
        lbl = QLabel("Aucun événement chargé")
        lbl.setObjectName("cal_placeholder")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        retry_btn = QPushButton("Réessayer")
        retry_btn.setObjectName("load_btn")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self._refresh_all_calendar)
        self._events_layout.insertWidget(0, retry_btn)
        self._events_layout.insertWidget(0, lbl)
        self._show_cal_toast(message)

    def _show_cal_toast(self, message: str):
        card = getattr(self, "_calendar_card", None)
        if card is None:
            return
        toast = _CalendarToast(message, self)
        toast.adjustSize()
        pos = card.mapTo(self, QPoint(card.width() - toast.width() - 16, 16))
        toast.move(pos)
        toast.show()
        toast.raise_()

    def _refresh_month_dots(self, year: int, month: int):
        if hasattr(self, "_dots_thread") and self._dots_thread.isRunning():
            return
        start = datetime.date(year, month, 1)
        end   = (datetime.date(year + 1, 1, 1) if month == 12
                 else datetime.date(year, month + 1, 1)) - datetime.timedelta(days=1)
        self._dots_stop    = threading.Event()
        self._dots_fetcher = _CalendarFetcher(start, end, self._dots_stop)
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
        self._apply_dot_filter()
        if self._cal_widget._selected_date is not None:
            self._on_day_selected(self._cal_widget._selected_date)

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
            for d, time_str in _event_day_occurrences(ev):
                if d == date:
                    day_events.append((ev, time_str))
                    break

        if not day_events:
            lbl = QLabel("Aucun événement")
            lbl.setObjectName("cal_placeholder")
            self._detail_events_layout.insertWidget(0, lbl)
            return

        for i, (ev, time_str) in enumerate(day_events):
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
        qv.addWidget(_hsep())

        total_row = QWidget()
        total_h = QHBoxLayout(total_row)
        total_h.setContentsMargins(16, 6, 16, 8)
        total_h.setSpacing(0)
        total_caption = QLabel("Durée totale")
        total_caption.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        self._total_time_lbl = QLabel("—")
        self._total_time_lbl.setStyleSheet(f"color: {_PLUM}; font-size: 11px; font-weight: bold;")
        self._total_time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        total_h.addWidget(total_caption)
        total_h.addStretch()
        total_h.addWidget(self._total_time_lbl)
        qv.addWidget(total_row)

        outer.addWidget(right_widget, stretch=1)
        return body

    def _make_progress_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(15)

        self._cur_lbl = QLabel("0:00")
        self._cur_lbl.setObjectName("time_lbl")
        self._cur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._cur_lbl.setFixedWidth(54)

        self._slider = _SeekSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("progress")
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider_dragging = False
        self._slider.sliderPressed.connect(self._on_seek_start)
        self._slider.sliderReleased.connect(self._on_seek_end)

        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setObjectName("time_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._dur_lbl.setFixedWidth(54)

        h.addWidget(self._cur_lbl)
        h.addWidget(self._slider)
        h.addWidget(self._dur_lbl)
        return h

    def _on_seek_start(self):
        self._slider_dragging = True

    def _on_seek_end(self):
        _, dur = music_service.get_position()
        if dur > 0:
            music_service.seek(self._slider.value() / 1000.0 * dur)
        self._slider_dragging = False

    def _make_controls_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        h.setSpacing(12)

        self._shuffle_btn = _IconButton('fa6s.shuffle', 66, 32, _PLUM, _AZURE_DEEP, _MUTED,
                                        active_color=_RUBY, tooltip='Lecture aléatoire')
        self._shuffle_btn.clicked.connect(self._toggle_shuffle)

        self._prev_btn = _IconButton('fa6s.backward-step', 66, 32, _PLUM, _AZURE_DEEP, _MUTED)
        self._prev_btn.clicked.connect(music_service.previous)

        self._play_btn = PlayButton()
        self._play_btn.clicked.connect(music_service.toggle_pause)

        self._next_btn = _IconButton('fa6s.forward-step', 66, 32, _PLUM, _AZURE_DEEP, _MUTED)
        self._next_btn.clicked.connect(music_service.next)

        self._stop_btn = _IconButton('fa6s.stop', 66, 32, _PLUM, _RUBY, _MUTED, tooltip='Arrêter et vider la file')
        self._stop_btn.clicked.connect(music_service.stop)

        h.addWidget(self._shuffle_btn)
        h.addWidget(self._prev_btn)
        h.addWidget(self._play_btn)
        h.addWidget(self._next_btn)
        h.addWidget(self._stop_btn)
        return h

    def _toggle_shuffle(self):
        music_service.toggle_shuffle()

    def _on_files_dropped(self, paths: list[Path]):
        was_empty = not music_service.has_tracks()
        for p in paths:
            music_service.add_track(p)
        if was_empty:
            music_service.play()

    def _make_queue(self) -> QTreeWidget:
        tv = _DroppableQueueWidget(self._on_files_dropped)
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
        tv.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        tv.setItemDelegate(_QueueDelegate(tv))
        tv.itemClicked.connect(self._on_queue_click)
        tv.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tv.customContextMenuRequested.connect(self._on_queue_context_menu)
        QScroller.grabGesture(tv.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        self._queue_scrolling = False
        QScroller.scroller(tv.viewport()).stateChanged.connect(self._on_queue_scroller_state)
        self._queue_tv = tv
        return tv

    # ── Settings card ────────────────────────────────────────────────────

    def _make_settings_card(self) -> QFrame:
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
        title = QLabel("Paramètres")
        title.setObjectName("music_title")
        hh.addWidget(title)
        hh.addStretch()
        v.addWidget(head)

        v.addWidget(_hsep())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("settings_scroll")

        body_widget = QWidget()
        body_widget.setObjectName("body")
        bv = QVBoxLayout(body_widget)
        bv.setContentsMargins(30, 28, 30, 28)
        bv.setSpacing(28)

        bv.addWidget(self._make_settings_free_mobile())
        bv.addWidget(self._make_settings_shopping())
        bv.addWidget(self._make_settings_playlists())
        bv.addStretch()

        scroll.setWidget(body_widget)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.TouchGesture)
        v.addWidget(scroll, stretch=1)

        v.addWidget(_hsep())
        save_bar = QWidget()
        save_bar.setObjectName("body")
        save_bar.setFixedHeight(64)
        sb = QHBoxLayout(save_bar)
        sb.setContentsMargins(30, 0, 30, 0)
        self._settings_save_btn = QPushButton("Enregistrer")
        self._settings_save_btn.setObjectName("save_btn")
        self._settings_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_save_btn.clicked.connect(self._save_settings)
        sb.addStretch()
        sb.addWidget(self._settings_save_btn)
        v.addWidget(save_bar)

        return card

    def _make_settings_free_mobile(self) -> QWidget:
        import config as _cfg
        section = QWidget()
        sv = QVBoxLayout(section)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(10)

        lbl = QLabel("FREE MOBILE")
        lbl.setObjectName("settings_section")
        sv.addWidget(lbl)
        sv.addWidget(_hsep())
        sv.addSpacing(4)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnMinimumWidth(0, 120)

        user_lbl = QLabel("Identifiant")
        user_lbl.setObjectName("settings_field_label")
        self._settings_user_edit = QLineEdit(_cfg.FREE_MOBILE_USER)
        self._settings_user_edit.setObjectName("settings_input")
        self._settings_user_edit.setPlaceholderText("Identifiant Free Mobile")
        grid.addWidget(user_lbl, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self._settings_user_edit, 0, 1)

        key_lbl = QLabel("Clé API")
        key_lbl.setObjectName("settings_field_label")
        self._settings_key_edit = QLineEdit(_cfg.FREE_MOBILE_API_KEY)
        self._settings_key_edit.setObjectName("settings_input")
        self._settings_key_edit.setPlaceholderText("Clé API Free Mobile")
        self._settings_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        show_btn = _IconButton('fa6s.eye', 32, 16, _MUTED, _GOLD, tooltip='Afficher / masquer')
        show_btn.setCheckable(True)
        show_btn.toggled.connect(
            lambda checked: self._settings_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.addWidget(self._settings_key_edit, stretch=1)
        key_row.addWidget(show_btn)
        grid.addWidget(key_lbl, 1, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addLayout(key_row, 1, 1)

        sv.addLayout(grid)
        return section

    def _make_settings_shopping(self) -> QWidget:
        import config as _cfg
        section = QWidget()
        sv = QVBoxLayout(section)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(10)

        lbl = QLabel("LISTE DE COURSES")
        lbl.setObjectName("settings_section")
        sv.addWidget(lbl)
        sv.addWidget(_hsep())
        sv.addSpacing(4)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnMinimumWidth(0, 120)

        file_lbl = QLabel("Fichier")
        file_lbl.setObjectName("settings_field_label")

        self._settings_shopping_edit = QLineEdit(
            str(_cfg.SHOPPING_LIST_FILE) if _cfg.SHOPPING_LIST_FILE else ""
        )
        self._settings_shopping_edit.setObjectName("settings_input")
        self._settings_shopping_edit.setPlaceholderText("Chemin du fichier…")
        self._settings_shopping_edit.setReadOnly(True)

        browse_btn = _IconButton('fa6s.folder-open', 32, 18, _PLUM_SOFT, _GOLD, tooltip='Choisir…')
        browse_btn.clicked.connect(self._browse_shopping_file)

        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.addWidget(self._settings_shopping_edit, stretch=1)
        file_row.addWidget(browse_btn)
        grid.addWidget(file_lbl, 0, 0, Qt.AlignmentFlag.AlignVCenter)
        grid.addLayout(file_row, 0, 1)

        sv.addLayout(grid)
        return section

    def _make_settings_playlists(self) -> QWidget:
        import config as _cfg
        section = QWidget()
        sv = QVBoxLayout(section)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        lbl = QLabel("PLAYLISTS")
        lbl.setObjectName("settings_section")
        lbl.setFixedWidth(110)  # matches name_edit width → ⓘ lands in same column
        info_btn = _IconButton(
            'fa6s.circle-info', 22, 13, _MUTED, _MUTED,
            tooltip=(
                "Ce nom est utilisé comme mot-clé de déclenchement vocal.\n"
                "Ex. : \"musique ROCK\""
            ),
        )
        info_btn.setCursor(Qt.CursorShape.ArrowCursor)
        header_row.addWidget(lbl)
        header_row.addWidget(info_btn)
        header_row.addStretch()
        sv.addLayout(header_row)
        sv.addWidget(_hsep())
        sv.addSpacing(4)

        self._playlist_rows: list[dict] = []
        self._playlists_container = QWidget()
        self._playlists_layout = QVBoxLayout(self._playlists_container)
        self._playlists_layout.setContentsMargins(0, 0, 0, 0)
        self._playlists_layout.setSpacing(8)

        for name, path in _cfg.PLAYLIST_FILES.items():
            row_widget = self._make_playlist_row(name, str(path))
            self._playlists_layout.addWidget(row_widget)

        sv.addWidget(self._playlists_container)

        add_btn = QPushButton("＋  Ajouter une playlist")
        add_btn.setObjectName("add_playlist_btn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_playlist_row)
        sv.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        return section

    def _make_playlist_row(self, name: str = "", path: str = "") -> QWidget:
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        name_edit = QLineEdit(name.upper() if name else "")
        name_edit.setObjectName("settings_input")
        name_edit.setPlaceholderText("NOM")
        name_edit.setFixedWidth(110)

        path_edit = QLineEdit(path)
        path_edit.setObjectName("settings_input")
        path_edit.setPlaceholderText("Chemin du fichier…")
        path_edit.setReadOnly(True)

        browse_btn = _IconButton('fa6s.folder-open', 32, 18, _PLUM_SOFT, _GOLD, tooltip='Choisir…')
        del_btn    = _IconButton('fa6s.xmark',       32, 16, _MUTED,      _RUBY, tooltip='Supprimer')

        row_data = {"name_edit": name_edit, "path_edit": path_edit, "row": row}
        browse_btn.clicked.connect(lambda: self._browse_playlist_file(path_edit))
        del_btn.clicked.connect(lambda: self._remove_playlist_row(row_data))

        rl.addWidget(name_edit)
        rl.addWidget(path_edit, stretch=1)
        rl.addWidget(browse_btn)
        rl.addWidget(del_btn)

        self._playlist_rows.append(row_data)
        return row

    def _add_playlist_row(self):
        row_widget = self._make_playlist_row()
        self._playlists_layout.addWidget(row_widget)

    def _remove_playlist_row(self, row_data: dict):
        if row_data in self._playlist_rows:
            self._playlist_rows.remove(row_data)
        row_data["row"].deleteLater()

    def _browse_shopping_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le fichier de liste de courses",
            str(self._settings_shopping_edit.text()) or "",
            "Fichiers texte (*.txt);;Tous les fichiers (*.*)",
        )
        if path:
            self._settings_shopping_edit.setText(path)

    def _browse_playlist_file(self, path_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier de playlist",
            str(path_edit.text()) or "",
            _PLAYLIST_FILETYPES,
        )
        if path:
            path_edit.setText(path)

    def _refresh_settings(self):
        import config as _cfg
        self._settings_user_edit.setText(_cfg.FREE_MOBILE_USER)
        self._settings_key_edit.setText(_cfg.FREE_MOBILE_API_KEY)
        self._settings_shopping_edit.setText(
            str(_cfg.SHOPPING_LIST_FILE) if _cfg.SHOPPING_LIST_FILE else ""
        )

        self._playlist_rows.clear()
        while self._playlists_layout.count():
            item = self._playlists_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name, path in _cfg.PLAYLIST_FILES.items():
            row_widget = self._make_playlist_row(name, str(path))
            self._playlists_layout.addWidget(row_widget)

        self._settings_snapshot()

    def _settings_snapshot(self):
        self._settings_base = {
            "user":      self._settings_user_edit.text(),
            "api_key":   self._settings_key_edit.text(),
            "shopping":  self._settings_shopping_edit.text(),
            "playlists": [
                (rd["name_edit"].text(), rd["path_edit"].text())
                for rd in self._playlist_rows
            ],
        }

    def _settings_has_changes(self) -> bool:
        base = getattr(self, "_settings_base", None)
        if base is None:
            return False
        return (
            self._settings_user_edit.text()     != base["user"]     or
            self._settings_key_edit.text()      != base["api_key"]  or
            self._settings_shopping_edit.text() != base["shopping"] or
            [
                (rd["name_edit"].text(), rd["path_edit"].text())
                for rd in self._playlist_rows
            ] != base["playlists"]
        )

    def _save_settings(self):
        user     = self._settings_user_edit.text().strip()
        api_key  = self._settings_key_edit.text().strip()
        shopping = self._settings_shopping_edit.text().strip()
        playlists = {
            rd["name_edit"].text().strip().upper(): rd["path_edit"].text().strip()
            for rd in self._playlist_rows
            if rd["name_edit"].text().strip() and rd["path_edit"].text().strip()
        }

        settings_service.save_all(user, api_key, shopping, playlists)
        import config as _cfg
        self._shopping_send_btn.setVisible(bool(_cfg.FREE_MOBILE_USER and _cfg.FREE_MOBILE_API_KEY))
        self._settings_snapshot()

        self._settings_save_btn.setText("✓  Enregistré")
        self._settings_save_btn.setEnabled(False)
        self.setFocus()  # reclaim focus so Qt doesn't push it to the next input
        QTimer.singleShot(2000, self._on_settings_saved)

    def _on_settings_saved(self):
        self._settings_save_btn.setText("Enregistrer")
        self._settings_save_btn.setEnabled(True)

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

    def _on_queue_scroller_state(self, state):
        if state in (QScroller.State.Dragging, QScroller.State.Scrolling):
            self._queue_scrolling = True
        elif state == QScroller.State.Inactive and self._queue_scrolling:
            QTimer.singleShot(300, lambda: setattr(self, '_queue_scrolling', False))

    def _on_queue_click(self, item: QTreeWidgetItem, _col: int):
        if self._queue_scrolling:
            return
        idx = self._queue_tv.indexOfTopLevelItem(item)
        if idx >= 0:
            music_service.play_track(idx)

    def _on_queue_context_menu(self, pos: QPoint):
        item = self._queue_tv.itemAt(pos)
        if item is None:
            return
        idx = self._queue_tv.indexOfTopLevelItem(item)
        if idx < 0:
            return
        menu = QMenu(self._queue_tv)
        remove_action = menu.addAction("Retirer de la file")
        if menu.exec(self._queue_tv.viewport().mapToGlobal(pos)) == remove_action:
            music_service.remove_track(idx)

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
        if not self._slider_dragging:
            self._slider.blockSignals(True)
            self._slider.setValue(int(cur / dur * 1000) if dur > 0 else 0)
            self._slider.blockSignals(False)

        self._play_btn.set_playing(music_service.is_playing())

        active = music_service.is_playing() or music_service.is_paused()
        has_tracks = music_service.has_tracks()
        self._shuffle_btn.setEnabled(has_tracks)
        self._shuffle_btn.set_active(music_service.is_shuffle())
        self._prev_btn.setEnabled(active)
        self._next_btn.setEnabled(active)
        self._stop_btn.setEnabled(active)

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

            total_s = int(sum(t["duration"] for t in tracks if t.get("duration")))
            if tracks and total_s:
                h = total_s // 3600
                m = (total_s % 3600) // 60
                s = total_s % 60
                total_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            else:
                total_str = "—"
            self._total_time_lbl.setText(total_str)

    def closeEvent(self, event):
        self._timer.stop()
        self._clock_timer.stop()
        self._shopping_timer.stop()
        self._events_timer.stop()
        # Disconnect voice thread signals so a late emission doesn't touch the destroyed window
        try:
            self._voice_thread.ready.disconnect()
            self._voice_thread.failed.disconnect()
        except RuntimeError:
            pass
        if self._voice_thread.isRunning():
            self._voice_thread.terminate()
            self._voice_thread.wait()
        if hasattr(self, "_cal_stop"):
            self._cal_stop.set()
        if hasattr(self, "_dots_stop"):
            self._dots_stop.set()
        self._on_close()
        event.accept()


def run(listener, on_close, splash=None):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("blancome.app")
    _t = time.perf_counter()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLESHEET)

    if splash:
        splash.step(45)
    logger.info("QApplication ready — %.3fs", time.perf_counter() - _t)

    _t = time.perf_counter()

    def _progress(val: int):
        if splash:
            splash.step(val)

    window = MainWindow(listener=listener, on_close=on_close, on_progress=_progress)
    logger.info("MainWindow built — %.3fs", time.perf_counter() - _t)

    if splash:
        splash.finish(window)
    window.showMaximized()
    app.exec()
