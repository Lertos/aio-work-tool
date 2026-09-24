"""Run a blocking function on Qt's thread pool and get the result back on the UI thread."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_running: set["_Task"] = set()  # keep Python objects alive until their signal is delivered


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self.setAutoDelete(False)
        self.fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # report anything to the UI instead of dying silently
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.signals.done.emit(result)


def run_in_background(fn: Callable[[], Any], on_done: Callable[[Any], None],
                      on_failed: Callable[[str], None]) -> None:
    task = _Task(fn)
    _running.add(task)

    def finish(callback, value):
        _running.discard(task)
        callback(value)

    task.signals.done.connect(lambda result: finish(on_done, result))
    task.signals.failed.connect(lambda message: finish(on_failed, message))
    QThreadPool.globalInstance().start(task)
