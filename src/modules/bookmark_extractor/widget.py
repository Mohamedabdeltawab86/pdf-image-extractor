# src/modules/bookmark_extractor/widget.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from ..base_module import PDFModuleBase

class BookmarkExtractorModule(PDFModuleBase):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Bookmark Extractor Module")
        layout.addWidget(label)
        self.setLayout(layout)

    def get_description(self):
        return "Extract bookmarks from PDF files."

    def get_name(self):
        return "Bookmark Extractor"

    def get_widget(self):
        return self