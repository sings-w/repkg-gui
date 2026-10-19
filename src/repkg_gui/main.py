import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("RePKG GUI")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
