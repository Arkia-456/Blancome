import ctypes
import sys
import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QFrame, QHeaderView, QAbstractItemView, QSlider, QSizePolicy,
    QStyledItemDelegate, QStackedWidget, QListWidget, QListWidgetItem, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath, QIcon, QBrush, QRadialGradient, QFont

from assistant.music_service import music_service
from assistant.shopping_service import shopping_service

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


class FrillWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        s = w / 1200
        pts = [(int(x * s), y) for x, y in _FRILL_RAW]

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(w, 0)
        for x, y in reversed(pts):
            path.lineTo(x, y)
        path.closeSubpath()
        p.fillPath(path, QColor(_PLUM))

        n = len(pts)
        for i in range(n - 1):
            pen = QPen(QColor(_frill_color(i / (n - 2))), 2,
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
    font-size: 20pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#tagline {{
    color: {_GOLD};
    font-family: "Segoe UI";
    font-size: 8pt;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#clock {{
    color: {_PEARL};
    font-family: Consolas;
    font-size: 18pt;
    background: transparent;
}}
QLabel#date_lbl {{
    color: {_DATE_FG};
    font-family: "Segoe UI";
    font-size: 10pt;
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
    font-size: 9pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#music_title {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 18pt;
    font-weight: bold;
    background: transparent;
}}
QPushButton#load_btn {{
    background-color: {_PEARL};
    color: {_PLUM_SOFT};
    border: 1px solid {_PEARL_DEEP};
    border-radius: 4px;
    padding: 4px 10px;
    font-family: "Segoe UI";
    font-size: 9pt;
}}
QPushButton#load_btn:hover {{
    background-color: {_PEARL_DEEP};
}}

/* ── Now playing ───────────────────────────────────────── */
QLabel#now_playing_lbl {{
    color: {_AZURE_DEEP};
    font-family: "Segoe UI";
    font-size: 9pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#track_title {{
    color: {_PLUM};
    font-family: Georgia;
    font-size: 17pt;
    font-weight: bold;
    background: transparent;
}}
QLabel#track_artist {{
    color: {_PLUM_SOFT};
    font-family: "Segoe UI";
    font-size: 11pt;
    background: transparent;
}}
QLabel#track_album {{
    color: {_MUTED};
    font-family: "Segoe UI";
    font-size: 9pt;
    font-style: italic;
    background: transparent;
}}
QLabel#time_lbl {{
    color: {_PLUM_SOFT};
    font-family: Consolas;
    font-size: 10pt;
    background: transparent;
    min-width: 36px;
}}

/* ── Progress slider ────────────────────────────────────── */
QSlider#progress::groove:horizontal {{
    background: {_PEARL_DEEP};
    height: 4px;
    border-radius: 2px;
    margin: 0px;
}}
QSlider#progress::sub-page:horizontal {{
    background: {_GOLD};
    height: 4px;
    border-radius: 2px;
}}
QSlider#progress::handle:horizontal {{
    background: {_GOLD};
    border: 2px solid {_CARD};
    width: 12px;
    height: 12px;
    margin: -4px 0px;
    border-radius: 6px;
}}

/* ── Controls (custom-painted — no QSS needed) ──────────── */

/* ── Queue ──────────────────────────────────────────────── */
QTreeWidget#queue {{
    background: {_CARD};
    border: none;
    outline: 0;
    font-family: "Segoe UI";
    font-size: 10pt;
    color: {_PLUM};
    show-decoration-selected: 0;
}}
QTreeWidget#queue::item {{
    height: 28px;
    border: none;
    padding: 0px 4px;
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
    font-size: 8pt;
    border: none;
    border-bottom: 1px solid {_PEARL_DEEP};
    padding: 2px 4px;
}}

/* ── Shopping ───────────────────────────────────────────── */
QListWidget#shopping_list {{
    background: {_CARD};
    border: none;
    outline: 0;
    font-family: "Segoe UI";
    font-size: 10pt;
    color: {_PLUM};
}}
QListWidget#shopping_list::item {{
    height: 32px;
    border-bottom: 1px solid {_PEARL_DEEP};
    padding: 0px 4px;
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
    padding: 4px 8px;
    font-family: "Segoe UI";
    font-size: 9pt;
}}
QLineEdit#product_input:focus {{
    border-color: {_GOLD};
    outline: none;
}}
QPushButton#remove_btn {{
    background: transparent;
    color: {_MUTED};
    border: none;
    border-radius: 10px;
    font-family: "Segoe UI";
    font-size: 13pt;
    font-weight: bold;
    padding: 0px;
}}
QPushButton#remove_btn:hover {{
    color: {_RUBY};
}}

/* ── Scrollbar ──────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {_PEARL};
    width: 8px;
    border: none;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {_PEARL_DEEP};
    border-radius: 4px;
    min-height: 20px;
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
        self.setFixedSize(80, 80)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_playing(self, playing: bool):
        if self._playing != playing:
            self._playing = playing
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r_btn, r_glow = 40, 40, 30, 38

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
        p.setPen(QPen(QColor(_GOLD), 2.5))
        p.setBrush(QBrush(fill))
        p.drawEllipse(cx - r_btn, cy - r_btn, r_btn * 2, r_btn * 2)

        # Icon — drawn as shapes so they're crisp and perfectly centred
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("white")))
        if self._playing:
            # Pause: two vertical bars  (5 × 20 px each, 6 px gap, centred at 40,40)
            p.drawRoundedRect(32, 30, 5, 20, 2, 2)
            p.drawRoundedRect(43, 30, 5, 20, 2, 2)
        else:
            # Play: right-pointing triangle (shifted +1 px right for visual balance)
            tri = QPainterPath()
            tri.moveTo(35, 30)
            tri.lineTo(35, 50)
            tri.lineTo(52, 40)
            tri.closeSubpath()
            p.drawPath(tri)


class SkipButton(QPushButton):
    """Compact skip button drawn as a filled triangle + bar."""

    def __init__(self, forward: bool, parent=None):
        super().__init__(parent)
        self._forward = forward
        self.setFixedSize(44, 44)
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

        # Icon: 16 px wide × 14 px tall, centred in 44×44 widget
        # y band: 15→29  |  x band: 14→30
        bw, bh, tw, gap = 3, 14, 11, 2  # bar width/height, triangle width, gap
        x0 = 14  # left edge (22 − 8)

        if self._forward:
            tri = QPainterPath()
            tri.moveTo(x0,        15)
            tri.lineTo(x0,        29)
            tri.lineTo(x0 + tw,   22)
            tri.closeSubpath()
            p.drawPath(tri)
            p.drawRect(x0 + tw + gap, 15, bw, bh)
        else:
            p.drawRect(x0, 15, bw, bh)
            tri = QPainterPath()
            tri.moveTo(x0 + bw + gap + tw, 15)
            tri.lineTo(x0 + bw + gap + tw, 29)
            tri.lineTo(x0 + bw + gap,      22)
            tri.closeSubpath()
            p.drawPath(tri)


class NavButton(QPushButton):
    """Sidebar navigation button with a custom-painted icon."""

    def __init__(self, section: str, parent=None):
        super().__init__(parent)
        self._section = section
        self.setFixedSize(56, 56)
        self.setCheckable(True)
        self.setStyleSheet("QPushButton{background:transparent;border:none;padding:0px;}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy, r = self.width() // 2, self.height() // 2, 22
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
        else:
            self._draw_shopping(p, color)

    def _draw_music(self, p: QPainter, color: QColor):
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        # Note head 1 (left)
        p.save(); p.translate(21, 37); p.rotate(-20)
        p.drawEllipse(-6, -4, 12, 8)
        p.restore()
        # Note head 2 (right)
        p.save(); p.translate(36, 34); p.rotate(-20)
        p.drawEllipse(-6, -4, 12, 8)
        p.restore()
        # Stems + connecting beam
        pen = QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(26, 34, 26, 18)
        p.drawLine(41, 31, 41, 15)
        p.drawLine(26, 18, 41, 15)

    def _draw_shopping(self, p: QPainter, color: QColor):
        pen = QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Document outline
        p.drawRoundedRect(17, 16, 22, 24, 2, 2)
        # Three list lines
        p.drawLine(22, 23, 34, 23)
        p.drawLine(22, 29, 34, 29)
        p.drawLine(22, 35, 30, 35)


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

    # ── Build helpers ────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")

        h = QHBoxLayout(header)
        h.setContentsMargins(40, 22, 40, 22)

        left = QVBoxLayout()
        left.setSpacing(4)
        app_name = QLabel("Blancome")
        app_name.setObjectName("app_name")
        tagline = QLabel("YOUR HOME, ATTENDED")
        tagline.setObjectName("tagline")
        left.addWidget(app_name)
        left.addWidget(tagline)

        right = QVBoxLayout()
        right.setSpacing(3)
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
        sidebar.setFixedWidth(56)
        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 8, 0, 8)
        v.setSpacing(4)
        self._nav_music = NavButton("music")
        self._nav_music.setChecked(True)
        self._nav_shopping = NavButton("shopping")
        v.addWidget(self._nav_music)
        v.addWidget(self._nav_shopping)
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
        ca.setContentsMargins(24, 16, 24, 16)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_card())
        self._stack.addWidget(self._make_shopping_card())
        ca.addWidget(self._stack)
        h.addWidget(card_area, stretch=1)

        self._nav_music.clicked.connect(lambda: self._switch_page(0))
        self._nav_shopping.clicked.connect(lambda: self._switch_page(1))

        return content

    def _switch_page(self, index: int):
        self._stack.setCurrentIndex(index)
        self._nav_music.setChecked(index == 0)
        self._nav_shopping.setChecked(index == 1)
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
        gold_band.setFixedHeight(4)
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
        gold_band.setFixedHeight(4)
        gold_band.setStyleSheet(f"background: {_GOLD}; border: none;")
        v.addWidget(gold_band)

        head = QFrame()
        head.setObjectName("card_head")
        hh = QHBoxLayout(head)
        hh.setContentsMargins(20, 14, 20, 14)
        title = QLabel("Liste de courses")
        title.setObjectName("music_title")
        hh.addWidget(title)
        hh.addStretch()
        send_btn = QPushButton("Envoyer par SMS")
        send_btn.setObjectName("load_btn")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._send_shopping_list)
        hh.addWidget(send_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        v.addWidget(head)

        v.addWidget(_hsep())

        body = QWidget()
        body.setObjectName("body")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(20, 16, 20, 16)
        bv.setSpacing(0)

        self._shopping_list = QListWidget()
        self._shopping_list.setObjectName("shopping_list")
        bv.addWidget(self._shopping_list, stretch=1)

        bv.addSpacing(10)
        bv.addWidget(_hsep())
        bv.addSpacing(10)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
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

    def _make_card_head(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card_head")

        h = QHBoxLayout(frame)
        h.setContentsMargins(20, 14, 20, 14)

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

        v = QVBoxLayout(body)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(0)

        now_lbl = QLabel("EN COURS")
        now_lbl.setObjectName("now_playing_lbl")
        v.addWidget(now_lbl)

        self._title_lbl = QLabel("—")
        self._title_lbl.setObjectName("track_title")
        self._title_lbl.setWordWrap(True)
        v.addWidget(self._title_lbl)
        v.addSpacing(4)

        self._artist_lbl = QLabel("—")
        self._artist_lbl.setObjectName("track_artist")
        self._artist_lbl.setWordWrap(True)
        v.addWidget(self._artist_lbl)
        v.addSpacing(2)

        self._album_lbl = QLabel()
        self._album_lbl.setObjectName("track_album")
        self._album_lbl.setWordWrap(True)
        v.addWidget(self._album_lbl)
        v.addSpacing(12)

        v.addLayout(self._make_progress_row())
        v.addSpacing(8)
        v.addLayout(self._make_controls_row())
        v.addSpacing(14)
        v.addWidget(_hsep())
        v.addSpacing(4)
        v.addWidget(self._make_queue(), stretch=1)
        return body

    def _make_progress_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(10)

        self._cur_lbl = QLabel("0:00")
        self._cur_lbl.setObjectName("time_lbl")
        self._cur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._cur_lbl.setFixedWidth(36)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("progress")
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setEnabled(False)  # display-only until seek is implemented

        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setObjectName("time_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._dur_lbl.setFixedWidth(36)

        h.addWidget(self._cur_lbl)
        h.addWidget(self._slider)
        h.addWidget(self._dur_lbl)
        return h

    def _make_controls_row(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        h.setSpacing(8)

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
        tv.setColumnWidth(0, 36)
        tv.setColumnWidth(2, 52)
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
        item.setSizeHint(QSize(0, 36))

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(8, 0, 4, 0)
        h.setSpacing(8)

        btn = QPushButton("×")
        btn.setObjectName("remove_btn")
        btn.setFixedSize(22, 22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, t=text: self._remove_product(t))
        h.addWidget(btn)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {_PLUM}; font-family: 'Segoe UI'; font-size: 10pt; background: transparent;"
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
