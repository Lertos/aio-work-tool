"""Short fading message centred on the window (replaces Toast.java).

Drawn as an overlay child of the window rather than a separate transparent
top-level window, which avoids per-platform translucency quirks.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ..config import TOAST_FADE_MS, TOAST_HOLD_MS


def show_toast(widget: QWidget, message: str) -> None:
    host = widget.window()
    label = QLabel(message, host)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    label.setStyleSheet("background: rgba(0, 0, 0, 190); color: white;"
                        "border-radius: 14px; padding: 12px 20px;")
    label.adjustSize()
    label.move((host.width() - label.width()) // 2, (host.height() - label.height()) // 2)

    effect = QGraphicsOpacityEffect(label)
    effect.setOpacity(0.0)
    label.setGraphicsEffect(effect)
    label.show()
    label.raise_()

    def fade(start: float, end: float) -> QPropertyAnimation:
        anim = QPropertyAnimation(effect, b"opacity", label)
        anim.setDuration(TOAST_FADE_MS)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        return anim

    sequence = QSequentialAnimationGroup(label)  # parented to the label, so it lives as long
    sequence.addAnimation(fade(0.0, 1.0))
    sequence.addPause(TOAST_HOLD_MS)
    sequence.addAnimation(fade(1.0, 0.0))
    sequence.finished.connect(label.deleteLater)
    sequence.start()
