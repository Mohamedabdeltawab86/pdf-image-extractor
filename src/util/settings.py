from PyQt5.QtCore import QSettings
import os
from pathlib import Path


class Settings:
    def __init__(self):
        self.settings = QSettings("DrWaleed", "PDFImageExtractor")

    def get_language(self):
        return self.settings.value("language", "ar")  # Default to Arabic

    def set_language(self, lang):
        self.settings.setValue("language", lang)

    def get_font_size(self):
        return self.settings.value("font_size", 12, type=int)

    def set_font_size(self, size):
        self.settings.setValue("font_size", size)

    def save_last_pdf_path(self, path):
        self.settings.setValue("last_pdf_path", path)
        self.settings.setValue("last_directory", os.path.dirname(path))

    def get_last_pdf_path(self):
        return self.settings.value("last_pdf_path", "")

    def get_last_directory(self):
        return self.settings.value("last_directory", str(Path.home()))

    def get_default_output_dir(self):
        documents_path = os.path.join(Path.home(), "Documents", "PDF Image Extractor")
        os.makedirs(documents_path, exist_ok=True)
        return documents_path
