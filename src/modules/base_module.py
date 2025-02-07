# src/modules/base_module.py
from PyQt5.QtWidgets import QWidget

class PDFModuleBase(QWidget):  # Inherit from QWidget
    def __init__(self):
        super().__init__()

    def get_description(self):
        raise NotImplementedError

    def get_name(self):
        raise NotImplementedError

    def get_widget(self):
        return self # return the widget it self