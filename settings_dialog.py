from PyQt6.QtCore import (QEasingCurve, QLocale, QParallelAnimationGroup, QPoint, QPropertyAnimation, QRectF, QSize,
                          Qt, pyqtProperty)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QAbstractButton, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QVBoxLayout)

import config

EN = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

LIGHT = {"card": "#ffffff", "text": "#1f2330", "muted": "#6b7280", "field": "#f1f2f8", "line": "#e5e7f0",
         "off": "#c9ccd8", "hover": "#e6e8f6"}
DARK = {"card": "#23252f", "text": "#eceef6", "muted": "#9aa0b4", "field": "#2f323f", "line": "#363948",
        "off": "#4a4e60", "hover": "#3a3d4d"}
ACCENT = "#6366f1"
ACCENT_HOVER = "#7c7ff5"


class Toggle(QAbstractButton):
    """Switch with a sliding knob."""

    def __init__(self, checked=False, off_color="#c9ccd8", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QSize(46, 26))
        self._off = QColor(off_color)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._on_toggled)

    def _get_knob(self):
        return self._pos

    def _set_knob(self, v):
        self._pos = v
        self.update()

    knob = pyqtProperty(float, _get_knob, _set_knob)

    def _on_toggled(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._pos
        a, b = QColor(ACCENT), self._off
        col = QColor(int(b.red() + (a.red() - b.red()) * t), int(b.green() + (a.green() - b.green()) * t),
                     int(b.blue() + (a.blue() - b.blue()) * t))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(QRectF(0, 0, 46, 26), 13, 13)
        p.setBrush(QColor("white"))
        # the knob slides from the left (off) to the right (on), the same in every layout direction
        p.drawEllipse(QRectF(3 + 20 * t, 3, 20, 20))


class SettingsDialog(QDialog):
    def __init__(self, cfg, dark, parent=None):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.result_config = None
        self._closing = False
        self._shown = False
        self.c = DARK if dark else LIGHT

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle("إعدادات TickTray")
        self.setFixedSize(400, 480)
        self._drag = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        self.card = QFrame(self)
        self.card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(2)

        title = QLabel("الإعدادات")
        title.setObjectName("title")
        sub = QLabel("اضبط سلوك العداد كما يناسبك")
        sub.setObjectName("muted")
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addSpacing(10)

        top = cfg["maximumMinutes"]
        self.max_spin = self._spin(cfg["maximumMinutes"], 1, config.HARD_MAX_MINUTES)
        self.def_spin = self._spin(cfg["defaultMinutes"], 1, top)
        self.snooze_spin = self._spin(cfg["defaultSnoozeMinutes"], 1, top)
        self.max_spin.valueChanged.connect(self._sync_max)
        self.sound = Toggle(cfg["completionSound"], self.c["off"])
        self.auto = Toggle(cfg["startWithWindows"], self.c["off"])

        lay.addWidget(self._row("المدة الافتراضية", "تُستخدم عند بدء العداد بنقرة", self.def_spin))
        lay.addWidget(self._row("مدة التأجيل", "بعد انتهاء الوقت", self.snooze_spin))
        lay.addWidget(self._row("الحد الأقصى", "أعلى مدة يمكن ضبطها", self.max_spin))
        lay.addWidget(self._row("صوت التنبيه", "نغمة عند انتهاء الوقت", self.sound))
        lay.addWidget(self._row("التشغيل مع Windows", "يبدأ تلقائياً عند تسجيل الدخول", self.auto))
        lay.addStretch()

        btns = QHBoxLayout()
        btns.setSpacing(10)
        save = QPushButton("حفظ")
        save.setObjectName("primary")
        cancel = QPushButton("إلغاء")
        for b in (save, cancel):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(38)
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        save.setDefault(True)
        btns.addWidget(save, 2)
        btns.addWidget(cancel, 1)
        lay.addLayout(btns)

        self._apply_style()
        self._build_animations()

    def _spin(self, value, low, high):
        s = QSpinBox()
        s.setLocale(EN)
        s.setRange(low, high)
        s.setValue(value)
        s.setSuffix(" min")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setFixedSize(96, 34)
        s.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        s.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        return s

    def _row(self, title, hint, widget):
        row = QFrame()
        row.setObjectName("row")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 8, 0, 8)
        text = QVBoxLayout()
        text.setSpacing(0)
        a = QLabel(title)
        b = QLabel(hint)
        b.setObjectName("muted")
        text.addWidget(a)
        text.addWidget(b)
        h.addLayout(text, 1)
        h.addWidget(widget)
        return row

    def _sync_max(self, top):
        self.def_spin.setMaximum(top)
        self.snooze_spin.setMaximum(top)

    def _apply_style(self):
        c = self.c
        self.setStyleSheet(f"""
            QFrame#card {{ background: {c['card']}; border-radius: 18px; }}
            QLabel {{ color: {c['text']}; font-size: 13px; background: transparent; }}
            QLabel#title {{ font-size: 21px; font-weight: 700; }}
            QLabel#muted {{ color: {c['muted']}; font-size: 11px; }}
            QFrame#row {{ border-bottom: 1px solid {c['line']}; background: transparent; }}
            QSpinBox {{ background: {c['field']}; color: {c['text']}; border: 1px solid transparent;
                        border-radius: 9px; font-size: 13px; selection-background-color: {ACCENT}; }}
            QSpinBox:hover {{ border-color: {c['line']}; }}
            QSpinBox:focus {{ border-color: {ACCENT}; }}
            QPushButton {{ background: {c['field']}; color: {c['text']}; border: none; border-radius: 10px;
                           font-size: 13px; }}
            QPushButton:hover {{ background: {c['hover']}; }}
            QPushButton#primary {{ background: {ACCENT}; color: white; font-weight: 600; }}
            QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
        """)

    def _build_animations(self):
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._slide = QPropertyAnimation(self, b"pos")
        self._group = QParallelAnimationGroup(self)
        for a in (self._fade, self._slide):
            a.setDuration(220)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._group.addAnimation(a)

    def showEvent(self, e):
        super().showEvent(e)
        if self._shown:
            return
        self._shown = True
        end = self.pos()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._slide.setStartValue(end + QPoint(0, 18))
        self._slide.setEndValue(end)
        self.setWindowOpacity(0.0)
        self._group.start()

    def done(self, r):
        if self._closing:
            return
        self._closing = True
        self._group.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(self.pos() + QPoint(0, 12))
        self._fade.setDuration(150)
        self._slide.setDuration(150)
        self._group.finished.connect(lambda: QDialog.done(self, r))
        self._group.start()

    def force_close(self):
        """Close at once, skipping the exit animation (used when the whole app is quitting)."""
        self._closing = True
        self._group.stop()
        QDialog.done(self, 0)

    def _save(self):
        cfg = dict(self.cfg)
        cfg.update({
            "maximumMinutes": self.max_spin.value(),
            "defaultMinutes": self.def_spin.value(),
            "defaultSnoozeMinutes": self.snooze_spin.value(),
            "completionSound": self.sound.isChecked(),
            "startWithWindows": self.auto.isChecked(),
        })
        self.result_config = config.validate(cfg)
        self.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
