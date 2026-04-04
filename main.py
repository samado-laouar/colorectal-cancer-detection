import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

from PySide6.QtWidgets import QApplication, QStackedWidget
from ui.home_page import HomePage
from ui.histology_window import HistologyWindow
from ui.ihc_window import IHCWindow


class AppWindow(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ColonScan — AI Cancer Detection")

        # Build all pages once
        self.home = HomePage(self)
        self.histology = HistologyWindow(self)
        self.ihc = IHCWindow(self)

        self.addWidget(self.home)       # index 0
        self.addWidget(self.histology)  # index 1
        self.addWidget(self.ihc)        # index 2

        self.showMaximized()

    def go_home(self):
        self.setCurrentIndex(0)

    def go_histology(self):
        self.setCurrentIndex(1)

    def go_ihc(self):
        self.setCurrentIndex(2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())