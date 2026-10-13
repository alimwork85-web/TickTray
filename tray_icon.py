from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap

SIZE = 64
TOP = QColor(99, 102, 241)
BOTTOM = QColor(139, 61, 214)
AMBER = QColor(251, 191, 36)


def render_icon(fraction=0.75, show_check=True):
    """Tray icon: the app icon, with the ring showing the share of time left (0..1)."""
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, 0, SIZE)
    grad.setColorAt(0, TOP)
    grad.setColorAt(1, BOTTOM)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(QRectF(2.5, 2.5, SIZE - 5, SIZE - 5), 14, 14)

    r = SIZE * 0.322
    box = QRectF(SIZE / 2 - r, SIZE / 2 - r, 2 * r, 2 * r)
    w = SIZE * 0.084
    pen = QPen(QColor(255, 255, 255, 70), w)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(box)

    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        pen = QPen(QColor(255, 255, 255), w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(box, 90 * 16, -int(360 * 16 * fraction))

    if show_check:
        pen = QPen(QColor(255, 255, 255), SIZE * 0.076)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        c = SIZE / 2
        k = SIZE / 1024
        p.drawPolyline([QPointF(c - 135 * k, c + 8 * k), QPointF(c - 28 * k, c + 118 * k),
                        QPointF(c + 150 * k, c - 105 * k)])
    p.end()
    return QIcon(pm)
