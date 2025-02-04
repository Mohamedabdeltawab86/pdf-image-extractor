import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from .main_window import MainWindow
from . import resources_rc


def run_app():
    app = QApplication(sys.argv)

    # Set application-wide style
    app.setStyle("Fusion")

    # Force RTL layout for Arabic
    app.setLayoutDirection(Qt.RightToLeft)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
