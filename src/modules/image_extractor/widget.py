from PyQt5.QtWidgets import QWidget, QVBoxLayout
from ..base_module import PDFModule


class ImageExtractorModule(PDFModule):
    def __init__(self):
        # No need to call super().__init__() for ABC classes
        pass

    def get_name(self) -> str:
        return "Image Extractor"

    def get_description(self) -> str:
        return "Extract images from PDF files"

    def get_widget(self) -> QWidget:
        return ImageExtractorWidget()


class ImageExtractorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
