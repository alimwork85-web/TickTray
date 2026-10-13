from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QIcon, QLinearGradient, QPainter, QPen, QPixmap

SIZE = 64
TOP = QColor(99, 102, 241)
BOTTOM = QColor(139, 61, 214)
AMBER = QColor(251, 191, 36)


def _fit_font(text, max_w, max_h):
    """Largest bold font whose rendering of `text` fits in max_w x max_h."""
    font = QFont("Segoe UI")
    font.setBold(True)
    size = int(max_h)
    while size > 6:
        font.setPixelSize(size)
        m = QFontMetricsF(font)
        if m.horizontalAdvance(text) <= max_w and m.capHeight() <= max_h:
            break
        size -= 1
    return font


def render_icon(fraction=0.75, show_check=True, text=None):
    """Tray icon: the app icon, with the ring showing the share of time left (0..1).

    With `text` (e.g. minutes left) the ring moves to the edge and the text fills the middle,
    so it stays readable at 16 px.
    """
    pm = QPixmap(SIZE, SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    grad = QLinearGradient(0, 0, 0, SIZE)
    grad.setColorAt(0, TOP)
    grad.setColorAt(1, BOTTOM)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(QRectF(2.5, 2.5, SIZE - 5, SIZE - 5), 14, 14)

    if text:
        r, w = SIZE * 0.41, SIZE * 0.06
    else:
        r, w = SIZE * 0.322, SIZE * 0.084
    box = QRectF(SIZE / 2 - r, SIZE / 2 - r, 2 * r, 2 * r)
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

    if text:
        inner = 2 * (r - w / 2)
        font = _fit_font(text, inner * 0.94, inner * 0.6)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        # center on the cap height so digits sit in the optical middle
        m = QFontMetricsF(font)
        x = (SIZE - m.horizontalAdvance(text)) / 2
        y = SIZE / 2 + m.capHeight() / 2
        p.drawText(QPointF(x, y), text)
    elif show_check:
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
