import subprocess
import threading

from PySide6.QtCore import QThread, QTimer, Signal

CREATE_NO_WINDOW = 0x08000000


class RepkgThread(QThread):
    """后台执行 RePKG 子进程，逐行转发 stdout/stderr。"""

    line = Signal(str, bool)  # 文本, 是否 stderr
    finished_with = Signal(int, bool)  # 退出码, 是否被取消
    startup_error = Signal(str)

    def __init__(self, exe: str, args: list[str], parent=None):
        super().__init__(parent)
        self._exe = exe
        self._args = args
        self._proc: subprocess.Popen | None = None
        self._canceled = False

    def cancel(self) -> None:
        self._canceled = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            QTimer.singleShot(2000, self._force_kill)

    def _force_kill(self) -> None:
        p = self._proc
        if p and p.poll() is None:
            p.kill()

    def run(self) -> None:
        try:
            self._proc = subprocess.Popen(
                [self._exe, *self._args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            self.startup_error.emit(str(e))
            return

        def read_stderr() -> None:
            for line in self._proc.stderr:
                self.line.emit(line.rstrip(), True)

        err_thread = threading.Thread(target=read_stderr, daemon=True)
        err_thread.start()
        for line in self._proc.stdout:
            self.line.emit(line.rstrip(), False)
        err_thread.join(timeout=1)

        code = self._proc.wait()
        self.finished_with.emit(code, self._canceled)
