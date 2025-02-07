# D:\10 Coding\PDF Imaging\src\ui\app.py
import sys
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow  # Correct import


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())