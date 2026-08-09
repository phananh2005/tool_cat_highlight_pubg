"""Timeline custom widget — hiển thị toàn bộ video, đánh dấu match và highlight.

Click = seek đến vị trí, drag handles = chỉnh highlight boundaries.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent, QPaintEvent

from core.models import Match, Highlight


# Bảng màu cho các game
MATCH_COLORS = [
    QColor(60, 80, 120, 50),
    QColor(80, 120, 60, 50),
    QColor(120, 80, 60, 50),
    QColor(80, 60, 120, 50),
    QColor(120, 120, 60, 50),
    QColor(60, 120, 120, 50),
]

HIGHLIGHT_COLORS = {
    "kill": QColor(220, 50, 50),
    "audio_spike": QColor(255, 165, 0),
    "scene_change": QColor(50, 150, 255),
    "manual": QColor(0, 200, 100),
    "mixed": QColor(200, 200, 50),
}


class TimelineWidget(QWidget):
    """Custom timeline bar with match backgrounds and highlight markers."""

    # Signals
    seek_requested = pyqtSignal(float)   # time in seconds
    highlight_moved = pyqtSignal(int, float, float)  # highlight_idx, new_start, new_end

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._duration: float = 0.0
        self._position: float = 0.0
        self._matches: list[Match] = []
        self._highlights: list[Highlight] = []

        # Drag state
        self._dragging: bool = False
        self._drag_highlight_idx: int = -1
        self._drag_edge: str = ""  # "start" or "end"

    # --- Public API ---

    def set_data(self, duration: float, matches: list[Match], highlights: list[Highlight]):
        self._duration = max(duration, 0.001)
        self._matches = matches
        self._highlights = highlights
        self.update()

    def set_position(self, time_sec: float):
        self._position = time_sec
        self.update()

    # --- Coordinate helpers ---

    def _time_to_x(self, t: float) -> float:
        margin = 10
        usable = self.width() - 2 * margin
        if self._duration <= 0:
            return margin
        return margin + (t / self._duration) * usable

    def _x_to_time(self, x: float) -> float:
        margin = 10
        usable = self.width() - 2 * margin
        if usable <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, (x - margin) / usable))
        return ratio * self._duration

    # --- Paint ---

    def paintEvent(self, event: QPaintEvent):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 10
        bar_y = 15
        bar_h = h - 30

        # Background
        p.fillRect(0, 0, w, h, QColor(30, 30, 35))

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(50, 50, 60))
        p.drawRoundedRect(margin, bar_y, w - 2 * margin, bar_h, 4, 4)

        # Match backgrounds
        for m in self._matches:
            x1 = self._time_to_x(m.start_time)
            x2 = self._time_to_x(m.end_time)
            color = MATCH_COLORS[m.index % len(MATCH_COLORS)]
            p.setBrush(color)
            p.drawRect(int(x1), bar_y, int(x2 - x1), bar_h)

            # Match label
            p.setPen(QColor(180, 180, 180))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(int(x1 + 4), bar_y + 12, m.label)

        # Highlight markers
        marker_h = bar_h - 4
        for hl in self._highlights:
            if not hl.enabled:
                continue
            x1 = self._time_to_x(hl.start_time)
            x2 = self._time_to_x(hl.end_time)
            color = HIGHLIGHT_COLORS.get(hl.highlight_type, QColor(200, 200, 200))
            fill = QColor(color)
            fill.setAlpha(120)
            p.setBrush(fill)
            p.setPen(QPen(color, 1))
            rect_w = max(4, int(x2 - x1))
            p.drawRoundedRect(int(x1), bar_y + 2, rect_w, marker_h, 2, 2)

        # Playback position
        px = self._time_to_x(self._position)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawLine(int(px), bar_y - 2, int(px), bar_y + bar_h + 2)

        # Position triangle
        p.setBrush(QColor(255, 255, 255))
        p.setPen(Qt.PenStyle.NoPen)
        tri_size = 5
        p.drawPolygon([
            QPointF(px - tri_size, bar_y - 2),
            QPointF(px + tri_size, bar_y - 2),
            QPointF(px, bar_y + 4),
        ])

        p.end()

    # --- Mouse events ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            t = self._x_to_time(event.position().x())
            # Kiểm tra có đang drag edge highlight không
            hl_idx, edge = self._hit_test_edge(event.position().x())
            if hl_idx >= 0:
                self._dragging = True
                self._drag_highlight_idx = hl_idx
                self._drag_edge = edge
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.seek_requested.emit(t)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and self._drag_highlight_idx >= 0:
            t = self._x_to_time(event.position().x())
            hl = self._highlights[self._drag_highlight_idx]
            if self._drag_edge == "start":
                new_start = min(t, hl.end_time - 0.5)
                self.highlight_moved.emit(self._drag_highlight_idx, max(0, new_start), hl.end_time)
            else:
                new_end = max(t, hl.start_time + 0.5)
                self.highlight_moved.emit(self._drag_highlight_idx, hl.start_time, min(new_end, self._duration))
            self.update()
        else:
            # Hover cursor
            hl_idx, _ = self._hit_test_edge(event.position().x())
            if hl_idx >= 0:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)

            # Tooltip
            t = self._x_to_time(event.position().x())
            mins, secs = divmod(int(t), 60)
            hours, mins = divmod(mins, 60)
            QToolTip.showText(event.globalPosition().toPoint(), f"{hours:02d}:{mins:02d}:{secs:02d}")

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            self._dragging = False
            self._drag_highlight_idx = -1
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _hit_test_edge(self, x: float, tolerance: float = 6.0) -> tuple[int, str]:
        """Kiểm tra chuột có gần edge của highlight nào không."""
        for i, hl in enumerate(self._highlights):
            if not hl.enabled:
                continue
            sx = self._time_to_x(hl.start_time)
            ex = self._time_to_x(hl.end_time)
            if abs(x - sx) <= tolerance:
                return i, "start"
            if abs(x - ex) <= tolerance:
                return i, "end"
        return -1, ""
